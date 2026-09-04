from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TECHNICAL_DISCLOSURE_TERMS = (
    "rag", "embedding", "vector", "api", "database", "json", "system prompt",
)
AVAILABILITY_TERMS = ("còn hàng", "hết hàng", "có sẵn", "trong kho")
PRICE_OR_PROMOTION_TERMS = ("giảm giá", "giảm 50", "khuyến mãi", "giá cuối")


def normalize(value: str) -> str:
    value = (value or "").replace("đ", "d").replace("Đ", "D")
    value = unicodedata.normalize("NFKD", value)
    return " ".join(
        re.sub(r"[^a-z0-9 ]+", " ", value.encode("ascii", "ignore").decode().lower()).split()
    )


def split_values(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"\s*[|;]\s*", value or "") if item.strip()]


def token_f1(left: str, right: str) -> float:
    a, b = set(normalize(left).split()), set(normalize(right).split())
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    precision, recall = overlap / len(a), overlap / len(b)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def context_ids(context: list[dict], fallback: list[str]) -> set[str]:
    values = set()
    for item in context:
        if isinstance(item, dict):
            value = item.get("product_id") or item.get("id") or item.get("source_id")
            if value is not None:
                values.add(str(value))
    return values or set(fallback)


def forbidden_claims_absent(answer: str, context: list[dict]) -> bool:
    answer_norm = normalize(answer)
    if any(normalize(term) in answer_norm for term in TECHNICAL_DISCLOSURE_TERMS):
        return False
    serialized = normalize(json.dumps(context, ensure_ascii=False))
    has_availability_evidence = any(
        token in serialized
        for token in ("inventory count", "total stock", "available", "variants")
    )
    has_price_evidence = any(
        token in serialized
        for token in ("price", "discounted price", "effective price")
    )
    # Policy wording such as "đổi size nếu còn hàng" is a condition, not a
    # claim that the currently discussed product is in stock.
    availability_claim_text = answer_norm
    for conditional in ("neu con hang", "trong truong hop con hang"):
        availability_claim_text = availability_claim_text.replace(conditional, "")
    if any(normalize(term) in availability_claim_text for term in AVAILABILITY_TERMS):
        if not has_availability_evidence:
            return False
    if any(normalize(term) in answer_norm for term in PRICE_OR_PROMOTION_TERMS):
        if not has_price_evidence:
            return False
    return True


def reference_forbidden_claims_absent(answer: str, reference: dict[str, str]) -> bool:
    answer_norm = normalize(answer)
    return all(
        normalize(term) not in answer_norm
        for term in split_values(reference.get("answer_must_not_include", ""))
        if normalize(term)
    )


def refusal_behavior_is_valid(answer: str, retrieved_ids: set[str]) -> bool:
    if retrieved_ids:
        return False
    normalized = normalize(answer)
    return any(
        marker in normalized
        for marker in (
            "chua ho tro",
            "chua co thong tin",
            "khong co thong tin",
            "khong the",
            "khong dam bao",
            "khong co gi dam bao",
        )
    )


def ordinal_expected_source_ids(
    question: dict[str, str],
    questions: dict[str, dict[str, str]],
    responses: dict[str, dict[str, str]],
) -> set[str]:
    match = re.search(r"ordinal_index=(\d+)", question.get("notes", ""))
    if not match:
        return set()
    current_turn = int(question.get("turn_index", "0") or 0)
    previous = [
        candidate
        for candidate in questions.values()
        if candidate.get("session_id") == question.get("session_id")
        and int(candidate.get("turn_index", "0") or 0) < current_turn
    ]
    if not previous:
        return set()
    previous_question = max(previous, key=lambda item: int(item.get("turn_index", "0") or 0))
    previous_ids = split_values(
        responses.get(previous_question.get("question_id", ""), {}).get(
            "retrieved_product_ids", ""
        ).replace("|", ";")
    )
    ordinal = int(match.group(1))
    return {previous_ids[ordinal - 1]} if len(previous_ids) >= ordinal else set()


