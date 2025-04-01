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
MAX_SEQ_LEN = 3000

# ---------------------- #
# FASTA Parsing Function
# ---------------------- #
def parse_fasta_partition(rows):
    logger.info("🔍 Parsing FASTA partition")
    sequence = []
    for row in rows:
        line = row.value.strip()
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
    logger.info(f"🚀 Running inference on batch of size {len(batch_data)}")
    try:
        truncated_batch = []
        for (label, seq) in batch_data:
            if len(seq) > MAX_SEQ_LEN:
                logger.warning(f"Sequence length {len(seq)} exceeds {MAX_SEQ_LEN}, truncating.")
                seq = seq[:MAX_SEQ_LEN]
            truncated_batch.append((label, seq))

        _, _, batch_tokens = batch_converter(truncated_batch)
        with torch.no_grad():
            results = model(batch_tokens, repr_layers=[30], return_contacts=False)
        token_reps = results["representations"][30]

        for i, (label, seq) in enumerate(truncated_batch):
            embedding = token_reps[i, 1:len(seq) + 1].mean(0).tolist()
            yield json.dumps({
                "sequence": seq,
                "embedding": embedding
            })

    except Exception as e:
        logger.error(f"❌ Batch processing error: {e}")
        logger.error(traceback.format_exc())
        for _, seq in batch_data:
            yield json.dumps({"sequence": seq, "error": str(e)})

# ---------------------- #
# Partition-level Inference
# ---------------------- #
def inference_map_partition(records):
    try:
        pid = os.getpid()
        logger.info(f"[Worker PID {pid}] ⚙️ Partition started. Loading model...")
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
            buffer.append((f"seq_{count}", seq))

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
        spark = SparkSession.builder.appName("ESM2-Pipeline").getOrCreate()

        input_path = "hdfs:///user/almalinux/datasets/uniref50.fasta"
        output_path = "hdfs:///user/almalinux/results/esm2_embeddings_json"

        logger.info("📥 Reading FASTA file from HDFS...")
        df = spark.read.text(input_path)

        # Use coalesce to evenly distribute across nodes based on executors
        num_partitions = spark.sparkContext.defaultParallelism
        logger.info(f"🧩 Repartitioning FASTA input into {num_partitions} partitions...")
        df = df.repartition(num_partitions)

        logger.info("🧠 Running distributed ESM inference across partitions...")
        rdd = df.rdd.mapPartitions(inference_map_partition)

        logger.info("💾 Saving embeddings to HDFS immediately...")
        rdd.saveAsTextFile(output_path)

        logger.info("🏁 ✅ Job completed successfully.")
        spark.stop()

    except Exception as e:
        logger.error(f"🔥 Fatal error in Spark job: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
