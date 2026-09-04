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
    "query_id", "mode", "source_product_id", "source_image_id", "image_url",
    "db_image_type", "semantic_image_type", "category", "brand", "color",
    "material", "gender", "image_quality", "difficulty", "manual_status", "notes",
]
ANNOTATION_FIELDS = [
    "source_image_id", "source_product_id", "image_url", "db_image_type",
    "sort_order", "semantic_image_type", "image_quality", "difficulty",
    "review_status", "notes",
]
GT_FIELDS = [
    "query_id", "mode", "query_type", "source_image_id", "relevant_product_id",
    "relevance_grade", "match_reason", "source", "review_status", "notes",
]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return " ".join(
        re.sub(r"[^a-z0-9 ]+", " ", value.encode("ascii", "ignore").decode().lower()).split()
    )


def difficulty_for(image_type: str) -> str:
    value = image_type.upper()
    if value == "MAIN" or value.startswith("FLAT"):
        return "easy"
    if value.startswith("MODEL") or value in {"REAR", "ULT"}:
        return "medium"
    if value.startswith("DETAIL"):
        return "hard"
    return ""


def semantic_type(image_type: str) -> str:
    difficulty = difficulty_for(image_type)
    if image_type.upper().startswith("FLAT"):
        return "flatlay"
    return {"easy": "front", "medium": "lifestyle", "hard": "detail"}.get(difficulty, "unknown")


def stratified_sample(
    candidates: list[dict[str, str]], count: int, rng: random.Random,
    excluded_products: set[str],
) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for image in candidates:
        if image["product_id"] not in excluded_products:
            groups[image["category"]].append(image)
    for group in groups.values():
        rng.shuffle(group)
    categories = sorted(groups)
    selected: list[dict[str, str]] = []
    cursor = 0
    while len(selected) < count:
        category = categories[cursor % len(categories)]
        group = groups[category]
        while group and group[-1]["product_id"] in excluded_products:
            group.pop()
        if group:
            image = group.pop()
            selected.append(image)
            excluded_products.add(image["product_id"])
        cursor += 1
        if cursor > count * max(1, len(categories)) * 10:
            raise RuntimeError("Not enough distinct products for balanced sampling")
    return selected


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    with args.products_csv.open(encoding="utf-8-sig", newline="") as handle:
        products = list(csv.DictReader(handle))
    with args.images_csv.open(encoding="utf-8-sig", newline="") as handle:
        raw_images = list(csv.DictReader(handle))
    if len(products) != 1000:
        raise RuntimeError(f"Expected 1000 products, got {len(products)}")

    product_by_id = {row["product_id"]: row for row in products}
    images: list[dict[str, str]] = []
    for image in raw_images:
        product = product_by_id.get(image["product_id"])
        difficulty = difficulty_for(image["image_type"])
        if not product or not difficulty:
            continue
        images.append({**image, **product, "difficulty": difficulty})

    excluded_products: set[str] = set()
    selected = []
    for difficulty, count in (("easy", 34), ("medium", 33), ("hard", 33)):
        bucket = [row for row in images if row["difficulty"] == difficulty]
        selected.extend(stratified_sample(bucket, count, rng, excluded_products))
    rng.shuffle(selected)

    query_rows = []
    annotation_rows = []
    gt_rows = []
    sampled_rows = []
    for index, image in enumerate(selected, 1):
        query_id = f"image-q{index:04d}"
        difficulty = image["difficulty"]
        semantic = semantic_type(image["image_type"])
        quality = {"easy": "good", "medium": "medium", "hard": "hard"}[difficulty]
        query_rows.append({
            "query_id": query_id, "mode": "image",
            "source_product_id": image["product_id"],
            "source_image_id": image["source_image_id"],
            "image_url": image["image_url"], "db_image_type": image["image_type"],
            "semantic_image_type": semantic, "category": image["category"],
            "brand": image["brand"], "color": image["color"],
            "material": image["material"], "gender": image["gender"],
            "image_quality": quality, "difficulty": difficulty,
            "manual_status": "approved",
            "notes": "balanced_from_mysql_1000",
        })
        annotation_rows.append({
            "source_image_id": image["source_image_id"],
            "source_product_id": image["product_id"], "image_url": image["image_url"],
            "db_image_type": image["image_type"], "sort_order": image["sort_order"],
            "semantic_image_type": semantic, "image_quality": quality,
            "difficulty": difficulty, "review_status": "approved",
            "notes": "mapped_from_mysql_image_type",
        })
        sampled_rows.append({
            "source_image_id": image["source_image_id"],
            "source_product_id": image["product_id"],
            "product_name": image["product_name"], "category": image["category"],
            "brand": image["brand"], "color": image["color"],
            "material": image["material"], "gender": image["gender"],
            "image_url": image["image_url"], "db_image_type": image["image_type"],
            "sort_order": image["sort_order"],
            "image_count": sum(1 for row in raw_images if row["product_id"] == image["product_id"]),
            "difficulty": difficulty,
        })

        scored = []
        for product in products:
            category_match = normalize(product["category"]) == normalize(image["category"])
            if not category_match:
                continue
            matches = sum(
                bool(normalize(product[key])) and normalize(product[key]) == normalize(image[key])
                for key in ("color", "material", "gender")
            )
            exact = product["product_id"] == image["product_id"]
            grade = 3 if exact else (2 if matches >= 2 else 1)
            scored.append((grade, exact, int(product["product_id"]), product))
        scored.sort(key=lambda item: (-item[0], not item[1], item[2]))
        for grade, exact, _, product in scored[:30]:
            gt_rows.append({
                "query_id": query_id, "mode": "image", "query_type": "positive",
                "source_image_id": image["source_image_id"],
                "relevant_product_id": product["product_id"],
                "relevance_grade": grade,
                "match_reason": "source_product_exact_match" if exact else "visual_metadata_similarity",
                "source": "mysql_snapshot_rule", "review_status": "approved",
                "notes": "generated_against_all_1000_products",
            })

    write_csv(args.queries_csv, query_rows, QUERY_FIELDS)
    write_csv(args.annotations_csv, annotation_rows, ANNOTATION_FIELDS)
    write_csv(args.sampled_csv, sampled_rows, list(sampled_rows[0]))
    write_csv(args.ground_truth_csv, gt_rows, GT_FIELDS)
    write_csv(args.candidates_csv, gt_rows, GT_FIELDS)
    print(f"queries={len(query_rows)} ground_truth_rows={len(gt_rows)}")
    print(f"difficulty={dict(Counter(row['difficulty'] for row in query_rows))}")
    print(f"categories={len(set(row['category'] for row in query_rows))}")
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
    parser.add_argument("--products-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--images-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_images.csv")
    parser.add_argument("--sampled-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "sampled_images.csv")
    parser.add_argument("--annotations-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_annotations.csv")
    parser.add_argument("--queries-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_queries.csv")
    parser.add_argument("--ground-truth-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_image.csv")
    parser.add_argument("--candidates-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_image_candidates.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
