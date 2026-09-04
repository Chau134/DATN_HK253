from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPT_DIR.parent
EVAL_DIR = SUITE_DIR.parent / "conversational_ai_evaluation"


def _load_review_module() -> ModuleType:
    path = EVAL_DIR / "scripts" / "09_ground_truth_review.py"
    spec = importlib.util.spec_from_file_location("conversational_ground_truth_apply", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load ground-truth review module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_pending(args: argparse.Namespace) -> dict[str, object]:
    review = _load_review_module()
    full_rows = review.read_csv_rows(args.full_review_csv)
    pending_rows = review.read_csv_rows(args.pending_review_csv)
    products = review.read_csv_rows(args.products)
    if args.approve_all:
        if not args.reviewer.strip():
            raise ValueError("--reviewer is required with --approve-all")
        for row in pending_rows:
            row["question_status"] = "approved"
            row["reference_status"] = "approved"
            row["evidence_status"] = (
                "approved" if review.parse_evidence(row) else "not_applicable"
            )
            row["reviewer"] = args.reviewer.strip()
            if args.review_notes.strip():
                row["review_notes"] = args.review_notes.strip()
        review.write_csv_rows(args.pending_review_csv, pending_rows, review.REVIEW_FIELDS)
    pending_by_id = {row["question_id"]: row for row in pending_rows}
    expected_pending = {
        row["question_id"] for row in full_rows
        if row["question_status"] != "approved"
        or row["reference_status"] != "approved"
        or row["evidence_status"] not in {"approved", "not_applicable"}
    }
    if set(pending_by_id) != expected_pending:
        raise ValueError(
            "Pending packet IDs changed: "
            f"missing={sorted(expected_pending - set(pending_by_id))}, "
            f"unexpected={sorted(set(pending_by_id) - expected_pending)}"
        )

    pending_errors = review.validate_review_rows(
        pending_rows,
        products,
        expected_question_ids=expected_pending,
        require_complete=True,
    )
    if pending_errors:
        raise ValueError("Pending review is incomplete or invalid:\n" + "\n".join(pending_errors))

    merged_rows = [pending_by_id.get(row["question_id"], row) for row in full_rows]
    full_errors = review.validate_review_rows(
        merged_rows,
        products,
        expected_question_ids={row["question_id"] for row in full_rows},
        require_complete=True,
    )
    if full_errors:
        raise ValueError("Merged master review is invalid:\n" + "\n".join(full_errors))

    review.write_csv_rows(args.full_review_csv, merged_rows, review.REVIEW_FIELDS)
    apply_args = SimpleNamespace(
        questions=args.questions,
        references=args.references,
        evidence=args.evidence,
        products=args.products,
        review_csv=args.full_review_csv,
        review_markdown=args.full_review_markdown,
        review_summary=args.full_review_summary,
    )
    result = review.apply_review(apply_args)
    if result != 0:
        raise RuntimeError(f"Ground-truth apply returned {result}")
    summary = {
        "status": "approved",
        "question_count": len(merged_rows),
        "reviewed_pending_count": len(pending_rows),
        "questions": str(args.questions),
        "references": str(args.references),
        "evidence": str(args.evidence),
    }
    args.approval_summary.parent.mkdir(parents=True, exist_ok=True)
    args.approval_summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    data_dir = SUITE_DIR / "data" / "master_80"
    review_dir = SUITE_DIR / "review" / "master_80"
    parser = argparse.ArgumentParser(
        description="Validate the focused 39-row packet and apply it to master-80-v2."
    )
    parser.add_argument("--questions", type=Path, default=data_dir / "question_set.csv")
    parser.add_argument("--references", type=Path, default=data_dir / "reference_answers.csv")
    parser.add_argument("--evidence", type=Path, default=data_dir / "required_evidence.csv")
    parser.add_argument("--products", type=Path, default=data_dir / "product_snapshot.csv")
    parser.add_argument("--full-review-csv", type=Path, default=review_dir / "ground_truth_review.csv")
    parser.add_argument("--full-review-markdown", type=Path, default=review_dir / "ground_truth_review.md")
    parser.add_argument("--full-review-summary", type=Path, default=review_dir / "ground_truth_review_summary.json")
    parser.add_argument("--pending-review-csv", type=Path, default=review_dir / "ground_truth_review_pending.csv")
    parser.add_argument("--approval-summary", type=Path, default=review_dir / "ground_truth_approval_summary.json")
    parser.add_argument(
        "--approve-all",
        action="store_true",
        help="Record explicit approval for every row in the focused pending packet before applying it.",
    )
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--review-notes", default="")
    return parser.parse_args()


def main() -> int:
    print(json.dumps(apply_pending(parse_args()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
