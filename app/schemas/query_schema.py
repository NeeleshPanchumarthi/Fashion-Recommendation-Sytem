from pydantic import BaseModel, Field
from typing import Optional, List

class QueryRequest(BaseModel):
    """Schema for the search request payload."""

    query: str = Field(..., description="User's natural language query for recommendation")
    vector: Optional[List[float]] = Field(None, description="Pre‑computed embedding vector (optional)")
    top_k: Optional[int] = Field(
        default=None,
        description="Number of results to return; falls back to default from settings if omitted",
    )
