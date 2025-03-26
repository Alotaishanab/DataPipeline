#!/usr/bin/env python
"""
run_pipeline.py

A Spark job that uses ESM-2 (esm2_t33_650M_UR50D) to process a FASTA file in HDFS,
computes per-sequence mean embeddings, and writes results as JSON to HDFS.
"""

import json
import torch
import esm
import logging
import os
from pyspark.sql import SparkSession

# === Setup logging (visible in yarn logs) ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Function that runs inference per Spark partition
def inference_map_partition(records):
    logger.info(f"Starting inference on partition (PID={os.getpid()})")

    try:
        model, alphabet = esm.pretrained.esm2_t33_650M_UR50D()
        model.eval()
        batch_converter = alphabet.get_batch_converter()
        logger.info("Successfully loaded ESM model on executor.")
    except Exception as e:
        logger.error(f"Failed to load ESM model: {e}")
        return  # Return nothing — kill the partition silently

    for row in records:
        seq = row.value.strip()
        if not seq or seq.startswith(">"):
            continue

        try:
            data = [("sequence", seq)]
            _, _, batch_tokens = batch_converter(data)

            with torch.no_grad():
                results = model(batch_tokens, repr_layers=[33])
                token_repr = results["representations"][33]
                seq_embedding = token_repr[0, 1:len(seq)+1].mean(0).tolist()

            yield json.dumps({
                "sequence": seq,
                "embedding": seq_embedding
            })

        except Exception as e:
            logger.warning(f"Error processing sequence: {seq[:30]}... - {e}")
            yield json.dumps({
                "sequence": seq,
                "error": str(e)
            })

def main():
    spark = SparkSession.builder.appName("ESM2-Pipeline").getOrCreate()
    logger.info("Spark session started.")

    input_path = "hdfs:///user/almalinux/datasets/uniref50.fasta.gz"
    output_path = "hdfs:///user/almalinux/results/esm2_embeddings_json"

    # === DELETE OUTPUT DIR IF EXISTS ===
    hadoop_conf = spark._jsc.hadoopConfiguration()
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(hadoop_conf)
    path = spark._jvm.org.apache.hadoop.fs.Path(output_path)

    if fs.exists(path):
        logger.info(f"Output path {output_path} exists. Deleting it.")
        fs.delete(path, True)

    logger.info(f"Reading FASTA input from: {input_path}")
    df = spark.read.text(input_path)

    logger.info("Starting distributed inference.")
    rdd = df.rdd.mapPartitions(inference_map_partition)

    logger.info(f"Saving output to: {output_path}")
    rdd.saveAsTextFile(output_path)

    logger.info("Pipeline completed successfully.")
    spark.stop()

if __name__ == "__main__":
    main()
