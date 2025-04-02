import os
import json
import subprocess
from celery.result import AsyncResult
from celery_worker import infer_fasta_content
from pyarrow import hdfs

# Setup HDFS client
hdfs_client = hdfs.connect('mgmtnode', port=9000)

# Configuration
INPUT_DIR = "/user/almalinux/datasets/fasta_parts"
OUTPUT_DIR = "/user/almalinux/results/esm2_celery_outputs"

# Create output dir if it doesn't exist
if not hdfs_client.exists(OUTPUT_DIR):
    hdfs_client.mkdir(OUTPUT_DIR)

# List input files
fasta_files = hdfs_client.ls(INPUT_DIR)

# Submit jobs
submitted_jobs = {}
print("🚀 Submitting jobs to Celery workers...")
for fasta_path in fasta_files:
    with hdfs_client.open(fasta_path, 'rb') as f:
        fasta_content = f.read().decode()
        task = infer_fasta_content.delay(fasta_content)
        submitted_jobs[fasta_path] = task.id

# Wait for results
print("⏳ Waiting for tasks to complete...")
for fasta_path, task_id in submitted_jobs.items():
    result = AsyncResult(task_id)
    result.wait(timeout=600)  # wait max 10 minutes per task
    output_filename = os.path.basename(fasta_path).replace(".fasta", ".json")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    if result.successful():
        data = result.get()
        with hdfs_client.open(output_path, 'wb') as out_f:
            out_f.write(data.encode())
        print(f"✅ {fasta_path} processed -> {output_path}")
    else:
        print(f"❌ Failed to process {fasta_path} (task_id={task_id})")