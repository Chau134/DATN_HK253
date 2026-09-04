from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import statistics
import unicodedata
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIGS = (
    "image_only", "text_only", "image_post_filter",
    "fusion_no_rerank", "fusion_rerank",
)
EXPECTED_RUN = {
    "image_only": ("image-only", False),
    "text_only": ("text-only", False),
    "image_post_filter": ("image-post-filter", False),
    "fusion_no_rerank": ("fusion", False),
    "fusion_rerank": ("fusion", True),
}
BOOTSTRAP_METRICS = (
    "strict_hit@5", "graded_ndcg@5", "graded_recall@5",
    "constraint_satisfaction@5", "constraint_success@5",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_run(name, query_ids, results, responses):
    expected_variant, expected_rerank = EXPECTED_RUN[name]
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


def required_constraints(query: dict[str, str]) -> dict[str, str]:
    fields = ("category", "color", "material", "price_bucket", "usage")
    return {field: query[field] for field in fields if normalize(query.get(field))}


def product_satisfies(product: dict[str, str] | None, constraints: dict[str, str]) -> bool:
    if not product:
        return False
    for field, expected in constraints.items():
        actual = price_bucket(product.get("price")) if field == "price_bucket" else product.get(field, "")
        if normalize(actual) != normalize(expected):
            return False
    return True


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
        relevant = {product_id for product_id, grade in grades.items() if grade >= 2}
        constraints = required_constraints(query)
        top5 = ranked[:5]
        satisfied = [product_satisfies(product_by_id.get(product_id), constraints) for product_id in top5]
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
            "graded_recall@5": sum(product_id in relevant for product_id in top5) / len(relevant) if relevant else 0.0,
            "constraint_satisfaction@5": sum(satisfied) / len(top5) if top5 else 0.0,
            "constraint_success@5": float(any(satisfied)),
            "returned@5": len(top5),
            "search_latency_ms": float(response.get("search_latency_ms") or 0),
            "http_ok": float(response.get("status_code") == 200),
        }
        per_query.append(row)
    return per_query


def aggregate(rows):
    metric_names = (
        "strict_hit@1", "strict_hit@5", "strict_hit@20", "graded_ndcg@5",
        "graded_recall@5", "constraint_satisfaction@5", "constraint_success@5", "http_ok",
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
        "relevance_threshold": 2,
        "constraint_contract": "independent exact normalized comparison against product_snapshot for every returned Top-5 product",
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
        "image_only": "Image-only", "text_only": "Text-only",
        "image_post_filter": "Image + text post-filter",
        "fusion_no_rerank": "Fusion, rerank off", "fusion_rerank": "Fusion, rerank on",
    }
    lines = [
        "# Hybrid Search Ablation", "",
        f"100 paired queries; {args.bootstrap_samples:,} bootstrap samples; seed {args.seed}.", "",
        "Constraint satisfaction is recomputed independently from `product_snapshot.csv`; it is not copied from the API response.", "",
        "| Configuration | Strict Hit@5 | Graded NDCG@5 | Graded Recall@5 | Constraint satisfaction@5 | Query success@5 | P95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in CONFIGS:
        a = aggregates[name]
        lines.append(
            f"| {labels[name]} | {a['strict_hit@5']:.3f} | {a['graded_ndcg@5']:.3f} | "
            f"{a['graded_recall@5']:.3f} | {a['constraint_satisfaction@5']:.3f} | "
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
