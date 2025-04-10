#!/usr/bin/env python3

import os
import glob
import time
import subprocess
from celery.result import AsyncResult
from celery_worker import infer_fasta_file

CHUNK_DIR = "/mnt/data_volume/datasets/uni_chunks"
OUTPUT_DIR = "/mnt/data_volume/results/esm2_celery_outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get all .fasta.gz chunks
chunk_files = sorted(glob.glob(os.path.join(CHUNK_DIR, "*.fasta.gz")))
tasks = []

for gz_path in chunk_files:
    fasta_path = gz_path[:-3]

    if not os.path.exists(fasta_path):
        print(f"🔓 Decompressing {gz_path}...")
        result = subprocess.run(["pigz", "-d", "-f", gz_path])
        if result.returncode != 0:
            print(f"❌ Failed to decompress {gz_path}")
            continue
    else:
        print(f"🟢 Already decompressed: {fasta_path}")

    print(f"🚀 Sending task for {fasta_path}")
    task = infer_fasta_file.delay(fasta_path)
    tasks.append((fasta_path, task))

# Optionally wait for results
for fasta_path, task in tasks:
    result = AsyncResult(task.id)
    try:
        output = result.get(timeout=600)
        if result.successful():
            output_filename = os.path.basename(fasta_path).replace(".fasta", ".json")
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            with open(output_path, 'w') as f_out:
                f_out.write(output)
            print(f"✅ Done → {output_path}")
        else:
            print(f"❌ Task failed: {fasta_path}")
    except Exception as e:
        print(f"❌ Timeout or error for {fasta_path}: {e}")
