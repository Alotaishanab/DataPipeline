#!/usr/bin/env python3

import os
import glob
import json
import time
import subprocess
from celery.result import AsyncResult
from celery_worker import infer_fasta_content

CHUNK_DIR = "/mnt/data_volume/datasets/uni_chunks"
OUTPUT_DIR = "/mnt/data_volume/results/esm2_celery_outputs"

# Get latest chunk
fasta_files = sorted(
    glob.glob(os.path.join(CHUNK_DIR, "*.fasta.gz")),
    key=os.path.getmtime,
    reverse=True
)

if not fasta_files:
    raise RuntimeError(f"❌ No FASTA files found in {CHUNK_DIR}")

chunk_path = fasta_files[0]
decompressed_path = chunk_path[:-3]  # remove .gz

print(f"📦 Found chunk: {chunk_path}")

# Decompress only if .fasta does not exist
if not os.path.exists(decompressed_path):
    print(f"🔓 Decompressing {chunk_path}...")
    result = subprocess.run(["pigz", "-d", "-f", chunk_path])
    if result.returncode != 0:
        raise RuntimeError(f"❌ Failed to decompress {chunk_path}")
else:
    print(f"🟢 Already decompressed: {decompressed_path}")

# Read content
if not os.path.exists(decompressed_path):
    raise FileNotFoundError(f"❌ Expected decompressed file missing: {decompressed_path}")

with open(decompressed_path, 'r') as f:
    content = f.read()

# Submit to Celery
task = infer_fasta_content.delay(content)
print(f"🚀 Submitted {os.path.basename(decompressed_path)} (task_id={task.id})")

# Wait for result
result = AsyncResult(task.id)
output = result.get(timeout=600)  # 10 min timeout

# Save result
if result.successful():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_filename = os.path.basename(decompressed_path).replace(".fasta", ".json")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    with open(output_path, 'w') as f_out:
        f_out.write(output)

    print(f"✅ Done! Output → {output_path}")
else:
    print(f"❌ Task {task.id} failed")
