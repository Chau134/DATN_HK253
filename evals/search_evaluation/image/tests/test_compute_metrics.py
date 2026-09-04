from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "05_compute_metrics.py"
SPEC = importlib.util.spec_from_file_location("image_compute_metrics", SCRIPT_PATH)
assert SPEC and SPEC.loader
METRICS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METRICS)


def test_ndcg_uses_all_ground_truth_grades_for_ideal_ranking() -> None:
    [metrics] = METRICS._per_query_metrics(
        {"q1": {"query_id": "q1", "source_product_id": "exact"}},
        {"q1": [(1, "low-relevance-product")]},
        {
            "q1": {
                "exact": 3,
                "medium-relevance-product": 2,
                "low-relevance-product": 1,
            }
        },
        [5],
        threshold=1,
    )

    ideal_dcg = 7 + 3 / math.log2(3) + 1 / math.log2(4)
    assert metrics["ndcg@5"] == pytest.approx(1 / ideal_dcg)
    assert metrics["ndcg@5"] < 0.11


def test_underfilled_results_report_fulfillment_and_precision_at_returned() -> None:
    [metrics] = METRICS._per_query_metrics(
        {"q1": {"query_id": "q1", "source_product_id": "p1"}},
        {"q1": [(1, "p1"), (2, "p2")]},
        {"q1": {"p1": 3, "p2": 0}},
        [5, 10],
        threshold=1,
    )

    assert metrics["precision@5"] == pytest.approx(0.2)
    assert metrics["precision@returned"] == pytest.approx(0.5)
    assert metrics["fulfillment@5"] == pytest.approx(0.4)
    assert metrics["fulfillment@10"] == pytest.approx(0.2)
    assert metrics["underfill@5"] == pytest.approx(1.0)
    assert metrics["underfill@10"] == pytest.approx(1.0)


def test_exact_product_metrics_are_independent_from_broad_relevance() -> None:
    [metrics] = METRICS._per_query_metrics(
        {"q1": {"query_id": "q1", "source_product_id": "exact"}},
        {"q1": [(1, "similar"), (2, "exact")]},
        {"q1": {"similar": 2, "exact": 3}},
        [1, 5],
        threshold=1,
    )

    assert metrics["exact_rank"] == 2
    assert metrics["exact_hit@1"] == pytest.approx(0.0)
    assert metrics["exact_hit@5"] == pytest.approx(1.0)
    assert metrics["exact_reciprocal_rank"] == pytest.approx(0.5)


def test_duplicate_products_do_not_inflate_fulfillment_or_precision() -> None:
    [metrics] = METRICS._per_query_metrics(
        {"q1": {"query_id": "q1", "source_product_id": "p1"}},
        {"q1": [(1, "p1"), (2, "p1"), (3, "p2")]},
        {"q1": {"p1": 3, "p2": 0}},
        [5],
        threshold=1,
    )

    assert metrics["returned_count"] == 3
    assert metrics["unique_product_count"] == 2
    assert metrics["precision@returned"] == pytest.approx(0.5)
    assert metrics["fulfillment@5"] == pytest.approx(0.4)


def test_aggregate_reports_underfill_rate_and_exact_mrr() -> None:
    per_query = METRICS._per_query_metrics(
        {
            "q1": {"query_id": "q1", "source_product_id": "p1"},
            "q2": {"query_id": "q2", "source_product_id": "p4"},
        },
        {
            "q1": [(1, "p1"), (2, "p2")],
            "q2": [(1, "p3"), (2, "p4"), (3, "p5"), (4, "p6"), (5, "p7")],
        },
        {"q1": {"p1": 3}, "q2": {"p4": 3}},
        [5],
        threshold=1,
    )

    aggregate = METRICS._aggregate_metrics(per_query, [5])

    assert aggregate["fulfillment@5"] == pytest.approx(0.7)
    assert aggregate["underfill_rate@5"] == pytest.approx(0.5)
    assert aggregate["exact_hit@1"] == pytest.approx(0.5)
    assert aggregate["exact_hit@5"] == pytest.approx(1.0)
    assert aggregate["exact_mrr"] == pytest.approx(0.75)

def test_latency_uses_one_successful_sample_per_query_and_reports_r7_p95() -> None:
    rows = [
        {"query_id": "q1", "latency_ms": "100", "request_status": "success"},
        {"query_id": "q1", "latency_ms": "100", "request_status": "success"},
        {"query_id": "q2", "latency_ms": "200", "request_status": "success"},
        {"query_id": "q3", "latency_ms": "999", "request_status": "error"},
        {"query_id": "q4", "latency_ms": "", "request_status": "success"},
    ]

    latencies = METRICS._latencies_by_query(rows)
    summary = METRICS._latency_summary(
        [{"latency_ms": latencies.get(query_id)} for query_id in ("q1", "q2", "q3", "q4")]
    )

    assert latencies == {"q1": 100.0, "q2": 200.0}
    assert summary["latency_sample_count"] == 2
    assert summary["latency_avg_ms"] == pytest.approx(150.0)
    assert summary["latency_p50_ms"] == pytest.approx(150.0)
    assert summary["latency_p95_ms"] == pytest.approx(195.0)
    assert summary["latency_p99_ms"] == pytest.approx(199.0)


def test_latency_is_missing_instead_of_zero_for_legacy_results() -> None:
    summary = METRICS._latency_summary([{"latency_ms": None}])

    assert summary["latency_sample_count"] == 0
    assert summary["latency_avg_ms"] is None
    assert summary["latency_p95_ms"] is None
