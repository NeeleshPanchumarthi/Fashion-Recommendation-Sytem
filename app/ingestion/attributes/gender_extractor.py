"""Gender extraction utilities for product titles.

This module provides a deterministic, rule‑based extractor that maps free‑form
text in a product title to one of the canonical gender categories defined in
:pydata:`app.ingestion.attributes.vocabularies.GENDERS`.
"""

from __future__ import annotations

import re
from typing import Optional

from .vocabularies import GENDERS


def _normalize_token(token: str) -> str:
    """Return a normalized version of *token*."""
    token = token.lower()
    # Remove surrounding punctuation
    token = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", token)
    # Strip possessive suffixes ('s or ')
    token = re.sub(r"'s$", "", token)
    token = re.sub(r"'$", "", token)
    # Normalise variants
    if token in ("men", "mens", "man"):
        return "men"
    if token in ("women", "womens", "woman"):
        return "women"
    if token in ("kids", "kid", "child", "children"):
        return "kids"
    if token in ("unisex",):
        return "unisex"
    return token


def extract_gender(title: str) -> Optional[str]:
    """Extract a gender tag from *title*."""
    if not title:
        return None

    # Tokenise on whitespace, hyphens (including Unicode hyphens), slashes
    tokens = re.split(r"[\s\-_/\u2010-\u2015]+", title)
    for raw in tokens:
        token = _normalize_token(raw)
        if token in GENDERS:
            return token
    return None
