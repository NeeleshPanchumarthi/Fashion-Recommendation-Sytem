import json

import pytest

from workers.checkpoint_manager import CheckpointManager


def _manager(tmp_path, batch_size=10, total=35):
    return CheckpointManager(tmp_path / "state.json", tmp_path / "failures.log", batch_size, total)


def test_fresh_run_has_every_batch_pending(tmp_path):
    manager = _manager(tmp_path)
    manager.load()
    assert manager.pending_offsets() == [0, 10, 20, 30]


def test_progress_survives_a_restart(tmp_path):
    first = _manager(tmp_path)
    first.mark_completed(0)
    first.mark_failed(10, RuntimeError("boom"))

    second = _manager(tmp_path)
    second.load()
    assert second.pending_offsets() == [10, 20, 30]
    assert second.pending_offsets(skip_failed=True) == [20, 30]
    assert second.pending_offsets(only_failed=True) == [10]
    assert "batch=1 rows=[10,20)  error=RuntimeError: boom" in (tmp_path / "failures.log").read_text()


def test_completing_a_failed_batch_clears_the_failure(tmp_path):
    manager = _manager(tmp_path)
    manager.mark_failed(10, RuntimeError("boom"))
    manager.mark_completed(10)
    assert json.loads((tmp_path / "state.json").read_text())["failed_batches"] == {}


def test_refuses_to_resume_with_a_different_batch_size(tmp_path):
    _manager(tmp_path, batch_size=10).mark_completed(0)
    with pytest.raises(ValueError, match="batch_size"):
        _manager(tmp_path, batch_size=20).load()


def test_refuses_to_resume_against_a_changed_dataset(tmp_path):
    _manager(tmp_path, total=35).mark_completed(0)
    with pytest.raises(ValueError, match="products"):
        _manager(tmp_path, total=40).load()
