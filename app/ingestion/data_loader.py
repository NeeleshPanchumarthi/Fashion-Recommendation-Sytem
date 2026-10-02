from pathlib import Path
from typing import List, Tuple, Optional

import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# Required columns
# ============================================================

METADATA_REQUIRED_COLUMNS = [
    "parent_asin",
    "title",
    "average_rating",
    "rating_number",
    "images",
]

REVIEWS_REQUIRED_COLUMNS = [
    "asin",
    "parent_asin",
    "rating",
    "title",
    "text",
    "user_id",
    "timestamp",
    "verified_purchase",
]


# ============================================================
# Schema validation
# ============================================================

def _validate_columns(
    available_columns: List[str],
    required: List[str],
    name: str
) -> None:
    missing = [col for col in required if col not in available_columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _get_parquet_columns(path: Path) -> List[str]:
    """Read only the Parquet schema; no dataset rows are loaded."""
    return pq.ParquetFile(path).schema_arrow.names


def validate_metadata(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")
    if p.suffix.lower() != ".parquet":
        raise ValueError("Validation currently expects metadata.parquet")

    columns = _get_parquet_columns(p)
    _validate_columns(columns, METADATA_REQUIRED_COLUMNS, "Metadata")
    print("✓ Metadata schema validated")
    print(f"  Rows in source file: {pq.ParquetFile(p).metadata.num_rows:,}")


def validate_reviews(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Reviews file not found: {path}")
    if p.suffix.lower() != ".parquet":
        raise ValueError("Validation currently expects reviews.parquet")

    columns = _get_parquet_columns(p)
    _validate_columns(columns, REVIEWS_REQUIRED_COLUMNS, "Reviews")
    print("✓ Reviews schema validated")
    print(f"  Rows in source file: {pq.ParquetFile(p).metadata.num_rows:,}")


def validate_parent_asin(
    metadata_path: str,
    reviews_path: str,
    batch_size: int = 100_000
) -> None:
    """Full relationship validation. Use this for production/full-dataset runs."""
    metadata_file = pq.ParquetFile(metadata_path)
    reviews_file = pq.ParquetFile(reviews_path)

    print("\nBuilding metadata parent_asin index...")
    metadata_table = metadata_file.read(columns=["parent_asin"])
    metadata_parent_asins = set(
        metadata_table.column("parent_asin").drop_null().to_pylist()
    )
    del metadata_table

    orphan_count = 0
    orphan_examples = []

    print("\nChecking review parent_asin values...")
    for batch in reviews_file.iter_batches(
        batch_size=batch_size,
        columns=["parent_asin"]
    ):
        review_parent_asins = (
            batch.column("parent_asin").drop_null().to_pylist()
        )
        for asin in review_parent_asins:
            if asin not in metadata_parent_asins:
                orphan_count += 1
                if len(orphan_examples) < 5:
                    orphan_examples.append(asin)

    if orphan_count > 0:
        raise ValueError(
            "Orphan reviews detected. "
            f"Total orphan reviews: {orphan_count:,}. "
            f"Examples: {orphan_examples}"
        )

    print("✓ parent_asin relationship validated")
    print("  No orphan reviews detected")


# ============================================================
# Efficient sample loading
# ============================================================

def _load_parquet_head(path: Path, nrows: int) -> pd.DataFrame:
    """
    Read only the first nrows from a Parquet file.

    Important: pd.read_parquet() has no nrows argument, so using it
    directly would read the complete file. iter_batches() stops after
    the requested sample and avoids loading the whole dataset.
    """
    parquet_file = pq.ParquetFile(path)
    batch_size = max(1, min(nrows, 10_000))

    batches = []
    rows_remaining = nrows

    for batch in parquet_file.iter_batches(batch_size=batch_size):
        batches.append(batch)
        rows_remaining -= batch.num_rows
        if rows_remaining <= 0:
            break

    if not batches:
        return pd.DataFrame()

    table = batches[0] if len(batches) == 1 else __import__("pyarrow").concat_tables(batches)

    # In case the last batch contains more rows than requested.
    table = table.slice(0, nrows)
    return table.to_pandas()


def load_metadata(path: str, nrows: Optional[int] = None) -> pd.DataFrame:
    """Load metadata, optionally limiting the number of rows."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    if p.suffix.lower() == ".parquet":
        df = (
            _load_parquet_head(p, nrows)
            if nrows is not None
            else pd.read_parquet(p)
        )
    elif p.suffix.lower() in {".jsonl", ".json"}:
        df = (
            pd.read_json(p, lines=True, nrows=nrows)
            if nrows is not None
            else pd.read_json(p, lines=True)
        )
    else:
        raise ValueError("Unsupported metadata file format. Use .parquet or .jsonl")

    _validate_columns(df.columns.tolist(), METADATA_REQUIRED_COLUMNS, "Metadata")
    return df


def load_reviews(path: str, nrows: Optional[int] = None) -> pd.DataFrame:
    """Load reviews, optionally limiting the number of rows."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Reviews file not found: {path}")

    if p.suffix.lower() == ".parquet":
        df = (
            _load_parquet_head(p, nrows)
            if nrows is not None
            else pd.read_parquet(p)
        )
    elif p.suffix.lower() in {".jsonl", ".json"}:
        df = (
            pd.read_json(p, lines=True, nrows=nrows)
            if nrows is not None
            else pd.read_json(p, lines=True)
        )
    else:
        raise ValueError("Unsupported reviews file format. Use .parquet or .jsonl")

    _validate_columns(df.columns.tolist(), REVIEWS_REQUIRED_COLUMNS, "Reviews")
    return df


# ============================================================
# Validation
# ============================================================

def validate_dataset(meta_path: str, reviews_path: str) -> None:
    """Perform complete validation of the full source datasets."""
    print("=" * 70)
    print("DATASET VALIDATION")
    print("=" * 70)

    print("\n[1/3] Validating metadata schema...")
    validate_metadata(meta_path)

    print("\n[2/3] Validating reviews schema...")
    validate_reviews(reviews_path)

    print("\n[3/3] Validating parent_asin relationship...")
    validate_parent_asin(meta_path, reviews_path)

    print("\n" + "=" * 70)
    print("✓ DATASET VALIDATION PASSED")
    print("=" * 70)


def load_dataset(
    meta_path: str,
    reviews_path: str,
    sample_rows: Optional[int] = 1000,
    validate: bool = False,
    validate_relationship: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the datasets.

    Default TEST MODE:
        - reads only the first 1,000 metadata rows
        - reads only the first 1,000 review rows
        - performs schema validation only
        - does NOT scan the complete source files

    FULL MODE:
        load_dataset(..., sample_rows=None, validate=True)

    FULL relationship validation can be explicitly enabled with
    validate_relationship=True.
    """
    if validate:
        validate_metadata(meta_path)
        validate_reviews(reviews_path)

        if validate_relationship:
            validate_parent_asin(meta_path, reviews_path)

    if sample_rows is not None:
        if sample_rows <= 0:
            raise ValueError("sample_rows must be greater than 0 or None")

        print(f"\nTEST MODE: loading only {sample_rows:,} rows from each dataset...")
    else:
        print("\nFULL MODE: loading complete datasets...")

    print("\nLoading metadata...")
    meta_df = load_metadata(meta_path, nrows=sample_rows)
    print(f"Metadata loaded: {len(meta_df):,} rows")

    print("\nLoading reviews...")
    rev_df = load_reviews(reviews_path, nrows=sample_rows)
    print(f"Reviews loaded: {len(rev_df):,} rows")

    return meta_df, rev_df
