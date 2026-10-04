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

from typing import List

from sentence_transformers import CrossEncoder

from app.config.settings import Settings

_model = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        settings = Settings()
        _model = CrossEncoder(settings.CROSS_ENCODER_MODEL)
    return _model


def _candidate_text(metadata: dict) -> str:
    parts = [
        str(metadata.get("title") or ""),
        str(metadata.get("description") or ""),
        str(metadata.get("category") or ""),
        str(metadata.get("color") or ""),
        str(metadata.get("style") or ""),
        str(metadata.get("gender") or ""),
    ]
    return " ".join(p for p in parts if p).strip()


def rerank(query: str, candidates: List[dict]) -> List[dict]:
    """candidates: list of dicts each with at least 'id', 'score' (the
    original cosine score from Pinecone), and 'metadata'. Returns the SAME
    list, re-sorted by cross-encoder score, with 'rerank_score' added to
    each item. A candidate with no usable text is kept (sorted to the
    bottom) rather than dropped, so counts stay predictable upstream."""
    if not candidates:
        return candidates

    model = _get_model()
    pairs = []
    scorable = []
    unscorable = []
    for c in candidates:
        text = _candidate_text(c.get("metadata", {}))
        if text:
            pairs.append((query, text))
            scorable.append(c)
        else:
            c["rerank_score"] = float("-inf")
            unscorable.append(c)

    if pairs:
        scores = model.predict(pairs)
        for c, s in zip(scorable, scores):
            c["rerank_score"] = float(s)

    ranked = sorted(scorable, key=lambda c: c["rerank_score"], reverse=True)
    return ranked + unscorable
