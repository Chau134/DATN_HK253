from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import read_csv_rows, write_csv_rows  # noqa: E402


REVIEW_DIR = SCRIPT_DIR.parent / "review"
REVIEW_CSV = REVIEW_DIR / "ground_truth_review.csv"
REVIEW_MD = REVIEW_DIR / "ground_truth_review.md"
REVIEW_SUMMARY = REVIEW_DIR / "ground_truth_review_summary.json"

QUESTION_FIELDS = [
    "question_id",
    "session_id",
    "turn_index",
    "category",
    "question",
    "expected_answer_type",
    "entity_ids",
    "depends_on_history",
    "difficulty",
    "manual_status",
    "notes",
    "reviewer",
    "reviewed_at",
    "review_notes",
]
REFERENCE_FIELDS = [
    "question_id",
    "reference_answer",
    "answer_must_include",
    "answer_must_not_include",
    "reference_source_ids",
    "review_status",
    "notes",
    "reviewer",
    "reviewed_at",
    "review_notes",
]
EVIDENCE_FIELDS = [
    "question_id",
    "evidence_id",
    "source_id",
    "evidence_text",
    "evidence_role",
    "required_level",
    "notes",
    "review_status",
    "reviewer",
    "reviewed_at",
    "review_notes",
]
REVIEW_FIELDS = [
    "question_id",
    "session_id",
    "turn_index",
    "category",
    "difficulty",
    "depends_on_history",
    "expected_answer_type",
    "question",
    "entity_ids",
    "reference_answer",
    "answer_must_include",
    "answer_must_not_include",
    "reference_source_ids",
    "evidence_json",
    "source_products_json",
    "review_warnings",
    "question_status",
    "reference_status",
    "evidence_status",
    "reviewer",
    "review_notes",
    "question_notes",
    "reference_notes",
]

DECISION_STATUSES = {"pending", "approved", "needs_revision", "rejected"}
EVIDENCE_STATUSES = DECISION_STATUSES | {"not_applicable"}
EVIDENCE_ROLES = {"primary", "supporting", "constraint"}
EVIDENCE_LEVELS = {"must_have", "nice_to_have"}


