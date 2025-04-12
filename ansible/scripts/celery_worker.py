#!/usr/bin/env python3
import os
import json
import subprocess
import torch
import esm
import logging
from Bio import SeqIO
from celery import Celery
import traceback

# Setup logging
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

# Load ESM model once
try:
    log.info("🧠 Loading ESM2 model into memory...")
    model, alphabet = esm.pretrained.esm2_t30_150M_UR50D()
    model.eval()
    batch_converter = alphabet.get_batch_converter()
    log.info("✅ Model loaded and ready.")
except Exception as e:
    log.exception("❌ Failed to load ESM model")
    raise

@app.task(name='celery_worker.infer_fasta_file', acks_late=True)
def infer_fasta_file(path):
    log.info(f"📥 Task started for: {path}")
    try:
        if path.endswith(".gz"):
            fasta_path = path[:-3]
            if not os.path.exists(fasta_path):
                log.info(f"🔓 Decompressing {path}...")
                try:
                    result = subprocess.run(
                        ["pigz", "-d", "-f", path],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                except subprocess.CalledProcessError as e:
                    log.error(f"❌ Decompression failed: {e.stderr}")
                    raise
            else:
                log.info(f"🟢 Already decompressed: {fasta_path}")
        else:
            fasta_path = path

        log.info(f"📖 Reading sequences from: {fasta_path}")
        results = []
        batch = []

        for record in SeqIO.parse(fasta_path, "fasta"):
            seq = str(record.seq)
            if len(seq) > MAX_SEQ_LEN:
                seq = seq[:MAX_SEQ_LEN]
            batch.append((record.id, seq))

            if len(batch) == BATCH_SIZE:
                log.info("⚙️ Processing batch...")
                _, _, tokens = batch_converter(batch)
                with torch.no_grad():
                    out = model(tokens, repr_layers=[30], return_contacts=False)
                reps = out["representations"][30]
                for i, (label, seq) in enumerate(batch):
                    embedding = reps[i, 1:len(seq)+1].mean(0).tolist()
                    results.append({"id": label, "sequence": seq, "embedding": embedding})
                batch = []

        if batch:
            log.info("⚙️ Processing remaining batch...")
            _, _, tokens = batch_converter(batch)
            with torch.no_grad():
                out = model(tokens, repr_layers=[30], return_contacts=False)
            reps = out["representations"][30]
            for i, (label, seq) in enumerate(batch):
                embedding = reps[i, 1:len(seq)+1].mean(0).tolist()
                results.append({"id": label, "sequence": seq, "embedding": embedding})

        # Determine output path
        if "/user_chunks/" in fasta_path:
            OUTPUT_DIR = os.path.join(RESULT_ROOT, "user_outputs")
        else:
            OUTPUT_DIR = os.path.join(RESULT_ROOT, "internal_outputs")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        base = os.path.basename(fasta_path).replace(".fasta", ".json").replace(".gz", "")
        output_path = os.path.join(OUTPUT_DIR, base)

        log.info(f"💾 Writing output to: {output_path}")
        with open(output_path, 'w') as f:
            json.dump(results, f)

        log.info("✅ Task complete.")

    except Exception as e:
        log.exception(f"❌ Error processing {path}")

    return "done"

# CLI support
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        log.error("Usage: python worker.py <path_to_fasta_file>")
    else:
        infer_fasta_file(sys.argv[1])
