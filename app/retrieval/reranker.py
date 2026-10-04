"""Cross-encoder reranking for the top dense-retrieval candidates.

Cosine similarity (used by the dense Pinecone search) compares two
INDEPENDENTLY computed vectors -- it's a decent first pass but a
cross-encoder, which feeds the query and a candidate's text TOGETHER
through one forward pass, is measurably better at fine-grained relevance
ranking. It's too slow to run over the whole catalog (hence only dense
search touches all 826k products), which is exactly why it only runs on
the already-small candidate set dense search returns.
"""

from __future__ import annotations

from app.clients.reranker_client import RerankerClient
from app.domain.product import Product, ProductMatch


def candidate_text(product: Product) -> str:
    parts = [
        product.title,
        product.description,
        product.category,
        product.color,
        product.style,
        product.gender,
    ]
    return " ".join(str(p) for p in parts if p).strip()


class Reranker:
    def __init__(self, client: RerankerClient) -> None:
        self._client = client

    def rerank(self, query: str, candidates: list[ProductMatch]) -> list[ProductMatch]:
        """Return the candidates sorted by cross-encoder score, with
        rerank_score set. A candidate with no usable text is kept (sorted to
        the bottom) rather than dropped, so counts stay predictable."""
        self.score([(query, c) for c in candidates])
        return sorted(candidates, key=lambda c: c.rerank_score, reverse=True)

    def score(self, pairs: list[tuple[str, ProductMatch]]) -> None:
        """Set rerank_score on each candidate against its own query, in ONE
        batched model call (outfit groups each have their own query text)."""
        items = [(query, c, candidate_text(c.product)) for query, c in pairs]
        for _, c, text in items:
            if not text:
                c.rerank_score = float("-inf")
        scorable = [item for item in items if item[2]]
        scores = self._client.score([(query, text) for query, _, text in scorable])
        for (_, c, _), s in zip(scorable, scores):
            c.rerank_score = s
