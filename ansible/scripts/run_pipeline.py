#!/usr/bin/env python

import os
import json
import logging
import torch
import esm
import traceback
import shutil
from pyspark.sql import SparkSession

# ---------------------- #
# Safe Torch cache path
# ---------------------- #
os.environ["TORCH_HOME"] = "/tmp/torch_cache"  # or wherever you'd like

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
# MAX SEQUENCE LENGTH (to prevent OOM)
# ---------------------- #
MAX_SEQ_LEN = 3000  # adjust as needed

# ---------------------- #
# FASTA Parsing function
# ---------------------- #
def parse_fasta_partition(rows):
    """
    Takes an iterator of PySpark Rows (each with .value field),
    yields each full sequence as a single string.
    """
    logger.info("🔍 Parsing FASTA partition")

    sequence = []
    for row in rows:
        line = row.value  # the actual string line
        line = line.strip()  # strip whitespace
        logger.info(f"📄 Line received: {line}")

        if line.startswith(">"):
            # If we already have a collected sequence, yield it
            if sequence:
                yield "".join(sequence)
                sequence = []
        elif line:
            sequence.append(line)

    # Yield the last sequence in the partition, if any
    if sequence:
        yield "".join(sequence)

# ---------------------- #
# Batch inference function
# ---------------------- #
def run_batch(batch_data, model, batch_converter):
    """
    Runs ESM inference on a batch of (label, sequence).
    If the sequence is too large, we truncate it to avoid OOM.
    """
    logger.info(f"🚀 Running inference on batch of size {len(batch_data)}")
    try:
        # Enforce max length to avoid huge memory usage
        truncated_batch_data = []
        for (label, seq) in batch_data:
            if len(seq) > MAX_SEQ_LEN:
                logger.warning(f"Sequence length {len(seq)} exceeds {MAX_SEQ_LEN}, truncating.")
                seq = seq[:MAX_SEQ_LEN]
            truncated_batch_data.append((label, seq))

        # Convert to tokens
        _, _, batch_tokens = batch_converter(truncated_batch_data)

        with torch.no_grad():
            results = model(batch_tokens, repr_layers=[30], return_contacts=False)
        token_representations = results["representations"][30]

        # Build embeddings
        for i, (label, seq) in enumerate(truncated_batch_data):
            # The model’s representations are aligned 1:1 with sequence length (after any trunc).
            embedding = token_representations[i, 1: len(seq) + 1].mean(0).tolist()
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
# Partition-level inference
# ---------------------- #
def inference_map_partition(records):
    """
    Loads the ESM2 model once per partition, processes sequences one at a time.
    """
    try:
        pid = os.getpid()
        logger.info(f"[Worker PID {pid}] ⚙️ Partition started. Loading model...")
        logger.info(f"[Worker PID {pid}] 🔧 TORCH_HOME: {os.environ.get('TORCH_HOME')}")

        # Use the 150M model
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

        # If there's anything left in buffer, process it
        if buffer:
            yield from run_batch(buffer, model, batch_converter)

        logger.info(f"✅ Finished processing {count} sequences in partition.")

    except Exception as e:
        logger.error(f"💥 Partition-level error: {e}")
        logger.error(traceback.format_exc())
        yield json.dumps({"error": str(e)})

# ---------------------- #
# Main Spark job
# ---------------------- #
def main():
    logger.info("🔥 Starting ESM2 Distributed Inference Job")
    try:
        spark = (SparkSession.builder
            .appName("ESM2-Pipeline")
            .master("local[1]")  # Local mode for testing
            .getOrCreate())

        # Local file paths
        input_path = "file:///home/almalinux/snippet.fasta"
        output_path = "file:///home/almalinux/esm2_embeddings_json_out"

        # Remove local output dir if it exists
        local_out_dir = "/home/almalinux/esm2_embeddings_json_out"
        if os.path.exists(local_out_dir):
            logger.warning(f"⚠️ Local output path {local_out_dir} exists. Deleting it.")
            shutil.rmtree(local_out_dir)

        logger.info("📥 Reading FASTA file from local filesystem...")
        df = spark.read.text(input_path)

        logger.info("🧠 Running distributed ESM inference across partitions...")
        rdd = df.rdd.mapPartitions(inference_map_partition)

        # Force evaluation
        record_count = rdd.count()
        logger.info(f"🧮 Total records processed by workers: {record_count}")

        logger.info("💾 Saving embeddings to local filesystem...")
        rdd.saveAsTextFile(output_path)

        logger.info("🏁 ✅ Job completed successfully.")
        spark.stop()

    except Exception as e:
        logger.error(f"🔥 Fatal error in Spark job: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