def main() -> int:
    args = parse_args()
    responses = {row["question_id"]: row for row in read_csv(args.responses_csv)}
    references = {row["question_id"]: row for row in read_csv(args.references_csv)}
    questions = {row["question_id"]: row for row in read_csv(args.questions_csv)}
    evidence_by_question: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(args.evidence_csv):
        evidence_by_question[row["question_id"]].append(row)

    scored = []
    for question_id, question in questions.items():
        response = responses.get(question_id, {})
        reference = references.get(question_id, {})
        answer = response.get("answer", "")
        answer_norm = normalize(answer)
        retrieved = [value for value in response.get("retrieved_product_ids", "").split("|") if value]
        try:
            context = json.loads(response.get("retrieved_context_json", "[]") or "[]")
        except json.JSONDecodeError:
            context = []
        if not isinstance(context, list):
            context = []
        retrieved_ids = context_ids(context, retrieved)
        expected_ids = set(split_values(reference.get("reference_source_ids", "")))
        if question.get("expected_answer_type") == "ordinal_reference":
            expected_ids = ordinal_expected_source_ids(question, questions, responses)
        required_terms = split_values(reference.get("answer_must_include", ""))
        required_coverage = ratio(
            sum(normalize(term) in answer_norm for term in required_terms), len(required_terms)
        ) if required_terms else 1.0
        if question.get("category") == "unanswerable":
            required_coverage = float(refusal_behavior_is_valid(answer, retrieved_ids))
        forbidden_ok = forbidden_claims_absent(
            answer, context
        ) and reference_forbidden_claims_absent(answer, reference)
        named_ids = set(
            re.findall(
                r"(?:product[_\s-]*id|mã\s+sản\s+phẩm)\s*[:#-]?\s*(\d{1,8})",
                answer,
                flags=re.IGNORECASE,
            )
        )
        id_grounding = ratio(len(named_ids & retrieved_ids), len(named_ids)) if named_ids else 1.0
        rule_based_grounding_score = (
            required_coverage + float(forbidden_ok) + id_grounding
        ) / 3

        lexical_relevancy = token_f1(answer, reference.get("reference_answer", ""))
        token_f1_relevancy = (
            required_coverage
            if question.get("category") == "unanswerable"
            else (required_coverage + lexical_relevancy) / 2
        )

        measured_context_precision = (
            ratio(len(retrieved_ids & expected_ids), len(retrieved_ids))
            if expected_ids and retrieved_ids
            else (
                float(not retrieved_ids)
                if question.get("category") == "unanswerable"
                else (0.0 if expected_ids else None)
            )
        )
        required_evidence = [
            row for row in evidence_by_question.get(question_id, [])
            if row.get("required_level") == "must_have" and row.get("source_id")
        ]
        if response.get("context_mode") == "full_context":
            serialized = normalize(json.dumps(context, ensure_ascii=False))
            evidence_hits = sum(
                row["source_id"] in retrieved_ids
                and all(token in serialized for token in normalize(row["evidence_text"]).split())
                for row in required_evidence
            )
        else:
            evidence_hits = sum(row["source_id"] in retrieved_ids for row in required_evidence)
        if question.get("expected_answer_type") in {
            "recommendation", "search_initial", "ordinal_reference"
        } and expected_ids:
            measured_context_recall = float(bool(retrieved_ids & expected_ids))
        elif question.get("category") == "unanswerable":
            measured_context_recall = float(not retrieved_ids)
        else:
            measured_context_recall = (
                ratio(evidence_hits, len(required_evidence)) if required_evidence else None
            )
        full_context = response.get("context_mode") == "full_context"
        scored.append({
            "question_id": question_id, "category": question["category"],
            "difficulty": question["difficulty"],
            "context_mode": response.get("context_mode", "missing"),
            "rule_based_grounding_score": round(rule_based_grounding_score, 6),
            "token_f1_relevancy": round(token_f1_relevancy, 6),
            "context_precision": (
                round(measured_context_precision, 6)
                if full_context and measured_context_precision is not None else None
            ),
            "context_recall": (
                round(measured_context_recall, 6)
                if full_context and measured_context_recall is not None else None
            ),
            "context_precision_product_id_proxy": (
                None if full_context or measured_context_precision is None
                else round(measured_context_precision, 6)
            ),
            "context_recall_product_id_proxy": (
                None if full_context or measured_context_recall is None
                else round(measured_context_recall, 6)
            ),
            "required_term_coverage": round(required_coverage, 6),
            "forbidden_claims_absent": str(forbidden_ok).lower(),
            "retrieved_count": len(retrieved_ids), "expected_source_count": len(expected_ids),
            "required_evidence_count": len(required_evidence),
        })

    metrics = (
        "rule_based_grounding_score",
        "token_f1_relevancy",
        "context_precision",
        "context_recall",
        "context_precision_product_id_proxy",
        "context_recall_product_id_proxy",
    )
    aggregate = {metric: average_present(scored, metric) for metric in metrics}
    thresholds = {
        "rule_based_grounding_score": args.min_rule_based_grounding,
        "token_f1_relevancy": args.min_token_f1_relevancy,
        "context_precision": args.min_context_precision,
        "context_recall": args.min_context_recall,
    }
    modes = sorted(set(row["context_mode"] for row in scored))
    full_context_count = sum(row["context_mode"] == "full_context" for row in scored)
    checks: dict[str, bool | None] = {
        "rule_based_grounding_score": (
            aggregate["rule_based_grounding_score"] >= thresholds["rule_based_grounding_score"]
        ),
        "token_f1_relevancy": (
            aggregate["token_f1_relevancy"] >= thresholds["token_f1_relevancy"]
        ),
        "context_precision": None,
        "context_recall": None,
    }
    if full_context_count == len(scored) and scored:
        checks["context_precision"] = aggregate["context_precision"] >= thresholds["context_precision"]
        checks["context_recall"] = aggregate["context_recall"] >= thresholds["context_recall"]
    acceptance_checks = [value for value in checks.values() if value is not None]
    summary = {
        "question_count": len(scored), "metrics": aggregate,
        "thresholds": thresholds, "threshold_checks": checks,
        "acceptance_passed": all(acceptance_checks),
        "context_modes": modes,
        "full_context_count": full_context_count,
        "context_release_gate_enabled": full_context_count == len(scored) and bool(scored),
        "release_gate_metrics": [
            "rule_based_grounding_score",
            "token_f1_relevancy",
            *(
                ["context_precision", "context_recall"]
                if full_context_count == len(scored) and scored
                else []
            ),
        ],
        "diagnostic_metrics": [
            "context_precision_product_id_proxy",
            "context_recall_product_id_proxy",
        ],
        "run_metadata": read_json_object(args.run_metadata_json),
        "evaluator_version": "rag-evaluator-v4",
        "measurement_note": (
            "Context Precision/Recall gate release only when every case uses full_context; "
            "product-ID proxies remain diagnostic-only; source-less constraint turns are "
            "excluded from context aggregates (including deterministic shop-knowledge turns); "
            "unanswerable turns are scored by refusal behavior, and per-reference forbidden "
            "claims are enforced."
        ),
        "breakdown": breakdown(scored, metrics),
    }
    write_csv(args.output_csv, scored, list(scored[0]))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["acceptance_passed"] else 1


