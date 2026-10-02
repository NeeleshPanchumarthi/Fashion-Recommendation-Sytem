"""Embedding utilities."""

from sentence_transformers import SentenceTransformer

from app.config.settings import Settings


_model = None


def _get_model() -> SentenceTransformer:
    """Load and return the embedding model."""

    global _model

    if _model is None:

        settings = Settings()

        print(
            f"Loading embedding model: "
            f"{settings.EMBEDDING_MODEL}"
        )

        _model = SentenceTransformer(
            settings.EMBEDDING_MODEL
        )

        print(
            f"Embedding dimension: "
            f"{_model.get_sentence_embedding_dimension()}"
        )

    return _model


def embed_text(
    text: str,
) -> list[float]:
    """Return a normalized embedding vector."""

    if text is None:
        text = ""

    text = str(text).strip()

    if not text:
        raise ValueError(
            "Cannot generate embedding for empty text."
        )

    model = _get_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()


def get_embedding_dimension() -> int:
    """Return embedding model dimensionality."""

    model = _get_model()

    return model.get_sentence_embedding_dimension()