from __future__ import annotations

import argparse
import csv
import random
import re
import unicodedata
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
QUERY_FIELDS = [
    "query_id", "mode", "source_image_query_id", "source_product_id",
    "image_id", "source_image_url", "image_url", "image_origin", "image_status",
    "image_edit_request", "reference_category", "reference_color",
    "reference_material", "reference_usage", "reference_price_bucket",
    "query_text", "transformation_type", "difficulty", "target_product_id",
    "category", "color", "material", "price_bucket", "usage",
    "candidate_count", "manual_status", "notes",
]
GT_FIELDS = [
    "query_id", "mode", "query_type", "relevant_product_id",
    "relevance_grade", "match_reason", "source", "review_status", "notes",
]
REQUIREMENT_FIELDS = [
    "query_id", "difficulty", "transformation_type", "source_image_query_id",
    "source_product_id", "category", "source_image_url", "source_color",
    "source_material", "required_reference_color", "required_reference_material",
    "target_text_color", "target_text_material", "image_edit_request",
    "new_image_url", "review_status", "notes",
]
TRANSFORMATION_COUNTS = {
    "easy": {"color": 17, "material": 17},
    "medium": {"usage": 17, "price": 16},
    "hard": {"color_material": 11, "color_usage": 11, "material_usage": 11},
}
ALT_COLORS = ["Đỏ", "Xanh cobalt", "Vàng", "Hồng fuchsia", "Trắng", "Đen"]
ALT_MATERIALS = ["Denim", "Da bóng", "Len dệt kim", "Satin", "Vải lanh"]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", value).split())


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


def price_text(bucket: str) -> str:
    return {
        "under_200k": "dưới 200k", "200k_500k": "từ 200k đến 500k",
        "500k_1m": "từ 500k đến 1 triệu", "1m_2m": "từ 1 đến 2 triệu",
        "over_2m": "trên 2 triệu",
    }.get(bucket, bucket)


def material_text(value: str) -> str:
    return re.sub(r"\b\d+(?:\.\d+)?%\s*", "", value or "").split(";")[0].strip().lower()


def constraints_for(product: dict[str, str], kind: str) -> dict[str, str]:
    constraints = {"category": product["category"].strip()}
    if "color" in kind:
        constraints["color"] = product["color"].strip()
    if "material" in kind:
        constraints["material"] = product["material"].strip()
    if "usage" in kind:
        constraints["usage"] = product["usage"].strip()
    if kind == "price":
        constraints["price_bucket"] = price_bucket(product["price"])
    return constraints


def matches(product: dict[str, str], constraints: dict[str, str]) -> bool:
    for key, expected in constraints.items():
        actual = price_bucket(product["price"]) if key == "price_bucket" else product[key]
        if not normalize(actual) or normalize(actual) != normalize(expected):
            return False
    return True


def query_text(product: dict[str, str], kind: str) -> str:
    category = product["category"].lower()
    color = product["color"].lower()
    material = material_text(product["material"])
    usage = product["usage"].lower()
    templates = {
        "color": f"tìm {category} giống ảnh nhưng đổi sang màu {color}",
        "material": f"tìm {category} giống ảnh nhưng đổi sang chất liệu {material}",
        "usage": f"tìm {category} giống ảnh, phù hợp {usage}",
        "price": f"tìm {category} giống ảnh, giá {price_text(price_bucket(product['price']))}",
        "color_material": f"tìm {category} giống ảnh nhưng đổi sang màu {color}, chất liệu {material}",
        "color_usage": f"tìm {category} giống ảnh nhưng đổi sang màu {color}, phù hợp {usage}",
        "material_usage": f"tìm {category} giống ảnh nhưng đổi sang chất liệu {material}, phù hợp {usage}",
    }
    return templates[kind]


