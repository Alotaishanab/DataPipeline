from celery import Celery
import torch
import esm
import json
from Bio import SeqIO
import subprocess
import os

# Celery configuration
app = Celery(
    'worker',
    broker='redis://mgmtnode:6379/0',
    backend='redis://mgmtnode:6379/1'
)

MAX_SEQ_LEN = 3000
OUTPUT_DIR = "/mnt/data_volume/results/esm2_celery_outputs"

# 🔁 Load model globally once (per worker process)
print("🧠 Loading ESM2 model into memory...")
model, alphabet = esm.pretrained.esm2_t30_150M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()
print("✅ Model loaded and ready.")

@app.task(name='celery_worker.infer_fasta_file')
def infer_fasta_file(path):
    # Handle decompression
    if path.endswith(".gz"):
        fasta_path = path[:-3]
        if not os.path.exists(fasta_path):
            print(f"🔓 Decompressing {path} on worker...")
            subprocess.run(["pigz", "-d", "-f", path], check=True)
        else:
            print(f"🟢 Already decompressed: {fasta_path}")
    else:
        fasta_path = path

    print(f"📖 Reading {fasta_path}")
    buffer = []
    for record in SeqIO.parse(fasta_path, "fasta"):
        seq = str(record.seq)
        if len(seq) > MAX_SEQ_LEN:
            seq = seq[:MAX_SEQ_LEN]
        buffer.append((record.id, seq))

    _, _, tokens = batch_converter(buffer)
    with torch.no_grad():
        out = model(tokens, repr_layers=[30], return_contacts=False)
    reps = out["representations"][30]

    results = []
    for i, (label, seq) in enumerate(buffer):
        embedding = reps[i, 1:len(seq)+1].mean(0).tolist()
        results.append({"id": label, "sequence": seq, "embedding": embedding})

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base = os.path.basename(fasta_path).replace(".fasta", ".json").replace(".gz", "")
    output_path = os.path.join(OUTPUT_DIR, base)
    with open(output_path, 'w') as f:
        json.dump(results, f)

    print(f"✅ Output written to: {output_path}")
    return "done"
