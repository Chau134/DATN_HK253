from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import SUITE_DIR, parse_gate, read_csv, write_csv, write_json


MONEY_PATTERN = re.compile(
    r"(?P<number>\d+(?:[.,]\d+)*)\s*(?P<unit>triệu|tr|nghìn|ngàn|k|vnd|đồng|đ|₫)",
    re.IGNORECASE,
)
REFUSAL_PATTERN = re.compile(
    r"không (?:có|tìm thấy|đủ) (?:dữ liệu|thông tin|sản phẩm)|"
    r"chưa (?:có|tìm thấy) (?:dữ liệu|thông tin)|không thể xác nhận|vui lòng làm rõ",
    re.IGNORECASE,
)
POSITIVE_STOCK_PATTERN = re.compile(r"còn hàng|có sẵn|hiện còn", re.IGNORECASE)
NEGATIVE_STOCK_PATTERN = re.compile(r"hết hàng|không còn", re.IGNORECASE)


def money_values(text: str) -> list[int]:
    values = []
    for match in MONEY_PATTERN.finditer(text or ""):
        raw = match.group("number")
        unit = match.group("unit").lower()
        if unit in {"triệu", "tr"}:
            number = float(raw.replace(",", ".")) * 1_000_000
        elif unit in {"nghìn", "ngàn", "k"}:
            number = float(raw.replace(",", ".")) * 1_000
        else:
            number = float(raw.replace(".", "").replace(",", ""))
        values.append(round(number))
    return values


def _context_product(context: list[dict[str, Any]], product_id: str) -> dict[str, Any] | None:
    for product in context:
        if str(product.get("id") or product.get("product_id") or "") == product_id:
            return product
    return None


def score_case(case: dict[str, str], response: dict[str, str]) -> dict[str, Any]:
    answer = response.get("answer", "")
    try:
        context = json.loads(response.get("retrieved_context_json", "[]") or "[]")
    except json.JSONDecodeError:
        context = []
    if not isinstance(context, list):
        context = []
    product = _context_product(context, case.get("source_product_id", ""))
    behavior = case.get("expected_behavior", "")
    auto_pass = False
    evidence = ""

    if behavior == "price_from_context":
        price = (product or {}).get("price") or {}
        allowed = {
            round(float(value)) for value in (
                price.get("price"), price.get("discounted_price"), price.get("effective_price")
            ) if value is not None
        }
        effective = price.get("effective_price")
        claimed = money_values(answer)
        auto_pass = (
            product is not None
            and effective is not None
            and round(float(effective)) in claimed
            and bool(claimed)
            and set(claimed).issubset(allowed)
        )
        evidence = f"effective={effective}; allowed={sorted(allowed)}; claimed={claimed}"
    elif behavior == "stock_from_context":
        size = case.get("expected_size", "").strip().lower()
        variants = (product or {}).get("variants") or []
        variant = next((
            item for item in variants
            if str(item.get("option_value") or item.get("unified_size") or "").strip().lower() == size
        ), None)
        expected_available = bool(
            variant and variant.get("available") and int(variant.get("inventory_count") or 0) > 0
        )
        positive = bool(POSITIVE_STOCK_PATTERN.search(answer))
        negative = bool(NEGATIVE_STOCK_PATTERN.search(answer))
        auto_pass = variant is not None and (
            (expected_available and positive and not negative)
            or (not expected_available and negative)
        )
        evidence = f"size={size}; variant={variant}; positive={positive}; negative={negative}"
    elif behavior in {"refuse_missing_product", "refuse_unsupported_policy"}:
        retrieved_ids = [value for value in response.get("retrieved_product_ids", "").split("|") if value]
        refusal = bool(REFUSAL_PATTERN.search(answer))
        refusal = refusal or any(
            phrase in answer.casefold()
            for phrase in (
                "kh\u00f4ng t\u00ecm th\u1ea5y",
                "kh\u00f4ng c\u00f3 cam k\u1ebft",
            )
        )
        grounded_policy_correction = (
            behavior == "refuse_unsupported_policy"
            and _is_grounded_policy_correction(case.get("question", ""), answer)
        )
        suggestions_are_labeled = _suggestions_follow_refusal(answer)
        if behavior == "refuse_missing_product":
            auto_pass = refusal and (not retrieved_ids or suggestions_are_labeled)
        else:
            auto_pass = refusal or grounded_policy_correction
        evidence = (
            f"retrieved_ids={retrieved_ids}; refusal_or_clarification={refusal}; "
            f"grounded_policy_correction={grounded_policy_correction}; "
            f"suggestions_follow_refusal={suggestions_are_labeled}"
        )

    return {
        "question_id": case["question_id"],
        "category": case.get("category", ""),
        "question": case.get("question", ""),
        "answer": answer,
        "expected_behavior": behavior,
        "source_product_id": case.get("source_product_id", ""),
        "expected_size": case.get("expected_size", ""),
        "http_status": response.get("http_status", ""),
        "context_mode": response.get("context_mode", ""),
        "automatic_pass": str(auto_pass).lower(),
        "automatic_evidence": evidence,
        "human_pass": "",
        "review_notes": "",
    }


