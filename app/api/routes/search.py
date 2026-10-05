"""POST /api/search -- natural-language product search."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_search_service
from app.schemas.common import ErrorResponse
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter(tags=["search"])


# Plain `def`, not `async def`: the search does blocking model inference and
# network calls, so FastAPI runs it in a worker thread instead of blocking
# the event loop for every other request.
@router.post(
    "/search",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def search_products(request: SearchRequest, service: SearchService = Depends(get_search_service)) -> SearchResponse:
    outcome = service.search(request.query, top_k=request.top_k, vector=request.vector)
    return SearchResponse.from_outcome(outcome)
