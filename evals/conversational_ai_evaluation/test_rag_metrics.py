from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


metrics = load_script("rag_metrics", "08_compute_rag_metrics.py")
runner = load_script("rag_runner", "07_run_rag_eval.py")
common = load_script("rag_common_for_metrics", "common.py")


def test_token_f1_and_normalization_support_vietnamese() -> None:
    assert metrics.normalize("Áo màu Đen") == "ao mau den"
    assert metrics.token_f1("áo màu đen", "áo màu đen") == 1.0


def test_ground_truth_color_matching_uses_runtime_color_families() -> None:
    assert common.colors_match_runtime_semantics("Nâu sọc", "Nâu")
    assert common.colors_match_runtime_semantics("Hồng / Trắng", "Trắng")
    assert common.colors_match_runtime_semantics("Vàng ánh kim", "Vàng")
    assert not common.colors_match_runtime_semantics("Nâu chocolate", "Vàng")


def test_context_ids_use_context_then_fallback() -> None:
    assert metrics.context_ids([{"product_id": 42}], ["7"]) == {"42"}
    assert metrics.context_ids([], ["7"]) == {"7"}


def test_response_product_ids_supports_api_contract() -> None:
    response = {"product_ids": [{"product_id": "42"}, {"id": 7}, "9"]}
    assert runner.response_product_ids(response) == ["42", "7", "9"]


def test_evaluation_trace_schema_requires_redacted_ids_and_full_context_fields() -> None:
    trace = {
        "schema_version": "1.0",
        "request_id_hash": "a" * 16,
        "session_id_hash": "b" * 16,
        "route": "text_search",
        "rule_filters": {},
        "llm_filters": {},
        "effective_filters": {},
        "retrieved_candidates": [
            {"product_id": "42", "score": 0.9, "rank": 1, "source": "text"}
        ],
        "retrieved_context": [{"product_id": "42", "title": "Example"}],
        "referenced_product_ids": [],
        "reference_resolution_source": "none",
        "memory_sources": ["none"],
        "warnings": [],
        "fallback_reasons": [],
        "stage_latencies_ms": {"text_search": 2.5},
    }

    assert runner.evaluation_trace_is_valid(trace)
    assert runner.trace_product_ids(trace) == ["42"]
    trace["session_id_hash"] = "raw-session"
    assert not runner.evaluation_trace_is_valid(trace)


def test_average_present_keeps_proxy_metrics_separate() -> None:
    rows = [{"metric": None}, {"metric": 0.5}, {"metric": 1.0}]
    assert metrics.average_present(rows, "metric") == 0.75


def test_grounding_claim_checks_use_available_structured_context() -> None:
    context = [{"id": 1, "total_stock": 2, "price": {"discounted_price": 100}}]

    assert metrics.forbidden_claims_absent("Sản phẩm còn hàng và có giảm giá.", context)
    assert not metrics.forbidden_claims_absent("Sản phẩm còn hàng.", [])
    assert metrics.forbidden_claims_absent(
        "Hàng giảm trên 30% chỉ được đổi size nếu còn hàng.", []
    )
    assert not metrics.forbidden_claims_absent("Dữ liệu lấy từ vector API.", context)


def test_reference_forbidden_claims_reject_catalog_hallucinations() -> None:
    reference = {
        "answer_must_not_include": "ví da | túi xách | balo | giày dép"
    }

    assert metrics.reference_forbidden_claims_absent(
        "Shop hiện có váy, áo thun và quần dài.", reference
    )
    assert not metrics.reference_forbidden_claims_absent(
        "Shop hiện có ví da, túi xách và balo.", reference
    )


def test_unanswerable_is_scored_by_refusal_behavior_not_reference_wording() -> None:
    assert metrics.refusal_behavior_is_valid(
        "Mình không có thông tin đã kiểm chứng về chính sách này.", set()
    )
    assert not metrics.refusal_behavior_is_valid(
        "Shop giao hàng trong 25 ngày.", set()
    )
    assert not metrics.refusal_behavior_is_valid(
        "Mình chưa có thông tin.", {"1"}
    )


def test_ordinal_expected_source_is_derived_from_previous_turn_order() -> None:
    questions = {
        "q0": {"question_id": "q0", "session_id": "s", "turn_index": "0"},
        "q1": {
            "question_id": "q1",
            "session_id": "s",
            "turn_index": "1",
            "notes": "ordinal_index=2",
        },
    }
    responses = {"q0": {"retrieved_product_ids": "10|20|30"}}

    assert metrics.ordinal_expected_source_ids(questions["q1"], questions, responses) == {"20"}


def test_recommendation_reference_uses_all_products_matching_approved_criteria() -> None:
    def product(product_id: str, color: str):
        return common.ConvProductRecord(
            product_id=product_id,
            product_name=f"Product {product_id}",
            product_name_vi="",
            category="hoodie",
            brand="brand",
            color=color,
            material="cotton",
            gender="unisex",
            is_active=True,
            description="",
            version="v1",
        )

    products = {item.product_id: item for item in (
        product("1", "black"), product("2", "black"), product("3", "white")
    )}
    reference, evidence = common.build_reference_and_evidence(
        {
            "question_id": "rec-1",
            "expected_answer_type": "recommendation",
            "entity_ids": "1",
            "notes": "criteria_based_reference",
        },
        products,
    )

    assert reference.reference_source_ids == "1;2"
    assert any(item.notes == "recommendation_valid_source_set" for item in evidence)


def test_initial_search_reference_also_accepts_all_products_matching_criteria() -> None:
    def product(product_id: str, color: str):
        return common.ConvProductRecord(
            product_id=product_id,
            product_name=f"Product {product_id}",
            product_name_vi="",
            category="hoodie",
            brand="brand",
            color=color,
            material="cotton",
            gender="unisex",
            is_active=True,
            description="",
            version="v1",
        )

    products = {item.product_id: item for item in (
        product("1", "black"), product("2", "black"), product("3", "white")
    )}
    reference, evidence = common.build_reference_and_evidence(
        {
            "question_id": "initial-1",
            "expected_answer_type": "search_initial",
            "entity_ids": "1",
            "notes": "initial_search_turn",
        },
        products,
    )

    assert reference.reference_source_ids == "1;2"
    assert any(item.notes == "initial_search_valid_source_set" for item in evidence)


def test_review_metadata_is_preserved_only_for_identical_generated_content() -> None:
    generated = {
        "question_id": "q1",
        "reference_source_ids": "1;2",
        "review_status": "pending",
        "reviewer": "",
        "reviewed_at": "",
        "review_notes": "",
    }
    existing = {
        **generated,
        "review_status": "approved",
        "reviewer": "human",
        "reviewed_at": "2026-08-23T00:00:00Z",
        "review_notes": "checked",
    }

    unchanged = common.preserve_review_metadata_if_unchanged(
        dict(generated), existing, content_fields=("question_id", "reference_source_ids")
    )
    changed = common.preserve_review_metadata_if_unchanged(
        {**generated, "reference_source_ids": "3"},
        existing,
        content_fields=("question_id", "reference_source_ids"),
    )

    assert unchanged["review_status"] == "approved"
    assert unchanged["reviewer"] == "human"
    assert changed["review_status"] == "pending"
    assert changed["reviewer"] == ""
