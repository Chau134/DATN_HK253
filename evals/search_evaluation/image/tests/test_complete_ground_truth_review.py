from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "11_complete_ground_truth_review.py"
SPEC = importlib.util.spec_from_file_location("complete_image_ground_truth", SCRIPT_PATH)
assert SPEC and SPEC.loader
COMPLETE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPLETE)


QUERY = {
    "query_id": "q1",
    "source_product_id": "p1",
    "category": "Áo thun",
    "color": "Xanh dương",
    "material": "100% Cotton",
}


def review_row(rank: int, product_id: str, *, grade: str = "", name: str = "Áo thun màu đen cotton") -> dict[str, str]:
    return {
        "query_id": "q1",
        "query_product_name": "Áo thun màu xanh dương cotton hai lớp",
        "query_category": "Áo thun",
        "candidate_rank": str(rank),
        "candidate_product_id": product_id,
        "candidate_product_name": name,
        "candidate_category": "Áo thun",
        "candidate_color": "Đen",
        "candidate_material": "100% Cotton",
        "relevance_grade": grade,
        "review_status": "pending",
    }


def test_completion_preserves_explicit_top5_human_grade_and_auto_labels_tail() -> None:
    rows = COMPLETE.complete_review_rows(
        [review_row(1, "p1", grade="3"), review_row(6, "p2", name="Áo thun màu đen cotton hai lớp")],
        [QUERY],
        {},
        human_top_k=5,
    )

    assert rows[0]["relevance_grade"] == 3
    assert rows[0]["reviewer_notes"] == "human_top5_review"
    assert rows[1]["relevance_grade"] == 2
    assert rows[1]["reviewer_notes"].startswith("metadata_rule_v1:")
    assert all(row["review_status"] == "approved" for row in rows)


def test_completion_requires_every_top5_row_to_have_human_grade_or_override() -> None:
    with pytest.raises(ValueError, match="requires a human grade"):
        COMPLETE.complete_review_rows([review_row(2, "p2")], [QUERY], {}, human_top_k=5)


def test_override_wins_and_is_recorded_as_human_audit() -> None:
    rows = COMPLETE.complete_review_rows(
        [review_row(2, "p2", grade="3")],
        [QUERY],
        {("q1", "p2"): (2, "different_sku")},
        human_top_k=5,
    )

    assert rows[0]["relevance_grade"] == 2
    assert rows[0]["reviewer_notes"] == "human_top5_audit_override:different_sku"


def test_auto_rule_keeps_different_categories_irrelevant() -> None:
    row = review_row(7, "p2")
    row["candidate_category"] = "Quần dài"
    row["candidate_product_name"] = "Quần dài màu xanh dương cotton"

    grade, reason = COMPLETE.auto_grade(QUERY, row)

    assert grade == 0
    assert reason == "different_category_or_insufficient_visual_metadata"


def test_auto_rule_never_promotes_same_metadata_to_exact_sku() -> None:
    row = review_row(7, "p2", name="Áo thun màu xanh dương cotton hai lớp")
    row["candidate_color"] = "Xanh dương"

    grade, reason = COMPLETE.auto_grade(QUERY, row)

    assert grade == 2
    assert reason == "identical_metadata_signature_but_unverified_sku"
