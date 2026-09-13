from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable


SUITE_DIR = Path(__file__).resolve().parent.parent
REVIEW_CSV = SUITE_DIR / "review" / "master_80" / "ground_truth_review.csv"
DATA_DIR = SUITE_DIR / "data"
MASTER_DIR = DATA_DIR / "master_80"
APPROVAL_SUMMARY = (
    SUITE_DIR / "review" / "master_80" / "ground_truth_approval_summary.json"
)

QUESTION_FIELDS = (
    "question_id",
    "session_id",
    "turn_index",
    "category",
    "question",
    "expected_answer_type",
    "entity_ids",
    "depends_on_history",
    "difficulty",
    "manual_status",
    "notes",
    "reviewer",
    "reviewed_at",
    "review_notes",
)
REFERENCE_FIELDS = (
    "question_id",
    "reference_answer",
    "answer_must_include",
    "answer_must_not_include",
    "reference_source_ids",
    "review_status",
    "notes",
    "reviewer",
    "reviewed_at",
    "review_notes",
)
EVIDENCE_FIELDS = (
    "question_id",
    "evidence_id",
    "source_id",
    "evidence_text",
    "evidence_role",
    "required_level",
    "notes",
    "review_status",
    "reviewer",
    "reviewed_at",
    "review_notes",
)
CRITICAL_FIELDS = (*QUESTION_FIELDS, "expected_behavior", "source_product_id", "expected_size")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, str]], fields: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def question_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "question_id": row["question_id"],
        "session_id": row["session_id"],
        "turn_index": row["turn_index"],
        "category": row["category"],
        "question": row["question"],
        "expected_answer_type": row["expected_answer_type"],
        "entity_ids": row["entity_ids"],
        "depends_on_history": row["depends_on_history"],
        "difficulty": row["difficulty"],
        "manual_status": row["question_status"],
        "notes": row["question_notes"],
        "reviewer": row["reviewer"],
        "reviewed_at": "",
        "review_notes": row["review_notes"],
    }


def reference_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "question_id": row["question_id"],
        "reference_answer": row["reference_answer"],
        "answer_must_include": row["answer_must_include"],
        "answer_must_not_include": row["answer_must_not_include"],
        "reference_source_ids": row["reference_source_ids"],
        "review_status": row["reference_status"],
        "notes": row["reference_notes"],
        "reviewer": row["reviewer"],
        "reviewed_at": "",
        "review_notes": row["review_notes"],
    }


def evidence_rows(row: dict[str, str]) -> list[dict[str, str]]:
    values = json.loads(row["evidence_json"])
    if not isinstance(values, list):
        raise ValueError(f"evidence_json is not a list for {row['question_id']}")
    return [
        {
            "question_id": row["question_id"],
            "evidence_id": str(value.get("evidence_id", "")),
            "source_id": str(value.get("source_id", "")),
            "evidence_text": str(value.get("evidence_text", "")),
            "evidence_role": str(value.get("evidence_role", "")),
            "required_level": str(value.get("required_level", "")),
            "notes": str(value.get("notes", "")),
            "review_status": row["evidence_status"],
            "reviewer": row["reviewer"],
            "reviewed_at": "",
            "review_notes": row["review_notes"],
        }
        for value in values
    ]


def critical_row(row: dict[str, str], evidence: dict[str, str]) -> dict[str, str]:
    notes = evidence["notes"]
    prefix = "critical_behavior="
    if not notes.startswith(prefix):
        raise ValueError(f"Missing critical behavior for {row['question_id']}")
    size_match = re.search(r"(?:^|;)\s*size=([^;]+)", evidence["evidence_text"])
    return question_row(row) | {
        "expected_behavior": notes.removeprefix(prefix),
        "source_product_id": evidence["source_id"],
        "expected_size": size_match.group(1).strip() if size_match else "",
    }


def main() -> int:
    rows = read_csv(REVIEW_CSV)
    question_ids = [row["question_id"] for row in rows]
    if len(rows) != 80 or len(set(question_ids)) != 80:
        raise ValueError("Approved review must contain exactly 80 unique questions")

    for row in rows:
        statuses = (
            row["question_status"],
            row["reference_status"],
            row["evidence_status"],
        )
        if statuses != ("approved", "approved", "approved"):
            raise ValueError(f"Unapproved ground truth for {row['question_id']}: {statuses}")

    questions = [question_row(row) for row in rows]
    references = [reference_row(row) for row in rows]
    evidence_by_question = {row["question_id"]: evidence_rows(row) for row in rows}
    evidence = [item for values in evidence_by_question.values() for item in values]
    critical = [
        critical_row(row, evidence_by_question[row["question_id"]][0])
        for row in rows
        if row["category"].startswith("critical_")
    ]
    if any(not values for values in evidence_by_question.values()):
        raise ValueError("Every approved question must have at least one evidence row")
    if len(critical) != 12:
        raise ValueError(f"Expected 12 critical cases, found {len(critical)}")

    write_csv(MASTER_DIR / "question_set.csv", questions, QUESTION_FIELDS)
    write_csv(MASTER_DIR / "reference_answers.csv", references, REFERENCE_FIELDS)
    write_csv(MASTER_DIR / "required_evidence.csv", evidence, EVIDENCE_FIELDS)
    write_csv(DATA_DIR / "critical_cases.csv", critical, CRITICAL_FIELDS)

    summary = {
        "status": "approved",
        "question_count": 80,
        "reviewed_pending_count": 39,
        "questions": "data/master_80/question_set.csv",
        "references": "data/master_80/reference_answers.csv",
        "evidence": "data/master_80/required_evidence.csv",
    }
    APPROVAL_SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary | {"critical_case_count": 12}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
