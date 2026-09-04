from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
IMAGE_ROOT = SCRIPT_DIR.parents[1]
FIELDS = [
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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def validated_grade(row: dict[str, str], label: str) -> int:
    raw = (row.get("relevance_grade") or "").strip()
    try:
        grade = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label}: blank or invalid relevance_grade={raw!r}") from exc
    if grade not in {0, 1, 2, 3}:
        raise ValueError(f"{label}: relevance_grade must be 0..3")
    return grade


def convert_new_row(
    row: dict[str, str],
    source_image_by_query: dict[str, str],
    *,
    human: bool,
) -> dict[str, Any]:
    query_id = (row.get("query_id") or "").strip()
    product_id = (row.get("candidate_product_id") or "").strip()
    if not query_id or not product_id:
        raise ValueError("new judgment requires query_id and candidate_product_id")
    grade = validated_grade(row, f"{query_id}|{product_id}")
    original_status = (row.get("review_status") or "").strip().lower()
    if original_status not in {"approved", "pending"}:
        raise ValueError(f"{query_id}|{product_id}: unsupported review_status={original_status!r}")
    reviewer_notes = (row.get("reviewer_notes") or "").strip()
    if human:
        match_reason = "human_visual_similarity"
        source = "human_visual_review_new_outdoor_top5"
        notes = "paired_pool_20260828"
        if original_status == "pending":
            notes += "; graded_pending_accepted_after_user_confirmation"
    else:
        reason = reviewer_notes.split(":", 1)[1] if reviewer_notes.startswith("metadata_rule_v1:") else reviewer_notes
        match_reason = reason or "auto_metadata_similarity"
        source = "metadata_rule_v1"
        notes = reviewer_notes or "paired_pool_20260828"
    return {
        "query_id": query_id,
        "mode": "image",
        "query_type": "positive",
        "source_image_id": source_image_by_query.get(query_id, ""),
        "relevant_product_id": product_id,
        "relevance_grade": grade,
        "match_reason": match_reason,
        "source": source,
        "review_status": "approved",
        "notes": notes,
    }


def build(args: argparse.Namespace) -> list[dict[str, Any]]:
    old_rows = read_csv(args.old_ground_truth)
    human_rows = read_csv(args.human_review)
    automatic_rows = read_csv(args.auto_rule)
    expected_human = read_csv(args.expected_human)
    query_rows = read_csv(args.challenging_queries)
    source_image_by_query = {row["query_id"]: row.get("source_image_id", "") for row in query_rows}

    expected_keys = {(row.get("query_id", ""), row.get("candidate_product_id", "")) for row in expected_human}
    human_keys = {(row.get("query_id", ""), row.get("candidate_product_id", "")) for row in human_rows}
    if human_keys != expected_keys:
        missing = sorted(expected_keys - human_keys)
        extra = sorted(human_keys - expected_keys)
        raise ValueError(f"human review does not match queue: missing={missing[:5]} extra={extra[:5]}")

    output: list[dict[str, Any]] = [dict(row) for row in old_rows]
    output.extend(convert_new_row(row, source_image_by_query, human=True) for row in human_rows)
    output.extend(convert_new_row(row, source_image_by_query, human=False) for row in automatic_rows)

    seen: set[tuple[str, str]] = set()
    for row in output:
        key = (str(row.get("query_id", "")), str(row.get("relevant_product_id", "")))
        if key in seen:
            raise ValueError(f"duplicate ground-truth pair: {key}")
        seen.add(key)
        if row.get("review_status") != "approved":
            raise ValueError(f"non-approved output row: {key}")
        validated_grade({"relevance_grade": str(row.get("relevance_grade", ""))}, "|".join(key))
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge canonical and incremental paired image-search judgments.")
    parser.add_argument("--old-ground-truth", type=Path, default=IMAGE_ROOT / "data/ground_truth_image.csv")
    parser.add_argument("--human-review", type=Path, default=IMAGE_ROOT / "data/paired_top20_pool_reviewed.csv")
    parser.add_argument("--expected-human", type=Path, default=IMAGE_ROOT / "simple/reports/pooling/paired_top20_pool_human_review_pending.csv")
    parser.add_argument("--auto-rule", type=Path, default=IMAGE_ROOT / "simple/reports/pooling/paired_top20_pool_auto_rule.csv")
    parser.add_argument("--challenging-queries", type=Path, default=IMAGE_ROOT / "challenging/data/image_queries.csv")
    parser.add_argument("--output", type=Path, default=IMAGE_ROOT / "data/ground_truth_image_paired.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build(args)
    write_csv(args.output, rows)
    source_counts: dict[str, int] = {}
    grade_counts: dict[str, int] = {}
    for row in rows:
        source = str(row["source"])
        grade = str(row["relevance_grade"])
        source_counts[source] = source_counts.get(source, 0) + 1
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    print(f"merged_rows={len(rows)} sources={source_counts} grades={grade_counts}")
    print(f"ground truth -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
