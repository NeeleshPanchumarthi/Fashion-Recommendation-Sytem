import pandas as pd
import pytest

from app.repositories.dataset_repository import DatasetRepository


def _meta(**overrides):
    data = {
        "parent_asin": ["A1", "A2"],
        "title": ["Red Shirt", "Blue Jeans"],
        "average_rating": [4.5, 4.0],
        "rating_number": [10, 8],
        "images": ["[]", "[]"],
        "features": ["unused", "unused"],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def _reviews(parent_asins):
    n = len(parent_asins)
    return pd.DataFrame({
        "asin": [f"B{i}" for i in range(n)],
        "parent_asin": parent_asins,
        "rating": [5] * n,
        "title": ["Great!"] * n,
        "text": ["Love it"] * n,
        "user_id": [f"U{i}" for i in range(n)],
        "timestamp": [1_700_000_000_000] * n,
        "verified_purchase": [True] * n,
    })


@pytest.fixture
def dataset(tmp_path):
    def make(meta, reviews):
        meta_path, rev_path = tmp_path / "meta.parquet", tmp_path / "reviews.parquet"
        meta.to_parquet(meta_path)
        reviews.to_parquet(rev_path)
        return DatasetRepository(meta_path, rev_path)
    return make


def test_valid_schema_passes(dataset):
    dataset(_meta(), _reviews(["A1", "A2"])).validate_schema()


def test_missing_metadata_columns_are_reported(dataset):
    repo = dataset(_meta().drop(columns=["title"]), _reviews(["A1"]))
    with pytest.raises(ValueError, match="Metadata is missing required columns: \\['title'\\]"):
        repo.validate_schema()


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        DatasetRepository(tmp_path / "nope.parquet", tmp_path / "nope2.parquet").validate_schema()


def test_orphan_reviews_are_detected(dataset):
    with pytest.raises(ValueError, match="Orphan reviews detected"):
        dataset(_meta(), _reviews(["A1", "ZZ"])).validate_relationships()


def test_load_metadata_prunes_unused_columns(dataset):
    with dataset(_meta(), _reviews(["A1"])) as repo:
        meta = repo.load_metadata()
    assert len(meta) == 2
    assert "features" not in meta.columns
    assert list(meta.columns[:2]) == ["parent_asin", "title"]


def test_load_reviews_for_returns_only_the_batch(dataset):
    with dataset(_meta(), _reviews(["A1", "A2", "A2"])) as repo:
        reviews = repo.load_reviews_for(["A2"])
    assert sorted(reviews["parent_asin"]) == ["A2", "A2"]


def test_empty_metadata_loads_with_columns(dataset):
    empty = _meta().iloc[0:0]
    with dataset(empty, _reviews([]).iloc[0:0]) as repo:
        meta = repo.load_metadata()
        reviews = repo.load_reviews_for([])
    assert meta.empty and "parent_asin" in meta.columns
    assert reviews.empty
