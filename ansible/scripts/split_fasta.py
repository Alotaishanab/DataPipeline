#!/usr/bin/env python3

import os
from pathlib import Path
from Bio import SeqIO

INPUT_FASTA = "uniref50.fasta"
OUTPUT_DIR = "fasta_parts"
MAX_FILE_SIZE_MB = 100

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

current_records = []
current_size = 0
file_index = 0

with open(INPUT_FASTA, "r") as handle:
    for record in SeqIO.parse(handle, "fasta"):
        record_str = f">{record.id}\n{record.seq}\n"
        record_bytes = len(record_str.encode("utf-8"))

        if current_size + record_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
            out_path = os.path.join(OUTPUT_DIR, f"chunk_{file_index:04}.fasta")
            with open(out_path, "w") as out_handle:
                SeqIO.write(current_records, out_handle, "fasta")
            print(f"✅ Wrote {out_path} ({len(current_records)} sequences)")

            file_index += 1
            current_records = []
            current_size = 0

        current_records.append(record)
        current_size += record_bytes

if current_records:
    out_path = os.path.join(OUTPUT_DIR, f"chunk_{file_index:04}.fasta")
    with open(out_path, "w") as out_handle:
        SeqIO.write(current_records, out_handle, "fasta")
    print(f"✅ Wrote {out_path} ({len(current_records)} sequences)")
