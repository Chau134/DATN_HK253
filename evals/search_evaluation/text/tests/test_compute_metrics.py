from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "05_compute_metrics.py"
SPEC = importlib.util.spec_from_file_location("text_compute_metrics", SCRIPT_PATH)
assert SPEC and SPEC.loader
METRICS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METRICS)


def test_ndcg_uses_all_ground_truth_grades_for_ideal_ranking() -> None:
    query_meta = {
        "q1": {
            "query_id": "q1",
            "query_type": "positive",
            "difficulty": "hard",
        }
    }
    results_by_query = {"q1": [(1, "low-relevance-product")]}
    grades_by_query = {
        "q1": {
            "high-relevance-product": 3,
            "medium-relevance-product": 2,
            "low-relevance-product": 1,
        }
    }

    [metrics] = METRICS._per_query_metrics(
        query_meta,
        results_by_query,
        grades_by_query,
        [5],
        threshold=1,
    )

    ideal_dcg = 7 + 3 / math.log2(3) + 1 / math.log2(4)
    assert metrics["ndcg@5"] == pytest.approx(1 / ideal_dcg)
    assert metrics["ndcg@5"] < 0.11


def test_singleton_query_reports_perfect_hit_and_recall_efficiency() -> None:
    [metrics] = METRICS._per_query_metrics(
        {
            "q1": {
                "query_id": "q1",
                "query_type": "positive",
                "intent_type": "exact_title",
                "retrieval_scope": "singleton",
            }
        },
        {"q1": [(1, "p1")]},
        {"q1": {"p1": 3}},
        [20],
        threshold=1,
    )

    assert metrics["precision@20"] == pytest.approx(0.05)
    assert metrics["precision_at_retrieved@20"] == pytest.approx(1.0)
    assert metrics["hit@20"] == pytest.approx(1.0)
    assert metrics["recall@20"] == pytest.approx(1.0)
    assert metrics["recall_ceiling@20"] == pytest.approx(1.0)
    assert metrics["recall_efficiency@20"] == pytest.approx(1.0)
    assert metrics["mrr"] == pytest.approx(1.0)


def test_broad_query_reaching_top_k_ceiling_has_full_recall_efficiency() -> None:
    relevant = {f"p{index}": 3 for index in range(1, 101)}
    ranked = [(index, f"p{index}") for index in range(1, 21)]

    [metrics] = METRICS._per_query_metrics(
        {"q1": {"query_id": "q1", "query_type": "positive", "intent_type": "facet_single"}},
        {"q1": ranked},
        {"q1": relevant},
        [20],
        threshold=1,
    )

    assert metrics["retrieval_scope"] == "broad"
    assert metrics["relevant_cardinality_bucket"] == "21_100"
    assert metrics["recall@20"] == pytest.approx(0.2)
    assert metrics["recall_ceiling@20"] == pytest.approx(0.2)
    assert metrics["recall_efficiency@20"] == pytest.approx(1.0)


def test_negative_breakdown_keeps_false_positive_query_ids() -> None:
    per_query = [
        {
            "query_id": "q-negative",
            "query_type": "negative",
            "intent_type": "negative_ood",
            "empty_result_accuracy": 0.0,
            "false_positive_flag": 1.0,
            "false_positive_rate@5": 1.0,
        }
    ]

    report = METRICS._negative_breakdown_metrics(per_query, [5], "intent_type")

    assert report["negative_ood"]["empty_result_accuracy"] == pytest.approx(0.0)
    assert report["negative_ood"]["false_positive_query_ids"] == ["q-negative"]
