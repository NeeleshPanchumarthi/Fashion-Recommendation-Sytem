"""Storefront sections (Men / Women / Kids / Accessories) for a product.

Pure rules over fields already in the index -- no LLM, no extra Pinecone
call. The frontend tabs filter the returned results by these tags.
"""

from __future__ import annotations

import re
from typing import Optional

from app.domain.attributes.category_extractor import extract_category
from app.domain.attributes.gender_extractor import extract_gender

# Garments with no men's version; an untagged one is treated as women's.
_WOMEN_ONLY_CATEGORIES = {"dress", "skirt", "blouse"}
_ACCESSORY_CATEGORIES = {"hat", "cap"}
_ACCESSORY_WORDS = re.compile(
    r"\b(hats?|caps?|beanies?|scarf|scarves|belts?|bags?|handbags?|purses?|wallets?|backpacks?|"
    r"watch(?:es)?|sunglasses|glasses|jewel(?:ry|lery)|necklaces?|bracelets?|earrings?|"
    r"gloves?|mittens?|neckties?|bow ?ties?|hair ?(?:bands?|clips?)|headbands?)\b",
    re.IGNORECASE,
)


_FOOTWEAR_CATEGORIES = {"shoes", "sneakers"}
_FOOTWEAR_WORDS = re.compile(
    r"\b(shoes?|sneakers?|boots?|sandals?|heels?|loafers?|slippers?|flats|pumps|oxfords?|"
    r"moccasins?|flip[- ]?flops?|footwear|trainers?)\b",
    re.IGNORECASE,
)


def is_footwear(category: Optional[str], title: str) -> bool:
    return (category or "").lower() in _FOOTWEAR_CATEGORIES or bool(_FOOTWEAR_WORDS.search(title))


def effective_gender(gender: Optional[str], category: Optional[str], title: str) -> Optional[str]:
    """men | women | kids | unisex, or None when the product doesn't say.
    Falls back to the title for products indexed before gender extraction."""
    gender = (gender or "").lower()
    if gender not in ("men", "women", "kids", "unisex"):
        gender = extract_gender(title) or ""
    if gender:
        return gender
    category = category or extract_category(title)
    return "women" if category in _WOMEN_ONLY_CATEGORIES else None


def is_accessory(category: Optional[str], title: str) -> bool:
    """Hats, bags, belts, watches... Footwear is its own section, not an accessory."""
    if is_footwear(category, title):
        return False
    return (category or "").lower() in _ACCESSORY_CATEGORIES or bool(_ACCESSORY_WORDS.search(title))
