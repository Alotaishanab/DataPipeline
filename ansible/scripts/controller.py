# Updated controller.py to work with NFS

import os
import glob
import json
import time
from celery.result import AsyncResult
from celery_worker import infer_fasta_content

# Updated paths to use NFS
CHUNK_DIR = "/mnt/datasets/uni_chunks"
OUTPUT_DIR = "/mnt/results/esm2_celery_outputs"

# Discover .fasta.gz file in CHUNK_DIR
fasta_files = glob.glob(os.path.join(CHUNK_DIR, "*.fasta.gz"))
if len(fasta_files) != 1:
    raise RuntimeError(f"❌ Expected 1 FASTA file in {CHUNK_DIR}, found: {len(fasta_files)}")

chunk_path = fasta_files[0]
print(f"📦 Found chunk: {chunk_path}")

# Decompress (in-place)
import subprocess
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

# Save result to NFS result directory
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
