#!/usr/bin/env python3
"""
celery_worker.py – Celery task that embeds FASTA chunks with ESM‑2.
• Writes user results into /results/user_outputs/<job_id>/<chunk>.json
• Writes internal results into /results/internal_outputs/<chunk>.json
• Appends both successes and failures to benchmark_log.jsonl
"""

import os
import json
import gzip
import shutil
import logging
import time
from Bio import SeqIO
from celery import Celery, current_task
import torch
import esm

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

MAX_SEQ_LEN   = 3000
BATCH_SIZE    = 8
RESULT_ROOT   = "/mnt/data_volume/results"
BENCHMARK_LOG = os.path.join(RESULT_ROOT, "benchmark_log.jsonl")

# ──────────────────────────────────────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Celery app
# ──────────────────────────────────────────────────────────────────────────────
app = Celery(
    "worker",
    broker="redis://mgmtnode:6379/0",
    backend="redis://mgmtnode:6379/1"
)

# ──────────────────────────────────────────────────────────────────────────────
# Load ESM2 model once
# ──────────────────────────────────────────────────────────────────────────────
log.info("🧠 Loading ESM‑2‑T6‑8M model (once per worker)…")
model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()
log.info(f"✅ Model ready ({model.num_layers} layers).")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def hr_size(n: int) -> str:
    for unit in ("B","K","M","G"):
        if n < 1024 or unit == "G":
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}G"

def safe_job_id(path: str) -> str:
    try:
        after = path.split("/user_chunks/")[1]
        jid   = after.split("/")[0]
        if "." in jid or "/" not in after:
            return "unknown_job"
        return jid
    except Exception:
        return "unknown_job"

def strip_suffix(name: str) -> str:
    if name.endswith(".fasta.gz"):
        return name[:-len(".fasta.gz")]
    if name.endswith(".fasta"):
        return name[:-len(".fasta")]
    return os.path.splitext(name)[0]

def run_batch(batch):
    _, _, toks = batch_converter(batch)
    with torch.no_grad():
        out = model(toks, repr_layers=[model.num_layers])
    reps = out["representations"][model.num_layers]
    return [
        {
            "id":       lab,
            "sequence": seq,
            "embedding": reps[i, 1:len(seq)+1].mean(0).tolist()
        }
        for i, (lab, seq) in enumerate(batch)
    ]

def log_benchmark(entry: dict):
    """Append a JSON line to the benchmark log."""
    os.makedirs(os.path.dirname(BENCHMARK_LOG), exist_ok=True)
    with open(BENCHMARK_LOG, "a") as bench:
        bench.write(json.dumps(entry) + "\n")

# ──────────────────────────────────────────────────────────────────────────────
# Celery Task
# ──────────────────────────────────────────────────────────────────────────────
@app.task(name="celery_worker.infer_fasta_file", acks_late=True)
def infer_fasta_file(path: str):
    """Process one FASTA (or .fasta.gz) chunk and log results or failures."""
    log.info(f"📥 Started task: {path}")
    t0 = time.time()
    seq_count = 0
    out_fp = None
    try:
        opener = gzip.open if path.endswith(".gz") else open
        base   = os.path.basename(path)

        # Determine output directory
        if "/user_chunks/" in path:
            job_id  = safe_job_id(path)
            out_dir = os.path.join(RESULT_ROOT, "user_outputs", job_id)
        else:
            out_dir = os.path.join(RESULT_ROOT, "internal_outputs")

        os.makedirs(out_dir, exist_ok=True)

        # Build out_fp name
        chunk_id = strip_suffix(base)
        out_fp   = os.path.join(out_dir, f"{chunk_id}.json")

        # Read, batch and infer
        with opener(path, "rt") as handle, open(out_fp, "w") as fout:
            fout.write("[\n")
            first = True
            batch = []
            for record in SeqIO.parse(handle, "fasta-pearson"):
                seq = str(record.seq)[:MAX_SEQ_LEN]
                batch.append((record.id, seq))
                seq_count += 1
                if len(batch) == BATCH_SIZE:
                    results = run_batch(batch)
                    if not first: fout.write(",\n")
                    fout.write(json.dumps(results)[1:-1])
                    first = False
                    batch = []
            # leftover
            if batch:
                results = run_batch(batch)
                if not first: fout.write(",\n")
                fout.write(json.dumps(results)[1:-1])
            fout.write("\n]\n")

        # Success benchmark entry
        elapsed = time.time() - t0
        entry = {
            "input_file":      path,
            "output_file":     out_fp,
            "num_sequences":   seq_count,
            "input_file_size": hr_size(os.path.getsize(path)),
            "time_seconds":    round(elapsed, 2),
            "worker":          current_task.request.hostname,
            "status":          "success",
            "timestamp":       time.strftime("%F %T")
        }
        log_benchmark(entry)
        log.info(f"✅ Completed: {out_fp} ({elapsed:.2f}s, {seq_count} seq)")

    except Exception as e:
        # Failure benchmark entry
        elapsed = time.time() - t0
        entry = {
            "input_file":      path,
            "output_file":     out_fp or "",
            "num_sequences":   seq_count,
            "input_file_size": hr_size(os.path.getsize(path)) if os.path.exists(path) else "",
            "time_seconds":    round(elapsed, 2),
            "worker":          current_task.request.hostname,
            "status":          "failure",
            "error":           str(e),
            "timestamp":       time.strftime("%F %T")
        }
        log_benchmark(entry)
        log.exception(f"❌ Error processing {path}")

    return "done"
