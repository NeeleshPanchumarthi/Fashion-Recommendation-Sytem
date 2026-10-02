from pathlib import Path
from typing import List, Tuple

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
    """
    Validate that all required columns exist.

    This operates on the Parquet schema instead of loading
    the entire dataset into Pandas.
    """

    missing = [
        col for col in required
        if col not in available_columns
    ]

    if missing:
        raise ValueError(
            f"{name} is missing required columns: {missing}"
        )


# ============================================================
# Get columns without loading entire dataset
# ============================================================

def _get_parquet_columns(path: Path) -> List[str]:
    """
    Read only the Parquet schema.

    This does NOT load the dataset into memory.
    """

    parquet_file = pq.ParquetFile(path)

    return parquet_file.schema_arrow.names


# ============================================================
# Validate metadata schema
# ============================================================

def validate_metadata(path: str) -> None:
    """
    Validate metadata Parquet schema without loading
    the entire dataset.
    """

    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {path}"
        )

    if p.suffix.lower() != ".parquet":
        raise ValueError(
            "Validation currently expects metadata.parquet"
        )

    columns = _get_parquet_columns(p)

    _validate_columns(
        columns,
        METADATA_REQUIRED_COLUMNS,
        "Metadata"
    )

    print("✓ Metadata schema validated")
    print(f"  Rows: {pq.ParquetFile(p).metadata.num_rows:,}")


# ============================================================
# Validate reviews schema
# ============================================================

def validate_reviews(path: str) -> None:
    """
    Validate reviews Parquet schema without loading
    the entire dataset.
    """

    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(
            f"Reviews file not found: {path}"
        )

    if p.suffix.lower() != ".parquet":
        raise ValueError(
            "Validation currently expects reviews.parquet"
        )

    columns = _get_parquet_columns(p)

    _validate_columns(
        columns,
        REVIEWS_REQUIRED_COLUMNS,
        "Reviews"
    )

    print("✓ Reviews schema validated")
    print(f"  Rows: {pq.ParquetFile(p).metadata.num_rows:,}")


# ============================================================
# Validate parent_asin relationship
# ============================================================

def validate_parent_asin(
    metadata_path: str,
    reviews_path: str,
    batch_size: int = 100_000
) -> None:
    """
    Validate that every review parent_asin exists in
    metadata.

    Reviews are processed in batches rather than loading
    the entire reviews dataset into Pandas.
    """

    metadata_file = pq.ParquetFile(metadata_path)
    reviews_file = pq.ParquetFile(reviews_path)

    # --------------------------------------------------------
    # Load ONLY parent_asin from metadata
    # --------------------------------------------------------

    print("\nBuilding metadata parent_asin index...")

    metadata_table = metadata_file.read(
        columns=["parent_asin"]
    )

    metadata_parent_asins = set(
        metadata_table
        .column("parent_asin")
        .drop_null()
        .to_pylist()
    )

    print(
        f"✓ Metadata parent_asin values: "
        f"{len(metadata_parent_asins):,}"
    )

    # Release Arrow table
    del metadata_table

    # --------------------------------------------------------
    # Process reviews in batches
    # --------------------------------------------------------

    orphan_count = 0
    orphan_examples = []

    print("\nChecking review parent_asin values...")

    for batch in reviews_file.iter_batches(
        batch_size=batch_size,
        columns=["parent_asin"]
    ):

        review_parent_asins = (
            batch.column("parent_asin")
            .drop_null()
            .to_pylist()
        )

        for asin in review_parent_asins:

            if asin not in metadata_parent_asins:

                orphan_count += 1

                if len(orphan_examples) < 5:
                    orphan_examples.append(asin)

        # Release batch
        del batch

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    if orphan_count > 0:

        raise ValueError(
            "Orphan reviews detected. "
            f"Total orphan reviews: {orphan_count:,}. "
            f"Examples: {orphan_examples}"
        )

    print("✓ parent_asin relationship validated")
    print("  No orphan reviews detected")


# ============================================================
# Full metadata loading
# ============================================================

def load_metadata(path: str) -> pd.DataFrame:
    """
    Load metadata into Pandas.

    NOTE:
    This intentionally loads the complete metadata DataFrame.
    Use only when the application actually needs the data.
    """

    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {path}"
        )

    if p.suffix.lower() == ".parquet":

        df = pd.read_parquet(p)

    elif p.suffix.lower() in {".jsonl", ".json"}:

        df = pd.read_json(
            p,
            lines=True
        )

    else:

        raise ValueError(
            "Unsupported metadata file format. "
            "Use .parquet or .jsonl"
        )

    _validate_columns(
        df.columns.tolist(),
        METADATA_REQUIRED_COLUMNS,
        "Metadata"
    )

    return df


# ============================================================
# Full review loading
# ============================================================

def load_reviews(path: str) -> pd.DataFrame:
    """
    Load reviews into Pandas.

    NOTE:
    This intentionally loads the complete reviews DataFrame.
    Use only when the application actually needs the data.
    """

    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(
            f"Reviews file not found: {path}"
        )

    if p.suffix.lower() == ".parquet":

        df = pd.read_parquet(p)

    elif p.suffix.lower() in {".jsonl", ".json"}:

        df = pd.read_json(
            p,
            lines=True
        )

    else:

        raise ValueError(
            "Unsupported reviews file format. "
            "Use .parquet or .jsonl"
        )

    _validate_columns(
        df.columns.tolist(),
        REVIEWS_REQUIRED_COLUMNS,
        "Reviews"
    )

    return df


# ============================================================
# Complete lightweight validation
# ============================================================

def validate_dataset(
    meta_path: str,
    reviews_path: str
) -> None:
    """
    Perform complete dataset validation without loading
    the entire metadata and reviews datasets into Pandas.
    """

    print("=" * 70)
    print("DATASET VALIDATION")
    print("=" * 70)

    print("\n[1/3] Validating metadata schema...")

    validate_metadata(meta_path)

    print("\n[2/3] Validating reviews schema...")

    validate_reviews(reviews_path)

    print("\n[3/3] Validating parent_asin relationship...")

    validate_parent_asin(
        meta_path,
        reviews_path
    )

    print("\n" + "=" * 70)
    print("✓ DATASET VALIDATION PASSED")
    print("=" * 70)


# ============================================================
# Full dataset loading
# ============================================================

def load_dataset(
    meta_path: str,
    reviews_path: str,
    validate: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the complete metadata and reviews datasets.

    WARNING:
    This loads both datasets into RAM.

    Use validate_dataset() separately when you only need
    validation.
    """

    if validate:

        validate_dataset(
            meta_path,
            reviews_path
        )

    print("\nLoading metadata into Pandas...")

    meta_df = load_metadata(
        meta_path
    )

    print(
        f"✓ Metadata loaded: "
        f"{len(meta_df):,} rows"
    )

    print("\nLoading reviews into Pandas...")

    rev_df = load_reviews(
        reviews_path
    )

    print(
        f"✓ Reviews loaded: "
        f"{len(rev_df):,} rows"
    )

    return meta_df, rev_df