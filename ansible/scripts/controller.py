import os
import json
from celery.result import AsyncResult
from celery_worker import infer_fasta_content
from pyarrow import hdfs
from io import StringIO

# Configuration
HDFS_HOST = "mgmtnode"
HDFS_PORT = 9000
INPUT_PATH = "/user/almalinux/datasets/uniref50.fasta"
OUTPUT_DIR = "/user/almalinux/results/esm2_celery_outputs"
CHUNK_SIZE = 1000  # number of FASTA records per chunk

# Connect to HDFS
hdfs_client = hdfs.connect(HDFS_HOST, port=HDFS_PORT)

# Ensure output directory exists
if not hdfs_client.exists(OUTPUT_DIR):
    hdfs_client.mkdir(OUTPUT_DIR)

# Read the FASTA file and split into chunks
print("📖 Reading FASTA file and splitting into chunks...")
chunks = []
current_chunk = []
record_count = 0
chunk_id = 0

with hdfs_client.open(INPUT_PATH, 'rb') as f:
    for line in f:
        line = line.decode()
        if line.startswith(">"):
            if len(current_chunk) >= CHUNK_SIZE * 2:  # Rough estimate (header + sequence line)
                chunks.append(("chunk_{}.fasta".format(chunk_id), "".join(current_chunk)))
                current_chunk = []
                chunk_id += 1
        current_chunk.append(line)
    if current_chunk:
        chunks.append(("chunk_{}.fasta".format(chunk_id), "".join(current_chunk)))

print(f"🚀 Dispatching {len(chunks)} chunks to Celery workers...")

# Submit chunks to Celery
submitted = {}
for filename, content in chunks:
    task = infer_fasta_content.delay(content)
    submitted[filename] = task.id

# Wait for results
print("⏳ Waiting for results from workers...")
for filename, task_id in submitted.items():
    result = AsyncResult(task_id)
    result.wait()  # no timeout!

    output_path = os.path.join(OUTPUT_DIR, filename.replace(".fasta", ".json"))

    if result.successful():
        data = result.get()
        with hdfs_client.open(output_path, 'wb') as f_out:
            f_out.write(data.encode())
        print(f"✅ {filename} completed -> {output_path}")
    else:
        print(f"❌ {filename} failed (task_id={task_id})")
