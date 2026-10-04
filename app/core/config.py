"""Centralized service configuration.

Every setting comes from environment variables (or the project-root .env
file in local development). Secrets have no defaults and are never logged.
Older variable names (GROQ_MODEL, PINECONE_ENVIRONMENT) are still accepted
so existing .env files keep working.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service
    SERVICE_NAME: str = "fashion-search"
    LOG_LEVEL: str = "INFO"
    # Browser origins allowed to call the API (any local port by default,
    # since Vite falls back to 5174, 5175... when 5173 is taken).
    CORS_ORIGIN_REGEX: str = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

    # Pinecone (vector database)
    PINECONE_API_KEY: SecretStr
    PINECONE_INDEX: str = "fashionvectors"
    PINECONE_REGION: str = Field(
        "us-east-1", validation_alias=AliasChoices("PINECONE_REGION", "PINECONE_ENVIRONMENT")
    )
    PINECONE_CONNECT_ATTEMPTS: int = 3

    # LLM (Groq) -- optional: without a key, query understanding is regex-only.
    GROQ_API_KEY: SecretStr = SecretStr("")
    LLM_MODEL: str = Field("openai/gpt-oss-120b", validation_alias=AliasChoices("LLM_MODEL", "GROQ_MODEL"))
    LLM_TIMEOUT_SECONDS: float = 6.0
    LLM_CONNECT_ATTEMPTS: int = 2

    # Models
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    SENTIMENT_MODEL: str = "nlptown/bert-base-multilingual-uncased-sentiment"
    # Load models at API startup instead of on the first request.
    WARM_MODELS_ON_STARTUP: bool = True

    # Retrieval
    TOP_K: int = 12                  # results returned when the request doesn't say
    DENSE_SEARCH_K: int = 40         # Pinecone candidates per search (normal queries)
    OUTFIT_DENSE_K: int = 10         # Pinecone candidates per search (outfit queries: one per group)
    RERANK_CANDIDATES_K: int = 24    # total candidates cross-encoder reranked, split across searches

    # Ingestion worker
    METADATA_PATH: Path = PROJECT_ROOT / "data" / "metadata.parquet"
    REVIEWS_PATH: Path = PROJECT_ROOT / "data" / "reviews.parquet"
    BATCH_SIZE: int = 15_000         # products per batch
    CHECKPOINT_PATH: Path = PROJECT_ROOT / "data" / "checkpoints" / "ingestion_state.json"
    FAILURE_LOG_PATH: Path = PROJECT_ROOT / "data" / "checkpoints" / "ingestion_failures.log"
    DUCKDB_MEMORY_LIMIT: str = "2GB"
    UPSERT_BATCH_SIZE: int = 100
    UPSERT_RETRIES: int = 3
    SENTIMENT_BATCH_SIZE: int = 32

    @property
    def llm_enabled(self) -> bool:
        return bool(self.GROQ_API_KEY.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings, read once."""
    return Settings()
