from __future__ import annotations

import argparse
import csv
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
QUERY_FIELDS = [
    "query_id", "mode", "query_type", "intent_type", "constraint_semantics",
    "expected_behavior", "source_product_id", "query_text",
    "category", "brand", "color", "material", "gender", "price_bucket",
    "usage", "difficulty", "expected_relevant_count", "retrieval_scope",
    "manual_status", "notes",
]
GT_FIELDS = [
    "query_id", "mode", "query_type", "intent_type", "constraint_semantics",
    "expected_behavior", "relevant_product_id",
    "relevance_grade", "match_reason", "source", "review_status", "notes",
]

NEGATIVE_CASES = [
    ("áo khoác lông cừu màu tím neon dưới 100k", "negative_impossible"),
    ("váy cưới đính kim cương chống nước", "negative_impossible"),
    ("giày trượt tuyết màu bạc cho mùa hè", "negative_ood"),
    ("quần jean chống cháy màu vàng neon", "negative_impossible"),
    ("áo hoodie da cá sấu màu hồng pastel", "negative_impossible"),
    ("túi xách leo núi bằng lông cừu", "negative_ood"),
    ("đầm dạ hội bằng vàng 24k", "negative_impossible"),
    ("áo sơ mi kim loại chống đạn", "negative_impossible"),
    ("giày cao gót leo núi chống trượt", "negative_ood"),
    ("áo phao mùa hè trong suốt dưới 50k", "negative_impossible"),
]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return " ".join(
        re.sub(r"[^a-z0-9 ]+", " ", value.encode("ascii", "ignore").decode().lower()).split()
    )


def price_bucket(value: str) -> str:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return ""
    if price < 200_000:
        return "under_200k"
    if price < 500_000:
        return "200k_500k"
    if price < 1_000_000:
        return "500k_1m"
    if price < 2_000_000:
        return "1m_2m"
    return "over_2m"


def category_name(row: dict[str, str]) -> str:
    return row["category"].strip().lower()


def attribute_value(row: dict[str, str], key: str) -> str:
    return price_bucket(row["price"]) if key == "price_bucket" else row[key].strip()


def _split_facets(value: str, pattern: str) -> list[str]:
    return [part.strip() for part in re.split(pattern, value or "") if part.strip()]


def facet_values(row: dict[str, str], key: str) -> list[str]:
    value = attribute_value(row, key)
    if not value:
        return []
    if key == "material":
        facets: list[str] = []
        for part in _split_facets(value, r"\s*[,;/+]\s*"):
            part = re.sub(r"^\d+(?:\.\d+)?%\s*", "", part).strip()
            parenthetical = re.findall(r"\(([^()]+)\)", part)
            facet = parenthetical[-1].strip() if parenthetical else part
            if facet:
                facets.append(facet)
        return list(dict.fromkeys(facets))
    if key == "usage":
        return list(dict.fromkeys(_split_facets(value, r"\s*[,;/]\s*")))
    if key == "color":
        return list(dict.fromkeys(_split_facets(value, r"\s*[/;]\s*")))
    return [value]


def selected_facet(row: dict[str, str], key: str, query_id: str) -> str:
    facets = facet_values(row, key)
    if not facets:
        return ""
    stable_offset = sum(ord(character) for character in f"{query_id}:{key}")
    return facets[stable_offset % len(facets)]


def display_value(key: str, value: str) -> str:
    if key == "color":
        return f"màu {value.lower()}"
    if key == "material":
        return f"chất liệu {value.lower()}"
    if key == "gender":
        return f"cho {value.lower()}"
    if key == "price_bucket":
        labels = {
            "under_200k": "giá dưới 200k", "200k_500k": "giá 200k đến 500k",
            "500k_1m": "giá 500k đến 1 triệu", "1m_2m": "giá 1 đến 2 triệu",
            "over_2m": "giá trên 2 triệu",
        }
        return labels.get(value, "")
    if key == "usage":
        return f"phù hợp {value.lower()}"
    return value.lower()


def choose_products(products: list[dict[str, str]], count: int, rng: random.Random) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for product in products:
        groups[category_name(product)].append(product)
    for group in groups.values():
        rng.shuffle(group)
    chosen: list[dict[str, str]] = []
    categories = sorted(groups)
    cursor = 0
    while len(chosen) < count:
        category = categories[cursor % len(categories)]
        if groups[category]:
            chosen.append(groups[category].pop())
        cursor += 1
    rng.shuffle(chosen)
    return chosen


def matches_facets(
    product: dict[str, str],
    category: str,
    selected_attributes: dict[str, str],
) -> bool:
    if normalize(category_name(product)) != normalize(category):
        return False
    for key, selected_value in selected_attributes.items():
        available = {normalize(value) for value in facet_values(product, key)}
        if not normalize(selected_value) or normalize(selected_value) not in available:
            return False
    return True


