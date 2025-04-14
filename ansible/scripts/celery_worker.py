#!/usr/bin/env python3
import os
import json
import subprocess
import torch
import esm
import logging
import gzip
from Bio import SeqIO
from celery import Celery

# Threading control (important for CPU usage)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger(__name__)

# Celery config
app = Celery(
    'worker',
    broker='redis://mgmtnode:6379/0',
    backend='redis://mgmtnode:6379/1'
)

MAX_SEQ_LEN = 3000
RESULT_ROOT = "/mnt/data_volume/results"
BATCH_SIZE = 8

# Model loading happens ONCE per worker
log.info("🧠 Loading ESM2 model...")
model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()
log.info(f"✅ ESM2 model loaded with {model.num_layers} layers.")

@app.task(name='celery_worker.infer_fasta_file', acks_late=True)
def infer_fasta_file(path):
    log.info(f"📥 Task started: {path}")
    try:
        # Use gzip.open if the file is compressed, else regular open
        open_func = gzip.open if path.endswith(".gz") else open

        results = []
        batch = []

        with open_func(path, "rt") as handle:
            for record in SeqIO.parse(handle, "fasta"):
                seq = str(record.seq)[:MAX_SEQ_LEN]
                batch.append((record.id, seq))

                if len(batch) == BATCH_SIZE:
                    results.extend(run_batch(batch))
                    batch = []

        if batch:
            results.extend(run_batch(batch))

        # Determine output directory
        if "/user_chunks/" in path:
            output_dir = os.path.join(RESULT_ROOT, "user_outputs")
        else:
            output_dir = os.path.join(RESULT_ROOT, "internal_outputs")
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(
            output_dir,
            os.path.basename(path).replace(".fasta", ".json").replace(".gz", "")
        )

        with open(output_file, 'w') as f:
            json.dump(results, f)

        log.info(f"✅ Completed: {output_file}")
    except Exception as e:
        log.exception(f"❌ Error processing {path}")
    return "done"

def run_batch(batch):
    _, _, tokens = batch_converter(batch)
    with torch.no_grad():
        out = model(tokens, repr_layers=[model.num_layers], return_contacts=False)
    reps = out["representations"][model.num_layers]
    return [
        {
            "id": label,
            "sequence": seq,
            "embedding": reps[i, 1:len(seq)+1].mean(0).tolist()
        }
        for i, (label, seq) in enumerate(batch)
    ]

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        infer_fasta_file(sys.argv[1])
    else:
        log.error("Usage: python celery_worker.py <fasta_file>")
