import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    The .env file located at the project root is read automatically. All
    variables have sensible defaults where appropriate, but the critical
    values (API keys, database URLs, etc.) must be provided by the user.
    """

    # LLM configuration
    GROQ_API_KEY: str
    GROQ_MODEL: str = "mixtral-8x7b-32768"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Vector store configuration (Pinecone)
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_INDEX: str = "fashionvectors"

    # PostgreSQL configuration
    POSTGRES_URL: str

    # Retrieval parameters
    TOP_K: int = 50
    RERANK_TOP_K: int = 10
    RRF_K: int = 60

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.env")
        env_file_encoding = "utf-8"

    def __repr__(self) -> str:
        # Avoid leaking secrets in logs
        safe = {
            "GROQ_MODEL": self.GROQ_MODEL,
            "EMBEDDING_MODEL": self.EMBEDDING_MODEL,
            "QDRANT_URL": self.QDRANT_URL,
            "QDRANT_COLLECTION": self.QDRANT_COLLECTION,
            "POSTGRES_URL": "<redacted>",
            "TOP_K": self.TOP_K,
            "RERANK_TOP_K": self.RERANK_TOP_K,
            "RRF_K": self.RRF_K,
        }
        return f"Settings({safe})"
