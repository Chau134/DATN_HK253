from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
AUDIT_FIELDS = [
    "question_id",
    "category",
    "rule_based_grounding_score",
    "token_f1_relevancy",
    "human_grounding_pass",
    "human_relevancy_pass",
    "audit_notes",
]


def select_stratified(rows: list[dict[str, str]], ratio: float, seed: int) -> list[dict[str, str]]:
    target = min(len(rows), max(1, math.ceil(len(rows) * ratio))) if rows else 0
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row.get("category", "unknown")].append(row)
    rng = random.Random(seed)
    for values in groups.values():
        rng.shuffle(values)
    selected: list[dict[str, str]] = []
    while len(selected) < target:
        progressed = False
        for category in sorted(groups):
            if groups[category] and len(selected) < target:
                selected.append(groups[category].pop())
                progressed = True
        if not progressed:
            break
    return selected


def summarize_audit(
    rows: list[dict[str, str]],
    *,
    total_cases: int,
    ratio: float,
    grounding_threshold: float,
    relevancy_threshold: float,
) -> dict:
    required = math.ceil(total_cases * ratio)
    completed = [
        row for row in rows
        if _parse_bool(row.get("human_grounding_pass")) is not None
        and _parse_bool(row.get("human_relevancy_pass")) is not None
    ]
    metrics = {
        "rule_based_grounding_score": (
            "human_grounding_pass", grounding_threshold
        ),
        "token_f1_relevancy": ("human_relevancy_pass", relevancy_threshold),
    }
    agreement = {}
    for metric, (human_field, threshold) in metrics.items():
        false_positives: list[str] = []
        false_negatives: list[str] = []
        matches = 0
        for row in completed:
            evaluator_pass = float(row.get(metric) or 0) >= threshold
            human_pass = bool(_parse_bool(row.get(human_field)))
            matches += evaluator_pass == human_pass
            if evaluator_pass and not human_pass:
                false_positives.append(row["question_id"])
            elif human_pass and not evaluator_pass:
                false_negatives.append(row["question_id"])
        agreement[metric] = {
            "agreement": matches / len(completed) if completed else None,
            "false_positive_question_ids": false_positives,
            "false_negative_question_ids": false_negatives,
        }
    audited_categories = sorted({row.get("category", "unknown") for row in completed})
    return {
        "total_cases": total_cases,
        "required_audit_cases": required,
        "completed_audit_cases": len(completed),
        "coverage": len(completed) / total_cases if total_cases else 0.0,
        "audited_categories": audited_categories,
        "audit_complete": len(completed) >= required,
        "agreement": agreement,
    }


def _parse_bool(value: str | None) -> bool | None:
    normalized = (value or "").strip().lower()
    if normalized in {"true", "1", "yes", "pass"}:
        return True
    if normalized in {"false", "0", "no", "fail"}:
        return False
    return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    metric_rows = read_csv(args.metrics_csv)
    if args.prepare or not args.audit_csv.exists():
        selected = select_stratified(metric_rows, args.ratio, args.seed)
        audit_rows = [
            {field: row.get(field, "") for field in AUDIT_FIELDS}
            for row in selected
        ]
        write_csv(args.audit_csv, audit_rows)
    else:
        audit_rows = read_csv(args.audit_csv)
    summary = summarize_audit(
        audit_rows,
        total_cases=len(metric_rows),
        ratio=args.ratio,
        grounding_threshold=args.grounding_threshold,
        relevancy_threshold=args.relevancy_threshold,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if args.prepare or summary["audit_complete"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and score a stratified evaluator audit.")
    parser.add_argument("--metrics-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "rag_metrics_by_question.csv")
    parser.add_argument("--audit-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "evaluator_manual_audit.csv")
    parser.add_argument("--output-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "evaluator_manual_audit_summary.json")
    parser.add_argument("--ratio", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=252)
    parser.add_argument("--grounding-threshold", type=float, default=0.85)
    parser.add_argument("--relevancy-threshold", type=float, default=0.70)
    parser.add_argument("--prepare", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
