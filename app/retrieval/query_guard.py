"""Fashion-topic fallback for the search query guard.

The real decision (fashion or not, plus translation to English) is made by the
single LLM call in query_processor.py. This vocabulary check is only the
fallback for when that call is unavailable (no key, network failure, unusable
answer): a query containing a fashion term passes unchanged, one without is
refused. On its own it can't tell "wedding dress" from "wedding venues", which
is why the LLM decides whenever it can.
"""

from __future__ import annotations

import re

from app.domain.attributes.vocabularies import FASHION_TERMS

NOT_FASHION_MESSAGE = (
    "Please ask a fashion-related question, such as clothing, footwear, accessories, "
    "outfits, sizing, style, or occasions."
)

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def has_fashion_term(query: str) -> bool:
    for word in _WORD_RE.findall(query.lower()):
        if word in FASHION_TERMS or word.rstrip("s") in FASHION_TERMS or word.removesuffix("es") in FASHION_TERMS:
            return True
    return False
