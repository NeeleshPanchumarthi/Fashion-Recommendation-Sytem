"""Readiness checks for the service's dependencies.

Liveness (is the process up?) needs no checks and lives in the API layer.
Readiness answers "can this instance serve searches right now?":

  - embedding + reranker models loaded  (required)
  - vector database reachable            (required; cached briefly so frequent
                                          probes don't hammer Pinecone)
  - LLM configured                       (optional: search falls back to
                                          regex-only query understanding)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from app.clients.embedding_client import EmbeddingClient
from app.clients.llm_client import LLMClient
from app.clients.reranker_client import RerankerClient
from app.core.exceptions import AppError
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)


@dataclass
class ReadinessReport:
    ready: bool
    checks: dict[str, dict] = field(default_factory=dict)


class HealthService:
    def __init__(
        self,
        vectors: VectorRepository,
        embedder: EmbeddingClient,
        reranker: RerankerClient,
        llm: LLMClient,
        cache_seconds: float = 15.0,
    ) -> None:
        self._vectors = vectors
        self._embedder = embedder
        self._reranker = reranker
        self._llm = llm
        self.cache_seconds = cache_seconds
        self._vector_check: tuple[float, dict] | None = None
        self._lock = threading.Lock()

    def readiness(self) -> ReadinessReport:
        checks = {
            "embedding_model": {"ok": self._embedder.loaded},
            "reranker_model": {"ok": self._reranker.loaded},
            "vector_db": self._check_vector_db(),
            "llm": {"ok": True, "enabled": self._llm.enabled, "required": False},
        }
        ready = all(check["ok"] for name, check in checks.items() if name != "llm")
        return ReadinessReport(ready=ready, checks=checks)

    def _check_vector_db(self) -> dict:
        with self._lock:
            now = time.monotonic()
            if self._vector_check and now - self._vector_check[0] < self.cache_seconds:
                return self._vector_check[1]
            try:
                result = {"ok": True, **self._vectors.ping()}
            except AppError as exc:
                logger.warning("Readiness: vector database check failed: %s", exc.message)
                result = {"ok": False, "error": exc.message}
            self._vector_check = (now, result)
            return result
