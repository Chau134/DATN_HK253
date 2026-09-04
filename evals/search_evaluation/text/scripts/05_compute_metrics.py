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

from common import (
    compute_negative_flag,
    ensure_parent_dir,
    load_json_config,
    mrr_from_ranks,
    ndcg_at_k,
    read_csv_rows,
    write_csv_rows,
)


def main() -> int:
    args = parse_args()
    k_values = [int(value) for value in str(args.k_values).split(",") if str(value).strip()]
    config = load_json_config(args.config) if args.config else {}
    paths = config.get("paths", {})

    results_csv = args.results_csv or _config_path(paths.get("search_results_csv")) or SCRIPT_DIR.parent / "data" / "search_results_text.csv"
    ground_truth_csv = args.ground_truth_csv or _config_path(paths.get("ground_truth_csv")) or SCRIPT_DIR.parent / "data" / "ground_truth_text.csv"
    query_set_csv = args.query_set_csv or _config_path(paths.get("query_set_csv")) or SCRIPT_DIR.parent / "data" / "text_queries.csv"
    output_json = args.output_json or _config_path(paths.get("metrics_json")) or SCRIPT_DIR.parent / "reports" / "metrics_text.json"
    output_csv = args.output_csv or _config_path(paths.get("metrics_csv")) or SCRIPT_DIR.parent / "reports" / "metrics_text.csv"

    result_rows = read_csv_rows(results_csv)
    ground_truth_rows = read_csv_rows(ground_truth_csv)
    query_rows = read_csv_rows(query_set_csv)

    results_by_query = _group_results_by_query(result_rows)
    grades_by_query = _grades_by_query(ground_truth_rows, args.relevance_threshold)
    query_meta = {row.get("query_id", ""): row for row in query_rows}

    per_query = _per_query_metrics(query_meta, results_by_query, grades_by_query, k_values, args.relevance_threshold)
    aggregate = _aggregate_metrics(per_query, k_values)
    breakdown = _breakdown_metrics(
        per_query,
        k_values,
        (
            'evaluation_slice',
            'semantic_variant_type',
            "intent_type",
            "constraint_semantics",
            "retrieval_scope",
            "relevant_cardinality_bucket",
            "difficulty",
            "category",
            "price_bucket",
        ),
    )
    negative_breakdown = _negative_breakdown_metrics(per_query, k_values, "intent_type")

    report = {
        "mode": "text",
        "relevance_threshold": args.relevance_threshold,
        "k_values": k_values,
        "query_count": len(per_query),
        "aggregate": aggregate,
        "breakdown": breakdown,
        "negative_breakdown": negative_breakdown,
        "per_query": per_query,
    }
    ensure_parent_dir(output_json)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    flat_rows, flat_fields = _flat_rows(aggregate, breakdown, k_values)
    write_csv_rows(output_csv, flat_rows, flat_fields)

    _print_summary(aggregate, k_values)
    print(f"metrics -> {output_json} , {output_csv}")
    return 0


def _group_results_by_query(rows: list[dict[str, str]]) -> dict[str, list[tuple[int, str]]]:
    grouped: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in rows:
        query_id = row.get("query_id", "")
        product_id = (row.get("product_id") or "").strip()
        rank_raw = (row.get("rank") or "").strip()
        try:
            rank = int(float(rank_raw))
        except ValueError:
            continue
        if rank <= 0 or not product_id:
            continue
        grouped[query_id].append((rank, product_id))
    for query_id in grouped:
        grouped[query_id].sort(key=lambda item: item[0])
    return grouped


def _grades_by_query(rows: list[dict[str, str]], threshold: int) -> dict[str, dict[str, int]]:
    grades: dict[str, dict[str, int]] = defaultdict(dict)
    for row in rows:
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


