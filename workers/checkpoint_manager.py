"""Resumable ingestion progress.

Batches are fixed row-offset ranges into the metadata (batch 0 = rows
[0, batch_size), batch 1 = [batch_size, 2*batch_size), ...). A batch is
recorded as completed only after its vectors are upserted, and the state
file is rewritten atomically after every batch -- so a crash never loses
completed batches and the in-flight batch simply reruns next time.
Re-running is safe: upserts are idempotent per product ID.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(self, state_path: Path, failure_log_path: Path, batch_size: int, total_products: int) -> None:
        self.state_path = Path(state_path)
        self.failure_log_path = Path(failure_log_path)
        self.batch_size = batch_size
        self.total_products = total_products
        self.completed: set[int] = set()
        self.failed: dict[str, str] = {}

    def load(self) -> None:
        """Load prior progress, refusing to resume an incompatible run."""
        if not self.state_path.exists():
            return
        state = json.loads(self.state_path.read_text())
        if state.get("batch_size") != self.batch_size:
            raise ValueError(
                f"Checkpoint at {self.state_path} was created with batch_size={state.get('batch_size')}, "
                f"but this run requested batch_size={self.batch_size}. Changing batch size mid-run would "
                f"make batch offsets inconsistent. Rerun with --batch-size {state.get('batch_size')}, "
                "or delete the checkpoint file to start fresh."
            )
        if state.get("total_products") != self.total_products:
            raise ValueError(
                f"Checkpoint at {self.state_path} was created against {state.get('total_products')} products, "
                f"but this run sees {self.total_products}. Has the metadata file changed? "
                "Delete the checkpoint to start fresh if that's expected."
            )
        self.completed = set(state.get("completed_batches", []))
        self.failed = dict(state.get("failed_batches", {}))
        logger.info(
            "Resuming from checkpoint: %d batches completed, %d previously failed",
            len(self.completed), len(self.failed),
        )

    def pending_offsets(self, only_failed: bool = False, skip_failed: bool = False) -> list[int]:
        if only_failed:
            return sorted(int(o) for o in self.failed)
        offsets = [o for o in range(0, self.total_products, self.batch_size) if o not in self.completed]
        if skip_failed:
            offsets = [o for o in offsets if str(o) not in self.failed]
        return offsets

    def mark_completed(self, offset: int) -> None:
        self.completed.add(offset)
        self.failed.pop(str(offset), None)
        self._save()

    def mark_failed(self, offset: int, error: Exception) -> None:
        self.failed[str(offset)] = f"{type(error).__name__}: {error}"
        self._save()
        end = min(offset + self.batch_size, self.total_products)
        self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.failure_log_path.open("a") as f:
            f.write(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}  batch={offset // self.batch_size} "
                f"rows=[{offset},{end})  error={type(error).__name__}: {error}\n"
            )

    def _save(self) -> None:
        state = {
            "batch_size": self.batch_size,
            "total_products": self.total_products,
            "completed_batches": sorted(self.completed),
            "failed_batches": self.failed,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(self.state_path)
