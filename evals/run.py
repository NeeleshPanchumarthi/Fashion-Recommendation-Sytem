"""Run the health evals against a live API and print/save a scored report.

    python -m evals.run                                  # http://127.0.0.1:8000/api
    python -m evals.run --base-url https://host/api --out evals/reports/latest.json
    python -m evals.run --baseline evals/reports/baseline.json   # show deltas

Exit code 1 if any threshold fails, so it can gate CI or a scheduled job.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

from .checks import check_probes, check_robustness, percentile, score_case, timed_post

GOLDEN = Path(__file__).with_name("golden.json")


def _mean(values: list[float]):
    return round(statistics.fmean(values), 3) if values else None


def evaluate(client: httpx.Client, golden: dict, repeats: int = 3) -> dict:
    probes = check_probes(client)
    scored = []
    for case in golden["cases"]:
        for _ in range(repeats):  # repeats give latency a distribution
            call = timed_post(client, "/search", {"query": case["query"], "top_k": 10})
            scored.append(score_case(case, call))
    robustness = check_robustness(client)

    ok = [s for s in scored if not s["error"]]
    latencies = [s["latency_ms"] for s in ok if s["latency_ms"] is not None]
    by_type = {
        kind: [s["latency_ms"] for s in ok if s["outfit"] == is_outfit and s["latency_ms"] is not None]
        for kind, is_outfit in (("normal", False), ("outfit", True))
    }
    hits = sum(s.get("filter_hits", 0) for s in ok)
    total = sum(s.get("filter_total", 0) for s in ok)
    metrics = {
        "liveness_ok": probes["liveness"]["ok"],
        "readiness_ok": probes["readiness"]["ok"],
        "error_rate": round(1 - len(ok) / len(scored), 3) if scored else None,
        "empty_rate": round(sum(s["empty"] for s in ok) / len(ok), 3) if ok else None,
        "network_flakes": sum(s["flakes"] for s in scored),
        "latency_p50_ms": round(percentile(latencies, 50) or 0),
        "latency_p95_ms": round(percentile(latencies, 95) or 0),
        "latency_p95_ms_normal": round(percentile(by_type["normal"], 95) or 0),
        "latency_p95_ms_outfit": round(percentile(by_type["outfit"], 95) or 0),
        "filter_accuracy": round(hits / total, 3) if total else None,
        "category_conformance": _mean([s["category_conformance"] for s in ok if "category_conformance" in s]),
        "gender_conformance": _mean([s["gender_conformance"] for s in ok if "gender_conformance" in s]),
        "outfit_coverage": _mean([s["outfit_coverage"] for s in ok if "outfit_coverage" in s]),
        "robustness_pass_rate": round(sum(r["ok"] for r in robustness) / len(robustness), 3),
        "request_id_present_rate": _mean([float(s["request_id_present"]) for s in ok]),
    }
    return {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "metrics": metrics, "probes": probes,
            "robustness": robustness, "cases": scored}


def verdicts(metrics: dict, th: dict) -> dict[str, bool]:
    def ge(key, lo):
        return metrics[key] is not None and metrics[key] >= lo

    def le(key, hi):
        return metrics[key] is not None and metrics[key] <= hi

    return {
        "liveness_ok": metrics["liveness_ok"],
        "readiness_ok": metrics["readiness_ok"],
        "error_rate": le("error_rate", th["error_rate_max"]),
        "empty_rate": le("empty_rate", th["empty_rate_max"]),
        "latency_p95_ms_normal": le("latency_p95_ms_normal", th["latency_p95_ms_max_normal"]),
        "latency_p95_ms_outfit": le("latency_p95_ms_outfit", th["latency_p95_ms_max_outfit"]),
        "filter_accuracy": ge("filter_accuracy", th["filter_accuracy_min"]),
        "category_conformance": ge("category_conformance", th["category_conformance_min"]),
        "gender_conformance": ge("gender_conformance", th["gender_conformance_min"]),
        "outfit_coverage": ge("outfit_coverage", th["outfit_coverage_min"]),
        "robustness_pass_rate": metrics["robustness_pass_rate"] == 1.0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args(argv)

    golden = json.loads(args.golden.read_text(encoding="utf-8"))
    with httpx.Client(base_url=args.base_url) as client:
        report = evaluate(client, golden, args.repeats)
    report["verdicts"] = verdicts(report["metrics"], golden["thresholds"])

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))["metrics"] if args.baseline else {}
    print(f"{'metric':<26}{'value':>10}  {'baseline':>10}  status")
    for name, value in report["metrics"].items():
        verdict = report["verdicts"].get(name)
        status = "" if verdict is None else ("PASS" if verdict else "FAIL")
        print(f"{name:<26}{str(value):>10}  {str(baseline.get(name, '')):>10}  {status}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    failed = [k for k, v in report["verdicts"].items() if not v]
    print("\nHEALTHY" if not failed else f"\nUNHEALTHY: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
