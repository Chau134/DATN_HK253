"""Runtime probes with independent metadata assertions and repeatable load.

Runs inside the existing container against a selected internal port. Never sends
fixture metadata to the API. Image downloads are outside timed load requests.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import statistics
import time
import unicodedata
import re
import urllib.request
import urllib.error


def load_runner(path):
    spec = importlib.util.spec_from_file_location("runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(value):
    value = unicodedata.normalize("NFKD", value.lower().replace("đ", "d"))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in value if not unicodedata.combining(c))).split())


def violations(case, response, products, *, status=200):
    failures = [] if status == 200 else [f"http_status:{status}"]
    ids = response.get("product_ids", [])
    if len(ids) != len(set(ids)):
        failures.append("duplicate_product_id")
    if case.get("expect_empty") and ids:
        failures.append("expected_empty")
    if not case.get("expect_empty") and not case.get("allow_empty") and not ids:
        failures.append("unexpected_empty")
    if case.get("optional_field") and (response.get("filters") or {}).get(case["optional_field"]):
        failures.append("preference_became_required")
    for pid in ids:
        product = products.get(pid)
        if not product:
            failures.append(f"unknown_product:{pid}")
            continue
        for field, expected in case.get("contains", {}).items():
            actual = normalize(product[field])
            if not all(token in actual for token in expected):
                failures.append(f"{pid}:missing_{field}")
        for field, unwanted in case.get("excludes", {}).items():
            if any(token in normalize(product[field]) for token in unwanted):
                failures.append(f"{pid}:excluded_{field}")
        for field, alternatives in case.get("contains_any", {}).items():
            actual = " " + normalize(product.get(field, "")) + " "
            if not any(" " + normalize(token) + " " in actual for token in alternatives):
                failures.append(f"{pid}:missing_any_{field}")
        for field, expected in case.get("exact_normalized", {}).items():
            if normalize(product[field]) != expected:
                failures.append(f"{pid}:exact_{field}")
        for fiber, amount in case.get("composition", {}).items():
            # Independently inspect percentage clauses; spinning/yarn qualifiers
            # do not turn 100% Cotton Yarn into a different fiber composition.
            clauses = re.findall(r"(\d+(?:[.,]\d+)?)\s*%\s*([^\d,%]+)", product["material"])
            if not any(float(pct.replace(",", ".")) == amount and fiber in normalize(name).split() for pct, name in clauses):
                failures.append(f"{pid}:composition_{fiber}")
        price = float(product["price"])
        if "max_exclusive" in case and price >= case["max_exclusive"]:
            failures.append(f"{pid}:max_exclusive")
        if "min_exclusive" in case and price <= case["min_exclusive"]:
            failures.append(f"{pid}:min_exclusive")
        if "max_inclusive" in case and price > case["max_inclusive"]:
            failures.append(f"{pid}:max_inclusive")
    return failures


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    p = (len(ordered) - 1) * fraction
    low = int(p)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (p - low)


def download_image(runner, url, *, attempts=3):
    """Retry only input downloads, before measurement; never retry search calls."""
    for attempt in range(1, attempts + 1):
        try:
            return runner.image_payload(url, 20)[0]
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            print(f"download attempt={attempt}/{attempts} error={type(exc).__name__}", flush=True)
            if attempt == attempts:
                raise
            time.sleep(attempt)
    raise ValueError("attempts must be positive")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["dev", "load"])
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--products", type=Path)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--count", type=int, default=72)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    runner = load_runner(args.runner)
    queries = runner.read_csv(args.queries)
    readiness = json.load(urllib.request.urlopen(args.base_url + "/health/ready", timeout=10))
    if not readiness.get("ready") or readiness["effective_features"]["reranker_enabled"]:
        raise RuntimeError("Expected ready, rerank-off runtime")
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.action == "dev":
        image = download_image(runner, queries[1]["image_url"])
        products = {r["product_id"]: r for r in runner.read_csv(args.products)}
        rows = []
        for case in json.loads(args.cases.read_text(encoding="utf-8"))["cases"]:
            status, response, ms = runner.call_search(args.base_url + "/search/hybrid", query=case["query"], image=image, top_k=20, timeout=90)
            failures = violations(case, response, products, status=status)
            rows.append({"id": case["id"], "status": status, "response": response, "latency_ms": ms, "failures": failures})
            print(f"{case['id']}: returned={len(response.get('product_ids', []))} failures={failures}", flush=True)
        output = {"readiness": readiness, "scope": "metadata/contract probes, not visual relevance judgments", "cases": rows,
                  "passed": all(not row["failures"] for row in rows)}
    else:
        # Cache images only in this process, use identical bytes for every repeat.
        selected = [queries[i % len(queries)] for i in range(args.count)]
        images = []
        for index, q in enumerate(selected, 1):
            print(f"download {index}/{len(selected)} {q['query_id']}", flush=True)
            images.append(download_image(runner, q["image_url"]))
        output = {"readiness": readiness, "workers": args.workers, "cache_policy": "images downloaded before measurement; service cache retained between repeats", "rounds": []}
        def call(index):
            started = time.monotonic()
            try:
                status, response, ms = runner.call_search(args.base_url + "/search/hybrid", query=selected[index]["query_text"], image=images[index], top_k=20, timeout=30)
                ids = response.get("product_ids", [])
                return {"query_id": selected[index]["query_id"], "status": status, "latency_ms": ms, "returned": len(ids), "duplicates": len(ids) - len(set(ids))}
            except Exception as exc:
                return {"query_id": selected[index]["query_id"], "status": 0, "latency_ms": (time.monotonic() - started) * 1000, "error_type": type(exc).__name__}
        for repeat in range(args.repeats):
            order = list(range(args.count))
            if repeat % 2:
                order.reverse()
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                rows = list(executor.map(call, order))
            times = [r["latency_ms"] for r in rows]
            summary = {"round": repeat + 1, "requests": len(rows), "errors": sum(r["status"] != 200 for r in rows),
                       "p50_ms": percentile(times, .5), "p95_ms": percentile(times, .95), "p99_ms": percentile(times, .99), "rows": rows}
            output["rounds"].append(summary)
            args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({k: v for k, v in summary.items() if k != "rows"}), flush=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
