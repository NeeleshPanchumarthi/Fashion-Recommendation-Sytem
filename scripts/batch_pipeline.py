"""Production batch ingestion pipeline — memory-bounded, resumable.

Why this exists
----------------
`app/ingestion/pipeline.py` loads the whole dataset into pandas DataFrames
at once. That's fine for dev-mode samples, but on a 16 GB laptop with no
dedicated GPU it is not safe to run against the full catalog (826,108
products / 2,500,939 reviews): a single BERT sentiment pass + embedding
pass + Pinecone upsert over the whole in-memory frame has no bound on
peak RAM.

This script re-runs the SAME pipeline steps (review scoring/selection,
local BERT sentiment, title-based attribute extraction, embeddings,
Pinecone upsert) but in fixed-size batches of products:

    Load batch -> Process -> Sentiment -> Embed -> Upsert -> Release -> Next

Two notes on your machine's actual constraints (12th Gen i7-1255U, 16 GB
RAM / 15.7 GB usable, no dedicated GPU, ~650 MB free disk at time of
writing):

1. `data/metadata.parquet` was written as a SINGLE Parquet row-group
   (826,108 rows, 1 group). That's a property of the file: any reader
   (pandas, pyarrow, DuckDB) must decode that row-group as a unit on
   first read -- there is no way to stream it in true per-batch chunks
   without first rewriting the file with smaller row-groups, which this
   script deliberately avoids given how little free disk you have. So
   metadata is loaded ONCE, column-pruned to only the 7 fields the
   pipeline actually uses (dropping heavy unused columns like `features`,
   `videos`, `details`, `categories`, `bought_together`, `store`,
   `main_category`), and batches are sliced from that single in-memory
   frame. This is a few hundred MB, not multiple GB -- not the risk.

2. `data/reviews.parquet` (2,500,939 rows, 3 row-groups, 378 MB) IS the
   expensive one, and it genuinely never needs to sit in memory whole.
   For each batch this script uses DuckDB (already in requirements.txt)
   to stream-scan reviews.parquet and semi-join against just that
   batch's parent_asin set, so only the matching rows for ~batch_size
   products are ever materialized.

Everything expensive -- BERT sentiment classification over the selected
reviews, embedding generation, and the Pinecone upsert -- happens per
batch, and the batch's DataFrames are explicitly released before the
next batch loads. The sentiment model and the embedding model are the
one exception: they're loaded lazily on first use and kept resident for
the rest of the run (both are already singletons in
sentiment_extractor.py / embedding.py) because reloading multi-hundred-MB
model weights every batch would be pure waste, not a memory saving.

Resumability
------------
Batches are defined by a fixed row-offset range into metadata
(batch 0 = rows [0, batch_size), batch 1 = [batch_size, 2*batch_size), ...).
After a batch's sentiment + embeddings + Pinecone upsert all complete
without error, its offset is appended to a small JSON state file and
flushed to disk immediately -- so a crash mid-run never loses already
completed batches, and the in-flight batch (not yet marked done) simply
reruns next time. Re-running is always safe: Pinecone upsert is
idempotent per vector ID, so even a batch that partially upserted before
failing just gets overwritten with identical data, never duplicated.

A batch that raises an exception (network blip, Pinecone timeout, a bad
row, etc.) is logged with its error and the run CONTINUES to the next
batch rather than aborting -- per-batch failures are expected in a
multi-hour unattended run. Failed batches are retried automatically on
the next invocation (together with any batches never attempted), unless
you pass --skip-failed.

Usage
-----
    # Estimate batch count / sanity-check without processing anything
    python scripts/batch_pipeline.py --dry-run

    # Small real test: first 2 batches only (good before committing to
    # a multi-hour run)
    python scripts/batch_pipeline.py --max-batches 2

    # Full production run (safe to Ctrl-C and rerun; it resumes)
    python scripts/batch_pipeline.py

    # Only retry batches that failed last time
    python scripts/batch_pipeline.py --only-failed

State / log files (tiny -- a few KB, not a disk concern):
    data/cache/batch_pipeline_state.json     machine-readable progress
    data/cache/batch_pipeline_failures.log   human-readable failure log
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from app.ingestion.pipeline import (  # noqa: E402
    _apply_attribute_extractors,
    _build_combined_text,
)
from app.ingestion.review_processor import (  # noqa: E402
    aggregate_product_sentiment,
    build_review_highlights,
    run_sentiment_pipeline,
    score_reviews,
    select_reviews,
)
from app.ingestion.vector_store import upsert_vectors  # noqa: E402

try:
    import psutil
    _HAVE_PSUTIL = True
except ImportError:
    _HAVE_PSUTIL = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_METADATA_PATH = "data/metadata.parquet"
DEFAULT_REVIEWS_PATH = "data/reviews.parquet"
DEFAULT_BATCH_SIZE = 15_000  # products per batch; see docstring for reasoning
DEFAULT_STATE_PATH = Path("data/cache/batch_pipeline_state.json")
DEFAULT_FAILURE_LOG_PATH = Path("data/cache/batch_pipeline_failures.log")

# Only these metadata columns are ever loaded -- the rest (features, videos,
# details, categories, bought_together, store, main_category) are not used
# anywhere downstream and would multiply the one-time metadata load cost
# for no benefit.
METADATA_COLUMNS = [
    "parent_asin",
    "title",
    "average_rating",
    "rating_number",
    "images",
    "description",
    "price",
]

REVIEW_COLUMNS = [
    "asin",
    "parent_asin",
    "rating",
    "title",
    "text",
    "user_id",
    "timestamp",
    "verified_purchase",
    "helpful_vote",
]

UPSERT_RETRIES = 3
UPSERT_BACKOFF_SECONDS = 2  # doubles each retry: 2s, 4s, 8s

# DuckDB memory cap for the per-batch reviews scan. The query itself is a
# simple streaming filter + semi-join (no big sort/shuffle), so this should
# never need to spill to disk -- which matters given how little free disk
# this machine has right now.
DUCKDB_MEMORY_LIMIT = "2GB"


# ---------------------------------------------------------------------------
# Memory / progress logging
# ---------------------------------------------------------------------------

def _rss_mb() -> Optional[float]:
    if not _HAVE_PSUTIL:
        return None
    return psutil.Process().memory_info().rss / (1024 * 1024)


def _available_mb() -> Optional[float]:
    if not _HAVE_PSUTIL:
        return None
    return psutil.virtual_memory().available / (1024 * 1024)


def _log_memory(tag: str) -> None:
    rss = _rss_mb()
    avail = _available_mb()
    if rss is None:
        logger.info("[%s] (psutil not installed -- memory stats unavailable)", tag)
        return
    logger.info("[%s] process RSS: %.0f MB | system available: %.0f MB", tag, rss, avail)


# ---------------------------------------------------------------------------
# State (checkpoint) handling
# ---------------------------------------------------------------------------

def _load_state(state_path: Path, batch_size: int, total_products: int) -> dict:
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state.get("batch_size") != batch_size:
            raise ValueError(
                f"Checkpoint at {state_path} was created with batch_size="
                f"{state.get('batch_size')}, but this run requested "
                f"batch_size={batch_size}. Changing batch size mid-run would "
                "make batch offsets inconsistent. Either rerun with "
                f"--batch-size {state.get('batch_size')}, or delete the "
                "checkpoint file to start a fresh run with the new size."
            )
        if state.get("total_products") != total_products:
            raise ValueError(
                f"Checkpoint at {state_path} was created against a dataset "
                f"of {state.get('total_products')} products, but this run "
                f"sees {total_products}. Has data/metadata.parquet changed? "
                "Delete the checkpoint to start fresh if that's expected."
            )
        logger.info(
            "Resuming from checkpoint: %d batches already completed, %d previously failed",
            len(state.get("completed_batches", [])),
            len(state.get("failed_batches", {})),
        )
        return state

    return {
        "batch_size": batch_size,
        "total_products": total_products,
        "completed_batches": [],
        "failed_batches": {},
    }


def _save_state(state: dict, state_path: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(state_path)


def _log_failure(failure_log_path: Path, batch_id: int, start: int, end: int, error: Exception) -> None:
    failure_log_path.parent.mkdir(parents=True, exist_ok=True)
    with failure_log_path.open("a") as f:
        f.write(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}  batch={batch_id} "
            f"rows=[{start},{end})  error={type(error).__name__}: {error}\n"
        )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_metadata(meta_path: str) -> pd.DataFrame:
    """Load metadata once, column-pruned. See module docstring: the file is
    a single Parquet row-group, so a full decode happens on first read no
    matter which engine reads it or how few rows are requested -- pruning
    to only the needed columns is what actually keeps this cheap."""
    logger.info("Loading metadata (column-pruned: %s)...", METADATA_COLUMNS)
    con = duckdb.connect()
    con.execute(f"PRAGMA memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    cols = ", ".join(METADATA_COLUMNS)
    df = con.execute(f"SELECT {cols} FROM read_parquet('{meta_path}')").fetchdf()
    con.close()
    logger.info("Metadata loaded: %d rows", len(df))
    return df


def _load_reviews_for_batch(con: duckdb.DuckDBPyConnection, reviews_path: str, asins: list) -> pd.DataFrame:
    """Stream-scan reviews.parquet and return only rows whose parent_asin is
    in this batch. DuckDB performs this as a streaming semi-join -- the full
    2.5M-row file is never materialized at once, only the matching subset."""
    asin_df = pd.DataFrame({"parent_asin": asins})
    con.register("batch_asins", asin_df)
    cols = ", ".join(f"r.{c}" for c in REVIEW_COLUMNS)
    query = f"""
        SELECT {cols}
        FROM read_parquet('{reviews_path}') r
        SEMI JOIN batch_asins b ON r.parent_asin = b.parent_asin
    """
    result = con.execute(query).fetchdf()
    con.unregister("batch_asins")
    return result


# ---------------------------------------------------------------------------
# Per-batch pipeline steps (mirrors app/ingestion/pipeline.py build_pipeline,
# but operating on one batch's slice instead of the whole dataset)
# ---------------------------------------------------------------------------

def _process_batch(meta_batch: pd.DataFrame, rev_batch: pd.DataFrame) -> pd.DataFrame:
    if rev_batch.empty:
        highlights_df = pd.DataFrame(columns=["parent_asin", "review_highlights"])
        sentiment_df = pd.DataFrame(columns=["parent_asin", "overall_sentiment"])
    else:
        scored = score_reviews(rev_batch)
        selected = select_reviews(scored)
        with_sentiment = run_sentiment_pipeline(selected)
        highlights_df = build_review_highlights(with_sentiment)
        sentiment_df = aggregate_product_sentiment(with_sentiment)

    meta = meta_batch.merge(sentiment_df, on="parent_asin", how="left")
    meta = meta.merge(highlights_df, on="parent_asin", how="left")

    meta["overall_sentiment"] = meta["overall_sentiment"].fillna("neutral")
    meta["review_highlights"] = meta["review_highlights"].apply(
        lambda v: v if isinstance(v, list) else []
    )

    meta = _apply_attribute_extractors(meta)
    meta["gender"] = meta["gender"].fillna("not specified")
    meta["color"] = meta["color"].fillna("not mentioned")
    meta["style"] = meta["style"].fillna("not specified")
    meta["category"] = meta["category"].fillna("not distributed")
    meta["description"] = meta.get(
        "description", pd.Series("no description", index=meta.index)
    ).fillna("no description")

    meta["combined_text"] = meta.apply(_build_combined_text, axis=1)

    return meta


def _upsert_with_retry(meta: pd.DataFrame) -> None:
    last_exc = None
    for attempt in range(1, UPSERT_RETRIES + 1):
        try:
            upsert_vectors(meta, id_column="parent_asin")
            return
        except Exception as exc:  # noqa: BLE001 -- must catch broadly here
            last_exc = exc
            if attempt < UPSERT_RETRIES:
                wait = UPSERT_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Pinecone upsert failed (attempt %d/%d): %s -- retrying in %ds",
                    attempt, UPSERT_RETRIES, exc, wait,
                )
                time.sleep(wait)
    raise last_exc


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------

def run(
    meta_path: str = DEFAULT_METADATA_PATH,
    reviews_path: str = DEFAULT_REVIEWS_PATH,
    batch_size: int = DEFAULT_BATCH_SIZE,
    state_path: Path = DEFAULT_STATE_PATH,
    failure_log_path: Path = DEFAULT_FAILURE_LOG_PATH,
    max_batches: Optional[int] = None,
    only_failed: bool = False,
    skip_failed: bool = False,
    stop_on_error: bool = False,
    dry_run: bool = False,
) -> None:
    meta_df = _load_metadata(meta_path)
    total_products = len(meta_df)
    _log_memory("after metadata load")

    offsets = list(range(0, total_products, batch_size))
    logger.info(
        "Dataset: %d products, batch_size=%d -> %d batches",
        total_products, batch_size, len(offsets),
    )

    if dry_run:
        print(f"Would process {len(offsets)} batches of up to {batch_size} products each "
              f"over {total_products} total products.")
        return

    state = _load_state(state_path, batch_size, total_products)
    completed = set(state["completed_batches"])
    failed = state["failed_batches"]

    if only_failed:
        todo_offsets = [int(o) for o in failed.keys()]
    else:
        todo_offsets = [o for o in offsets if o not in completed]
        if skip_failed:
            todo_offsets = [o for o in todo_offsets if str(o) not in failed]

    if max_batches is not None:
        todo_offsets = todo_offsets[:max_batches]

    if not todo_offsets:
        logger.info("Nothing to do -- all batches already completed. "
                     "(Use --only-failed or delete the checkpoint to reprocess.)")
        return

    logger.info("%d batches to process this run", len(todo_offsets))

    con = duckdb.connect()
    con.execute(f"PRAGMA memory_limit='{DUCKDB_MEMORY_LIMIT}'")

    run_started = time.time()
    n_ok = 0
    n_fail = 0

    try:
        for i, start in enumerate(todo_offsets, 1):
            end = min(start + batch_size, total_products)
            batch_id = start // batch_size
            batch_started = time.time()
            meta_batch = None
            rev_batch = None
            processed = None

            logger.info(
                "=== Batch %d/%d (id=%d, rows [%d, %d)) ===",
                i, len(todo_offsets), batch_id, start, end,
            )

            try:
                meta_batch = meta_df.iloc[start:end].copy()
                asins = meta_batch["parent_asin"].dropna().tolist()

                rev_batch = _load_reviews_for_batch(con, reviews_path, asins)
                logger.info("Batch %d: %d products, %d matching reviews", batch_id, len(meta_batch), len(rev_batch))

                processed = _process_batch(meta_batch, rev_batch)

                sentiment_counts = processed["overall_sentiment"].value_counts().to_dict()
                logger.info("Batch %d: sentiment distribution %s", batch_id, sentiment_counts)

                _upsert_with_retry(processed)

                completed.add(start)
                failed.pop(str(start), None)
                state["completed_batches"] = sorted(completed)
                state["failed_batches"] = failed
                _save_state(state, state_path)

                n_ok += 1
                elapsed = time.time() - batch_started
                logger.info("Batch %d done in %.1fs", batch_id, elapsed)

            except Exception as exc:  # noqa: BLE001 -- batch-level isolation is the point
                n_fail += 1
                logger.error("Batch %d FAILED: %s", batch_id, exc, exc_info=True)
                failed[str(start)] = f"{type(exc).__name__}: {exc}"
                state["failed_batches"] = failed
                _save_state(state, state_path)
                _log_failure(failure_log_path, batch_id, start, end, exc)

                if stop_on_error:
                    logger.error("--stop-on-error set; halting run.")
                    raise

            finally:
                # Release this batch's data before loading the next one.
                meta_batch = None
                rev_batch = None
                processed = None
                gc.collect()
                _log_memory(f"after batch {batch_id}")

    except KeyboardInterrupt:
        logger.warning(
            "Interrupted by user. %d batches completed and checkpointed so far "
            "this run (%d total). Safe to rerun the same command to resume.",
            n_ok, len(completed),
        )
        con.close()
        return

    con.close()

    total_elapsed = time.time() - run_started
    logger.info(
        "Run finished in %.1fs -- %d batches OK, %d batches FAILED this run "
        "(%d total completed, %d total still failed).",
        total_elapsed, n_ok, n_fail, len(completed), len(failed),
    )

    if failed:
        print("\n" + "=" * 70)
        print(f"{len(failed)} batch(es) failed and need attention:")
        for offset, err in sorted(failed.items(), key=lambda kv: int(kv[0])):
            batch_id = int(offset) // batch_size
            print(f"  batch {batch_id} (rows starting {offset}): {err}")
        print(f"\nFull details in {failure_log_path}")
        print("Rerun the same command to retry them (along with any never-attempted "
              "batches), or pass --only-failed to retry just these.")
        print("=" * 70)

    if len(completed) == len(offsets) and not failed:
        print(f"\nAll {len(offsets)} batches completed successfully. "
              f"{total_products} products processed and upserted to Pinecone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Memory-bounded, resumable batch ingestion pipeline")
    parser.add_argument("--metadata-path", default=DEFAULT_METADATA_PATH)
    parser.add_argument("--reviews-path", default=DEFAULT_REVIEWS_PATH)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                         help=f"Products per batch (default {DEFAULT_BATCH_SIZE}). "
                              "Lower this if you see memory pressure; raise it to reduce "
                              "the number of reviews.parquet scans (fewer, bigger batches).")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--failure-log-path", type=Path, default=DEFAULT_FAILURE_LOG_PATH)
    parser.add_argument("--max-batches", type=int, default=None,
                         help="Process at most N batches this run (for testing a small slice).")
    parser.add_argument("--only-failed", action="store_true",
                         help="Only retry batches that failed on a previous run.")
    parser.add_argument("--skip-failed", action="store_true",
                         help="Don't retry previously-failed batches this run (only do never-attempted ones).")
    parser.add_argument("--stop-on-error", action="store_true",
                         help="Abort the whole run on the first batch failure, instead of logging and continuing.")
    parser.add_argument("--dry-run", action="store_true",
                         help="Just report how many batches would be processed, then exit.")
    args = parser.parse_args()

    if not _HAVE_PSUTIL:
        logger.warning("psutil is not installed -- memory logging will be skipped. "
                        "Install with: pip install psutil")

    run(
        meta_path=args.metadata_path,
        reviews_path=args.reviews_path,
        batch_size=args.batch_size,
        state_path=args.state_path,
        failure_log_path=args.failure_log_path,
        max_batches=args.max_batches,
        only_failed=args.only_failed,
        skip_failed=args.skip_failed,
        stop_on_error=args.stop_on_error,
        dry_run=args.dry_run,
    )
