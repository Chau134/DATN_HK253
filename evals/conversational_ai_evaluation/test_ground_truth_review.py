from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parent


def load_review_module():
    spec = importlib.util.spec_from_file_location(
        "ground_truth_review", ROOT / "scripts" / "09_ground_truth_review.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review = load_review_module()


def fixture_rows():
    products = [
        {
            "product_id": "42",
            "product_name_vi": "Áo đen",
            "product_name": "Black top",
            "category": "Top",
            "color": "Đen",
            "material": "Cotton",
            "gender": "Nữ",
            "version": "v1",
        }
    ]
    questions = [
        {
            "question_id": "q1",
            "session_id": "s1",
            "turn_index": "0",
            "category": "product_factual",
            "question": "Áo đen có màu gì?",
            "expected_answer_type": "attribute_color",
            "entity_ids": "42",
            "depends_on_history": "false",
            "difficulty": "easy",
            "manual_status": "pending",
            "notes": "attr=color",
        }
    ]
    references = [
        {
            "question_id": "q1",
            "reference_answer": "Áo có màu đen.",
            "answer_must_include": "đen",
            "answer_must_not_include": "bịa tồn kho",
            "reference_source_ids": "42",
            "review_status": "pending",
            "notes": "generated",
        }
    ]
    evidence = [
        {
            "question_id": "q1",
            "evidence_id": "q1-e1",
            "source_id": "42",
            "evidence_text": "color=Đen",
            "evidence_role": "primary",
            "required_level": "must_have",
            "notes": "attribute_color",
        }
    ]
    return questions, references, evidence, products


def test_build_review_rows_joins_question_reference_evidence_and_product() -> None:
    questions, references, evidence, products = fixture_rows()
    rows = review.build_review_rows(questions, references, evidence, products)

    assert len(rows) == 1
    assert rows[0]["question_status"] == "pending"
    assert rows[0]["evidence_status"] == "pending"
    assert '"product_id":"42"' in rows[0]["source_products_json"]
    assert review.validate_review_rows(rows, products, expected_question_ids={"q1"}) == []


def test_complete_review_requires_decisions_and_reviewer() -> None:
    questions, references, evidence, products = fixture_rows()
    rows = review.build_review_rows(questions, references, evidence, products)

    incomplete = review.validate_review_rows(rows, products, require_complete=True)
    assert any("review is not complete" in error for error in incomplete)

    rows[0].update(
        {
            "question_status": "approved",
            "reference_status": "approved",
            "evidence_status": "approved",
            "reviewer": "human-reviewer",
        }
    )
    assert review.validate_review_rows(rows, products, require_complete=True) == []


def test_review_validation_rejects_unknown_snapshot_ids() -> None:
    questions, references, evidence, products = fixture_rows()
    rows = review.build_review_rows(questions, references, evidence, products)
    rows[0]["reference_source_ids"] = "999"

    errors = review.validate_review_rows(rows, products)

    assert any("absent from snapshot" in error and "999" in error for error in errors)


def test_apply_review_writes_human_decisions_and_metadata(tmp_path: Path) -> None:
    questions, references, evidence, products = fixture_rows()
    rows = review.build_review_rows(questions, references, evidence, products)
    rows[0].update(
        {
            "question_status": "approved",
            "reference_status": "approved",
            "evidence_status": "approved",
            "reviewer": "human-reviewer",
            "review_notes": "verified against snapshot",
        }
    )
    paths = {
        "questions": tmp_path / "questions.csv",
        "references": tmp_path / "references.csv",
        "evidence": tmp_path / "evidence.csv",
        "products": tmp_path / "products.csv",
        "review_csv": tmp_path / "review.csv",
        "review_markdown": tmp_path / "review.md",
        "review_summary": tmp_path / "summary.json",
    }
    review.write_csv_rows(paths["questions"], questions, list(questions[0]))
    review.write_csv_rows(paths["references"], references, list(references[0]))
    review.write_csv_rows(paths["evidence"], evidence, list(evidence[0]))
    review.write_csv_rows(paths["products"], products, list(products[0]))
    review.write_csv_rows(paths["review_csv"], rows, review.REVIEW_FIELDS)

    assert review.apply_review(SimpleNamespace(**paths)) == 0

    applied_question = review.read_csv_rows(paths["questions"])[0]
    applied_reference = review.read_csv_rows(paths["references"])[0]
    applied_evidence = review.read_csv_rows(paths["evidence"])[0]
    assert applied_question["manual_status"] == "approved"
    assert applied_reference["review_status"] == "approved"
    assert applied_evidence["review_status"] == "approved"
    assert applied_question["reviewer"] == "human-reviewer"
    assert applied_question["reviewed_at"]


def test_current_ground_truth_sources_are_structurally_valid() -> None:
    questions = review.read_csv_rows(ROOT / "data" / "question_set.csv")
    references = review.read_csv_rows(ROOT / "data" / "reference_answers.csv")
    evidence = review.read_csv_rows(ROOT / "data" / "required_evidence.csv")
    products = review.read_csv_rows(ROOT / "data" / "product_snapshot.csv")
    rows = review.build_review_rows(questions, references, evidence, products)

    assert len(rows) == 80
    assert review.validate_review_rows(
        rows,
        products,
        expected_question_ids={row["question_id"] for row in questions},
    ) == []