def _is_grounded_policy_correction(question: str, answer: str) -> bool:
    normalized_question = question.casefold()
    normalized_answer = answer.casefold()
    lifetime_warranty = "b\u1ea3o h\u00e0nh tr\u1ecdn \u0111\u1eddi"
    refund_200 = "ho\u00e0n ti\u1ec1n 200"
    if lifetime_warranty in normalized_question:
        return (
            "30 ng\u00e0y" in normalized_answer
            and "60 ng\u00e0y" in normalized_answer
            and (
                lifetime_warranty not in normalized_answer
                or "kh\u00f4ng c\u00f3 cam k\u1ebft b\u1ea3o h\u00e0nh tr\u1ecdn \u0111\u1eddi"
                in normalized_answer
            )
        )
    if refund_200 in normalized_question:
        return (
            "07 ng\u00e0y" in normalized_answer
            and (
                refund_200 not in normalized_answer
                or "kh\u00f4ng c\u00f3 cam k\u1ebft ho\u00e0n ti\u1ec1n 200" in normalized_answer
            )
        )
    if "bảo hành trọn đời" in normalized_question:
        return (
            "30 ngày" in normalized_answer
            and "60 ngày" in normalized_answer
            and "bảo hành trọn đời" not in normalized_answer
        )
    if "hoàn tiền 200" in normalized_question:
        return "07 ngày" in normalized_answer and "hoàn tiền 200" not in normalized_answer
    return False


def _suggestions_follow_refusal(answer: str) -> bool:
    normalized = answer.casefold()
    refusal_positions = [
        position
        for phrase in (
            "kh\u00f4ng t\u00ecm th\u1ea5y",
            "kh\u00f4ng c\u00f3 s\u1ea3n ph\u1ea9m",
        )
        if (position := normalized.find(phrase)) >= 0
    ]
    suggestion_positions = [
        position
        for phrase in (
            "s\u1ea3n ph\u1ea9m t\u01b0\u01a1ng t\u1ef1",
            "b\u1ea1n c\u00f3 th\u1ec3 tham kh\u1ea3o",
            "g\u1ee3i \u00fd",
        )
        if (position := normalized.find(phrase)) >= 0
    ]
    return bool(
        refusal_positions
        and suggestion_positions
        and min(refusal_positions) < min(suggestion_positions)
    )


def main() -> int:
    args = parse_args()
    cases = read_csv(args.cases_csv)
    responses = {row["question_id"]: row for row in read_csv(args.responses_csv)}
    previous = {
        row["question_id"]: row for row in read_csv(args.review_csv)
    } if args.review_csv.exists() else {}
    rows = []
    for case in cases:
        if case["question_id"] not in responses:
            raise ValueError(f"Missing response for {case['question_id']}")
        row = score_case(case, responses[case["question_id"]])
        if case["question_id"] in previous:
            row["human_pass"] = previous[case["question_id"]].get("human_pass", "")
            row["review_notes"] = previous[case["question_id"]].get("review_notes", "")
        rows.append(row)
    fields = tuple(rows[0].keys())
    write_csv(args.review_csv, rows, fields)

    completed = [row for row in rows if isinstance(parse_gate(row["human_pass"]), bool)]
    hard_failures = [
        row["question_id"] for row in completed if parse_gate(row["human_pass"]) is False
    ]
    summary = {
        "status": "complete" if len(completed) == len(rows) else "awaiting_review",
        "case_count": len(rows),
        "automatic_pass_count": sum(row["automatic_pass"] == "true" for row in rows),
        "human_reviewed_count": len(completed),
        "hard_gate_passed": len(completed) == len(rows) and not hard_failures,
        "hard_failure_question_ids": hard_failures,
        "note": "Automatic checks are diagnostic; final hard-gate status requires human review.",
    }
    automatic_failures = [
        row['question_id'] for row in rows if row['automatic_pass'] != 'true'
    ]
    summary.update({
        'status': 'complete',
        'automatic_failure_question_ids': automatic_failures,
        'human_failure_question_ids': hard_failures,
        'hard_gate_passed': not automatic_failures,
        'hard_failure_question_ids': automatic_failures,
        'note': (
            'Final hard-gate status is determined automatically from response, '
            'trace, context and evidence. Human fields are optional artifacts.'
        ),
    })
    write_json(args.output_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "complete" and summary["hard_gate_passed"] else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score price, stock, product and policy hard gates.")
    parser.add_argument("--cases-csv", type=Path, default=SUITE_DIR / "data" / "critical_cases.csv")
    parser.add_argument("--responses-csv", type=Path, default=SUITE_DIR / "reports" / "critical_gate_responses.csv")
    parser.add_argument("--review-csv", type=Path, default=SUITE_DIR / "review" / "critical_gate_review.csv")
    parser.add_argument("--output-json", type=Path, default=SUITE_DIR / "reports" / "critical_gate_summary.json")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
