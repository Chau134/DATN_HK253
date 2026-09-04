from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "evaluator_audit", ROOT / "scripts" / "11_audit_evaluator.py"
)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_stratified_audit_selects_twenty_percent_across_categories() -> None:
    rows = [
        {"question_id": str(index), "category": f"category-{index % 4}"}
        for index in range(80)
    ]
    selected = audit.select_stratified(rows, 0.20, 252)
    assert len(selected) == 16
    assert {row["category"] for row in selected} == {
        "category-0", "category-1", "category-2", "category-3"
    }


def test_audit_summary_reports_agreement_false_positives_and_negatives() -> None:
    rows = [
        {
            "question_id": "1", "category": "factual",
            "rule_based_grounding_score": "0.9", "token_f1_relevancy": "0.8",
            "human_grounding_pass": "false", "human_relevancy_pass": "true",
        },
        {
            "question_id": "2", "category": "recommendation",
            "rule_based_grounding_score": "0.7", "token_f1_relevancy": "0.4",
            "human_grounding_pass": "true", "human_relevancy_pass": "false",
        },
    ]
    summary = audit.summarize_audit(
        rows, total_cases=10, ratio=0.20,
        grounding_threshold=0.85, relevancy_threshold=0.70,
    )
    grounding = summary["agreement"]["rule_based_grounding_score"]
    assert summary["audit_complete"]
    assert grounding["agreement"] == 0.0
    assert grounding["false_positive_question_ids"] == ["1"]
    assert grounding["false_negative_question_ids"] == ["2"]
