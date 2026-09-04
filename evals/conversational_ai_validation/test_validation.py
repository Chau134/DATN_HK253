from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("validation_common", ROOT / "scripts" / "common.py")
assert SPEC and SPEC.loader
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
sys.modules["common"] = common

CRITICAL_SPEC = importlib.util.spec_from_file_location(
    "critical_gates", ROOT / "scripts" / "05_score_critical_gates.py"
)
assert CRITICAL_SPEC and CRITICAL_SPEC.loader
critical = importlib.util.module_from_spec(CRITICAL_SPEC)
CRITICAL_SPEC.loader.exec_module(critical)

MASTER_SPEC = importlib.util.spec_from_file_location(
    "master_suite", ROOT / "scripts" / "08_build_master_suite.py"
)
assert MASTER_SPEC and MASTER_SPEC.loader
master_suite = importlib.util.module_from_spec(MASTER_SPEC)
MASTER_SPEC.loader.exec_module(master_suite)


def test_stratified_sample_is_deterministic_and_covers_strata() -> None:
    rows = [
        {
            "question_id": str(index),
            "category": f"category-{index % 4}",
            "difficulty": "hard" if index % 3 == 0 else "easy",
        }
        for index in range(80)
    ]
    first = common.select_stratified(rows, 40, 252)
    second = common.select_stratified(rows, 40, 252)
    assert [row["question_id"] for row in first] == [row["question_id"] for row in second]
    assert len(first) == 40
    assert {
        (row["category"], row["difficulty"]) for row in first
    } == {
        (row["category"], row["difficulty"]) for row in rows
    }


def test_case_requires_all_applicable_scores_and_hard_gates() -> None:
    row = {field: "4" for field in common.RATING_FIELDS}
    row.update({field: "NA" for field in common.HARD_GATE_FIELDS})
    row["critical_product_exists"] = "pass"
    result = common.evaluate_review_row(row)
    assert result["complete"]
    assert result["accepted"]

    row["helpfulness"] = "3"
    result = common.evaluate_review_row(row)
    assert not result["accepted"]
    assert result["failed_dimensions"] == ["helpfulness"]

    row["helpfulness"] = "5"
    row["critical_product_exists"] = "fail"
    result = common.evaluate_review_row(row)
    assert not result["accepted"]
    assert result["failed_hard_gates"] == ["critical_product_exists"]


def test_incomplete_applicable_field_is_not_scored_as_failure() -> None:
    row = {field: "4" for field in common.RATING_FIELDS}
    row.update({field: "NA" for field in common.HARD_GATE_FIELDS})
    row["groundedness"] = ""
    result = common.evaluate_review_row(row)
    assert not result["complete"]
    assert result["accepted"] is None
    assert result["missing_fields"] == ["groundedness"]


def test_threshold_calibration_prefers_separating_threshold() -> None:
    best, rows = common.calibrate_threshold(
        [0.20, 0.40, 0.80, 0.90],
        [False, False, True, True],
    )
    assert rows
    assert best is not None
    assert best["threshold"] == 0.80
    assert best["balanced_accuracy"] == 1.0


def test_cohen_kappa_perfect_agreement() -> None:
    assert common.cohen_kappa([True, False, True], [True, False, True]) == 1.0


def test_money_parser_supports_vnd_and_compact_vietnamese_units() -> None:
    assert critical.money_values("Giá 579.000 VND, giá gốc 599k") == [579000, 599000]


def test_price_hard_gate_uses_runtime_context_not_static_expected_price() -> None:
    case = {
        "question_id": "price-1",
        "category": "critical_price",
        "question": "Giá bao nhiêu?",
        "expected_behavior": "price_from_context",
        "source_product_id": "1035",
        "expected_size": "",
    }
    response = {
        "answer": "Giá hiện tại là 579.000 VND.",
        "http_status": "200",
        "context_mode": "full_context",
        "retrieved_context_json": json.dumps([{
            "id": 1035,
            "price": {"price": 599000, "discounted_price": 579000, "effective_price": 579000},
        }]),
    }
    assert critical.score_case(case, response)["automatic_pass"] == "true"


