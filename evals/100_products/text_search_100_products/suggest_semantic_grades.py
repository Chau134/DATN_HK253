"""Populate provisional relevance grades for manual semantic review.

The generated grades are deliberately kept in ``pending`` state. A reviewer
must confirm or change them before they are copied to semantic_judgments.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_CANDIDATES = EVAL_DIR / "data" / "semantic_review_candidates.csv"
DEFAULT_CASES = EVAL_DIR / "data" / "test_cases.csv"
DEFAULT_JUDGMENTS = EVAL_DIR / "config" / "semantic_judgments.json"

CATEGORY_PHRASES = (
    "đầm jumpsuit",
    "áo sơ mi",
    "áo bodysuit",
    "áo cardigan",
    "áo croptop",
    "áo hoodie",
    "áo blazer",
    "áo khoác",
    "áo blouse",
    "áo hai dây",
    "áo cardigan",
    "áo thun",
    "áo polo",
    "áo gile",
    "áo kiểu",
    "quần short",
    "quần culotte",
    "quần jeans",
    "quần legging",
    "quần joger",
    "quần tây",
    "váy quần",
    "quần dài",
    "quần nỉ",
    "chân váy",
    "jumpsuit",
    "đầm",
)

RELATED_CATEGORIES = {
    frozenset(("áo sơ mi", "áo blouse")),
    frozenset(("áo hai dây", "áo bodysuit")),
    frozenset(("đầm jumpsuit", "jumpsuit")),
    frozenset(("quần culotte", "quần dài")),
    frozenset(("quần jeans", "quần dài")),
}

GENERIC_TOKENS = {
    "ao",
    "quan",
    "dam",
    "vay",
    "chan",
    "jumpsuit",
    "minh",
    "muon",
    "tim",
    "de",
    "mac",
    "hang",
    "ngay",
    "co",
    "kem",
    "phoi",
    "dang",
}

WEAK_CROSS_CATEGORY_TOKENS = {
    "be",
    "cao",
    "cam",
    "co",
    "dai",
    "den",
    "do",
    "fuchsia",
    "hong",
    "kem",
    "mau",
    "nam",
    "ngan",
    "nau",
    "navy",
    "nu",
    "pastel",
    "rong",
    "tay",
    "trang",
    "vang",
    "xam",
    "xanh",
}

COLOR_TOKENS = {
    "be",
    "cam",
    "den",
    "do",
    "fuchsia",
    "hong",
    "kem",
    "nau",
    "navy",
    "pastel",
    "trang",
    "vang",
    "xam",
    "xanh",
}


def normalize(value: str) -> str:
    value = value.lower().replace("đ", "d")
    value = "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(re.findall(r"[a-z0-9]+", value))


NORMALIZED_CATEGORIES = tuple((normalize(value), value) for value in CATEGORY_PHRASES)


def category(value: str) -> str:
    normalized = f" {normalize(value)} "
    for phrase, label in NORMALIZED_CATEGORIES:
        if f" {phrase} " in normalized:
            return label
    return ""


def attribute_tokens(value: str, product_category: str) -> set[str]:
    tokens = set(normalize(value).split())
    tokens.difference_update(GENERIC_TOKENS)
    tokens.difference_update(normalize(product_category).split())
    return tokens


def token_matches(source: set[str], candidate: set[str]) -> set[str]:
    matches: set[str] = set()
    for source_token in source:
        if source_token in candidate or any(
            len(source_token) >= 4
            and abs(len(source_token) - len(candidate_token)) <= 1
            and SequenceMatcher(None, source_token, candidate_token).ratio() >= 0.86
            for candidate_token in candidate
        ):
            matches.add(source_token)
    return matches


def categories_related(left: str, right: str) -> bool:
    return left == right or frozenset((left, right)) in RELATED_CATEGORIES


def suggest_grade(
    *,
    query_text: str,
    source_title: str,
    candidate_title: str,
) -> tuple[int, str]:
    source_category = category(source_title)
    candidate_category = category(candidate_title)
    source_attributes = attribute_tokens(source_title, source_category)
    candidate_attributes = attribute_tokens(candidate_title, candidate_category)
    matches = token_matches(source_attributes, candidate_attributes)
    query_tokens = set(normalize(query_text).split())

    if normalize(source_title) == normalize(candidate_title):
        return 3, "khớp đầy đủ tên và thuộc tính sản phẩm"

    gender_conflict = (
        ("nu" in query_tokens and "nam" in candidate_attributes)
        or ("nam" in query_tokens and "nu" in candidate_attributes)
    )
    if gender_conflict:
        return 0, "đúng một phần loại sản phẩm nhưng sai giới tính được nêu trong query"

    matched = sorted(matches)
    missing = sorted(source_attributes - matches)
    coverage = len(matches) / len(source_attributes) if source_attributes else 1.0
    source_colors = source_attributes & COLOR_TOKENS
    candidate_colors = candidate_attributes & COLOR_TOKENS
    explicit_color_conflict = bool(
        source_colors and candidate_colors and not source_colors.intersection(candidate_colors)
    )
    strong_cross_matches = matches - WEAK_CROSS_CATEGORY_TOKENS

    if source_category and source_category == candidate_category:
        if coverage >= 0.8:
            grade = 3
        else:
            grade = 2
        if explicit_color_conflict:
            grade = min(grade, 2)
        reason = f"đúng loại {source_category}"
    elif source_category and candidate_category and categories_related(
        source_category, candidate_category
    ):
        grade = 2 if coverage >= 0.65 else 1
        reason = (
            f"loại gần liên quan ({candidate_category} thay cho {source_category})"
        )
    elif len(strong_cross_matches) >= 2 and coverage >= 0.4:
        grade = 1
        reason = (
            f"sai loại sản phẩm nhưng còn {len(strong_cross_matches)} thuộc tính đặc hiệu"
        )
    elif strong_cross_matches:
        grade = 1
        reason = "sai loại sản phẩm, chỉ còn liên quan một phần"
    else:
        grade = 0
        reason = "không khớp loại sản phẩm hoặc thuộc tính đặc hiệu"

    details: list[str] = [reason]
    if matched:
        details.append("khớp: " + "/".join(matched[:4]))
    if missing and grade < 3:
        details.append("thiếu/khác: " + "/".join(missing[:4]))
    return grade, "; ".join(details)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--test-cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    parser.add_argument(
        "--approve-all-drafts",
        action="store_true",
        help=(
            "Promote every populated pending draft to reviewed and write the complete "
            "ground-truth JSON. Use only after a reviewer has approved the CSV."
        ),
    )
    args = parser.parse_args()

    cases = {
        row["query_id"]: row
        for row in read_csv(args.test_cases)
    }
    rows = read_csv(args.candidates)
    suggested = 0
    for row in rows:
        is_existing_draft = row["notes"].startswith("[AI draft]")
        if row["review_status"] != "pending" or (
            row["relevance_grade"].strip() and not is_existing_draft
        ):
            continue
        case = cases[row["query_id"]]
        grade, reason = suggest_grade(
            query_text=row["query_text"],
            source_title=case["source_product_name_vi"],
            candidate_title=row["title_vi"],
        )
        row["relevance_grade"] = str(grade)
        row["notes"] = f"[AI draft] {reason}"
        suggested += 1

    if args.approve_all_drafts:
        for row in rows:
            if row["review_status"] == "pending" and row["notes"].startswith("[AI draft]"):
                row["review_status"] = "reviewed"
                row["notes"] = row["notes"].removeprefix("[AI draft] ").strip()

        invalid = [
            row
            for row in rows
            if row["review_status"] != "reviewed"
            or row["relevance_grade"] not in {"0", "1", "2", "3"}
        ]
        if invalid:
            raise ValueError(
                "Cannot promote incomplete candidates: "
                + ", ".join(
                    f"{row['query_id']}/{row['product_id']}" for row in invalid[:10]
                )
            )

    with args.candidates.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    if args.approve_all_drafts:
        existing_payload: dict[str, object] = {}
        if args.judgments.exists():
            existing_payload = json.loads(args.judgments.read_text(encoding="utf-8"))
        judgments: dict[str, dict[str, dict[str, object]]] = {
            query_id: dict(products)
            for query_id, products in dict(
                existing_payload.get("judgments", {})
            ).items()
        }
        for row in rows:
            judgments.setdefault(row["query_id"], {})[row["product_id"]] = {
                "grade": int(row["relevance_grade"]),
                "review_status": "reviewed",
                "notes": row["notes"],
            }
        payload = {
            "version": 2,
            "grade_scale": {
                "0": "not relevant",
                "1": "weakly relevant",
                "2": "relevant alternative",
                "3": "exact or fully relevant",
            },
            "default_rule": "Every acceptable_product_id receives grade 3.",
            "review_scope": (
                "All reviewed Top-5 candidates observed across approved robustness runs."
            ),
            "judgments": judgments,
        }
        args.judgments.parent.mkdir(parents=True, exist_ok=True)
        args.judgments.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.approve_all_drafts:
        print(f"Promoted {len(rows)} reviewed judgments to {args.judgments}.")
    else:
        print(f"Added {suggested} provisional grades; review_status remains pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
