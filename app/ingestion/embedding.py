"""Embedding utilities.

Uses the Sentence‑Transformers model specified in ``Settings.EMBEDDING_MODEL``
to turn a piece of text into a dense vector.
"""

from sentence_transformers import SentenceTransformer
from ..config.settings import Settings

# Lazy‑load the model to avoid heavy imports at import time.
_model = None

def _get_model():
    global _model
    if _model is None:
        _settings = Settings()
        _model = SentenceTransformer(_settings.EMBEDDING_MODEL)
    return _model

def embed_text(text: str) -> list[float]:
    """Return a normalized embedding vector for *text*.
    
    The returned list can be directly used with Pinecone's ``upsert`` API.
    """
    # ``encode`` already returns a NumPy array; we convert to list for JSON safety.
    return _model.encode(text, normalize_embeddings=True).tolist()
