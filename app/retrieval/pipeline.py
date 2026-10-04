"""The search retrieval pipeline.

    query
      → query processing (regex + LLM, outfit detection)   query_processor.py
      → plan searches: gender pools × outfit groups         retriever.py
      → query embedding(s), one batched call                embedding_client.py
      → dense searches, run in parallel                     retriever.py
      → ONE batched cross-encoder rerank over all candidates reranker.py
      → interleave: genders within each group, then groups
      → top K

Normal query ("black jeans for men"): 1–2 searches (one per gender pool).
Outfit query ("an outfit for a wedding"): one search per garment group
(tops, bottoms, footwear) per pool -- up to 6 -- each with a smaller
candidate count, so the reranking
budget -- the expensive step -- stays the same. Each group searches and
reranks with its own text ("shoes for a wedding"), so footwear results are
judged as footwear.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app.clients.embedding_client import EmbeddingClient
from app.domain.outfit import OUTFIT_GROUPS, group_query
from app.domain.product import ProductMatch
from app.domain.search import SearchOutcome

from .query_processor import QueryProcessor
from .reranker import Reranker
from .retriever import Retriever, interleave, plan_subqueries

logger = logging.getLogger(__name__)

# Each outfit search must contribute at least this many reranked candidates.
MIN_CANDIDATES_PER_SEARCH = 2


class RetrievalPipeline:
    def __init__(
        self,
        query_processor: QueryProcessor,
        embedder: EmbeddingClient,
        retriever: Retriever,
        reranker: Reranker,
        rerank_candidates_k: int,
        outfit_dense_k: int = 10,
        max_parallel_searches: int = 8,
    ) -> None:
        self._query_processor = query_processor
        self._embedder = embedder
        self._retriever = retriever
        self._reranker = reranker
        self.rerank_candidates_k = rerank_candidates_k
        self.outfit_dense_k = outfit_dense_k
        # Pinecone searches are network-bound, so threads overlap them well.
        self._executor = ThreadPoolExecutor(max_workers=max_parallel_searches, thread_name_prefix="search")

    def run(self, query: str, top_k: int, vector: Optional[list[float]] = None) -> SearchOutcome:
        started = time.perf_counter()

        understanding = self._query_processor.process(query)
        outfit = understanding.outfit

        plan = plan_subqueries(understanding.filters, outfit)
        dense_k = self.outfit_dense_k if outfit else None
        per_search_k = max(MIN_CANDIDATES_PER_SEARCH, self.rerank_candidates_k // len(plan))

        # Search text per outfit group ("shoes for a wedding"); a single text
        # for a normal query. All embedded in one batch.
        groups = list(dict.fromkeys(sq.group for sq in plan))
        rerank_texts = {g: group_query(understanding.search_query or query, g) for g in groups}
        if vector is not None:
            vectors = {g: vector for g in groups}
        else:
            embed_texts = [group_query(understanding.expanded_query, g) for g in groups]
            vectors = dict(zip(groups, self._embedder.embed_many(embed_texts)))

        # 1. Dense searches, in parallel.
        results = list(self._executor.map(
            lambda sq: self._retriever.retrieve(vectors[sq.group], sq.filters, dense_k, relax_all_at_once=outfit),
            plan,
        ))
        searched = time.perf_counter()

        # 2. One batched rerank over every search's top candidates.
        candidates = [matches[:per_search_k] for matches, _ in results]
        self._reranker.score([(rerank_texts[sq.group], m) for sq, ranked in zip(plan, candidates) for m in ranked])
        for group in candidates:
            group.sort(key=lambda m: m.relevance, reverse=True)
        reranked_count = sum(len(c) for c in candidates)

        # 3. Interleave genders within each outfit group, then the groups.
        by_group: dict[Optional[str], list[list[ProductMatch]]] = defaultdict(list)
        for sq, ranked in zip(plan, candidates):
            by_group[sq.group].append(ranked)
        merged = interleave([interleave(pools) for pools in by_group.values()])

        # Don't return more than we actually reranked.
        final = merged[: min(top_k, reranked_count)]

        applied = results[0][1].applied()
        if outfit:
            applied["outfit"] = ", ".join(g for g in OUTFIT_GROUPS if g in by_group)

        logger.info(
            "search completed: outfit=%s searches=%d dense_k=%d reranked=%d results=%d filters=%s "
            "search_ms=%.0f total_ms=%.0f",
            outfit, len(plan), dense_k or self._retriever.dense_k, reranked_count, len(final), applied,
            (searched - started) * 1000, (time.perf_counter() - started) * 1000,
        )
        return SearchOutcome(query=query, matches=final, applied_filters=applied)
