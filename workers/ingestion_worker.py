"""Offline ingestion worker: memory-bounded, resumable batch indexing.

Runs as its own process (python -m workers.ingestion_worker), never inside
the API. Each batch of products goes:

    load batch → review analysis → enrichment → embeddings → upsert
      → checkpoint → release memory → next batch

Only one batch's reviews are ever in memory (see
app/repositories/dataset_repository.py for the memory model). A failing
batch is logged and recorded, and the run continues; failed batches are
retried on the next run unless --skip-failed is passed. Ctrl-C is safe:
rerun the same command to resume.

Usage
-----
    python -m workers.ingestion_worker --dry-run          # count batches only
    python -m workers.ingestion_worker --max-batches 2    # small real test
    python -m workers.ingestion_worker                    # full run (resumable)
    python -m workers.ingestion_worker --only-failed      # retry failures
"""

from __future__ import annotations

import argparse
import gc
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.clients.embedding_client import EmbeddingClient
from app.clients.sentiment_client import SentimentClient
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.dependencies import build_vector_repository
from app.repositories.dataset_repository import DatasetRepository
from app.services.review_analysis_service import ReviewAnalysisService

from .batch_processor import BatchProcessor
from .checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:  # optional: only used for memory logging
    psutil = None


@dataclass
class WorkerOptions:
    metadata_path: Path
    reviews_path: Path
    batch_size: int
    checkpoint_path: Path
    failure_log_path: Path
    max_batches: Optional[int] = None
    only_failed: bool = False
    skip_failed: bool = False
    stop_on_error: bool = False
    dry_run: bool = False
    validate: bool = False
    validate_relationships: bool = False


def _log_memory(tag: str) -> None:
    if psutil is None:
        return
    rss = psutil.Process().memory_info().rss / 2**20
    available = psutil.virtual_memory().available / 2**20
    logger.info("[%s] process RSS: %.0f MB | system available: %.0f MB", tag, rss, available)


def build_processor(settings: Settings) -> BatchProcessor:
    """Real clients; also creates the vector index if it doesn't exist."""
    embedder = EmbeddingClient(settings.EMBEDDING_MODEL)
    vectors = build_vector_repository(settings)
    vectors.ensure_index(embedder.dimension)
    return BatchProcessor(
        reviews=ReviewAnalysisService(SentimentClient(settings.SENTIMENT_MODEL, settings.SENTIMENT_BATCH_SIZE)),
        embedder=embedder,
        vectors=vectors,
        upsert_retries=settings.UPSERT_RETRIES,
    )


