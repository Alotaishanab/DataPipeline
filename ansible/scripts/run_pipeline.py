#!/usr/bin/env python
"""
run_pipeline.py

A Spark job that uses ESM-2 (esm2_t33_650M_UR50D) to process a FASTA file in HDFS,
computes per-sequence mean embeddings, and writes results as JSON to HDFS.
"""

import json
import torch
import esm
from pyspark.sql import SparkSession

# Function that runs inference per Spark partition
def inference_map_partition(records):
    # Load ESM-2 model once per partition
    model, alphabet = esm.pretrained.esm2_t33_650M_UR50D()
    model.eval()

    batch_converter = alphabet.get_batch_converter()

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

                # Compute mean embedding for actual sequence tokens
                seq_embedding = token_repr[0, 1:len(seq)+1].mean(0).tolist()

            yield json.dumps({
                "sequence": seq,
                "embedding": seq_embedding
            })

        except Exception as e:
            yield json.dumps({
                "sequence": seq,
                "error": str(e)
            })

def main():
    spark = SparkSession.builder.appName("ESM2-Pipeline").getOrCreate()

    input_path = "hdfs:///user/almalinux/datasets/uniref50.fasta.gz"
    output_path = "hdfs:///user/almalinux/results/esm2_embeddings_json"

    # === DELETE OUTPUT DIR IF EXISTS ===
    hadoop_conf = spark._jsc.hadoopConfiguration()
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(hadoop_conf)
    path = spark._jvm.org.apache.hadoop.fs.Path(output_path)

    if fs.exists(path):
        fs.delete(path, True)  # True = recursive

    # Run pipeline
    df = spark.read.text(input_path)
    rdd = df.rdd.mapPartitions(inference_map_partition)

    rdd.saveAsTextFile(output_path)

    spark.stop()

if __name__ == "__main__":
    main()
