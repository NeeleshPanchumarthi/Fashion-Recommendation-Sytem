"""HTTP-level tests: real app, routing, middleware and error handling, with
the external systems replaced by in-memory fakes (no network, no models)."""

import io
import json
import time

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
from app.services.tryon_service import TryOnService
from tests.fakes import (
    FakeEmbedder, FakeLLM, FakePineconeClient, FakeRerankerClient, FakeTryOnClient, product_vector,
)

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
        tryon_service=TryOnService(FakeTryOnClient()),
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
    assert client.get("/api/health").json() == {"status": "ok", "service": "fashion-search"}


def test_ready_reports_dependency_checks(client):
    body = client.get("/api/ready").json()
    assert body["status"] == "ready"
    assert body["checks"]["vector_db"] == {"ok": True, "index": "test-index", "vector_count": 2}
    assert body["checks"]["llm"]["required"] is False


def test_search_returns_the_frontend_contract(client):
    resp = client.post("/api/search", json={"query": "shirt for college party"})
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
        "garment_type": "upper_body",
        "gender": "men",
        "is_accessory": False,
        "is_footwear": False,
    }
    assert resp.headers["X-Request-ID"]


def test_request_id_is_propagated(client):
    resp = client.get("/api/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["X-Request-ID"] == "abc123"


def test_validation_errors_are_422(client):
    assert client.post("/api/search", json={"query": ""}).status_code == 422
    assert client.post("/api/search", json={"query": "shirt", "top_k": 0}).status_code == 422


def test_blank_query_is_400_with_error_shape(client):
    resp = client.post("/api/search", json={"query": "   "})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_request"
    assert resp.json()["request_id"] == resp.headers["X-Request-ID"]


def test_vector_db_outage_is_503_without_internals():
    with _client(FakePineconeClient([], fail_times=100)) as c:
        resp = c.post("/api/search", json={"query": "red shirt"})
        assert resp.status_code == 503
        assert resp.json() == {
            "detail": "connection reset", "code": "dependency_unavailable", "request_id": resp.headers["X-Request-ID"],
        }
        assert c.get("/api/ready").status_code == 503


def test_cors_allows_local_frontend_on_any_port(client):
    resp = client.options(
        "/api/search",
        headers={"Origin": "http://localhost:5174", "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5174"


def _photo() -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (900, 1200), (200, 180, 160)).save(out, format="JPEG")
    return out.getvalue()


TRY_ON_FORM = {"garment_image_url": "https://m.media-amazon.com/images/I/x.jpg", "garment_type": "upper_body"}


def test_try_on_job_is_started_then_polled_to_a_result(client):
    resp = client.post(
        "/api/try-on", data=TRY_ON_FORM, files={"person_image": ("me.jpg", _photo(), "image/jpeg")}
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    deadline = time.monotonic() + 5
    while (body := client.get(f"/api/try-on/{job_id}").json())["stage"] != "done":
        assert time.monotonic() < deadline, body
        time.sleep(0.01)
    assert body["result_image"].startswith("data:image/webp;base64,")
    assert body["error"] is None


def test_try_on_rejects_non_catalog_garment_url(client):
    resp = client.post(
        "/api/try-on",
        data={**TRY_ON_FORM, "garment_image_url": "https://evil.example.com/x.jpg"},
        files={"person_image": ("me.jpg", _photo(), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_request"


def test_try_on_requires_a_photo(client):
    assert client.post("/api/try-on", data=TRY_ON_FORM).status_code == 422


def test_unknown_try_on_job_is_404(client):
    assert client.get("/api/try-on/does-not-exist").status_code == 404
