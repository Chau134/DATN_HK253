from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import statistics
import sys
import unicodedata
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

SERVICE_SRC = Path(__file__).resolve().parents[4] / "service-ai" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from ecommerce_search_assistant.services.search.canonicalization import (
    canonicalize_material_keys, canonicalize_use_case_keys, catalog_color_keys,
)
from ecommerce_search_assistant.services.search.hybrid_intent import parse_hybrid_intent
from ecommerce_search_assistant.services.search.service import _filter_satisfaction

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIGS = (
    "text_only", "image_only", "fusion_no_rerank",
    "image_conditioned_no_rerank", "image_conditioned_rerank",
)
EXPECTED_RUN = {
    "text_only": ("text-only", False, False),
    "image_only": ("image-only", False, False),
    "fusion_no_rerank": ("fusion", False, False),
    "image_conditioned_no_rerank": ("fusion", False, True),
    "image_conditioned_rerank": ("fusion", True, True),
}
BOOTSTRAP_METRICS = (
    "strict_hit@5", "graded_ndcg@5", "request_conditioned_ndcg@5", "graded_recall@5",
    "constraint_satisfaction@5", "constraint_success@5",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_run(name, query_ids, results, responses):
    expected_variant, expected_rerank, expected_conditioned = EXPECTED_RUN[name]
    response_ids = [row.get("query_id") for row in responses]
    if len(responses) != len(query_ids) or len(set(response_ids)) != len(response_ids):
        raise ValueError(f"{name}: expected one response row per query")
    if set(response_ids) != set(query_ids):
        raise ValueError(f"{name}: response query IDs differ from the frozen query set")
    if any(row.get("status_code") != 200 for row in responses):
        raise ValueError(f"{name}: not all requests returned HTTP 200")
    if any(row.get("variant") != expected_variant for row in responses):
        raise ValueError(f"{name}: unexpected endpoint variant")
    if any(bool(row.get("reranker_enabled")) != expected_rerank for row in responses):
        raise ValueError(f"{name}: reranker state does not match the configuration")
    conditioned_states = [
        bool((row.get("effective_features") or {}).get("hybrid_image_conditioned_enabled"))
        for row in responses
    ]
    if any(state != expected_conditioned for state in conditioned_states):
        raise ValueError(f"{name}: image-conditioned state does not match the configuration")
    result_ids = {row.get("query_id") for row in results}
    if not result_ids.issubset(set(query_ids)):
        raise ValueError(f"{name}: results contain unknown query IDs")
    rerank_scores = 0
    reranked_queries = set()
    for row in results:
        if int(row.get("rank") or 0) <= 0:
            continue
        raw = json.loads(row.get("raw_score_json") or "{}")
        if raw.get("rerank_score") is not None:
            rerank_scores += 1
            reranked_queries.add(row["query_id"])
    if expected_rerank and not rerank_scores:
        raise ValueError(f"{name}: rerank is enabled but no rerank_score was recorded")
    if not expected_rerank and rerank_scores:
        raise ValueError(f"{name}: rerank_score exists while rerank is disabled")
    return {"rerank_score_rows": rerank_scores, "reranked_queries": len(reranked_queries)}


def normalize(value: str | None) -> str:
    value = (value or "").replace("Đ", "D").replace("đ", "d")
    value = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", ascii_text.casefold()).split())


def price_bucket(value: str | None) -> str:
    try:
        price = float(value or "")
    except ValueError:
        return ""
    if price < 200_000:
        return "under_200k"
    if price < 500_000:
        return "200k_500k"
    if price < 1_000_000:
        return "500k_1m"
    if price < 2_000_000:
        return "1m_2m"
    return "over_2m"


def legacy_exact_required_constraints(query: dict[str, str]) -> dict[str, str]:
    """Original report contract, retained only as a versioned diagnostic."""
    fields = ("category", "color", "material", "price_bucket", "usage")
    return {field: query[field] for field in fields if normalize(query.get(field))}


def legacy_exact_product_satisfies(product: dict[str, str] | None, constraints: dict[str, str]) -> bool:
    if not product:
        return False
    for field, expected in constraints.items():
        actual = price_bucket(product.get("price")) if field == "price_bucket" else product.get(field, "")
        if normalize(actual) != normalize(expected):
            return False
    return True


@lru_cache(maxsize=512)
def _parse_requested_intent(text: str):
    intent = parse_hybrid_intent(text)
    return intent


def _requested_intent(query: dict[str, str]):
    text = query.get("query_text") or ""
    intent = _parse_requested_intent(text)
    if intent.uncertain:
        raise ValueError(f"{query.get('query_id')}: unresolved requested constraints: {intent.uncertain}")
    return intent


def required_constraints(query: dict[str, str]) -> dict[str, Any]:
    """Only constraints explicitly expressed by the user's query text.

    Product category/visual identity is evaluated by relevance labels and NDCG;
    it is not silently added to the attribute-constraint score.
    """
    intent = _requested_intent(query)
    required = intent.required
    constraints: dict[str, Any] = {}
    if required.colors:
        constraints["color"] = {"values": list(required.colors), "mode": required.color_match_mode or "any"}
    if required.material:
        constraints["material"] = {
            "values": list(dict.fromkeys(canonicalize_material_keys([required.material]))),
            "mode": intent.material_mode,
            "composition": dict(intent.required_composition),
        }
    if required.use_cases:
        constraints["usage"] = {
            "values": list(required.use_cases), "phrases": list(intent.usage_phrases),
            "mode": intent.usage_mode,
        }
    if required.min_price is not None or required.max_price is not None:
        constraints["price"] = {"min": required.min_price, "max": required.max_price}
    declared = {part for part in (query.get("transformation_type") or "").split("_") if part}
    if declared and set(constraints) != declared:
        raise ValueError(
            f"{query.get('query_id')}: query-text scope {sorted(constraints)} "
            f"differs from declared transformation {sorted(declared)}"
        )
    if not constraints:
        raise ValueError(f"{query.get('query_id')}: no requested attribute constraint in query text")
    return constraints


def _snapshot_payload(product: dict[str, str]) -> dict[str, Any]:
    def stored_keys(name: str, fallback) -> list[str]:
        raw = product.get(name) or ""
        if raw:
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid canonical snapshot field {name} for product {product.get('product_id')}") from exc
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"Expected string list in {name} for product {product.get('product_id')}")
            return value
        return list(fallback)
    try:
        price = float(product.get("selling_price") or product.get("price") or "")
    except ValueError:
        price = None
    return {
        "product_id": product.get("product_id", ""),
        "base_colour": product.get("base_colour", ""),
        "base_colour_vi": product.get("base_colour_vi") or product.get("color", ""),
        "color_keys": stored_keys("color_keys_json", catalog_color_keys([product.get("color")])),
        "material": product.get("material_raw") or product.get("material", ""),
        "material_vi": product.get("material_vi") or product.get("material", ""),
        "material_keys": stored_keys("material_keys_json", canonicalize_material_keys([product.get("material")])),
        "product_usage_vi": product.get("product_usage_vi") or product.get("usage", ""),
        "use_case_keys": stored_keys("use_case_keys_json", canonicalize_use_case_keys([product.get("usage")])),
        "selling_price": price,
    }


