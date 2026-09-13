"""Diagnose ranking vs coverage on frozen human judgments; never modify grades."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("comparison", ROOT / "scripts/13_compare_ablation.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--admission-audit", type=Path, help="Frozen judged_missing.csv from the catalog admission audit")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    queries = comparison.read_csv(ROOT / "data/multimodal_queries.csv")
    gt = comparison.read_csv(args.ground_truth)
    results = comparison.read_csv(args.results)
    admission_rows = comparison.read_csv(args.admission_audit) if args.admission_audit else []
    rejected = {(r["query_id"], r["product_id"]) for r in admission_rows if r["eligible"].lower() == "false"}
    rows, missing = [], []
    for q in queries:
        qid = q["query_id"]
        grades = {r["relevant_product_id"]: int(r["relevance_grade"]) for r in gt if r["query_id"] == qid}
        ranked = [r["product_id"] for r in sorted((r for r in results if r["query_id"] == qid), key=lambda r: int(r["rank"]))]
        ideal_within_returned = sorted(ranked, key=lambda p: -grades.get(p, 0))
        actual = comparison.ndcg(ranked, grades, 5)
        ceiling = comparison.ndcg(ideal_within_returned, grades, 5)
        rows.append({"query_id": qid, "query_text": q["query_text"], "transformation_type": q["transformation_type"],
                     "returned_top5": min(5, len(ranked)), "returned_top20": len(ranked), "ndcg@5": actual,
                     "judged_reorder_ceiling@5": ceiling, "ranking_gap": max(0, ceiling - actual),
                     "coverage_gap": max(0, 1 - ceiling), "unjudged_top20": sum(p not in grades for p in ranked),
                     "positive_judgments": sum(g > 0 for g in grades.values())})
        if args.admission_audit:
            # Optimistic: only exclude products positively identified as rejected.
            # Untested judgments (including grade 1) are all assumed admissible.
            admissible = sorted((p for p in grades if (qid, p) not in rejected), key=lambda p: -grades[p])
            rows[-1]["optimistic_fixed_gt_admission_ceiling@5"] = comparison.ndcg(admissible, grades, 5)
        for pid, grade in grades.items():
            if grade > 0 and pid not in ranked:
                missing.append({"query_id": qid, "query_text": q["query_text"], "product_id": pid, "grade": grade})
    args.output.mkdir(parents=True, exist_ok=False)
    for name, values, fields in (
        ("per_query.csv", rows, list(rows[0])),
        ("judged_positive_not_returned.csv", missing, ["query_id", "query_text", "product_id", "grade"]),
    ):
        with (args.output / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(values)
    summary = {"ground_truth_sha256": hashlib.sha256(args.ground_truth.read_bytes()).hexdigest(),
               "actual_ndcg@5": statistics.fmean(r["ndcg@5"] for r in rows),
               "judged_reorder_ceiling@5": statistics.fmean(r["judged_reorder_ceiling@5"] for r in rows),
               "mean_ranking_gap": statistics.fmean(r["ranking_gap"] for r in rows),
               "mean_coverage_gap": statistics.fmean(r["coverage_gap"] for r in rows),
               "underfilled_queries": sum(r["returned_top5"] < 5 for r in rows),
               "unjudged_top20": sum(r["unjudged_top20"] for r in rows),
               "note": "Oracle reorder diagnostic uses known labels only; not a deployable ranking or proof of a ceiling for unjudged candidates.",
               "largest_gaps": sorted(rows, key=lambda r: -r["coverage_gap"])[:10]}
    if args.admission_audit:
        summary.update({
            "admission_audit_sha256": hashlib.sha256(args.admission_audit.read_bytes()).hexdigest(),
            "known_rejected_judgments": len(rejected),
            "optimistic_fixed_gt_admission_ceiling@5": statistics.fmean(r["optimistic_fixed_gt_admission_ceiling@5"] for r in rows),
            "admission_ceiling_scope": "Diagnostic for this fixed GT and audited predicates only; assumes every unaudited judgment admissible. Not a bound after new human labels or rule changes; not a deployable ranking.",
        })
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "largest_gaps"}, indent=2))


if __name__ == "__main__":
    main()
