from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "13_compare_ablation.py"
spec = importlib.util.spec_from_file_location("hybrid_ablation", SCRIPT)
assert spec and spec.loader
ABLATION = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ABLATION)


def test_constraints_are_normalized_and_all_required() -> None:
    query = {
        "category": "Áo thun", "color": "Đỏ", "material": "cotton",
        "price_bucket": "under_200k", "usage": "Đi làm",
    }
    product = {
        "category": "ao thun", "color": "do", "material": "Cotton",
        "price": "199999", "usage": "di lam",
    }
    constraints = ABLATION.required_constraints(query)
    assert ABLATION.product_satisfies(product, constraints)
    assert not ABLATION.product_satisfies({**product, "color": "blue"}, constraints)


def test_blank_constraints_are_not_counted() -> None:
    assert ABLATION.required_constraints({
        "category": "shirt", "color": "", "material": " ",
        "price_bucket": "", "usage": "",
    }) == {"category": "shirt"}


def test_constraint_satisfaction_uses_returned_top_five_denominator() -> None:
    queries = [{
        "query_id": "q1", "difficulty": "easy", "transformation_type": "color",
        "target_product_id": "p1", "category": "shirt", "color": "red",
        "material": "", "price_bucket": "", "usage": "",
    }]
    products = [
        {"product_id": "p1", "category": "shirt", "color": "red", "price": "100"},
        {"product_id": "p2", "category": "shirt", "color": "blue", "price": "100"},
    ]
    ground_truth = [{
        "query_id": "q1", "relevant_product_id": "p1", "relevance_grade": "3",
        "review_status": "approved",
    }]
    results = [
        {"query_id": "q1", "rank": "1", "product_id": "p1"},
        {"query_id": "q1", "rank": "2", "product_id": "p2"},
    ]
    rows = ABLATION.build_per_query(
        queries, products, ground_truth, results,
        [{"query_id": "q1", "status_code": 200, "search_latency_ms": 10}],
    )
    assert rows[0]["constraint_satisfaction@5"] == pytest.approx(0.5)
    assert rows[0]["constraint_success@5"] == 1.0


def test_paired_bootstrap_identical_rows_has_zero_interval() -> None:
    left = [{"query_id": f"q{i}", **{metric: float(i % 2) for metric in ABLATION.BOOTSTRAP_METRICS}} for i in range(10)]
    output = ABLATION.paired_bootstrap(left, list(left), samples=200, seed=42)
    for value in output.values():
        assert value == {"delta": 0.0, "ci95_low": 0.0, "ci95_high": 0.0}


def test_validate_run_rejects_rerank_state_mismatch() -> None:
    responses = [{
        "query_id": "q1", "status_code": 200, "variant": "fusion",
        "reranker_enabled": False,
    }]
    with pytest.raises(ValueError, match="reranker state"):
        ABLATION.validate_run("fusion_rerank", ["q1"], [], responses)


def test_validate_run_accepts_image_post_filter_artifact() -> None:
    responses = [{
        "query_id": "q1", "status_code": 200, "variant": "image-post-filter",
        "reranker_enabled": False,
    }]
    assert ABLATION.validate_run("image_post_filter", ["q1"], [], responses) == {
        "rerank_score_rows": 0,
        "reranked_queries": 0,
    }