def choose_alternative(original: str, choices: list[str], offset: int) -> str:
    rotated = choices[offset % len(choices):] + choices[:offset % len(choices)]
    original_normalized = normalize(original)
    for choice in rotated:
        choice_normalized = normalize(choice)
        if choice_normalized not in original_normalized and original_normalized not in choice_normalized:
            return choice
    raise RuntimeError(f"No alternative found for {original}")


def edit_request(product: dict[str, str], kind: str, alt_color: str, alt_material: str) -> str:
    instructions = ["Giữ nguyên sản phẩm, kiểu dáng, họa tiết, bố cục và góc chụp"]
    if "color" in kind:
        instructions.append(f"đổi màu sản phẩm từ {product['color']} sang {alt_color}")
    if "material" in kind:
        instructions.append(f"đổi bề mặt chất liệu từ {product['material']} sang {alt_material}")
    instructions.append("không thêm hoặc xóa chi tiết thiết kế")
    return "; ".join(instructions) + "."


def assign_transformations(images, products_by_id, rng):
    assignments = {}
    for difficulty, counts in TRANSFORMATION_COUNTS.items():
        subset = [row for row in images if row["difficulty"] == difficulty]
        kinds = [kind for kind, count in counts.items() for _ in range(count)]
        if len(subset) != len(kinds):
            raise RuntimeError(f"Unexpected {difficulty} image count: {len(subset)}")
        for _ in range(10_000):
            rng.shuffle(subset)
            rng.shuffle(kinds)
            proposal = dict(zip((row["query_id"] for row in subset), kinds))
            valid = True
            for image in subset:
                product = products_by_id.get(image["source_product_id"])
                if product is None:
                    raise RuntimeError(f"{image['query_id']}: source product not found")
                constraints = constraints_for(product, proposal[image["query_id"]])
                if not all(normalize(value) for value in constraints.values()):
                    valid = False
                    break
            if valid:
                assignments.update(proposal)
                break
        else:
            raise RuntimeError(f"Cannot assign transformations for {difficulty}")
    return assignments


