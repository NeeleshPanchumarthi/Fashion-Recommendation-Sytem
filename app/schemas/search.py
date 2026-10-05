"""HTTP contracts for POST /api/search.

Kept separate from the domain models: field names here are the public API
the frontend depends on, and can stay stable while internals change.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.product import ProductMatch
from app.domain.search import SearchOutcome
from app.domain.sections import effective_gender, is_accessory, is_footwear
from app.domain.tryon import garment_type_for


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural-language product query")
    vector: Optional[List[float]] = Field(None, description="Pre-computed query embedding (optional)")
    top_k: Optional[int] = Field(None, ge=1, le=50, description="Number of results; server default if omitted")


class SearchResult(BaseModel):
    """One product card: only what the frontend displays."""

    product_id: str = Field(..., description="Product identifier (parent_asin)")
    title: str = Field(..., description="Product title")
    images: List[str] = Field(
        default_factory=list,
        description="Large image URLs for the card carousel: MAIN first, then PT01 and any angle shots",
    )
    average_rating: Optional[float] = Field(None, description="Average rating")
    review_highlights: Optional[List[str]] = Field(
        None, description="Selected review snippets (60% positive / 20% neutral / 20% negative mix)"
    )
    garment_type: Optional[str] = Field(
        None, description="Try-on garment type (upper_body | lower_body | dresses); null if it can't be tried on"
    )

    gender: Optional[str] = Field(
        None, description="men | women | kids | unisex; null if the product doesn't say (drives the Men/Women/Kids tabs)"
    )
    is_accessory: bool = Field(False, description="Hat, bag, belt, watch...; drives the Accessories tab")
    is_footwear: bool = Field(False, description="Shoes, sneakers, boots, sandals...; drives the Footwear tab")

    @classmethod
    def from_match(cls, match: ProductMatch) -> "SearchResult":
        product = match.product
        return cls(
            gender=effective_gender(product.gender, product.category, product.title),
            is_accessory=is_accessory(product.category, product.title),
            is_footwear=is_footwear(product.category, product.title),
            product_id=product.product_id,
            title=product.title,
            images=product.display_images,
            average_rating=product.average_rating,
            review_highlights=product.review_highlights,
            garment_type=garment_type_for(product.category, product.title),
        )


class SearchResponse(BaseModel):
    query: str = Field(..., description="Original user query string")
    detected_language: Optional[str] = Field(None, description="ISO language code detected from the query")
    filters: Optional[dict] = Field(None, description="Filters applied, e.g. {'gender': 'women', 'color': 'red'}")
    results: List[SearchResult] = Field(..., description="Ranked products")

    @classmethod
    def from_outcome(cls, outcome: SearchOutcome) -> "SearchResponse":
        return cls(
            query=outcome.query,
            filters=outcome.applied_filters or None,
            results=[SearchResult.from_match(m) for m in outcome.matches],
        )
