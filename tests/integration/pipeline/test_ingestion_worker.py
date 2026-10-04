"""End-to-end worker run over a small parquet dataset: real dataset loading,
batching, review analysis, enrichment and checkpointing; fake models and
vector database."""

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.repositories.vector_repository import VectorRepository
from app.services.review_analysis_service import ReviewAnalysisService
from scripts.generate_sample_data import build_sample
from tests.fakes import FakeEmbedder, FakePineconeClient, FakeSentimentClient
from workers.batch_processor import BatchProcessor
from workers.ingestion_worker import WorkerOptions, run


@pytest.fixture
def sample(tmp_path: Path):
    metadata, reviews = build_sample()
    metadata.to_parquet(tmp_path / "metadata.parquet")
    reviews.to_parquet(tmp_path / "reviews.parquet")
    return tmp_path


def _options(path: Path, **overrides) -> WorkerOptions:
    values = dict(
        metadata_path=path / "metadata.parquet",
        reviews_path=path / "reviews.parquet",
        batch_size=2,
        checkpoint_path=path / "state.json",
        failure_log_path=path / "failures.log",
        validate=True,
    )
    values.update(overrides)
    return WorkerOptions(**values)


def _factory(pinecone: FakePineconeClient):
    def build(settings):
        return BatchProcessor(ReviewAnalysisService(FakeSentimentClient()), FakeEmbedder(), VectorRepository(pinecone))
    return build


SETTINGS = Settings(PINECONE_API_KEY="test")


def test_full_run_indexes_all_products_and_checkpoints(sample):
    pinecone = FakePineconeClient()
    assert run(_options(sample), SETTINGS, _factory(pinecone)) == 0

    assert sorted(pinecone.vectors) == ["B01D234567", "B02E345678", "B03F456789"]
    dress = pinecone.vectors["B02E345678"]["metadata"]
    assert dress["gender"] == "women" and dress["category"] == "dress"
    assert len(json.loads(dress["images"])) == 4
    state = json.loads((sample / "state.json").read_text())
    assert state["completed_batches"] == [0, 2] and state["failed_batches"] == {}


def test_rerun_resumes_and_skips_completed_batches(sample):
    pinecone = FakePineconeClient()
    run(_options(sample, max_batches=1), SETTINGS, _factory(pinecone))
    assert len(pinecone.vectors) == 2

    run(_options(sample), SETTINGS, _factory(pinecone))
    assert len(pinecone.vectors) == 3
    assert len(pinecone.upsert_batches) == 2  # batch 0 was not redone


def test_failed_batch_is_recorded_and_retried_later(sample):
    failing = FakePineconeClient(fail_times=100)
    assert run(_options(sample), SETTINGS, _factory(failing)) == 1
    assert set(json.loads((sample / "state.json").read_text())["failed_batches"]) == {"0", "2"}

    healthy = FakePineconeClient()
    assert run(_options(sample, only_failed=True), SETTINGS, _factory(healthy)) == 0
    assert len(healthy.vectors) == 3


def test_dry_run_processes_nothing(sample):
    pinecone = FakePineconeClient()
    assert run(_options(sample, dry_run=True), SETTINGS, _factory(pinecone)) == 0
    assert pinecone.vectors == {} and not (sample / "state.json").exists()
