"""In-memory stand-ins for external systems (Pinecone, models, LLM)."""

from __future__ import annotations

from typing import Any, Optional

from app.core.exceptions import DependencyUnavailableError


class FakeLLM:
    def __init__(self, response: Optional[dict] = None, fail: bool = False, enabled: bool = True) -> None:
        self.response = response or {}
        self.fail = fail
        self.enabled = enabled
        self.calls: list[str] = []

    def complete_json(self, system_prompt: str, user_message: str) -> dict:
        self.calls.append(user_message)
        if self.fail:
            raise DependencyUnavailableError("llm", "connection reset")
        return self.response


class FakeEmbedder:
    dimension = 3
    loaded = True

    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.texts.append(text)
        return [float(len(text)), 0.0, 1.0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def warm(self) -> None:
        pass


class FakeRerankerClient:
    """Scores a pair by how many query words appear in the text."""

    loaded = True

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        return [float(sum(w in text.lower() for w in query.lower().split())) for query, text in pairs]

    def warm(self) -> None:
        pass


class FakePineconeClient:
    """Stores vectors in memory and applies the subset of Pinecone's filter
    syntax the repository emits (equality, $in, $nin, $gte)."""

    def __init__(self, vectors: Optional[list[dict[str, Any]]] = None, fail_times: int = 0) -> None:
        self.vectors = {v["id"]: v for v in (vectors or [])}
        self.queries: list[Optional[dict]] = []
        self.upsert_batches: list[list[dict]] = []
        self.fail_times = fail_times
        self.created_dimension: Optional[int] = None

    def _maybe_fail(self) -> None:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise DependencyUnavailableError("pinecone", "connection reset")

    @staticmethod
    def _matches(metadata: dict, flt: Optional[dict]) -> bool:
        for key, cond in (flt or {}).items():
            value = metadata.get(key)
            if isinstance(cond, dict):
                if "$nin" in cond and value in cond["$nin"]:
                    return False
                if "$in" in cond and value not in cond["$in"]:
                    return False
                if "$gte" in cond and (value is None or value < cond["$gte"]):
                    return False
            elif value != cond:
                return False
        return True

    def query(self, vector, top_k, filter):
        self._maybe_fail()
        self.queries.append(filter)
        hits = [v for v in self.vectors.values() if self._matches(v["metadata"], filter)]
        return [{"id": v["id"], "score": 0.5, "metadata": v["metadata"]} for v in hits[:top_k]]

    def upsert(self, vectors):
        self._maybe_fail()
        self.upsert_batches.append(vectors)
        for v in vectors:
            self.vectors[v["id"]] = v

    def ensure_index(self, dimension: int) -> None:
        self.created_dimension = dimension

    def ping(self):
        self._maybe_fail()
        return {"index": "test-index", "vector_count": len(self.vectors)}


class FakeSentimentClient:
    """Rating-free stand-in: 'great'/'love' → positive, 'bad' → negative."""

    def classify(self, texts: list[str]) -> list[str]:
        out = []
        for t in texts:
            t = t.lower()
            out.append("positive" if ("great" in t or "love" in t) else "negative" if "bad" in t else "neutral")
        return out


def product_vector(pid: str, title: str, **metadata: Any) -> dict[str, Any]:
    return {"id": pid, "values": [0.0, 0.0, 1.0], "metadata": {"title": title, **metadata}}
