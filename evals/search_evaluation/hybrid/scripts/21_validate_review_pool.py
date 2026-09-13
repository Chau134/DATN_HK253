"""Validate completed human-review CSVs before creating a new GT version."""

import argparse
import csv
import json
from pathlib import Path


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ndcg", type=Path, required=True, help="completed review_pool_top5_unjudged_union.csv")
    parser.add_argument("--constraint", type=Path, required=True, help="completed constraint_review_top5.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ndcg = rows(args.ndcg)
    constraint = rows(args.constraint)
    allowed_grades = {"0", "1", "2", "3"}
    allowed_constraint = {"pass", "fail", "unclear"}
    errors = []
    for row in ndcg:
        if row.get("manual_relevance_grade", "") not in allowed_grades:
            errors.append({"kind": "missing_or_invalid_relevance_grade", "query_id": row.get("query_id"), "product_id": row.get("product_id")})
        if not row.get("reviewer") or not row.get("reviewed_at"):
            errors.append({"kind": "missing_reviewer_provenance", "query_id": row.get("query_id"), "product_id": row.get("product_id")})
    for row in constraint:
        value = row.get("manual_constraint_status", "")
        if value not in allowed_constraint:
            errors.append({"kind": "missing_or_invalid_constraint_status", "query_id": row.get("query_id"), "product_id": row.get("product_id")})
        if value in {"fail", "unclear"} and not row.get("manual_violation_fields") and not row.get("review_notes"):
            errors.append({"kind": "constraint_decision_needs_notes", "query_id": row.get("query_id"), "product_id": row.get("product_id")})
    summary = {
        "ndcg_rows": len(ndcg),
        "constraint_rows": len(constraint),
        "error_count": len(errors),
        "ready_for_gt_version": not errors,
        "errors": errors,
        "next_step": "Create a versioned ground truth and rerun both policies only after ready_for_gt_version=true.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not errors else 2)


if __name__ == "__main__":
    main()
