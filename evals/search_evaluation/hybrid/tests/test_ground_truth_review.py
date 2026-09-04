from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = load("build_hybrid_review", "09_build_ground_truth_review.py")
FINALIZE = load("finalize_hybrid_review", "10_finalize_ground_truth_review.py")


QUERIES = [{
    "query_id": "q1", "difficulty": "hard", "transformation_type": "color",
    "source_product_id": "p1", "target_product_id": "p1", "source_image_query_id": "image-q1",
    "source_image_url": "source.jpg", "image_url": "edited.jpg", "image_edit_request": "change red to blue",
}]


def approved_reference() -> dict[str, str]:
    return {
        "query_id": "q1", "image_edit_request": "change red to blue",
        "identity_preserved": "yes", "requested_change_present": "yes",
        "unintended_change_absent": "yes", "review_status": "approved", "reviewer_notes": "visual review",
    }


def test_reference_review_requires_visual_checks() -> None:
    row = approved_reference()
    row["identity_preserved"] = "no"
    with pytest.raises(ValueError, match="identity"):
        FINALIZE.validate_references([row], QUERIES)


def test_candidate_review_rejects_pending_rows() -> None:
    references = FINALIZE.validate_references([approved_reference()], QUERIES)
    with pytest.raises(ValueError, match="unresolved"):
        FINALIZE.finalize_candidates([
            {"query_id": "q1", "candidate_product_id": "p1", "review_status": "pending", "relevance_grade": "3"}
        ], QUERIES, references)


def test_target_requires_grade_three() -> None:
    references = FINALIZE.validate_references([approved_reference()], QUERIES)
    with pytest.raises(ValueError, match="grade 3"):
        FINALIZE.finalize_candidates([
            {"query_id": "q1", "candidate_product_id": "p1", "review_status": "approved", "relevance_grade": "2"}
        ], QUERIES, references)


def test_prior_approved_visual_grade_is_reused() -> None:
    products = [{"product_id": "p1", "product_name": "target"}, {"product_id": "p2", "product_name": "candidate"}]
    rows = BUILD.build_candidate_rows(
        [{**QUERIES[0], "query_text": "find blue", "image_url": "edited.jpg"}],
        [{"query_id": "q1", "relevant_product_id": "p2", "relevance_grade": "2"}],
        products,
        [{"query_id": "image-q1", "relevant_product_id": "p2", "relevance_grade": "1", "review_status": "approved", "source": "human"}],
        [],
    )
    assert rows[0]["review_status"] == "approved"
    assert rows[0]["relevance_grade"] == "1"
    assert rows[0]["reviewer_notes"].startswith("reused_image_ground_truth:")
