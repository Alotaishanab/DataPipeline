from celery import Celery
import torch
import esm
import json
from Bio import SeqIO
import subprocess
import os

app = Celery('worker', broker='redis://mgmtnode:6379/0')  # Name matches CLI command

MAX_SEQ_LEN = 3000

@app.task(name='celery_worker.infer_fasta_file')  
def infer_fasta_file(gz_path):
    # Decompress if needed
    fasta_path = gz_path[:-3]
    if not os.path.exists(fasta_path):
        print(f"🔓 Decompressing {gz_path} on worker...")
        subprocess.run(["pigz", "-d", "-f", gz_path], check=True)

    print(f"📖 Reading {fasta_path}")
    model, alphabet = esm.pretrained.esm2_t30_150M_UR50D()
    model.eval()
    batch_converter = alphabet.get_batch_converter()

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

    return json.dumps(results)
