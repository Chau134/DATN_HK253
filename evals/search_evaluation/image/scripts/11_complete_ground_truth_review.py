from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVIEW_FIELDS = [
    "query_id",
    "difficulty",
    "query_product_id",
    "query_product_name",
    "query_category",
    "query_image_url",
    "candidate_rank",
    "candidate_product_id",
    "candidate_product_name",
    "candidate_category",
    "candidate_brand",
    "candidate_color",
    "candidate_material",
    "candidate_image_url",
    "candidate_image_urls",
    "retrieval_score",
    "candidate_source",
    "review_priority",
    "suggested_grade",
    "suggestion_reason",
    "relevance_grade",
    "review_status",
    "reviewer_notes",
]

RULE_VERSION = "metadata_rule_v1"
NAME_STOPWORDS = {
    "ao",
    "quan",
    "vay",
    "dam",
    "mau",
    "va",
    "vai",
    "dang",
    "co",
    "tay",
    "nu",
    "pha",
    "chat",
    "lieu",
}
UPPER_BODY_CATEGORIES = {
    "ao det kim",
    "ao hai day ao sat nach ao yem",
    "ao kieu",
    "ao so mi",
    "ao thun",
    "blazer ao vest",
    "bodysuit",
}
LOWER_BODY_CATEGORIES = {"chan vay", "quan dai", "quan jeans", "quan legging", "quan short"}
ONE_PIECE_CATEGORIES = {"jumpsuit ao lien quan", "vay dam"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def normalize(value: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", (value or "").casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def name_tokens(value: str | None) -> set[str]:
    return {token for token in normalize(value).split() if token not in NAME_STOPWORDS and not token.isdigit()}


def token_similarity(left: str | None, right: str | None) -> float:
    left_tokens = name_tokens(left)
    right_tokens = name_tokens(right)
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def material_similarity(left: str | None, right: str | None) -> float:
    left_tokens = {token for token in normalize(left).split() if not token.isdigit()}
    right_tokens = {token for token in normalize(right).split() if not token.isdigit()}
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def categories_are_adjacent(left: str | None, right: str | None) -> bool:
    normalized = {normalize(left), normalize(right)}
    return normalized <= UPPER_BODY_CATEGORIES or normalized <= LOWER_BODY_CATEGORIES or normalized <= ONE_PIECE_CATEGORIES


def auto_grade(query: dict[str, str], row: dict[str, str]) -> tuple[int, str]:
    source_product_id = (query.get("source_product_id") or "").strip()
    candidate_product_id = (row.get("candidate_product_id") or "").strip()
    if source_product_id and candidate_product_id == source_product_id:
        return 3, "source_product_exact_match"

    query_name = row.get("query_product_name") or ""
    candidate_name = row.get("candidate_product_name") or ""
    query_category = row.get("query_category") or query.get("category") or ""
    candidate_category = row.get("candidate_category") or ""
    same_category = normalize(query_category) == normalize(candidate_category)
    adjacent_category = categories_are_adjacent(query_category, candidate_category)
    name_score = token_similarity(query_name, candidate_name)
    color_match = bool(normalize(query.get("color"))) and normalize(query.get("color")) == normalize(row.get("candidate_color"))
    material_score = material_similarity(query.get("material"), row.get("candidate_material"))

    duplicate_signature = (
        normalize(query_name) == normalize(candidate_name)
        and same_category
        and color_match
        and material_score >= 0.8
    )
    if duplicate_signature:
        return 2, "identical_metadata_signature_but_unverified_sku"

    if same_category:
        if name_score >= 0.55:
            return 2, f"same_category_name_similarity={name_score:.2f}"
        if color_match and material_score >= 0.35 and name_score >= 0.25:
            return 2, f"same_category_color_material_name={name_score:.2f}"
        if color_match and name_score >= 0.40:
            return 2, f"same_category_color_name={name_score:.2f}"
        return 1, f"same_category_weak_similarity={name_score:.2f}"

    if adjacent_category:
        if color_match and name_score >= 0.60:
            return 2, f"adjacent_category_color_name={name_score:.2f}"
        if name_score >= 0.35 or (color_match and name_score >= 0.20):
            return 1, f"adjacent_category_weak_similarity={name_score:.2f}"
    return 0, "different_category_or_insufficient_visual_metadata"


def read_overrides(path: Path | None) -> dict[tuple[str, str], tuple[int, str]]:
    if path is None:
        return {}
    overrides: dict[tuple[str, str], tuple[int, str]] = {}
    for row in read_csv(path):
        key = ((row.get("query_id") or "").strip(), (row.get("candidate_product_id") or "").strip())
        grade = int((row.get("relevance_grade") or "").strip())
        if not all(key) or grade not in {0, 1, 2, 3}:
            raise ValueError(f"invalid override row: {row}")
        overrides[key] = (grade, (row.get("reason") or "manual_audit_override").strip())
    return overrides


def complete_review_rows(
    review_rows: list[dict[str, str]],
    query_rows: list[dict[str, str]],
    overrides: dict[tuple[str, str], tuple[int, str]],
    *,
    human_top_k: int = 5,
) -> list[dict[str, Any]]:
    query_by_id = {row.get("query_id", ""): row for row in query_rows}
    completed: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_overrides: set[tuple[str, str]] = set()

    for line_number, original in enumerate(review_rows, start=2):
        row: dict[str, Any] = {field: original.get(field, "") for field in REVIEW_FIELDS}
        query_id = str(row.get("query_id") or "").strip()
        candidate_id = str(row.get("candidate_product_id") or "").strip()
        query = query_by_id.get(query_id)
        if query is None:
            errors.append(f"line {line_number}: unknown query_id={query_id!r}")
            continue
        try:
            rank = int(float(str(row.get("candidate_rank") or "0")))
        except ValueError:
            rank = 0

        override = overrides.get((query_id, candidate_id))
        if override is not None:
            grade, reason = override
            seen_overrides.add((query_id, candidate_id))
            row["relevance_grade"] = grade
            row["review_status"] = "approved"
            row["reviewer_notes"] = f"human_top5_audit_override:{reason}"
        elif rank == 0 or rank <= human_top_k:
            raw_grade = str(row.get("relevance_grade") or "").strip()
            if raw_grade not in {"0", "1", "2", "3"}:
                errors.append(f"line {line_number}: top-{human_top_k} row requires a human grade")
                continue
            row["relevance_grade"] = int(raw_grade)
            row["review_status"] = "approved"
            existing_notes = str(row.get("reviewer_notes") or "").strip()
            row["reviewer_notes"] = existing_notes or "human_top5_review"
        else:
            grade, reason = auto_grade(query, original)
            row["relevance_grade"] = grade
            row["review_status"] = "approved"
            row["reviewer_notes"] = f"{RULE_VERSION}:{reason}"
        completed.append(row)

    missing_overrides = sorted(set(overrides) - seen_overrides)
    if missing_overrides:
        errors.append(f"overrides not found in review rows: {missing_overrides}")
    if errors:
        raise ValueError("review completion failed:\n" + "\n".join(f"- {error}" for error in errors[:20]))
    return completed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Approve human-reviewed top K and conservatively label the remaining review rows.")
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--query-set-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_queries.csv")
    parser.add_argument("--overrides-csv", type=Path, default=None)
    parser.add_argument("--human-top-k", type=int, default=5)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=SCRIPT_DIR.parent / "reports" / "review" / "ground_truth_image_review_completed.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = complete_review_rows(
        read_csv(args.review_csv),
        read_csv(args.query_set_csv),
        read_overrides(args.overrides_csv),
        human_top_k=args.human_top_k,
    )
    write_csv(args.output_csv, rows)
    grade_counts = {grade: sum(str(row["relevance_grade"]) == str(grade) for row in rows) for grade in range(4)}
    human_count = sum(not str(row["reviewer_notes"]).startswith(f"{RULE_VERSION}:") for row in rows)
    print(f"completed_rows={len(rows)} human={human_count} auto={len(rows) - human_count} grades={grade_counts}")
    print(f"completed review -> {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
