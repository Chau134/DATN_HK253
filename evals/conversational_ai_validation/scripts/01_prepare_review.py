from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from common import (
    HARD_GATE_FIELDS,
    RATING_FIELDS,
    REVIEW_FIELDS,
    default_applicability,
    load_config,
    read_csv,
    read_json,
    resolve,
    select_stratified,
    write_csv,
)


def index_by(rows: list[dict[str, str]], field: str) -> dict[str, dict[str, str]]:
    return {row[field]: row for row in rows}


def compact_context(raw_context: str) -> str:
    try:
        context = json.loads(raw_context or "[]")
    except json.JSONDecodeError:
        return ""
    if not isinstance(context, list):
        return ""
    summaries = []
    for product in context:
        if not isinstance(product, dict):
            continue
        price = product.get("price") or {}
        summaries.append(
            "; ".join((
                f"id={product.get('id', '')}",
                f"tên={product.get('title_vi') or product.get('title') or ''}",
                f"màu={product.get('base_colour_vi') or product.get('base_colour') or ''}",
                f"chất liệu={product.get('material_vi') or product.get('material') or ''}",
                f"giá hiệu lực={price.get('effective_price', '')}",
                f"tồn kho={product.get('total_stock', '')}",
            ))
        )
    return " || ".join(summaries)


def build_packets(config_path: Path | None = None, *, force: bool = False) -> dict[str, object]:
    config, base = load_config(config_path)
    source = config["source"]
    questions = index_by(read_csv(resolve(base, source["questions_csv"])), "question_id")
    references = index_by(read_csv(resolve(base, source["references_csv"])), "question_id")
    responses = index_by(read_csv(resolve(base, source["responses_csv"])), "question_id")
    metrics = index_by(read_csv(resolve(base, source["metrics_csv"])), "question_id")

    evidence_by_question: dict[str, list[str]] = defaultdict(list)
    for row in read_csv(resolve(base, source["evidence_csv"])):
        evidence_by_question[row["question_id"]].append(row.get("evidence_text", ""))

    questions_by_session: dict[str, list[dict[str, str]]] = defaultdict(list)
    for question in questions.values():
        questions_by_session[question.get("session_id", "")].append(question)
    history_by_question: dict[str, str] = {}
    for session_questions in questions_by_session.values():
        history: list[str] = []
        for question in sorted(
            session_questions, key=lambda item: int(item.get("turn_index", "0") or 0)
        ):
            question_id = question["question_id"]
            history_by_question[question_id] = "\n".join(history)
            response = responses.get(question_id)
            if response:
                prior_evidence = compact_context(response.get("retrieved_context_json", ""))
                history.append(
                    f"Lượt {question.get('turn_index', '0')} - Người dùng: "
                    f"{question.get('question', '')}\nTrợ lý: {response.get('answer', '')}"
                    + (f"\nBằng chứng lượt: {prior_evidence}" if prior_evidence else "")
                )

    merged: list[dict[str, str]] = []
    missing: list[str] = []
    for question_id, question in questions.items():
        if question_id not in responses or question_id not in references or question_id not in metrics:
            missing.append(question_id)
            continue
        response = responses[question_id]
        reference = references[question_id]
        context = response.get("retrieved_context_json", "")
        try:
            parsed_context = json.loads(context or "[]")
            context = json.dumps(parsed_context, ensure_ascii=False, separators=(",", ":"))
        except json.JSONDecodeError:
            pass
        merged.append({
            **question,
            "conversation_history": history_by_question.get(question_id, ""),
            "answer": response.get("answer", ""),
            "reference_answer": reference.get("reference_answer", ""),
            "answer_must_include": reference.get("answer_must_include", ""),
            "answer_must_not_include": reference.get("answer_must_not_include", ""),
            "required_evidence": " | ".join(evidence_by_question.get(question_id, [])),
            "retrieved_context": context,
            "token_f1_relevancy": metrics[question_id].get("token_f1_relevancy", ""),
            "rule_based_grounding_score": metrics[question_id].get("rule_based_grounding_score", ""),
        })

    selected = select_stratified(
        merged,
        int(config["sample_size"]),
        int(config["sampling_seed"]),
    )
    selected_ids = {row["question_id"] for row in selected}

    manifest_rows = [
        {
            "question_id": row["question_id"],
            "category": row.get("category", ""),
            "difficulty": row.get("difficulty", ""),
            "token_f1_relevancy": row.get("token_f1_relevancy", ""),
            "rule_based_grounding_score": row.get("rule_based_grounding_score", ""),
            "selected": str(row["question_id"] in selected_ids).lower(),
        }
        for row in sorted(merged, key=lambda item: item["question_id"])
    ]
    manifest_path = resolve(base, config["reports"]["sample_manifest_csv"])
    write_csv(
        manifest_path,
        manifest_rows,
        (
            "question_id", "category", "difficulty", "token_f1_relevancy",
            "rule_based_grounding_score", "selected",
        ),
    )

    for reviewer_index, key in enumerate(("reviewer_a_csv", "reviewer_b_csv")):
        output = resolve(base, config["review"][key])
        if output.exists() and not force:
            raise FileExistsError(
                f"{output} already exists; use --force only if no review work must be preserved"
            )
        ordered = list(selected)
        random.Random(int(config["sampling_seed"]) + reviewer_index + 1).shuffle(ordered)
        packet = []
        for order, row in enumerate(ordered, start=1):
            review_row = {field: "" for field in REVIEW_FIELDS}
            review_row.update({field: row.get(field, "") for field in REVIEW_FIELDS})
            review_row["review_order"] = str(order)
            review_row["review_notes"] = ""
            review_row.update(default_applicability(row))
            for field in RATING_FIELDS:
                review_row.setdefault(field, "")
            for field in HARD_GATE_FIELDS:
                review_row.setdefault(field, "")
            packet.append(review_row)
        write_csv(output, packet, REVIEW_FIELDS)

    automatic_summary = read_json(resolve(base, source["metrics_summary_json"]))
    breakdown_rows = []
    for dimension, groups in automatic_summary.get("breakdown", {}).items():
        for group, values in groups.items():
            breakdown_rows.append({"dimension": dimension, "group": group, **values})
    breakdown_path = resolve(base, config["reports"]["automatic_breakdown_csv"])
    fields = (
        "dimension", "group", "question_count", "rule_based_grounding_score",
        "token_f1_relevancy", "context_precision", "context_recall",
        "context_precision_product_id_proxy", "context_recall_product_id_proxy",
    )
    write_csv(breakdown_path, breakdown_rows, fields)
    return {
        "available_cases": len(merged),
        "selected_cases": len(selected),
        "missing_source_cases": missing,
        "reviewer_a": str(resolve(base, config["review"]["reviewer_a_csv"])),
        "reviewer_b": str(resolve(base, config["review"]["reviewer_b_csv"])),
        "manifest": str(manifest_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare two blinded human-review packets.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_packets(args.config, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
