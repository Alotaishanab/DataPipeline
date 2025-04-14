# test_controller.py

import pytest
from unittest import mock
from datetime import datetime
import controller


def test_get_worker_load_returns_dict():
    fake_active = {'worker1': ['task1', 'task2']}
    fake_stats = {
        'worker1': {
            'pool': {
                'max-concurrency': 4
            }
        }
    }
    with mock.patch.object(controller.app.control, 'inspect') as mock_inspect:
        mock_inspect.return_value.active.return_value = fake_active
        mock_inspect.return_value.stats.return_value = fake_stats

        load = controller.get_worker_load()
        assert isinstance(load, dict)
        assert load['worker1']['active'] == 2
        assert load['worker1']['free_slots'] == 2


def test_all_workers_idle():
    workers = {
        'worker1': {'active': 0},
        'worker2': {'active': 0}
    }
    assert controller.all_workers_idle(workers)

    workers['worker1']['active'] = 1
    assert not controller.all_workers_idle(workers)


def test_wait_for_decompression(tmp_path):
    gz_file = tmp_path / "test.fasta.gz"
    decompressed = tmp_path / "test.fasta"

    gz_file.write_bytes(b'\x1f\x8b')  # mock gzip file

    with mock.patch("os.path.exists") as mock_exists, \
         mock.patch("time.sleep"):
        mock_exists.side_effect = [False, False, True]
        controller.wait_for_decompression(str(gz_file), delay=1, max_wait=3)