def requested_constraint_results(query: dict[str, str], product: dict[str, str] | None) -> dict[str, bool]:
    constraints = required_constraints(query)
    if not product:
        return {field: False for field in constraints}
    intent = _requested_intent(query)
    checks = intent.checks(_snapshot_payload(product), _filter_satisfaction)
    results: dict[str, bool] = {}
    if "color" in constraints:
        results["color"] = bool(checks.get("colors"))
    if "material" in constraints:
        results["material"] = bool(checks.get("material")) and bool(checks.get("material_composition", True))
    if "usage" in constraints:
        results["usage"] = bool(checks.get("use_cases"))
    if "price" in constraints:
        price_checks = [checks.get(key) for key in ("min_price", "max_price") if key in checks]
        results["price"] = bool(price_checks) and all(price_checks)
    return results


def product_satisfies(product: dict[str, str] | None, query: dict[str, str]) -> bool:
    return all(requested_constraint_results(query, product).values())


def ndcg(ranked: list[str], grades: dict[str, int], k: int) -> float:
    def dcg(values: list[int]) -> float:
        return sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(values, 1))
    actual = dcg([grades.get(product_id, 0) for product_id in ranked[:k]])
    ideal = dcg(sorted(grades.values(), reverse=True)[:k])
    return actual / ideal if ideal else 0.0


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * probability
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def build_per_query(queries, products, ground_truth, results, responses):
    product_by_id = {row["product_id"]: row for row in products}
    grades_by_query: dict[str, dict[str, int]] = defaultdict(dict)
    for row in ground_truth:
        if row.get("review_status") == "approved":
            grades_by_query[row["query_id"]][row["relevant_product_id"]] = int(row["relevance_grade"])
    ranked_by_query: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in results:
        rank = int(row.get("rank") or 0)
        if rank > 0 and row.get("product_id"):
            ranked_by_query[row["query_id"]].append((rank, row["product_id"]))
    response_by_query = {row["query_id"]: row for row in responses}
    per_query = []
    for query in queries:
        query_id = query["query_id"]
        ranked = [product_id for _, product_id in sorted(ranked_by_query[query_id])]
        ranked = list(dict.fromkeys(ranked))
        grades = grades_by_query[query_id]
        request_conditioned_grades = {
            product_id: grade if product_satisfies(product_by_id.get(product_id), query) else 0
            for product_id, grade in grades.items()
        }
        relevant = {product_id for product_id, grade in grades.items() if grade >= 2}
        top5 = ranked[:5]
        constraint_fields = sorted(required_constraints(query))
        satisfied = [product_satisfies(product_by_id.get(product_id), query) for product_id in top5]
        legacy_constraints = legacy_exact_required_constraints(query)
        legacy_satisfied = [legacy_exact_product_satisfies(product_by_id.get(product_id), legacy_constraints) for product_id in top5]
        target = query["target_product_id"]
        target_rank = ranked.index(target) + 1 if target in ranked else None
        response = response_by_query.get(query_id, {})
        row = {
            "query_id": query_id,
            "difficulty": query["difficulty"],
            "transformation_type": query["transformation_type"],
            "strict_hit@1": float(bool(target_rank and target_rank <= 1)),
            "strict_hit@5": float(bool(target_rank and target_rank <= 5)),
            "strict_hit@20": float(bool(target_rank and target_rank <= 20)),
            "graded_ndcg@5": ndcg(ranked, grades, 5),
            "request_conditioned_ndcg@5": ndcg(ranked, request_conditioned_grades, 5),
            "graded_recall@5": sum(product_id in relevant for product_id in top5) / len(relevant) if relevant else 0.0,
            "constraint_satisfaction@5": sum(satisfied) / len(top5) if top5 else 0.0,
            "constraint_success@5": float(any(satisfied)),
            "legacy_exact_constraint_satisfaction@5": sum(legacy_satisfied) / len(top5) if top5 else 0.0,
            "legacy_exact_constraint_success@5": float(any(legacy_satisfied)),
            "requested_constraint_fields": constraint_fields,
            "returned@5": len(top5),
            "search_latency_ms": float(response.get("search_latency_ms") or 0),
            "http_ok": float(response.get("status_code") == 200),
        }
        per_query.append(row)
    return per_query


