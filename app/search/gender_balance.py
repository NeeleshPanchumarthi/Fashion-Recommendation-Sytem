"""Gender-balanced retrieval for queries that don't name a gender.

"I need a dress for wedding" says nothing about gender, but a single dense
search for it returns almost only women's dresses -- the word "dress" pulls
the embedding there. So when no gender is resolved we search two pools and
interleave their reranked results:

  - men:    gender == "men"
  - others: gender not in (men, kids)   (women, unisex, not specified)

Kids' items only appear when the query asks for them ("kids", resolved as
gender = kids, takes the single-pool path).

For the men's pool, categories that mean formal wear rather than a garment
("dress" -> dress shirts, suits, tuxedos) are dropped. Women-only garments
(skirt, blouse) stay filtered, so that pool simply comes back empty and only
women's results are shown.
"""

from __future__ import annotations

# Categories that, for men, describe an occasion/formality rather than the
# garment itself, so they must not be applied as a hard filter.
MEN_DROP_CATEGORIES = {"dress"}

MEN = "men"
KIDS = "kids"


def gender_pools(filters: dict) -> list[dict]:
    """Filter sets to search. One set (unchanged) when a gender was resolved;
    otherwise a men's pool and a women/unisex/unspecified pool."""
    if filters.get("gender") is not None:
        return [filters]

    men = dict(filters, gender=MEN)
    if men.get("category") in MEN_DROP_CATEGORIES:
        men["category"] = None

    others = dict(filters, gender={"$nin": [MEN, KIDS]})
    return [others, men]


def interleave(ranked_pools: list[list[dict]]) -> list[dict]:
    """Merge per-pool ranked lists, alternating between pools. The pool with
    the best top match goes first; an exhausted pool is skipped. Duplicate
    ids keep their first position."""
    pools = [list(p) for p in ranked_pools if p]
    pools.sort(key=lambda p: p[0].get("rerank_score", p[0].get("score", 0.0)), reverse=True)

    merged: list[dict] = []
    seen: set[str] = set()
    for rank in range(max((len(p) for p in pools), default=0)):
        for pool in pools:
            if rank < len(pool) and pool[rank]["id"] not in seen:
                seen.add(pool[rank]["id"])
                merged.append(pool[rank])
    return merged