def _per_query_metrics(
    query_meta: dict[str, dict[str, str]],
    results_by_query: dict[str, list[tuple[int, str]]],
    grades_by_query: dict[str, dict[str, int]],
    k_values: list[int],
    threshold: int,
) -> list[dict[str, Any]]:
    per_query: list[dict[str, Any]] = []
    query_ids = set(query_meta) | set(results_by_query)
    for query_id in sorted(query_ids):
        meta = query_meta.get(query_id, {})
        query_type = (meta.get("query_type") or "positive").strip() or "positive"
        ranked = results_by_query.get(query_id, [])
        ranked_product_ids = [product_id for _, product_id in ranked]
        grades = grades_by_query.get(query_id, {})

        entry: dict[str, Any] = {
            'evaluation_slice': (meta.get('evaluation_slice') or 'canonical_v2').strip() or 'canonical_v2',
            'semantic_variant_type': (meta.get('semantic_variant_type') or 'none').strip() or 'none',
            'source_query_id': (meta.get('source_query_id') or '').strip(),
            "query_id": query_id,
            "query_type": query_type,
            "intent_type": (meta.get("intent_type") or "unknown").strip() or "unknown",
            "constraint_semantics": (meta.get("constraint_semantics") or "unknown").strip() or "unknown",
            "expected_behavior": (meta.get("expected_behavior") or "retrieve").strip() or "retrieve",
            "category": (meta.get("category") or "").strip(),
            "price_bucket": (meta.get("price_bucket") or "").strip(),
            "difficulty": (meta.get("difficulty") or "").strip(),
            "retrieval_scope": (meta.get("retrieval_scope") or "").strip(),
            "hits": len(ranked_product_ids),
        }

        if query_type == "negative":
            entry["empty_result_accuracy"] = 1.0 if not ranked_product_ids else 0.0
            entry["false_positive_flag"] = compute_negative_flag(query_type, len(ranked_product_ids))
            for k in k_values:
                entry[f"false_positive_rate@{k}"] = 1.0 if ranked_product_ids[:k] else 0.0
            per_query.append(entry)
            continue

        relevant_ids = {product_id for product_id, grade in grades.items() if grade >= threshold}
        total_relevant = len(relevant_ids)
        relevances = [grades.get(product_id, 0) for product_id in ranked_product_ids]
        ideal_relevances = list(grades.values())

        for k in k_values:
            top_k_ids = ranked_product_ids[:k]
            hits_k = sum(1 for product_id in top_k_ids if product_id in relevant_ids)
            retrieved_k = len(top_k_ids)
            recall = hits_k / total_relevant if total_relevant else 0.0
            recall_ceiling = min(k, total_relevant) / total_relevant if total_relevant else 0.0
            entry[f"precision@{k}"] = hits_k / k if k else 0.0
            entry[f"precision_at_retrieved@{k}"] = hits_k / retrieved_k if retrieved_k else 0.0
            entry[f"recall@{k}"] = recall
            entry[f"recall_ceiling@{k}"] = recall_ceiling
            entry[f"recall_efficiency@{k}"] = recall / recall_ceiling if recall_ceiling else 0.0
            entry[f"hit@{k}"] = 1.0 if hits_k else 0.0
            entry[f"ndcg@{k}"] = ndcg_at_k(relevances, ideal_relevances, k)

        relevant_ranks = [rank for rank, product_id in ranked if product_id in relevant_ids]
        entry["mrr"] = mrr_from_ranks(relevant_ranks)
        entry["first_relevant_rank"] = min(relevant_ranks) if relevant_ranks else 0
        entry["total_relevant"] = total_relevant
        if not entry["retrieval_scope"]:
            entry["retrieval_scope"] = _retrieval_scope(total_relevant, max(k_values, default=0))
        entry["relevant_cardinality_bucket"] = _relevant_cardinality_bucket(total_relevant)
        per_query.append(entry)
    return per_query


def _retrieval_scope(total_relevant: int, max_k: int) -> str:
    if total_relevant <= 1:
        return "singleton"
    if total_relevant <= max_k:
        return "bounded"
    return "broad"


def _relevant_cardinality_bucket(total_relevant: int) -> str:
    if total_relevant <= 1:
        return "1"
    if total_relevant <= 5:
        return "2_5"
    if total_relevant <= 20:
        return "6_20"
    if total_relevant <= 100:
        return "21_100"
    return "over_100"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _aggregate_metrics(per_query: list[dict[str, Any]], k_values: list[int]) -> dict[str, Any]:
    positives = [entry for entry in per_query if entry["query_type"] != "negative"]
    negatives = [entry for entry in per_query if entry["query_type"] == "negative"]

    positive_metrics: dict[str, Any] = {}
    for k in k_values:
        positive_metrics[f"precision@{k}"] = _mean([entry[f"precision@{k}"] for entry in positives])
        positive_metrics[f"precision_at_retrieved@{k}"] = _mean(
            [entry[f"precision_at_retrieved@{k}"] for entry in positives]
        )
        positive_metrics[f"recall@{k}"] = _mean([entry[f"recall@{k}"] for entry in positives])
        positive_metrics[f"recall_ceiling@{k}"] = _mean(
            [entry[f"recall_ceiling@{k}"] for entry in positives]
        )
        positive_metrics[f"recall_efficiency@{k}"] = _mean(
            [entry[f"recall_efficiency@{k}"] for entry in positives]
        )
        positive_metrics[f"hit@{k}"] = _mean([entry[f"hit@{k}"] for entry in positives])
        positive_metrics[f"ndcg@{k}"] = _mean([entry[f"ndcg@{k}"] for entry in positives])
    positive_metrics["mrr"] = _mean([entry["mrr"] for entry in positives])

    negative_metrics: dict[str, Any] = {}
    if negatives:
        negative_metrics["empty_result_accuracy"] = _mean([entry["empty_result_accuracy"] for entry in negatives])
        for k in k_values:
            negative_metrics[f"false_positive_rate@{k}"] = _mean([entry[f"false_positive_rate@{k}"] for entry in negatives])
        negative_metrics["false_positive_query_ids"] = [
            entry["query_id"] for entry in negatives if entry["false_positive_flag"]
        ]

    return {
        "positive_query_count": len(positives),
        "negative_query_count": len(negatives),
        "positive": positive_metrics,
        "negative": negative_metrics,
    }


