"""Pinecone vector-store helper."""

from typing import Iterable
import json
import logging

import pandas as pd
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from pinecone.errors import PineconeConnectionError

from app.config.settings import Settings

from .embedding import (
    embed_text,
    get_embedding_dimension,
)

logger = logging.getLogger(__name__)

_settings = Settings()

if not _settings.PINECONE_API_KEY:
    raise ValueError(
        "PINECONE_API_KEY is not configured."
    )

pc = Pinecone(
    api_key=_settings.PINECONE_API_KEY
)

# Connection resets during the TLS handshake (WinError 10054) happen on some
# networks; a couple of quick retries usually get through.
QUERY_CONNECT_ATTEMPTS = 3

# Cached after the first successful lookup so each search makes one Pinecone
# call (the query) instead of three (list + describe + query).
_index = None


class VectorStoreUnavailable(RuntimeError):
    """Pinecone could not be reached or rejected the request."""


def _get_index():
    """Return the Pinecone index, creating it if necessary."""

    global _index
    if _index is not None:
        return _index

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

    # v10+ requires host= to avoid the 'Malformed domain' 401 error
    host = pc.describe_index(index_name).host
    _index = pc.Index(host=host)
    return _index



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
        "size",             # needed for query-time size filtering (search.py)
        "category",
        "average_rating",   # avg rating from product metadata
        "rating_number",    # needed by search.py's SearchResult.rating_number
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

            if key == "review_highlights":
                # Always serialise as a JSON string so Pinecone receives a
                # reliable scalar value regardless of the internal list type.
                # The search layer can json.loads() it back when serving results.
                if isinstance(value, (list, tuple)):
                    metadata[key] = json.dumps(
                        [str(v) for v in value],
                        ensure_ascii=False,
                    )
                else:
                    metadata[key] = str(value)

            elif isinstance(value, (list, tuple)):
                # Pinecone allows lists of primitives only.
                # images may be list[dict]; serialise those to a JSON string.
                if all(isinstance(v, (str, int, float, bool)) for v in value):
                    metadata[key] = list(value)
                else:
                    metadata[key] = json.dumps(value, default=str)

            elif isinstance(value, dict):
                metadata[key] = json.dumps(value, default=str)

            elif isinstance(value, (np.ndarray, pd.Series)):
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

        # Debug: log review_highlights for the first product to confirm the
        # field is populated before it reaches Pinecone.
        if len(vectors) == 0 and "review_highlights" in metadata:
            logger.info(
                "Review highlights for %s: %s",
                product_id,
                metadata["review_highlights"],
            )

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
    filter: dict = None,
) -> Iterable[dict]:
    """Query Pinecone using an embedding vector.

    filter: optional Pinecone metadata filter dict (see
    app/search/filtering.py build_pinecone_filter()). None means unfiltered,
    same as before this parameter existed -- fully backward compatible.
    """

    if top_k is None:
        top_k = _settings.TOP_K

    index = _get_index()
    if index is None:
        raise VectorStoreUnavailable(
            "Could not connect to Pinecone (check PINECONE_API_KEY and your network)."
        )

    for attempt in range(QUERY_CONNECT_ATTEMPTS):
        try:
            results = index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter,
            )
            break
        except PineconeConnectionError as exc:
            logger.warning(
                "Pinecone query connection failed (attempt %d/%d): %s",
                attempt + 1, QUERY_CONNECT_ATTEMPTS, exc,
            )
            if attempt == QUERY_CONNECT_ATTEMPTS - 1:
                raise VectorStoreUnavailable(
                    "Could not reach Pinecone; the connection was reset. Please try again."
                ) from exc

    for match in results.matches:

        yield {
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata,
        }