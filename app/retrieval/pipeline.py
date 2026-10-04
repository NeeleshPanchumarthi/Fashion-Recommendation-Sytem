"""The search retrieval pipeline.

    query
      → query processing (regex + LLM)      app/retrieval/query_processor.py
      → query embedding                     app/clients/embedding_client.py
      → candidate retrieval per gender pool app/retrieval/retriever.py
      → cross-encoder rerank per pool       app/retrieval/reranker.py
      → interleave pools, take top K
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.clients.embedding_client import EmbeddingClient
from app.domain.search import SearchOutcome

from .query_processor import QueryProcessor
from .reranker import Reranker
from .retriever import Retriever, gender_pools, interleave

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    def __init__(
        self,
        query_processor: QueryProcessor,
        embedder: EmbeddingClient,
        retriever: Retriever,
        reranker: Reranker,
        rerank_candidates_k: int,
    ) -> None:
        self._query_processor = query_processor
        self._embedder = embedder
        self._retriever = retriever
        self._reranker = reranker
        self.rerank_candidates_k = rerank_candidates_k

    def run(self, query: str, top_k: int, vector: Optional[list[float]] = None) -> SearchOutcome:
        started = time.perf_counter()

        understanding = self._query_processor.process(query)
        query_vector = vector or self._embedder.embed(understanding.expanded_query)

        pools = gender_pools(understanding.filters)
        # Same total rerank cost whether we search one pool or two.
        per_pool_k = max(1, self.rerank_candidates_k // len(pools))

        ranked_pools = []
        used_filters = []
        for pool_filters in pools:
            matches, used = self._retriever.retrieve(query_vector, pool_filters)
            ranked_pools.append(self._reranker.rerank(query, matches[:per_pool_k]))
            used_filters.append(used)

        # Don't return more than we actually reranked.
        final = interleave(ranked_pools)[: min(top_k, self.rerank_candidates_k)]

        logger.info(
            "search completed: pools=%d results=%d filters=%s sources=%s duration_ms=%.0f",
            len(pools), len(final), understanding.filters.applied(), understanding.sources,
            (time.perf_counter() - started) * 1000,
        )
        # Report what the first pool actually used, after any relaxation.
        return SearchOutcome(query=query, matches=final, applied_filters=used_filters[0].applied())
