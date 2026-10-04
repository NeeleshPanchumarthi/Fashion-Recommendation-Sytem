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
        scorable = [(c, candidate_text(c.product)) for c in candidates]
        unscorable = [c for c, text in scorable if not text]
        scorable = [(c, text) for c, text in scorable if text]

        scores = self._client.score([(query, text) for _, text in scorable])
        for (c, _), s in zip(scorable, scores):
            c.rerank_score = s
        for c in unscorable:
            c.rerank_score = float("-inf")

        ranked = sorted((c for c, _ in scorable), key=lambda c: c.rerank_score, reverse=True)
        return ranked + unscorable
