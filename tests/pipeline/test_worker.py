# test_worker.py

import pytest
from unittest import mock
import celery_worker


def test_run_batch_returns_list():
    batch = [('seq1', 'MADEUPSEQ')]
    with mock.patch.object(celery_worker, 'model') as mock_model:
        mock_model.num_layers = 33
        mock_model.return_contacts = False
        mock_model.return_value = {
            "representations": {
                33: mock.Mock(__getitem__=lambda self, idx: mock.Mock(mean=lambda axis: mock.Mock(to_list=lambda: [0.1]*128)))
            }
        }
        result = celery_worker.run_batch(batch)
        assert isinstance(result, list)
        assert "id" in result[0]
        assert "embedding" in result[0]


def test_infer_fasta_file_handles_invalid_file():
    with mock.patch("builtins.open", side_effect=FileNotFoundError):
        result = celery_worker.infer_fasta_file("/nonexistent.fasta")
        assert result == "done"