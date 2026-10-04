"""Composition root: builds clients → repositories → retrieval → services.

Objects are created once per process (at API startup, or by the worker) and
shared, so models load once and connections are reused. Routes get services
through the FastAPI providers at the bottom, which tests can override.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.clients.embedding_client import EmbeddingClient
from app.clients.llm_client import LLMClient
from app.clients.pinecone_client import PineconeClient
from app.clients.reranker_client import RerankerClient
from app.core.config import Settings
from app.repositories.vector_repository import VectorRepository
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.query_processor import QueryProcessor
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Retriever
from app.services.health_service import HealthService
from app.services.search_service import SearchService


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

    def warm(self) -> None:
        """Load models now so the first search isn't slow."""
        self.embedder.warm()
        self.reranker.warm()


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
    )
    return ServiceContainer(
        embedder=embedder,
        reranker=reranker_client,
        search_service=SearchService(pipeline, default_top_k=settings.TOP_K),
        health_service=HealthService(vectors, embedder, reranker_client, llm),
    )


# -- FastAPI providers -------------------------------------------------------

def get_search_service(request: Request) -> SearchService:
    return request.app.state.container.search_service


def get_health_service(request: Request) -> HealthService:
    return request.app.state.container.health_service
