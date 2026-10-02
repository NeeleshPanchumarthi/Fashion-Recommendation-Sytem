"""Pinecone vector‑store helper.

Initialises the Pinecone client using the API key and environment from
``Settings`` and provides a simple ``upsert_vectors`` function that receives a
DataFrame with the enriched product records.
"""

from typing import Iterable
import pandas as pd
from pinecone import Pinecone, ServerlessSpec
from ..config.settings import Settings
from .embedding import embed_text

_settings = Settings()

# Initialise Pinecone once
pc = Pinecone(api_key=_settings.PINECONE_API_KEY)

def _get_index():
    """Return the Pinecone index instance, creating it if it does not exist."""
    existing_indexes = pc.list_indexes().names()
    if _settings.PINECONE_INDEX not in existing_indexes:
        # all-MiniLM-L6-v2 produces 384-dimensional vectors
        pc.create_index(
            name=_settings.PINECONE_INDEX,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="gcp",
                region=_settings.PINECONE_ENVIRONMENT.replace("-gcp", "") if "-gcp" in _settings.PINECONE_ENVIRONMENT else _settings.PINECONE_ENVIRONMENT
            )
        )
    return pc.Index(_settings.PINECONE_INDEX)

def upsert_vectors(df: pd.DataFrame, id_column: str = "asin") -> None:
    """Upsert product vectors into Pinecone.

    The DataFrame must contain a column with a unique identifier (default ``asin``)
    and a column called ``combined_text`` that holds the full text we want to
    embed. Any additional columns are stored as metadata.
    """
    index = _get_index()
    # Build the list of points in the format Pinecone expects.
    points = []
    for _, row in df.iterrows():
        text = str(row.get("combined_text", ""))
        if not text:
            continue
        vector = embed_text(text)
        metadata = {k: v for k, v in row.to_dict().items() if k != id_column and k != "combined_text"}
        points.append((str(row[id_column]), vector, metadata))
    # Pinecone accepts a batch upsert of up to 100 vectors per call – we batch for safety.
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        ids, vectors, metas = zip(*batch)
        index.upsert(vectors=list(vectors), ids=list(ids), payloads=list(metas))

def query_vector(vector: list[float], top_k: int = None) -> Iterable[dict]:
    """Search the Pinecone index with a pre‑computed vector.

    Returns an iterable of match dictionaries (id, score, metadata).
    """
    if top_k is None:
        top_k = _settings.TOP_K
    index = _get_index()
    results = index.query(vector=vector, top_k=top_k, include_metadata=True)
    for match in results.matches:
        yield {"id": match.id, "score": match.score, "metadata": match.metadata}
