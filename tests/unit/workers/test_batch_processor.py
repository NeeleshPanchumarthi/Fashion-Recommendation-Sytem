import json

import pandas as pd
import pytest

from app.core.exceptions import DependencyUnavailableError
from app.repositories.vector_repository import VectorRepository
from app.services.review_analysis_service import ReviewAnalysisService
from tests.fakes import FakeEmbedder, FakePineconeClient, FakeSentimentClient
from workers import batch_processor
from workers.batch_processor import BatchProcessor


def _meta():
    return pd.DataFrame({
        "parent_asin": ["A1", "A2", None],
        "title": ["Women's Black Dress", "Men's Red Shirt", "No id"],
        "average_rating": [4.5, 3.0, 1.0],
        "images": [[{"variant": "MAIN", "large": "L1"}], [], []],
    })


def _reviews():
    return pd.DataFrame({
        "parent_asin": ["A1"], "rating": [5], "text": ["Love it"],
        "timestamp": [1_690_000_000_000], "verified_purchase": [True], "helpful_vote": [2],
    })


def _processor(client, retries=3):
    return BatchProcessor(
        ReviewAnalysisService(FakeSentimentClient()), FakeEmbedder(), VectorRepository(client), upsert_retries=retries
    )


def test_process_indexes_every_product_with_an_id(monkeypatch):
    client = FakePineconeClient()
    result = _processor(client).process(0, _meta(), _reviews())

    assert (result.products, result.reviews, result.vectors) == (3, 1, 2)
    stored = client.vectors["A1"]["metadata"]
    assert stored["overall_sentiment"] == "positive"
    assert json.loads(stored["review_highlights"]) == ["Love it"]
    assert json.loads(stored["images"]) == [{"variant": "MAIN", "large": "L1"}]
    assert client.vectors["A2"]["metadata"]["overall_sentiment"] == "neutral"


def test_upsert_is_retried_on_connection_failures(monkeypatch):
    monkeypatch.setattr(batch_processor.time, "sleep", lambda s: None)
    client = FakePineconeClient(fail_times=2)
    assert _processor(client).process(0, _meta(), _reviews()).vectors == 2


def test_upsert_gives_up_after_the_retry_budget(monkeypatch):
    monkeypatch.setattr(batch_processor.time, "sleep", lambda s: None)
    with pytest.raises(DependencyUnavailableError):
        _processor(FakePineconeClient(fail_times=5), retries=2).process(0, _meta(), _reviews())
