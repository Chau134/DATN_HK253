from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPT_DIR.parent
EVAL_DIR = SUITE_DIR.parent / "conversational_ai_evaluation"

QUESTION_FIELDS = (
    "question_id", "session_id", "turn_index", "category", "question",
    "expected_answer_type", "entity_ids", "depends_on_history", "difficulty",
    "manual_status", "notes", "reviewer", "reviewed_at", "review_notes",
)
REFERENCE_FIELDS = (
    "question_id", "reference_answer", "answer_must_include",
    "answer_must_not_include", "reference_source_ids", "review_status", "notes",
    "reviewer", "reviewed_at", "review_notes",
)
EVIDENCE_FIELDS = (
    "question_id", "evidence_id", "source_id", "evidence_text", "evidence_role",
    "required_level", "notes", "review_status", "reviewer", "reviewed_at",
    "review_notes",
)

KEEP_QUOTAS = {
    "product_factual": 16,
    "product_comparison": 8,
    "product_recommendation": 14,
    "followup_ordinal": 10,
    "filter_refinement": 10,
    "shop_knowledge": 8,
    "unanswerable": 2,
}

GENERIC_FORBIDDEN = (
    "bịa product_id không có trong danh sách trả về | "
    "lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt"
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


def _stable_sample(rows: list[dict[str, str]], count: int, seed: int) -> list[dict[str, str]]:
    ordered = sorted(rows, key=lambda row: row["question_id"])
    random.Random(seed).shuffle(ordered)
    return ordered[:count]


def _select_factual(rows: list[dict[str, str]], count: int, seed: int) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row.get("expected_answer_type", "unknown")].append(row)
    selected: list[dict[str, str]] = []
    rng = random.Random(seed)
    for key in sorted(groups):
        values = sorted(groups[key], key=lambda row: row["question_id"])
        rng.shuffle(values)
        selected.extend(values[: min(4, len(values))])
    if len(selected) < count:
        selected_ids = {row["question_id"] for row in selected}
        remaining = [row for row in rows if row["question_id"] not in selected_ids]
        selected.extend(_stable_sample(remaining, count - len(selected), seed + 1))
    return selected[:count]


