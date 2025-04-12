#!/usr/bin/env python3
import os
import glob
import time
import random
from datetime import datetime, timedelta
from kombu.exceptions import OperationalError
from celery_app.app import app  # Make sure your PYTHONPATH is set to include /home/almalinux

# Directories where chunks reside (you can adjust if needed)
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

# Set to 1 to send only one file per worker at a time
MAX_PENDING = 1  
# Wait this many seconds before checking workers again
WAIT_FOR_IDLE_DELAY = 30  # seconds
# Additional delay after submitting a gzip file to allow decompression
GZ_SUBMIT_DELAY = 20      # seconds

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

# Purge any leftover tasks at startup
try:
    print("🧹 Purging leftover tasks...")
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

        for kind, chunk_dir in CHUNK_DIRS.items():
            # Get all .fasta and .fasta.gz files from the chunk directory
            files = sorted(
                glob.glob(os.path.join(chunk_dir, "*.fasta")) +
                glob.glob(os.path.join(chunk_dir, "*.fasta.gz"))
            )

            # For each file, check if the corresponding JSON output already exists in the proper output dir.
            for path in files:
                # Determine the output directory based on the file type
                output_dir = OUTPUT_DIRS.get(kind)
                os.makedirs(output_dir, exist_ok=True)
                base = os.path.basename(path)
                base_out = base.replace(".fasta", ".json").replace(".fasta.gz", ".json")
                output_path = os.path.join(output_dir, base_out)

                if os.path.exists(output_path):
                    print(f"✅ Already processed: {output_path}")
                    log_file.write(f"✅ Already processed: {output_path}\n")
                else:
                    while True:
                        worker_load = get_worker_load()
                        if worker_load:
                            # Shuffle the list to distribute load more evenly
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
                            # If the file is compressed, delay additional time to allow decompression
                            if path.endswith(".gz"):
                                print("🕓 Delaying for gzip decompression...")
                                log_file.write("🕓 Delaying for gzip decompression...\n")
                                log_file.flush()
                                time.sleep(GZ_SUBMIT_DELAY)
                            break

        # Wait for all workers to finish the current batch before moving on
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
