"""Pinecone vector-store helper."""

from typing import Iterable
import json

import pandas as pd
import numpy as np
from pinecone import Pinecone, ServerlessSpec

from app.config.settings import Settings

from .embedding import (
    embed_text,
    get_embedding_dimension,
)


_settings = Settings()

if not _settings.PINECONE_API_KEY:
    raise ValueError(
        "PINECONE_API_KEY is not configured."
    )

pc = Pinecone(
    api_key=_settings.PINECONE_API_KEY
)


def _get_index():
    """Return the Pinecone index, creating it if necessary."""

    index_name = _settings.PINECONE_INDEX

    try:
        existing_indexes = pc.list_indexes().names()
    except Exception as exc:
        logger.warning("Pinecone unavailable or API key missing: %s", exc)
        return None

    if index_name not in existing_indexes:

        dimension = get_embedding_dimension()

        print(
            f"Creating Pinecone index "
            f"'{index_name}' "
            f"with dimension {dimension}"
        )

        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=_settings.PINECONE_ENVIRONMENT,
            ),
        )

    return pc.Index(index_name)


def upsert_vectors(
    df: pd.DataFrame,
    id_column: str = "parent_asin",
) -> None:
    """Generate embeddings and upsert products to Pinecone."""

    if id_column not in df.columns:
        raise ValueError(
            f"Missing vector ID column: {id_column}"
        )

    if "combined_text" not in df.columns:
        raise ValueError(
            "DataFrame must contain 'combined_text'"
        )

    index = _get_index()
    if index is None:
        logger.info("Pinecone unavailable; skipping vector upsert.")
        return

    vectors = []

    # Fields explicitly stored in Pinecone metadata.
    # Only these columns are written; all others (combined_text, scoring
    # intermediates, etc.) are excluded.
    PINECONE_METADATA_FIELDS = {
        "title",
        "description",
        "gender",
        "color",
        "style",
        "category",
        "average_rating",   # avg rating from product metadata
        "images",           # image_url(s)
        "review_highlights",
        "overall_sentiment",
    }

    for _, row in df.iterrows():

        product_id = row.get(id_column)

        if product_id is None:
            continue

        try:
            if pd.isna(product_id):
                continue
        except (TypeError, ValueError):
            pass

        text = row.get(
            "combined_text",
            "",
        )

        if text is None:
            continue

        text = str(text).strip()

        if not text:
            continue

        vector = embed_text(text)

        if not vector:
            continue

        metadata = {}

        for key, value in row.to_dict().items():

            # Skip the vector ID column and the embedding source text
            if key in {id_column, "combined_text"}:
                continue

            # Only store explicitly allowed metadata fields
            if key not in PINECONE_METADATA_FIELDS:
                continue

            if value is None:
                continue

            try:
                if pd.isna(value):
                    continue
            except (TypeError, ValueError):
                pass

            if isinstance(value, (list, tuple)):
                # Pinecone only allows lists of primitives (str/int/float/bool).
                # review_highlights is list[str] so it passes through directly.
                # images may be list[dict]; serialise those to JSON string.
                if all(isinstance(v, (str, int, float, bool)) for v in value):
                    metadata[key] = list(value)
                else:
                    metadata[key] = json.dumps(value, default=str)

            elif isinstance(value, dict):
                metadata[key] = json.dumps(value, default=str)

            elif isinstance(value, (np.ndarray, pd.Series)):
                # Convert numpy/pandas arrays to plain Python objects.
                converted = value.tolist()
                if all(isinstance(v, (str, int, float, bool)) for v in converted):
                    metadata[key] = converted
                else:
                    metadata[key] = json.dumps(converted, default=str)

            elif hasattr(value, "item"):
                # Scalar numpy types (e.g. np.float32)
                metadata[key] = value.item()

            else:
                metadata[key] = value

        vectors.append(
            {
                "id": str(product_id),
                "values": vector,
                "metadata": metadata,
            }
        )

    if not vectors:
        print(
            "No valid vectors generated."
        )
        return

    batch_size = 100
    total = len(vectors)

    print(
        f"Upserting {total:,} vectors to Pinecone..."
    )

    for start in range(
        0,
        total,
        batch_size,
    ):

        batch = vectors[
            start:start + batch_size
        ]

        index.upsert(
            vectors=batch
        )

        uploaded = min(
            start + batch_size,
            total,
        )

        print(
            f"Uploaded "
            f"{uploaded:,}/{total:,}"
        )

    print(
        f"Successfully upserted "
        f"{total:,} vectors to Pinecone"
    )


def query_vector(
    vector: list[float],
    top_k: int = None,
) -> Iterable[dict]:
    """Query Pinecone using an embedding vector."""

    if top_k is None:
        top_k = _settings.TOP_K

    index = _get_index()

    results = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
    )

    for match in results.matches:

        yield {
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata,
        }