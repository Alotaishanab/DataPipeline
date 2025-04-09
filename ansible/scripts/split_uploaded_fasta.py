#!/usr/bin/env python3
import os
import sys
import gzip
import shutil
import subprocess

if len(sys.argv) != 2:
    print("Usage: split_uploaded_fasta.py <uploaded_fasta_path>")
    sys.exit(1)

input_file = sys.argv[1]

# Updated GlusterFS paths
gluster_base = "/mnt/data_volume"
chunk_dir = os.path.join(gluster_base, "tmp_chunks")
final_target = os.path.join(gluster_base, "datasets/uni_chunks")
chunk_count = 32

# Ensure target directories exist
os.makedirs(chunk_dir, exist_ok=True)
os.makedirs(final_target, exist_ok=True)

# Count the number of sequences
seq_count_cmd = f"grep '^>' {input_file} | wc -l"
seq_count = int(subprocess.check_output(seq_count_cmd, shell=True).decode().strip())
chunk_size = -(-seq_count // chunk_count)  # ceiling division

# Split using awk
split_cmd = f"""
awk -v chunk_size={chunk_size} -v out="{chunk_dir}" '
  BEGIN {{ file_n = 1; seq_seen = 0; }}
  /^>/ {{ seq_seen++; if (seq_seen > chunk_size) {{ seq_seen=1; file_n++; }} }}
  {{ outFile = sprintf("%s/chunk_%03d.fasta", out, file_n); print >> outFile; }}
' {input_file}
"""
subprocess.run(split_cmd, shell=True, check=True)

# Compress each chunk using pigz
for fname in os.listdir(chunk_dir):
    if fname.endswith(".fasta"):
        fpath = os.path.join(chunk_dir, fname)
        subprocess.run(f"pigz -f {fpath}", shell=True)

# Move compressed files to GlusterFS dataset target
for fname in os.listdir(chunk_dir):
    if fname.endswith(".gz"):
        shutil.move(os.path.join(chunk_dir, fname), os.path.join(final_target, fname))
