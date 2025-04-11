#!/usr/bin/env python3
import os
import json
import subprocess
import torch
import esm
from Bio import SeqIO
from celery import Celery
import traceback  # <-- Added

# Celery configuration
app = Celery(
    'worker',
    broker='redis://mgmtnode:6379/0',
    backend='redis://mgmtnode:6379/1'
)

MAX_SEQ_LEN = 3000
OUTPUT_DIR = "/mnt/data_volume/results/esm2_celery_outputs"
BATCH_SIZE = 8

print("🧠 Loading ESM2 model into memory...")
model, alphabet = esm.pretrained.esm2_t30_150M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()
print("✅ Model loaded and ready.")

@app.task(name='celery_worker.infer_fasta_file')
def infer_fasta_file(path):
    print(f"📥 Task started for: {path}")
    
    if path.endswith(".gz"):
        fasta_path = path[:-3]
        if not os.path.exists(fasta_path):
            print(f"🔓 Decompressing {path}...")
            subprocess.run(["pigz", "-d", "-f", path], check=True)
        else:
            print(f"🟢 Already decompressed: {fasta_path}")
    else:
        fasta_path = path

    print(f"📖 Reading sequences from: {fasta_path}")
    results = []
    batch = []

    try:
        for record in SeqIO.parse(fasta_path, "fasta"):
            seq = str(record.seq)
            if len(seq) > MAX_SEQ_LEN:
                seq = seq[:MAX_SEQ_LEN]
            batch.append((record.id, seq))

            if len(batch) == BATCH_SIZE:
                print("⚙️ Processing batch...")
                _, _, tokens = batch_converter(batch)
                with torch.no_grad():
                    out = model(tokens, repr_layers=[30], return_contacts=False)
                reps = out["representations"][30]
                for i, (label, seq) in enumerate(batch):
                    embedding = reps[i, 1:len(seq)+1].mean(0).tolist()
                    results.append({"id": label, "sequence": seq, "embedding": embedding})
                batch = []
        
        if batch:
            print("⚙️ Processing remaining batch...")
            _, _, tokens = batch_converter(batch)
            with torch.no_grad():
                out = model(tokens, repr_layers=[30], return_contacts=False)
            reps = out["representations"][30]
            for i, (label, seq) in enumerate(batch):
                embedding = reps[i, 1:len(seq)+1].mean(0).tolist()
                results.append({"id": label, "sequence": seq, "embedding": embedding})

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        base = os.path.basename(fasta_path).replace(".fasta", ".json").replace(".gz", "")
        output_path = os.path.join(OUTPUT_DIR, base)
        print(f"💾 Writing output to: {output_path}")
        with open(output_path, 'w') as f:
            json.dump(results, f)

        print("✅ Task complete.")

    except Exception as e:
        print(f"❌ Error processing {fasta_path}: {e}")
        traceback.print_exc()  # <-- Added this to dump full stack trace

    return "done"
