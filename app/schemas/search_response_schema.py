from pydantic import BaseModel, Field
from typing import List, Optional

class SearchResult(BaseModel):
    """Individual product entry in the search response.

    Kept deliberately lean: only what the frontend product card displays.
    """

    product_id: str = Field(..., description="Product identifier (parent_asin)")
    title: str = Field(..., description="Product title")
    images: List[str] = Field(
        default_factory=list,
        description="Large image URLs for the card carousel: MAIN first, then PT01 and any angle shots (front/back/left/right/top/bottom/side)",
    )
    average_rating: Optional[float] = Field(None, description="Average rating")
    review_highlights: Optional[List[str]] = Field(None, description="Enriched review snippets (60% positive / 20% neutral / 20% negative mix)")

class SearchResponseSchema(BaseModel):
    """Full response payload for the /search endpoint."""

    query: str = Field(..., description="Original user query string")
    detected_language: Optional[str] = Field(None, description="ISO language code detected from the query")
    filters: Optional[dict] = Field(
        None, description="Dictionary of applied hard filters (e.g., {'gender': 'women', 'color': 'red'})"
    )
    results: List[SearchResult] = Field(..., description="List of ranked products")