def breakdown(rows: list[dict], metrics: tuple[str, ...]) -> dict:
    result = {}
    for field in ("category", "difficulty"):
        groups = defaultdict(list)
        for row in rows:
            groups[row[field]].append(row)
        result[field] = {
            key: {
                "question_count": len(values),
                **{metric: average_present(values, metric) for metric in metrics},
            }
            for key, values in sorted(groups.items())
        }
    return result


def average_present(rows: list[dict], metric: str) -> float | None:
    values = [float(row[metric]) for row in rows if row.get(metric) is not None]
    return sum(values) / len(values) if values else None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "rag_eval_responses.csv")
    parser.add_argument("--questions-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "question_set.csv")
    parser.add_argument("--references-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "reference_answers.csv")
    parser.add_argument("--evidence-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "required_evidence.csv")
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "rag_metrics_by_question.csv")
    parser.add_argument("--output-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "rag_metrics_summary.json")
    parser.add_argument("--run-metadata-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "rag_eval_run_metadata.json")
    parser.add_argument(
        "--min-rule-based-grounding",
        "--min-faithfulness",
        dest="min_rule_based_grounding",
        type=float,
        default=0.85,
    )
    parser.add_argument(
        "--min-token-f1-relevancy",
        "--min-response-relevancy",
        dest="min_token_f1_relevancy",
        type=float,
        default=0.70,
    )
    parser.add_argument("--min-context-precision", type=float, default=0.60)
    parser.add_argument("--min-context-recall", type=float, default=0.80)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
