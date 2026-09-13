from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
K_VALUES = (5, 10, 20)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def mean(values) -> float:
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def ndcg(ranked: list[str], grades: dict[str, int], k: int) -> float:
    def dcg(values: list[int]) -> float:
        return sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(values, 1))
    actual = dcg([grades.get(product_id, 0) for product_id in ranked[:k]])
    ideal = dcg(sorted(grades.values(), reverse=True)[:k])
    return actual / ideal if ideal else 0.0


def expected_fields(kind: str) -> set[str]:
    # Attribute-evaluation scope follows what the user asks to change/require.
    # Product type and visual identity are relevance concerns, not a hidden
    # attribute constraint added to every Hybrid query.
    fields = set()
    if "color" in kind:
        fields.add("colors")
    if "material" in kind:
        fields.add("material")
    if "usage" in kind:
        fields.add("use_cases")
    if kind == "price":
        fields.update(("min_price", "max_price"))
    return fields


def has_value(value) -> bool:
    return value not in (None, "", [], {})

def build_per_query(queries, result_rows, gt_rows, response_rows):
    ranked_by_query = defaultdict(list)
    for row in result_rows:
        try:
            rank = int(row.get("rank") or 0)
        except ValueError:
            rank = 0
        if rank > 0 and row.get("product_id"):
            ranked_by_query[row["query_id"]].append((rank, row["product_id"]))
    grades_by_query = defaultdict(dict)
    for row in gt_rows:
        product_id = row.get("relevant_product_id", "")
        if product_id:
            grades_by_query[row["query_id"]][product_id] = int(row.get("relevance_grade") or 0)
    responses = {row["query_id"]: row for row in response_rows}
    per_query = []
    for query in queries:
        query_id = query["query_id"]
        ranked = [product_id for _, product_id in sorted(ranked_by_query[query_id])]
        ranked = list(dict.fromkeys(ranked))
        target = query["target_product_id"]
        grades = grades_by_query[query_id]
        relevant = {product_id for product_id, grade in grades.items() if grade >= 2}
        target_rank = ranked.index(target) + 1 if target in ranked else None
        relevant_ranks = [index for index, product_id in enumerate(ranked, 1) if product_id in relevant]
        response_row = responses.get(query_id, {})
        response = response_row.get("response") or {}
        explicit = response.get("explicit_filters") or {}
        inferred = response.get("inferred_filters") or {}
        merged_filters = response.get("filters") or {}
        expected = expected_fields(query["transformation_type"])
        parsed_fields = {field for field in expected if has_value(merged_filters.get(field))}
        entry = {
            "query_id": query_id,
            "difficulty": query["difficulty"],
            "transformation_type": query["transformation_type"],
            "category": query["category"],
            "target_product_id": target,
            "target_rank": target_rank,
            "returned_count": len(ranked),
            "http_ok": response_row.get("status_code") == 200,
            "error": response_row.get("error", ""),
            "expected_filter_fields": sorted(expected),
            "parsed_filter_fields": sorted(parsed_fields),
            "explicit_filter_fields": sorted(field for field in expected if has_value(explicit.get(field))),
            "inferred_filter_fields": sorted(field for field in expected if has_value(inferred.get(field))),
            "filter_parse_complete": expected == parsed_fields,
            "search_latency_ms": float(response_row.get("search_latency_ms") or 0),
            "strict_mrr": 1 / target_rank if target_rank else 0.0,
            "graded_mrr": 1 / relevant_ranks[0] if relevant_ranks else 0.0,
        }
        for k in K_VALUES:
            top = ranked[:k]
            hits = sum(product_id in relevant for product_id in top)
            entry[f"strict_hit@{k}"] = bool(target_rank and target_rank <= k)
            entry[f"strict_ndcg@{k}"] = ndcg(ranked, {target: 3}, k)
            entry[f"graded_precision@{k}"] = hits / k
            entry[f"graded_recall@{k}"] = hits / len(relevant) if relevant else 0.0
            entry[f"graded_ndcg@{k}"] = ndcg(ranked, grades, k)
        per_query.append(entry)
    return per_query


def aggregate(rows):
    latencies = [row["search_latency_ms"] for row in rows if row["http_ok"]]
    result = {
        "query_count": len(rows),
        "http_success_rate": mean(row["http_ok"] for row in rows),
        "empty_result_rate": mean(row["returned_count"] == 0 for row in rows),
        "filter_parse_complete_rate": mean(row["filter_parse_complete"] for row in rows),
        "strict_mrr": mean(row["strict_mrr"] for row in rows),
        "graded_mrr": mean(row["graded_mrr"] for row in rows),
        "mean_search_latency_ms": mean(latencies),
        "p50_search_latency_ms": percentile(latencies, 0.50),
        "p95_search_latency_ms": percentile(latencies, 0.95),
    }
    for k in K_VALUES:
        result[f"strict_hit@{k}"] = mean(row[f"strict_hit@{k}"] for row in rows)
        result[f"strict_ndcg@{k}"] = mean(row[f"strict_ndcg@{k}"] for row in rows)
        for metric in ("precision", "recall", "ndcg"):
            key = f"graded_{metric}@{k}"
            result[key] = mean(row[key] for row in rows)
    return result


