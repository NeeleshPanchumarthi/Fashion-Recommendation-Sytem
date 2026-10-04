"""Cross-encoder model wrapper used for reranking.

Loaded lazily, once per process. Scores (query, text) pairs; deciding what
text to score and how to order results is app/retrieval/reranker.py.
"""

from __future__ import annotations

import logging
import threading

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class RerankerClient:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: CrossEncoder | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _get_model(self) -> CrossEncoder:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info("Loading cross-encoder model: %s", self.model_name)
                    self._model = CrossEncoder(self.model_name)
        return self._model

    def warm(self) -> None:
        self._get_model()

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        return [float(s) for s in self._get_model().predict(pairs)]
