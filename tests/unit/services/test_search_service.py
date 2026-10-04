import pytest

from app.core.exceptions import InvalidRequestError
from app.domain.search import SearchOutcome
from app.services.search_service import SearchService


class RecordingPipeline:
    def __init__(self):
        self.calls = []

    def run(self, query, top_k, vector=None):
        self.calls.append((query, top_k, vector))
        return SearchOutcome(query=query, matches=[], applied_filters={})


def test_uses_default_top_k_and_strips_query():
    pipeline = RecordingPipeline()
    SearchService(pipeline, default_top_k=10).search("  red shirt  ")
    assert pipeline.calls == [("red shirt", 10, None)]


def test_blank_query_is_rejected():
    with pytest.raises(InvalidRequestError):
        SearchService(RecordingPipeline(), default_top_k=10).search("   ")