def breakdown(per_query, field):
    groups = defaultdict(list)
    for row in per_query:
        groups[row[field]].append(row)
    return {name: aggregate(rows) for name, rows in sorted(groups.items())}


def write_csv(path: Path, report: dict) -> None:
    rows = []
    for scope, groups in (
        ("overall", {"all": report["aggregate"]}),
        ("difficulty", report["breakdown"]["difficulty"]),
        ("transformation_type", report["breakdown"]["transformation_type"]),
    ):
        for group, metrics in groups.items():
            rows.append({"scope": scope, "group": group, **metrics})
    fields = list(dict.fromkeys(key for row in rows for key in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def markdown(report: dict) -> str:
    aggregate_metrics = report["aggregate"]
    lines = [
        "# Hybrid Search Evaluation", "",
        f"- Queries: {aggregate_metrics['query_count']}",
        f"- HTTP success: {aggregate_metrics['http_success_rate']:.1%}",
        f"- Strict Hit@1/5/10/20: {report['strict_hit_at_1']:.1%} / "
        f"{aggregate_metrics['strict_hit@5']:.1%} / {aggregate_metrics['strict_hit@10']:.1%} / "
        f"{aggregate_metrics['strict_hit@20']:.1%}",
        f"- Strict MRR: {aggregate_metrics['strict_mrr']:.4f}",
        f"- Graded NDCG@5/10/20: {aggregate_metrics['graded_ndcg@5']:.4f} / "
        f"{aggregate_metrics['graded_ndcg@10']:.4f} / {aggregate_metrics['graded_ndcg@20']:.4f}",
        f"- Filter parse complete: {aggregate_metrics['filter_parse_complete_rate']:.1%}",
        f"- Latency p50/p95: {aggregate_metrics['p50_search_latency_ms']:.0f}/"
        f"{aggregate_metrics['p95_search_latency_ms']:.0f} ms", "",
        "## Transformation breakdown", "",
        "| Type | N | Strict Hit@1 | Hit@5 | Hit@20 | Strict MRR | Graded NDCG@5 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, metrics in report["breakdown"]["transformation_type"].items():
        rows = [row for row in report["per_query"] if row["transformation_type"] == name]
        lines.append(
            f"| {name} | {metrics['query_count']} | "
            f"{mean(row['target_rank'] == 1 for row in rows):.1%} | "
            f"{metrics['strict_hit@5']:.1%} | {metrics['strict_hit@20']:.1%} | "
            f"{metrics['strict_mrr']:.4f} | {metrics['graded_ndcg@5']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    queries = read_csv(args.queries_csv)
    results = read_csv(args.results_csv)
    ground_truth = read_csv(args.ground_truth_csv)
    responses = read_jsonl(args.responses_jsonl)
    per_query = build_per_query(queries, results, ground_truth, responses)
    report = {
        "mode": "multimodal",
        "ground_truth_contract": {
            "strict": "target_product_id only; user-approved counterfactual image",
            "graded": "all approved grade >=2 candidates; provenance is preserved per judgment",
        },
        "k_values": list(K_VALUES),
        "aggregate": aggregate(per_query),
        "breakdown": {
            "difficulty": breakdown(per_query, "difficulty"),
            "transformation_type": breakdown(per_query, "transformation_type"),
        },
        "strict_hit_at_1": mean(row["target_rank"] == 1 for row in per_query),
        "status_counts": dict(Counter(str(row.get("status_code")) for row in responses)),
        "miss_query_ids": [row["query_id"] for row in per_query if row["target_rank"] is None],
        "filter_parse_failure_query_ids": [
            row["query_id"] for row in per_query if not row["filter_parse_complete"]
        ],
        "per_query": per_query,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(args.output_csv, report)
    args.output_markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2))
    print(f"strict_hit@1={report['strict_hit_at_1']:.4f} misses={len(report['miss_query_ids'])}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "multimodal_queries.csv")
    parser.add_argument("--results-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "search_results_multimodal.csv")
    parser.add_argument("--ground-truth-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_multimodal.csv")
    parser.add_argument("--responses-jsonl", type=Path, default=SCRIPT_DIR.parent / "reports" / "hybrid_eval_responses.jsonl")
    parser.add_argument("--output-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "metrics_multimodal.json")
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "metrics_multimodal.csv")
    parser.add_argument("--output-markdown", type=Path, default=SCRIPT_DIR.parent / "reports" / "hybrid_evaluation.md")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