def select_legacy_questions(
    questions: list[dict[str, str]], seed: int
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in questions:
        groups[row["category"]].append(row)
    unknown = sorted(set(groups) - set(KEEP_QUOTAS))
    if unknown:
        raise ValueError(f"No master-suite quota for categories: {unknown}")

    selected: list[dict[str, str]] = []
    for index, (category, quota) in enumerate(KEEP_QUOTAS.items()):
        values = groups.get(category, [])
        if len(values) < quota:
            raise ValueError(f"Category {category} has {len(values)} rows, needs {quota}")
        if category == "product_factual":
            picked = _select_factual(values, quota, seed + index)
        elif category in {"followup_ordinal", "filter_refinement"}:
            # Preserve every turn of all multi-turn sessions.
            picked = sorted(values, key=lambda row: (row["session_id"], int(row["turn_index"])))
        else:
            picked = _stable_sample(values, quota, seed + index)
        selected.extend(picked)

    selected_ids = {row["question_id"] for row in selected}
    dropped = [row for row in questions if row["question_id"] not in selected_ids]
    if len(selected) != 68 or len(dropped) != 12:
        raise ValueError(f"Expected 68 selected and 12 dropped, got {len(selected)} and {len(dropped)}")
    return selected, dropped


def _context_by_question(responses: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in responses:
        try:
            value = json.loads(row.get("retrieved_context_json", "[]") or "[]")
        except json.JSONDecodeError:
            value = []
        result[row["question_id"]] = value if isinstance(value, list) else []
    return result


def _approved_answers(review_rows: list[dict[str, str]]) -> dict[str, str]:
    result = {}
    for row in review_rows:
        if row.get("human_pass", "").strip().lower() != "pass":
            raise ValueError(f"Critical case {row.get('question_id')} is not human-approved")
        result[row["question_id"]] = row.get("answer", "").strip()
    return result


def _critical_reference(
    case: dict[str, str], answer: str
) -> dict[str, str]:
    behavior = case["expected_behavior"]
    required: list[str] = []
    forbidden = GENERIC_FORBIDDEN
    if behavior == "price_from_context":
        required = ["giá hiện tại", "VND"]
        forbidden += " | nêu giá không có trong context"
    elif behavior == "stock_from_context":
        required = [f"size {case['expected_size']}", "còn hàng"]
        forbidden += " | suy tồn kho size từ total_stock"
    elif behavior == "refuse_missing_product":
        requested = case.get("question", "")
        required = ["không tìm thấy"]
        if "MC-999999" in requested:
            required.append("MC-999999")
            answer = (
                "Không, shop không tìm thấy mã MC-999999 trong danh mục hiện tại. "
                "Shop có thể gợi ý riêng các sản phẩm tương tự nếu bạn muốn."
            )
        else:
            required.append("Sao Hỏa")
            answer = (
                "Không, shop không tìm thấy Áo khoác Sao Hỏa phiên bản 2099 trong danh mục hiện tại. "
                "Shop có thể gợi ý riêng các sản phẩm tương tự nếu bạn muốn."
            )
        forbidden += " | khẳng định sản phẩm được hỏi tồn tại"
    elif behavior == "refuse_unsupported_policy":
        required = ["Không"]
        if "bảo hành" in case.get("question", ""):
            required.extend(["30 ngày", "60 ngày"])
            forbidden += " | khẳng định bảo hành trọn đời"
        else:
            required.append("07 ngày")
            forbidden += " | khẳng định hoàn tiền 200%"
    return {
        "question_id": case["question_id"],
        "reference_answer": answer,
        "answer_must_include": " | ".join(required),
        "answer_must_not_include": forbidden,
        "reference_source_ids": case.get("source_product_id", ""),
        "review_status": "pending",
        "notes": "master_v2_proposal_from_human_approved_critical_run",
        "reviewer": "",
        "reviewed_at": "",
        "review_notes": "",
    }


def _critical_evidence(
    case: dict[str, str], context: list[dict[str, Any]]
) -> dict[str, str]:
    behavior = case["expected_behavior"]
    source_id = case.get("source_product_id", "")
    role = "primary" if source_id else "constraint"
    if behavior == "price_from_context":
        product = next((item for item in context if str(item.get("id")) == source_id), {})
        price = product.get("price") or {}
        evidence_text = (
            f"effective_price={price.get('effective_price')}; "
            f"price={price.get('price')}; discounted_price={price.get('discounted_price')}"
        )
    elif behavior == "stock_from_context":
        product = next((item for item in context if str(item.get("id")) == source_id), {})
        size = case.get("expected_size", "").casefold()
        variant = next(
            (
                item for item in (product.get("variants") or [])
                if str(item.get("unified_size") or item.get("option_value") or "").casefold() == size
            ),
            {},
        )
        evidence_text = (
            f"size={case.get('expected_size')}; available={variant.get('available')}; "
            f"active={variant.get('active')}; inventory_count={variant.get('inventory_count')}"
        )
    elif behavior == "refuse_missing_product":
        evidence_text = (
            "Normalized exact title/product-code lookup returns no catalog product; "
            "semantic neighbors may only be labeled as optional similar suggestions"
        )
    elif "bảo hành" in case.get("question", ""):
        evidence_text = (
            "Official footer-aligned policy: clothing warranty 30 days; footwear warranty "
            "60 days; no lifetime-warranty commitment"
        )
    else:
        evidence_text = (
            "Official footer-aligned return policy: eligible requests within 07 days; "
            "no unconditional 200% refund commitment"
        )
    return {
        "question_id": case["question_id"],
        "evidence_id": f"{case['question_id']}-e1",
        "source_id": source_id,
        "evidence_text": evidence_text,
        "evidence_role": role,
        "required_level": "must_have",
        "notes": f"critical_behavior={behavior}",
        "review_status": "pending",
        "reviewer": "",
        "reviewed_at": "",
        "review_notes": "",
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    legacy_questions = read_csv(args.legacy_questions)
    legacy_references = {row["question_id"]: row for row in read_csv(args.legacy_references)}
    legacy_evidence = read_csv(args.legacy_evidence)
    product_rows = read_csv(args.product_snapshot)
    critical_cases = read_csv(args.critical_cases)
    critical_answers = _approved_answers(read_csv(args.critical_review))
    critical_context = _context_by_question(read_csv(args.critical_responses))

    selected, dropped = select_legacy_questions(legacy_questions, args.seed)
    selected_ids = {row["question_id"] for row in selected}
    selected_references = [legacy_references[row["question_id"]] for row in selected]
    selected_evidence = [row for row in legacy_evidence if row["question_id"] in selected_ids]

    critical_questions = []
    critical_references = []
    critical_evidence = []
    for case in critical_cases:
        critical_questions.append({
            field: case.get(field, "") for field in QUESTION_FIELDS
        } | {
            "notes": f"{case.get('notes', '')} | master_v2_critical=true",
            "reviewer": case.get("reviewer", "user-approved"),
            "review_notes": case.get("review_notes", "Critical test design approved on 2026-08-26"),
        })
        critical_references.append(_critical_reference(case, critical_answers[case["question_id"]]))
        critical_evidence.append(_critical_evidence(case, critical_context[case["question_id"]]))

    questions = [*selected, *critical_questions]
    references = [*selected_references, *critical_references]
    evidence = [*selected_evidence, *critical_evidence]
    if len(questions) != 80 or len(references) != 80:
        raise ValueError(f"Master suite must contain 80 questions/references, got {len(questions)}/{len(references)}")
    if len({row['question_id'] for row in questions}) != 80:
        raise ValueError("Master suite contains duplicate question IDs")

    write_csv(args.output_dir / "question_set.csv", questions, QUESTION_FIELDS)
    write_csv(args.output_dir / "reference_answers.csv", references, REFERENCE_FIELDS)
    write_csv(args.output_dir / "required_evidence.csv", evidence, EVIDENCE_FIELDS)

    context_products = {
        str(product.get("id")): product
        for values in critical_context.values()
        for product in values
        if isinstance(product, dict) and product.get("id") is not None
    }
    enriched_products = []
    for row in product_rows:
        enriched = dict(row)
        context_product = context_products.get(row.get("product_id", ""), {})
        price = context_product.get("price") or {}
        enriched.update({
            "price": price.get("effective_price", ""),
            "list_price": price.get("price", ""),
            "sale_price": price.get("discounted_price", ""),
            "variants_json": json.dumps(
                context_product.get("variants") or [],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        })
        enriched_products.append(enriched)
    product_fields = [
        *product_rows[0].keys(),
        "price",
        "list_price",
        "sale_price",
        "variants_json",
    ]
    write_csv(args.output_dir / "product_snapshot.csv", enriched_products, product_fields)

    manifest = []
    selected_order = {row["question_id"]: index for index, row in enumerate(questions, start=1)}
    for row in legacy_questions:
        included = row["question_id"] in selected_ids
        manifest.append({
            "question_id": row["question_id"],
            "origin": "legacy_80",
            "category": row["category"],
            "difficulty": row["difficulty"],
            "included": str(included).lower(),
            "master_order": selected_order.get(row["question_id"], ""),
            "reason": "selected_by_fixed_quota_seed" if included else "removed_to_make_room_for_critical_slice",
        })
    for row in critical_cases:
        manifest.append({
            "question_id": row["question_id"],
            "origin": "critical_12",
            "category": row["category"],
            "difficulty": row["difficulty"],
            "included": "true",
            "master_order": selected_order[row["question_id"]],
            "reason": "mandatory_critical_slice",
        })
    write_csv(
        args.output_dir / "selection_manifest.csv",
        manifest,
        ("question_id", "origin", "category", "difficulty", "included", "master_order", "reason"),
    )

    summary = {
        "version": "master-80-v2",
        "seed": args.seed,
        "question_count": len(questions),
        "legacy_selected": len(selected),
        "legacy_dropped": len(dropped),
        "critical_selected": len(critical_questions),
        "category_counts": dict(sorted(Counter(row["category"] for row in questions).items())),
        "difficulty_counts": dict(sorted(Counter(row["difficulty"] for row in questions).items())),
        "pending_question_count": sum(row.get("manual_status") != "approved" for row in questions),
        "pending_reference_count": sum(row.get("review_status") != "approved" for row in references),
        "pending_evidence_row_count": sum(row.get("review_status") != "approved" for row in evidence),
        "dropped_question_ids": sorted(row["question_id"] for row in dropped),
    }
    (args.output_dir / "master_suite_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a fixed 80-case master suite containing all 12 critical cases.")
    parser.add_argument("--seed", type=int, default=252)
    parser.add_argument("--legacy-questions", type=Path, default=EVAL_DIR / "data" / "question_set.csv")
    parser.add_argument("--legacy-references", type=Path, default=EVAL_DIR / "data" / "reference_answers.csv")
    parser.add_argument("--legacy-evidence", type=Path, default=EVAL_DIR / "data" / "required_evidence.csv")
    parser.add_argument("--product-snapshot", type=Path, default=EVAL_DIR / "data" / "product_snapshot.csv")
    parser.add_argument("--critical-cases", type=Path, default=SUITE_DIR / "data" / "critical_cases.csv")
    parser.add_argument("--critical-review", type=Path, default=SUITE_DIR / "review" / "critical_gate_review.csv")
    parser.add_argument("--critical-responses", type=Path, default=SUITE_DIR / "reports" / "critical_gate_responses.csv")
    parser.add_argument("--output-dir", type=Path, default=SUITE_DIR / "data" / "master_80")
    return parser.parse_args()


def main() -> int:
    summary = build(parse_args())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
