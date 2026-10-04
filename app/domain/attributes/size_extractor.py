"""Size extraction utilities for product titles.

This module provides a deterministic, rule-based extractor that maps free-form
text in a product title to one of the canonical size tags defined in
:pydata:`app.domain.attributes.vocabularies.SIZES`.
"""

from __future__ import annotations

import re
from typing import Optional

from .vocabularies import SIZES


def _normalize_token(token: str) -> str:
    """Return a normalized version of *token* for size matching."""
    token = token.lower()
    token = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", token)
    if token in ("small", "s"):
        return "s"
    if token in ("medium", "m"):
        return "m"
    if token in ("large", "l"):
        return "l"
    if token in ("extra-large", "xl"):
        return "xl"
    if token in ("xxl", "2xl"):
        return "xxl"
    if token in ("3xl", "xxxl"):
        return "3xl"
    if token in ("xs", "extra-small"):
        return "xs"
    return token


def extract_size(title: str) -> Optional[str]:
    """Extract a size tag from *title*."""
    if not title:
        return None

    normalized_title = title.lower()
    if "extra-large" in normalized_title or "extra large" in normalized_title or "x-large" in normalized_title:
        return "xl"
    if "extra-small" in normalized_title or "extra small" in normalized_title or "x-small" in normalized_title:
        return "xs"

    # Check for explicitly labeled size strings like "Size M", "Size XL"
    size_match = re.search(r"\bsize\s*[:\-]?\s*([a-z0-9]+)\b", title, re.IGNORECASE)
    if size_match:
        norm = _normalize_token(size_match.group(1))
        if norm in SIZES:
            return norm

    tokens = re.split(r"[\s\-_/\u2010-\u2015]+", title)
    for raw in tokens:
        token = _normalize_token(raw)
        if token in SIZES:
            return token
    return None
