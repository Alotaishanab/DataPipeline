#!/usr/bin/env python3

import os
import glob
import time
import random
from datetime import datetime, timedelta
from kombu.exceptions import OperationalError
from celery_app.app import app

CHUNK_DIRS = {
    "internal": "/mnt/data_volume/datasets/internal_chunks",
    "user": "/mnt/data_volume/datasets/user_chunks"
}
LOG_PATH = "/mnt/data_volume/results/controller_submit_log.txt"
MAX_PENDING = 1  # Only one file per worker
WAIT_FOR_IDLE_DELAY = 30  # seconds
GZ_SUBMIT_DELAY = 20      # seconds to wait after submitting a .gz

def get_worker_load():
    try:
        i = app.control.inspect()
        active = i.active()
        stats = i.stats()
        if not active or not stats:
            print("⚠️ Celery returned no active task info or no stats.")
            return None
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
        return None

def all_workers_idle(worker_load):
    return all(w["active"] == 0 for w in worker_load.values())

# 🔄 Purge leftover tasks at startup
try:
    print("🧹 Purging leftover tasks...")
    purged = app.control.purge()
    print(f"✅ Purged {purged} task(s)")
except OperationalError as e:
    print(f"❌ Failed to purge tasks: {e}")

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

end_time = datetime.now() + timedelta(hours=24)
iteration = 0

print("📅 Starting stress test loop...")

with open(LOG_PATH, "a") as log_file:
    while datetime.now() < end_time:
        iteration += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n⏱️ Iteration #{iteration} — {timestamp}")
        log_file.write(f"\n--- Iteration #{iteration} at {timestamp} ---\n")

        for kind, chunk_dir in CHUNK_DIRS.items():
            # Get all .fasta and .fasta.gz files
            fasta_files = sorted(
                glob.glob(os.path.join(chunk_dir, "*.fasta")) +
                glob.glob(os.path.join(chunk_dir, "*.fasta.gz"))
            )

            for path in fasta_files:
                while True:
                    worker_load = get_worker_load()
                    if worker_load:
                        workers = list(worker_load.items())
                        random.shuffle(workers)
                        chosen = next((w for w, l in workers if l["active"] < MAX_PENDING), None)
                    else:
                        chosen = None

                    if not chosen:
                        print("⏳ All workers busy or unreachable. Waiting...")
                        log_file.write("⏳ All workers busy or unreachable. Waiting...\n")
                        log_file.flush()
                        time.sleep(WAIT_FOR_IDLE_DELAY)
                    else:
                        print(f"🚀 Submitting {path} to {chosen}")
                        log_file.write(f"🚀 Submitting {path} to {chosen}\n")
                        app.send_task("celery_worker.infer_fasta_file", args=[path])
                        log_file.flush()

                        if path.endswith(".gz"):
                            print("🕓 Delaying for gzip decompression...")
                            log_file.write("🕓 Delaying for gzip decompression...\n")
                            log_file.flush()
                            time.sleep(GZ_SUBMIT_DELAY)
                        break

        # Wait until all workers are idle
        print("⌛ Waiting for all workers to finish current batch...")
        log_file.write("⌛ Waiting for all workers to finish current batch...\n")
        log_file.flush()
        while True:
            worker_load = get_worker_load()
            if worker_load and all_workers_idle(worker_load):
                print("✅ All workers are idle. Proceeding to next iteration.")
                log_file.write("✅ All workers are idle. Proceeding to next iteration.\n")
                log_file.flush()
                break
            time.sleep(WAIT_FOR_IDLE_DELAY)

print("\n🎉 Completed full 24-hour stress loop.")
