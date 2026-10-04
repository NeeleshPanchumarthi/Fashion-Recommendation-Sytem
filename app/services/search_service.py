"""Product search use case: the entry point the API calls."""

from __future__ import annotations

from typing import Optional

from app.core.exceptions import InvalidRequestError
from app.domain.search import SearchOutcome
from app.retrieval.pipeline import RetrievalPipeline


class SearchService:
    def __init__(self, pipeline: RetrievalPipeline, default_top_k: int) -> None:
        self._pipeline = pipeline
        self.default_top_k = default_top_k

    def search(self, query: str, top_k: Optional[int] = None, vector: Optional[list[float]] = None) -> SearchOutcome:
        query = query.strip()
        if not query:
            raise InvalidRequestError("Query must not be empty.")
        return self._pipeline.run(query, top_k or self.default_top_k, vector)
