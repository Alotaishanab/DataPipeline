import os
import tarfile
import json
import time
import tempfile
from celery.result import AsyncResult
from celery_worker import infer_fasta_content
from pyarrow import hdfs

# Configuration
HDFS_HOST = "mgmtnode"
HDFS_PORT = 9000
CHUNKS_DIR = "/user/almalinux/datasets/chunks_compressed"
OUTPUT_DIR = "/user/almalinux/results/esm2_celery_outputs"
MAX_ACTIVE_TASKS = 10  # Limit concurrent tasks
SUBMIT_PAUSE_SECONDS = 2  # Pause between task submissions

# Connect to HDFS
hdfs_client = hdfs.connect(HDFS_HOST, port=HDFS_PORT)

# Ensure output directory exists
if not hdfs_client.exists(OUTPUT_DIR):
    hdfs_client.mkdir(OUTPUT_DIR)

# List archive chunk files
chunk_archives = sorted([f for f in hdfs_client.ls(CHUNKS_DIR) if f.endswith(".tar.gz")])

# Submit tasks with batching and throttling
print(f"\U0001F680 Submitting {len(chunk_archives)} archive chunks to Celery workers...")
submitted = {}

for archive_path in chunk_archives:
    print(f"\n📦 Processing archive: {os.path.basename(archive_path)}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_tar_path = os.path.join(tmp_dir, os.path.basename(archive_path))

        # Download archive from HDFS
        with hdfs_client.open(archive_path, 'rb') as hdfs_file, open(local_tar_path, 'wb') as local_file:
            local_file.write(hdfs_file.read())

        # Extract files
        with tarfile.open(local_tar_path, 'r:gz') as tar:
            tar.extractall(tmp_dir)

        # Submit each FASTA chunk
        for file in sorted(os.listdir(tmp_dir)):
            if file.endswith(".fasta"):
                file_path = os.path.join(tmp_dir, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                    task = infer_fasta_content.delay(content)
                    submitted[file] = task.id
                    print(f"🚀 Submitted {file} (task_id={task.id})")
                    time.sleep(SUBMIT_PAUSE_SECONDS)

                # Wait if too many active tasks
                while sum(1 for t in submitted.values() if not AsyncResult(t).ready()) >= MAX_ACTIVE_TASKS:
                    print("⏳ Throttling: waiting for active tasks to finish...")
                    time.sleep(10)

# Wait for all results
print("\n⏳ Waiting for results from all workers...")
for file, task_id in submitted.items():
    result = AsyncResult(task_id)
    result.wait()  # No timeout

    output_filename = file.replace(".fasta", ".json")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    if result.successful():
        data = result.get()
        with hdfs_client.open(output_path, 'wb') as f_out:
            f_out.write(data.encode())
        print(f"✅ {file} processed → {output_path}")
    else:
        print(f"❌ Failed to process {file} (task_id={task_id})")
