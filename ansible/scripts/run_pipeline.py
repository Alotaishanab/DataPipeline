#!/usr/bin/env python

import os
import json
import logging
import torch
import esm
import traceback
from io import StringIO
from Bio import SeqIO
from pyspark.sql import SparkSession

os.environ["TORCH_HOME"] = "/tmp/torch_cache"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True
)
logger = logging.getLogger(__name__)

MAX_SEQ_LEN = 3000
BATCH_SIZE = 4

def run_batch(batch_data, model, batch_converter):
    logger.info(f"✨ Running inference on batch of size {len(batch_data)}")
    try:
        truncated_batch = []
        for (label, seq) in batch_data:
            if len(seq) > MAX_SEQ_LEN:
                logger.warning(f"Sequence too long ({len(seq)}), truncating to {MAX_SEQ_LEN}.")
                seq = seq[:MAX_SEQ_LEN]
            truncated_batch.append((label, seq))

        _, _, batch_tokens = batch_converter(truncated_batch)
        with torch.no_grad():
            results = model(batch_tokens, repr_layers=[30], return_contacts=False)
        token_reps = results["representations"][30]

        for i, (label, seq) in enumerate(truncated_batch):
            embedding = token_reps[i, 1:len(seq)+1].mean(0).tolist()
            yield json.dumps({"sequence": seq, "embedding": embedding})

    except Exception as e:
        logger.error(f"❌ Batch error: {e}")
        logger.error(traceback.format_exc())
        for _, seq in batch_data:
            yield json.dumps({"sequence": seq, "error": str(e)})

def inference_map_partition(records):
    try:
        pid = os.getpid()
        logger.info(f"[PID {pid}] 🌐 Partition starting...")
        model, alphabet = esm.pretrained.esm2_t30_150M_UR50D()
        model.eval()
        batch_converter = alphabet.get_batch_converter()

        buffer = []
        count = 0

        for filename, content in records:
            logger.info(f"📁 Processing file: {filename}")
            fasta_io = StringIO(content)
            for record in SeqIO.parse(fasta_io, "fasta"):
                seq = str(record.seq)
                buffer.append((record.id, seq))
                count += 1

                if len(buffer) == BATCH_SIZE:
                    yield from run_batch(buffer, model, batch_converter)
                    buffer = []

        if buffer:
            yield from run_batch(buffer, model, batch_converter)

        logger.info(f"✅ Done partition, total {count} sequences.")
    except Exception as e:
        logger.error(f"❌ Partition error: {e}")
        logger.error(traceback.format_exc())
        yield json.dumps({"error": str(e)})

def main():
    logger.info("🔥 Starting ESM2 Inference Job")
    try:
        spark = SparkSession.builder.appName("ESM2-Pipeline").getOrCreate()

        input_path = "hdfs:///user/almalinux/datasets/fasta_parts/"
        timestamp = spark.sparkContext._jvm.java.time.LocalDateTime.now().toString().replace(":", "_")
        output_path = f"hdfs:///user/almalinux/results/esm2_embeddings_json_{timestamp}"

        rdd = spark.sparkContext.wholeTextFiles(input_path, minPartitions=64)
        rdd = rdd.mapPartitions(inference_map_partition)
        rdd.saveAsTextFile(output_path)

        logger.info(f"🏁 ✅ Pipeline finished. Output: {output_path}")
        spark.stop()

    except Exception as e:
        logger.error(f"🔥 Fatal error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
