#!/usr/bin/env python3

import os
import glob
import time
from datetime import datetime, timedelta
from worker import infer_fasta_file

CHUNK_DIR = "/mnt/data_volume/datasets/uni_chunks"
LOG_PATH = "/mnt/data_volume/results/esm2_celery_outputs/submit_log.txt"

end_time = datetime.now() + timedelta(hours=24)
iteration = 0

print("📅 Starting 24-hour job loop...")

with open(LOG_PATH, "a") as log_file:
    while datetime.now() < end_time:
        iteration += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n⏱️ Iteration #{iteration} — {timestamp}")
        log_file.write(f"\n--- Iteration #{iteration} at {timestamp} ---\n")

        # Match both .fasta and .fasta.gz
        files = sorted(
            glob.glob(os.path.join(CHUNK_DIR, "*.fasta")) +
            glob.glob(os.path.join(CHUNK_DIR, "*.fasta.gz"))
        )

        if not files:
            print("⚠️ No FASTA or GZ files found!")
            log_file.write("⚠️ No FASTA or GZ files found!\n")
            time.sleep(60)
            continue

        for path in files:
            print(f"🚀 Submitting {path}...")
            log_file.write(f"🚀 Submitting {path}\n")
            infer_fasta_file.delay(path)

        log_file.flush()
        time.sleep(10)  # short pause between loops

print("\n🎉 Completed 24-hour run.")
