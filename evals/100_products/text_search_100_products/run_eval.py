from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
import math
import re
import statistics
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
PRODUCT_PATTERN = re.compile(
    r"\(\d+,(\d+),'search_name_vi',NULL,'[^']*','[^']*','((?:''|[^'])*)'\)"
)
MIN_SEMANTIC_NDCG = 0.90
MIN_SEMANTIC_JUDGMENT_COVERAGE = 1.0


def extract_products(sql_path: Path) -> list[dict[str, str]]:
    sql = sql_path.read_text(encoding="utf-8")
    products = [
        {"product_id": match.group(1), "product_name_vi": match.group(2).replace("''", "'")}
        for match in PRODUCT_PATTERN.finditer(sql)
    ]
    if len(products) != 100:
        raise RuntimeError(f"Expected 100 search_name_vi rows in {sql_path}, found {len(products)}")
    if len({row['product_id'] for row in products}) != 100:
        raise RuntimeError("The SQL snapshot contains duplicate product IDs")
    return products


def post_search(url: str, query: str, top_k: int, timeout: int) -> tuple[int, dict[str, Any], float]:
    payload = json.dumps({"query": query, "top_k": top_k}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body, (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw_error": raw}
        return exc.code, body, (time.perf_counter() - started) * 1000


def get_json(url: str, timeout: int) -> tuple[int, dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw_error": raw}
        return exc.code, body
    except Exception as exc:
        return 0, {"error": f"{type(exc).__name__}: {exc}"}


def smoke_check(
    *,
    direct_url: str,
    public_url: str,
    query: str,
    timeout: int,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, url in (("service_ai", direct_url), ("public_api", public_url)):
        try:
            status, body, latency_ms = post_search(url, query, 1, timeout)
            returned = response_products(body)
            sources = [
                str(item.get("ai_source", item.get("source", "")))
                for item in returned
            ]
            warnings = [str(value) for value in body.get("warnings", [])]
            valid = (
                status == 200
                and bool(returned)
                and all(source == "text" for source in sources)
                and "ai_service_unavailable" not in warnings
                and "ai_keyword_fallback" not in warnings
            )
            checks[name] = {
                "url": url,
                "status_code": status,
                "latency_ms": round(latency_ms, 3),
                "sources": sources,
                "warnings": warnings,
                "valid": valid,
            }
        except Exception as exc:
            checks[name] = {
                "url": url,
                "status_code": 0,
                "error": f"{type(exc).__name__}: {exc}",
                "valid": False,
            }
    checks["valid"] = all(check.get("valid") for check in checks.values())
    return checks


def response_products(body: dict[str, Any]) -> list[dict[str, Any]]:
    products = body.get("products")
    if isinstance(products, list):
        return products
    results = body.get("results")
    return results if isinstance(results, list) else []


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    accentless = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[0-9a-z]+", accentless))


def _without_trailing_gender(value: str) -> str:
    return re.sub(r"\s+(?:nam|nữ)\s*$", "", value, flags=re.IGNORECASE).strip()


def _reordered_keywords(value: str) -> str:
    tokens = value.split()
    if len(tokens) < 4:
        return " ".join(reversed(tokens))
    pivot = 2 if tokens[0].casefold() == "áo" else 1
    return " ".join(tokens[pivot:] + tokens[:pivot])


def _with_minor_typo(value: str) -> str:
    tokens = value.split()
    candidates = [
        (len(re.sub(r"\W", "", token, flags=re.UNICODE)), index)
        for index, token in enumerate(tokens)
        if len(re.sub(r"\W", "", token, flags=re.UNICODE)) >= 4
    ]
    if not candidates:
        return value
    _, index = max(candidates)
    token = tokens[index]
    middle = max(1, len(token) // 2)
    tokens[index] = token[:middle] + token[middle + 1 :]
    return " ".join(tokens)


def build_advanced_cases(products: list[dict[str, str]]) -> list[dict[str, str]]:
    """Build a deterministic robustness suite while retaining all source products."""
    equivalent_ids: dict[str, list[str]] = {}
    for product in products:
        equivalent_ids.setdefault(normalize_text(product["product_name_vi"]), []).append(
            product["product_id"]
        )

    builders = (
        ("accentless_title", lambda title: normalize_text(title)),
        (
            "conversational_title",
            lambda title: f"mình muốn tìm {_without_trailing_gender(title)} để mặc hằng ngày",
        ),
        ("reordered_keywords", _reordered_keywords),
        ("minor_typo", lambda title: _with_minor_typo(_without_trailing_gender(title))),
    )
    cases: list[dict[str, str]] = []
    for index, product in enumerate(products, 1):
        test_type, query_builder = builders[(index - 1) % len(builders)]
        title = product["product_name_vi"]
        cases.append(
            {
                # Product-backed IDs keep semantic judgments attached to the
                # same catalog item when database/100.sql is resampled.
                "query_id": (
                    f"{test_type.replace('_', '-')}-product-{product['product_id']}"
                ),
                "query_text": query_builder(title),
                "source_product_name_vi": title,
                "expected_product_id": product["product_id"],
                "acceptable_product_ids": "|".join(equivalent_ids[normalize_text(title)]),
                "test_type": test_type,
            }
        )
    return cases


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def acceptable_product_ids(row: dict[str, Any]) -> set[str]:
    raw = row.get("acceptable_product_ids")
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, str):
        values = raw.split("|")
    else:
        values = []
    acceptable = {str(value).strip() for value in values if str(value).strip()}
    if not acceptable and row.get("expected_product_id") is not None:
        acceptable.add(str(row["expected_product_id"]))
    return acceptable


def first_acceptable_rank(returned_ids: list[str], case: dict[str, Any]) -> int | None:
    acceptable = acceptable_product_ids(case)
    return next(
        (rank for rank, product_id in enumerate(returned_ids, 1) if product_id in acceptable),
        None,
    )


def load_semantic_judgments(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    judgments = payload.get("judgments", {})
    return judgments if isinstance(judgments, dict) else {}


def relevance_grades_for_case(
    case: dict[str, Any],
    judgments: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, int]:
    grades = {product_id: 3 for product_id in acceptable_product_ids(case)}
    for product_id, judgment in judgments.get(str(case.get("query_id", "")), {}).items():
        if isinstance(judgment, dict):
            grades[str(product_id)] = int(judgment.get("grade", 0))
    return grades


def ndcg_at_k(returned_ids: list[str], grades: dict[str, int], k: int) -> float:
    dcg = sum(
        (2 ** grades.get(product_id, 0) - 1) / math.log2(rank + 1)
        for rank, product_id in enumerate(returned_ids[:k], 1)
        if grades.get(product_id, 0) > 0
    )
    ideal = sorted(grades.values(), reverse=True)[:k]
    idcg = sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(ideal, 1)
        if grade > 0
    )
    return dcg / idcg if idcg else 0.0


def result_relevance_grades(row: dict[str, Any]) -> dict[str, int]:
    raw = row.get("relevance_grades")
    if isinstance(raw, dict) and raw:
        return {str(key): int(value) for key, value in raw.items()}
    return {product_id: 3 for product_id in acceptable_product_ids(row)}


def build_summary(
    results: list[dict[str, Any]],
    top_k: int,
    run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    successful = [row for row in results if row["status_code"] == 200]
    ranks = [row["expected_rank"] for row in successful if row["expected_rank"] is not None]
    source_ranks = [
        row.get("source_product_rank", row.get("expected_rank"))
        for row in successful
        if row.get("source_product_rank", row.get("expected_rank")) is not None
    ]
    latencies = [row["latency_ms"] for row in results]
    warning_counts = Counter(warning for row in results for warning in row["warnings"])
    source_counts = Counter(source for row in results for source in row["sources"])
    miss_filter_counts: Counter[str] = Counter()
    for row in results:
        if row["expected_rank"] is None:
            filters = row.get("response", {}).get("filters") or {}
            for key in ("category", "brand", "colors", "sizes", "min_price", "max_price", "gender", "material"):
                if filters.get(key) not in (None, "", []):
                    miss_filter_counts[key] += 1
    returned_result_count = sum(len(row["returned_product_ids"]) for row in results)
    test_type_counts = Counter(str(row.get("test_type", "unknown")) for row in results)
    metrics_by_test_type: dict[str, dict[str, Any]] = {}
    for test_type, count in sorted(test_type_counts.items()):
        typed_rows = [row for row in results if str(row.get("test_type", "unknown")) == test_type]
        typed_ranks = [row["expected_rank"] for row in typed_rows if row["expected_rank"] is not None]
        typed_ndcg = [
            ndcg_at_k(
                row["returned_product_ids"],
                result_relevance_grades(row),
                top_k,
            )
            for row in typed_rows
        ]
        metrics_by_test_type[test_type] = {
            "query_count": count,
            "hit_rate_at_1": sum(rank <= 1 for rank in typed_ranks) / count,
            "hit_rate_at_3": sum(rank <= 3 for rank in typed_ranks) / count,
            f"hit_rate_at_{top_k}": sum(rank <= top_k for rank in typed_ranks) / count,
            "mean_reciprocal_rank": sum(1 / rank for rank in typed_ranks) / count,
            f"ndcg_at_{top_k}": statistics.fmean(typed_ndcg) if typed_ndcg else 0.0,
            "empty_result_query_count": sum(not row["returned_product_ids"] for row in typed_rows),
        }
    exact_only = set(test_type_counts) == {"exact_title_vi"}
    test_scope = (
        "one exact-title query for each product in database/100.sql"
        if exact_only
        else "100-product deterministic robustness suite: accentless, conversational, "
        "reordered-keyword, and minor-typo queries"
    )
    semantic_ndcg = [
        ndcg_at_k(
            row["returned_product_ids"],
            result_relevance_grades(row),
            top_k,
        )
        for row in results
    ]
    judged_returned = sum(
        product_id in result_relevance_grades(row)
        for row in results
        for product_id in row["returned_product_ids"][:top_k]
    )
    total_returned_at_k = sum(min(top_k, len(row["returned_product_ids"])) for row in results)
    return {
        "run_context": run_context or {},
        "run_validity": (run_context or {}).get("validity", "UNKNOWN"),
        "test_scope": test_scope,
        "query_count": len(results),
        "test_type_counts": dict(test_type_counts),
        "metrics_by_test_type": metrics_by_test_type,
        "http_success_count": len(successful),
        "http_error_count": len(results) - len(successful),
        "hit_rate_at_1": sum(rank <= 1 for rank in ranks) / len(results),
        "hit_rate_at_3": sum(rank <= 3 for rank in ranks) / len(results),
        f"hit_rate_at_{top_k}": sum(rank <= top_k for rank in ranks) / len(results),
        "source_product_hit_rate_at_1": sum(rank <= 1 for rank in source_ranks) / len(results),
        f"source_product_hit_rate_at_{top_k}": sum(rank <= top_k for rank in source_ranks) / len(results),
        "miss_count": sum(row["expected_rank"] is None for row in results),
        "empty_result_query_count": sum(not row["returned_product_ids"] for row in results),
        "returned_result_count": returned_result_count,
        "mean_results_per_query": returned_result_count / len(results),
        "miss_filter_counts": dict(miss_filter_counts),
        "mean_reciprocal_rank": sum(1 / rank for rank in ranks) / len(results),
        "source_product_mean_reciprocal_rank": sum(1 / rank for rank in source_ranks) / len(results),
        f"semantic_ndcg_at_{top_k}": (
            statistics.fmean(semantic_ndcg) if semantic_ndcg else 0.0
        ),
        f"semantic_judgment_coverage_at_{top_k}": (
            judged_returned / total_returned_at_k if total_returned_at_k else 0.0
        ),
        "duplicate_result_query_count": sum(row["has_duplicate_product_ids"] for row in results),
        "mean_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "max_latency_ms": max(latencies, default=0.0),
        "warning_counts": dict(warning_counts),
        "source_counts": dict(source_counts),
        "ai_service_degraded_query_count": sum(
            "ai_service_unavailable" in row["warnings"] or "ai_keyword_fallback" in row["warnings"]
            for row in results
        ),
    }


def acceptance_gates(summary: dict[str, Any], top_k: int) -> bool:
    per_type_gate = all(
        metrics[f"hit_rate_at_{top_k}"] >= 0.80
        for metrics in summary["metrics_by_test_type"].values()
    )
    return (
        summary["run_validity"] in {"VALID", "UNKNOWN"}
        and summary["query_count"] == 100
        and summary["http_success_count"] == summary["query_count"]
        and summary["ai_service_degraded_query_count"] == 0
        and summary["hit_rate_at_1"] >= 0.70
        and summary[f"hit_rate_at_{top_k}"] >= 0.90
        and per_type_gate
        and summary["empty_result_query_count"] == 0
        and summary["duplicate_result_query_count"] == 0
        and summary["p95_latency_ms"] <= 3000
        and summary[f"semantic_ndcg_at_{top_k}"] >= MIN_SEMANTIC_NDCG
        and (
            summary[f"semantic_judgment_coverage_at_{top_k}"]
            >= MIN_SEMANTIC_JUDGMENT_COVERAGE
        )
    )


def assessment(summary: dict[str, Any], results: list[dict[str, Any]], top_k: int, endpoint: str) -> str:
    misses = [row for row in results if row["expected_rank"] is None]
    degraded = summary["ai_service_degraded_query_count"]
    gates_passed = acceptance_gates(summary, top_k)
    lines = [
        "# Assessment: text search on the 100-product pilot",
        "",
        "## Run context",
        "",
        f"- Endpoint: `{endpoint}`",
        f"- Scope: {summary['test_scope']}.",
        f"- Queries: {summary['query_count']} (`{json.dumps(summary['test_type_counts'], ensure_ascii=False)}`).",
        f"- HTTP success: {summary['http_success_count']}/{summary['query_count']}.",
        f"- Degraded/fallback responses: {degraded}/{summary['query_count']}.",
        "",
        "## Metrics",
        "",
        f"- Hit@1: {summary['hit_rate_at_1']:.1%}",
        f"- Hit@3: {summary['hit_rate_at_3']:.1%}",
        f"- Hit@{top_k}: {summary[f'hit_rate_at_{top_k}']:.1%}",
        f"- Exact source-product Hit@{top_k}: {summary[f'source_product_hit_rate_at_{top_k}']:.1%}",
        f"- Semantic NDCG@{top_k}: {summary[f'semantic_ndcg_at_{top_k}']:.4f}",
        (
            f"- Judgment coverage@{top_k}: "
            f"{summary[f'semantic_judgment_coverage_at_{top_k}']:.1%}"
        ),
        f"- MRR: {summary['mean_reciprocal_rank']:.4f}",
        f"- Misses: {summary['miss_count']}",
        f"- Empty-result queries: {summary['empty_result_query_count']}",
        (
            f"- Returned products: {summary['returned_result_count']} "
            f"(mean {summary['mean_results_per_query']:.2f}/query)"
        ),
        (
            f"- Latency p50/p95/max: {summary['p50_latency_ms']:.0f}/"
            f"{summary['p95_latency_ms']:.0f}/{summary['max_latency_ms']:.0f} ms"
        ),
        f"- Sources: `{json.dumps(summary['source_counts'], ensure_ascii=False)}`",
        f"- Warnings: `{json.dumps(summary['warning_counts'], ensure_ascii=False)}`",
        "",
        "## Findings",
        "",
    ]
    if degraded:
        lines.extend([
            (
                f"1. **The AI path was unavailable for {degraded}/{summary['query_count']} queries.** "
                "Results came from Spring's keyword fallback, so this run does not validate embedding, "
                "Qdrant retrieval, query understanding, or reranking quality."
            ),
            (
                "2. Restore `service-ai` readiness and connectivity first, then rerun this exact suite. "
                "Treat the rerun as a separate baseline and require `ai_source=text` with no "
                "`ai_service_unavailable` warning."
            ),
        ])
    else:
        lines.extend([
            (
                f"1. **The AI path is healthy for this run.** All {summary['query_count']} requests "
                "succeeded, all returned results use `ai_source=text`, and no fallback warnings were emitted."
            ),
            (
                f"2. **The robustness acceptance gate "
                f"{'passed' if gates_passed else 'did not pass'}.** Hit@{top_k} is "
                f"{summary[f'hit_rate_at_{top_k}']:.1%}, Hit@1 is "
                f"{summary['hit_rate_at_1']:.1%}, and "
                f"{summary['empty_result_query_count']} queries returned no product."
            ),
        ])
    if misses:
        examples = ", ".join(f"{row['query_id']}->{row['expected_product_id']}" for row in misses[:10])
        lines.append(
            f"3. **{len(misses)} robustness queries missed at Top {top_k}.** Examples: {examples}. "
            "Misses commonly carry extracted hard filters: "
            f"`{json.dumps(summary['miss_filter_counts'], ensure_ascii=False)}`."
        )
    else:
        lines.append(f"3. Every query retrieved an acceptable product in Top {top_k}.")
    type_metrics = "; ".join(
        f"{name}: Hit@{top_k}={metrics[f'hit_rate_at_{top_k}']:.1%}, "
        f"MRR={metrics['mean_reciprocal_rank']:.3f}"
        for name, metrics in summary["metrics_by_test_type"].items()
    )
    lines.append(f"4. Breakdown by query transformation: {type_metrics}.")
    lines.extend([
        (
            "5. Duplicate catalog titles are evaluated as an acceptable-ID group. The exact "
            "source-product rank remains available for variant-level diagnosis."
        ),
        "",
        f"## Acceptance gate: {'PASS' if gates_passed else 'FAIL'}",
        "",
        "- HTTP success = 100%.",
        "- Degraded/fallback responses = 0.",
        f"- Acceptable product Hit@1 >= 70% and Hit@{top_k} >= 90%.",
        f"- Every query type Hit@{top_k} >= 80%.",
        "- Empty-result queries = 0.",
        "- Duplicate product IDs = 0.",
        "- p95 latency <= 3 seconds (adjust only with an explicit production SLO).",
        (
            f"- Semantic NDCG@{top_k} >= {MIN_SEMANTIC_NDCG:.2f} with "
            f"{MIN_SEMANTIC_JUDGMENT_COVERAGE:.0%} judgment coverage."
        ),
        "- Broad use-case and negative queries remain a separate semantic extension.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", type=Path, default=ROOT / "database" / "100.sql")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--endpoint", default="/api/search/ai/text")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--ai-health-url",
        default="http://localhost:8000/health/ready/text_search",
    )
    parser.add_argument(
        "--ai-search-url",
        default="http://localhost:8000/search/text",
        help="Direct service-ai endpoint used by the preflight smoke check",
    )
    parser.add_argument("--health-check-every", type=int, default=10)
    parser.add_argument("--max-consecutive-fallbacks", type=int, default=1)
    parser.add_argument("--max-fallback-rate", type=float, default=0.0)
    parser.add_argument(
        "--collection-name",
        default="product_text_vectors_cohere_embed_v4_1536_metadata_v4_100_products",
    )
    parser.add_argument(
        "--semantic-judgments",
        type=Path,
        default=EVAL_DIR / "config" / "semantic_judgments.json",
    )
    parser.add_argument("--report-only", action="store_true", help="Recompute reports from the existing results.jsonl")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Regenerate products.csv and advanced test_cases.csv without calling the service",
    )
    args = parser.parse_args()
    if args.top_k <= 0:
        parser.error("--top-k must be greater than 0")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.health_check_every < 0:
        parser.error("--health-check-every must be 0 or greater")
    if args.max_consecutive_fallbacks <= 0:
        parser.error("--max-consecutive-fallbacks must be greater than 0")
    if not 0.0 <= args.max_fallback_rate <= 1.0:
        parser.error("--max-fallback-rate must be between 0 and 1")

    products = extract_products(args.sql)
    write_csv(EVAL_DIR / "data" / "products.csv", products, ["product_id", "product_name_vi"])

    url = args.base_url.rstrip("/") + "/" + args.endpoint.lstrip("/")
    context_path = EVAL_DIR / "reports" / "run_context.json"
    if args.report_only:
        jsonl_path = EVAL_DIR / "data" / "results.jsonl"
        results = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        semantic_judgments = load_semantic_judgments(args.semantic_judgments)
        for result in results:
            result["relevance_grades"] = relevance_grades_for_case(
                result,
                semantic_judgments,
            )
        run_context = json.loads(context_path.read_text(encoding="utf-8")) if context_path.exists() else {}
        summary = build_summary(results, args.top_k, run_context)
        summary["acceptance_gate_passed"] = acceptance_gates(summary, args.top_k)
        reports = EVAL_DIR / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (reports / "assessment.md").write_text(assessment(summary, results, args.top_k, url), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["acceptance_gate_passed"] else 1

    test_cases = build_advanced_cases(products)
    semantic_judgments = load_semantic_judgments(args.semantic_judgments)
    write_csv(
        EVAL_DIR / "data" / "test_cases.csv",
        test_cases,
        [
            "query_id",
            "query_text",
            "source_product_name_vi",
            "expected_product_id",
            "acceptable_product_ids",
            "test_type",
        ],
    )
    if args.prepare_only:
        print(
            f"Prepared {len(test_cases)} advanced test cases in "
            f"{EVAL_DIR / 'data' / 'test_cases.csv'}"
        )
        return 0

    readiness_status, readiness_body = get_json(
        args.ai_health_url,
        timeout=min(args.timeout, 10),
    )
    smoke = smoke_check(
        direct_url=args.ai_search_url,
        public_url=url,
        query=test_cases[0]["query_text"],
        timeout=args.timeout,
    )
    preflight_valid = (
        readiness_status == 200
        and readiness_body.get("ready") is True
        and smoke["valid"] is True
    )
    run_context = {
        "run_id": args.run_id or f"text-search-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
        "started_at": datetime.now(UTC).isoformat(),
        "endpoint": url,
        "ai_health_url": args.ai_health_url,
        "ai_readiness_status": readiness_status,
        "ai_readiness": readiness_body,
        "service_instance_id": readiness_body.get("instance_id"),
        "service_started_at": readiness_body.get("started_at"),
        "preflight_smoke": smoke,
        "validity": "RUNNING" if preflight_valid else "INVALID_PRECHECK",
        "collection_name": args.collection_name,
        "search_config": {
            "top_k": args.top_k,
            "timeout_seconds": args.timeout,
            "health_check_every": args.health_check_every,
            "max_consecutive_fallbacks": args.max_consecutive_fallbacks,
            "max_fallback_rate": args.max_fallback_rate,
        },
    }
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(run_context, ensure_ascii=False, indent=2), encoding="utf-8")
    if not preflight_valid:
        print(json.dumps(run_context, ensure_ascii=False, indent=2))
        print("Preflight failed; benchmark aborted before results were overwritten.", flush=True)
        return 2

    results: list[dict[str, Any]] = []
    ranked_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    jsonl_path = EVAL_DIR / "data" / "results.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    consecutive_fallbacks = 0
    aborted = False
    with jsonl_path.open("w", encoding="utf-8") as jsonl:
        for index, case in enumerate(test_cases, 1):
            if args.health_check_every > 0 and index > 1 and (index - 1) % args.health_check_every == 0:
                health_status, health_body = get_json(
                    args.ai_health_url,
                    timeout=min(args.timeout, 10),
                )
                instance_changed = (
                    run_context.get("service_instance_id")
                    and health_body.get("instance_id")
                    and health_body.get("instance_id") != run_context["service_instance_id"]
                )
                if health_status != 200 or health_body.get("ready") is not True or instance_changed:
                    run_context["validity"] = (
                        "INVALIDATED_BY_RESTART" if instance_changed else "DEGRADED"
                    )
                    run_context["abort_health_snapshot"] = health_body
                    aborted = True
                    break
            try:
                status, body, latency_ms = post_search(url, case["query_text"], args.top_k, args.timeout)
                returned = response_products(body)[: args.top_k]
                returned_ids = [str(item.get("product_id", "")) for item in returned]
                expected_id = case["expected_product_id"]
                source_product_rank = (
                    returned_ids.index(expected_id) + 1 if expected_id in returned_ids else None
                )
                expected_rank = first_acceptable_rank(returned_ids, case)
                sources = [str(item.get("ai_source", item.get("source", ""))) for item in returned]
                warnings = [str(value) for value in body.get("warnings", [])]
                error = ""
            except Exception as exc:  # keep the full 100-query run going
                status, body, latency_ms = 0, {}, 0.0
                returned, returned_ids, sources, warnings = [], [], [], []
                source_product_rank = None
                expected_rank = None
                error = f"{type(exc).__name__}: {exc}"

            result = {
                **case,
                "status_code": status,
                "latency_ms": round(latency_ms, 3),
                "expected_rank": expected_rank,
                "source_product_rank": source_product_rank,
                "returned_product_ids": returned_ids,
                "sources": sources,
                "warnings": warnings,
                "has_duplicate_product_ids": len(returned_ids) != len(set(returned_ids)),
                "error": error,
                "response": body,
                "relevance_grades": relevance_grades_for_case(case, semantic_judgments),
            }
            results.append(result)
            jsonl.write(json.dumps(result, ensure_ascii=False) + "\n")
            jsonl.flush()
            for rank, item in enumerate(returned, 1):
                product_id = str(item.get("product_id", ""))
                judgment = semantic_judgments.get(case["query_id"], {}).get(product_id, {})
                default_grade = result["relevance_grades"].get(product_id)
                ranked_rows.append({
                    "query_id": case["query_id"],
                    "query_text": case["query_text"],
                    "expected_product_id": case["expected_product_id"],
                    "acceptable_product_ids": case["acceptable_product_ids"],
                    "test_type": case["test_type"],
                    "rank": rank,
                    "product_id": item.get("product_id", ""),
                    "title_vi": item.get("title_vi", ""),
                    "score": item.get("ai_score", item.get("score", "")),
                    "source": item.get("ai_source", item.get("source", "")),
                })
                review_rows.append({
                    "query_id": case["query_id"],
                    "query_text": case["query_text"],
                    "test_type": case["test_type"],
                    "rank": rank,
                    "product_id": product_id,
                    "title_vi": item.get("title_vi", ""),
                    "relevance_grade": default_grade if default_grade is not None else "",
                    "review_status": (
                        judgment.get("review_status", "reviewed")
                        if default_grade is not None
                        else "pending"
                    ),
                    "notes": judgment.get("notes", ""),
                })
            print(
                f"[{index:03d}/{len(test_cases):03d}] {case['query_id']} status={status} "
                f"expected_rank={expected_rank} warnings={','.join(warnings) or '-'}",
                flush=True,
            )
            degraded_response = (
                "ai_service_unavailable" in warnings
                or "ai_keyword_fallback" in warnings
                or any(source != "text" for source in sources)
            )
            consecutive_fallbacks = consecutive_fallbacks + 1 if degraded_response else 0
            fallback_count = sum(
                "ai_service_unavailable" in row["warnings"]
                or "ai_keyword_fallback" in row["warnings"]
                or any(source != "text" for source in row["sources"])
                for row in results
            )
            fallback_rate = fallback_count / len(results)
            if (
                consecutive_fallbacks >= args.max_consecutive_fallbacks
                or fallback_rate > args.max_fallback_rate
            ):
                run_context["validity"] = "DEGRADED"
                run_context["abort_reason"] = {
                    "consecutive_fallbacks": consecutive_fallbacks,
                    "fallback_count": fallback_count,
                    "fallback_rate": fallback_rate,
                }
                aborted = True
                break

    write_csv(
        EVAL_DIR / "data" / "ranked_results.csv",
        ranked_rows,
        [
            "query_id",
            "query_text",
            "expected_product_id",
            "acceptable_product_ids",
            "test_type",
            "rank",
            "product_id",
            "title_vi",
            "score",
            "source",
        ],
    )
    write_csv(
        EVAL_DIR / "data" / "semantic_review_candidates.csv",
        review_rows,
        [
            "query_id",
            "query_text",
            "test_type",
            "rank",
            "product_id",
            "title_vi",
            "relevance_grade",
            "review_status",
            "notes",
        ],
    )
    if not aborted:
        run_context["validity"] = "VALID"
    run_context["completed_query_count"] = len(results)
    context_path.write_text(json.dumps(run_context, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = build_summary(results, args.top_k, run_context)
    summary["acceptance_gate_passed"] = acceptance_gates(summary, args.top_k)
    reports = EVAL_DIR / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports / "assessment.md").write_text(assessment(summary, results, args.top_k, url), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if aborted:
        return 2
    return 0 if summary["acceptance_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
