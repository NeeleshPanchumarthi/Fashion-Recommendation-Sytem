import pytest
import pandas as pd
from pathlib import Path
from app.ingestion.data_loader import load_dataset, load_metadata, load_reviews

# Helper to create a parquet file from a DataFrame
def _write_parquet(df: pd.DataFrame, path: Path):
    df.to_parquet(path, engine="pyarrow")

def test_load_valid_dataset(tmp_path):
    # Prepare minimal valid metadata
    meta = pd.DataFrame({
        "parent_asin": ["A1", "A2"],
        "title": ["Red Shirt", "Blue Jeans"],
        "average_rating": [4.5, 4.0],
        "rating_number": [10, 8],
        "image_url": ["http://img1", "http://img2"],
    })
    meta_path = tmp_path / "meta.parquet"
    _write_parquet(meta, meta_path)

    # Prepare matching reviews
    reviews = pd.DataFrame({
        "asin": ["B1", "B2"],
        "parent_asin": ["A1", "A2"],
        "rating": [5, 4],
        "title": ["Great!", "Nice"],
        "text": ["Love it", "Fit well"],
        "user_id": ["U1", "U2"],
        "timestamp": ["2023-01-01", "2023-01-02"],
        "verified_purchase": [True, True],
    })
    rev_path = tmp_path / "reviews.parquet"
    _write_parquet(reviews, rev_path)

    meta_df, rev_df = load_dataset(str(meta_path), str(rev_path))
    assert len(meta_df) == 2
    assert len(rev_df) == 2
    # Ensure required columns are present
    assert "parent_asin" in meta_df.columns
    assert "parent_asin" in rev_df.columns

def test_missing_required_columns(tmp_path):
    # Metadata missing 'title'
    meta = pd.DataFrame({
        "parent_asin": ["A1"],
        "average_rating": [4.5],
        "rating_number": [10],
        "image_url": ["http://img1"],
    })
    meta_path = tmp_path / "meta.parquet"
    _write_parquet(meta, meta_path)

    reviews = pd.DataFrame({
        "asin": ["B1"],
        "parent_asin": ["A1"],
        "rating": [5],
        "title": ["Great!"],
        "text": ["Love it"],
        "user_id": ["U1"],
        "timestamp": ["2023-01-01"],
        "verified_purchase": [True],
    })
    rev_path = tmp_path / "reviews.parquet"
    _write_parquet(reviews, rev_path)

    with pytest.raises(ValueError) as exc:
        load_dataset(str(meta_path), str(rev_path))
    assert "Metadata is missing required columns" in str(exc.value)

def test_orphan_reviews(tmp_path):
    # Metadata has one product
    meta = pd.DataFrame({
        "parent_asin": ["A1"],
        "title": ["Red Shirt"],
        "average_rating": [4.5],
        "rating_number": [10],
        "image_url": ["http://img1"],
    })
    meta_path = tmp_path / "meta.parquet"
    _write_parquet(meta, meta_path)

    # Review references a non‑existent parent_asin
    reviews = pd.DataFrame({
        "asin": ["B1"],
        "parent_asin": ["A2"],
        "rating": [5],
        "title": ["Great!"],
        "text": ["Love it"],
        "user_id": ["U1"],
        "timestamp": ["2023-01-01"],
        "verified_purchase": [True],
    })
    rev_path = tmp_path / "reviews.parquet"
    _write_parquet(reviews, rev_path)

    with pytest.raises(ValueError) as exc:
        load_dataset(str(meta_path), str(rev_path))
    assert "Orphan reviews detected" in str(exc.value)

def test_empty_dataset(tmp_path):
    # Empty metadata and reviews files
    meta_path = tmp_path / "meta.parquet"
    pd.DataFrame(columns=["parent_asin", "title", "average_rating", "rating_number", "image_url"]).to_parquet(meta_path)
    rev_path = tmp_path / "reviews.parquet"
    pd.DataFrame(columns=["asin", "parent_asin", "rating", "title", "text", "user_id", "timestamp", "verified_purchase"]).to_parquet(rev_path)

    meta_df, rev_df = load_dataset(str(meta_path), str(rev_path))
    assert meta_df.empty
    assert rev_df.empty
