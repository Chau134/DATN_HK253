from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPT_DIR.parent

RATING_FIELDS = (
    "factual_correctness",
    "groundedness",
    "answer_relevancy",
    "completeness",
    "task_success",
    "context_retention",
    "refusal_correctness",
    "helpfulness",
)

HARD_GATE_FIELDS = (
    "critical_price",
    "critical_stock",
    "critical_product_exists",
    "critical_policy",
    "critical_clarification_or_refusal",
)

CONTEXT_FIELDS = (
    "review_order",
    "question_id",
    "session_id",
    "turn_index",
    "category",
    "difficulty",
    "conversation_history",
    "question",
    "answer",
    "reference_answer",
    "answer_must_include",
    "answer_must_not_include",
    "required_evidence",
    "retrieved_context",
)

REVIEW_FIELDS = CONTEXT_FIELDS[:-1] + RATING_FIELDS + HARD_GATE_FIELDS + (CONTEXT_FIELDS[-1],) + (
    "review_notes",
)

PRICE_PATTERN = re.compile(
    r"\b(giá|vnd|đồng|nghìn|triệu|rẻ|đắt|ngân sách)\b|₫", re.IGNORECASE
)
STOCK_PATTERN = re.compile(
    r"\b(tồn kho|còn hàng|hết hàng|còn size|hết size|số lượng)\b", re.IGNORECASE
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_config(path: Path | None = None) -> tuple[dict[str, Any], Path]:
    config_path = path or SUITE_DIR / "config.json"
    config = read_json(config_path)
    return config, config_path.parent


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def parse_rating(value: str | None) -> int | None | str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    if normalized in {"na", "n/a", "not_applicable", "không áp dụng"}:
        return "NA"
    try:
        rating = int(normalized)
    except ValueError:
        return None
    return rating if 1 <= rating <= 5 else None


def parse_gate(value: str | None) -> bool | None | str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    if normalized in {"na", "n/a", "not_applicable", "không áp dụng"}:
        return "NA"
    if normalized in {"pass", "true", "1", "đạt", "yes"}:
        return True
    if normalized in {"fail", "false", "0", "không đạt", "no"}:
        return False
    return None


def select_stratified(
    rows: list[dict[str, str]], sample_size: int, seed: int
) -> list[dict[str, str]]:
    """Select a deterministic approximately proportional category x difficulty sample."""
    if sample_size <= 0 or not rows:
        return []
    sample_size = min(sample_size, len(rows))
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row.get("category", "unknown"), row.get("difficulty", "unknown"))
        groups[key].append(row)

    rng = random.Random(seed)
    for key in sorted(groups):
        rng.shuffle(groups[key])

    allocations = {key: 0 for key in groups}
    if sample_size >= len(groups):
        for key in groups:
            allocations[key] = 1

    total = len(rows)
    while sum(allocations.values()) < sample_size:
        candidates = [
            key for key, values in groups.items()
            if allocations[key] < len(values)
        ]
        if not candidates:
            break
        key = max(
            candidates,
            key=lambda item: (
                sample_size * len(groups[item]) / total - allocations[item],
                len(groups[item]) - allocations[item],
                tuple(reversed(item)),
            ),
        )
        allocations[key] += 1

    selected: list[dict[str, str]] = []
    for key in sorted(groups):
        selected.extend(groups[key][: allocations[key]])
    rng.shuffle(selected)
    return selected


def default_applicability(row: dict[str, str]) -> dict[str, str]:
    category = row.get("category", "")
    depends_on_history = row.get("depends_on_history", "").strip().lower() == "true"
    text = f"{row.get('question', '')} {row.get('answer', '')}"
    task_categories = {
        "product_comparison",
        "product_recommendation",
        "followup_ordinal",
        "filter_refinement",
    }
    return {
        "task_success": "" if category in task_categories else "NA",
        "context_retention": "" if depends_on_history else "NA",
        "refusal_correctness": (
            "" if category in {"unanswerable", "critical_product", "critical_policy"}
            else "NA"
        ),
        "critical_price": (
            "" if category == "critical_price" or PRICE_PATTERN.search(text) else "NA"
        ),
        "critical_stock": (
            "" if category == "critical_stock" or STOCK_PATTERN.search(text) else "NA"
        ),
        "critical_product_exists": (
            "" if category in {
                "product_factual", "product_comparison", "product_recommendation",
                "followup_ordinal", "filter_refinement", "critical_price",
                "critical_stock", "critical_product",
            } else "NA"
        ),
        "critical_policy": (
            "" if category in {"shop_knowledge", "critical_policy"} else "NA"
        ),
        "critical_clarification_or_refusal": (
            "" if category in {"unanswerable", "critical_product", "critical_policy"}
            else "NA"
        ),
    }


def evaluate_review_row(
    row: dict[str, str], acceptable_rating: int = 4
) -> dict[str, Any]:
    ratings = {field: parse_rating(row.get(field)) for field in RATING_FIELDS}
    gates = {field: parse_gate(row.get(field)) for field in HARD_GATE_FIELDS}
    missing_ratings = [field for field, value in ratings.items() if value is None]
    missing_gates = [field for field, value in gates.items() if value is None]
    complete = not missing_ratings and not missing_gates
    applicable_ratings = [value for value in ratings.values() if isinstance(value, int)]
    applicable_gates = [value for value in gates.values() if isinstance(value, bool)]
    accepted = (
        complete
        and bool(applicable_ratings)
        and all(value >= acceptable_rating for value in applicable_ratings)
        and all(applicable_gates)
    )
    return {
        "complete": complete,
        "accepted": accepted if complete else None,
        "mean_rating": (
            sum(applicable_ratings) / len(applicable_ratings)
            if applicable_ratings else None
        ),
        "ratings": ratings,
        "gates": gates,
        "missing_fields": missing_ratings + missing_gates,
        "failed_dimensions": [
            field for field, value in ratings.items()
            if isinstance(value, int) and value < acceptable_rating
        ],
        "failed_hard_gates": [
            field for field, value in gates.items() if value is False
        ],
    }


def cohen_kappa(left: list[bool], right: list[bool]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    left_true = sum(left) / len(left)
    right_true = sum(right) / len(right)
    expected = left_true * right_true + (1 - left_true) * (1 - right_true)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1 - expected)


def confusion(scores: list[float], labels: list[bool], threshold: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for score, label in zip(scores, labels):
        predicted = score >= threshold
        if predicted and label:
            tp += 1
        elif predicted:
            fp += 1
        elif label:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    accuracy = (tp + tn) / len(labels) if labels else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": (recall + specificity) / 2,
        "accuracy": accuracy,
        "f1": f1,
    }


def calibrate_threshold(
    scores: list[float], labels: list[bool]
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not scores or len(scores) != len(labels) or len(set(labels)) < 2:
        return None, []
    candidates = sorted({0.0, 1.0, *scores})
    results = [confusion(scores, labels, threshold) for threshold in candidates]
    best = max(
        results,
        key=lambda row: (
            row["balanced_accuracy"],
            row["f1"],
            row["precision"],
            row["threshold"],
        ),
    )
    return best, results


def rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None
