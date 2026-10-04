import json

from app.domain.search import SearchFilters
from app.repositories.vector_repository import (
    VectorRepository,
    decode_product,
    encode_metadata,
    to_pinecone_filter,
)
from tests.fakes import FakePineconeClient, product_vector


def test_builds_pinecone_clauses():
    filters = SearchFilters(gender="men", category="shirt", color="black", min_rating=4.0, sentiment="positive")
    assert to_pinecone_filter(filters) == {
        "gender": "men",
        "category": "shirt",
        "color": "black",
        "overall_sentiment": "positive",
        "average_rating": {"$gte": 4.0},
    }


def test_excluded_genders_become_nin_unless_gender_is_set():
    assert to_pinecone_filter(SearchFilters(exclude_genders=("men", "kids"))) == {"gender": {"$nin": ["men", "kids"]}}
    assert to_pinecone_filter(SearchFilters(gender="women", exclude_genders=("men",))) == {"gender": "women"}


def test_no_filters_returns_none():
    assert to_pinecone_filter(SearchFilters()) is None


def test_encode_metadata_keeps_the_stored_vector_schema():
    images = [{"variant": "MAIN", "large": "L"}]
    metadata = encode_metadata({
        "title": "Red Shirt",
        "images": images,
        "review_highlights": ["Great", "Bad fit"],
        "average_rating": 4.5,
        "price": 19.99,          # not a metadata field
        "combined_text": "x",    # not a metadata field
        "color": None,           # missing values are dropped
    })
    assert metadata == {
        "title": "Red Shirt",
        "images": json.dumps(images),
        "review_highlights": json.dumps(["Great", "Bad fit"]),
        "average_rating": 4.5,
    }


def test_decode_product_round_trips_encoded_metadata():
    images = [{"variant": "MAIN", "large": "L"}, {"variant": "PT01", "large": "P"}]
    product = decode_product("A1", encode_metadata({
        "title": "Red Shirt", "images": images, "review_highlights": ["Great"], "rating_number": 12.0,
    }))
    assert product.product_id == "A1"
    assert product.images == images
    assert product.review_highlights == ["Great"]
    assert product.rating_number == 12
    assert product.display_images == ["L", "P"]


def test_decode_product_accepts_a_bare_image_url():
    assert decode_product("A1", {"title": "T", "images": "http://x.jpg"}).display_images == ["http://x.jpg"]


def test_search_returns_domain_matches():
    client = FakePineconeClient([product_vector("A1", "Red Shirt", gender="men")])
    matches = VectorRepository(client).search([0.0], 5, SearchFilters(gender="men"))
    assert [m.product.title for m in matches] == ["Red Shirt"]
    assert client.queries == [{"gender": "men"}]


def test_upsert_writes_in_batches():
    client = FakePineconeClient()
    records = [(f"A{i}", [0.0], {"title": f"P{i}"}) for i in range(5)]
    assert VectorRepository(client, upsert_batch_size=2).upsert(records) == 5
    assert [len(b) for b in client.upsert_batches] == [2, 2, 1]
