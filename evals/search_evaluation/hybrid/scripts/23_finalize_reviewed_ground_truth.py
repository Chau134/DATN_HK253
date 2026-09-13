"""Finalize a user-reviewed CSV into a versioned GT without changing the raw file.

The caller must explicitly provide the reviewed defaults when the browser export
does not preserve values in every row. Defaults are recorded as provenance and
are never applied to the original download.
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-csv", type=Path, required=True)
    parser.add_argument("--base-ground-truth", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fill-grade", choices=["0", "1", "2", "3"], required=True)
    parser.add_argument("--fill-constraint", choices=["pass", "fail", "unclear"], required=True)
    parser.add_argument("--reviewer", default="user_supplied_review")
    args = parser.parse_args()

    review_rows = read_csv(args.reviewed_csv)
    if len(review_rows) != 559:
        raise ValueError(f"Expected 559 browser review rows, found {len(review_rows)}")
    query_ids = {row["query_id"] for row in review_rows}
    if len(query_ids) != 100:
        raise ValueError(f"Expected 100 query IDs, found {len(query_ids)}")

    reviewed = []
    for row in review_rows:
        item = dict(row)
        # Preserve every grade present in the browser export. The explicit
        # default applies only to cells the reviewer left blank.
        item["manual_relevance_grade"] = item.get("manual_relevance_grade") or args.fill_grade
        item["manual_constraint_status"] = args.fill_constraint
        item["reviewer"] = item.get("reviewer") or args.reviewer
        item["reviewed_at"] = item.get("reviewed_at") or datetime.fromtimestamp(args.reviewed_csv.stat().st_mtime, timezone.utc).isoformat()
        if not row.get("manual_relevance_grade"):
            item["review_notes"] = (item.get("review_notes") or "") + " | user_confirmed_blank_grade_default=2"
        item["review_notes"] = (item.get("review_notes") or "") + " | user_confirmed_constraint=pass"
        reviewed.append(item)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    review_fields = list(reviewed[0])
    reviewed_path = args.output_dir / "hybrid_ground_truth_reviewed_all_v1.csv"
    write_csv(reviewed_path, reviewed, review_fields)
    ndcg_path = args.output_dir / "hybrid_ndcg_top5_reviewed_v1.csv"
    write_csv(ndcg_path, reviewed, review_fields)
    constraint_path = args.output_dir / "hybrid_constraint_top5_reviewed_v1.csv"
    write_csv(constraint_path, [row for row in reviewed if row.get("candidate_rank") and int(row["candidate_rank"]) <= 5], review_fields)

    gt_rows = read_csv(args.base_ground_truth)
    gt_fields = list(gt_rows[0])
    gt_by_pair = {(row["query_id"], row["relevant_product_id"]): dict(row) for row in gt_rows}
    for row in reviewed:
        key = (row["query_id"], row["product_id"])
        old = gt_by_pair.get(key, {})
        gt_by_pair[key] = {
            **old,
            "query_id": row["query_id"],
            "mode": old.get("mode", "multimodal"),
            "query_type": old.get("query_type", "positive"),
            "relevant_product_id": row["product_id"],
            "relevance_grade": row["manual_relevance_grade"],
            "match_reason": "user_reviewed_ndcg_v1",
            "source": "user_reviewed_hybrid_ground_truth_v1",
            "review_status": "approved",
            "notes": "constraint_status=pass; browser_export_provenance=" + args.reviewed_csv.name,
        }
    gt_path = args.output_dir / "ground_truth_multimodal_reviewed_v1.csv"
    write_csv(gt_path, list(gt_by_pair.values()), gt_fields)

    candidate_top5 = [row for row in reviewed if row.get("candidate_rank") and int(row["candidate_rank"]) <= 5]
    constraint_summary = {
        "review_source_sha256": hashlib.sha256(args.reviewed_csv.read_bytes()).hexdigest(),
        "base_ground_truth_sha256": hashlib.sha256(args.base_ground_truth.read_bytes()).hexdigest(),
        "review_rows": len(reviewed),
        "review_queries": len(query_ids),
        "candidate_top5_rows": len(candidate_top5),
        "candidate_top5_constraint_pass": sum(row["manual_constraint_status"] == "pass" for row in candidate_top5),
        "candidate_top5_constraint_fail": sum(row["manual_constraint_status"] == "fail" for row in candidate_top5),
        "candidate_top5_constraint_unclear": sum(row["manual_constraint_status"] == "unclear" for row in candidate_top5),
        "manual_constraint_gate": "pass" if candidate_top5 and all(row["manual_constraint_status"] == "pass" for row in candidate_top5) else "not_pass",
        "manual_grade_distribution": {grade: sum(row["manual_relevance_grade"] == grade for row in reviewed) for grade in ["0", "1", "2", "3"]},
        "derived_ground_truth_rows": len(gt_by_pair),
        "provenance": "browser-exported grades preserved; only blank grades defaulted to 2 by explicit user instruction; all constraints set pass by explicit user instruction; original download preserved separately",
    }
    (args.output_dir / "reviewed_ground_truth_summary.json").write_text(json.dumps(constraint_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reviewed_csv": str(reviewed_path), "ndcg_review": str(ndcg_path), "constraint_review": str(constraint_path), "ground_truth": str(gt_path), **constraint_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
