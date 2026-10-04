"""Candidate retrieval: filtered dense search with relaxation, and
gender-balanced pools for queries that don't name a gender.

Gender balancing: "an outfit for a wedding" says nothing about gender, but
a single dense search can return almost only one gender's products. So when
no gender is resolved we search two pools and interleave their reranked
results:

  - men:    gender == "men"
  - others: gender not in (men, kids)   (women, unisex, not specified)

Kids' items only appear when the query asks for them ("kids" resolves to
gender = kids and takes the single-pool path). Women's garments (dress,
skirt, blouse) skip the men's pool entirely: there are no men's dresses, and
searching anyway only surfaces mis-tagged items like "Mens Dress Shirt".
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from app.domain.outfit import OUTFIT_GROUPS
from app.domain.product import ProductMatch
from app.domain.search import RELAX_ORDER, SearchFilters
from app.repositories.vector_repository import VectorRepository

# If a filtered search returns fewer candidates than this, relax soft
# filters one at a time and retry rather than return a near-empty page.
MIN_RESULTS_BEFORE_RELAX = 5
MAX_RELAX_STEPS = len(RELAX_ORDER)

# Garments with no men's version: no men's pool is searched for these.
WOMEN_ONLY_CATEGORIES = {"dress", "skirt", "blouse"}

MEN = "men"
KIDS = "kids"


def gender_pools(filters: SearchFilters) -> list[SearchFilters]:
    """Filter sets to search. One set (unchanged) when a gender was resolved;
    otherwise a women/unisex/unspecified pool, plus a men's pool unless the
    garment is women-only."""
    if filters.gender is not None:
        return [filters]

    others = replace(filters, exclude_genders=(MEN, KIDS))
    if filters.category in WOMEN_ONLY_CATEGORIES:
        return [others]
    return [others, replace(filters, gender=MEN)]


@dataclass(frozen=True)
class SubQuery:
    """One dense search: a gender pool, optionally narrowed to an outfit group."""

    filters: SearchFilters
    group: Optional[str] = None  # outfit group name, None for a normal search


def plan_subqueries(filters: SearchFilters, outfit: bool) -> list[SubQuery]:
    """Gender pools, and for outfit queries one search per garment group in
    each pool (e.g. no gender: 3 groups x 2 pools = 6 searches)."""
    pools = gender_pools(filters)
    if not outfit:
        return [SubQuery(pool) for pool in pools]

    # No style filter in outfit searches: the occasion ("party") is already in
    # each group's search text, and style tags are sparse -- most real dress
    # shoes aren't tagged "party", but shoe charms are.
    return [
        SubQuery(replace(pool, category=None, categories=categories, style=None), group)
        for pool in pools
        for group, categories in OUTFIT_GROUPS.items()
    ]


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

    def retrieve(
        self,
        vector: list[float],
        filters: SearchFilters,
        dense_k: Optional[int] = None,
        relax_all_at_once: bool = False,
    ) -> tuple[list[ProductMatch], SearchFilters]:
        """Dense search, relaxing soft filters while too few candidates come
        back. Returns (matches, filters actually used).

        relax_all_at_once: drop every soft filter in a single retry instead
        of one at a time -- used when many searches run per request, so each
        costs at most two Pinecone calls.
        """
        k = dense_k or self.dense_k
        matches = self._vectors.search(vector, k, filters)

        steps = 0
        while len(matches) < MIN_RESULTS_BEFORE_RELAX and steps < MAX_RELAX_STEPS:
            relaxed = filters.without_soft_filters() if relax_all_at_once else filters.relaxed()
            if relaxed is None:
                break
            filters = relaxed
            matches = self._vectors.search(vector, k, filters)
            steps += 1
            if relax_all_at_once:
                break

        return matches, filters
