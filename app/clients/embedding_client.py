"""Text embedding model (SentenceTransformer) wrapper.

The model is loaded lazily, once per process, and shared by every caller.
Vectors are L2-normalized, matching how the existing index was built.
"""

from __future__ import annotations

import logging
import threading

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info("Loading embedding model: %s", self.model_name)
                    self._model = SentenceTransformer(self.model_name)
                    logger.info("Embedding model loaded (dimension=%d)", self.dimension_of(self._model))
        return self._model

    @staticmethod
    def dimension_of(model: SentenceTransformer) -> int:
        return model.get_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self.dimension_of(self._get_model())

    def warm(self) -> None:
        self._get_model()

    def embed(self, text: str) -> list[float]:
        """Return a normalized embedding vector for non-empty text."""
        text = str(text or "").strip()
        if not text:
            raise ValueError("Cannot generate embedding for empty text.")
        return self._get_model().encode(text, normalize_embeddings=True).tolist()
