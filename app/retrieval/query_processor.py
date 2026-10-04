"""Query understanding: deterministic attribute extraction (regex, same vocab as
ingestion) + LLM-based expansion/extraction (Groq) for recall on queries the
regex extractors miss, plus a canonicalized/expanded text for embedding.

Order matters: regex extraction always runs first and is authoritative for any
field it finds a match on (it's exact -- no hallucination risk). The Groq call
only fills in fields regex left as None, and every LLM-provided categorical
value is validated against the SAME controlled vocabularies used at ingestion
before it's trusted -- a value outside that vocabulary can never match a real
product's Pinecone metadata anyway, so it's discarded rather than used.

Groq (not the local Ollama used for batch enrichment earlier) is deliberately
the right tool here even though Groq's free tier struggled under the earlier
BATCH job: that job made thousands of rapid calls and got rate-limited. A
live search endpoint makes one call per request -- a completely different
load pattern, well within free-tier limits.

If the Groq call fails for any reason (network, rate limit, malformed JSON,
timeout), this falls back to regex-only + the original query text
unexpanded. Search must keep working even if the LLM is unavailable.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.clients.llm_client import LLMClient
from app.core.exceptions import DependencyUnavailableError
from app.domain.attributes.category_extractor import extract_category
from app.domain.attributes.color_extractor import extract_color
from app.domain.attributes.gender_extractor import extract_gender
from app.domain.attributes.size_extractor import extract_size
from app.domain.attributes.style_extractor import extract_style
from app.domain.attributes.vocabularies import CATEGORIES, COLORS, GENDERS, SIZES, STYLES
from app.domain.search import QueryUnderstanding, SearchFilters

logger = logging.getLogger(__name__)

SENTIMENTS = {"positive", "neutral", "negative"}

_PRICE_RANGE_RE = re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
_PRICE_UNDER_RE = re.compile(r"\b(?:under|below|less than|<)\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
_PRICE_OVER_RE = re.compile(r"\b(?:over|above|more than|>)\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
_RATING_RE = re.compile(r"\b(\d(?:\.\d)?)\s*\+?\s*stars?\b|\brated?\s*(\d(?:\.\d)?)\s*\+", re.I)
_WELL_REVIEWED_RE = re.compile(
    r"\b(highly rated|best rated|top rated|well reviewed|well-reviewed|positive reviews|loved by)\b", re.I
)


def extract_price_range(query: str):
    """Very small deterministic price-range extractor. Returns (min, max),
    either side may be None. Doesn't try to guess vague terms like
    'affordable' -- that's left to the LLM tier, and even there only if it
    returns an actual number, never a guess dressed up as one."""
    m = _PRICE_RANGE_RE.search(query)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return (min(lo, hi), max(lo, hi))
    m = _PRICE_UNDER_RE.search(query)
    if m:
        return (None, float(m.group(1)))
    m = _PRICE_OVER_RE.search(query)
    if m:
        return (float(m.group(1)), None)
    return (None, None)


def extract_min_rating(query: str) -> Optional[float]:
    m = _RATING_RE.search(query)
    if m:
        val = m.group(1) or m.group(2)
        try:
            return float(val)
        except ValueError:
            return None
    if _WELL_REVIEWED_RE.search(query):
        return 4.0
    return None


def extract_sentiment(query: str) -> Optional[str]:
    if _WELL_REVIEWED_RE.search(query):
        return "positive"
    return None


# Query-only gender cues ("a dress for my wife"). Kept out of the shared
# title extractor so ingestion tagging is unaffected. son/daughter are left
# out, as are boy/girl: they usually mean kids sizing, not adult.
_RELATION_GENDER = {
    "women": ("wife", "girlfriend", "mom", "mother", "sister", "her", "she", "ladies", "lady"),
    "men": ("husband", "boyfriend", "dad", "father", "brother", "him", "he", "guy", "guys", "gents"),
}
_RELATION_PATTERNS = {
    gender: re.compile(r"\b(" + "|".join(words) + r")\b", re.IGNORECASE)
    for gender, words in _RELATION_GENDER.items()
}


def extract_query_gender(query: str) -> Optional[str]:
    """Explicit gender words first, then relationship cues. Ambiguous
    queries ("for him and her") resolve to None so both genders show."""
    explicit = extract_gender(query)
    if explicit:
        return explicit
    hits = [g for g, pattern in _RELATION_PATTERNS.items() if pattern.search(query)]
    return hits[0] if len(hits) == 1 else None


def extract_filters_regex(query: str) -> dict:
    """Deterministic, zero-latency extraction using the SAME extractors used
    at ingestion -- authoritative whenever they find a match."""
    price_min, price_max = extract_price_range(query)
    return {
        "gender": extract_query_gender(query),
        "category": extract_category(query),
        "color": extract_color(query),
        "style": extract_style(query),
        "size": extract_size(query),
        "price_min": price_min,
        "price_max": price_max,
        "min_rating": extract_min_rating(query),
        "sentiment": extract_sentiment(query),
    }


_LLM_SYSTEM_PROMPT = """You extract shopping-search attributes from a short fashion product query.

