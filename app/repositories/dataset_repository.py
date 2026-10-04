"""Read access to the raw product dataset (metadata.parquet + reviews.parquet).

Memory model (826,108 products / 2,500,939 reviews):

- metadata.parquet is a SINGLE Parquet row-group, so any reader must decode
  it as a unit; there is no way to stream it per batch without rewriting
  the file. It is loaded once, column-pruned to only the fields ingestion
  uses -- a few hundred MB rather than several GB.
- reviews.parquet never sits in memory whole. For each batch, DuckDB
  stream-scans it and semi-joins against just that batch's parent_asins,
  so only the matching rows are materialized.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import TracebackType
from typing import Optional

import duckdb
import pandas as pd
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

METADATA_REQUIRED_COLUMNS = ["parent_asin", "title", "average_rating", "rating_number", "images"]
REVIEWS_REQUIRED_COLUMNS = [
    "asin", "parent_asin", "rating", "title", "text", "user_id", "timestamp", "verified_purchase",
]

# Only these metadata columns are loaded -- the rest (features, videos,
# details, categories, bought_together, store, main_category) are unused
# downstream and would multiply the load cost.
METADATA_COLUMNS = ["parent_asin", "title", "average_rating", "rating_number", "images", "description", "price"]
REVIEW_COLUMNS = REVIEWS_REQUIRED_COLUMNS + ["helpful_vote"]


def _parquet_columns(path: Path) -> list[str]:
    """Read only the Parquet schema; no rows are loaded."""
    return pq.ParquetFile(path).schema_arrow.names


def _require_columns(available: list[str], required: list[str], name: str) -> None:
    missing = [col for col in required if col not in available]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _require_parquet(path: Path, name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{name} file not found: {path}")
    if path.suffix.lower() != ".parquet":
        raise ValueError(f"{name} must be a .parquet file: {path}")


class DatasetRepository:
    """Use as a context manager so the DuckDB connection is closed."""

    def __init__(self, metadata_path: Path, reviews_path: Path, duckdb_memory_limit: str = "2GB") -> None:
        self.metadata_path = Path(metadata_path)
        self.reviews_path = Path(reviews_path)
        self.duckdb_memory_limit = duckdb_memory_limit
        self._con: Optional[duckdb.DuckDBPyConnection] = None

    def __enter__(self) -> "DatasetRepository":
        return self

    def __exit__(self, exc_type: type | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        self.close()

    @property
    def _connection(self) -> duckdb.DuckDBPyConnection:
        if self._con is None:
            self._con = duckdb.connect()
            # A streaming filter + semi-join: should never need to spill to disk.
            self._con.execute(f"PRAGMA memory_limit='{self.duckdb_memory_limit}'")
        return self._con

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None

    # -- validation ---------------------------------------------------------

    def validate_schema(self) -> None:
        _require_parquet(self.metadata_path, "Metadata")
        _require_parquet(self.reviews_path, "Reviews")
        _require_columns(_parquet_columns(self.metadata_path), METADATA_REQUIRED_COLUMNS, "Metadata")
        _require_columns(_parquet_columns(self.reviews_path), REVIEWS_REQUIRED_COLUMNS, "Reviews")
        logger.info(
            "Dataset schema validated (metadata rows=%d, review rows=%d)",
            pq.ParquetFile(self.metadata_path).metadata.num_rows,
            pq.ParquetFile(self.reviews_path).metadata.num_rows,
        )

    def validate_relationships(self, batch_size: int = 100_000) -> None:
        """Fail if any review points at a product missing from metadata.
        Scans the full files, so it only runs when explicitly requested."""
        metadata_asins = set(
            pq.ParquetFile(self.metadata_path).read(columns=["parent_asin"])
            .column("parent_asin").drop_null().to_pylist()
        )
        orphan_count = 0
        examples: list[str] = []
        for batch in pq.ParquetFile(self.reviews_path).iter_batches(batch_size=batch_size, columns=["parent_asin"]):
            for asin in batch.column("parent_asin").drop_null().to_pylist():
                if asin not in metadata_asins:
                    orphan_count += 1
                    if len(examples) < 5:
                        examples.append(asin)
        if orphan_count:
            raise ValueError(
                f"Orphan reviews detected. Total orphan reviews: {orphan_count:,}. Examples: {examples}"
            )
        logger.info("parent_asin relationship validated: no orphan reviews")

    # -- loading ------------------------------------------------------------

    def load_metadata(self) -> pd.DataFrame:
        """All products, column-pruned (see module docstring)."""
        available = set(_parquet_columns(self.metadata_path))
        cols = ", ".join(c for c in METADATA_COLUMNS if c in available)
        logger.info("Loading metadata (columns: %s)", cols)
        df = self._connection.execute(f"SELECT {cols} FROM read_parquet(?)", [str(self.metadata_path)]).fetchdf()
        logger.info("Metadata loaded: %d products", len(df))
        return df

    def load_reviews_for(self, parent_asins: list[str]) -> pd.DataFrame:
        """Only the reviews of the given products, via a streaming semi-join."""
        available = set(_parquet_columns(self.reviews_path))
        cols = ", ".join(f"r.{c}" for c in REVIEW_COLUMNS if c in available)
        con = self._connection
        con.register("batch_asins", pd.DataFrame({"parent_asin": parent_asins}))
        try:
            return con.execute(
                f"SELECT {cols} FROM read_parquet(?) r SEMI JOIN batch_asins b ON r.parent_asin = b.parent_asin",
                [str(self.reviews_path)],
            ).fetchdf()
        finally:
            con.unregister("batch_asins")
