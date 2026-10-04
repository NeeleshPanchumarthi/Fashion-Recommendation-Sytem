"""Candidate retrieval: filtered dense search with relaxation, and
gender-balanced pools for queries that don't name a gender.

Gender balancing: "I need a dress for wedding" says nothing about gender,
but a single dense search for it returns almost only women's dresses -- the
word "dress" pulls the embedding there. So when no gender is resolved we
search two pools and interleave their reranked results:

  - men:    gender == "men"
  - others: gender not in (men, kids)   (women, unisex, not specified)

Kids' items only appear when the query asks for them ("kids" resolves to
gender = kids and takes the single-pool path). For the men's pool,
categories that mean formal wear rather than a garment ("dress" -> dress
shirts, suits, tuxedos) are dropped. Women-only garments (skirt, blouse)
stay filtered, so that pool simply comes back empty.
"""

from __future__ import annotations

from dataclasses import replace

from app.domain.product import ProductMatch
from app.domain.search import RELAX_ORDER, SearchFilters
from app.repositories.vector_repository import VectorRepository

# If a filtered search returns fewer candidates than this, relax soft
# filters one at a time and retry rather than return a near-empty page.
MIN_RESULTS_BEFORE_RELAX = 5
MAX_RELAX_STEPS = len(RELAX_ORDER)

# Categories that, for men, describe an occasion/formality rather than the
# garment itself, so they must not be applied as a hard filter.
MEN_DROP_CATEGORIES = {"dress"}

MEN = "men"
KIDS = "kids"


def gender_pools(filters: SearchFilters) -> list[SearchFilters]:
    """Filter sets to search. One set (unchanged) when a gender was resolved;
    otherwise a women/unisex/unspecified pool and a men's pool."""
    if filters.gender is not None:
        return [filters]

    men = replace(filters, gender=MEN)
    if men.category in MEN_DROP_CATEGORIES:
        men = replace(men, category=None)

    others = replace(filters, exclude_genders=(MEN, KIDS))
    return [others, men]


def interleave(ranked_pools: list[list[ProductMatch]]) -> list[ProductMatch]:
    """Merge per-pool ranked lists, alternating between pools. The pool with
    the best top match goes first; an exhausted pool is skipped. Duplicate
    products keep their first position."""
    pools = [list(p) for p in ranked_pools if p]
    pools.sort(key=lambda p: p[0].relevance, reverse=True)

    merged: list[ProductMatch] = []
    seen: set[str] = set()
    for rank in range(max((len(p) for p in pools), default=0)):
        for pool in pools:
            if rank < len(pool) and pool[rank].product.product_id not in seen:
                seen.add(pool[rank].product.product_id)
                merged.append(pool[rank])
    return merged


class Retriever:
    def __init__(self, vectors: VectorRepository, dense_k: int) -> None:
        self._vectors = vectors
        self.dense_k = dense_k

    def retrieve(self, vector: list[float], filters: SearchFilters) -> tuple[list[ProductMatch], SearchFilters]:
        """Dense search, relaxing soft filters one at a time while too few
        candidates come back. Returns (matches, filters actually used)."""
        matches = self._vectors.search(vector, self.dense_k, filters)

        steps = 0
        while len(matches) < MIN_RESULTS_BEFORE_RELAX and steps < MAX_RELAX_STEPS:
            relaxed = filters.relaxed()
            if relaxed is None:
                break
            filters = relaxed
            matches = self._vectors.search(vector, self.dense_k, filters)
            steps += 1

        return matches, filters
