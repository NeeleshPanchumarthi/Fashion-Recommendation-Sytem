"""Composition root: builds clients → repositories → retrieval → services.

Objects are created once per process (at API startup, or by the worker) and
shared, so models load once and connections are reused. Routes get services
through the FastAPI providers at the bottom, which tests can override.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request

from app.clients.embedding_client import EmbeddingClient
from app.clients.llm_client import LLMClient
from app.clients.pinecone_client import PineconeClient
from app.clients.reranker_client import RerankerClient
from app.clients.tryon_client import TryOnClient
from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.repositories.vector_repository import VectorRepository
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.query_processor import QueryProcessor
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Retriever
from app.services.health_service import HealthService
from app.services.search_service import SearchService
from app.services.tryon_service import TryOnService


def build_vector_repository(settings: Settings) -> VectorRepository:
    client = PineconeClient(
        api_key=settings.PINECONE_API_KEY.get_secret_value(),
        index_name=settings.PINECONE_INDEX,
        region=settings.PINECONE_REGION,
        connect_attempts=settings.PINECONE_CONNECT_ATTEMPTS,
    )
    return VectorRepository(client, upsert_batch_size=settings.UPSERT_BATCH_SIZE)


@dataclass
class ServiceContainer:
    embedder: EmbeddingClient
    reranker: RerankerClient
    search_service: SearchService
    health_service: HealthService
    tryon_service: Optional[TryOnService] = None

    def warm(self) -> None:
        """Load models now so the first search isn't slow."""
        self.embedder.warm()
        self.reranker.warm()

    def close(self) -> None:
        if self.tryon_service is not None:
            self.tryon_service.shutdown()


def build_container(settings: Settings) -> ServiceContainer:
    embedder = EmbeddingClient(settings.EMBEDDING_MODEL)
    reranker_client = RerankerClient(settings.CROSS_ENCODER_MODEL)
    llm = LLMClient(
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        model=settings.LLM_MODEL,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        connect_attempts=settings.LLM_CONNECT_ATTEMPTS,
    )
    vectors = build_vector_repository(settings)

    pipeline = RetrievalPipeline(
        query_processor=QueryProcessor(llm),
        embedder=embedder,
        retriever=Retriever(vectors, dense_k=settings.DENSE_SEARCH_K),
        reranker=Reranker(reranker_client),
        rerank_candidates_k=settings.RERANK_CANDIDATES_K,
        outfit_dense_k=settings.OUTFIT_DENSE_K,
    )
    return ServiceContainer(
        embedder=embedder,
        reranker=reranker_client,
        search_service=SearchService(pipeline, default_top_k=settings.TOP_K),
        health_service=HealthService(vectors, embedder, reranker_client, llm),
        tryon_service=build_tryon_service(settings),
    )


def build_tryon_service(settings: Settings) -> TryOnService:
    client = TryOnClient(
        space=settings.TRYON_SPACE,
        token=settings.HF_TOKEN.get_secret_value(),
        timeout_seconds=settings.TRYON_TIMEOUT_SECONDS,
    )
    return TryOnService(
        client,
        max_active_jobs=settings.TRYON_MAX_ACTIVE_JOBS,
        job_ttl_seconds=settings.TRYON_JOB_TTL_SECONDS,
        max_upload_bytes=settings.TRYON_MAX_UPLOAD_MB * 1024 * 1024,
        workers=settings.TRYON_WORKERS,
    )


# -- FastAPI providers -------------------------------------------------------

def get_search_service(request: Request) -> SearchService:
    return request.app.state.container.search_service


def get_health_service(request: Request) -> HealthService:
    return request.app.state.container.health_service


def get_tryon_service(request: Request) -> TryOnService:
    service = request.app.state.container.tryon_service
    if service is None:
        raise DependencyUnavailableError("tryon", "Virtual try-on is not available.")
    return service
