#!/usr/bin/env python3
import os
import glob
import time
import random
from datetime import datetime, timedelta
from kombu.exceptions import OperationalError
from celery_app.app import app

# ===========================
# ✅ CONFIG
# ===========================
ONLY_USER_MODE = True  # Set True to skip stress loop and only monitor user chunks

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

# ===========================
# 🚀 Utility Functions
# ===========================
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

def wait_for_decompression(gz_path, delay=5, max_wait=60):
    decompressed_path = gz_path[:-3]
    waited = 0
    print(f"🕓 Waiting for decompression of {gz_path} to complete...")
    while not os.path.exists(decompressed_path) and waited < max_wait:
        time.sleep(delay)
        waited += delay
        print(f"   ... waited {waited}/{max_wait} seconds")
    if os.path.exists(decompressed_path):
        print(f"✅ Decompression complete: {decompressed_path}")
    else:
        print(f"⚠️ WARNING: Decompressed file not found for {gz_path} after {max_wait} seconds")
    return

# ===========================
# 🔁 Initialization
# ===========================
try:
    print("🧹 Purging leftover Celery tasks...")
    purged = app.control.purge()
    print(f"✅ Purged {purged} task(s)")
except OperationalError as e:
    print(f"❌ Failed to purge tasks: {e}")

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# ===========================
# 🔄 PHASE 1: Stress Test (24hr)
# ===========================
if not ONLY_USER_MODE:
    end_time = datetime.now() + timedelta(hours=24)
    iteration = 0
    print("\n📅 Starting 24-hour stress loop...")
    with open(LOG_PATH, "a") as log_file:
        while datetime.now() < end_time:
            iteration += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_file.write(f"\n--- Iteration #{iteration} at {timestamp} ---\n")
            print(f"\n⏱️ Iteration #{iteration} — {timestamp}")

            for kind in ["internal"]:
                chunk_dir = CHUNK_DIRS[kind]
                output_dir = OUTPUT_DIRS[kind]
                os.makedirs(output_dir, exist_ok=True)

                files = sorted(glob.glob(os.path.join(chunk_dir, "*.fasta")) +
                               glob.glob(os.path.join(chunk_dir, "*.fasta.gz")))

                for path in files:
                    base = os.path.basename(path)
                    base_out = base.replace(".fasta", ".json").replace(".fasta.gz", ".json")
                    output_path = os.path.join(output_dir, base_out)

                    if os.path.exists(output_path):
                        print(f"✅ Already processed: {output_path}")
                        log_file.write(f"✅ Already processed: {output_path}\n")
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
                                print("🕓 Initial delay for gzip decompression...")
                                log_file.write("🕓 Initial delay for gzip decompression...\n")
                                log_file.flush()
                                time.sleep(GZ_SUBMIT_DELAY)
                                wait_for_decompression(path)
                            break

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

# ===========================
# 🔄 PHASE 2: Continuous User Chunk Watch
# ===========================
print("\n🧑‍💻 Entering continuous user chunk monitor mode...")
with open(LOG_PATH, "a") as log_file:
    while True:
        chunk_dir = CHUNK_DIRS["user"]
        output_dir = OUTPUT_DIRS["user"]
        os.makedirs(output_dir, exist_ok=True)

        files = sorted(glob.glob(os.path.join(chunk_dir, "**", "*.fasta"), recursive=True) +
                       glob.glob(os.path.join(chunk_dir, "**", "*.fasta.gz"), recursive=True))

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
                    time.sleep(WAIT_FOR_IDLE_DELAY)
                else:
                    print(f"🚀 Submitting {path} to {chosen}")
                    log_file.write(f"🚀 Submitting {path} to {chosen}\n")
                    app.send_task("celery_worker.infer_fasta_file", args=[path])
                    log_file.flush()

                    if path.endswith(".gz"):
                        time.sleep(GZ_SUBMIT_DELAY)
                        wait_for_decompression(path)
                    break
        time.sleep(WAIT_FOR_IDLE_DELAY)
