from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    build_reference_and_evidence,
    load_conv_products,
    preserve_review_metadata_if_unchanged,
    read_csv_rows,
    write_csv_rows,
)

REFERENCE_FIELDNAMES = [
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
]
EVIDENCE_FIELDNAMES = [
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
]


def main() -> int:
    args = parse_args()
    products = load_conv_products(args.snapshot_csv)
    products_by_id = {product.product_id: product for product in products}
    question_rows = read_csv_rows(args.question_set_csv)
    existing_references = (
        {row["question_id"]: row for row in read_csv_rows(args.reference_csv)}
        if args.reference_csv.exists()
        else {}
    )
    existing_evidence = (
        {
            (row["question_id"], row["evidence_id"]): row
            for row in read_csv_rows(args.evidence_csv)
        }
        if args.evidence_csv.exists()
        else {}
    )

    reference_rows: list[dict] = []
    evidence_rows: list[dict] = []
    for question_row in question_rows:
        reference, evidence = build_reference_and_evidence(question_row, products_by_id)
        reference_row = reference.to_row()
        reference_rows.append(
            preserve_review_metadata_if_unchanged(
                reference_row,
                existing_references.get(reference.question_id),
                content_fields=(
                    "question_id",
                    "reference_answer",
                    "answer_must_include",
                    "answer_must_not_include",
                    "reference_source_ids",
                    "notes",
                ),
            )
        )
        for record in evidence:
            evidence_row = record.to_row()
            evidence_rows.append(
                preserve_review_metadata_if_unchanged(
                    evidence_row,
                    existing_evidence.get((record.question_id, record.evidence_id)),
                    content_fields=(
                        "question_id",
                        "evidence_id",
                        "source_id",
                        "evidence_text",
                        "evidence_role",
                        "required_level",
                        "notes",
                    ),
                )
            )

    write_csv_rows(args.reference_csv, reference_rows, REFERENCE_FIELDNAMES)
    write_csv_rows(args.evidence_csv, evidence_rows, EVIDENCE_FIELDNAMES)
    print(f"generated {len(reference_rows)} reference answers, {len(evidence_rows)} evidence rows")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create reference answers and required evidence for the conversational eval question set.")
    parser.add_argument("--snapshot-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--question-set-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "question_set.csv")
    parser.add_argument("--reference-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "reference_answers.csv")
    parser.add_argument("--evidence-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "required_evidence.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
