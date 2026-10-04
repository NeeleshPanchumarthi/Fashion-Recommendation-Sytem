"""Outfit queries: general requests ("an outfit for a party", "wedding
attire", "something to wear to college") that should return a complete look
-- topwear, bottomwear and footwear -- rather than one garment type.

A query is an outfit query when it uses a general clothing word and doesn't
name a specific garment. "dress" is a specific garment (a one-piece covering
top and bottom), so "a dress for a wedding" searches dresses only, just like
"black jeans" or "party shirt" search one category.
"""

from __future__ import annotations

import re
from typing import Optional

_GENERAL_TERMS = re.compile(
    r"\b(outfits?|dressed|attire|clothes|clothing|apparel|ensemble|wardrobe|"
    r"look|get-?up|wear|something to wear)\b",
    re.IGNORECASE,
)

# Garment groups searched for an outfit query, in display order. Values are
# the category tags assigned at ingestion (app/domain/attributes/vocabularies.py).
OUTFIT_GROUPS: dict[str, tuple[str, ...]] = {
    "tops": ("shirt", "t-shirt", "blouse", "sweater", "hoodie", "jacket", "coat"),
    "bottoms": ("pants", "trousers", "jeans", "shorts", "skirt"),
    "footwear": ("shoes", "sneakers"),
}

# Garment word substituted for the general term in each group's search text,
# so the footwear search looks for shoes rather than "an outfit".
GROUP_NOUNS = {"tops": "shirt", "bottoms": "pants", "footwear": "shoes"}


def is_outfit_query(query: str, category: Optional[str]) -> bool:
    """General clothing word, and no specific garment named."""
    return bool(_GENERAL_TERMS.search(query)) and category is None


def group_query(text: str, group: Optional[str]) -> str:
    """Search text for one outfit group: "outfit for a wedding" becomes
    "shoes for a wedding" for footwear. Appends the noun if no general
    term is present (e.g. an LLM-rewritten query)."""
    if group is None:
        return text
    noun = GROUP_NOUNS[group]
    replaced, count = _GENERAL_TERMS.subn(noun, text, count=1)
    return replaced if count else f"{text} {noun}"
