"""Live checks against the real Pinecone index and models.

Skipped unless RUN_LIVE_TESTS=1, since they need network access, a valid
PINECONE_API_KEY and model downloads:

    RUN_LIVE_TESTS=1 pytest tests/integration/vector_db
"""

import os

import pytest

from app.core.config import get_settings
from app.dependencies import build_container, build_vector_repository
from app.domain.search import SearchFilters

pytestmark = pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="set RUN_LIVE_TESTS=1 to run")


def test_index_is_reachable():
    info = build_vector_repository(get_settings()).ping()
    assert info["vector_count"] > 0


def test_filtered_search_returns_matching_products():
    container = build_container(get_settings())
    outcome = container.search_service.search("black leather jacket for men")
    assert outcome.matches
    assert outcome.applied_filters.get("gender") == "men"
    assert all(m.product.gender == "men" for m in outcome.matches)


def test_vector_filter_round_trip():
    settings = get_settings()
    container = build_container(settings)
    vector = container.embedder.embed("red skirt")
    matches = build_vector_repository(settings).search(vector, 5, SearchFilters(category="skirt"))
    assert matches and all(m.product.category == "skirt" for m in matches)
