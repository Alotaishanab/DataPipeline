#!/usr/bin/env python3

import os
import glob
import time
from datetime import datetime, timedelta
from celery_worker import infer_fasta_file
from celery.result import AsyncResult

CHUNK_DIR = "/mnt/data_volume/datasets/uni_chunks"
OUTPUT_DIR = "/mnt/data_volume/results/esm2_celery_outputs"

end_time = datetime.now() + timedelta(hours=24)

print("📅 Starting 24-hour job loop...")
iteration = 0

while datetime.now() < end_time:
    iteration += 1
    print(f"\n⏱️ Iteration #{iteration} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    fasta_files = sorted(glob.glob(os.path.join(CHUNK_DIR, "*.fasta.gz")))
    if not fasta_files:
        raise RuntimeError("❌ No FASTA .gz files found!")

    tasks = []
    for gz_path in fasta_files:
        print(f"🚀 Submitting {gz_path}...")
        task = infer_fasta_file.delay(gz_path)
        tasks.append((gz_path, task))

    for gz_path, task in tasks:
        print(f"📡 Waiting for task {task.id} ({os.path.basename(gz_path)})...")
        result = AsyncResult(task.id)
        try:
            output = result.get(timeout=3600)
            if result.successful():
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                out_file = os.path.basename(gz_path).replace(".fasta.gz", f".{iteration}.json")
                with open(os.path.join(OUTPUT_DIR, out_file), 'w') as f:
                    f.write(output)
                print(f"✅ Done: {out_file}")
            else:
                print(f"❌ Failed: {task.id}")
        except Exception as e:
            print(f"⚠️ Timeout or error: {e}")
    
    # Optional sleep between rounds
    time.sleep(5)

print("\n🎉 Completed 24-hour run.")
