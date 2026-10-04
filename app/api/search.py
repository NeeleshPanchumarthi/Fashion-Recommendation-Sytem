import json
import logging

from fastapi import APIRouter, HTTPException

from ..config.settings import Settings
from ..ingestion.embedding import embed_text
from ..ingestion.vector_store import VectorStoreUnavailable, query_vector
from ..schemas.query_schema import QueryRequest
from ..schemas.search_response_schema import SearchResponseSchema, SearchResult
from ..search.filtering import RELAX_ORDER, build_pinecone_filter, relax_once
from ..search.gender_balance import gender_pools, interleave
from ..search.images import select_display_images
from ..search.query_understanding import FILTER_KEYS, build_query_understanding
from ..search.reranker import rerank

logger = logging.getLogger(__name__)
router = APIRouter()

# If a filtered search comes back with fewer than this many candidates,
# relax soft filters (see app/search/filtering.py) one at a time and retry,
# rather than returning a near-empty result set.
MIN_RESULTS_BEFORE_RELAX = 5
MAX_RELAX_STEPS = len(RELAX_ORDER)


def _dense_search(query_vec, top_k, pinecone_filter) -> list[dict]:
    try:
        return list(query_vector(query_vec, top_k=top_k, filter=pinecone_filter))
    except VectorStoreUnavailable as exc:
        # A clear 503 the frontend can show, instead of an opaque 500.
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _search_pool(query_vec, filters: dict, settings: Settings) -> tuple[list[dict], dict]:
    """Dense search for one filter set, relaxing soft filters one at a time
    while too few candidates come back. Returns (matches, filters used)."""
    matches = _dense_search(query_vec, settings.DENSE_SEARCH_K, build_pinecone_filter(filters))

    relax_steps = 0
    while len(matches) < MIN_RESULTS_BEFORE_RELAX and relax_steps < MAX_RELAX_STEPS:
        relaxed = relax_once(filters)
        if relaxed is None:
            break
        filters = relaxed
        matches = _dense_search(query_vec, settings.DENSE_SEARCH_K, build_pinecone_filter(filters))
        relax_steps += 1

    return matches, filters


@router.post("/search", response_model=SearchResponseSchema)
async def search(request: QueryRequest):
    """Filtered dense search + cross-encoder rerank.

    Pipeline:
      1. Query understanding: regex extractors (authoritative) + Groq LLM
         (fills gaps, proposes an expanded query for embedding -- never
         overrides a regex-resolved filter).
      2. Dense Pinecone search over the resolved filters, top DENSE_SEARCH_K.
         No gender in the query -> search a men's and a women's pool and
         interleave them (app/search/gender_balance.py), so "dress for
         wedding" shows both women's dresses and men's formal wear.
      3. If too few results, relax soft filters one at a time and retry
         (gender/category are never relaxed).
      4. Cross-encoder rerank the top RERANK_CANDIDATES_K candidates
         (split evenly across pools).
      5. Return the top TOP_K (default 10).
    """
    settings = Settings()

    understanding = build_query_understanding(request.query, settings)
    expanded_query = understanding["expanded_query"]
    filters = {key: understanding[key] for key in FILTER_KEYS}

    query_vec = request.vector if request.vector else embed_text(expanded_query)

    # Don't return more than we actually reranked.
    requested_top_k = request.top_k or settings.TOP_K
    final_k = min(requested_top_k, settings.RERANK_CANDIDATES_K)

    pools = gender_pools(filters)
    # Same total rerank cost whether we search one pool or two.
    per_pool_k = max(1, settings.RERANK_CANDIDATES_K // len(pools))

    ranked_pools = []
    pool_filters = []
    for pool in pools:
        matches, used = _search_pool(query_vec, pool, settings)
        ranked_pools.append(rerank(request.query, matches[:per_pool_k]))
        pool_filters.append(used)

    final = interleave(ranked_pools)[:final_k]

    hits = []
    for match in final:
        meta = match.get("metadata", {})

        # review_highlights is stored as list[str] in Pinecone
        highlights = meta.get("review_highlights")
        if isinstance(highlights, str):
            # Older vectors stored as JSON string -- parse gracefully
            try:
                highlights = json.loads(highlights)
            except Exception:
                highlights = [highlights] if highlights else None

        hit = SearchResult(
            product_id=match["id"],
            title=meta.get("title", "Unknown Title"),
            images=select_display_images(meta.get("images")),
            average_rating=meta.get("average_rating"),
            review_highlights=highlights,
        )
        hits.append(hit)

    # Report what the first pool actually used (after any relaxation),
    # minus the internal per-pool gender clause.
    applied_filters = {
        k: v for k, v in pool_filters[0].items()
        if v is not None and not (k == "gender" and filters["gender"] is None)
    }
    return SearchResponseSchema(query=request.query, filters=applied_filters or None, results=hits)
