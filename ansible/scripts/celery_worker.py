#!/usr/bin/env python3
"""
celery_worker.py – Celery task that embeds FASTA chunks with ESM‑2.
• Writes user results into /results/user_outputs/<job_id>/<chunk>.json
• Writes internal results into /results/internal_outputs/<chunk>.json
"""

import os, json, torch, esm, logging, gzip, time
from Bio import SeqIO
from celery import Celery

# ------------------------------------------------------------------ constants
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

MAX_SEQ_LEN   = 3000
RESULT_ROOT   = "/mnt/data_volume/results"
BATCH_SIZE    = 8
BENCHMARK_LOG = os.path.join(RESULT_ROOT, "benchmark_log.jsonl")

# ------------------------------------------------------------------ logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ------------------------------------------------------------------ Celery app
app = Celery(
    "worker",
    broker="redis://mgmtnode:6379/0",
    backend="redis://mgmtnode:6379/1",
)

# ------------------------------------------------------------------ load model
log.info("🧠 Loading ESM‑2‑T6‑8M model (once per worker)…")
model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()
log.info("✅ Model ready (%d layers).", model.num_layers)

# ------------------------------------------------------------------ helpers
def hr_size(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n:.1f}{unit}"
        n /= 1024

def safe_job_id(path):
    """Return a clean directory name for user results."""
    try:
        after = path.split("/user_chunks/")[1]
        jid   = after.split("/")[0]
        # if no slash (flat file) or jid contains a dot, treat as unknown
        if "." in jid or "/" not in after:
            return "unknown_job"
        return jid
    except Exception:
        return "unknown_job"

def run_batch(batch):
    _, _, toks = batch_converter(batch)
    with torch.no_grad():
        rep = model(toks, repr_layers=[model.num_layers])["representations"][model.num_layers]
    return [
        {
            "id":  lab,
            "sequence": seq,
            "embedding": rep[i, 1:len(seq)+1].mean(0).tolist(),
        } for i, (lab, seq) in enumerate(batch)
    ]

# ------------------------------------------------------------------ task
@app.task(name="celery_worker.infer_fasta_file", acks_late=True)
def infer_fasta_file(path):
    log.info("📥 Started task: %s", path)
    t0 = time.time()

    try:
        opener = gzip.open if path.endswith(".gz") else open

        # -------- choose output directory / filename -----------------
        if "/user_chunks/" in path:
            job_id = safe_job_id(path)
            out_dir = os.path.join(RESULT_ROOT, "user_outputs", job_id)
            chunk   = os.path.basename(path).replace(".fasta", "").replace(".fasta.gz", "")
            out_fp  = os.path.join(out_dir, f"{chunk}.json")
        else:  # internal
            out_dir = os.path.join(RESULT_ROOT, "internal_outputs")
            chunk   = os.path.basename(path).replace(".fasta", "").replace(".fasta.gz", "")
            out_fp  = os.path.join(out_dir, f"{chunk}.json")

        os.makedirs(out_dir, exist_ok=True)

        # -------- embed sequences ------------------------------------
        seq_cnt = 0
        with opener(path, "rt") as fh, open(out_fp, "w") as fout:
            fout.write("[\n")
            first = True
            batch = []

            for rec in SeqIO.parse(fh, "fasta-pearson"):
                seq_cnt += 1
                batch.append((rec.id, str(rec.seq)[:MAX_SEQ_LEN]))
                if len(batch) == BATCH_SIZE:
                    res = run_batch(batch)
                    if not first: fout.write(",\n")
                    fout.write(json.dumps(res)[1:-1])
                    first = False
                    batch = []

            if batch:
                res = run_batch(batch)
                if not first: fout.write(",\n")
                fout.write(json.dumps(res)[1:-1])

            fout.write("\n]\n")

        # -------- benchmark log --------------------------------------
        elapsed = time.time() - t0
        with open(BENCHMARK_LOG, "a") as bl:
            bl.write(json.dumps({
                "input_file":  path,
                "output_file": out_fp,
                "num_sequences": seq_cnt,
                "input_file_size": hr_size(os.path.getsize(path)),
                "time_seconds": round(elapsed, 2),
                "timestamp": time.strftime("%F %T"),
            }) + "\n")

        log.info("✅ Done: %s (%.1fs, %d seq)", out_fp, elapsed, seq_cnt)

    except Exception as e:
        log.exception("❌ Error processing %s: %s", path, e)

    return "done"
