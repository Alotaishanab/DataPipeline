# test_split_fasta.py

import os
import gzip
import shutil
import subprocess


def test_split_uploaded_fasta(tmp_path):
    test_input_path = tmp_path / "input.fasta"
    test_output_dir = tmp_path / "out"
    chunk_dir = tmp_path / "tmp_chunks"

    # Simulate FASTA content with 6 sequences
    fasta_content = ">seq1\nATGC\n>seq2\nATGC\n>seq3\nATGC\n>seq4\nATGC\n>seq5\nATGC\n>seq6\nATGC\n"
    with open(test_input_path, 'w') as f:
        f.write(fasta_content)

    # Update chunk path env
    os.environ['TMPDIR'] = str(chunk_dir)
    os.makedirs(chunk_dir, exist_ok=True)

    chunk_size = 2  # simulate manually for testing
    split_cmd = f"""
    awk -v chunk_size={chunk_size} -v out="{chunk_dir}" '
      BEGIN {{ file_n = 1; seq_seen = 0; }}
      /^>/ {{ seq_seen++; if (seq_seen > chunk_size) {{ seq_seen=1; file_n++; }} }}
      {{ outFile = sprintf("%s/chunk_%03d.fasta", out, file_n); print >> outFile; }}
    ' {test_input_path}
    """

    subprocess.run(split_cmd, shell=True, check=True)

    chunked = list(chunk_dir.glob("chunk_*.fasta"))
    assert len(chunked) == 3

    for f in chunked:
        subprocess.run(["pigz", "-f", str(f)])

    gz_files = list(chunk_dir.glob("*.gz"))
    assert len(gz_files) == 3

    final_target = tmp_path / "final_chunks"
    os.makedirs(final_target, exist_ok=True)

    for f in gz_files:
        shutil.move(str(f), final_target / f.name)

    assert len(list(final_target.iterdir())) == 3
