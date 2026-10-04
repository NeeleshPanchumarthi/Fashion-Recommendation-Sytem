"""HTTP-level tests: real app, routing, middleware and error handling, with
the external systems replaced by in-memory fakes (no network, no models)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import ServiceContainer
from app.main import create_app
from app.repositories.vector_repository import VectorRepository
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.query_processor import QueryProcessor
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Retriever
from app.services.health_service import HealthService
from app.services.search_service import SearchService
from tests.fakes import FakeEmbedder, FakeLLM, FakePineconeClient, FakeRerankerClient, product_vector

IMAGES = json.dumps([
    {"variant": "MAIN", "large": "https://img/main.jpg"},
    {"variant": "PT01", "large": "https://img/pt01.jpg"},
    {"variant": "PT02", "large": "https://img/pt02.jpg"},
])


def _client(pinecone: FakePineconeClient) -> TestClient:
    vectors = VectorRepository(pinecone)
    embedder, reranker, llm = FakeEmbedder(), FakeRerankerClient(), FakeLLM(enabled=False)
    pipeline = RetrievalPipeline(QueryProcessor(llm), embedder, Retriever(vectors, 50), Reranker(reranker), 30)
    container = ServiceContainer(
        embedder=embedder,
        reranker=reranker,
        search_service=SearchService(pipeline, default_top_k=10),
        health_service=HealthService(vectors, embedder, reranker, llm),
    )
    settings = Settings(PINECONE_API_KEY="test", WARM_MODELS_ON_STARTUP=False)
    return TestClient(create_app(settings=settings, container=container))


@pytest.fixture
def client():
    catalog = [
        product_vector("A1", "Men's Red Party Shirt", gender="men", category="shirt", average_rating=4.3,
                       images=IMAGES, review_highlights=json.dumps(["Great fit"])),
        product_vector("A2", "Women's Party Shirt", gender="women", category="shirt", average_rating=3.8),
    ]
    with _client(FakePineconeClient(catalog)) as c:
        yield c


def test_health_is_cheap_and_always_ok(client):
    assert client.get("/api/v1/health").json() == {"status": "ok", "service": "fashion-search"}


def test_ready_reports_dependency_checks(client):
    body = client.get("/api/v1/ready").json()
    assert body["status"] == "ready"
    assert body["checks"]["vector_db"] == {"ok": True, "index": "test-index", "vector_count": 2}
    assert body["checks"]["llm"]["required"] is False


def test_search_returns_the_frontend_contract(client):
    resp = client.post("/api/v1/search", json={"query": "shirt for college party"})
    assert resp.status_code == 200
    body = resp.json()
    # "party" is extracted as a style, then relaxed away: no product has it.
    assert body["filters"] == {"category": "shirt"}
    first = next(r for r in body["results"] if r["product_id"] == "A1")
    assert first == {
        "product_id": "A1",
        "title": "Men's Red Party Shirt",
        "images": ["https://img/main.jpg", "https://img/pt01.jpg"],  # MAIN + PT01 only
        "average_rating": 4.3,
        "review_highlights": ["Great fit"],
    }
    assert resp.headers["X-Request-ID"]


def test_request_id_is_propagated(client):
    resp = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["X-Request-ID"] == "abc123"


def test_validation_errors_are_422(client):
    assert client.post("/api/v1/search", json={"query": ""}).status_code == 422
    assert client.post("/api/v1/search", json={"query": "shirt", "top_k": 0}).status_code == 422


def test_blank_query_is_400_with_error_shape(client):
    resp = client.post("/api/v1/search", json={"query": "   "})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_request"
    assert resp.json()["request_id"] == resp.headers["X-Request-ID"]


def test_vector_db_outage_is_503_without_internals():
    with _client(FakePineconeClient([], fail_times=100)) as c:
        resp = c.post("/api/v1/search", json={"query": "red shirt"})
        assert resp.status_code == 503
        assert resp.json() == {
            "detail": "connection reset", "code": "dependency_unavailable", "request_id": resp.headers["X-Request-ID"],
        }
        assert c.get("/api/v1/ready").status_code == 503


def test_cors_allows_local_frontend_on_any_port(client):
    resp = client.options(
        "/api/v1/search",
        headers={"Origin": "http://localhost:5174", "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5174"
