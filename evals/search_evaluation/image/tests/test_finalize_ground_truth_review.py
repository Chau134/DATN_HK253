from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "10_finalize_ground_truth_review.py"
SPEC = importlib.util.spec_from_file_location("finalize_image_ground_truth", SCRIPT_PATH)
assert SPEC and SPEC.loader
FINALIZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FINALIZE)


QUERIES = [{"query_id": "q1", "source_product_id": "p1", "source_image_id": "image-1"}]


def test_finalize_requires_every_review_row_to_be_resolved() -> None:
    with pytest.raises(ValueError, match="still pending"):
        FINALIZE.finalize_rows(
            [
                {
                    "query_id": "q1",
                    "candidate_product_id": "p1",
                    "relevance_grade": "3",
                    "review_status": "pending",
                }
            ],
            QUERIES,
        )


def test_finalize_requires_exact_source_product_at_grade_three() -> None:
    with pytest.raises(ValueError, match="source product must be approved with grade 3"):
        FINALIZE.finalize_rows(
            [
                {
                    "query_id": "q1",
                    "candidate_product_id": "p1",
                    "relevance_grade": "2",
                    "review_status": "approved",
                }
            ],
            QUERIES,
        )


def test_finalize_converts_rejected_candidates_to_judged_grade_zero() -> None:
    rows = FINALIZE.finalize_rows(
        [
            {
                "query_id": "q1",
                "candidate_product_id": "p1",
                "relevance_grade": "3",
                "review_status": "approved",
            },
            {
                "query_id": "q1",
                "candidate_product_id": "p2",
                "relevance_grade": "",
                "review_status": "rejected",
                "reviewer_notes": "not visually similar",
            },
        ],
        QUERIES,
    )

    assert [row["relevance_grade"] for row in rows] == [3, 0]
    assert rows[0]["source"] == "query_source_mapping"
    assert rows[1]["source"] == "human_visual_review_top5"
    assert rows[1]["notes"] == "not visually similar"


def test_finalize_preserves_auto_rule_provenance() -> None:
    rows = FINALIZE.finalize_rows(
        [
            {
                "query_id": "q1",
                "candidate_product_id": "p1",
                "relevance_grade": "3",
                "review_status": "approved",
                "reviewer_notes": "metadata_rule_v1:source_product_exact_match",
            },
            {
                "query_id": "q1",
                "candidate_product_id": "p2",
                "relevance_grade": "1",
                "review_status": "approved",
                "reviewer_notes": "metadata_rule_v1:same_category_weak_similarity=0.20",
            },
        ],
        QUERIES,
    )

    assert rows[0]["source"] == "query_source_mapping"
    assert rows[1]["source"] == "metadata_rule_v1"
    assert rows[1]["match_reason"] == "same_category_weak_similarity=0.20"
