#!/usr/bin/env python3
"""
celery_worker.py – Celery tasks for splitting & scheduling, then embedding chunks.
"""

import os, sys, gzip, shutil, json, subprocess, time, logging
from datetime import datetime
from celery import Celery, current_task
from Bio import SeqIO
import torch, esm

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

MAX_SEQ_LEN   = 3000
BATCH_SIZE    = 8
GLUSTER_BASE  = "/mnt/data_volume"
CHUNK_TMP     = os.path.join(GLUSTER_BASE, "tmp_chunks")
USER_CHUNKS   = os.path.join(GLUSTER_BASE, "datasets/user_chunks")
INTERNAL_CHUNKS = os.path.join(GLUSTER_BASE, "datasets/internal_chunks")
RESULT_ROOT   = "/mnt/data_volume/results"
BENCHMARK_LOG = os.path.join(RESULT_ROOT, "benchmark_log.jsonl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
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
# Load ESM2 once
# ──────────────────────────────────────────────────────────────────────────────
log.info("🧠 Loading ESM‑2‑T6‑8M model…")
model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()
log.info(f"✅ Model ready ({model.num_layers} layers).")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def hr_size(n): 
    for unit in ("B","K","M","G"):
        if n<1024 or unit=="G": return f"{n:.1f}{unit}"
        n/=1024
    return f"{n:.1f}G"

def log_benchmark(entry):
    os.makedirs(os.path.dirname(BENCHMARK_LOG), exist_ok=True)
    with open(BENCHMARK_LOG,"a") as f:
        f.write(json.dumps(entry)+"\n")

def run_batch(batch):
    _,_,toks = batch_converter(batch)
    with torch.no_grad(): out = model(toks, repr_layers=[model.num_layers])
    reps = out["representations"][model.num_layers]
    return [
        {"id":lab,"sequence":seq,"embedding":reps[i,1:len(seq)+1].mean(0).tolist()}
        for i,(lab,seq) in enumerate(batch)
    ]

def is_gzipped(filepath):
    try:
        with open(filepath, 'rb') as f:
            return f.read(2) == b'\x1f\x8b'
    except Exception:
        return False

# ──────────────────────────────────────────────────────────────────────────────
# Task: split + schedule all chunks
# ──────────────────────────────────────────────────────────────────────────────
@app.task(name="celery_worker.split_and_schedule")
def split_and_schedule(uploaded_path, job_id):
    log.info(f"✂️ Splitting upload {uploaded_path} for job {job_id}…")
    os.makedirs(CHUNK_TMP, exist_ok=True)
    target_dir = os.path.join(USER_CHUNKS, job_id)
    os.makedirs(target_dir, exist_ok=True)

    # decompress (safely)
    if uploaded_path.endswith(".gz") and is_gzipped(uploaded_path):
        raw = uploaded_path[:-3]
        try:
            with gzip.open(uploaded_path,"rb") as fi, open(raw,"wb") as fo:
                shutil.copyfileobj(fi,fo)
            uploaded_path = raw
        except Exception as e:
            log.error(f"❌ Failed to decompress: {uploaded_path} — {e}")
            raise
    elif uploaded_path.endswith(".gz"):
        log.warning(f"⚠️ File ends with .gz but is not a valid gzip. Using as-is: {uploaded_path}")

    size = os.path.getsize(uploaded_path)
    chunk_files = []

    if size < 30 * 1024 * 1024:
        single = os.path.join(target_dir, "chunk_001.fasta")
        shutil.copy(uploaded_path, single)
        subprocess.run(f"pigz -f {single}", shell=True, check=True)
        chunk_files.append("chunk_001.fasta.gz")
    else:
        split_cmd = (
            f"split --numeric-suffixes=1 --suffix-length=3 -C 30m "
            f"--additional-suffix=.fasta {uploaded_path} {CHUNK_TMP}/chunk_"
        )
        log.info(f"🧪 Running split: {split_cmd}")
        subprocess.run(split_cmd, shell=True, check=True)

        for f in sorted(os.listdir(CHUNK_TMP)):
            if f.endswith(".fasta"):
                p = os.path.join(CHUNK_TMP, f)
                subprocess.run(f"pigz -f {p}", shell=True, check=True)

        for f in sorted(os.listdir(CHUNK_TMP)):
            if f.endswith(".gz"):
                shutil.move(os.path.join(CHUNK_TMP, f), os.path.join(target_dir, f))
                chunk_files.append(f)

    man = {"job_id": job_id, "chunks": chunk_files}
    with open(os.path.join(target_dir, "manifest.json"), "w") as mf:
        json.dump(man, mf, indent=2)

    for fname in chunk_files:
        chunk_path = os.path.join(target_dir, fname)
        log.info(f"🚀 Scheduling inference for {chunk_path}")
        app.send_task("celery_worker.infer_fasta_file", args=[chunk_path])

# ──────────────────────────────────────────────────────────────────────────────
# Task: actual model inference
# ──────────────────────────────────────────────────────────────────────────────
@app.task(name="celery_worker.infer_fasta_file", acks_late=True)
def infer_fasta_file(path: str):
    log.info(f"📥 Started task: {path}")
    t0, seq_count = time.time(), 0
    try:
        opener = gzip.open if path.endswith(".gz") else open
        base = os.path.basename(path)
        out_dir = (INTERNAL_CHUNKS in path
            and os.path.join(RESULT_ROOT, "internal_outputs")
            or os.path.join(RESULT_ROOT, "user_outputs", path.split("/user_chunks/")[1].split("/")[0])
        )
        os.makedirs(out_dir, exist_ok=True)
        out_fp = os.path.join(out_dir, base.replace(".fasta", ".json").replace(".gz", ".json"))

        with opener(path, "rt") as hin, open(out_fp, "w") as fout:
            fout.write("[")
            first = True
            batch = []
            for rec in SeqIO.parse(hin, "fasta-pearson"):
                seq = str(rec.seq)[:MAX_SEQ_LEN]
                batch.append((rec.id, seq))
                seq_count += 1
                if len(batch) == BATCH_SIZE:
                    res = run_batch(batch)
                    if not first: fout.write(",")
                    fout.write(json.dumps(res)[1:-1])
                    first = False
                    batch = []
            if batch:
                res = run_batch(batch)
                if not first: fout.write(",")
                fout.write(json.dumps(res)[1:-1])
            fout.write("]")

        elapsed = time.time() - t0
        entry = {
            "input_file": path,
            "output_file": out_fp,
            "num_sequences": seq_count,
            "input_file_size": hr_size(os.path.getsize(path)),
            "time_seconds": round(elapsed, 2),
            "worker": current_task.request.hostname,
            "status": "success",
            "timestamp": datetime.now().strftime("%F %T")
        }
        log_benchmark(entry)
        log.info(f"✅ Finished {out_fp} ({seq_count} seq in {elapsed:.1f}s)")

    except Exception as e:
        elapsed = time.time() - t0
        entry = {
            "input_file": path,
            "output_file": out_fp if 'out_fp' in locals() else "",
            "num_sequences": seq_count,
            "input_file_size": os.path.getsize(path) if os.path.exists(path) else "",
            "time_seconds": round(elapsed, 2),
            "worker": current_task.request.hostname,
            "status": "failure",
            "error": str(e),
            "timestamp": datetime.now().strftime("%F %T")
        }
        log_benchmark(entry)
        log.exception(f"❌ Error on {path}")
    return "done"
