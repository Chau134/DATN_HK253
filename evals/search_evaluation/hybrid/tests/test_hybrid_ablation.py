from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "13_compare_ablation.py"
spec = importlib.util.spec_from_file_location("hybrid_ablation", SCRIPT)
assert spec and spec.loader
ABLATION = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ABLATION)


def test_only_user_requested_fields_are_scored() -> None:
    query = {
        "query_id": "q", "query_text": "tìm áo giống ảnh nhưng đổi sang màu đỏ",
        "transformation_type": "color",
        "category": "Áo thun", "color": "Đỏ", "material": "cotton",
        "price_bucket": "under_200k", "usage": "Đi làm",
    }
    product = {
        "category": "ao thun", "color": "do", "material": "Cotton",
        "price": "199999", "usage": "di lam",
    }
    constraints = ABLATION.required_constraints(query)
    assert set(constraints) == {"color"}
    assert ABLATION.product_satisfies(product, query)
    assert ABLATION.product_satisfies({**product, "category": "quần", "material": "silk", "usage": "du lịch", "price": "9000000"}, query)
    assert not ABLATION.product_satisfies({**product, "color": "blue"}, query)


def test_query_without_requested_attribute_is_rejected() -> None:
    with pytest.raises(ValueError, match="no requested attribute"):
        ABLATION.required_constraints({"query_id": "q", "query_text": "tìm áo giống ảnh", "transformation_type": ""})


def test_declared_fixture_scope_must_match_query_text() -> None:
    with pytest.raises(ValueError, match="differs from declared transformation"):
        ABLATION.required_constraints({"query_id": "q", "query_text": "giống ảnh màu đỏ", "transformation_type": "color_material"})


def test_requested_color_material_and_price_are_all_required_but_usage_is_not_hidden() -> None:
    query = {"query_id": "q", "query_text": "giống ảnh màu đỏ chất liệu cotton giá dưới 500k",
             "transformation_type": "color_material_price"}
    good = {"product_id": "p", "color": "Đỏ / Trắng", "material": "80% Cotton, 20% Polyester",
            "price": "499000", "usage": "đi làm"}
    assert ABLATION.product_satisfies(good, query)
    assert not ABLATION.product_satisfies({**good, "material": "polyester"}, query)
    assert not ABLATION.product_satisfies({**good, "price": "500000"}, query)
    assert not ABLATION.product_satisfies({**good, "color": "blue"}, query)


def test_usage_list_matches_one_named_occasion() -> None:
    query = {"query_id": "q", "query_text": "giống ảnh phù hợp đi chơi, dạo phố, du lịch", "transformation_type": "usage"}
    assert ABLATION.product_satisfies({"product_id": "p", "usage": "dạo phố, đi làm", "price": "1"}, query)
    assert not ABLATION.product_satisfies({"product_id": "p", "usage": "đi làm", "price": "1"}, query)


def test_canonical_constraint_snapshot_avoids_translation_false_negative() -> None:
    query = {"query_id": "q", "query_text": "giống ảnh màu trắng", "transformation_type": "color"}
    product = {"product_id": "p", "color": "Trắng ngà", "base_colour": "Oyster-white",
               "base_colour_vi": "Trắng ngà", "color_keys_json": '["white"]', "price": "1"}
    assert ABLATION.product_satisfies(product, query)


def test_invalid_canonical_snapshot_field_fails_closed() -> None:
    query = {"query_id": "q", "query_text": "giống ảnh màu trắng", "transformation_type": "color"}
    with pytest.raises(ValueError, match="Invalid canonical snapshot"):
        ABLATION.product_satisfies({"product_id": "p", "color_keys_json": "not-json", "price": "1"}, query)


def test_legacy_exact_contract_is_retained_separately() -> None:
    query = {"category": "shirt", "color": "red", "material": "cotton", "price_bucket": "under_200k", "usage": "office"}
    constraints = ABLATION.legacy_exact_required_constraints(query)
    assert set(constraints) == {"category", "color", "material", "price_bucket", "usage"}
    assert ABLATION.legacy_exact_product_satisfies(
        {"category": "shirt", "color": "red", "material": "cotton", "price": "100", "usage": "office"}, constraints)


def test_all_frozen_queries_have_scope_derived_from_user_text() -> None:
    queries = ABLATION.read_csv(Path(__file__).resolve().parents[1] / "data/multimodal_queries.csv")
    assert len(queries) == 100
    for query in queries:
        declared = set(query["transformation_type"].split("_"))
        assert set(ABLATION.required_constraints(query)) == declared


def test_constraint_satisfaction_uses_returned_top_five_denominator() -> None:
    queries = [{
        "query_id": "q1", "difficulty": "easy", "transformation_type": "color",
        "query_text": "tìm áo giống ảnh nhưng đổi sang màu đỏ",
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
    assert rows[0]["requested_constraint_fields"] == ["color"]
    assert rows[0]["legacy_exact_constraint_satisfaction@5"] == pytest.approx(0.5)


def test_request_conditioned_ndcg_keeps_grades_but_zeroes_wrong_constraint_gain() -> None:
    query = {
        "query_id": "q1", "difficulty": "easy", "transformation_type": "color",
        "query_text": "giống ảnh nhưng đổi sang màu đỏ", "target_product_id": "right",
        "category": "shirt", "color": "red", "material": "", "price_bucket": "", "usage": "",
    }
    rows = ABLATION.build_per_query(
        [query],
        [{"product_id": "wrong", "color": "blue", "price": "1"},
         {"product_id": "right", "color": "red", "price": "1"}],
        [{"query_id": "q1", "relevant_product_id": "wrong", "relevance_grade": "3", "review_status": "approved"},
         {"query_id": "q1", "relevant_product_id": "right", "relevance_grade": "2", "review_status": "approved"}],
        [{"query_id": "q1", "rank": "1", "product_id": "wrong"},
         {"query_id": "q1", "rank": "2", "product_id": "right"}],
        [{"query_id": "q1", "status_code": 200, "search_latency_ms": 1}],
    )
    assert rows[0]["graded_ndcg@5"] == pytest.approx(1.0)
    assert rows[0]["request_conditioned_ndcg@5"] == pytest.approx(1 / 1.584962500721156)


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
        ABLATION.validate_run("image_conditioned_rerank", ["q1"], [], responses)


def test_validate_run_accepts_image_conditioned_artifact() -> None:
    responses = [{
        "query_id": "q1", "status_code": 200, "variant": "fusion",
        "reranker_enabled": False,
        "effective_features": {"hybrid_image_conditioned_enabled": True},
    }]
    assert ABLATION.validate_run("image_conditioned_no_rerank", ["q1"], [], responses) == {
        "rerank_score_rows": 0,
        "reranked_queries": 0,
    }