def aggregate(rows):
    metric_names = (
        "strict_hit@1", "strict_hit@5", "strict_hit@20", "graded_ndcg@5", "request_conditioned_ndcg@5",
        "graded_recall@5", "constraint_satisfaction@5", "constraint_success@5", "http_ok",
        "legacy_exact_constraint_satisfaction@5", "legacy_exact_constraint_success@5",
    )
    output = {metric: statistics.fmean(float(row[metric]) for row in rows) for metric in metric_names}
    latencies = [float(row["search_latency_ms"]) for row in rows if row["http_ok"]]
    output["mean_latency_ms"] = statistics.fmean(latencies) if latencies else 0.0
    output["p95_latency_ms"] = percentile(latencies, 0.95)
    output["query_count"] = len(rows)
    return output


def paired_bootstrap(left, right, samples: int, seed: int):
    left_by_id = {row["query_id"]: row for row in left}
    right_by_id = {row["query_id"]: row for row in right}
    query_ids = sorted(left_by_id)
    if query_ids != sorted(right_by_id):
        raise ValueError("paired configurations have different query IDs")
    rng = random.Random(seed)
    output = {}
    for metric in BOOTSTRAP_METRICS:
        deltas = [float(right_by_id[q][metric]) - float(left_by_id[q][metric]) for q in query_ids]
        boot = []
        for _ in range(samples):
            boot.append(statistics.fmean(deltas[rng.randrange(len(deltas))] for _ in deltas))
        output[metric] = {
            "delta": statistics.fmean(deltas),
            "ci95_low": percentile(boot, 0.025),
            "ci95_high": percentile(boot, 0.975),
        }
    return output