def split_ids(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").replace(";", "|").split("|") if item.strip()]


def _by_unique_id(rows: list[dict[str, str]], field: str, label: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(field, "").strip()
        if not value:
            raise ValueError(f"{label} contains an empty {field}")
        if value in result:
            raise ValueError(f"duplicate {label} {field}: {value}")
        result[value] = row
    return result


def _evidence_status(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "not_applicable"
    statuses = {row.get("review_status", "pending").strip() or "pending" for row in rows}
    return statuses.pop() if len(statuses) == 1 else "needs_revision"


def _compact_product(product: dict[str, str]) -> dict[str, str]:
    return {
        key: product.get(key, "")
        for key in (
            "product_id",
            "product_name_vi",
            "product_name",
            "category",
            "brand",
            "color",
            "material",
            "gender",
            "description",
            "version",
        )
    }


def _editable_evidence(row: dict[str, str]) -> dict[str, str]:
    return {
        key: row.get(key, "")
        for key in (
            "evidence_id",
            "source_id",
            "evidence_text",
            "evidence_role",
            "required_level",
            "notes",
        )
    }


def _review_warnings(
    question: dict[str, str],
    reference: dict[str, str],
    evidence_rows: list[dict[str, str]],
    products: list[dict[str, str]],
) -> list[str]:
    warnings: list[str] = []
    searchable_text = f"{question.get('question', '')} {reference.get('reference_answer', '')}".lower()
    catalog_has_price = any(
        any(product.get(field, "").strip() for field in ("price", "list_price", "sale_price"))
        for product in products
    )
    if any(token in searchable_text for token in ("giá", "rẻ", "ngân sách")) and not catalog_has_price:
        warnings.append("snapshot_missing_price_for_price_intent")
    if question.get("depends_on_history", "").strip().lower() == "true" and not split_ids(
        reference.get("reference_source_ids")
    ):
        warnings.append("dynamic_history_expectation_requires_manual_check")
    if question.get("category") == "product_recommendation" and len(
        split_ids(reference.get("reference_source_ids"))
    ) <= 1:
        warnings.append("recommendation_reference_set_is_not_exhaustive")
    if question.get("category") == "unanswerable" and not evidence_rows:
        warnings.append("unanswerable_has_no_explicit_constraint_evidence")
    return warnings


def build_review_rows(
    questions: list[dict[str, str]],
    references: list[dict[str, str]],
    evidence: list[dict[str, str]],
    products: list[dict[str, str]],
) -> list[dict[str, str]]:
    question_by_id = _by_unique_id(questions, "question_id", "question")
    reference_by_id = _by_unique_id(references, "question_id", "reference")
    product_by_id = _by_unique_id(products, "product_id", "product")
    evidence_by_question: dict[str, list[dict[str, str]]] = defaultdict(list)
    evidence_ids: set[str] = set()
    for row in evidence:
        evidence_id = row.get("evidence_id", "").strip()
        if not evidence_id:
            raise ValueError("evidence contains an empty evidence_id")
        if evidence_id in evidence_ids:
            raise ValueError(f"duplicate evidence_id: {evidence_id}")
        evidence_ids.add(evidence_id)
        evidence_by_question[row.get("question_id", "")].append(row)

    missing_references = sorted(set(question_by_id) - set(reference_by_id))
    orphan_references = sorted(set(reference_by_id) - set(question_by_id))
    orphan_evidence = sorted(set(evidence_by_question) - set(question_by_id))
    if missing_references or orphan_references or orphan_evidence:
        raise ValueError(
            "ground-truth join mismatch: "
            f"missing_references={missing_references}, "
            f"orphan_references={orphan_references}, orphan_evidence={orphan_evidence}"
        )

    result: list[dict[str, str]] = []
    for question in questions:
        question_id = question["question_id"]
        reference = reference_by_id[question_id]
        evidence_rows = evidence_by_question.get(question_id, [])
        source_ids = list(
            dict.fromkeys(
                [
                    *split_ids(question.get("entity_ids")),
                    *split_ids(reference.get("reference_source_ids")),
                    *[row.get("source_id", "").strip() for row in evidence_rows],
                ]
            )
        )
        source_products = [
            _compact_product(product_by_id[source_id])
            for source_id in source_ids
            if source_id and source_id in product_by_id
        ]
        result.append(
            {
                "question_id": question_id,
                "session_id": question.get("session_id", ""),
                "turn_index": question.get("turn_index", ""),
                "category": question.get("category", ""),
                "difficulty": question.get("difficulty", ""),
                "depends_on_history": question.get("depends_on_history", ""),
                "expected_answer_type": question.get("expected_answer_type", ""),
                "question": question.get("question", ""),
                "entity_ids": question.get("entity_ids", ""),
                "reference_answer": reference.get("reference_answer", ""),
                "answer_must_include": reference.get("answer_must_include", ""),
                "answer_must_not_include": reference.get("answer_must_not_include", ""),
                "reference_source_ids": reference.get("reference_source_ids", ""),
                "evidence_json": json.dumps(
                    [_editable_evidence(row) for row in evidence_rows],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "source_products_json": json.dumps(
                    source_products, ensure_ascii=False, separators=(",", ":")
                ),
                "review_warnings": "|".join(
                    _review_warnings(question, reference, evidence_rows, products)
                ),
                "question_status": question.get("manual_status", "pending") or "pending",
                "reference_status": reference.get("review_status", "pending") or "pending",
                "evidence_status": _evidence_status(evidence_rows),
                "reviewer": question.get("reviewer") or reference.get("reviewer") or "",
                "review_notes": question.get("review_notes") or reference.get("review_notes") or "",
                "question_notes": question.get("notes", ""),
                "reference_notes": reference.get("notes", ""),
            }
        )
    return result


def parse_evidence(row: dict[str, str]) -> list[dict[str, str]]:
    try:
        value = json.loads(row.get("evidence_json", "[]") or "[]")
    except json.JSONDecodeError as error:
        raise ValueError(f"{row.get('question_id')}: evidence_json is invalid: {error}") from error
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{row.get('question_id')}: evidence_json must be a JSON array of objects")
    return [{str(key): str(item.get(key, "")) for key in _editable_evidence({})} for item in value]


def validate_review_rows(
    rows: list[dict[str, str]],
    products: list[dict[str, str]],
    *,
    expected_question_ids: set[str] | None = None,
    require_complete: bool = False,
) -> list[str]:
    errors: list[str] = []
    product_ids = {row.get("product_id", "").strip() for row in products}
    seen_question_ids: set[str] = set()
    seen_evidence_ids: set[str] = set()

    for index, row in enumerate(rows, start=2):
        question_id = row.get("question_id", "").strip()
        prefix = question_id or f"CSV row {index}"
        if not question_id:
            errors.append(f"CSV row {index}: missing question_id")
            continue
        if question_id in seen_question_ids:
            errors.append(f"{prefix}: duplicate question_id")
        seen_question_ids.add(question_id)

        for field in ("session_id", "category", "expected_answer_type", "question", "reference_answer"):
            if not row.get(field, "").strip():
                errors.append(f"{prefix}: missing {field}")

        question_status = row.get("question_status", "").strip()
        reference_status = row.get("reference_status", "").strip()
        evidence_status = row.get("evidence_status", "").strip()
        if question_status not in DECISION_STATUSES:
            errors.append(f"{prefix}: invalid question_status={question_status!r}")
        if reference_status not in DECISION_STATUSES:
            errors.append(f"{prefix}: invalid reference_status={reference_status!r}")
        if evidence_status not in EVIDENCE_STATUSES:
            errors.append(f"{prefix}: invalid evidence_status={evidence_status!r}")

        try:
            evidence_rows = parse_evidence(row)
        except ValueError as error:
            errors.append(str(error))
            evidence_rows = []

        if evidence_rows and evidence_status == "not_applicable":
            errors.append(f"{prefix}: evidence_status cannot be not_applicable when evidence exists")
        if not evidence_rows and evidence_status != "not_applicable":
            errors.append(f"{prefix}: evidence_status must be not_applicable when evidence is empty")

        ids_to_check = [*split_ids(row.get("entity_ids")), *split_ids(row.get("reference_source_ids"))]
        for evidence_row in evidence_rows:
            evidence_id = evidence_row.get("evidence_id", "").strip()
            if not evidence_id:
                errors.append(f"{prefix}: evidence row missing evidence_id")
            elif evidence_id in seen_evidence_ids:
                errors.append(f"{prefix}: duplicate evidence_id={evidence_id}")
            seen_evidence_ids.add(evidence_id)
            source_id = evidence_row.get("source_id", "").strip()
            role = evidence_row.get("evidence_role", "").strip()
            level = evidence_row.get("required_level", "").strip()
            if source_id:
                ids_to_check.append(source_id)
            elif role != "constraint":
                errors.append(f"{prefix}: empty evidence source_id is allowed only for constraint")
            if not evidence_row.get("evidence_text", "").strip():
                errors.append(f"{prefix}: evidence row missing evidence_text")
            if role not in EVIDENCE_ROLES:
                errors.append(f"{prefix}: invalid evidence_role={role!r}")
            if level not in EVIDENCE_LEVELS:
                errors.append(f"{prefix}: invalid required_level={level!r}")

        unknown_ids = sorted({value for value in ids_to_check if value not in product_ids})
        if unknown_ids:
            errors.append(f"{prefix}: source/entity IDs absent from snapshot: {unknown_ids}")

        decisions = {question_status, reference_status, evidence_status} - {"not_applicable"}
        if any(status != "pending" for status in decisions) and not row.get("reviewer", "").strip():
            errors.append(f"{prefix}: reviewer is required after making a decision")
        if require_complete:
            unfinished = decisions & {"pending", "needs_revision"}
            if unfinished:
                errors.append(f"{prefix}: review is not complete: {sorted(unfinished)}")

    if expected_question_ids is not None:
        missing = sorted(expected_question_ids - seen_question_ids)
        unexpected = sorted(seen_question_ids - expected_question_ids)
        if missing:
            errors.append(f"review file is missing question IDs: {missing}")
        if unexpected:
            errors.append(f"review file contains unexpected question IDs: {unexpected}")
    return errors


def review_summary(rows: list[dict[str, str]], errors: list[str]) -> dict[str, Any]:
    warning_counts = Counter(
        warning
        for row in rows
        for warning in row.get("review_warnings", "").split("|")
        if warning
    )
    return {
        "question_count": len(rows),
        "category_counts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "difficulty_counts": dict(sorted(Counter(row["difficulty"] for row in rows).items())),
        "question_status_counts": dict(sorted(Counter(row["question_status"] for row in rows).items())),
        "reference_status_counts": dict(sorted(Counter(row["reference_status"] for row in rows).items())),
        "evidence_status_counts": dict(sorted(Counter(row["evidence_status"] for row in rows).items())),
        "review_warning_counts": dict(sorted(warning_counts.items())),
        "structural_validation_passed": not errors,
        "validation_errors": errors,
    }


def _markdown_text(value: str) -> str:
    return (value or "—").replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def write_review_markdown(path: Path, rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    lines = [
        "# Ground-truth review — Conversational AI",
        "",
        "> File chỉnh sửa chính: `ground_truth_review.csv`. Markdown này là bản đọc thuận tiện và",
        "> sẽ được sinh lại từ CSV/source; không ghi quyết định review trực tiếp vào file này.",
        "",
        "## Hướng dẫn quyết định",
        "",
        "- `approved`: câu hỏi/reference/evidence đúng và đủ để làm acceptance ground truth.",
        "- `needs_revision`: sửa nội dung tương ứng trong CSV rồi đổi thành `approved` khi hoàn tất.",
        "- `rejected`: case mơ hồ, sai snapshot hoặc không nên nằm trong suite.",
        "- `not_applicable`: chỉ dùng cho `evidence_status` khi `evidence_json=[]`.",
        "- Điền `reviewer` cho mọi row đã đưa ra quyết định; `review_notes` ghi lý do sửa/reject.",
        "",
        "## Tổng quan",
        "",
        f"- Testcase: **{summary['question_count']}**",
        f"- Structural validation: **{'PASS' if summary['structural_validation_passed'] else 'FAIL'}**",
        f"- Question status: `{json.dumps(summary['question_status_counts'], ensure_ascii=False)}`",
        f"- Reference status: `{json.dumps(summary['reference_status_counts'], ensure_ascii=False)}`",
        f"- Evidence status: `{json.dumps(summary['evidence_status_counts'], ensure_ascii=False)}`",
        f"- Review warnings: `{json.dumps(summary['review_warning_counts'], ensure_ascii=False)}`",
        "",
        "## Checklist review",
        "",
        "Với từng case, kiểm tra:",
        "",
        "1. Câu hỏi tự nhiên, không mơ hồ ngoài chủ đích và đúng category/difficulty.",
        "2. Entity/source ID tồn tại và đúng sản phẩm trong snapshot.",
        "3. Reference answer chỉ dùng dữ liệu nguồn và trả lời đúng trọng tâm.",
        "4. `answer_must_include` không quá cứng với recommendation/follow-up.",
        "5. Evidence `must_have` đủ để tạo câu trả lời; `nice_to_have` không bị dùng làm hard gate.",
        "6. Case unanswerable không chứa policy tự bịa và hướng người dùng kiểm tra nguồn phù hợp.",
        "",
    ]

    current_category = ""
    for row in rows:
        if row["category"] != current_category:
            current_category = row["category"]
            lines.extend([f"## Nhóm `{current_category}`", ""])
        lines.extend(
            [
                f"### `{row['question_id']}`",
                "",
                f"- Session/turn: `{row['session_id']}` / `{row['turn_index']}`",
                f"- Difficulty/history: `{row['difficulty']}` / `{row['depends_on_history']}`",
                f"- Expected type: `{row['expected_answer_type']}`",
                f"- Entity IDs: `{_markdown_text(row['entity_ids'])}`",
                f"- Trạng thái: question=`{row['question_status']}`, reference=`{row['reference_status']}`, evidence=`{row['evidence_status']}`",
                f"- Review warnings: `{_markdown_text(row.get('review_warnings', ''))}`",
                "",
                f"**Question:** {_markdown_text(row['question'])}",
                "",
                f"**Reference:** {_markdown_text(row['reference_answer'])}",
                "",
                f"**Must include:** {_markdown_text(row['answer_must_include'])}",
                "",
                f"**Must not include:** {_markdown_text(row['answer_must_not_include'])}",
                "",
                f"**Reference source IDs:** `{_markdown_text(row['reference_source_ids'])}`",
                "",
                "**Evidence:**",
                "",
                "| Evidence ID | Source | Role | Level | Text |",
                "|---|---|---|---|---|",
            ]
        )
        evidence_rows = parse_evidence(row)
        if evidence_rows:
            for evidence in evidence_rows:
                lines.append(
                    "| {evidence_id} | {source_id} | {evidence_role} | {required_level} | {evidence_text} |".format(
                        **{key: _markdown_text(value) for key, value in evidence.items()}
                    )
                )
        else:
            lines.append("| — | — | — | — | Không áp dụng |")

        lines.extend(
            [
                "",
                "**Source products:**",
                "",
                "| ID | Tên | Category | Color | Material | Gender |",
                "|---|---|---|---|---|---|",
            ]
        )
        source_products = json.loads(row.get("source_products_json", "[]") or "[]")
        if source_products:
            for product in source_products:
                name = product.get("product_name_vi") or product.get("product_name") or ""
                lines.append(
                    f"| {_markdown_text(product.get('product_id', ''))} | {_markdown_text(name)} | "
                    f"{_markdown_text(product.get('category', ''))} | {_markdown_text(product.get('color', ''))} | "
                    f"{_markdown_text(product.get('material', ''))} | {_markdown_text(product.get('gender', ''))} |"
                )
        else:
            lines.append("| — | Không có source product | — | — | — | — |")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare(args: argparse.Namespace) -> int:
    if args.review_csv.exists() and not args.force:
        raise FileExistsError(
            f"Review file already exists: {args.review_csv}. Use --force only to regenerate it."
        )
    questions = read_csv_rows(args.questions)
    references = read_csv_rows(args.references)
    evidence = read_csv_rows(args.evidence)
    products = read_csv_rows(args.products)
    rows = build_review_rows(questions, references, evidence, products)
    errors = validate_review_rows(
        rows,
        products,
        expected_question_ids={row["question_id"] for row in questions},
    )
    summary = review_summary(rows, errors)
    write_csv_rows(args.review_csv, rows, REVIEW_FIELDS)
    write_review_markdown(args.review_markdown, rows, summary)
    args.review_summary.parent.mkdir(parents=True, exist_ok=True)
    args.review_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"prepared {len(rows)} review rows -> {args.review_csv}; "
        f"structural_validation={'passed' if not errors else 'failed'}"
    )
    return 0 if not errors else 1


def validate(args: argparse.Namespace, *, require_complete: bool) -> tuple[list[dict[str, str]], list[str]]:
    rows = read_csv_rows(args.review_csv)
    products = read_csv_rows(args.products)
    expected_ids = {row["question_id"] for row in read_csv_rows(args.questions)}
    errors = validate_review_rows(
        rows,
        products,
        expected_question_ids=expected_ids,
        require_complete=require_complete,
    )
    summary = review_summary(rows, errors)
    args.review_summary.parent.mkdir(parents=True, exist_ok=True)
    args.review_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_review_markdown(args.review_markdown, rows, summary)
    print(
        f"validated {len(rows)} review rows; errors={len(errors)}; "
        f"complete_required={require_complete}"
    )
    for error in errors:
        print(f"ERROR: {error}")
    return rows, errors


def apply_review(args: argparse.Namespace) -> int:
    rows, errors = validate(args, require_complete=True)
    if errors:
        return 1
    reviewed_at = datetime.now(timezone.utc).isoformat()
    existing_questions = _by_unique_id(read_csv_rows(args.questions), "question_id", "question")
    existing_references = _by_unique_id(read_csv_rows(args.references), "question_id", "reference")
    question_rows: list[dict[str, str]] = []
    reference_rows: list[dict[str, str]] = []
    evidence_rows: list[dict[str, str]] = []

    for row in rows:
        question_id = row["question_id"]
        question = dict(existing_questions[question_id])
        question.update(
            {
                "session_id": row["session_id"],
                "turn_index": row["turn_index"],
                "category": row["category"],
                "difficulty": row["difficulty"],
                "depends_on_history": row["depends_on_history"],
                "expected_answer_type": row["expected_answer_type"],
                "question": row["question"],
                "entity_ids": row["entity_ids"],
                "manual_status": row["question_status"],
                "reviewer": row["reviewer"],
                "reviewed_at": reviewed_at,
                "review_notes": row["review_notes"],
            }
        )
        question_rows.append(question)

        reference = dict(existing_references[question_id])
        reference.update(
            {
                "reference_answer": row["reference_answer"],
                "answer_must_include": row["answer_must_include"],
                "answer_must_not_include": row["answer_must_not_include"],
                "reference_source_ids": row["reference_source_ids"],
                "review_status": row["reference_status"],
                "reviewer": row["reviewer"],
                "reviewed_at": reviewed_at,
                "review_notes": row["review_notes"],
            }
        )
        reference_rows.append(reference)

        for evidence in parse_evidence(row):
            evidence_rows.append(
                {
                    "question_id": question_id,
                    **evidence,
                    "review_status": row["evidence_status"],
                    "reviewer": row["reviewer"],
                    "reviewed_at": reviewed_at,
                    "review_notes": row["review_notes"],
                }
            )

    write_csv_rows(args.questions, question_rows, QUESTION_FIELDS)
    write_csv_rows(args.references, reference_rows, REFERENCE_FIELDS)
    write_csv_rows(args.evidence, evidence_rows, EVIDENCE_FIELDS)
    print(
        f"applied review: questions={len(question_rows)}, references={len(reference_rows)}, "
        f"evidence={len(evidence_rows)}"
    )
    return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    root = SCRIPT_DIR.parent
    parser.add_argument("--questions", type=Path, default=root / "data" / "question_set.csv")
    parser.add_argument("--references", type=Path, default=root / "data" / "reference_answers.csv")
    parser.add_argument("--evidence", type=Path, default=root / "data" / "required_evidence.csv")
    parser.add_argument("--products", type=Path, default=root / "data" / "product_snapshot.csv")
    parser.add_argument("--review-csv", type=Path, default=REVIEW_CSV)
    parser.add_argument("--review-markdown", type=Path, default=REVIEW_MD)
    parser.add_argument("--review-summary", type=Path, default=REVIEW_SUMMARY)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare, validate, and apply human review for conversational ground truth."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare", help="Create the editable review packet.")
    add_common_arguments(prepare_parser)
    prepare_parser.add_argument("--force", action="store_true", help="Overwrite an existing review packet.")
    validate_parser = subparsers.add_parser("validate", help="Validate the edited review packet.")
    add_common_arguments(validate_parser)
    validate_parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail on pending or needs_revision decisions.",
    )
    apply_parser = subparsers.add_parser("apply", help="Apply a complete review to ground-truth CSVs.")
    add_common_arguments(apply_parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "prepare":
        return prepare(args)
    if args.command == "validate":
        _, errors = validate(args, require_complete=args.require_complete)
        return 0 if not errors else 1
    if args.command == "apply":
        return apply_review(args)
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
