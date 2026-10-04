"""Search domain models: what a query was understood to mean, the filters
retrieval applies, and the outcome of a search.

These are storage-agnostic. Translating SearchFilters into Pinecone's
filter syntax happens in app/repositories/vector_repository.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from typing import Optional

from .product import ProductMatch

# Order soft filters are DROPPED in when a filtered search returns too few
# results. gender/category are never relaxed: "men's" or "dress" is a hard
# constraint, not a hint. Price is not a filter at all -- most products have
# no price, so it isn't stored in the index.
RELAX_ORDER = ("min_rating", "sentiment", "style", "size", "color")


@dataclass(frozen=True)
class SearchFilters:
    gender: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None
    size: Optional[str] = None
    min_rating: Optional[float] = None
    sentiment: Optional[str] = None
    # Genders to leave out, used by gender-balanced retrieval when no gender
    # was asked for. Ignored when `gender` is set.
    exclude_genders: tuple[str, ...] = ()
    # Match any of these categories (an outfit group). Ignored when
    # `category` is set.
    categories: tuple[str, ...] = ()

    def relaxed(self) -> Optional["SearchFilters"]:
        """A copy with the next soft filter dropped, or None if none are left."""
        for name in RELAX_ORDER:
            if getattr(self, name) is not None:
                return replace(self, **{name: None})
        return None

    def without_soft_filters(self) -> Optional["SearchFilters"]:
        """A copy with every soft filter dropped at once, or None if none are set."""
        if all(getattr(self, name) is None for name in RELAX_ORDER):
            return None
        return replace(self, **{name: None for name in RELAX_ORDER})

    def applied(self) -> dict:
        """User-facing view of the active filters."""
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if f.name not in ("exclude_genders", "categories") and getattr(self, f.name) is not None
        }


@dataclass
class QueryUnderstanding:
    """Result of query processing: filters plus the text to embed."""

    filters: SearchFilters
    expanded_query: str               # text to embed (LLM-rewritten when available)
    search_query: str = ""            # the user's query, cleaned, for reranking
    # Where each extracted field came from ("regex" | "llm"), for debugging.
    sources: dict[str, str] = field(default_factory=dict)
    # General request ("an outfit for a wedding") -> search every outfit group.
    outfit: bool = False
    # Extracted but not used as filters (price isn't stored in the index).
    price_min: Optional[float] = None
    price_max: Optional[float] = None


@dataclass
class SearchOutcome:
    query: str
    matches: list[ProductMatch]
    applied_filters: dict
