import os
import json
from celery.result import AsyncResult
from celery_worker import infer_fasta_content
from pyarrow import hdfs

# Configuration
HDFS_HOST = "mgmtnode"
HDFS_PORT = 9000
CHUNKS_DIR = "/user/almalinux/datasets/chunks"
OUTPUT_DIR = "/user/almalinux/results/esm2_celery_outputs"

# Connect to HDFS
hdfs_client = hdfs.connect(HDFS_HOST, port=HDFS_PORT)

# Ensure output directory exists
if not hdfs_client.exists(OUTPUT_DIR):
    hdfs_client.mkdir(OUTPUT_DIR)

# List chunk files
chunk_files = sorted([f for f in hdfs_client.ls(CHUNKS_DIR) if f.endswith(".fasta")])

# Submit tasks
print(f"🚀 Submitting {len(chunk_files)} chunks to Celery workers...")
submitted = {}

for chunk_path in chunk_files:
    with hdfs_client.open(chunk_path, 'rb') as f:
        content = f.read().decode()
        task = infer_fasta_content.delay(content)
        submitted[chunk_path] = task.id

# Wait for completion
print("⏳ Waiting for results...")
for chunk_path, task_id in submitted.items():
    result = AsyncResult(task_id)
    result.wait()  # let it take as long as it needs

    output_filename = os.path.basename(chunk_path).replace(".fasta", ".json")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    if result.successful():
        data = result.get()
        with hdfs_client.open(output_path, 'wb') as f_out:
            f_out.write(data.encode())
        print(f"✅ {chunk_path} processed → {output_path}")
    else:
        print(f"❌ Failed to process {chunk_path} (task_id={task_id})")
