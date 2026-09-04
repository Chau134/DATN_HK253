from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_FIELDS = [
    "query_id",
    "mode",
    "query_type",
    "source_image_id",
    "relevant_product_id",
    "relevance_grade",
    "match_reason",
    "source",
    "review_status",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def finalize_rows(
    review_rows: list[dict[str, str]],
    query_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    expected_query_ids = {row.get("query_id", "") for row in query_rows if row.get("query_id")}
    source_by_query = {
        row.get("query_id", ""): row.get("source_product_id", "")
        for row in query_rows
        if row.get("query_id")
    }
    source_image_by_query = {
        row.get("query_id", ""): row.get("source_image_id", "")
        for row in query_rows
        if row.get("query_id")
    }
    errors: list[str] = []
    finalized: list[dict[str, Any]] = []
    exact_grade_by_query: dict[str, int] = {}
    seen_pairs: set[tuple[str, str]] = set()
    status_counts: dict[str, int] = defaultdict(int)

    for line_number, row in enumerate(review_rows, start=2):
        query_id = (row.get("query_id") or "").strip()
        product_id = (row.get("candidate_product_id") or "").strip()
        status = (row.get("review_status") or "pending").strip().lower()
        status_counts[status] += 1
        if query_id not in expected_query_ids:
            errors.append(f"line {line_number}: unknown query_id={query_id!r}")
            continue
        if not product_id:
            errors.append(f"line {line_number}: candidate_product_id is blank")
            continue
        pair = (query_id, product_id)
        if pair in seen_pairs:
            errors.append(f"line {line_number}: duplicate pair {query_id}|{product_id}")
            continue
        seen_pairs.add(pair)
        if status == "pending":
            continue
        if status not in {"approved", "rejected"}:
            errors.append(f"line {line_number}: invalid review_status={status!r}")
            continue
        if status == "rejected":
            grade = 0
        else:
            raw_grade = (row.get("relevance_grade") or "").strip()
            try:
                grade = int(raw_grade)
            except ValueError:
                errors.append(f"line {line_number}: approved row requires grade 0..3")
                continue
            if grade not in {0, 1, 2, 3}:
                errors.append(f"line {line_number}: relevance_grade must be 0..3")
                continue
        is_exact = product_id == source_by_query.get(query_id)
        if is_exact:
            exact_grade_by_query[query_id] = grade
        notes = (row.get("reviewer_notes") or "").strip()
        is_auto_rule = notes.startswith("metadata_rule_v1:")
        if is_exact:
            match_reason = "source_product_exact_match"
            source = "query_source_mapping"
        elif is_auto_rule:
            match_reason = notes.split(":", 1)[1] or "auto_metadata_similarity"
            source = "metadata_rule_v1"
        else:
            match_reason = "human_visual_similarity"
            source = "human_visual_review_top5"
        finalized.append(
            {
                "query_id": query_id,
                "mode": "image",
                "query_type": "positive",
                "source_image_id": source_image_by_query.get(query_id, ""),
                "relevant_product_id": product_id,
                "relevance_grade": grade,
                "match_reason": match_reason,
                "source": source,
                "review_status": "approved",
                "notes": notes or f"review_status={status}",
            }
        )

    pending_count = status_counts.get("pending", 0)
    if pending_count:
        errors.append(f"review is incomplete: {pending_count} rows are still pending")
    for query_id in sorted(expected_query_ids):
        if exact_grade_by_query.get(query_id) != 3:
            errors.append(f"{query_id}: source product must be approved with grade 3")
    if errors:
        preview = "\n".join(f"- {message}" for message in errors[:20])
        suffix = f"\n- ... and {len(errors) - 20} more" if len(errors) > 20 else ""
        raise ValueError(f"ground-truth review validation failed:\n{preview}{suffix}")
    return finalized


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=GROUND_TRUTH_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a completed visual review and create ground truth.")
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--query-set-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_queries.csv")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=SCRIPT_DIR.parent / "reports" / "ground_truth_image_reviewed.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    finalized = finalize_rows(read_csv(args.review_csv), read_csv(args.query_set_csv))
    write_csv(args.output_csv, finalized)
    print(f"finalized_rows={len(finalized)} -> {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
