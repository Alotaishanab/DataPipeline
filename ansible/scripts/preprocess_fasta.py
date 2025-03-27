#!/usr/bin/env python3

import json

input_path = "/mnt/datasets/uniref50.fasta"
output_path = "/mnt/datasets/uniref50_preprocessed.jsonl"

with open(input_path, "r") as infile, open(output_path, "w") as outfile:
    header = None
    seq_lines = []

    for line in infile:
        line = line.strip()
        if line.startswith(">"):
            if header:
                outfile.write(json.dumps({
                    "header": header,
                    "sequence": "".join(seq_lines)
                }) + "\n")
            header = line[1:]  # Remove ">"
            seq_lines = []
        else:
            seq_lines.append(line)

    if header and seq_lines:
        outfile.write(json.dumps({
            "header": header,
            "sequence": "".join(seq_lines)
        }) + "\n")
