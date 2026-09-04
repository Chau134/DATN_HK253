from __future__ import annotations

import csv
import json
import math
import random
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

PRICE_BUCKETS = (
    (200_000, "under_200k", "dưới 200k"),
    (500_000, "200k_500k", "200k đến 500k"),
    (1_000_000, "500k_1m", "500k đến 1 triệu"),
    (2_000_000, "1m_2m", "1 đến 2 triệu"),
)


@dataclass(frozen=True)
class ProductRecord:
    product_id: str
    product_name: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    price: float | None
    usage: str
    is_active: bool
    description: str = ""

    def to_row(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "category": self.category,
            "brand": self.brand,
            "color": self.color,
            "material": self.material,
            "gender": self.gender,
            "price": "" if self.price is None else f"{self.price:.2f}",
            "usage": self.usage,
            "is_active": str(self.is_active).lower(),
            "description": self.description,
            "price_bucket": price_bucket(self.price),
        }


@dataclass(frozen=True)
class QueryRecord:
    query_id: str
    mode: str
    query_type: str
    source_product_id: str
    query_text: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    price_bucket: str
    usage: str
    manual_status: str
    notes: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GroundTruthRecord:
    query_id: str
    mode: str
    query_type: str
    relevant_product_id: str
    relevance_grade: int
    match_reason: str
    source: str
    review_status: str
    notes: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_json_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_non_empty(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            value = str(value).strip()
            if value:
                return value
    return ""


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9,.-]", "", text).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "active", "available"}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    lowered = strip_accents(str(text)).lower()
    lowered = re.sub(r"[^0-9a-z]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def has_text(text: str | None) -> bool:
    return bool(text and str(text).strip())


def token_contains(haystack: str | None, needle: str | None) -> bool:
    haystack_norm = normalize_text(haystack)
    needle_norm = normalize_text(needle)
    if not haystack_norm or not needle_norm:
        return False
    return needle_norm in haystack_norm or haystack_norm in needle_norm


def product_label(product: ProductRecord) -> str:
    return normalize_text(" ".join(filter(None, [product.product_name, product.category, product.brand, product.color, product.material, product.gender, product.usage])))


def price_bucket(price: float | None) -> str:
    if price is None:
        return "unknown"
    for threshold, bucket, _ in PRICE_BUCKETS:
        if price < threshold:
            return bucket
    return "over_2m"


def price_bucket_label(bucket: str) -> str:
    for _, current_bucket, label in PRICE_BUCKETS:
        if current_bucket == bucket:
            return label
    if bucket == "over_2m":
        return "trên 2 triệu"
    return bucket


def load_products(path: Path) -> list[ProductRecord]:
    rows = read_csv_rows(path)
    return [_product_from_row(row) for row in rows]


def _product_from_row(row: dict[str, str]) -> ProductRecord:
    return ProductRecord(
        product_id=first_non_empty(row, "product_id", "id", "external_id"),
        product_name=first_non_empty(row, "product_name", "product_display_name", "title", "name"),
        category=first_non_empty(row, "category", "category_name", "category_name_vi"),
        brand=first_non_empty(row, "brand", "brand_name"),
        color=first_non_empty(row, "color", "base_colour", "base_colour_vi", "colour1", "colour1_vi"),
        material=first_non_empty(row, "material", "material_vi"),
        gender=first_non_empty(row, "gender", "gender_vi"),
        price=parse_float(first_non_empty(row, "price", "effective_price", "discounted_price")),
        usage=first_non_empty(row, "usage", "product_usage", "product_usage_vi", "season"),
        is_active=parse_bool(first_non_empty(row, "is_active", "available", "active")),
        description=first_non_empty(row, "description", "description_vi"),
    )


def load_categories(path: Path) -> dict[str, dict[str, str]]:
    categories: dict[str, dict[str, str]] = {}
    for row in read_csv_rows(path):
        category_id = first_non_empty(row, "id", "category_id")
        if not category_id:
            continue
        categories[category_id] = row
    return categories


def load_product_category_map(path: Path) -> dict[str, list[str]]:
    product_categories: dict[str, list[str]] = {}
    for row in read_csv_rows(path):
        product_id = first_non_empty(row, "product_id")
        category_id = first_non_empty(row, "category_id")
        if not product_id or not category_id:
            continue
        product_categories.setdefault(product_id, []).append(category_id)
    return product_categories


def enrich_product_categories(
    products: list[ProductRecord],
    product_categories: dict[str, list[str]],
    categories: dict[str, dict[str, str]],
) -> list[ProductRecord]:
    if not product_categories or not categories:
        return products

    def category_name(category_row: dict[str, str]) -> str:
        return first_non_empty(category_row, "category_name_vi", "category_name")

    def category_rank(category_row: dict[str, str]) -> tuple[int, str]:
        level = normalize_text(first_non_empty(category_row, "category_level"))
        if level == "article type":
            priority = 0
        elif level == "sub":
            priority = 1
        else:
            priority = 2
        return priority, category_name(category_row)

    enriched: list[ProductRecord] = []
    for product in products:
        if has_text(product.category):
            enriched.append(product)
            continue
        category_ids = product_categories.get(product.product_id, [])
        resolved = ""
        if category_ids:
            ranked_rows = [categories[category_id] for category_id in category_ids if category_id in categories]
            ranked_rows.sort(key=category_rank)
            if ranked_rows:
                resolved = category_name(ranked_rows[0])
        enriched.append(
            ProductRecord(
                product_id=product.product_id,
                product_name=product.product_name,
                category=resolved,
                brand=product.brand,
                color=product.color,
                material=product.material,
                gender=product.gender,
                price=product.price,
                usage=product.usage,
                is_active=product.is_active,
                description=product.description,
            )
        )
    return enriched


def allocate_category_counts(products: list[ProductRecord], total_count: int, min_per_category: int, max_per_category: int) -> dict[str, int]:
    category_groups = group_products_by_category(products)
    categories = sorted(category_groups)
    if not categories:
        return {}

    total_available = sum(len(category_groups[category]) for category in categories)
    target_total = min(total_count, total_available)
    desired = {category: target_total * len(category_groups[category]) / total_available for category in categories}
    counts = {}
    for category in categories:
        capacity = min(max_per_category, len(category_groups[category]))
        counts[category] = min(capacity, max(min_per_category, math.floor(desired[category])))

    def total_assigned() -> int:
        return sum(counts.values())

    fractional = sorted(categories, key=lambda category: (desired[category] - math.floor(desired[category]), len(category_groups[category]), category), reverse=True)
    while total_assigned() < target_total:
        changed = False
        for category in fractional:
            capacity = min(max_per_category, len(category_groups[category]))
            if counts[category] < capacity:
                counts[category] += 1
                changed = True
                if total_assigned() >= target_total:
                    break
        if not changed:
            break

    while total_assigned() > target_total:
        reducible = sorted(categories, key=lambda category: (counts[category] - min_per_category, counts[category], category), reverse=True)
        adjusted = False
        for category in reducible:
            if counts[category] > min_per_category:
                counts[category] -= 1
                adjusted = True
                if total_assigned() <= target_total:
                    break
        if not adjusted:
            break

    return {category: count for category, count in counts.items() if count > 0}


def group_products_by_category(products: list[ProductRecord]) -> dict[str, list[ProductRecord]]:
    grouped: dict[str, list[ProductRecord]] = {}
    for product in products:
        category = product.category or "unknown"
        grouped.setdefault(category, []).append(product)
    return grouped


def sample_products_for_queries(
    products: list[ProductRecord],
    *,
    total_positive_count: int,
    seed: int,
    min_per_category: int,
    max_per_category: int,
) -> list[ProductRecord]:
    rng = random.Random(seed)
    active_products = [product for product in products if product.is_active]
    grouped = group_products_by_category(active_products)
    if not grouped:
        return []

    category_counts = allocate_category_counts(active_products, total_positive_count, min_per_category, max_per_category)
    sampled: list[ProductRecord] = []
    for category in sorted(category_counts):
        available = grouped.get(category, [])
        if not available:
            continue
        sample_size = min(category_counts[category], len(available))
        sampled.extend(rng.sample(available, sample_size))

    if len(sampled) < total_positive_count:
        remaining = [product for product in products if product.is_active and product not in sampled]
        rng.shuffle(remaining)
        sampled.extend(remaining[: total_positive_count - len(sampled)])

    return sampled[:total_positive_count]


# Catalog values are English (Zara data), but real Vietnamese shoppers type
# "áo sơ mi" not "Shirts & Blouses". These maps translate ONLY the query_text so
# it reads like a real user query; the CSV attribute columns keep the raw English
# values because 03_generate_ground_truth_candidates matches them against the catalog.
_CATEGORY_VI: dict[str, str] = {
    "dresses": "váy",
    "dress": "váy",
    "shirts blouses": "áo sơ mi",
    "shirts": "áo sơ mi",
    "blouses": "áo kiểu",
    "t shirts": "áo thun",
    "tshirts": "áo thun",
    "tops": "áo",
    "sweaters cardigans": "áo len",
    "sweaters": "áo len",
    "cardigans": "áo cardigan",
    "knitwear": "đồ len",
    "hoodies": "áo hoodie",
    "sweatshirts": "áo nỉ",
    "jackets": "áo khoác",
    "coats": "áo khoác dài",
    "blazers": "áo blazer",
    "jeans": "quần jean",
    "trousers": "quần dài",
    "pants": "quần dài",
    "shorts": "quần short",
    "skirts": "chân váy",
    "jumpsuits": "áo liền quần",
    "polo shirts": "áo polo",
    "polos": "áo polo",
    "shoes": "giày",
    "sneakers": "giày thể thao",
    "boots": "bốt",
    "sandals": "dép sandal",
    "heels": "giày cao gót",
    "bags": "túi xách",
    "backpacks": "balo",
    "accessories": "phụ kiện",
    "hats": "mũ",
    "scarves": "khăn",
    "belts": "thắt lưng",
    "socks": "tất",
    "underwear": "đồ lót",
    "swimwear": "đồ bơi",
}
_COLOR_VI: dict[str, str] = {
    "black": "đen",
    "white": "trắng",
    "red": "đỏ",
    "blue": "xanh dương",
    "navy": "xanh navy",
    "green": "xanh lá",
    "yellow": "vàng",
    "pink": "hồng",
    "purple": "tím",
    "orange": "cam",
    "brown": "nâu",
    "grey": "xám",
    "gray": "xám",
    "beige": "be",
    "ecru": "trắng ngà",
    "ivory": "ngà",
    "cream": "kem",
    "sand": "màu cát",
    "khaki": "kaki",
    "camel": "nâu camel",
    "taupe": "nâu xám",
    "multicoloured": "nhiều màu",
    "multicolored": "nhiều màu",
    "gold": "vàng gold",
    "silver": "bạc",
    "burgundy": "đỏ booc đô",
    "maroon": "đỏ đô",
    "turquoise": "xanh ngọc",
    "mint": "xanh mint",
    "lilac": "tím nhạt",
    "coral": "màu san hô",
    "olive": "xanh olive",
    "mustard": "vàng mù tạt",
    "nude": "màu nude",
}
_GENDER_VI: dict[str, str] = {
    "women": "nữ",
    "woman": "nữ",
    "men": "nam",
    "man": "nam",
    "unisex": "unisex",
    "girls": "bé gái",
    "boys": "bé trai",
    "kids": "trẻ em",
}
_USAGE_VI: dict[str, str] = {
    "casual": "hằng ngày",
    "party": "dự tiệc",
    "office": "công sở",
    "formal": "trang trọng",
    "sports": "thể thao",
    "sport": "thể thao",
    "date": "hẹn hò",
    "travel": "du lịch",
    "beach": "đi biển",
    "work": "đi làm",
    "wedding": "đám cưới",
    "home": "ở nhà",
    "gym": "tập gym",
    "outdoor": "dã ngoại",
    "smart": "lịch sự",
    "ethnic": "truyền thống",
}
_MATERIAL_VI: dict[str, str] = {
    "cotton": "cotton",
    "polyester": "polyester",
    "viscose": "viscose",
    "elastane": "elastane",
    "acrylic": "acrylic",
    "polyamide": "polyamide",
    "wool": "len",
    "linen": "vải lanh",
    "silk": "lụa",
    "leather": "da",
    "denim": "denim",
    "nylon": "nylon",
    "cashmere": "cashmere",
    "spandex": "spandex",
    "modal": "modal",
    "lyocell": "lyocell",
    "rayon": "rayon",
}


def _vi(value: str, mapping: dict[str, str]) -> str:
    if not has_text(value):
        return ""
    return mapping.get(normalize_text(value), value.strip())


def _color_phrase(color_vi: str) -> str:
    if not color_vi:
        return ""
    if color_vi.startswith("màu") or color_vi == "nhiều màu":
        return color_vi
    return f"màu {color_vi}"


def _material_vi(material: str) -> str:
    if not has_text(material):
        return ""
    normalized = normalize_text(material)
    best_fiber = ""
    best_percent = -1.0
    for match in re.finditer(r"(\d+)\s*([a-z]+)", normalized):
        fiber = _MATERIAL_VI.get(match.group(2))
        percent = float(match.group(1))
        if fiber and percent > best_percent:
            best_percent = percent
            best_fiber = fiber
    if best_fiber:
        return best_fiber
    for word in normalized.split():
        if word in _MATERIAL_VI:
            return _MATERIAL_VI[word]
    return ""


def build_positive_query_text(product: ProductRecord, index: int) -> str:
    category = _vi(product.category, _CATEGORY_VI)
    color = _vi(product.color, _COLOR_VI)
    gender = _vi(product.gender, _GENDER_VI)
    usage = _vi(product.usage, _USAGE_VI)
    material = _material_vi(product.material)
    brand = product.brand.strip()
    color_phrase = _color_phrase(color)

    templates: list[str] = []
    if has_text(category) and has_text(color_phrase):
        templates.append(f"{category} {color_phrase}")
    if has_text(brand) and has_text(category):
        templates.append(f"{category} {brand}")
    if has_text(category) and has_text(material):
        templates.append(f"{category} chất liệu {material}")
    if has_text(category) and has_text(gender):
        templates.append(f"{category} cho {gender}")
    if has_text(category) and has_text(usage):
        templates.append(f"{category} {usage}")
    bucket = price_bucket(product.price)
    if has_text(category) and bucket != "unknown":
        templates.append(f"{category} giá {price_bucket_label(bucket)}")
    if has_text(brand) and has_text(category) and has_text(color_phrase) and has_text(usage):
        templates.append(f"{category} {brand} {color_phrase} {usage}")
    if not templates:
        return product.product_name
    return templates[index % len(templates)]


def build_negative_query_text(index: int) -> str:
    templates = [
        "áo nike màu tím neon",
        "áo lông cừu Canada Goose",
        "giày trượt tuyết chống nước màu bạc",
        "váy cưới đính kim cương",
        "áo khoác da thật dưới 100k",
        "quần jean chống cháy màu vàng neon",
        "đầm dạ hội bằng lụa vàng hồng cao cấp",
        "áo hoodie lông cừu màu bạc kim loại",
        "túi xách da cá sấu màu tím pastel",
        "giày cao gót leo núi chống trượt",
        "áo phao mùa hè siêu mỏng",
        "sơ mi thể thao chống nước màu đen bóng",
    ]
    return templates[index % len(templates)]


def build_query_records(products: list[ProductRecord], *, total_query_count: int, positive_ratio: float, seed: int) -> list[QueryRecord]:
    desired_positive_count = round(total_query_count * positive_ratio)
    sampled_products = sample_products_for_queries(
        products,
        total_positive_count=desired_positive_count,
        seed=seed,
        min_per_category=5,
        max_per_category=20,
    )
    positive_count = desired_positive_count if sampled_products else 0
    if sampled_products and len(sampled_products) < desired_positive_count:
        repeated_products: list[ProductRecord] = []
        index = 0
        while len(repeated_products) < desired_positive_count:
            repeated_products.append(sampled_products[index % len(sampled_products)])
            index += 1
        sampled_products = repeated_products
    elif not sampled_products:
        sampled_products = []

    negative_count = max(0, total_query_count - positive_count)
    rng = random.Random(seed)
    query_records: list[QueryRecord] = []
    for index, product in enumerate(sampled_products, start=1):
        query_records.append(
            QueryRecord(
                query_id=f"text-q{index:04d}",
                mode="text",
                query_type="positive",
                source_product_id=product.product_id,
                query_text=build_positive_query_text(product, index - 1),
                category=product.category,
                brand=product.brand,
                color=product.color,
                material=product.material,
                gender=product.gender,
                price_bucket=price_bucket(product.price),
                usage=product.usage,
                manual_status="pending",
                notes="generated_from_stratified_sample",
            )
        )

    negative_templates = [build_negative_query_text(index) for index in range(negative_count)]
    rng.shuffle(negative_templates)
    for offset, query_text in enumerate(negative_templates, start=positive_count + 1):
        query_records.append(
            QueryRecord(
                query_id=f"text-q{offset:04d}",
                mode="text",
                query_type="negative",
                source_product_id="",
                query_text=query_text,
                category="",
                brand="",
                color="",
                material="",
                gender="",
                price_bucket="",
                usage="",
                manual_status="pending",
                notes="expected_empty_manual_validation_required",
            )
        )

    return query_records


def build_query_attributes(query_row: dict[str, str]) -> dict[str, str]:
    return {
        "category": first_non_empty(query_row, "category"),
        "brand": first_non_empty(query_row, "brand"),
        "color": first_non_empty(query_row, "color"),
        "material": first_non_empty(query_row, "material"),
        "gender": first_non_empty(query_row, "gender"),
        "price_bucket": first_non_empty(query_row, "price_bucket"),
        "usage": first_non_empty(query_row, "usage"),
        "query_type": first_non_empty(query_row, "query_type"),
        "query_text": first_non_empty(query_row, "query_text"),
        "query_id": first_non_empty(query_row, "query_id"),
        "mode": first_non_empty(query_row, "mode") or "text",
        "source_product_id": first_non_empty(query_row, "source_product_id"),
    }


def attribute_match_score(query_value: str, product_value: str) -> int:
    if not has_text(query_value) or not has_text(product_value):
        return 0
    query_norm = normalize_text(query_value)
    product_norm = normalize_text(product_value)
    if query_norm == product_norm:
        return 2
    if query_norm in product_norm or product_norm in query_norm:
        return 1
    return 0


def candidate_grade(query_attrs: dict[str, str], product: ProductRecord) -> tuple[int, str]:
    category_score = attribute_match_score(query_attrs["category"], product.category)
    if category_score == 0:
        return 0, ""

    matched = []
    for key, value in (
        ("brand", product.brand),
        ("color", product.color),
        ("material", product.material),
        ("gender", product.gender),
        ("usage", product.usage),
    ):
        if attribute_match_score(query_attrs[key], value) > 0:
            matched.append(key)

    if len(matched) >= 4:
        grade = 3
    elif len(matched) >= 2:
        grade = 2
    else:
        grade = 1

    reason_parts = ["category match"] + [f"{key} match" for key in matched]
    return grade, "+".join(reason_parts)


def build_candidate_rows(query_row: dict[str, str], products: list[ProductRecord], *, max_candidates: int = 20) -> list[GroundTruthRecord]:
    query_attrs = build_query_attributes(query_row)
    query_type = query_attrs["query_type"]
    source_product_id = query_attrs["source_product_id"]
    candidates: list[GroundTruthRecord] = []
    seen_product_ids: set[str] = set()

    if source_product_id:
        source_product = next((product for product in products if product.product_id == source_product_id), None)
        if source_product is not None:
            candidates.append(
                GroundTruthRecord(
                    query_id=query_attrs["query_id"],
                    mode=query_attrs["mode"],
                    query_type=query_type,
                    relevant_product_id=source_product.product_id,
                    relevance_grade=3,
                    match_reason="source_product_exact_match",
                    source="sql_candidate",
                    review_status="pending",
                    notes="auto_candidate_from_sampled_source_product",
                )
            )
            seen_product_ids.add(source_product.product_id)

    scored_products: list[tuple[int, str, ProductRecord]] = []
    for product in products:
        if product.product_id in seen_product_ids:
            continue
        grade, reason = candidate_grade(query_attrs, product)
        if grade <= 0:
            continue
        scored_products.append((grade, reason, product))

    scored_products.sort(key=lambda item: (-item[0], item[2].product_id))
    for grade, reason, product in scored_products[:max_candidates - len(candidates)]:
        candidates.append(
            GroundTruthRecord(
                query_id=query_attrs["query_id"],
                mode=query_attrs["mode"],
                query_type=query_type,
                relevant_product_id=product.product_id,
                relevance_grade=grade,
                match_reason=reason or "attribute_candidate",
                source="sql_candidate",
                review_status="pending",
                notes="review_candidate_before_final_ground_truth",
            )
        )

    if not candidates:
        candidates.append(
            GroundTruthRecord(
                query_id=query_attrs["query_id"],
                mode=query_attrs["mode"],
                query_type=query_type,
                relevant_product_id="",
                relevance_grade=0,
                match_reason="no_sql_candidate_found",
                source="sql_candidate",
                review_status="pending",
                notes="expected_empty_for_negative_or_needs_manual_review",
            )
        )

    return candidates


def json_response_from_text_search(raw_response: dict[str, Any], *, query_id: str, run_id: str, top_k: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # POST /search/text returns SearchResponse: results[] with {product_id, score,
    # source, rerank_score?} plus rewritten_query and an optional filters object.
    # There is no "products"/"ai_score"/"warnings" field in the real contract.
    results = raw_response.get("results") or []
    rewritten_query = raw_response.get("rewritten_query")
    filters = raw_response.get("filters")
    for rank, item in enumerate(results[:top_k], start=1):
        item = item if isinstance(item, dict) else {}
        rows.append(
            {
                "run_id": run_id,
                "query_id": query_id,
                "mode": "text",
                "rank": rank,
                "product_id": first_non_empty(item, "product_id"),
                "score": item.get("score"),
                "raw_score_json": json.dumps(
                    {
                        "rewritten_query": rewritten_query,
                        "filters": filters,
                        "rerank_score": item.get("rerank_score"),
                        "source": item.get("source"),
                        "product": item,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            }
        )
    return rows


def compute_negative_flag(query_type: str, hits: int) -> float:
    return 1.0 if query_type == "negative" and hits > 0 else 0.0


def call_text_search(base_url: str, endpoint: str, query_text: str, top_k: int, timeout_seconds: int) -> dict[str, Any]:
    payload = json.dumps({"query": query_text, "top_k": top_k}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"text search request failed with HTTP {exc.code}: {exc.read().decode('utf-8', errors='ignore')}") from exc


def ndcg_at_k(
    relevances: list[int],
    ideal_relevances: list[int],
    k: int,
) -> float:
    dcg = 0.0
    for rank, relevance in enumerate(relevances[:k], start=1):
        if relevance <= 0:
            continue
        dcg += (2**relevance - 1) / math.log2(rank + 1)
    ideal = sorted(ideal_relevances, reverse=True)
    idcg = 0.0
    for rank, relevance in enumerate(ideal[:k], start=1):
        if relevance <= 0:
            continue
        idcg += (2**relevance - 1) / math.log2(rank + 1)
    return 0.0 if idcg == 0 else dcg / idcg


def mrr_from_ranks(relevance_ranks: list[int]) -> float:
    if not relevance_ranks:
        return 0.0
    return 1.0 / min(relevance_ranks)
