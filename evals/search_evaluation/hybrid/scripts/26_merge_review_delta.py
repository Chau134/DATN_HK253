"""Validate and merge a reviewed delta without overwriting existing labels.

An exact frozen pool match is required. Existing GT rows are immutable. Import
time/file modification time are provenance, never invented human review times.
An optional blank-grade default is applied only when explicitly requested and
is recorded in the output provenance.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re


MANUAL_FIELDS = {
    "manual_relevance_grade", "manual_constraint_status", "manual_violation_fields",
    "reviewer", "reviewed_at", "review_notes",
}


def read_table(path):
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    fields = reader.fieldnames or []
    rows = list(reader)
    if not fields or len(fields) != len(set(fields)) or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError(f"Malformed CSV: {path}")
    return raw, fields, rows


def index_unique(rows, product_field):
    indexed = {}
    for row in rows:
        key = (row.get("query_id"), row.get(product_field))
        if not all(key) or key in indexed:
            raise ValueError(f"Missing or duplicate pair: {key}")
        indexed[key] = row
    return indexed


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def merge_delta(reviewed_csv, expected_pool, base_ground_truth, output_dir, version,
                fill_blank_grade=None, grade_override=None):
    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise ValueError("Expected a version such as v2")
    raw_review, fields, reviewed = read_table(reviewed_csv)
    raw_pool, pool_fields, pool = read_table(expected_pool)
    raw_base, gt_fields, base = read_table(base_ground_truth)
    if not reviewed or not base or set(fields) != set(pool_fields) or not MANUAL_FIELDS <= set(fields):
        raise ValueError("Empty input or review schema mismatch")
    required_gt = {"query_id", "mode", "query_type", "relevant_product_id", "relevance_grade", "match_reason", "source", "review_status", "notes"}
    if not required_gt <= set(gt_fields):
        raise ValueError("Base GT schema mismatch")
    actual = index_unique(reviewed, "product_id")
    expected = index_unique(pool, "product_id")
    existing = index_unique(base, "relevant_product_id")
    if set(actual) != set(expected):
        raise ValueError("Review pairs do not match the frozen expected pool")
    if set(actual) & set(existing):
        raise ValueError("Delta would overwrite existing ground truth")
    for row in base:
        if row["review_status"] != "approved" or row["relevance_grade"] not in {"0", "1", "2", "3"}:
            raise ValueError("Base GT must contain approved, valid grades")
    base_queries = {r["query_id"] for r in base}
    overrides = {}
    for query_id, product_id, grade in grade_override or []:
        key = (query_id, product_id)
        if key in overrides:
            raise ValueError(f"Duplicate grade override: {key}")
        overrides[key] = grade
    if set(overrides) - set(actual):
        raise ValueError(f"Grade override is outside the review pool: {set(overrides) - set(actual)}")
    grade_defaults_applied = 0
    grade_overrides_applied = 0
    for key, row in actual.items():
        if row["query_id"] not in base_queries:
            raise ValueError(f"Unknown query: {key}")
        if any(row[f] != expected[key][f] for f in set(fields) - MANUAL_FIELDS):
            raise ValueError(f"Frozen context changed: {key}")
        if key in overrides:
            if row["manual_relevance_grade"]:
                raise ValueError(f"Grade override may only target a blank reviewed cell: {key}")
            row["manual_relevance_grade"] = overrides[key]
            grade_overrides_applied += 1
            note = row.get("review_notes", "").strip()
            marker = f"user_confirmed_grade_override={overrides[key]}"
            row["review_notes"] = f"{note} | {marker}" if note else marker
        if not row["manual_relevance_grade"] and fill_blank_grade is not None:
            row["manual_relevance_grade"] = fill_blank_grade
            grade_defaults_applied += 1
            note = row.get("review_notes", "").strip()
            marker = f"user_confirmed_blank_grade_default={fill_blank_grade}"
            row["review_notes"] = f"{note} | {marker}" if note else marker
        if row["manual_relevance_grade"] not in {"0", "1", "2", "3"}:
            raise ValueError(f"Missing or invalid grade: {key}")
        if row["manual_constraint_status"] not in {"pass", "fail", "unclear"}:
            raise ValueError(f"Missing or invalid constraint: {key}")
        if row["manual_constraint_status"] != "pass" and not (row["manual_violation_fields"].strip() or row["review_notes"].strip()):
            raise ValueError(f"Constraint decision needs notes: {key}")
    source_hash = hashlib.sha256(raw_review).hexdigest()
    derived = [dict(r) for r in base]
    for row in reviewed:
        item = dict.fromkeys(gt_fields, "")
        provenance = {
            "constraint_status": row["manual_constraint_status"],
            "violation_fields": row["manual_violation_fields"],
            "review_notes": row["review_notes"],
            "reviewer": row["reviewer"], "reviewed_at": row["reviewed_at"],
            "review_source": reviewed_csv.name, "review_source_sha256": source_hash,
            "attribution": "user supplied completed review in conversation; blank reviewer/time fields remain unknown",
        }
        item.update(query_id=row["query_id"], mode="multimodal", query_type="positive",
                    relevant_product_id=row["product_id"], relevance_grade=row["manual_relevance_grade"],
                    match_reason=f"user_reviewed_usage_any_delta_{version}",
                    source=f"user_reviewed_hybrid_ground_truth_{version}", review_status="approved",
                    notes=json.dumps(provenance, ensure_ascii=False, separators=(",", ":")))
        derived.append(item)
    # All validation completes before creating files. Never overwrite an old run.
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "source_review.csv").write_bytes(raw_review)
    write_csv(output_dir / "reviewed_delta.csv", reviewed, fields)
    gt_path = output_dir / f"ground_truth_multimodal_reviewed_{version}.csv"
    write_csv(gt_path, derived, gt_fields)
    summary = {
        "version": version, "ready_for_gt_version": True, "error_count": 0,
        "review_source_sha256": source_hash,
        "expected_pool_sha256": hashlib.sha256(raw_pool).hexdigest(),
        "base_ground_truth_sha256": hashlib.sha256(raw_base).hexdigest(),
        "derived_ground_truth_sha256": hashlib.sha256(gt_path.read_bytes()).hexdigest(),
        "review_rows": len(reviewed), "review_queries": len({r['query_id'] for r in reviewed}),
        "grade_distribution": dict(sorted(Counter(r["manual_relevance_grade"] for r in reviewed).items())),
        "constraint_distribution": dict(Counter(r["manual_constraint_status"] for r in reviewed)),
        "base_rows_preserved": len(base), "derived_rows": len(derived), "derived_queries": len(base_queries),
        "grade_defaults_applied": grade_defaults_applied,
        "grade_default": fill_blank_grade,
        "grade_overrides_applied": grade_overrides_applied,
        "grade_overrides": [
            {"query_id": key[0], "product_id": key[1], "grade": grade}
            for key, grade in sorted(overrides.items())
        ],
        "constraint_defaults_applied": 0,
        "reviewer_or_time_invented": False, "attribution": "user supplied completed review in conversation",
        "source_file_modified_at_utc": datetime.fromtimestamp(reviewed_csv.stat().st_mtime, timezone.utc).isoformat(),
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "timestamp_note": "File/import timestamps are not human review timestamps.",
        "manual_constraint_scope": "Only this delta, not an automatic verdict on every result or the exact evaluator gate.",
    }
    (output_dir / "review_validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    def parse_override(value):
        parts = value.split(":")
        if len(parts) != 3 or parts[2] not in {"0", "1", "2", "3"} or not all(parts[:2]):
            raise argparse.ArgumentTypeError("grade override must be QUERY_ID:PRODUCT_ID:GRADE")
        return tuple(parts)

    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-csv", type=Path, required=True)
    parser.add_argument("--expected-pool", type=Path, required=True)
    parser.add_argument("--base-ground-truth", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--fill-blank-grade", choices=["0", "1", "2", "3"])
    parser.add_argument("--grade-override", action="append", type=parse_override)
    args = parser.parse_args()
    print(json.dumps(merge_delta(**vars(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
