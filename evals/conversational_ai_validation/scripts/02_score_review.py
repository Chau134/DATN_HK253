from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import (
    HARD_GATE_FIELDS,
    RATING_FIELDS,
    calibrate_threshold,
    cohen_kappa,
    confusion,
    evaluate_review_row,
    load_config,
    parse_gate,
    parse_rating,
    read_csv,
    resolve,
    rounded,
    write_csv,
    write_json,
)


def _index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["question_id"]: row for row in rows}


def _agreement(left: list[Any], right: list[Any]) -> dict[str, Any]:
    if not left:
        return {"case_count": 0, "exact_agreement": None, "within_one": None, "kappa_at_4": None}
    exact = sum(a == b for a, b in zip(left, right)) / len(left)
    within_one = sum(abs(a - b) <= 1 for a, b in zip(left, right)) / len(left)
    return {
        "case_count": len(left),
        "exact_agreement": rounded(exact),
        "within_one": rounded(within_one),
        "kappa_at_4": rounded(cohen_kappa(
            [value >= 4 for value in left],
            [value >= 4 for value in right],
        )),
    }


def _human_breakdown(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field, "unknown"))].append(row)
    result = {}
    for group, values in sorted(groups.items()):
        decided = [row for row in values if row["consensus_accepted"] is not None]
        result[group] = {
            "case_count": len(values),
            "consensus_case_count": len(decided),
            "acceptance_rate": rounded(
                sum(bool(row["consensus_accepted"]) for row in decided) / len(decided)
            ) if decided else None,
            "adjudication_count": sum(row["consensus"] == "adjudication_required" for row in values),
        }
    return result


