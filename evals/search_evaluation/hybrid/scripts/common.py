from __future__ import annotations

import csv
import json
import math
import random
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

PRICE_BUCKETS = (
    (200_000, "under_200k", "dưới 200k"),
    (500_000, "200k_500k", "200k đến 500k"),
    (1_000_000, "500k_1m", "500k đến 1 triệu"),
    (2_000_000, "1m_2m", "1 đến 2 triệu"),
)


@dataclass(frozen=True)
class MultimodalProductRecord:
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


@dataclass(frozen=True)
class MultimodalItemRecord:
    product_id: str
    product_name: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    price: float | None
    usage: str
    image_id: str
    image_url: str

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["price"] = "" if self.price is None else f"{self.price:.2f}"
        row["price_bucket"] = price_bucket(self.price)
        return row


@dataclass(frozen=True)
class MultimodalQueryRecord:
    query_id: str
    mode: str
    source_product_id: str
    image_id: str
    image_url: str
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
class MultimodalGroundTruthRecord:
    query_id: str
    mode: str
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


def first_non_empty(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active", "available"}


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


def attribute_match_score(query_value: str, product_value: str) -> int:
    query_norm = normalize_text(query_value)
    product_norm = normalize_text(product_value)
    if not query_norm or not product_norm:
        return 0
    if query_norm == product_norm:
        return 2
    if query_norm in product_norm or product_norm in query_norm:
        return 1
    return 0


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


def load_products(path: Path) -> list[MultimodalProductRecord]:
    return [_product_from_row(row) for row in read_csv_rows(path)]


def _product_from_row(row: dict[str, str]) -> MultimodalProductRecord:
    return MultimodalProductRecord(
        product_id=first_non_empty(row, "product_id", "id", "external_id"),
        product_name=first_non_empty(row, "product_name", "product_display_name", "product_display_name_vi", "title", "name"),
        category=first_non_empty(row, "category", "category_name", "category_name_vi"),
        brand=first_non_empty(row, "brand", "brand_name"),
        color=first_non_empty(row, "color", "base_colour", "base_colour_vi", "colour1", "colour1_vi", "colour2", "colour2_vi"),
        material=first_non_empty(row, "material", "material_vi"),
        gender=first_non_empty(row, "gender", "gender_vi"),
        price=parse_float(first_non_empty(row, "price", "effective_price", "discounted_price")),
        usage=first_non_empty(row, "usage", "product_usage", "product_usage_vi", "season"),
        is_active=parse_bool(first_non_empty(row, "is_active", "available", "active")),
        description=first_non_empty(row, "description", "description_vi"),
    )


def load_multimodal_items(products_csv: Path, product_images_csv: Path | None = None) -> list[MultimodalItemRecord]:
    products = load_products(products_csv)
    product_by_id = {product.product_id: product for product in products if product.product_id}
    if product_images_csv and product_images_csv.exists():
        return _items_from_product_images(product_by_id, product_images_csv)
    product_rows = read_csv_rows(products_csv)
    rows_by_product_id = {
        first_non_empty(row, "product_id", "id", "external_id"): row
        for row in product_rows
    }
    items: list[MultimodalItemRecord] = []
    for product in products:
        source_row = rows_by_product_id.get(product.product_id, {})
        urls = image_urls_from_row(source_row)
        for index, image_url in enumerate(urls):
            items.append(_item_record(product, image_id=f"{product.product_id}:img:{index}", image_url=image_url))
    return items


def _items_from_product_images(
    product_by_id: dict[str, MultimodalProductRecord],
    product_images_csv: Path,
) -> list[MultimodalItemRecord]:
    items: list[MultimodalItemRecord] = []
    for index, row in enumerate(read_csv_rows(product_images_csv)):
        product_id = first_non_empty(row, "product_id", "source_product_id")
        image_url = first_non_empty(row, "image_url", "url", "main_image")
        product = product_by_id.get(product_id)
        if not product or not image_url:
            continue
        image_id = first_non_empty(row, "image_id", "source_image_id", "id") or f"{product_id}:img:{index}"
        items.append(_item_record(product, image_id=image_id, image_url=image_url))
    return items


def image_urls_from_row(row: dict[str, str]) -> list[str]:
    raw_values = [
        first_non_empty(row, "image_url", "main_image"),
        first_non_empty(row, "image_urls"),
    ]
    urls: list[str] = []
    for raw in raw_values:
        if not raw:
            continue
        text = raw.strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                for item in parsed if isinstance(parsed, list) else []:
                    image_url = str(item).strip()
                    if image_url and image_url not in urls:
                        urls.append(image_url)
                continue
            except json.JSONDecodeError:
                pass
        for value in re.split(r"[|,;]\s*", text):
            image_url = value.strip()
            if image_url and image_url not in urls:
                urls.append(image_url)
    return urls


def _item_record(product: MultimodalProductRecord, *, image_id: str, image_url: str) -> MultimodalItemRecord:
    return MultimodalItemRecord(
        product_id=product.product_id,
        product_name=product.product_name,
        category=product.category,
        brand=product.brand,
        color=product.color,
        material=product.material,
        gender=product.gender,
        price=product.price,
        usage=product.usage,
        image_id=image_id,
        image_url=image_url,
    )


def item_from_row(row: dict[str, str]) -> MultimodalItemRecord:
    return MultimodalItemRecord(
        product_id=first_non_empty(row, "product_id", "source_product_id"),
        product_name=first_non_empty(row, "product_name"),
        category=first_non_empty(row, "category"),
        brand=first_non_empty(row, "brand"),
        color=first_non_empty(row, "color"),
        material=first_non_empty(row, "material"),
        gender=first_non_empty(row, "gender"),
        price=parse_float(first_non_empty(row, "price")),
        usage=first_non_empty(row, "usage"),
        image_id=first_non_empty(row, "image_id", "source_image_id"),
        image_url=first_non_empty(row, "image_url"),
    )


def sample_items_for_queries(
    items: list[MultimodalItemRecord],
    products: list[MultimodalProductRecord],
    *,
    total_count: int,
    seed: int,
    min_per_category: int,
    max_per_category: int,
    max_products: int,
) -> list[MultimodalItemRecord]:
    rng = random.Random(seed)
    active_product_ids = {product.product_id for product in products if product.product_id and product.is_active}
    valid_items = [item for item in items if item.product_id in active_product_ids and item.image_url]
    grouped_by_product: dict[str, list[MultimodalItemRecord]] = {}
    for item in valid_items:
        grouped_by_product.setdefault(item.product_id, []).append(item)

    product_lookup = {product.product_id: product for product in products}
    candidate_products = [
        product_lookup[product_id]
        for product_id in grouped_by_product
        if product_id in product_lookup
    ]
    if max_products > 0 and len(candidate_products) > max_products:
        candidate_products = sample_products_by_category(
            candidate_products,
            total_count=max_products,
            seed=seed,
            min_per_category=1,
            max_per_category=max_products,
        )

    sampled_products = sample_products_by_category(
        candidate_products,
        total_count=total_count,
        seed=seed,
        min_per_category=min_per_category,
        max_per_category=max_per_category,
    )
    sampled_items: list[MultimodalItemRecord] = []
    for product in sampled_products:
        product_images = grouped_by_product.get(product.product_id, [])
        if product_images:
            sampled_items.append(rng.choice(product_images))
    return sampled_items[:total_count]


def sample_products_by_category(
    products: list[MultimodalProductRecord],
    *,
    total_count: int,
    seed: int,
    min_per_category: int,
    max_per_category: int,
) -> list[MultimodalProductRecord]:
    rng = random.Random(seed)
    grouped: dict[str, list[MultimodalProductRecord]] = {}
    for product in products:
        grouped.setdefault(product.category or "unknown", []).append(product)
    if not grouped:
        return []
    counts = allocate_category_counts(grouped, total_count, min_per_category, max_per_category)
    sampled: list[MultimodalProductRecord] = []
    for category in sorted(counts):
        available = grouped.get(category, [])
        sampled.extend(rng.sample(available, min(counts[category], len(available))))
    if len(sampled) < total_count:
        remaining = [product for product in products if product not in sampled]
        rng.shuffle(remaining)
        sampled.extend(remaining[: total_count - len(sampled)])
    return sampled[:total_count]


def allocate_category_counts(
    grouped: dict[str, list[MultimodalProductRecord]],
    total_count: int,
    min_per_category: int,
    max_per_category: int,
) -> dict[str, int]:
    categories = sorted(grouped)
    target_total = min(total_count, sum(len(items) for items in grouped.values()))
    if not categories or target_total <= 0:
        return {}
    effective_min_per_category = min_per_category
    if effective_min_per_category * len(categories) > target_total:
        effective_min_per_category = 1 if len(categories) <= target_total else 0
    total_available = max(1, sum(len(items) for items in grouped.values()))
    desired = {category: target_total * len(grouped[category]) / total_available for category in categories}
    counts = {
        category: min(max_per_category, len(grouped[category]), max(effective_min_per_category, math.floor(desired[category])))
        for category in categories
    }

    def total_assigned() -> int:
        return sum(counts.values())

    while total_assigned() < target_total:
        changed = False
        ordered = sorted(categories, key=lambda item: (desired[item] - math.floor(desired[item]), len(grouped[item]), item), reverse=True)
        for category in ordered:
            capacity = min(max_per_category, len(grouped[category]))
            if counts[category] < capacity:
                counts[category] += 1
                changed = True
                if total_assigned() >= target_total:
                    break
        if not changed:
            break
    while total_assigned() > target_total:
        changed = False
        ordered = sorted(categories, key=lambda item: (counts[item] - effective_min_per_category, counts[item], item), reverse=True)
        for category in ordered:
            if counts[category] > effective_min_per_category:
                counts[category] -= 1
                changed = True
                if total_assigned() <= target_total:
                    break
        if not changed:
            break
    return {category: count for category, count in counts.items() if count > 0}


def build_query_records(
    sampled_items: list[MultimodalItemRecord],
    products: list[MultimodalProductRecord],
    *,
    total_query_count: int,
    seed: int,
    min_candidates: int,
    min_non_self_candidates: int,
    manual_review_ratio: float,
) -> list[MultimodalQueryRecord]:
    rng = random.Random(seed)
    shuffled_items = list(sampled_items)
    rng.shuffle(shuffled_items)
    records: list[MultimodalQueryRecord] = []
    manual_review_count = math.ceil(total_query_count * manual_review_ratio)

    for index, item in enumerate(shuffled_items[:total_query_count], start=1):
        template = best_query_template(item, products, index - 1, min_candidates, min_non_self_candidates)
        query_id = f"multimodal-q{index:04d}"
        candidate_count, non_self_count = count_candidates_for_item(item, products, template["condition_keys"])
        manual_status = "review_required" if index <= manual_review_count else "pending"
        notes = [
            "generated_from_stratified_image_product_sample",
            f"condition_keys={','.join(template['condition_keys'])}",
            f"candidate_count={candidate_count}",
            f"non_self_candidates={non_self_count}",
        ]
        if non_self_count < min_non_self_candidates or candidate_count < min_candidates:
            notes.append("needs_manual_review_low_candidate_count")
        if manual_status == "review_required":
            notes.append("manual_review_priority")
        records.append(
            MultimodalQueryRecord(
                query_id=query_id,
                mode="multimodal",
                source_product_id=item.product_id,
                image_id=item.image_id,
                image_url=item.image_url,
                query_text=template["query_text"],
                category=item.category,
                brand=item.brand,
                color=item.color,
                material=item.material,
                gender=item.gender,
                price_bucket=price_bucket(item.price),
                usage=item.usage,
                manual_status=manual_status,
                notes=";".join(notes),
            )
        )
    return records


def best_query_template(
    item: MultimodalItemRecord,
    products: list[MultimodalProductRecord],
    offset: int,
    min_candidates: int,
    min_non_self_candidates: int,
) -> dict[str, Any]:
    templates = query_template_candidates(item)
    if not templates:
        templates = [{"query_text": "tìm sản phẩm giống ảnh", "condition_keys": []}]
    rotated = templates[offset % len(templates) :] + templates[: offset % len(templates)]
    fallback = rotated[-1]
    for template in rotated:
        candidate_count, non_self_count = count_candidates_for_item(item, products, template["condition_keys"])
        if candidate_count >= min_candidates and non_self_count >= min_non_self_candidates:
            return template
        if candidate_count >= min_candidates:
            fallback = template
    return fallback


def query_template_candidates(item: MultimodalItemRecord) -> list[dict[str, Any]]:
    category = display_value(item.category, "sản phẩm")
    templates: list[dict[str, Any]] = []
    if has_text(item.color):
        templates.append({"query_text": f"tìm sản phẩm giống ảnh, màu {display_value(item.color)}", "condition_keys": ["color"]})
    if has_text(item.material):
        templates.append({"query_text": f"tìm sản phẩm giống ảnh, chất liệu {display_value(item.material)}", "condition_keys": ["material"]})
    if has_text(item.usage):
        templates.append({"query_text": f"tìm đồ giống ảnh phù hợp {display_value(item.usage)}", "condition_keys": ["usage"]})
    bucket = price_bucket(item.price)
    if bucket != "unknown":
        templates.append({"query_text": f"tìm sản phẩm giống ảnh trong khoảng {price_bucket_label(bucket)}", "condition_keys": ["price_bucket"]})
    if has_text(item.category):
        templates.append({"query_text": f"tìm {category} giống ảnh", "condition_keys": ["category"]})
    return templates


def display_value(value: str, fallback: str = "") -> str:
    return value.strip() if has_text(value) else fallback


def count_candidates_for_item(
    item: MultimodalItemRecord,
    products: list[MultimodalProductRecord],
    condition_keys: list[str],
) -> tuple[int, int]:
    pseudo_query = {
        "source_product_id": item.product_id,
        "category": item.category,
        "brand": item.brand,
        "color": item.color,
        "material": item.material,
        "gender": item.gender,
        "price_bucket": price_bucket(item.price),
        "usage": item.usage,
        "notes": f"condition_keys={','.join(condition_keys)}",
    }
    count = 0
    non_self_count = 0
    for product in products:
        grade, _ = multimodal_candidate_grade(pseudo_query, product)
        if grade > 0:
            count += 1
            if product.product_id != item.product_id:
                non_self_count += 1
    return count, non_self_count


def condition_keys_from_notes(notes: str) -> list[str]:
    for part in notes.split(";"):
        if part.startswith("condition_keys="):
            raw = part.removeprefix("condition_keys=")
            return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def multimodal_candidate_grade(query_row: dict[str, str], product: MultimodalProductRecord) -> tuple[int, str]:
    source_product_id = first_non_empty(query_row, "source_product_id")
    condition_keys = condition_keys_from_notes(first_non_empty(query_row, "notes"))
    if product.product_id == source_product_id:
        return 3, "source_product_exact_match"

    category_score = attribute_match_score(first_non_empty(query_row, "category"), product.category)
    if category_score == 0:
        return 0, ""

    visual_matches = []
    for key, product_value in (
        ("brand", product.brand),
        ("color", product.color),
        ("material", product.material),
        ("gender", product.gender),
    ):
        if attribute_match_score(first_non_empty(query_row, key), product_value) > 0:
            visual_matches.append(key)

    text_matches = []
    for key in condition_keys:
        if key == "price_bucket":
            if first_non_empty(query_row, "price_bucket") == price_bucket(product.price):
                text_matches.append(key)
            continue
        product_value = getattr(product, key, "")
        if attribute_match_score(first_non_empty(query_row, key), str(product_value)) > 0:
            text_matches.append(key)

    if condition_keys and not text_matches:
        return 0, ""
    if len(text_matches) == len(condition_keys) and len(visual_matches) >= 2:
        grade = 3
    elif text_matches and visual_matches:
        grade = 2
    elif text_matches or len(visual_matches) >= 2:
        grade = 1
    else:
        grade = 1 if not condition_keys else 0

    reason_parts = ["image_category_match"]
    reason_parts.extend(f"visual_{key}_match" for key in visual_matches)
    reason_parts.extend(f"text_{key}_match" for key in text_matches)
    return grade, "+".join(reason_parts)


def build_multimodal_candidate_rows(
    query_row: dict[str, str],
    products: list[MultimodalProductRecord],
    *,
    max_candidates: int = 30,
) -> list[MultimodalGroundTruthRecord]:
    query_id = first_non_empty(query_row, "query_id")
    scored: list[tuple[int, str, MultimodalProductRecord]] = []
    for product in products:
        grade, reason = multimodal_candidate_grade(query_row, product)
        if grade > 0:
            scored.append((grade, reason, product))
    scored.sort(key=lambda item: (-item[0], item[2].product_id))

    notes = first_non_empty(query_row, "notes")
    manual_priority = "manual_review_priority" if "manual_review_priority" in notes else "review_candidate_before_final_ground_truth"
    candidates = [
        MultimodalGroundTruthRecord(
            query_id=query_id,
            mode="multimodal",
            relevant_product_id=product.product_id,
            relevance_grade=grade,
            match_reason=reason,
            source="sql_candidate",
            review_status="pending",
            notes=manual_priority,
        )
        for grade, reason, product in scored[:max_candidates]
    ]
    if candidates:
        return candidates
    return [
        MultimodalGroundTruthRecord(
            query_id=query_id,
            mode="multimodal",
            relevant_product_id="",
            relevance_grade=0,
            match_reason="no_sql_candidate_found",
            source="sql_candidate",
            review_status="pending",
            notes="manual_review_required",
        )
    ]