def read_existing_urls(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["query_id"]: row.get("new_image_url", "").strip()
            for row in csv.DictReader(handle)
        }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    with args.products_csv.open(encoding="utf-8-sig", newline="") as handle:
        products = [row for row in csv.DictReader(handle) if row["is_active"].lower() == "true"]
    with args.image_queries_csv.open(encoding="utf-8-sig", newline="") as handle:
        images = list(csv.DictReader(handle))
    if len(products) != 1000 or len(images) != 100:
        raise RuntimeError(f"Expected 1000 products and 100 images, got {len(products)} and {len(images)}")
    products_by_id = {row["product_id"]: row for row in products}
    assignments = assign_transformations(images, products_by_id, rng)
    existing_urls = read_existing_urls(args.requirements_csv)
    images.sort(key=lambda row: int(row["query_id"].split("q")[-1]))

    query_rows, gt_rows, sampled_rows, requirement_rows = [], [], [], []
    for index, image in enumerate(images, 1):
        query_id = f"multimodal-q{index:04d}"
        kind = assignments[image["query_id"]]
        target = products_by_id[image["source_product_id"]]
        constraints = constraints_for(target, kind)
        candidates = [product for product in products if matches(product, constraints)]
        candidates.sort(key=lambda row: (row["product_id"] != target["product_id"], int(row["product_id"])))
        needs_edit = "color" in kind or "material" in kind
        alt_color = choose_alternative(target["color"], ALT_COLORS, index) if "color" in kind else image["color"]
        alt_material = choose_alternative(target["material"], ALT_MATERIALS, index) if "material" in kind else image["material"]
        request = edit_request(target, kind, alt_color, alt_material) if needs_edit else ""
        final_url = existing_urls.get(query_id, "") if needs_edit else image["image_url"]
        image_status = (
            "awaiting_edited_url" if needs_edit and not final_url
            else "provided_pending_review" if needs_edit
            else "approved_reused"
        )
        manual_status = "awaiting_edited_url" if needs_edit and not final_url else "pending_hybrid_review"
        query_rows.append({
            "query_id": query_id, "mode": "multimodal",
            "source_image_query_id": image["query_id"],
            "source_product_id": target["product_id"], "image_id": image["source_image_id"],
            "source_image_url": image["image_url"], "image_url": final_url,
            "image_origin": "user_edited_counterfactual" if needs_edit else "image_evaluation_external",
            "image_status": image_status, "image_edit_request": request,
            "reference_category": target["category"], "reference_color": alt_color,
            "reference_material": alt_material, "reference_usage": target["usage"],
            "reference_price_bucket": price_bucket(target["price"]),
            "query_text": query_text(target, kind), "transformation_type": kind,
            "difficulty": image["difficulty"], "target_product_id": target["product_id"],
            "category": target["category"], "color": constraints.get("color", ""),
            "material": constraints.get("material", ""),
            "price_bucket": constraints.get("price_bucket", ""),
            "usage": constraints.get("usage", ""), "candidate_count": len(candidates),
            "manual_status": manual_status,
            "notes": "counterfactual_reference_image;target_is_source_database_product",
        })
        sampled_rows.append({
            "query_id": query_id, "source_image_query_id": image["query_id"],
            "source_product_id": target["product_id"], "source_image_url": image["image_url"],
            "image_url": final_url, "target_product_id": target["product_id"],
            "transformation_type": kind, "difficulty": image["difficulty"],
        })
        if needs_edit:
            requirement_rows.append({
                "query_id": query_id, "difficulty": image["difficulty"],
                "transformation_type": kind, "source_image_query_id": image["query_id"],
                "source_product_id": target["product_id"], "category": target["category"],
                "source_image_url": image["image_url"], "source_color": target["color"],
                "source_material": target["material"], "required_reference_color": alt_color,
                "required_reference_material": alt_material,
                "target_text_color": constraints.get("color", ""),
                "target_text_material": constraints.get("material", ""),
                "image_edit_request": request, "new_image_url": final_url,
                "review_status": "awaiting_url" if not final_url else "pending_review",
                "notes": "Fill new_image_url with the edited image; do not replace source_image_url.",
            })
        for candidate in candidates[:30]:
            gt_rows.append({
                "query_id": query_id, "mode": "multimodal", "query_type": "positive",
                "relevant_product_id": candidate["product_id"],
                "relevance_grade": 3 if candidate["product_id"] == target["product_id"] else 2,
                "match_reason": "+".join(f"target_{key}_match" for key in constraints),
                "source": "controlled_counterfactual_rule",
                "review_status": "awaiting_edited_url" if needs_edit and not final_url else "pending_hybrid_review",
                "notes": "approve_after_edited_image_and_visual_similarity_review",
            })

    write_csv(args.queries_csv, query_rows, QUERY_FIELDS)
    write_csv(args.sampled_csv, sampled_rows, list(sampled_rows[0]))
    write_csv(args.ground_truth_csv, gt_rows, GT_FIELDS)
    write_csv(args.candidates_csv, gt_rows, GT_FIELDS)
    write_csv(args.requirements_csv, requirement_rows, REQUIREMENT_FIELDS)
    print(f"queries={len(query_rows)} candidate_rows={len(gt_rows)}")
    print(f"transformations={dict(Counter(row['transformation_type'] for row in query_rows))}")
    print(f"reused_ready_urls={sum(bool(row['image_url']) for row in query_rows)}")
    print(f"edited_urls_required={sum(not row['new_image_url'] for row in requirement_rows)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--products-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--image-queries-csv", type=Path, default=SCRIPT_DIR.parent.parent / "image" / "data" / "image_queries.csv")
    parser.add_argument("--queries-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "multimodal_queries.csv")
    parser.add_argument("--sampled-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "sampled_multimodal_items.csv")
    parser.add_argument("--ground-truth-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_multimodal.csv")
    parser.add_argument("--candidates-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_multimodal_candidates.csv")
    parser.add_argument("--requirements-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "reference_image_requirements.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
