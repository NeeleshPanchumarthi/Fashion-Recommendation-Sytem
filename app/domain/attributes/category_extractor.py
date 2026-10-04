"""Category extraction utilities for product titles.

This module provides a deterministic, rule-based extractor that maps free-form
text in a product title to one of the canonical categories defined in
:pydata:`app.domain.attributes.vocabularies.CATEGORIES`.
"""

from __future__ import annotations

import re
from typing import Optional

from .vocabularies import CATEGORIES


def _normalize_token(token: str) -> str:
    """Return a normalized version of *token* for category matching."""
    token = token.lower()
    token = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", token)
    # Synonyms and mapping
    if token in ("tshirt", "tee", "t-shirt"):
        return "t-shirt"
    if token in ("trousers", "pant", "pants"):
        return "pants"
    if token in ("sneaker", "sneakers", "kicks"):
        return "sneakers"
    if token in ("boot", "boots", "shoe", "shoes"):
        return "shoes"
    if token in ("caps", "cap", "hats", "hat"):
        return "hat"
    if token in ("jackets", "jacket"):
        return "jacket"
    if token in ("hoodies", "hoodie"):
        return "hoodie"
    if token in ("sweaters", "sweater", "pullover"):
        return "sweater"
    if token in ("dresses", "dress"):
        return "dress"
    if token in ("shirts", "shirt"):
        return "shirt"
    if token in ("shorts", "short"):
        return "shorts"
    if token in ("skirts", "skirt"):
        return "skirt"
    if token in ("blouses", "blouse"):
        return "blouse"
    if token in ("coats", "coat", "overcoat"):
        return "coat"
    if token in ("jeans", "denim"):
        return "jeans"
    return token


def extract_category(title: str) -> Optional[str]:
    """Extract a category tag from *title*."""
    if not title:
        return None

    # Check for multi-word or hyphenated categories like "t-shirt" first
    normalized_title = title.lower()
    if "t-shirt" in normalized_title or "t shirt" in normalized_title or " tee" in normalized_title:
        return "t-shirt"

    tokens = re.split(r"[\s\-_/\u2010-\u2015]+", title)
    for raw in tokens:
        token = _normalize_token(raw)
        if token in CATEGORIES:
            return token
    return None
