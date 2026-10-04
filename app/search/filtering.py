"""Pinecone metadata filter construction + iterative relaxation.

Priority: gender/category are never relaxed (they're almost always
deliberate -- "men's" or "dress" is a hard constraint, not a hint).
rating/sentiment/style/size/color are soft constraints, dropped one
at a time, cheapest-signal-first, only when a filtered search comes back
with too few results.

Price is not filtered on: most products have no price, so it isn't stored
in Pinecone and a price clause would match almost nothing.
"""

from __future__ import annotations

from typing import Optional

# Order filters are DROPPED in, when results are too few. Deliberately
# excludes gender/category -- those stay applied no matter what.
RELAX_ORDER = ["min_rating", "sentiment", "style", "size", "color"]


def build_pinecone_filter(filters: dict) -> Optional[dict]:
    """Translate the merged query-understanding filters into Pinecone's
    metadata filter syntax. Top-level keys are implicitly ANDed by Pinecone."""
    clauses = {}

    if filters.get("gender"):
        clauses["gender"] = filters["gender"]
    if filters.get("category"):
        clauses["category"] = filters["category"]
    if filters.get("color"):
        clauses["color"] = filters["color"]
    if filters.get("style"):
        clauses["style"] = filters["style"]
    if filters.get("size"):
        clauses["size"] = filters["size"]
    if filters.get("sentiment"):
        clauses["overall_sentiment"] = filters["sentiment"]

    if filters.get("min_rating") is not None:
        clauses["average_rating"] = {"$gte": filters["min_rating"]}

    return clauses or None


def relax_once(filters: dict) -> Optional[dict]:
    """Returns a NEW filters dict with the next-lowest-priority active
    filter dropped, or None if nothing left to relax (gender/category are
    never touched here, by design -- caller should stop retrying at that
    point rather than running an unfiltered search unexpectedly)."""
    relaxed = dict(filters)
    for key in RELAX_ORDER:
        if relaxed.get(key) is not None:
            relaxed[key] = None
            return relaxed
    return None