Only use these exact values (or null if not mentioned/unclear):
- gender: one of {genders} or null
- category: one of {categories} or null
- color: one of {colors} or null
- style: one of {styles} or null
- size: one of {sizes} or null
- price_min: a number (only if the user gives an explicit lower price bound), else null
- price_max: a number (only if the user gives an explicit upper price bound), else null
- min_rating: a number 1-5 (only if the user asks for highly-rated/best-rated items), else null
- sentiment: "positive" if the user wants well-reviewed items, else null
- expanded_query: a short natural phrase (5-12 words) restating the query using the
  SAME canonical vocabulary above wherever applicable, to improve semantic search.
  Do not invent attributes the user didn't imply.

Never invent a value outside the given lists. If genuinely unsure, use null.
gender: ONLY if the user states it ("men's", "for my wife", "boys"). Never infer it
from the garment or occasion -- "a dress for a wedding" has gender null.
category: ONLY if the user names a garment type. Generic words like "outfit",
"clothes", "something to wear" have category null.
Respond with ONLY a JSON object with exactly these 9 keys."""


def _validate_choice(value, allowed: set) -> Optional[str]:
    if isinstance(value, str) and value.lower().strip() in allowed:
        return value.lower().strip()
    return None


def _validate_number(value) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


# Fields that become search filters. price_min/price_max are extracted but
# not filtered on: price is empty for most products and isn't in the index.
FILTER_KEYS = ("gender", "category", "color", "style", "size", "min_rating", "sentiment")
EXTRACTED_KEYS = FILTER_KEYS + ("price_min", "price_max")


class QueryProcessor:
    """Turns a raw query into filters + text to embed.

    Regex extraction runs first and is authoritative. The LLM only fills the
    fields regex left empty and proposes an expanded query; if it fails for
    any reason, search continues with regex-only results.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def process(self, query: str) -> QueryUnderstanding:
        regex = extract_filters_regex(query)
        llm = self._llm_extract(query)

        merged: dict = {}
        sources: dict[str, str] = {}
        for key in EXTRACTED_KEYS:
            if regex.get(key) is not None:
                merged[key], sources[key] = regex[key], "regex"
            elif llm.get(key) is not None:
                merged[key], sources[key] = llm[key], "llm"
            else:
                merged[key] = None

        return QueryUnderstanding(
            filters=SearchFilters(**{key: merged[key] for key in FILTER_KEYS}),
            expanded_query=llm.get("expanded_query") or query,
            sources=sources,
            price_min=merged["price_min"],
            price_max=merged["price_max"],
        )

    def _llm_extract(self, query: str) -> dict:
        """LLM-extracted fields, validated against the controlled
        vocabularies. Empty dict when the LLM is disabled or fails."""
        if not self._llm.enabled:
            return {}

        system_prompt = _LLM_SYSTEM_PROMPT.format(
            genders=sorted(GENDERS), categories=sorted(CATEGORIES), colors=sorted(COLORS),
            styles=sorted(STYLES), sizes=sorted(SIZES),
        )
        try:
            data = self._llm.complete_json(system_prompt, query)
        except DependencyUnavailableError as exc:
            logger.warning("LLM query expansion failed, falling back to regex-only: %s", exc)
            return {}

        expanded = data.get("expanded_query")
        return {
            "gender": _validate_choice(data.get("gender"), GENDERS),
            "category": _validate_choice(data.get("category"), CATEGORIES),
            "color": _validate_choice(data.get("color"), COLORS),
            "style": _validate_choice(data.get("style"), STYLES),
            "size": _validate_choice(data.get("size"), SIZES),
            "price_min": _validate_number(data.get("price_min")),
            "price_max": _validate_number(data.get("price_max")),
            "min_rating": _validate_number(data.get("min_rating")),
            "sentiment": _validate_choice(data.get("sentiment"), SENTIMENTS),
            "expanded_query": expanded.strip() if isinstance(expanded, str) and expanded.strip() else None,
        }
