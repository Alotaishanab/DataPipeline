#!/usr/bin/env python3
"""
Simple script to compute summary statistics from a JSONL benchmark log.
Usage:
    python compute_benchmark_stats.py /path/to/benchmark_log.jsonl

Outputs:
    - total_entries
    - total_sequences
    - total_time (s)
    - avg_time_per_entry (s)
    - avg_time_per_sequence (s)
    - throughput (sequences/s)
"""
import json
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute statistics from a JSONL benchmark log file"
    )
    parser.add_argument(
        "input_file",
        help="Path to the benchmark_log.jsonl file"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    total_entries = 0
    total_sequences = 0
    total_time = 0.0

    try:
        with open(args.input_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                total_entries += 1
                total_sequences += record.get('num_sequences', 0)
                total_time += record.get('time_seconds', 0.0)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON on line {total_entries+1}: {e}", file=sys.stderr)
        sys.exit(1)

    if total_entries == 0:
        print("No entries found in the log.")
        sys.exit(0)

    avg_time_per_entry = total_time / total_entries
    avg_time_per_sequence = total_time / total_sequences if total_sequences else 0
    throughput = total_sequences / total_time if total_time else 0

    print(f"Total entries:        {total_entries}")
    print(f"Total sequences:      {total_sequences}")
    print(f"Total time (s):       {total_time:.2f}")
    print(f"Avg time per entry:   {avg_time_per_entry:.4f} s")
    print(f"Avg time per sequence:{avg_time_per_sequence:.6f} s")
    print(f"Throughput:           {throughput:.2f} seq/s")

if __name__ == '__main__':
    main()
