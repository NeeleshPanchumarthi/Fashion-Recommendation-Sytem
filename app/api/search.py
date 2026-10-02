from fastapi import APIRouter, Depends
from ..config.settings import Settings
from ..schemas.query_schema import QueryRequest
from ..schemas.search_response_schema import SearchResponseSchema, SearchResult
from ..ingestion.embedding import embed_text
from ..ingestion.vector_store import query_vector

router = APIRouter()

@router.post("/search", response_model=SearchResponseSchema)
async def search(request: QueryRequest):
    """Execute a vector search against Pinecone."""
    # Instantiate settings to access configuration
    settings = Settings()
    # If a pre-computed vector isn't provided, embed the query text
    query_vec = request.vector if request.vector else embed_text(request.query)
    
    # Query Pinecone using our helper
    results = query_vector(query_vec, top_k=settings.TOP_K)
    
    hits = []
    for match in results:
        meta = match.get("metadata", {})
        style_str = meta.get("style")
        
        hit = SearchResult(
            product_id=match["id"],
            title=meta.get("title", "Unknown Title"),
            category=meta.get("category"),
            gender=meta.get("gender"),
            color=meta.get("color"),
            style=[style_str] if style_str else None,
            image_url=meta.get("images"),
            average_rating=meta.get("average_rating"),
            rating_number=meta.get("rating_number"),
            review_highlights=meta.get("overall_sentiment"),
            relevance_score=match["score"]
        )
        hits.append(hit)
        
    return SearchResponseSchema(query=request.query, results=hits)
