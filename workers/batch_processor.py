"""Processes one ingestion batch, logging each stage:

    review analysis (score → select → sentiment → highlights)
      → product enrichment (attributes, defaults, combined text)
      → embedding generation
      → vector upsert (with retry)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import pandas as pd

from app.clients.embedding_client import EmbeddingClient
from app.core.exceptions import DependencyUnavailableError
from app.repositories.vector_repository import VectorRepository
from app.services.product_enrichment_service import enrich
from app.services.review_analysis_service import ReviewAnalysisService

logger = logging.getLogger(__name__)

ID_COLUMN = "parent_asin"
UPSERT_BACKOFF_SECONDS = 2  # doubles each retry: 2s, 4s, 8s


@dataclass
class BatchResult:
    products: int
    reviews: int
    vectors: int
    sentiment_counts: dict


class BatchProcessor:
    def __init__(
        self,
        reviews: ReviewAnalysisService,
        embedder: EmbeddingClient,
        vectors: VectorRepository,
        upsert_retries: int = 3,
    ) -> None:
        self._reviews = reviews
        self._embedder = embedder
        self._vectors = vectors
        self.upsert_retries = max(1, upsert_retries)

    def process(self, batch_id: int, meta_batch: pd.DataFrame, rev_batch: pd.DataFrame) -> BatchResult:
        with _stage(batch_id, "review analysis"):
            highlights_df, sentiment_df = self._reviews.analyze(rev_batch)

        with _stage(batch_id, "product enrichment"):
            products = enrich(meta_batch, highlights_df, sentiment_df)

        with _stage(batch_id, "embedding generation"):
            records = self._embed(products)

        with _stage(batch_id, "vector upsert"):
            written = self._upsert_with_retry(records)

        return BatchResult(
            products=len(meta_batch),
            reviews=len(rev_batch),
            vectors=written,
            sentiment_counts=products["overall_sentiment"].value_counts().to_dict(),
        )

    def _embed(self, products: pd.DataFrame) -> list[tuple[str, list[float], dict]]:
        """(product_id, vector, record) for every product with an ID and
        non-empty combined text; others are skipped."""
        records = []
        for row in products.to_dict(orient="records"):
            product_id = row.get(ID_COLUMN)
            text = str(row.get("combined_text") or "").strip()
            if product_id is None or pd.isna(product_id) or not text:
                continue
            records.append((str(product_id), self._embedder.embed(text), row))
        return records

    def _upsert_with_retry(self, records: list[tuple[str, list[float], dict]]) -> int:
        for attempt in range(1, self.upsert_retries + 1):
            try:
                return self._vectors.upsert(records)
            except DependencyUnavailableError as exc:
                if attempt == self.upsert_retries:
                    raise
                wait = UPSERT_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Vector upsert failed (attempt %d/%d): %s -- retrying in %ds",
                    attempt, self.upsert_retries, exc.message, wait,
                )
                time.sleep(wait)
        raise AssertionError("unreachable")


class _stage:
    """Logs '<stage> started/completed in Ns' for one batch."""

    def __init__(self, batch_id: int, name: str) -> None:
        self.batch_id = batch_id
        self.name = name

    def __enter__(self) -> None:
        self.started = time.perf_counter()
        logger.info("Batch %d %s started", self.batch_id, self.name)

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            logger.info("Batch %d %s completed in %.1fs", self.batch_id, self.name, time.perf_counter() - self.started)
