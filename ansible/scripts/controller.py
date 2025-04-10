#!/usr/bin/env python3

import os
import glob
import time
from datetime import datetime, timedelta
from celery import Celery

CHUNK_DIR = "/mnt/data_volume/datasets/uni_chunks"
LOG_PATH = "/mnt/data_volume/results/esm2_celery_outputs/submit_log.txt"
MAX_PENDING = 4  # Max allowed tasks per worker before skipping it

app = Celery(broker="redis://mgmtnode:6379/0")

def get_worker_load():
    try:
        i = app.control.inspect()
        active = i.active() or {}
        stats = i.stats() or {}
        load = {}
        for worker, tasks in active.items():
            concurrency = stats.get(worker, {}).get("pool", {}).get("max-concurrency", 4)
            load[worker] = {
                "active": len(tasks),
                "free_slots": concurrency - len(tasks)
            }
        return load
    except Exception as e:
        print(f"⚠️ Failed to fetch worker stats: {e}")
        return {}

def pick_available_worker(worker_load):
    available = [w for w, l in worker_load.items() if l["active"] < MAX_PENDING]
    return available[0] if available else None

# ✅ Ensure log directory exists
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

end_time = datetime.now() + timedelta(hours=24)
iteration = 0

print("📅 Starting 24-hour job loop...")

with open(LOG_PATH, "a") as log_file:
    while datetime.now() < end_time:
        iteration += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n⏱️ Iteration #{iteration} — {timestamp}")
        log_file.write(f"\n--- Iteration #{iteration} at {timestamp} ---\n")

        files = sorted(
            glob.glob(os.path.join(CHUNK_DIR, "*.fasta")) +
            glob.glob(os.path.join(CHUNK_DIR, "*.fasta.gz"))
        )

        if not files:
            print("⚠️ No FASTA or GZ files found!")
            log_file.write("⚠️ No FASTA or GZ files found!\n")
            time.sleep(60)
            continue

        worker_load = get_worker_load()

        for path in files:
            chosen = pick_available_worker(worker_load)
            if not chosen:
                print("⏳ All workers busy, waiting 30s...")
                log_file.write("⏳ All workers busy, waiting 30s...\n")
                log_file.flush()
                time.sleep(30)
                break

            print(f"🚀 Submitting {path} to {chosen}")
            log_file.write(f"🚀 Submitting {path} to {chosen}\n")
            app.send_task("celery_worker.infer_fasta_file", args=[path])

        log_file.flush()
        time.sleep(10)

print("\n🎉 Completed 24-hour run.")
