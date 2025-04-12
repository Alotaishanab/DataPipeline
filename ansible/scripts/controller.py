#!/usr/bin/env python3
import os
import glob
import time
import random
from datetime import datetime, timedelta
from kombu.exceptions import OperationalError
from celery_app.app import app  

# Directories where chunk files are stored
CHUNK_DIRS = {
    "internal": "/mnt/data_volume/datasets/internal_chunks",
    "user": "/mnt/data_volume/datasets/user_chunks"
}

# Output directories for processed results
OUTPUT_DIRS = {
    "internal": "/mnt/data_volume/results/internal_outputs",
    "user": "/mnt/data_volume/results/user_outputs"
}

# Log file for the controller’s activity
LOG_PATH = "/mnt/data_volume/results/controller_submit_log.txt"

# Configuration: send one task per worker (1 file per worker at a time)
MAX_PENDING = 1  
# Delay (in seconds) to wait before rechecking worker status
WAIT_FOR_IDLE_DELAY = 30  
# Base delay (in seconds) after submitting a .gz file; additional polling is added below
GZ_SUBMIT_DELAY = 20  

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
    """Wait until the decompressed file (i.e. without the .gz suffix) exists.
       This polls every `delay` seconds until max_wait seconds have passed."""
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

# Purge any leftover tasks at startup
try:
    print("🧹 Purging leftover Celery tasks...")
    purged = app.control.purge()
    print(f"✅ Purged {purged} task(s)")
except OperationalError as e:
    print(f"❌ Failed to purge tasks: {e}")

# Ensure the log directory exists
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

end_time = datetime.now() + timedelta(hours=24)
iteration = 0

print("📅 Starting stress test loop...")
with open(LOG_PATH, "a") as log_file:
    while datetime.now() < end_time:
        iteration += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"\n--- Iteration #{iteration} at {timestamp} ---\n")
        print(f"\n⏱️ Iteration #{iteration} — {timestamp}")

        # Loop over the defined chunk directories (for internal and user)
        for kind, chunk_dir in CHUNK_DIRS.items():
            # Determine the output directory for this kind
            output_dir = OUTPUT_DIRS.get(kind)
            os.makedirs(output_dir, exist_ok=True)

            # Find both .fasta and .fasta.gz files in the chunk directory (sorted)
            files = sorted(
                glob.glob(os.path.join(chunk_dir, "*.fasta")) +
                glob.glob(os.path.join(chunk_dir, "*.fasta.gz"))
            )

            # Iterate through each file
            for path in files:
                # Determine the expected output JSON filename.
                base = os.path.basename(path)
                base_out = base.replace(".fasta", ".json").replace(".fasta.gz", ".json")
                output_path = os.path.join(output_dir, base_out)

                # Skip files that have already been processed.
                if os.path.exists(output_path):
                    print(f"✅ Already processed: {output_path}")
                    log_file.write(f"✅ Already processed: {output_path}\n")
                    continue

                # Attempt to submit the file task.
                while True:
                    worker_load = get_worker_load()
                    if worker_load:
                        # Randomize workers to distribute load.
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

                        # If the file is compressed (.gz), wait for a fixed delay and then poll until it is decompressed.
                        if path.endswith(".gz"):
                            print("🕓 Initial delay for gzip decompression...")
                            log_file.write("🕓 Initial delay for gzip decompression...\n")
                            log_file.flush()
                            time.sleep(GZ_SUBMIT_DELAY)
                            wait_for_decompression(path)
                        break  # Move on to submit next file

        # After submitting all files in all chunk directories, wait until all workers are idle before starting the next iteration.
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
