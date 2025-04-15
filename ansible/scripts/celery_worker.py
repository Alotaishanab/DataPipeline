#!/usr/bin/env python3
import os
import json
import torch
import esm
import logging
import gzip
import time
from Bio import SeqIO
from celery import Celery

# Threading control
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger(__name__)

# Celery setup
app = Celery(
    'worker',
    broker='redis://mgmtnode:6379/0',
    backend='redis://mgmtnode:6379/1'
)

MAX_SEQ_LEN = 3000
RESULT_ROOT = "/mnt/data_volume/results"
BENCHMARK_FILE = os.path.join(RESULT_ROOT, "benchmark_log.jsonl")
BATCH_SIZE = 8

# Load model once
log.info("🧠 Loading ESM2 model...")
model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()
log.info(f"✅ ESM2 model loaded with {model.num_layers} layers.")

def human_readable_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f}K"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f}M"
    else:
        return f"{size_bytes / (1024 ** 3):.1f}G"

@app.task(name='celery_worker.infer_fasta_file', acks_late=True)
def infer_fasta_file(path):
    log.info(f"📥 Task started: {path}")
    start = time.time()

    try:
        open_func = gzip.open if path.endswith(".gz") else open

        # Determine output dir
        if "/user_chunks/" in path:
            output_dir = os.path.join(RESULT_ROOT, "user_outputs")
        else:
            output_dir = os.path.join(RESULT_ROOT, "internal_outputs")
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(
            output_dir,
            os.path.basename(path).replace(".fasta", ".json").replace(".gz", "")
        )

        sequence_count = 0
        file_size_bytes = os.path.getsize(path)
        file_size_str = human_readable_size(file_size_bytes)

        with open_func(path, "rt") as handle, open(output_file, 'w') as f_out:
            f_out.write("[\n")
            first = True
            batch = []

            for record in SeqIO.parse(handle, "fasta-pearson"):
                seq = str(record.seq)[:MAX_SEQ_LEN]
                batch.append((record.id, seq))
                sequence_count += 1

                if len(batch) == BATCH_SIZE:
                    batch_result = run_batch(batch)
                    if not first:
                        f_out.write(",\n")
                    f_out.write(json.dumps(batch_result)[1:-1])
                    first = False
                    batch = []

            if batch:
                batch_result = run_batch(batch)
                if not first:
                    f_out.write(",\n")
                f_out.write(json.dumps(batch_result)[1:-1])

            f_out.write("\n]\n")

        duration = time.time() - start

        log.info(f"📊 Stats: {sequence_count} sequences, {file_size_str} input")
        log.info(f"✅ Completed: {output_file} in {duration:.2f} seconds")

        benchmark_data = {
            "input_file": path,
            "output_file": output_file,
            "num_sequences": sequence_count,
            "input_file_size": file_size_str,
            "time_seconds": round(duration, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(BENCHMARK_FILE, "a") as bench_out:
            bench_out.write(json.dumps(benchmark_data) + "\n")

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
