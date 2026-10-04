"""Product vector storage: the persistence boundary for the vector index.

Owns the vector *schema* -- metadata field names and how values are encoded
-- and the translation of domain SearchFilters into the vector database's
filter syntax. Services never see Pinecone types or filter operators, so
the vector database can be replaced by changing only this module and the
client.

Vector schema (must stay compatible with vectors already in the index):
    id        parent_asin
    values    normalized text embedding of the product's combined text
    metadata  METADATA_FIELDS below; `images` and `review_highlights` are
              stored as JSON strings (Pinecone only allows lists of primitives).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

from app.clients.pinecone_client import PineconeClient
from app.domain.product import Product, ProductMatch
from app.domain.search import SearchFilters

logger = logging.getLogger(__name__)

# Only these columns are written as metadata; everything else (combined
# text, scoring intermediates, price) stays out of the index.
METADATA_FIELDS = (
    "title",
    "description",
    "gender",
    "color",
    "style",
    "size",
    "category",
    "average_rating",
    "rating_number",
    "images",
    "review_highlights",
    "overall_sentiment",
)


def to_pinecone_filter(filters: SearchFilters) -> Optional[dict]:
    """Translate domain filters into Pinecone's metadata filter syntax.
    Top-level keys are implicitly ANDed by Pinecone."""
    clauses: dict[str, Any] = {}

    if filters.gender:
        clauses["gender"] = filters.gender
    elif filters.exclude_genders:
        clauses["gender"] = {"$nin": list(filters.exclude_genders)}
    if filters.category:
        clauses["category"] = filters.category
    elif filters.categories:
        clauses["category"] = {"$in": list(filters.categories)}
    if filters.color:
        clauses["color"] = filters.color
    if filters.style:
        clauses["style"] = filters.style
    if filters.size:
        clauses["size"] = filters.size
    if filters.sentiment:
        clauses["overall_sentiment"] = filters.sentiment
    if filters.min_rating is not None:
        clauses["average_rating"] = {"$gte": filters.min_rating}

    return clauses or None


# ---------------------------------------------------------------------------
# Metadata encoding
# ---------------------------------------------------------------------------

def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False  # arrays/lists: not a scalar NaN


def encode_metadata(row: dict[str, Any]) -> dict[str, Any]:
    """Product record -> Pinecone metadata (primitives / lists of strings)."""
    metadata: dict[str, Any] = {}
    for key in METADATA_FIELDS:
        value = row.get(key)
        if _is_missing(value):
            continue

        if key == "review_highlights":
            # Always a JSON string so Pinecone receives a reliable scalar.
            if isinstance(value, (list, tuple, np.ndarray)):
                metadata[key] = json.dumps([str(v) for v in value], ensure_ascii=False)
            else:
                metadata[key] = str(value)
        elif isinstance(value, (list, tuple)):
            # images may be list[dict]; those become a JSON string.
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
            metadata[key] = value.item()  # numpy scalar
        else:
            metadata[key] = value
    return metadata


def _decode_json_list(value: Any) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return [value]
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    return [value]


def decode_product(product_id: str, metadata: dict[str, Any]) -> Product:
    """Pinecone metadata -> domain Product."""
    images = _decode_json_list(metadata.get("images"))
    if images and isinstance(images[0], str):
        # A bare URL rather than the list of image dicts.
        images = [{"variant": "MAIN", "large": url} for url in images if isinstance(url, str)]

    rating_number = metadata.get("rating_number")
    return Product(
        product_id=product_id,
        title=metadata.get("title") or "Unknown Title",
        description=metadata.get("description"),
        category=metadata.get("category"),
        gender=metadata.get("gender"),
        color=metadata.get("color"),
        style=metadata.get("style"),
        size=metadata.get("size"),
        average_rating=metadata.get("average_rating"),
        rating_number=int(rating_number) if rating_number is not None else None,
        overall_sentiment=metadata.get("overall_sentiment"),
        images=[img for img in images if isinstance(img, dict)],
        review_highlights=[str(h) for h in _decode_json_list(metadata.get("review_highlights"))],
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class VectorRepository:
    def __init__(self, client: PineconeClient, upsert_batch_size: int = 100) -> None:
        self._client = client
        self.upsert_batch_size = upsert_batch_size

    def search(self, vector: list[float], top_k: int, filters: SearchFilters) -> list[ProductMatch]:
        rows = self._client.query(vector, top_k=top_k, filter=to_pinecone_filter(filters))
        return [ProductMatch(product=decode_product(r["id"], r["metadata"]), score=r["score"]) for r in rows]

    def ensure_index(self, dimension: int) -> None:
        self._client.ensure_index(dimension)

    def upsert(self, records: Iterable[tuple[str, list[float], dict[str, Any]]]) -> int:
        """Upsert (product_id, vector, product record) tuples in batches.
        Idempotent per product ID. Returns the number of vectors written."""
        vectors = [
            {"id": str(product_id), "values": vector, "metadata": encode_metadata(record)}
            for product_id, vector, record in records
        ]
        total = len(vectors)
        for start in range(0, total, self.upsert_batch_size):
            self._client.upsert(vectors[start : start + self.upsert_batch_size])
            logger.info("Upserted %d/%d vectors", min(start + self.upsert_batch_size, total), total)
        return total

    def ping(self) -> dict[str, Any]:
        return self._client.ping()