def score_reviews(config_path: Path | None = None) -> dict[str, Any]:
    config, base = load_config(config_path)
    reviewer_a = _index(read_csv(resolve(base, config["review"]["reviewer_a_csv"])))
    reviewer_b = _index(read_csv(resolve(base, config["review"]["reviewer_b_csv"])))
    if set(reviewer_a) != set(reviewer_b):
        missing_a = sorted(set(reviewer_b) - set(reviewer_a))
        missing_b = sorted(set(reviewer_a) - set(reviewer_b))
        raise ValueError(f"Reviewer packets differ; missing A={missing_a}, missing B={missing_b}")

    metrics = _index(read_csv(resolve(base, config["source"]["metrics_csv"])))
    acceptable_rating = int(config["acceptable_rating"])
    by_case: list[dict[str, Any]] = []
    adjudication_rows: list[dict[str, Any]] = []
    reviewer_results = {"reviewer_a": [], "reviewer_b": []}

    for question_id in sorted(reviewer_a):
        row_a = reviewer_a[question_id]
        row_b = reviewer_b[question_id]
        result_a = evaluate_review_row(row_a, acceptable_rating)
        result_b = evaluate_review_row(row_b, acceptable_rating)
        reviewer_results["reviewer_a"].append(result_a)
        reviewer_results["reviewer_b"].append(result_b)

        consensus = "pending"
        consensus_accepted = None
        if result_a["complete"] and result_b["complete"]:
            if result_a["accepted"] == result_b["accepted"]:
                consensus_accepted = bool(result_a["accepted"])
                consensus = "accepted" if consensus_accepted else "rejected"
            else:
                consensus = "adjudication_required"

        metric = metrics.get(question_id, {})
        case = {
            "question_id": question_id,
            "category": row_a.get("category", ""),
            "difficulty": row_a.get("difficulty", ""),
            "token_f1": float(metric.get("token_f1_relevancy") or 0),
            "grounding": float(metric.get("rule_based_grounding_score") or 0),
            "reviewer_a_complete": result_a["complete"],
            "reviewer_a_accepted": result_a["accepted"],
            "reviewer_a_mean": rounded(result_a["mean_rating"]),
            "reviewer_b_complete": result_b["complete"],
            "reviewer_b_accepted": result_b["accepted"],
            "reviewer_b_mean": rounded(result_b["mean_rating"]),
            "consensus": consensus,
            "consensus_accepted": consensus_accepted,
            "reviewer_a_failed_dimensions": " | ".join(result_a["failed_dimensions"]),
            "reviewer_b_failed_dimensions": " | ".join(result_b["failed_dimensions"]),
            "reviewer_a_failed_hard_gates": " | ".join(result_a["failed_hard_gates"]),
            "reviewer_b_failed_hard_gates": " | ".join(result_b["failed_hard_gates"]),
        }
        by_case.append(case)
        if consensus == "adjudication_required":
            adjudication_rows.append({
                **case,
                "question": row_a.get("question", ""),
                "answer": row_a.get("answer", ""),
                "reference_answer": row_a.get("reference_answer", ""),
                "reviewer_a_notes": row_a.get("review_notes", ""),
                "reviewer_b_notes": row_b.get("review_notes", ""),
                "adjudicated_accept": "",
                "adjudication_notes": "",
            })

    dimension_agreement = {}
    for field in RATING_FIELDS:
        pairs = []
        for question_id in sorted(reviewer_a):
            left = parse_rating(reviewer_a[question_id].get(field))
            right = parse_rating(reviewer_b[question_id].get(field))
            if isinstance(left, int) and isinstance(right, int):
                pairs.append((left, right))
        dimension_agreement[field] = _agreement(
            [left for left, _ in pairs], [right for _, right in pairs]
        )

    complete_pairs = [
        row for row in by_case
        if row["reviewer_a_complete"] and row["reviewer_b_complete"]
    ]
    overall_left = [bool(row["reviewer_a_accepted"]) for row in complete_pairs]
    overall_right = [bool(row["reviewer_b_accepted"]) for row in complete_pairs]
    overall_agreement = {
        "case_count": len(complete_pairs),
        "percent_agreement": rounded(
            sum(a == b for a, b in zip(overall_left, overall_right)) / len(complete_pairs)
        ) if complete_pairs else None,
        "cohen_kappa": rounded(cohen_kappa(overall_left, overall_right)),
    }

    decided = [row for row in by_case if row["consensus_accepted"] is not None]
    scores = [float(row["token_f1"]) for row in decided]
    labels = [bool(row["consensus_accepted"]) for row in decided]
    best_threshold, calibration_rows = calibrate_threshold(scores, labels)
    current_threshold = float(config["current_token_f1_threshold"])
    current_performance = confusion(scores, labels, current_threshold) if scores else None

    fields = tuple(by_case[0].keys()) if by_case else ("question_id",)
    write_csv(resolve(base, config["reports"]["human_validation_by_case_csv"]), by_case, fields)
    calibration_fields = (
        "threshold", "tp", "fp", "tn", "fn", "precision", "recall",
        "specificity", "balanced_accuracy", "accuracy", "f1",
    )
    write_csv(
        resolve(base, config["reports"]["calibration_csv"]),
        calibration_rows,
        calibration_fields,
    )
    adjudication_fields = tuple(adjudication_rows[0].keys()) if adjudication_rows else (
        "question_id", "category", "difficulty", "question", "answer",
        "reference_answer", "reviewer_a_accepted", "reviewer_b_accepted",
        "reviewer_a_notes", "reviewer_b_notes", "adjudicated_accept",
        "adjudication_notes",
    )
    write_csv(
        resolve(base, config["reports"]["adjudication_csv"]),
        adjudication_rows,
        adjudication_fields,
    )

    complete = len(complete_pairs) == len(by_case) and bool(by_case)
    ai_prescore = complete and all(
        reviewer_a[question_id].get("review_notes", "").startswith("AI pre-score")
        and reviewer_b[question_id].get("review_notes", "").startswith("AI pre-score")
        for question_id in reviewer_a
    )
    user_confirmed_prescore = complete and all(
        reviewer_a[question_id].get("review_notes", "").startswith(
            "User confirmed AI pre-score"
        )
        and reviewer_b[question_id].get("review_notes", "").startswith(
            "User confirmed AI pre-score"
        )
        for question_id in reviewer_a
    )
    summary = {
        "status": (
            "ai_prescore" if ai_prescore else
            "user_confirmed_prescore" if user_confirmed_prescore else
            "complete" if complete else "awaiting_review"
        ),
        "provenance": (
            "same_ai_prescore_in_both_packets" if ai_prescore else
            "same_ai_prescore_confirmed_by_user" if user_confirmed_prescore else
            "independent_human_review"
            if complete else "incomplete"
        ),
        "report_eligible": complete and not ai_prescore and not user_confirmed_prescore,
        "sample_size": len(by_case),
        "acceptable_rating": acceptable_rating,
        "completed_by_reviewer": {
            "reviewer_a": sum(result["complete"] for result in reviewer_results["reviewer_a"]),
            "reviewer_b": sum(result["complete"] for result in reviewer_results["reviewer_b"]),
        },
        "consensus_counts": dict(Counter(row["consensus"] for row in by_case)),
        "overall_agreement": overall_agreement,
        "dimension_agreement": dimension_agreement,
        "breakdown": {
            "category": _human_breakdown(by_case, "category"),
            "difficulty": _human_breakdown(by_case, "difficulty"),
        },
        "token_f1_calibration": {
            "eligible_consensus_cases": len(decided),
            "current_threshold": current_threshold,
            "current_threshold_performance": current_performance,
            "recommended_threshold": best_threshold,
            "selection_rule": "maximize balanced accuracy, then F1, precision, and threshold",
            "warning": (
                "Provisional only: both packets contain the same AI pre-score; do not report this threshold."
                if ai_prescore else
                "Provisional only: one user confirmed the same AI pre-score in both packets; independent human labels are still required."
                if user_confirmed_prescore else None if best_threshold is not None
                else "Need completed consensus labels containing both acceptable and unacceptable cases."
            ),
        },
    }
    write_json(resolve(base, config["reports"]["human_validation_summary_json"]), summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score two independent human-review packets.")
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--allow-incomplete", action="store_true",
        help="Return success while reviews are still incomplete.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = score_reviews(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] in {
        "complete", "ai_prescore", "user_confirmed_prescore"
    } or args.allow_incomplete else 2


if __name__ == "__main__":
    raise SystemExit(main())
