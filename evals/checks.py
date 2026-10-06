"""Health eval checks. Each takes an httpx.Client pointed at the API base URL
and returns plain dicts, so scoring is testable with httpx.MockTransport."""

from __future__ import annotations

import math
import re
import time
from typing import Optional

import httpx

TOP_K = 10
# Search runs CPU inference, so allow generous per-request time.
REQUEST_TIMEOUT = 60.0
RETRIES = 2  # transport errors only (this network resets connections often)

# Result flags that identify each outfit group (see app/schemas/search.py).
OUTFIT_GROUPS = {
    "footwear": lambda r: r.get("is_footwear"),
    "accessories": lambda r: r.get("is_accessory"),
    "tops": lambda r: r.get("garment_type") == "upper_body",
    "bottoms": lambda r: r.get("garment_type") == "lower_body",
}


def percentile(values: list[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(pct / 100 * len(ordered)) - 1)]


def timed_post(client: httpx.Client, path: str, payload: dict) -> dict:
    """POST with transport-error retries. Returns status, body, latency_ms, flakes."""
    flakes = 0
    for attempt in range(RETRIES + 1):
        started = time.perf_counter()
        try:
            resp = client.post(path, json=payload, timeout=REQUEST_TIMEOUT)
        except httpx.TransportError as exc:
            flakes += 1
            if attempt == RETRIES:
                return {"status": None, "body": None, "latency_ms": None, "flakes": flakes, "error": repr(exc)}
            continue
        try:
            body = resp.json()
        except ValueError:
            body = None
        return {
            "status": resp.status_code,
            "body": body,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "flakes": flakes,
            "request_id": resp.headers.get("X-Request-ID"),
        }
    raise AssertionError("unreachable")


def check_probes(client: httpx.Client) -> dict:
    """Liveness and readiness, including which dependency is failing."""
    out = {}
    for name, path in (("liveness", "/health"), ("readiness", "/ready")):
        try:
            resp = client.get(path, timeout=30.0)
            out[name] = {"ok": resp.status_code == 200, "status": resp.status_code, "body": resp.json()}
        except (httpx.TransportError, ValueError) as exc:
            out[name] = {"ok": False, "status": None, "error": repr(exc)}
    return out


def _matches_any(title: str, needles: list[str]) -> bool:
    return any(re.search(re.escape(n), title, re.I) for n in needles)


def score_case(case: dict, call: dict) -> dict:
    """Score one golden query against one API response."""
    result = {"query": case["query"], "outfit": bool(case.get("outfit")), "latency_ms": call["latency_ms"], "status": call["status"], "flakes": call["flakes"]}
    body = call["body"]
    if call["status"] != 200 or not body:
        return {**result, "error": True}
    results = body.get("results", [])[:TOP_K]
    result.update(error=False, empty=not results, n_results=len(results), request_id_present=bool(call.get("request_id")))

    applied = body.get("filters") or {}
    expected = {k: case[k] for k in ("gender", "category", "color") if k in case}
    if expected:
        result["filter_hits"] = sum(applied.get(k) == v for k, v in expected.items())
        result["filter_total"] = len(expected)

    if case.get("title_any") and results:
        result["category_conformance"] = sum(_matches_any(r["title"], case["title_any"]) for r in results) / len(results)
    if case.get("gender") and results:
        # Unisex / unspecified products are acceptable for a gendered query.
        ok = {case["gender"], "unisex", None}
        result["gender_conformance"] = sum(r.get("gender") in ok for r in results) / len(results)

    if case.get("outfit"):
        covered = [g for g, test in OUTFIT_GROUPS.items() if any(test(r) for r in results)]
        result["outfit_groups"] = covered
        result["outfit_coverage"] = len(covered) / len(OUTFIT_GROUPS)
    return result


def check_robustness(client: httpx.Client) -> list[dict]:
    """Bad input must be rejected cleanly (4xx), never a 5xx."""
    probes = [
        ("empty_query", {"query": "   "}, {400, 422}),
        ("overlong_query", {"query": "x" * 501}, {422}),
        ("zero_top_k", {"query": "shirt", "top_k": 0}, {422}),
    ]
    out = []
    for name, payload, allowed in probes:
        call = timed_post(client, "/search", payload)
        out.append({"name": name, "status": call["status"], "ok": call["status"] in allowed})
    return out
