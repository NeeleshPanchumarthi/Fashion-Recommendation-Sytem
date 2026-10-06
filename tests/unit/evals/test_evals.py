import json
from pathlib import Path

import httpx

from evals.checks import check_robustness, percentile, score_case
from evals.run import evaluate, verdicts

GOLDEN = json.loads((Path(__file__).parents[3] / "evals" / "golden.json").read_text(encoding="utf-8"))


def _result(title, **kw):
    return {"product_id": "p", "title": title, "gender": "men", "is_footwear": False, "is_accessory": False,
            "garment_type": None, **kw}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok"})
    if request.url.path == "/ready":
        return httpx.Response(200, json={"status": "ready"})
    body = json.loads(request.content)
    q = body["query"].strip()
    if not q:
        return httpx.Response(400, json={"detail": "empty"})
    if len(q) > 500 or body.get("top_k") == 0:
        return httpx.Response(422, json={"detail": "bad"})
    if "outfit" in q or "wear" in q:
        results = [_result("Shoes", is_footwear=True), _result("Hat", is_accessory=True),
                   _result("Shirt", garment_type="upper_body"), _result("Chinos", garment_type="lower_body")]
        return httpx.Response(200, json={"query": q, "filters": {}, "results": results},
                              headers={"X-Request-ID": "abc"})
    return httpx.Response(200, json={"query": q, "filters": {"gender": "men", "category": "jeans", "color": "black"},
                                     "results": [_result("Slim Fit Jeans")] * 10}, headers={"X-Request-ID": "abc"})


def test_percentile():
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([], 95) is None


def test_score_case_flags_wrong_category():
    case = {"query": "black jeans", "category": "jeans", "title_any": ["jean"]}
    call = {"status": 200, "latency_ms": 10, "flakes": 0, "request_id": "x",
            "body": {"filters": {"category": "jeans"}, "results": [_result("Jeans"), _result("Sandals")]}}
    scored = score_case(case, call)
    assert scored["category_conformance"] == 0.5
    assert scored["filter_hits"] == 1


def test_error_response_counts_as_error():
    scored = score_case({"query": "q"}, {"status": 503, "latency_ms": 5, "flakes": 0, "body": {"detail": "x"}})
    assert scored["error"] is True


def test_evaluate_scores_a_working_service():
    client = httpx.Client(transport=httpx.MockTransport(_handler), base_url="http://t")
    report = evaluate(client, GOLDEN, repeats=1)
    metrics = report["metrics"]
    assert metrics["liveness_ok"] and metrics["readiness_ok"]
    assert metrics["error_rate"] == 0
    assert metrics["outfit_coverage"] == 1.0
    assert metrics["robustness_pass_rate"] == 1.0
    assert verdicts(metrics, GOLDEN["thresholds"])["error_rate"]


def test_outage_is_reported_unhealthy():
    def down(request):
        raise httpx.ConnectError("refused")

    client = httpx.Client(transport=httpx.MockTransport(down), base_url="http://t")
    report = evaluate(client, {**GOLDEN, "cases": GOLDEN["cases"][:1]}, repeats=1)
    verdict = verdicts(report["metrics"], GOLDEN["thresholds"])
    assert report["metrics"]["error_rate"] == 1.0
    assert not verdict["liveness_ok"] and not verdict["error_rate"]


def test_robustness_checks_accept_clean_rejections():
    client = httpx.Client(transport=httpx.MockTransport(_handler), base_url="http://t")
    assert all(r["ok"] for r in check_robustness(client))