def _breakdown_metrics(per_query: list[dict[str, Any]], k_values: list[int], fields: tuple[str, ...]) -> dict[str, Any]:
    breakdown: dict[str, Any] = {}
    positives = [entry for entry in per_query if entry["query_type"] != "negative"]
    for field in fields:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in positives:
            key = entry.get(field) or "unknown"
            groups[key].append(entry)
        field_report: dict[str, Any] = {}
        for key, entries in sorted(groups.items()):
            metrics: dict[str, float] = {"query_count": len(entries)}
            for k in k_values:
                metrics[f"precision@{k}"] = _mean([entry[f"precision@{k}"] for entry in entries])
                metrics[f"precision_at_retrieved@{k}"] = _mean(
                    [entry[f"precision_at_retrieved@{k}"] for entry in entries]
                )
                metrics[f"recall@{k}"] = _mean([entry[f"recall@{k}"] for entry in entries])
                metrics[f"recall_ceiling@{k}"] = _mean(
                    [entry[f"recall_ceiling@{k}"] for entry in entries]
                )
                metrics[f"recall_efficiency@{k}"] = _mean(
                    [entry[f"recall_efficiency@{k}"] for entry in entries]
                )
                metrics[f"hit@{k}"] = _mean([entry[f"hit@{k}"] for entry in entries])
                metrics[f"ndcg@{k}"] = _mean([entry[f"ndcg@{k}"] for entry in entries])
            metrics["mrr"] = _mean([entry["mrr"] for entry in entries])
            field_report[key] = metrics
        breakdown[field] = field_report
    return breakdown


def _negative_breakdown_metrics(
    per_query: list[dict[str, Any]],
    k_values: list[int],
    field: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in per_query:
        if entry["query_type"] == "negative":
            groups[entry.get(field) or "unknown"].append(entry)
    report: dict[str, Any] = {}
    for key, entries in sorted(groups.items()):
        metrics: dict[str, Any] = {
            "query_count": len(entries),
            "empty_result_accuracy": _mean([entry["empty_result_accuracy"] for entry in entries]),
            "false_positive_query_ids": [
                entry["query_id"] for entry in entries if entry["false_positive_flag"]
            ],
        }
        for k in k_values:
            metrics[f"false_positive_rate@{k}"] = _mean(
                [entry[f"false_positive_rate@{k}"] for entry in entries]
            )
        report[key] = metrics
    return report


def _flat_rows(aggregate: dict[str, Any], breakdown: dict[str, Any], k_values: list[int]) -> tuple[list[dict[str, Any]], list[str]]:
    metric_keys = []
    for k in k_values:
        metric_keys.extend(
            [
                f"precision@{k}",
                f"precision_at_retrieved@{k}",
                f"recall@{k}",
                f"recall_ceiling@{k}",
                f"recall_efficiency@{k}",
                f"hit@{k}",
                f"ndcg@{k}",
            ]
        )
    metric_keys.append("mrr")
    fields = ["scope", "group", "query_count", *metric_keys]

    rows: list[dict[str, Any]] = []

    overall = {"scope": "overall", "group": "positive", "query_count": aggregate["positive_query_count"]}
    for key in metric_keys:
        overall[key] = round(aggregate["positive"].get(key, 0.0), 4)
    rows.append(overall)

    for field, groups in breakdown.items():
        for group, metrics in groups.items():
            row = {"scope": field, "group": group, "query_count": metrics.get("query_count", 0)}
            for key in metric_keys:
                row[key] = round(metrics.get(key, 0.0), 4)
            rows.append(row)
    return rows, fields


def _print_summary(aggregate: dict[str, Any], k_values: list[int]) -> None:
    positive = aggregate["positive"]
    parts = [f"positive_queries={aggregate['positive_query_count']}"]
    for k in k_values:
        parts.append(f"P@{k}={positive.get(f'precision@{k}', 0.0):.3f}")
        parts.append(f"Hit@{k}={positive.get(f'hit@{k}', 0.0):.3f}")
        parts.append(f"RecallEff@{k}={positive.get(f'recall_efficiency@{k}', 0.0):.3f}")
        parts.append(f"NDCG@{k}={positive.get(f'ndcg@{k}', 0.0):.3f}")
    parts.append(f"MRR={positive.get('mrr', 0.0):.3f}")
    print(" ".join(parts))
    if aggregate["negative"]:
        print(f"negative_queries={aggregate['negative_query_count']} empty_result_accuracy={aggregate['negative'].get('empty_result_accuracy', 0.0):.3f}")


def _config_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else SCRIPT_DIR.parent / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute text search evaluation metrics against ground truth.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--results-csv", type=Path, default=None)
    parser.add_argument("--ground-truth-csv", type=Path, default=None)
    parser.add_argument("--query-set-csv", type=Path, default=None)
    parser.add_argument("--k-values", type=str, default="5,10,20")
    parser.add_argument("--relevance-threshold", type=int, default=1)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
