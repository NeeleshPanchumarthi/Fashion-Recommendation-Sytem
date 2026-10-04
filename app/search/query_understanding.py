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

import json
import logging
import re
from typing import Optional

import httpx

from app.config.settings import Settings
from app.ingestion.attributes.category_extractor import extract_category
from app.ingestion.attributes.color_extractor import extract_color
from app.ingestion.attributes.gender_extractor import extract_gender
from app.ingestion.attributes.size_extractor import extract_size
from app.ingestion.attributes.style_extractor import extract_style
from app.ingestion.attributes.vocabularies import CATEGORIES, COLORS, GENDERS, SIZES, STYLES

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TIMEOUT_SECONDS = 6.0  # a live search request can't wait long on this
# Connection resets (WinError 10054) during the TLS handshake are common on
# some networks; one quick retry usually gets through.
GROQ_CONNECT_ATTEMPTS = 2

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


def llm_expand_and_extract(query: str, settings: Settings) -> dict:
    """Calls Groq to fill gaps the regex extractor left and to produce an
    expanded query for embedding. Returns an all-None dict (with
    expanded_query falling back to the original query) on ANY failure --
    callers should treat this as 'no LLM signal', never as an error to
    propagate up to the search response."""
    empty = {
        "gender": None, "category": None, "color": None, "style": None, "size": None,
        "price_min": None, "price_max": None, "min_rating": None, "sentiment": None,
        "expanded_query": query,
    }

    if not settings.GROQ_API_KEY:
        return empty

    system_prompt = _LLM_SYSTEM_PROMPT.format(
        genders=sorted(GENDERS), categories=sorted(CATEGORIES), colors=sorted(COLORS),
        styles=sorted(STYLES), sizes=sorted(SIZES),
    )

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        # Reasoning models (gpt-oss) spend tokens thinking before the JSON;
        # too small a budget truncates the JSON and Groq returns a 400.
        "max_tokens": 1024,
    }
    if "gpt-oss" in settings.GROQ_MODEL:
        payload["reasoning_effort"] = "low"

    try:
        for attempt in range(GROQ_CONNECT_ATTEMPTS):
            try:
                resp = httpx.post(
                    GROQ_CHAT_URL,
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    json=payload,
                    timeout=GROQ_TIMEOUT_SECONDS,
                )
                break
            except httpx.ConnectError:
                if attempt == GROQ_CONNECT_ATTEMPTS - 1:
                    raise
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except Exception as exc:  # noqa: BLE001 -- any failure degrades to regex-only
        logger.warning("Groq query expansion failed, falling back to regex-only: %s", exc)
        return empty

    expanded = data.get("expanded_query")
    if not isinstance(expanded, str) or not expanded.strip():
        expanded = query

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
        "expanded_query": expanded,
    }


# Keys applied as Pinecone filters. price_min/price_max are still extracted
# but deliberately left out: price is empty for most products and isn't
# stored in Pinecone (see app/search/filtering.py).
FILTER_KEYS = (
    "gender", "category", "color", "style", "size",
    "min_rating", "sentiment",
)


def build_query_understanding(query: str, settings: Settings) -> dict:
    """Full query-understanding step: regex first (authoritative), Groq
    fills gaps + proposes an expanded query for embedding (never touching
    filters regex already resolved). Returns a dict with the filter keys
    above, plus 'expanded_query' and 'source' (which fields came from regex
    vs llm vs neither, for observability/debugging)."""
    regex_filters = extract_filters_regex(query)
    llm_filters = llm_expand_and_extract(query, settings)

    merged = {}
    source = {}
    for key in FILTER_KEYS:
        if regex_filters.get(key) is not None:
            merged[key] = regex_filters[key]
            source[key] = "regex"
        elif llm_filters.get(key) is not None:
            merged[key] = llm_filters[key]
            source[key] = "llm"
        else:
            merged[key] = None
            source[key] = None

    merged["expanded_query"] = llm_filters.get("expanded_query") or query
    merged["source"] = source
    return merged
