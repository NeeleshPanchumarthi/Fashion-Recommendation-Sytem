"""Style extraction utilities for product titles.

This module provides a deterministic, rule-based extractor that maps free-form
text in a product title to one of the canonical style tags defined in
:pydata:`app.domain.attributes.vocabularies.STYLES`.
"""

from __future__ import annotations

import re
from typing import Optional

from .vocabularies import STYLES


def _normalize_token(token: str) -> str:
    """Return a normalized version of *token* for style matching."""
    token = token.lower()
    token = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", token)
    if token in ("sport", "sports", "sporty", "athletic"):
        return "sporty"
    if token in ("casuals", "casual"):
        return "casual"
    if token in ("formals", "formal"):
        return "formal"
    if token in ("vintages", "vintage"):
        return "vintage"
    return token


def extract_style(title: str) -> Optional[str]:
    """Extract a style tag from *title*."""
    if not title:
        return None

    tokens = re.split(r"[\s\-_/\u2010-\u2015]+", title)
    for raw in tokens:
        token = _normalize_token(raw)
        if token in STYLES:
            return token
    return None
