from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import average_precision, ensure_parent_dir, mrr_from_ranks, ndcg_at_k, read_csv_rows, write_csv_rows


def main() -> int:
    args = parse_args()
    k_values = [int(value) for value in str(args.k_values).split(",") if str(value).strip()]

    result_rows = read_csv_rows(args.results_csv)
    ground_truth_rows = read_csv_rows(args.ground_truth_csv)
    query_rows = read_csv_rows(args.query_set_csv)

    results_by_query = _group_results_by_query(result_rows)
    latencies_by_query = _latencies_by_query(result_rows)
    grades_by_query = _grades_by_query(ground_truth_rows)
    query_meta = {row.get("query_id", ""): row for row in query_rows}

    per_query = _per_query_metrics(
        query_meta,
        results_by_query,
        grades_by_query,
        k_values,
        args.relevance_threshold,
        latencies_by_query,
    )
    aggregate = _aggregate_metrics(per_query, k_values)
    breakdown = _breakdown_metrics(per_query, k_values, ("difficulty", "category", "semantic_image_type", "image_quality"))

    report = {
        "mode": "image",
        "relevance_threshold": args.relevance_threshold,
        "k_values": k_values,
        "query_count": len(per_query),
        "metric_definitions": {
            "precision@returned": "relevant unique products / returned unique products",
            "fulfillment@k": "min(returned unique products, k) / k",
            "underfill_rate@k": "share of queries returning fewer than k unique products",
            "exact_hit@k": "share of queries whose source_product_id appears in top k",
            "exact_mrr": "mean reciprocal rank of source_product_id",
            "latency_ms": "client-observed AI Service HTTP latency; excludes fixture image download",
            "latency_p95_ms": "R-7 linearly interpolated 95th percentile over successful requests",
        },
        "aggregate": aggregate,
        "breakdown": breakdown,
        "per_query": per_query,
    }
    ensure_parent_dir(args.output_json)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    flat_rows, flat_fields = _flat_rows(aggregate, breakdown, k_values)
    write_csv_rows(args.output_csv, flat_rows, flat_fields)

    _print_summary(aggregate, k_values)
    print(f"metrics -> {args.output_json} , {args.output_csv}")
    return 0


def _group_results_by_query(rows: list[dict[str, str]]) -> dict[str, list[tuple[int, str]]]:
    grouped: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in rows:
        query_id = row.get("query_id", "")
        product_id = (row.get("product_id") or "").strip()
        try:
            rank = int(float((row.get("rank") or "").strip()))
        except ValueError:
            continue
        if rank > 0 and product_id:
            grouped[query_id].append((rank, product_id))
    for query_id in grouped:
        grouped[query_id].sort(key=lambda item: item[0])
    return grouped


