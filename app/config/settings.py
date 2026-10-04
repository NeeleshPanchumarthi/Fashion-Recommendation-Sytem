import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Groq
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Embeddings
    EMBEDDING_MODEL: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_INDEX: str = "fashionvectors"
    PINECONE_ENVIRONMENT: str = "us-east-1"
    
    # PostgreSQL
    POSTGRES_URL: str

    # Retrieval
    TOP_K: int = 10
    RERANK_TOP_K: int = 10
    RRF_K: int = 10

    # Dense search + cross-encoder reranking (app/search/)
    DENSE_SEARCH_K: int = 50        # candidates pulled from Pinecone before reranking
    RERANK_CANDIDATES_K: int = 30   # how many of those get cross-encoder reranked
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    model_config = SettingsConfigDict(
        env_file=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../.env",
            )
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __repr__(self) -> str:
        safe = {
            "GROQ_MODEL": self.GROQ_MODEL,
            "EMBEDDING_MODEL": self.EMBEDDING_MODEL,
            "PINECONE_INDEX": self.PINECONE_INDEX,
            "PINECONE_ENVIRONMENT": self.PINECONE_ENVIRONMENT,
            "POSTGRES_URL": "<redacted>",
            "TOP_K": self.TOP_K,
            "RERANK_TOP_K": self.RERANK_TOP_K,
            "RRF_K": self.RRF_K,
            "DENSE_SEARCH_K": self.DENSE_SEARCH_K,
            "RERANK_CANDIDATES_K": self.RERANK_CANDIDATES_K,
            "CROSS_ENCODER_MODEL": self.CROSS_ENCODER_MODEL,
        }

        return f"Settings({safe})"