def test_policy_hard_gate_accepts_grounded_correction_without_fake_commitment() -> None:
    case = {
        "question_id": "policy-1",
        "category": "critical_policy",
        "question": "Shop có cam kết bảo hành trọn đời cho mọi sản phẩm không?",
        "expected_behavior": "refuse_unsupported_policy",
        "source_product_id": "",
        "expected_size": "",
    }
    response = {
        "answer": "Chính sách hiện tại bảo hành quần áo 30 ngày và giày dép 60 ngày.",
        "retrieved_product_ids": "",
        "http_status": "200",
        "context_mode": "full_context",
        "retrieved_context_json": "[]",
    }

    assert critical.score_case(case, response)["automatic_pass"] == "true"


def test_missing_product_gate_allows_labeled_suggestions_after_refusal() -> None:
    case = {
        "question_id": "missing-1",
        "category": "critical_product",
        "question": "Shop c\u00f3 s\u1ea3n ph\u1ea9m Sao H\u1ecfa kh\u00f4ng?",
        "expected_behavior": "refuse_missing_product",
        "source_product_id": "",
        "expected_size": "",
    }
    response = {
        "answer": (
            "Kh\u00f4ng, shop kh\u00f4ng t\u00ecm th\u1ea5y Sao H\u1ecfa trong danh m\u1ee5c hi\u1ec7n t\u1ea1i. "
            "B\u1ea1n c\u00f3 th\u1ec3 tham kh\u1ea3o c\u00e1c s\u1ea3n ph\u1ea9m t\u01b0\u01a1ng t\u1ef1: "
            "\u00c1o kho\u00e1c m\u00e0u n\u00e2u."
        ),
        "retrieved_product_ids": "10",
        "http_status": "200",
        "context_mode": "full_context",
        "retrieved_context_json": "[]",
    }

    assert critical.score_case(case, response)["automatic_pass"] == "true"


def test_missing_product_gate_rejects_unlabeled_nearest_neighbor() -> None:
    case = {
        "question_id": "missing-2",
        "category": "critical_product",
        "question": "Shop c\u00f3 s\u1ea3n ph\u1ea9m Sao H\u1ecfa kh\u00f4ng?",
        "expected_behavior": "refuse_missing_product",
        "source_product_id": "",
        "expected_size": "",
    }
    response = {
        "answer": "Shop c\u00f3 \u00c1o kho\u00e1c m\u00e0u n\u00e2u.",
        "retrieved_product_ids": "10",
        "http_status": "200",
        "context_mode": "full_context",
        "retrieved_context_json": "[]",
    }

    assert critical.score_case(case, response)["automatic_pass"] == "false"


def test_master_suite_selection_is_deterministic_and_keeps_multiturn_sessions() -> None:
    rows = master_suite.read_csv(
        ROOT.parent / "conversational_ai_evaluation" / "data" / "question_set.csv"
    )

    first, first_dropped = master_suite.select_legacy_questions(rows, 252)
    second, second_dropped = master_suite.select_legacy_questions(rows, 252)

    assert [row["question_id"] for row in first] == [row["question_id"] for row in second]
    assert [row["question_id"] for row in first_dropped] == [
        row["question_id"] for row in second_dropped
    ]
    assert len(first) == 68
    assert len(first_dropped) == 12
    selected_ids = {row["question_id"] for row in first}
    assert all(
        row["question_id"] in selected_ids
        for row in rows
        if row["category"] in {"followup_ordinal", "filter_refinement"}
    )


def test_generated_master_suite_contains_80_cases_and_all_critical_cases() -> None:
    data_dir = ROOT / "data" / "master_80"
    questions = master_suite.read_csv(data_dir / "question_set.csv")
    critical_cases = master_suite.read_csv(ROOT / "data" / "critical_cases.csv")

    question_ids = {row["question_id"] for row in questions}
    assert len(questions) == 80
    assert len(question_ids) == 80
    assert {row["question_id"] for row in critical_cases}.issubset(question_ids)


def test_critical_categories_receive_their_required_human_hard_gates() -> None:
    price = common.default_applicability({"category": "critical_price", "question": "price"})
    missing = common.default_applicability({"category": "critical_product", "question": "missing"})
    policy = common.default_applicability({"category": "critical_policy", "question": "policy"})

    assert price["critical_price"] == ""
    assert price["critical_product_exists"] == ""
    assert missing["critical_product_exists"] == ""
    assert missing["refusal_correctness"] == ""
    assert missing["critical_clarification_or_refusal"] == ""
    assert policy["critical_policy"] == ""
    assert policy["refusal_correctness"] == ""
    assert policy["critical_product_exists"] == "NA"