def _grades_by_query(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    grades: dict[str, dict[str, int]] = defaultdict(dict)
    for row in rows:
        if row.get("review_status") and row.get("review_status") != "approved":
            continue
        query_id = row.get("query_id", "")
        product_id = (row.get("relevant_product_id") or "").strip()
        if not product_id:
            continue
        try:
            grade = int(float((row.get("relevance_grade") or "0").strip()))
        except ValueError:
            grade = 0
        grades[query_id][product_id] = grade
    return grades


def _latencies_by_query(rows: list[dict[str, str]]) -> dict[str, float]:
    latencies: dict[str, float] = {}
    for row in rows:
        query_id = (row.get("query_id") or "").strip()
        if not query_id or query_id in latencies:
            continue
        status = (row.get("request_status") or "").strip()
        if status and status != "success":
            continue
        try:
            latency_ms = float((row.get("latency_ms") or "").strip())
        except ValueError:
            continue
        if latency_ms >= 0:
            latencies[query_id] = latency_ms
    return latencies


def _per_query_metrics(
    query_meta: dict[str, dict[str, str]],
    results_by_query: dict[str, list[tuple[int, str]]],
    grades_by_query: dict[str, dict[str, int]],
    k_values: list[int],
    threshold: int,
    latencies_by_query: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    per_query: list[dict[str, Any]] = []
    query_ids = set(query_meta) | set(results_by_query)
    for query_id in sorted(query_ids):
        meta = query_meta.get(query_id, {})
        ranked = results_by_query.get(query_id, [])
        returned_product_ids = [product_id for _, product_id in ranked]
        ranked_product_ids = list(dict.fromkeys(returned_product_ids))
        grades = grades_by_query.get(query_id, {})
        relevant_ids = {product_id for product_id, grade in grades.items() if grade >= threshold}
        relevances = [grades.get(product_id, 0) for product_id in ranked_product_ids]
        ideal_relevances = list(grades.values())
        source_product_id = (meta.get("source_product_id") or "").strip()
        exact_rank = (
            ranked_product_ids.index(source_product_id) + 1
            if source_product_id and source_product_id in ranked_product_ids
            else None
        )
        returned_relevant = sum(1 for product_id in ranked_product_ids if product_id in relevant_ids)
        entry: dict[str, Any] = {
            "query_id": query_id,
            "category": (meta.get("category") or "").strip() or "unknown",
            "semantic_image_type": (meta.get("semantic_image_type") or "").strip() or "unknown",
            "image_quality": (meta.get("image_quality") or "").strip() or "unknown",
            "difficulty": (meta.get("difficulty") or "").strip() or "unknown",
            "hits": len(ranked_product_ids),
            "returned_count": len(returned_product_ids),
            "unique_product_count": len(ranked_product_ids),
            "total_relevant": len(relevant_ids),
            "precision@returned": returned_relevant / len(ranked_product_ids) if ranked_product_ids else 0.0,
            "exact_rank": exact_rank,
            "exact_hit@1": 1.0 if exact_rank == 1 else 0.0,
            "exact_reciprocal_rank": 1.0 / exact_rank if exact_rank else 0.0,
            "latency_ms": (latencies_by_query or {}).get(query_id),
        }
        for k in k_values:
            top_k_ids = ranked_product_ids[:k]
            hits_k = sum(1 for product_id in top_k_ids if product_id in relevant_ids)
            entry[f"precision@{k}"] = hits_k / k if k else 0.0
            entry[f"recall@{k}"] = hits_k / len(relevant_ids) if relevant_ids else 0.0
            entry[f"ndcg@{k}"] = ndcg_at_k(relevances, ideal_relevances, k)
            entry[f"fulfillment@{k}"] = min(len(ranked_product_ids), k) / k if k else 0.0
            entry[f"underfill@{k}"] = 1.0 if len(ranked_product_ids) < k else 0.0
            entry[f"exact_hit@{k}"] = 1.0 if exact_rank and exact_rank <= k else 0.0
        relevant_ranks = [rank for rank, product_id in enumerate(ranked_product_ids, start=1) if product_id in relevant_ids]
        entry["mrr"] = mrr_from_ranks(relevant_ranks)
        entry["ap"] = average_precision(ranked_product_ids, relevant_ids)
        per_query.append(entry)
    return per_query


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _latency_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(entry["latency_ms"]) for entry in entries if entry.get("latency_ms") is not None]
    return {
        "latency_sample_count": len(values),
        "latency_avg_ms": _mean(values) if values else None,
        "latency_p50_ms": _percentile(values, 0.50),
        "latency_p95_ms": _percentile(values, 0.95),
        "latency_p99_ms": _percentile(values, 0.99),
    }


def _aggregate_metrics(per_query: list[dict[str, Any]], k_values: list[int]) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "query_count": len(per_query),
        "returned_count_avg": _mean([entry["returned_count"] for entry in per_query]),
        "unique_product_count_avg": _mean([entry["unique_product_count"] for entry in per_query]),
        "precision@returned": _mean([entry["precision@returned"] for entry in per_query]),
        "exact_hit@1": _mean([entry["exact_hit@1"] for entry in per_query]),
    }
    for k in k_values:
        metrics[f"precision@{k}"] = _mean([entry[f"precision@{k}"] for entry in per_query])
        metrics[f"recall@{k}"] = _mean([entry[f"recall@{k}"] for entry in per_query])
        metrics[f"ndcg@{k}"] = _mean([entry[f"ndcg@{k}"] for entry in per_query])
        metrics[f"fulfillment@{k}"] = _mean([entry[f"fulfillment@{k}"] for entry in per_query])
        metrics[f"underfill_rate@{k}"] = _mean([entry[f"underfill@{k}"] for entry in per_query])
        metrics[f"exact_hit@{k}"] = _mean([entry[f"exact_hit@{k}"] for entry in per_query])
    metrics["mrr"] = _mean([entry["mrr"] for entry in per_query])
    metrics["map"] = _mean([entry["ap"] for entry in per_query])
    metrics["exact_mrr"] = _mean([entry["exact_reciprocal_rank"] for entry in per_query])
    metrics.update(_latency_summary(per_query))
    return metrics


