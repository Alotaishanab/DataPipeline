#!/usr/bin/env python3
import os
import glob
import json
import time
import subprocess
from celery.result import AsyncResult
from celery_worker import infer_fasta_content

# Updated GlusterFS paths
CHUNK_DIR = "/mnt/data_volume/datasets/uni_chunks"
OUTPUT_DIR = "/mnt/data_volume/results/esm2_celery_outputs"

# Optional: Automatically find the latest .fasta.gz chunk
fasta_files = sorted(glob.glob(os.path.join(CHUNK_DIR, "*.fasta.gz")), key=os.path.getmtime, reverse=True)
if not fasta_files:
    raise RuntimeError(f"❌ No FASTA files found in {CHUNK_DIR}")

chunk_path = fasta_files[0]
print(f"📦 Found chunk: {chunk_path}")

# Decompress .fasta.gz in-place
subprocess.run(["pigz", "-d", "-f", chunk_path])
decompressed_path = chunk_path[:-3]  # remove .gz

# Read content
with open(decompressed_path, 'r') as f:
    content = f.read()

# Submit to Celery
task = infer_fasta_content.delay(content)
print(f"🚀 Submitted {os.path.basename(decompressed_path)} (task_id={task.id})")

# Wait for result
result = AsyncResult(task.id)
result.wait()

# Save result to GlusterFS results dir
if result.successful():
    data = result.get()
    output_filename = os.path.basename(decompressed_path).replace(".fasta", ".json")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, 'w') as f_out:
        f_out.write(data)

    print(f"✅ Done! Output → {output_path}")
else:
    print(f"❌ Task {task.id} failed for {decompressed_path}")
