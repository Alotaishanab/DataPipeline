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
    force=True  # ensures config is applied even if logging is already configured
)
logger = logging.getLogger(__name__)

# ---------------------- #
# FASTA Parsing function
# ---------------------- #
def parse_fasta_partition(lines):
    logger.info("🔍 Parsing FASTA partition")
    sequence = []
    for line in lines:
        line = line.strip()
        if line.startswith(">"):
            if sequence:
                yield "".join(sequence)
                sequence = []
        elif line:
            sequence.append(line)
    if sequence:
        yield "".join(sequence)

# ---------------------- #
# Batch inference function
# ---------------------- #
def run_batch(batch_data, model, batch_converter):
    logger.info(f"🚀 Running inference on batch of size {len(batch_data)}")
    try:
        _, _, batch_tokens = batch_converter(batch_data)
        with torch.no_grad():
            results = model(batch_tokens, repr_layers=[33], return_contacts=False)
        token_representations = results["representations"][33]

        for i, (label, seq) in enumerate(batch_data):
            embedding = token_representations[i, 1:len(seq)+1].mean(0).tolist()
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
    try:
        pid = os.getpid()
        logger.info(f"[Worker PID {pid}] ⚙️ Loading model inside partition...")
        logger.info(f"[Worker PID {pid}] 🔧 TORCH_HOME: {os.environ.get('TORCH_HOME')}")

        model, alphabet = esm.pretrained.esm2_t33_650M_UR50D()
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
# Main Spark job
# ---------------------- #
def main():
    logger.info("🔥 Starting ESM2 Distributed Inference Job")
    try:
        spark = SparkSession.builder.appName("ESM2-Pipeline").getOrCreate()

        input_path = "hdfs:///user/almalinux/datasets/sample_uniref50.fasta"
        output_path = "hdfs:///user/almalinux/results/esm2_embeddings_json"

        # Delete output directory if it already exists
        hadoop_conf = spark._jsc.hadoopConfiguration()
        fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(hadoop_conf)
        path = spark._jvm.org.apache.hadoop.fs.Path(output_path)
        if fs.exists(path):
            logger.warning(f"⚠️ Output path {output_path} exists. Deleting it.")
            fs.delete(path, True)

        logger.info("📥 Reading FASTA file from HDFS...")
        df = spark.read.text(input_path)

        logger.info("🧠 Running distributed ESM inference across partitions...")
        rdd = df.rdd.mapPartitions(inference_map_partition)

        logger.info("💾 Saving embeddings to HDFS...")
        rdd.saveAsTextFile(output_path)

        logger.info("🏁 ✅ Job completed successfully.")
        spark.stop()

    except Exception as e:
        logger.error(f"🔥 Fatal error in Spark job: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
