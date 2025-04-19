#!/usr/bin/env python3
"""
controller.py  –  Dispatches ESM2 inference tasks.

Phase 1 (stress test): process INTERNAL chunks for STRESS_HOURS.
Phase 2 (steady‑state): watch USER chunks only.

Set ONLY_USER_MODE=False to enable Phase 1 on startup.
"""
import os
import glob
import time
from datetime import datetime, timedelta
from kombu.exceptions import OperationalError
from celery_app.app import app

# ===========================  CONFIG  ========================================
STRESS_HOURS    = 24      # duration of Phase‑1 stress test
ONLY_USER_MODE  = False    # if False, Phase 1 will run first, then switch

CHUNK_DIRS = {
    "internal": "/mnt/data_volume/datasets/internal_chunks",
    "user":     "/mnt/data_volume/datasets/user_chunks",
}
OUTPUT_DIRS = {
    "internal": "/mnt/data_volume/results/internal_outputs",
    "user":     "/mnt/data_volume/results/user_outputs",
}
LOG_PATH            = "/mnt/data_volume/results/controller_submit_log.txt"
MAX_PENDING         = 1       # max active tasks per worker
WAIT_FOR_IDLE_DELAY = 30      # sec
GZ_SUBMIT_DELAY     = 20      # extra wait after submitting .gz
# ============================================================================

def _log(msg, lf):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    lf.write(line)
    lf.flush()
    print(line, end="")

def get_worker_load():
    try:
        insp   = app.control.inspect()
        active = insp.active() or {}
        stats  = insp.stats()  or {}
        load = {}
        for w, tasks in active.items():
            conc = stats.get(w, {}).get("pool", {}).get("max-concurrency", 4)
            load[w] = {"active": len(tasks), "free_slots": conc - len(tasks)}
        return load
    except Exception as e:
        return {}

def all_idle(load):
    return all(v["active"] == 0 for v in load.values())

def wait_for_decompression(gz_path, delay=5, max_wait=60):
    target, waited = gz_path[:-3], 0
    while not os.path.exists(target) and waited < max_wait:
        time.sleep(delay); waited += delay
    return os.path.exists(target)

# ──────── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ensure log directory
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    # open log once
    with open(LOG_PATH, "a") as log_file:
        _log("🧹 Purging any leftover Celery tasks...", log_file)
        try:
            purged = app.control.purge()
            _log(f"✅ Purged {purged} task(s)", log_file)
        except OperationalError as e:
            _log(f"❌ Could not purge tasks: {e}", log_file)

        # dump chunk‐dirs at startup
        for phase in ("internal", "user"):
            listing = glob.glob(os.path.join(CHUNK_DIRS[phase], "**", "*"), recursive=True)
            _log(f"→ {phase.upper()} dir ({CHUNK_DIRS[phase]}) contains {len(listing)} entries", log_file)

        # ========== PHASE 1: STRESS ==========
        if not ONLY_USER_MODE:
            end_time  = datetime.now() + timedelta(hours=STRESS_HOURS)
            iteration = 0
            _log(f"📅 Starting {STRESS_HOURS}-hour stress loop …", log_file)
            while datetime.now() < end_time:
                iteration += 1
                _log(f"--- Iteration #{iteration} @ {datetime.now():%H:%M:%S} ---", log_file)

                # submit INTERNAL chunks
                for path in sorted(glob.glob(os.path.join(CHUNK_DIRS["internal"], "*.fasta*"))):
                    out_name = os.path.basename(path).replace(".fasta", ".json").replace(".gz", ".json")
                    out_path = os.path.join(OUTPUT_DIRS["internal"], out_name)
                    if os.path.exists(out_path):
                        continue

                    # wait for free worker
                    while True:
                        load = get_worker_load()
                        idle = next((w for w,l in load.items() if l["active"] < MAX_PENDING), None)
                        if not idle:
                            time.sleep(WAIT_FOR_IDLE_DELAY)
                            continue
                        _log(f"🚀 Submitting INTERNAL {path} → {idle}", log_file)
                        app.send_task("celery_worker.infer_fasta_file", args=[path])
                        if path.endswith(".gz"):
                            time.sleep(GZ_SUBMIT_DELAY)
                            wait_for_decompression(path)
                        break

                # wait until all idle
                while not all_idle(get_worker_load()):
                    time.sleep(WAIT_FOR_IDLE_DELAY)

            # end stress
            _log("🛑 Stress window finished – switching to USER‑only mode.", log_file)
            try:
                purged = app.control.purge()
                _log(f"🧹 Purged leftover internal tasks: {purged}", log_file)
            except OperationalError as e:
                _log(f"⚠️ Could not purge tasks: {e}", log_file)
            ONLY_USER_MODE = True

        # ========== PHASE 2: USER‑ONLY ==========
        _log("🧑‍💻 Entering continuous USER chunk monitor …", log_file)
        while True:
            # scan each job subdir
            for path in sorted(glob.glob(os.path.join(CHUNK_DIRS["user"], "**", "*.fasta*"), recursive=True)):
                rel    = path.split("/user_chunks/", 1)[-1]
                job_id = rel.split("/", 1)[0]
                out_dir = os.path.join(OUTPUT_DIRS["user"], job_id)
                os.makedirs(out_dir, exist_ok=True)

                out_name = os.path.basename(path).replace(".fasta", ".json").replace(".gz", ".json")
                out_path = os.path.join(out_dir, out_name)
                if os.path.exists(out_path):
                    continue

                # submit as soon as a worker frees up
                while True:
                    load = get_worker_load()
                    idle = next((w for w,l in load.items() if l["active"] < MAX_PENDING), None)
                    if not idle:
                        time.sleep(WAIT_FOR_IDLE_DELAY)
                        continue
                    _log(f"🚀 Submitting USER {path} → {idle}", log_file)
                    app.send_task("celery_worker.infer_fasta_file", args=[path])
                    if path.endswith(".gz"):
                        time.sleep(GZ_SUBMIT_DELAY)
                        wait_for_decompression(path)
                    break

            time.sleep(WAIT_FOR_IDLE_DELAY)
