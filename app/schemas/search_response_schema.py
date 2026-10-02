from pydantic import BaseModel, Field
from typing import List, Optional

class SearchResult(BaseModel):
    """Individual product entry in the search response."""

    product_id: str = Field(..., description="Product identifier (parent_asin)")
    title: str = Field(..., description="Product title")
    category: Optional[str] = Field(None, description="Category tag")
    gender: Optional[str] = Field(None, description="Gender tag")
    color: Optional[str] = Field(None, description="Primary color")
    style: Optional[List[str]] = Field(None, description="List of style tags")
    image_url: Optional[str] = Field(None, description="URL of the main product image")
    average_rating: Optional[float] = Field(None, description="Average rating")
    rating_number: Optional[int] = Field(None, description="Number of ratings")
    review_highlights: Optional[str] = Field(None, description="LLM‑generated review summary")
    relevance_score: float = Field(..., description="Combined relevance score (0‑1 range)")

class SearchResponseSchema(BaseModel):
    """Full response payload for the /search endpoint."""

    query: str = Field(..., description="Original user query string")
    detected_language: Optional[str] = Field(None, description="ISO language code detected from the query")
    filters: Optional[dict] = Field(
        None, description="Dictionary of applied hard filters (e.g., {'gender': 'women', 'color': 'red'})"
    )
    results: List[SearchResult] = Field(..., description="List of ranked products")
