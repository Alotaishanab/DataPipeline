#!/usr/bin/env python

import os
import json
import logging
import torch
import esm
import traceback
from pyspark.sql import SparkSession

# ---------------------- #
# Safe Torch cache path
# ---------------------- #
os.environ["TORCH_HOME"] = "/tmp/torch_cache"

# ---------------------- #
# Logging configuration
# ---------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True
)
logger = logging.getLogger(__name__)

# ---------------------- #
# MAX SEQUENCE LENGTH
# ---------------------- #
MAX_SEQ_LEN = 3000  # adjust as needed

# ---------------------- #
# FASTA Parsing Function
# ---------------------- #
def parse_fasta_partition(rows):
    """
    Reads an iterator of PySpark Rows (each with a .value field)
    and yields each complete FASTA sequence as a string.
    """
    logger.info("🔍 Parsing FASTA partition")
    sequence = []
    for row in rows:
        line = row.value.strip()  # strip whitespace
        logger.info(f"📄 Line received: {line}")
        if line.startswith(">"):
            if sequence:
                yield "".join(sequence)
                sequence = []
        elif line:
            sequence.append(line)
    if sequence:
        yield "".join(sequence)

# ---------------------- #
# Batch Inference Function
# ---------------------- #
def run_batch(batch_data, model, batch_converter):
    """
    Runs inference on a batch of (label, sequence) tuples.
    Sequences longer than MAX_SEQ_LEN are truncated.
    """
    logger.info(f"🚀 Running inference on batch of size {len(batch_data)}")
    try:
        truncated_batch = []
        for (label, seq) in batch_data:
            if len(seq) > MAX_SEQ_LEN:
                logger.warning(f"Sequence length {len(seq)} exceeds {MAX_SEQ_LEN}, truncating.")
                seq = seq[:MAX_SEQ_LEN]
            truncated_batch.append((label, seq))
        # Convert sequences to tokens
        _, _, batch_tokens = batch_converter(truncated_batch)
        with torch.no_grad():
            # For the t30 model, request representations from layer 30
            results = model(batch_tokens, repr_layers=[30], return_contacts=False)
        token_reps = results["representations"][30]

        for i, (label, seq) in enumerate(truncated_batch):
            # Average the token representations (ignoring the special tokens)
            embedding = token_reps[i, 1:len(seq) + 1].mean(0).tolist()
            yield json.dumps({
                "sequence": seq,
                "embedding": embedding
            })

    except Exception as e:
        logger.error(f"❌ Batch processing error: {e}")
        logger.error(traceback.format_exc())
        for _, seq in batch_data:
            yield json.dumps({
                "sequence": seq,
                "error": str(e)
            })

# ---------------------- #
# Partition-level Inference
# ---------------------- #
def inference_map_partition(records):
    """
    Loads the ESM2 model once per partition and processes all sequences.
    """
    try:
        pid = os.getpid()
        logger.info(f"[Worker PID {pid}] ⚙️ Partition started. Loading model...")
        logger.info(f"[Worker PID {pid}] 🔧 TORCH_HOME: {os.environ.get('TORCH_HOME')}")
        model, alphabet = esm.pretrained.esm2_t30_150M_UR50D()
        model.eval()
        batch_converter = alphabet.get_batch_converter()

        batch_size = 1
        buffer = []
        count = 0
        for seq in parse_fasta_partition(records):
            if not seq:
                continue
            count += 1
            buffer.append(("sequence", seq))
            if len(buffer) == batch_size:
                yield from run_batch(buffer, model, batch_converter)
                buffer = []
        if buffer:
            yield from run_batch(buffer, model, batch_converter)
        logger.info(f"✅ Finished processing {count} sequences in partition.")
    except Exception as e:
        logger.error(f"💥 Partition-level error: {e}")
        logger.error(traceback.format_exc())
        yield json.dumps({"error": str(e)})

# ---------------------- #
# Main Spark Job
# ---------------------- #
def main():
    logger.info("🔥 Starting ESM2 Distributed Inference Job")
    try:
        # Rely on spark-submit --master yarn (do not specify local mode here)
        spark = SparkSession.builder.appName("ESM2-Pipeline").getOrCreate()

        # Use HDFS paths for input and output
        input_path = "hdfs:///user/almalinux/datasets/uniref50.fasta"
        output_path = "hdfs:///user/almalinux/results/esm2_embeddings_json"

        logger.info("📥 Reading FASTA file from HDFS...")
        df = spark.read.text(input_path)
        # Repartition to ensure sufficient parallelism across the cluster
        df = df.repartition(64)

        logger.info("🧠 Running distributed ESM inference across partitions...")
        rdd = df.rdd.mapPartitions(inference_map_partition)

        # Force actual computation
        record_count = rdd.count()
        logger.info(f"🧮 Total records processed by workers: {record_count}")

        logger.info("💾 Saving embeddings to HDFS...")
        rdd.saveAsTextFile(output_path)

        logger.info("🏁 ✅ Job completed successfully.")
        spark.stop()

    except Exception as e:
        logger.error(f"🔥 Fatal error in Spark job: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
