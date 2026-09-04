from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType


SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPT_DIR.parent
EVAL_DIR = SUITE_DIR.parent / "conversational_ai_evaluation"


def _load_review_module() -> ModuleType:
    path = EVAL_DIR / "scripts" / "09_ground_truth_review.py"
    spec = importlib.util.spec_from_file_location("conversational_ground_truth_review", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load ground-truth review module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(args: argparse.Namespace) -> dict[str, object]:
    review = _load_review_module()
    questions = review.read_csv_rows(args.questions)
    references = review.read_csv_rows(args.references)
    evidence = review.read_csv_rows(args.evidence)
    products = review.read_csv_rows(args.products)
    rows = review.build_review_rows(questions, references, evidence, products)
    errors = review.validate_review_rows(
        rows,
        products,
        expected_question_ids={row["question_id"] for row in questions},
    )
    if errors:
        raise ValueError("Master ground truth is structurally invalid:\n" + "\n".join(errors))

    full_summary = review.review_summary(rows, errors)
    review.write_csv_rows(args.review_csv, rows, review.REVIEW_FIELDS)
    review.write_review_markdown(args.review_markdown, rows, full_summary)
    args.review_summary.parent.mkdir(parents=True, exist_ok=True)
    args.review_summary.write_text(
        json.dumps(full_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    pending_rows = [
        row for row in rows
        if row["question_status"] != "approved"
        or row["reference_status"] != "approved"
        or row["evidence_status"] not in {"approved", "not_applicable"}
    ]
    pending_summary = review.review_summary(pending_rows, [])
    review.write_csv_rows(args.pending_csv, pending_rows, review.REVIEW_FIELDS)
    review.write_review_markdown(args.pending_markdown, pending_rows, pending_summary)
    args.pending_summary.parent.mkdir(parents=True, exist_ok=True)
    args.pending_summary.write_text(
        json.dumps(pending_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "master_question_count": len(rows),
        "pending_review_count": len(pending_rows),
        "full_review_csv": str(args.review_csv),
        "pending_review_csv": str(args.pending_csv),
        "pending_review_markdown": str(args.pending_markdown),
    }


def parse_args() -> argparse.Namespace:
    data_dir = SUITE_DIR / "data" / "master_80"
    review_dir = SUITE_DIR / "review" / "master_80"
    parser = argparse.ArgumentParser(description="Prepare full and focused ground-truth review packets for master-80-v2.")
    parser.add_argument("--questions", type=Path, default=data_dir / "question_set.csv")
    parser.add_argument("--references", type=Path, default=data_dir / "reference_answers.csv")
    parser.add_argument("--evidence", type=Path, default=data_dir / "required_evidence.csv")
    parser.add_argument("--products", type=Path, default=data_dir / "product_snapshot.csv")
    parser.add_argument("--review-csv", type=Path, default=review_dir / "ground_truth_review.csv")
    parser.add_argument("--review-markdown", type=Path, default=review_dir / "ground_truth_review.md")
    parser.add_argument("--review-summary", type=Path, default=review_dir / "ground_truth_review_summary.json")
    parser.add_argument("--pending-csv", type=Path, default=review_dir / "ground_truth_review_pending.csv")
    parser.add_argument("--pending-markdown", type=Path, default=review_dir / "ground_truth_review_pending.md")
    parser.add_argument("--pending-summary", type=Path, default=review_dir / "ground_truth_review_pending_summary.json")
    return parser.parse_args()


def main() -> int:
    print(json.dumps(prepare(parse_args()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
