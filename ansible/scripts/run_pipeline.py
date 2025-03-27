#!/usr/bin/env python
import json
import torch
import esm
from pyspark.sql import SparkSession

# Combine multi-line FASTA sequences
def fasta_parser(lines):
    header = None
    seq_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith(">"):
            if header and seq_lines:
                yield (header, "".join(seq_lines))
            header = line
            seq_lines = []
        else:
            seq_lines.append(line)

    # Emit last record
    if header and seq_lines:
        yield (header, "".join(seq_lines))

# Per-partition processing
def inference_map_partition(records):
    model, alphabet = esm.pretrained.esm2_t33_650M_UR50D()
    model.eval()
    batch_converter = alphabet.get_batch_converter()

    # Recombine FASTA from plain text lines
    parsed = fasta_parser(records)

    for header, seq in parsed:
        try:
            data = [(header, seq)]
            _, _, batch_tokens = batch_converter(data)
            with torch.no_grad():
                results = model(batch_tokens, repr_layers=[33])
                token_repr = results["representations"][33]
                embedding = token_repr[0, 1:len(seq)+1].mean(0).tolist()

            yield json.dumps({
                "header": header,
                "sequence": seq,
                "embedding": embedding
            })

        except Exception as e:
            yield json.dumps({
                "header": header,
                "error": str(e)
            })

def main():
    spark = SparkSession.builder.appName("ESM2-Pipeline").getOrCreate()

    input_path = "hdfs:///user/almalinux/datasets/uniref50.fasta.gz"
    output_path = "hdfs:///user/almalinux/results/esm2_embeddings_json"

    # Delete output directory if exists
    hadoop_conf = spark._jsc.hadoopConfiguration()
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(hadoop_conf)
    path = spark._jvm.org.apache.hadoop.fs.Path(output_path)

    if fs.exists(path):
        fs.delete(path, True)

    df = spark.read.text(input_path)
    rdd = df.rdd.mapPartitions(inference_map_partition)
    rdd.saveAsTextFile(output_path)

    spark.stop()

if __name__ == "__main__":
    main()
