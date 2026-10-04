"""Color extraction utilities for product titles.

This module provides a deterministic, rule-based extractor that maps free-form
text in a product title to one of the canonical colors defined in
:pydata:`app.domain.attributes.vocabularies.COLORS`.
"""

from __future__ import annotations

import re
from typing import Optional

from .vocabularies import COLORS


def _normalize_token(token: str) -> str:
    """Return a normalized version of *token* for color matching."""
    token = token.lower()
    token = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", token)
    if token in ("gray", "grey"):
        return "grey"
    if token in ("navy-blue", "navyblue"):
        return "navy"
    if token in ("golden", "gold"):
        return "gold"
    return token


def extract_color(title: str) -> Optional[str]:
    """Extract a color tag from *title*."""
    if not title:
        return None

    normalized_title = title.lower()
    if "navy blue" in normalized_title or "navy-blue" in normalized_title:
        return "navy"

    tokens = re.split(r"[\s\-_/\u2010-\u2015]+", title)
    for raw in tokens:
        token = _normalize_token(raw)
        if token in COLORS:
            return token
    return None
