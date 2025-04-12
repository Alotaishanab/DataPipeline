#!/usr/bin/env python3

import os
import glob
import time
from datetime import datetime, timedelta
from kombu.exceptions import OperationalError
from celery_app.app import app  # ✅ Note the change here

CHUNK_DIRS = {
    "internal": "/mnt/data_volume/datasets/internal_chunks",
    "user": "/mnt/data_volume/datasets/user_chunks"
}
OUTPUT_DIRS = {
    "internal": "/mnt/data_volume/results/internal_outputs",
    "user": "/mnt/data_volume/results/user_outputs"
}
LOG_PATH = "/mnt/data_volume/results/controller_submit_log.txt"
MAX_PENDING = 4
WAIT_FOR_IDLE_DELAY = 30  # seconds


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

def all_workers_idle(worker_load):
    return all(w["active"] == 0 for w in worker_load.values())

# 🔄 Purge existing Celery tasks before starting
try:
    print("🧹 Purging any leftover Celery tasks from Redis...")
    purged = app.control.purge()
    print(f"✅ Purged {purged} task(s) from the queue.")
except OperationalError as e:
    print(f"❌ Failed to purge tasks: {e}")

# Ensure log dir
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

        for kind, chunk_dir in CHUNK_DIRS.items():
            output_dir = OUTPUT_DIRS[kind]
            os.makedirs(output_dir, exist_ok=True)

            all_files = sorted(
                glob.glob(os.path.join(chunk_dir, "*.fasta")) +
                glob.glob(os.path.join(chunk_dir, "*.fasta.gz"))
            )
            files_to_process = []

            for path in all_files:
                base = os.path.basename(path).replace(".fasta", ".json").replace(".gz", "")
                output_path = os.path.join(output_dir, base)
                if not os.path.exists(output_path):
                    files_to_process.append(path)
                else:
                    print(f"✅ Already processed: {output_path}")
                    log_file.write(f"✅ Already processed: {output_path}\n")

            for path in files_to_process:
                while True:
                    worker_load = get_worker_load()
                    chosen = next((w for w, l in worker_load.items() if l["active"] < MAX_PENDING), None)

                    if not chosen:
                        print("⏳ All workers busy, waiting 30s...")
                        log_file.write("⏳ All workers busy, waiting 30s...\n")
                        log_file.flush()
                        time.sleep(WAIT_FOR_IDLE_DELAY)
                    else:
                        print(f"🚀 Submitting {path} to {chosen}")
                        log_file.write(f"🚀 Submitting {path} to {chosen}\n")
                        app.send_task("celery_worker.infer_fasta_file", args=[path])
                        break

            print("⌛ Waiting for all workers to finish current batch...")
            log_file.write("⌛ Waiting for all workers to finish current batch...\n")
            log_file.flush()
            while True:
                if all_workers_idle(get_worker_load()):
                    print("✅ All workers are idle. Proceeding to next iteration.")
                    log_file.write("✅ All workers are idle. Proceeding to next iteration.\n")
                    log_file.flush()
                    break
                time.sleep(WAIT_FOR_IDLE_DELAY)

print("\n🎉 Completed 24-hour run.")
