import os

# The API module builds Settings at import time, which requires a Pinecone
# key. Tests never reach Pinecone (fakes are injected), so any value works;
# a real key from .env is used instead when present.
os.environ.setdefault("PINECONE_API_KEY", "test-key")
