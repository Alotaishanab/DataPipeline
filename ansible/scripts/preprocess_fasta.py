#!/usr/bin/env python

import json
import logging
from pyspark.sql import SparkSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fasta_to_jsonl(rdd):
    buffer = []
    current_sequence = ""

    def flush(seq):
        if seq:
            return json.dumps({"sequence": seq})
        return None

    for line in rdd.collect():
        line = line.strip()
        if line.startswith(">"):
            if current_sequence:
                buffer.append(flush(current_sequence))
                current_sequence = ""
        else:
            current_sequence += line

    if current_sequence:
        buffer.append(flush(current_sequence))

    return [x for x in buffer if x]

def main():
    spark = SparkSession.builder.appName("Preprocess-FASTA").getOrCreate()
    sc = spark.sparkContext

    input_path = "hdfs:///user/almalinux/datasets/uniref50.fasta"
    output_path = "hdfs:///user/almalinux/datasets/uniref50.jsonl"

    logger.info("Reading FASTA from HDFS...")
    rdd = sc.textFile(input_path)

    logger.info("Converting FASTA to JSONL...")
    result = fasta_to_jsonl(rdd)

    logger.info("Writing to HDFS as JSON lines...")
    sc.parallelize(result).saveAsTextFile(output_path)

    spark.stop()
    logger.info("✅ Preprocessing completed")

if __name__ == "__main__":
    main()