def matched_facet_count(product: dict[str, str], selected_attributes: dict[str, str]) -> int:
    return sum(
        normalize(selected_value) in {normalize(value) for value in facet_values(product, key)}
        for key, selected_value in selected_attributes.items()
    )


def retrieval_scope(relevant_count: int) -> str:
    if relevant_count <= 1:
        return "singleton"
    if relevant_count <= 20:
        return "bounded"
    return "broad"


def preserved_query_definitions(
    path: Path,
    products_by_id: dict[str, dict[str, str]],
) -> list[tuple[str, dict[str, str], str, list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if row.get("query_type") == "positive"
        ]
    rows.sort(key=lambda row: row["query_id"])
    expected_ids = [f"text-q{index:04d}" for index in range(1, 91)]
    actual_ids = [row.get("query_id", "") for row in rows]
    if actual_ids != expected_ids:
        raise RuntimeError(
            "Existing query set must contain exactly text-q0001 through "
            f"text-q0090, got {actual_ids}"
        )

    definitions: list[tuple[str, dict[str, str], str, list[str]]] = []
    valid_attributes = {"color", "material", "usage", "gender", "price_bucket", "brand"}
    for row in rows:
        query_id = row["query_id"]
        source_id = row.get("source_product_id", "").strip()
        source = products_by_id.get(source_id)
        if source is None:
            raise RuntimeError(f"Source product {source_id!r} for {query_id} is absent from the new snapshot")
        difficulty = row.get("difficulty", "").strip()
        if difficulty not in {"easy", "medium", "hard"}:
            raise RuntimeError(f"Unsupported difficulty {difficulty!r} for {query_id}")

        match = re.search(r"(?:^|;)constraints=([^;]+)", row.get("notes", ""))
        constraints = match.group(1).split("+") if match else []
        expected_prefix = "product_name" if difficulty == "easy" else "category"
        if not constraints or constraints[0] != expected_prefix:
            raise RuntimeError(f"Invalid preserved constraints for {query_id}: {constraints}")
        selected_attributes = constraints[1:]
        invalid_attributes = set(selected_attributes) - valid_attributes
        if invalid_attributes:
            raise RuntimeError(f"Invalid preserved attributes for {query_id}: {sorted(invalid_attributes)}")
        missing_attributes = [
            key for key in selected_attributes
            if not attribute_value(source, key)
        ]
        if missing_attributes:
            raise RuntimeError(
                f"New snapshot is missing preserved attributes for {query_id}: {missing_attributes}"
            )
        definitions.append((query_id, source, difficulty, selected_attributes))
    return definitions


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    with args.snapshot.open(encoding="utf-8-sig", newline="") as handle:
        products = [
            row for row in csv.DictReader(handle)
            if row["is_active"].lower() == "true" and row["category"].strip()
        ]
    if len(products) != 1000:
        raise RuntimeError(f"Expected 1000 active products, got {len(products)}")

    products_by_id = {product["product_id"]: product for product in products}
    if args.existing_queries:
        definitions = preserved_query_definitions(args.existing_queries, products_by_id)
    else:
        selected = choose_products(products, 90, rng)
        difficulties = ["easy"] * 30 + ["medium"] * 30 + ["hard"] * 30
        rng.shuffle(difficulties)
        definitions = []
        attribute_order = ["color", "material", "usage", "gender", "price_bucket", "brand"]
        for index, (source, difficulty) in enumerate(zip(selected, difficulties), 1):
            available = [key for key in attribute_order if attribute_value(source, key)]
            needed = {"easy": 0, "medium": 1, "hard": 3}[difficulty]
            start = (index - 1) % max(1, len(available))
            selected_attributes = [
                available[(start + offset) % len(available)]
                for offset in range(min(needed, len(available)))
            ]
            definitions.append((f"text-q{index:04d}", source, difficulty, selected_attributes))

    query_rows: list[dict[str, str]] = []
    gt_rows: list[dict[str, str | int]] = []
    candidate_rows: list[dict[str, str | int]] = []

    for query_id, source, difficulty, selected_attributes in definitions:
        if difficulty == "easy":
            constraints = ["product_name"]
            query_text = source["product_name"].strip().lower()
            intent_type = "exact_title"
            constraint_semantics = "exact"
            selected_values: dict[str, str] = {}
            relevant = [
                product
                for product in products
                if normalize(product["product_name"]) == normalize(source["product_name"])
            ]
        else:
            constraints = ["category", *selected_attributes]
            intent_type = "facet_single" if difficulty == "medium" else "facet_all"
            constraint_semantics = "all"
            selected_values = {
                key: selected_facet(source, key, query_id)
                for key in selected_attributes
            }
            query_text = " ".join([
                category_name(source),
                *(display_value(key, selected_values[key]) for key in selected_attributes),
            ]).strip()
            relevant = [
                product
                for product in products
                if matches_facets(product, category_name(source), selected_values)
            ]
        relevant.sort(key=lambda product: int(product["product_id"]))
        row = {field: "" for field in QUERY_FIELDS}
        row.update({
            "query_id": query_id, "mode": "text", "query_type": "positive",
            "intent_type": intent_type,
            "constraint_semantics": constraint_semantics,
            "expected_behavior": "retrieve",
            "source_product_id": source["product_id"], "query_text": query_text,
            "category": source["category"], "difficulty": difficulty,
            "expected_relevant_count": len(relevant),
            "retrieval_scope": retrieval_scope(len(relevant)),
            "manual_status": "approved",
            "notes": f"mysql_1000_balanced_v2;constraints={'+'.join(constraints)}",
        })
        for key, selected_value in selected_values.items():
            row[key] = selected_value
        query_rows.append(row)

        for product in relevant:
            ground_truth_row = {
                "query_id": query_id, "mode": "text", "query_type": "positive",
                "intent_type": intent_type,
                "constraint_semantics": constraint_semantics,
                "expected_behavior": "retrieve",
                "relevant_product_id": product["product_id"],
                "relevance_grade": 3,
                "match_reason": "+".join(f"{key}_match" for key in constraints),
                "source": "mysql_snapshot_canonical_rule_v2", "review_status": "approved",
                "notes": "full_intent_match_against_all_1000_products",
            }
            gt_rows.append(ground_truth_row)
            candidate_rows.append(dict(ground_truth_row))

        if difficulty != "easy":
            relevant_ids = {product["product_id"] for product in relevant}
            for product in products:
                if (
                    product["product_id"] in relevant_ids
                    or normalize(category_name(product)) != normalize(category_name(source))
                ):
                    continue
                matched_count = matched_facet_count(product, selected_values)
                if not selected_values:
                    continue
                if matched_count >= max(1, len(selected_values) - 1):
                    grade = 2
                elif matched_count >= 1:
                    grade = 1
                else:
                    continue
                candidate_rows.append({
                    "query_id": query_id, "mode": "text", "query_type": "positive",
                    "intent_type": intent_type,
                    "constraint_semantics": constraint_semantics,
                    "expected_behavior": "retrieve",
                    "relevant_product_id": product["product_id"],
                    "relevance_grade": grade,
                    "match_reason": f"partial_facet_match_{matched_count}_of_{len(selected_values)}",
                    "source": "mysql_snapshot_candidate_rule_v2", "review_status": "pending",
                    "notes": "requires_manual_semantic_review_before_ground_truth",
                })

    for offset, (query_text, intent_type) in enumerate(NEGATIVE_CASES, 91):
        query_id = f"text-q{offset:04d}"
        row = {field: "" for field in QUERY_FIELDS}
        row.update({
            "query_id": query_id, "mode": "text", "query_type": "negative",
            "intent_type": intent_type, "constraint_semantics": "none",
            "expected_behavior": "empty",
            "query_text": query_text, "difficulty": "adversarial",
            "expected_relevant_count": 0, "retrieval_scope": "none",
            "manual_status": "approved", "notes": "expected_empty_mysql_1000_v2",
        })
        query_rows.append(row)
        ground_truth_row = {
            "query_id": query_id, "mode": "text", "query_type": "negative",
            "intent_type": intent_type, "constraint_semantics": "none",
            "expected_behavior": "empty",
            "relevant_product_id": "", "relevance_grade": 0,
            "match_reason": "expected_empty", "source": "mysql_snapshot_rule_v2",
            "review_status": "approved", "notes": "validated_absent_by_contract",
        }
        gt_rows.append(ground_truth_row)
        candidate_rows.append(dict(ground_truth_row))

    write_csv(args.queries, query_rows, QUERY_FIELDS)
    write_csv(args.ground_truth, gt_rows, GT_FIELDS)
    write_csv(args.candidates, candidate_rows, GT_FIELDS)
    print(
        f"queries={len(query_rows)} ground_truth_rows={len(gt_rows)} "
        f"candidate_rows={len(candidate_rows)}"
    )
    print(f"difficulty={dict(Counter(row['difficulty'] for row in query_rows))}")
    print(f"categories={len(set(row['category'] for row in query_rows if row['category']))}")
    return 0


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--snapshot", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument(
        "--existing-queries",
        type=Path,
        default=None,
        help="Preserve query IDs, source product IDs, difficulties, and constraints from an existing query set",
    )
    parser.add_argument("--queries", type=Path, default=SCRIPT_DIR.parent / "data" / "text_queries_v2.csv")
    parser.add_argument("--ground-truth", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_text_v2.csv")
    parser.add_argument("--candidates", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_text_candidates_v2.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
