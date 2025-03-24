#!/usr/bin/env python
"""
run_pipeline.py

A Spark job that uses ESM (esm1b_t33_650M_UR50S) to process a FASTA file in HDFS.
"""

import sys
import torch
import esm
from pyspark.sql import SparkSession

# We'll define a function that loads the ESM model once per partition,
# processes all sequences in that partition, and yields results.
def inference_map_partition(records):
    # Load the ESM model & alphabet just once
    model, alphabet = esm.pretrained.esm1b_t33_650M_UR50S()
    model.eval()  # turn off dropout, etc.
    
    batch_converter = alphabet.get_batch_converter()

    # We'll accumulate sequences to batch them, but for simplicity let's
    # just do them 1 by 1 in this example:
    for row in records:
        seq = row.value.strip()  # row is a Row object with 'value'
        # If it's a FASTA header or empty, skip
        if not seq or seq.startswith(">"):
            continue

        # Build a batch with a single sequence
        data = [("seq1", seq)]
        batch_labels, batch_strs, batch_tokens = batch_converter(data)

        # Torch inference
        with torch.no_grad():
            results = model(batch_tokens, repr_layers=[33])  # final layer = 33
            # We won't do real embedding logic here; just confirm it runs
            # The shape: [batch_size, seq_length, embed_dim]
            # For a single sequence: [1, len, 1280]
            token_repr = results["representations"][33]
            length = token_repr.shape[1]
        
        # This is just a placeholder to show we did something
        yield f"SeqLen={length} ; snippet={seq[:30]}"

def main():
    spark = SparkSession.builder.appName("ESM-Pipeline").getOrCreate()

    # 1) Input from HDFS
    input_path = "hdfs:///user/almalinux/datasets/uniref50.fasta.gz"
    df = spark.read.text(input_path)

    # 2) Map partitions to load the model only once per partition
    rdd = df.rdd.mapPartitions(inference_map_partition)

    # 3) Save results to HDFS
    output_path = "hdfs:///user/almalinux/results/esm_inferences"
    rdd.saveAsTextFile(output_path)

    spark.stop()

if __name__ == "__main__":
    main()
