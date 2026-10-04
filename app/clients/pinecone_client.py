"""Pinecone SDK wrapper: the only module that talks to Pinecone directly.

Handles connecting, retrying transient connection resets, and translating
SDK errors into application exceptions. Knows nothing about products or
filters -- that's app/repositories/vector_repository.py.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional, TypeVar

from pinecone import Pinecone, ServerlessSpec
from pinecone.errors import PineconeConnectionError, PineconeError, UnauthorizedError

from app.core.exceptions import ConfigurationError, DependencyUnavailableError

logger = logging.getLogger(__name__)

T = TypeVar("T")
DEPENDENCY = "pinecone"


class PineconeClient:
    def __init__(self, api_key: str, index_name: str, region: str, connect_attempts: int = 3) -> None:
        self._pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.region = region
        self.connect_attempts = max(1, connect_attempts)
        self._index = None
        self._lock = threading.Lock()

    # -- connection ---------------------------------------------------------

    def _index_handle(self):
        """The index handle, looked up once and cached so each query is a
        single Pinecone call (not list + describe + query)."""
        if self._index is None:
            with self._lock:
                if self._index is None:
                    def connect():
                        if not self._pc.has_index(self.index_name):
                            raise ConfigurationError(
                                f"Pinecone index '{self.index_name}' does not exist. "
                                "Run the ingestion worker to create and fill it."
                            )
                        # v10+ requires host= to avoid the 'Malformed domain' 401 error
                        host = self._pc.describe_index(self.index_name).host
                        return self._pc.Index(host=host)

                    self._index = self._call("connect", connect)
        return self._index

    def ensure_index(self, dimension: int) -> None:
        """Create the index if it doesn't exist. Worker only: the API never
        creates infrastructure on a search request."""
        def create():
            if not self._pc.has_index(self.index_name):
                logger.info("Creating Pinecone index '%s' (dimension=%d)", self.index_name, dimension)
                self._pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=self.region),
                )

        self._call("ensure_index", create)

    # -- operations ---------------------------------------------------------

    def query(self, vector: list[float], top_k: int, filter: Optional[dict]) -> list[dict[str, Any]]:
        index = self._index_handle()
        results = self._call(
            "query",
            lambda: index.query(vector=vector, top_k=top_k, include_metadata=True, filter=filter),
        )
        return [{"id": m.id, "score": m.score, "metadata": m.metadata or {}} for m in results.matches]

    def upsert(self, vectors: list[dict[str, Any]]) -> None:
        index = self._index_handle()
        self._call("upsert", lambda: index.upsert(vectors=vectors))

    def ping(self) -> dict[str, Any]:
        """Cheap reachability check for readiness probes."""
        index = self._index_handle()
        stats = self._call("ping", index.describe_index_stats)
        return {"index": self.index_name, "vector_count": getattr(stats, "total_vector_count", None)}

    # -- error handling -----------------------------------------------------

    def _call(self, operation: str, fn: Callable[[], T]) -> T:
        """Run an SDK call, retrying connection resets (WinError 10054
        during the TLS handshake happens on some networks)."""
        for attempt in range(1, self.connect_attempts + 1):
            try:
                return fn()
            except PineconeConnectionError as exc:
                logger.warning(
                    "Pinecone %s connection failed (attempt %d/%d): %s",
                    operation, attempt, self.connect_attempts, exc,
                )
                if attempt == self.connect_attempts:
                    raise DependencyUnavailableError(
                        DEPENDENCY, "Could not reach the vector database; the connection was reset. Please try again."
                    ) from exc
            except UnauthorizedError as exc:
                raise DependencyUnavailableError(
                    DEPENDENCY, "The vector database rejected the configured API key."
                ) from exc
            except PineconeError as exc:
                logger.error("Pinecone %s failed: %s", operation, exc)
                raise DependencyUnavailableError(DEPENDENCY, "The vector database request failed.") from exc
        raise AssertionError("unreachable")
