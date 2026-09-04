from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_FIELDS = [
    "query_id", "mode", "query_type", "relevant_product_id", "relevance_grade",
    "match_reason", "source", "review_status", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def validate_references(rows: list[dict[str, str]], queries: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    expected = {row["query_id"] for row in queries}
    by_query = {row.get("query_id", ""): row for row in rows}
    errors: list[str] = []
    if len(rows) != len(by_query):
        errors.append("reference review contains duplicate query_id values")
    if set(by_query) != expected:
        errors.append(f"reference review query mismatch: missing={sorted(expected-set(by_query))} extra={sorted(set(by_query)-expected)}")
    for query_id, row in by_query.items():
        if row.get("review_status", "").lower() != "approved":
            errors.append(f"{query_id}: reference image is not approved")
            continue
        if row.get("identity_preserved", "").lower() != "yes":
            errors.append(f"{query_id}: product identity must be preserved")
        if row.get("unintended_change_absent", "").lower() != "yes":
            errors.append(f"{query_id}: unintended changes must be absent")
        edited = bool(row.get("image_edit_request", "").strip())
        expected_change = "yes" if edited else "not_applicable"
        if row.get("requested_change_present", "").lower() != expected_change:
            errors.append(f"{query_id}: requested_change_present must be {expected_change}")
    if errors:
        raise ValueError("reference review validation failed:\n" + "\n".join(f"- {error}" for error in errors[:30]))
    return by_query


def finalize_candidates(
    rows: list[dict[str, str]],
    queries: list[dict[str, str]],
    approved_references: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    query_by_id = {row["query_id"]: row for row in queries}
    expected_targets = {row["query_id"]: row["target_product_id"] for row in queries}
    seen: set[tuple[str, str]] = set()
    target_grade: dict[str, int] = {}
    output: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, row in enumerate(rows, 2):
        query_id = row.get("query_id", "").strip()
        product_id = row.get("candidate_product_id", "").strip()
        if query_id not in query_by_id:
            errors.append(f"line {line_number}: unknown query_id={query_id!r}")
            continue
        pair = (query_id, product_id)
        if not product_id or pair in seen:
            errors.append(f"line {line_number}: blank or duplicate candidate pair {pair}")
            continue
        seen.add(pair)
        status = row.get("review_status", "").strip().lower()
        if status == "rejected":
            grade = 0
        elif status == "approved":
            try:
                grade = int(row.get("relevance_grade", ""))
            except ValueError:
                errors.append(f"line {line_number}: approved candidate requires grade 0..3")
                continue
            if grade not in {0, 1, 2, 3}:
                errors.append(f"line {line_number}: invalid relevance_grade={grade}")
                continue
        else:
            errors.append(f"line {line_number}: unresolved candidate status={status!r}")
            continue
        is_target = product_id == expected_targets[query_id]
        if is_target:
            target_grade[query_id] = grade
            source = "controlled_counterfactual_visual_review"
            reason = "approved_target_identity_and_counterfactual_edit"
        elif row.get("reviewer_notes", "").startswith("reused_image_ground_truth:"):
            source = "approved_image_ground_truth_transfer"
            reason = "text_constraints_match+approved_visual_grade"
        elif row.get("reviewer_notes", "").startswith("metadata_hybrid_rule_v1:"):
            source = "metadata_hybrid_rule_v1"
            reason = "text_constraints_match+conservative_metadata_visual_proxy"
        else:
            source = "human_hybrid_visual_review"
            reason = "text_constraints_match+human_visual_grade"
        output.append({
            "query_id": query_id,
            "mode": "multimodal",
            "query_type": "positive",
            "relevant_product_id": product_id,
            "relevance_grade": grade,
            "match_reason": reason,
            "source": source,
            "review_status": "approved",
            "notes": row.get("reviewer_notes", "").strip() or approved_references[query_id].get("reviewer_notes", ""),
        })
    for query_id in expected_targets:
        if target_grade.get(query_id) != 3:
            errors.append(f"{query_id}: target product must be approved at grade 3")
    if errors:
        raise ValueError("candidate review validation failed:\n" + "\n".join(f"- {error}" for error in errors[:30]))
    return output


def update_query_status(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    updated = []
    for original in rows:
        row = dict(original)
        row["image_status"] = "approved_counterfactual" if row.get("image_edit_request", "").strip() else "approved_reused"
        row["manual_status"] = "approved"
        row["notes"] = "approved_hybrid_ground_truth_review;target_is_source_database_product"
        updated.append(row)
    return updated


def update_requirement_status(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    updated = []
    for original in rows:
        row = dict(original)
        row["review_status"] = "approved"
        row["notes"] = "visual_identity_and_requested_counterfactual_change_approved"
        updated.append(row)
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Hybrid visual review and freeze approved ground truth.")
    root = SCRIPT_DIR.parent
    parser.add_argument("--queries-csv", type=Path, default=root / "data" / "multimodal_queries.csv")
    parser.add_argument("--requirements-csv", type=Path, default=root / "data" / "reference_image_requirements.csv")
    parser.add_argument("--reference-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_reference_review.csv")
    parser.add_argument("--candidate-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_candidate_review.csv")
    parser.add_argument("--output-ground-truth-csv", type=Path, default=root / "data" / "ground_truth_multimodal.csv")
    parser.add_argument("--summary-json", type=Path, default=root / "reports" / "review" / "hybrid_ground_truth_review_summary.json")
    parser.add_argument("--update-source-status", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queries = read_csv(args.queries_csv)
    references = validate_references(read_csv(args.reference_review_csv), queries)
    ground_truth = finalize_candidates(read_csv(args.candidate_review_csv), queries, references)
    write_csv(args.output_ground_truth_csv, GROUND_TRUTH_FIELDS, ground_truth)
    if args.update_source_status:
        requirements = read_csv(args.requirements_csv)
        write_csv(args.queries_csv, list(queries[0]), update_query_status(queries))
        write_csv(args.requirements_csv, list(requirements[0]), update_requirement_status(requirements))
    summary = {
        "reviewed_at_utc": datetime.now(UTC).isoformat(),
        "query_count": len(queries),
        "reference_images_approved": len(references),
        "ground_truth_rows_approved": len(ground_truth),
        "grade_distribution": dict(sorted(Counter(str(row["relevance_grade"]) for row in ground_truth).items())),
        "source_distribution": dict(sorted(Counter(row["source"] for row in ground_truth).items())),
        "review_status": "approved",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
