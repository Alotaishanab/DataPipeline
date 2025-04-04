import os
import glob
import json
import time
from celery_worker import infer_fasta_content
from pyarrow import hdfs
from celery.result import AsyncResult

# Settings
CHUNK_DIR = "/mnt/data/chunks"
OUTPUT_DIR = "/user/almalinux/results/esm2_celery_outputs"
HDFS_HOST = "mgmtnode"
HDFS_PORT = 9000

# Connect to HDFS
hdfs_client = hdfs.connect(HDFS_HOST, port=HDFS_PORT)

# Discover .fasta file in CHUNK_DIR
fasta_files = glob.glob(os.path.join(CHUNK_DIR, "*.fasta"))
if len(fasta_files) != 1:
    raise RuntimeError(f"❌ Expected 1 FASTA file in {CHUNK_DIR}, found: {len(fasta_files)}")

chunk_path = fasta_files[0]
print(f"📦 Found chunk: {chunk_path}")

# Read content
with open(chunk_path, 'r') as f:
    content = f.read()

# Submit to Celery
task = infer_fasta_content.delay(content)
print(f"🚀 Submitted {os.path.basename(chunk_path)} (task_id={task.id})")

# Wait for result
result = AsyncResult(task.id)
result.wait()

# Save result to HDFS
if result.successful():
    data = result.get()
    output_filename = os.path.basename(chunk_path).replace(".fasta", ".json")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    with hdfs_client.open(output_path, 'wb') as f_out:
        f_out.write(data.encode())

    print(f"✅ Done! Output → {output_path}")
else:
    print(f"❌ Task {task.id} failed for {chunk_path}")