def parse_run(value: str) -> tuple[str, Path, Path]:
    try:
        name, result_path, response_path = value.split("=", 1)[0], *value.split("=", 1)[1].split(";", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("run must be NAME=RESULTS_CSV;RESPONSES_JSONL") from exc
    if name not in CONFIGS:
        raise argparse.ArgumentTypeError(f"unknown run name {name!r}")
    return name, Path(result_path), Path(response_path)


def main() -> int:
    args = parse_args()
    runs = dict((name, (results, responses)) for name, results, responses in args.run)
    missing = set(CONFIGS) - set(runs)
    if missing:
        raise ValueError(f"missing configurations: {sorted(missing)}")
    queries = read_csv(args.queries_csv)
    products = read_csv(args.products_csv)
    ground_truth = read_csv(args.ground_truth_csv)
    if len(queries) != 100 or any(row.get("review_status") != "approved" for row in ground_truth):
        raise ValueError("expected frozen approved Hybrid ground truth and 100 queries")
    ground_truth_pairs = [(row["query_id"], row["relevant_product_id"]) for row in ground_truth]
    if len(ground_truth_pairs) != len(set(ground_truth_pairs)):
        raise ValueError("Hybrid ground truth contains duplicate query-product pairs")
    query_ids = [row["query_id"] for row in queries]
    run_data = {
        name: (read_csv(paths[0]), read_jsonl(paths[1]))
        for name, paths in runs.items()
    }
    run_validation = {
        name: validate_run(name, query_ids, results, responses)
        for name, (results, responses) in run_data.items()
    }
    per_config = {
        name: build_per_query(queries, products, ground_truth, results, responses)
        for name, (results, responses) in run_data.items()
    }
    aggregates = {name: aggregate(rows) for name, rows in per_config.items()}
    comparisons = {}
    for left, right in itertools.combinations(CONFIGS, 2):
        comparisons[f"{right}_minus_{left}"] = paired_bootstrap(
            per_config[left], per_config[right], args.bootstrap_samples, args.seed
        )
    report = {
        "query_count": len(queries),
        "ground_truth_rows": len(ground_truth),
        "product_snapshot": str(args.products_csv),
        "product_snapshot_sha256": hashlib.sha256(args.products_csv.read_bytes()).hexdigest(),
        "relevance_threshold": 2,
        "constraint_contract": "v2: per returned Top-5 product, require only attributes parsed from user query text; all requested fields must pass; ordinary usage lists use ANY",
        "legacy_exact_constraint_contract": "v1 diagnostic: exact normalized comparison of every non-empty fixture category/color/material/price_bucket/usage field",
        "request_conditioned_ndcg_contract": "original human relevance grades are preserved; a judged product contributes zero gain for a query when it violates that query's request-scoped constraints",
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "run_validation": run_validation,
        "configurations": aggregates,
        "paired_comparisons": comparisons,
        "per_query": per_config,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        fields = ["configuration", *next(iter(aggregates.values())).keys()]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name in CONFIGS:
            writer.writerow({"configuration": name, **aggregates[name]})
    labels = {
        "text_only": "Text-only", "image_only": "Image-only",
        "fusion_no_rerank": "Fusion, rerank off",
        "image_conditioned_no_rerank": "Image-conditioned, usage ANY, rerank off",
        "image_conditioned_rerank": "Image-conditioned, usage ANY, rerank on",
    }
    lines = [
        "# Hybrid Search Ablation", "",
        f"100 paired queries; {args.bootstrap_samples:,} bootstrap samples; seed {args.seed}.", "",
        "Request-scoped constraint satisfaction is recomputed independently from user `query_text` and `product_snapshot.csv`; it is not copied from the API response. Legacy exact-fixture satisfaction is retained only as a diagnostic.", "",
        "| Configuration | Strict Hit@5 | Graded NDCG@5 | Request-conditioned NDCG@5 | Graded Recall@5 | Request-scoped satisfaction@5 | Legacy exact diagnostic | Query success@5 | P95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in CONFIGS:
        a = aggregates[name]
        lines.append(
            f"| {labels[name]} | {a['strict_hit@5']:.3f} | {a['graded_ndcg@5']:.3f} | {a['request_conditioned_ndcg@5']:.3f} | "
            f"{a['graded_recall@5']:.3f} | {a['constraint_satisfaction@5']:.3f} | "
            f"{a['legacy_exact_constraint_satisfaction@5']:.3f} | "
            f"{a['constraint_success@5']:.3f} | {a['p95_latency_ms']:.0f} |"
        )
    lines.extend(["", "## Paired bootstrap 95% CI", "", "Delta is right minus left.", "",
                  "| Comparison | Metric | Delta | CI 95% |", "|---|---|---:|---:|"])
    for comparison, metrics in comparisons.items():
        for metric in BOOTSTRAP_METRICS:
            stat = metrics[metric]
            lines.append(f"| {comparison} | {metric} | {stat['delta']:+.4f} | [{stat['ci95_low']:+.4f}, {stat['ci95_high']:+.4f}] |")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(aggregates, ensure_ascii=False, indent=2))
    print(f"comparison={args.output_json} markdown={args.output_md}")
    return 0


def parse_args() -> argparse.Namespace:
    root = SCRIPT_DIR.parent
    parser = argparse.ArgumentParser(description="Compare five Hybrid Search configurations with paired bootstrap CI.")
    parser.add_argument("--run", action="append", type=parse_run, required=True, help="NAME=RESULTS_CSV;RESPONSES_JSONL")
    parser.add_argument("--queries-csv", type=Path, default=root / "data/multimodal_queries.csv")
    parser.add_argument("--products-csv", type=Path, default=root / "data/product_snapshot.csv")
    parser.add_argument("--ground-truth-csv", type=Path, default=root / "data/ground_truth_multimodal.csv")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-json", type=Path, default=root / "reports/hybrid_ablation_comparison.json")
    parser.add_argument("--output-csv", type=Path, default=root / "reports/hybrid_ablation_summary.csv")
    parser.add_argument("--output-md", type=Path, default=root / "reports/hybrid_ablation_comparison.md")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
