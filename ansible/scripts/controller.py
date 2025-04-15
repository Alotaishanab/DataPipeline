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

OUTPUT_DIRS = {
    "internal": "/mnt/data_volume/results/internal_outputs",
    "user": "/mnt/data_volume/results/user_outputs"
}

LOG_PATH = "/mnt/data_volume/results/controller_submit_log.txt"
MAX_PENDING = 1
WAIT_FOR_IDLE_DELAY = 30
GZ_SUBMIT_DELAY = 20

def get_worker_load():
    try:
        i = app.control.inspect()
        active = i.active()
        stats = i.stats()
        if not active or not stats:
            print("⚠️ Celery returned no active task info or no stats.")
            return None
        return {
            worker: {
                "active": len(tasks),
                "free_slots": stats.get(worker, {}).get("pool", {}).get("max-concurrency", 4) - len(tasks)
            } for worker, tasks in active.items()
        }
    except Exception as e:
        print(f"⚠️ Failed to fetch worker stats: {e}")
        return None

def all_workers_idle(worker_load):
    return all(w["active"] == 0 for w in worker_load.values())

def wait_for_decompression(gz_path, delay=5, max_wait=60):
    decompressed_path = gz_path[:-3]
    waited = 0
    while not os.path.exists(decompressed_path) and waited < max_wait:
        time.sleep(delay)
        waited += delay
    return

# Purge leftover tasks
try:
    print("🧹 Purging leftover Celery tasks...")
    purged = app.control.purge()
    print(f"✅ Purged {purged} task(s)")
except OperationalError as e:
    print(f"❌ Failed to purge tasks: {e}")

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

### PHASE 1: 24-hour internal chunk stress loop
end_time = datetime.now() + timedelta(hours=24)
iteration = 0

print("📅 Starting 24-hour stress loop...")
with open(LOG_PATH, "a") as log_file:
    while datetime.now() < end_time:
        iteration += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"\n--- Iteration #{iteration} at {timestamp} ---\n")

        for kind, chunk_dir in CHUNK_DIRS.items():
            if kind != "internal":
                continue  # Skip user chunks in Phase 1

            output_dir = OUTPUT_DIRS[kind]
            os.makedirs(output_dir, exist_ok=True)

            files = sorted(
                glob.glob(os.path.join(chunk_dir, "*.fasta")) +
                glob.glob(os.path.join(chunk_dir, "*.fasta.gz"))
            )

            for path in files:
                base = os.path.basename(path)
                base_out = base.replace(".fasta", ".json").replace(".fasta.gz", ".json")
                output_path = os.path.join(output_dir, base_out)

                if os.path.exists(output_path):
                    continue

                while True:
                    worker_load = get_worker_load()
                    if worker_load:
                        workers = list(worker_load.items())
                        random.shuffle(workers)
                        chosen = next((w for w, l in workers if l["active"] < MAX_PENDING), None)
                    else:
                        chosen = None

                    if not chosen:
                        log_file.write("⏳ All workers busy. Waiting...\n")
                        time.sleep(WAIT_FOR_IDLE_DELAY)
                    else:
                        log_file.write(f"🚀 Submitting {path} to {chosen}\n")
                        app.send_task("celery_worker.infer_fasta_file", args=[path])
                        if path.endswith(".gz"):
                            time.sleep(GZ_SUBMIT_DELAY)
                            wait_for_decompression(path)
                        break

        while True:
            worker_load = get_worker_load()
            if worker_load and all_workers_idle(worker_load):
                break
            time.sleep(WAIT_FOR_IDLE_DELAY)

    ### PHASE 2: Watch user_chunks forever
    log_file.write("\n🔄 Entering continuous user monitoring mode...\n")
    print("\n🔄 Entering continuous user monitoring mode...\n")

    while True:
        user_dir = CHUNK_DIRS["user"]
        output_dir = OUTPUT_DIRS["user"]
        os.makedirs(output_dir, exist_ok=True)

        files = sorted(
            glob.glob(os.path.join(user_dir, "**/*.fasta"), recursive=True) +
            glob.glob(os.path.join(user_dir, "**/*.fasta.gz"), recursive=True)
        )

        for path in files:
            base = os.path.basename(path)
            base_out = base.replace(".fasta", ".json").replace(".fasta.gz", ".json")
            output_path = os.path.join(output_dir, base_out)

            if os.path.exists(output_path):
                continue

            while True:
                worker_load = get_worker_load()
                if worker_load:
                    workers = list(worker_load.items())
                    random.shuffle(workers)
                    chosen = next((w for w, l in workers if l["active"] < MAX_PENDING), None)
                else:
                    chosen = None

                if not chosen:
                    log_file.write("⏳ All workers busy. Waiting...\n")
                    time.sleep(WAIT_FOR_IDLE_DELAY)
                else:
                    log_file.write(f"🚀 Submitting user file {path} to {chosen}\n")
                    app.send_task("celery_worker.infer_fasta_file", args=[path])
                    if path.endswith(".gz"):
                        time.sleep(GZ_SUBMIT_DELAY)
                        wait_for_decompression(path)
                    break

        time.sleep(20)  # Small delay before re-scanning
