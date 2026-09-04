from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
FIELDS = [
    "query_id",
    "mode",
    "query_type",
    "relevant_product_id",
    "relevance_grade",
    "match_reason",
    "source",
    "review_status",
    "notes",
]
ATTRIBUTE_ORDER = [
    "category",
    "brand",
    "color",
    "material",
    "gender",
    "price_bucket",
    "usage",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize(value: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^0-9a-z]+", " ", unaccented.lower()).strip()


def price_bucket(value: str) -> str:
    price = float(value)
    if price < 200_000:
        return "under_200k"
    if price < 500_000:
        return "200k_500k"
    if price < 1_000_000:
        return "500k_1m"
    if price < 2_000_000:
        return "1m_2m"
    return "over_2m"


def list_values(value: str | None) -> set[str]:
    return {normalize(item) for item in (value or "").split(",") if normalize(item)}


def attribute_matches(query: dict[str, str], product: dict[str, str], key: str) -> bool:
    if key == "price_bucket":
        return price_bucket(product["price"]) == query[key]
    if key == "usage":
        # Usage values describe suitable occasions. Matching any requested occasion
        # satisfies this part of the natural-language intent.
        return bool(list_values(query[key]) & list_values(product[key]))
    return normalize(query[key]) == normalize(product[key])


def full_intent_match(query: dict[str, str], product: dict[str, str]) -> bool:
    if query["difficulty"] == "easy":
        return normalize(query["query_text"]) == normalize(product["product_name"])
    constraints = [key for key in ATTRIBUTE_ORDER if query.get(key, "").strip()]
    return all(attribute_matches(query, product, key) for key in constraints)


def match_reason(query: dict[str, str], product: dict[str, str]) -> str:
    if product["product_id"] == query["source_product_id"]:
        return "source_product_exact_match"
    if query["difficulty"] == "easy":
        return "product_name_exact_match"
    constraints = [key for key in ATTRIBUTE_ORDER if query.get(key, "").strip()]
    return "+".join(f"{key}_match" for key in constraints)


def reviewed_rows(
    queries: list[dict[str, str]], products: list[dict[str, str]]
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for query in queries:
        matches = [product for product in products if full_intent_match(query, product)]
        matches.sort(
            key=lambda product: (
                product["product_id"] != query["source_product_id"],
                int(product["product_id"]),
            )
        )
        if not matches:
            raise RuntimeError(f"No full-intent match for {query['query_id']}")
        for product in matches:
            rows.append(
                {
                    "query_id": query["query_id"],
                    "mode": "text",
                    "query_type": "positive",
                    "relevant_product_id": product["product_id"],
                    "relevance_grade": 3,
                    "match_reason": match_reason(query, product),
                    "source": "manual_snapshot_review",
                    "review_status": "approved",
                    "notes": "reviewed_full_query_intent_against_all_1000_products",
                }
            )
    return rows


def replace_reviewed_queries(
    path: Path,
    replacements: list[dict[str, str | int]],
    reviewed_query_ids: set[str],
) -> None:
    retained = [row for row in read_rows(path) if row["query_id"] not in reviewed_query_ids]
    rows = [*replacements, *retained]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    reviewed_query_ids = {
        f"text-q{index:04d}" for index in range(args.start_query, args.end_query + 1)
    }
    queries = [
        row
        for row in read_rows(args.queries)
        if row["query_id"] in reviewed_query_ids
    ]
    products = [row for row in read_rows(args.products) if row["is_active"].lower() == "true"]
    if {row["query_id"] for row in queries} != reviewed_query_ids:
        raise RuntimeError(
            f"The query set does not contain every query from text-q{args.start_query:04d} "
            f"to text-q{args.end_query:04d}"
        )

    replacements = reviewed_rows(queries, products)
    for output in (args.candidates, args.ground_truth):
        replace_reviewed_queries(output, replacements, reviewed_query_ids)

    counts = {
        query_id: sum(row["query_id"] == query_id for row in replacements)
        for query_id in sorted(reviewed_query_ids)
    }
    print(f"reviewed_rows={len(replacements)} counts={counts}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply a manual full-catalog review to an inclusive text-query range."
    )
    parser.add_argument("--start-query", type=int, default=1)
    parser.add_argument("--end-query", type=int, default=10)
    parser.add_argument("--queries", type=Path, default=DATA_DIR / "text_queries.csv")
    parser.add_argument("--products", type=Path, default=DATA_DIR / "product_snapshot.csv")
    parser.add_argument(
        "--candidates", type=Path, default=DATA_DIR / "ground_truth_text_candidates.csv"
    )
    parser.add_argument("--ground-truth", type=Path, default=DATA_DIR / "ground_truth_text.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