def run(
    options: WorkerOptions,
    settings: Settings,
    processor_factory: Callable[[Settings], BatchProcessor] = build_processor,
) -> int:
    """Run ingestion. Returns a process exit code (0 = no failed batches)."""
    with DatasetRepository(options.metadata_path, options.reviews_path, settings.DUCKDB_MEMORY_LIMIT) as dataset:
        if options.validate or options.validate_relationships:
            dataset.validate_schema()
        if options.validate_relationships:
            dataset.validate_relationships()

        meta_df = dataset.load_metadata()
        total = len(meta_df)
        _log_memory("after metadata load")

        checkpoints = CheckpointManager(options.checkpoint_path, options.failure_log_path, options.batch_size, total)
        all_batches = (total + options.batch_size - 1) // options.batch_size
        logger.info("Dataset: %d products, batch_size=%d -> %d batches", total, options.batch_size, all_batches)

        if options.dry_run:
            logger.info("Dry run: would process %d batches; exiting", all_batches)
            return 0

        checkpoints.load()
        todo = checkpoints.pending_offsets(options.only_failed, options.skip_failed)
        if options.max_batches is not None:
            todo = todo[: options.max_batches]
        if not todo:
            logger.info("Nothing to do: all batches completed (use --only-failed or delete the checkpoint to redo)")
            return 0

        processor = processor_factory(settings)

        logger.info("%d batches to process this run", len(todo))
        run_started = time.time()
        n_ok = n_fail = 0

        try:
            for i, start in enumerate(todo, 1):
                end = min(start + options.batch_size, total)
                batch_id = start // options.batch_size
                batch_started = time.time()
                logger.info("Batch %d/%d started (id=%d, rows [%d, %d))", i, len(todo), batch_id, start, end)
                try:
                    meta_batch = meta_df.iloc[start:end].copy()
                    rev_batch = dataset.load_reviews_for(meta_batch["parent_asin"].dropna().tolist())
                    logger.info("Batch %d loaded: %d products, %d reviews", batch_id, len(meta_batch), len(rev_batch))

                    result = processor.process(batch_id, meta_batch, rev_batch)
                    logger.info("Batch %d sentiment distribution: %s", batch_id, result.sentiment_counts)

                    checkpoints.mark_completed(start)
                    logger.info("Batch %d checkpoint saved", batch_id)
                    n_ok += 1
                    logger.info("Batch %d done in %.1fs (%d vectors)", batch_id, time.time() - batch_started, result.vectors)
                except Exception as exc:  # noqa: BLE001 -- batch-level isolation is the point
                    n_fail += 1
                    logger.error("Batch %d FAILED: %s", batch_id, exc, exc_info=True)
                    checkpoints.mark_failed(start, exc)
                    if options.stop_on_error:
                        logger.error("--stop-on-error set; halting run")
                        raise
                finally:
                    meta_batch = rev_batch = None
                    gc.collect()
                    _log_memory(f"after batch {batch_id}")
        except KeyboardInterrupt:
            logger.warning(
                "Interrupted. %d batches completed this run (%d total). Rerun the same command to resume.",
                n_ok, len(checkpoints.completed),
            )
            return 130

        logger.info(
            "Run finished in %.1fs: %d batches OK, %d FAILED this run (%d completed in total, %d still failed)",
            time.time() - run_started, n_ok, n_fail, len(checkpoints.completed), len(checkpoints.failed),
        )
        for offset, error in sorted(checkpoints.failed.items(), key=lambda kv: int(kv[0])):
            logger.error("Still failed: batch %d (rows from %s): %s", int(offset) // options.batch_size, offset, error)
        if checkpoints.failed:
            logger.error("Details in %s. Rerun to retry, or pass --only-failed.", options.failure_log_path)
        return 1 if checkpoints.failed else 0


def parse_args(argv: Optional[list[str]], settings: Settings) -> WorkerOptions:
    parser = argparse.ArgumentParser(description="Memory-bounded, resumable ingestion worker")
    parser.add_argument("--metadata-path", type=Path, default=settings.METADATA_PATH)
    parser.add_argument("--reviews-path", type=Path, default=settings.REVIEWS_PATH)
    parser.add_argument("--batch-size", type=int, default=settings.BATCH_SIZE,
                        help="Products per batch. Lower it under memory pressure.")
    parser.add_argument("--checkpoint-path", type=Path, default=settings.CHECKPOINT_PATH)
    parser.add_argument("--failure-log-path", type=Path, default=settings.FAILURE_LOG_PATH)
    parser.add_argument("--max-batches", type=int, default=None, help="Process at most N batches this run.")
    parser.add_argument("--only-failed", action="store_true", help="Only retry batches that failed before.")
    parser.add_argument("--skip-failed", action="store_true", help="Don't retry previously failed batches.")
    parser.add_argument("--stop-on-error", action="store_true", help="Abort on the first failed batch.")
    parser.add_argument("--dry-run", action="store_true", help="Report the batch count and exit.")
    parser.add_argument("--validate", action="store_true", help="Validate dataset schemas first.")
    parser.add_argument("--validate-relationships", action="store_true",
                        help="Also check every review's product exists (scans the full files).")
    args = parser.parse_args(argv)
    return WorkerOptions(**vars(args))


def main(argv: Optional[list[str]] = None) -> int:
    settings = get_settings()
    configure_logging(f"{settings.SERVICE_NAME}-worker", settings.LOG_LEVEL)
    if psutil is None:
        logger.warning("psutil is not installed: memory logging is skipped")
    return run(parse_args(argv, settings), settings)


if __name__ == "__main__":
    sys.exit(main())
