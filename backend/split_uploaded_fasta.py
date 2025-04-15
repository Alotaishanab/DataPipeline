#!/usr/bin/env python3
import os
import sys
import gzip
import shutil
import subprocess
import json

if len(sys.argv) != 3:
    print("Usage: split_uploaded_fasta.py <uploaded_fasta_path> <job_id>")
    sys.exit(1)

input_file = sys.argv[1]
job_id = sys.argv[2]

# Decompress if .gz
if input_file.endswith('.gz'):
    uncompressed_path = input_file[:-3]
    with gzip.open(input_file, 'rb') as f_in:
        with open(uncompressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    input_file = uncompressed_path

# GlusterFS paths
gluster_base = "/mnt/data_volume"
chunk_dir = os.path.join(gluster_base, "tmp_chunks")
final_target = os.path.join(gluster_base, "datasets/user_chunks", job_id)
manifest_path = os.path.join(final_target, "manifest.json")

os.makedirs(chunk_dir, exist_ok=True)
os.makedirs(final_target, exist_ok=True)

file_size_bytes = os.path.getsize(input_file)
chunk_files = []

if file_size_bytes < 30 * 1024 * 1024:  # < 30MB
    print("📦 File is small, no need to split. Copying as single chunk...")

    single_chunk = os.path.join(final_target, "chunk_001.fasta")
    shutil.copyfile(input_file, single_chunk)

    subprocess.run(f"pigz -f {single_chunk}", shell=True)
    chunk_files.append("chunk_001.fasta.gz")

else:
    print("🔪 Splitting file into ~30MB chunks...")

    # Split by file size (~30MB)
    split_cmd = f"""
    split --numeric-suffixes=1 --suffix-length=3 -C 30m \
    --additional-suffix=.fasta {input_file} {chunk_dir}/chunk_
    """
    subprocess.run(split_cmd, shell=True, check=True)

    for fname in sorted(os.listdir(chunk_dir)):
        if fname.endswith(".fasta"):
            fpath = os.path.join(chunk_dir, fname)
            subprocess.run(f"pigz -f {fpath}", shell=True)

    for fname in sorted(os.listdir(chunk_dir)):
        if fname.endswith(".gz"):
            src = os.path.join(chunk_dir, fname)
            dst = os.path.join(final_target, fname)
            shutil.move(src, dst)
            chunk_files.append(fname)

# Save manifest
with open(manifest_path, "w") as mf:
    json.dump({"job_id": job_id, "chunks": chunk_files}, mf, indent=2)

print("✅ Done. Manifest saved.")
