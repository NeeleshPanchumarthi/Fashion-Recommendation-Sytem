"""Product domain model and the rule for which product images to display.

Image records are Amazon image dicts:
    [{"thumb": ..., "large": ..., "hi_res": ..., "variant": "MAIN"}, ...]

We only ever return the "large" URL of each chosen image, ordered for a
carousel (MAIN first):

  1. Angle shots exist (FRNT/BACK/LEFT/RGHT/TOPP/BOTT/SIDE, or spelled-out
     variants like "front"/"bottom")  ->  MAIN + PT01 + every angle shot.
  2. PT01 exists                      ->  MAIN + PT01.
  3. Only MAIN                        ->  MAIN.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Product:
    """A catalog product as stored in the vector index (ID = parent_asin)."""

    product_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    gender: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None
    size: Optional[str] = None
    average_rating: Optional[float] = None
    rating_number: Optional[int] = None
    overall_sentiment: Optional[str] = None
    images: list[dict[str, Any]] = field(default_factory=list)
    review_highlights: list[str] = field(default_factory=list)

    @property
    def display_images(self) -> list[str]:
        return select_display_images(self.images)


@dataclass
class ProductMatch:
    """A product returned by retrieval, with its relevance scores."""

    product: Product
    score: float                          # cosine similarity from dense search
    rerank_score: Optional[float] = None  # cross-encoder score, once reranked

    @property
    def relevance(self) -> float:
        return self.rerank_score if self.rerank_score is not None else self.score

# Amazon uses 4-letter codes (FRNT, RGHT, TOPP, BOTT); other sources may
# spell them out ("front", "bottom"), so each angle accepts both forms.
_ANGLE_PATTERNS = {
    "front": re.compile(r"^(frnt|front)", re.IGNORECASE),
    "back": re.compile(r"^back", re.IGNORECASE),
    "left": re.compile(r"^left", re.IGNORECASE),
    "right": re.compile(r"^(rght|right)", re.IGNORECASE),
    "top": re.compile(r"^top", re.IGNORECASE),
    "bottom": re.compile(r"^(bott|bottom)", re.IGNORECASE),
    "side": re.compile(r"^side", re.IGNORECASE),
}
_ANGLE_ORDER = list(_ANGLE_PATTERNS)


def _angle_name(variant: str) -> str | None:
    for name, pattern in _ANGLE_PATTERNS.items():
        if pattern.match(variant):
            return name
    return None


def _parse(raw) -> list[dict]:
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            # A bare URL string rather than the JSON list.
            return [{"variant": "MAIN", "large": raw}]
    if isinstance(raw, dict):
        raw = [raw]
    return [img for img in raw if isinstance(img, dict)]


def _large_url(img: dict) -> str | None:
    # Fall back to hi_res/thumb only if a record has no "large" entry.
    return img.get("large") or img.get("hi_res") or img.get("thumb")


def select_display_images(raw) -> list[str]:
    """Return the ordered list of large image URLs for a product."""
    images = _parse(raw)
    if not images:
        return []

    by_variant: dict[str, dict] = {}
    angles: dict[str, dict] = {}
    for img in images:
        variant = str(img.get("variant") or "").strip()
        by_variant.setdefault(variant.upper(), img)
        angle = _angle_name(variant)
        if angle:
            angles.setdefault(angle, img)

    main = by_variant.get("MAIN") or images[0]
    chosen = [main]

    if "PT01" in by_variant:
        chosen.append(by_variant["PT01"])

    for name in _ANGLE_ORDER:
        if name in angles:
            chosen.append(angles[name])

    urls: list[str] = []
    for img in chosen:
        url = _large_url(img)
        if url and url not in urls:
            urls.append(url)
    return urls
