#!/usr/bin/env python3
"""
controller.py  –  Dispatches ESM2 inference tasks.

Phase 1  (stress test) : process INTERNAL chunks for STRESS_HOURS.
Phase 2  (steady‑state) : watch USER chunks only.

If ONLY_USER_MODE is set True at launch, Phase 1 is skipped.
"""
import os, glob, time, random
from datetime import datetime, timedelta
from kombu.exceptions import OperationalError
from celery_app.app import app

# ===========================  CONFIG  ========================================
STRESS_HOURS   = 24      # duration of Phase‑1 stress test
ONLY_USER_MODE = False   # will flip to True automatically after Phase‑1

CHUNK_DIRS = {
    "internal": "/mnt/data_volume/datasets/internal_chunks",
    "user":     "/mnt/data_volume/datasets/user_chunks",
}
OUTPUT_DIRS = {
    "internal": "/mnt/data_volume/results/internal_outputs",
    "user":     "/mnt/data_volume/results/user_outputs",
}

LOG_PATH           = "/mnt/data_volume/results/controller_submit_log.txt"
MAX_PENDING        = 1         # max active tasks per worker
WAIT_FOR_IDLE_DELAY = 30       # sec
GZ_SUBMIT_DELAY     = 20       # sec extra wait after submitting *.gz
# ============================================================================

# ----------------------- utility helpers ------------------------------------
def get_worker_load():
    try:
        i      = app.control.inspect()
        active = i.active() or {}
        stats  = i.stats()  or {}
        load = {}
        for worker, tasks in active.items():
            conc = stats.get(worker, {}).get("pool", {}).get("max-concurrency", 4)
            load[worker] = {"active": len(tasks), "free_slots": conc - len(tasks)}
        return load
    except Exception as e:
        print(f"⚠️  Failed to fetch worker stats: {e}")
        return None

def all_idle(load):  # True if every worker has 0 active
    return load and all(w["active"] == 0 for w in load.values())

def wait_for_decompression(gz_path, delay=5, max_wait=60):
    target = gz_path[:-3]
    waited = 0
    while not os.path.exists(target) and waited < max_wait:
        time.sleep(delay)
        waited += delay
    return os.path.exists(target)
# ---------------------------------------------------------------------------

# ----------------------- initial purge --------------------------------------
try:
    print("🧹  Purging leftover Celery tasks...")
    purged = app.control.purge()
    print(f"✅  Purged {purged} task(s)")
except OperationalError as e:
    print(f"❌  Failed to purge tasks: {e}")

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# =========================  PHASE 1  ========================================
if not ONLY_USER_MODE:
    end_time = datetime.now() + timedelta(hours=STRESS_HOURS)
    iteration = 0
    print(f"\n📅  Starting {STRESS_HOURS}-hour stress loop ...")
    with open(LOG_PATH, "a") as log_file:
        while datetime.now() < end_time:
            iteration += 1
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_file.write(f"\n--- Iteration #{iteration} at {ts} ---\n")
            print(f"\n⏱️  Iteration #{iteration}  —  {ts}")

            # ---------- submit INTERNAL chunks ----------
            chunk_dir  = CHUNK_DIRS["internal"]
            output_dir = OUTPUT_DIRS["internal"]
            os.makedirs(output_dir, exist_ok=True)

            files = sorted(glob.glob(os.path.join(chunk_dir, "*.fasta*")))
            for path in files:
                out_name = os.path.basename(path).replace(".fasta", ".json").replace(".gz", ".json")
                out_path = os.path.join(output_dir, out_name)
                if os.path.exists(out_path):
                    continue  # already done

                # pick a worker with < MAX_PENDING active
                while True:
                    load = get_worker_load()
                    if not load:
                        time.sleep(WAIT_FOR_IDLE_DELAY)
                        continue
                    idle_worker = next((w for w,l in load.items() if l["active"] < MAX_PENDING), None)
                    if not idle_worker:
                        time.sleep(WAIT_FOR_IDLE_DELAY)
                        continue

                    print(f"🚀  Submitting {path}  ->  {idle_worker}")
                    app.send_task("celery_worker.infer_fasta_file", args=[path])
                    if path.endswith(".gz"):
                        time.sleep(GZ_SUBMIT_DELAY)
                        wait_for_decompression(path)
                    break

            # wait until workers are idle before next iteration
            while True:
                if all_idle(get_worker_load()):
                    break
                time.sleep(WAIT_FOR_IDLE_DELAY)

    # --------------- end of stress window -----------------------------------
    print("\n🛑  Stress window finished – switching to USER‑only mode.")
    try:
        purge_count = app.control.purge()
        print(f"🧹  Purged {purge_count} leftover internal tasks.")
    except OperationalError as e:
        print(f"⚠️  Could not purge queue: {e}")
    ONLY_USER_MODE = True

# =========================  PHASE 2  (USER‑only) ============================
print("\n🧑‍💻  Entering continuous USER chunk monitor ...")
with open(LOG_PATH, "a") as log_file:
    while True:
        chunk_dir  = CHUNK_DIRS["user"]
        output_dir = OUTPUT_DIRS["user"]
        os.makedirs(output_dir, exist_ok=True)

        files = sorted(glob.glob(os.path.join(chunk_dir, "**", "*.fasta*"), recursive=True))
        for path in files:
            out_name = os.path.basename(path).replace(".fasta", ".json").replace(".gz", ".json")
            out_path = os.path.join(output_dir, out_name)
            if os.path.exists(out_path):
                continue

            while True:
                load = get_worker_load()
                idle_worker = None
                if load:
                    idle_worker = next((w for w,l in load.items() if l["active"] < MAX_PENDING), None)
                if not idle_worker:
                    time.sleep(WAIT_FOR_IDLE_DELAY)
                    continue

                print(f"🚀  Submitting {path}  ->  {idle_worker}")
                app.send_task("celery_worker.infer_fasta_file", args=[path])
                if path.endswith(".gz"):
                    time.sleep(GZ_SUBMIT_DELAY)
                    wait_for_decompression(path)
                break

        time.sleep(WAIT_FOR_IDLE_DELAY)