def _breakdown_metrics(per_query: list[dict[str, Any]], k_values: list[int], fields: tuple[str, ...]) -> dict[str, Any]:
    breakdown: dict[str, Any] = {}
    for field in fields:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in per_query:
            groups[entry.get(field) or "unknown"].append(entry)
        field_report: dict[str, Any] = {}
        for key, entries in sorted(groups.items()):
            metrics: dict[str, float] = {
                "query_count": len(entries),
                "returned_count_avg": _mean([entry["returned_count"] for entry in entries]),
                "unique_product_count_avg": _mean([entry["unique_product_count"] for entry in entries]),
                "precision@returned": _mean([entry["precision@returned"] for entry in entries]),
                "exact_hit@1": _mean([entry["exact_hit@1"] for entry in entries]),
            }
            for k in k_values:
                metrics[f"precision@{k}"] = _mean([entry[f"precision@{k}"] for entry in entries])
                metrics[f"recall@{k}"] = _mean([entry[f"recall@{k}"] for entry in entries])
                metrics[f"ndcg@{k}"] = _mean([entry[f"ndcg@{k}"] for entry in entries])
                metrics[f"fulfillment@{k}"] = _mean([entry[f"fulfillment@{k}"] for entry in entries])
                metrics[f"underfill_rate@{k}"] = _mean([entry[f"underfill@{k}"] for entry in entries])
                metrics[f"exact_hit@{k}"] = _mean([entry[f"exact_hit@{k}"] for entry in entries])
            metrics["mrr"] = _mean([entry["mrr"] for entry in entries])
            metrics["map"] = _mean([entry["ap"] for entry in entries])
            metrics["exact_mrr"] = _mean([entry["exact_reciprocal_rank"] for entry in entries])
            metrics.update(_latency_summary(entries))
            field_report[key] = metrics
        breakdown[field] = field_report
    return breakdown


def _flat_rows(aggregate: dict[str, Any], breakdown: dict[str, Any], k_values: list[int]) -> tuple[list[dict[str, Any]], list[str]]:
    metric_keys = ["returned_count_avg", "unique_product_count_avg", "precision@returned", "exact_hit@1"]
    for k in k_values:
        metric_keys.extend(
            [
                f"precision@{k}",
                f"recall@{k}",
                f"ndcg@{k}",
                f"fulfillment@{k}",
                f"underfill_rate@{k}",
                f"exact_hit@{k}",
            ]
        )
    metric_keys.extend(
        [
            "mrr",
            "map",
            "exact_mrr",
            "latency_sample_count",
            "latency_avg_ms",
            "latency_p50_ms",
            "latency_p95_ms",
            "latency_p99_ms",
        ]
    )
    fields = ["scope", "group", "query_count", *metric_keys]
    rows: list[dict[str, Any]] = [{"scope": "overall", "group": "all", "query_count": aggregate.get("query_count", 0)}]
    for key in metric_keys:
        value = aggregate.get(key)
        rows[0][key] = "" if value is None else round(value, 4)
    for field, groups in breakdown.items():
        for group, metrics in groups.items():
            row = {"scope": field, "group": group, "query_count": metrics.get("query_count", 0)}
            for key in metric_keys:
                value = metrics.get(key)
                row[key] = "" if value is None else round(value, 4)
            rows.append(row)
    return rows, fields


def _print_summary(aggregate: dict[str, Any], k_values: list[int]) -> None:
    parts = [
        f"queries={aggregate.get('query_count', 0)}",
        f"ExactHit@1={aggregate.get('exact_hit@1', 0.0):.3f}",
    ]
    for k in k_values:
        parts.append(f"P@{k}={aggregate.get(f'precision@{k}', 0.0):.3f}")
        parts.append(f"NDCG@{k}={aggregate.get(f'ndcg@{k}', 0.0):.3f}")
        parts.append(f"Fill@{k}={aggregate.get(f'fulfillment@{k}', 0.0):.3f}")
        parts.append(f"ExactHit@{k}={aggregate.get(f'exact_hit@{k}', 0.0):.3f}")
    parts.append(f"P@returned={aggregate.get('precision@returned', 0.0):.3f}")
    parts.append(f"MRR={aggregate.get('mrr', 0.0):.3f}")
    parts.append(f"ExactMRR={aggregate.get('exact_mrr', 0.0):.3f}")
    parts.append(f"mAP={aggregate.get('map', 0.0):.3f}")
    if aggregate.get("latency_p95_ms") is not None:
        parts.append(
            f"P95={aggregate['latency_p95_ms']:.1f}ms"
            f"({aggregate.get('latency_sample_count', 0)}/{aggregate.get('query_count', 0)})"
        )
    print(" ".join(parts))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute image search evaluation metrics against ground truth.")
    parser.add_argument("--results-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "search_results_image.csv")
    parser.add_argument("--ground-truth-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_image.csv")
    parser.add_argument("--query-set-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_queries.csv")
    parser.add_argument("--k-values", type=str, default="5,10,20")
    parser.add_argument("--relevance-threshold", type=int, default=2)
    parser.add_argument("--output-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "metrics_image.json")
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "metrics_image.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
