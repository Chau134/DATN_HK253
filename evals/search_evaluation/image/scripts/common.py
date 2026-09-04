from __future__ import annotations

import base64
import csv
import json
import math
import mimetypes
import random
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


SEMANTIC_IMAGE_TYPES = {"front", "back", "side", "detail", "lifestyle", "flatlay", "unknown"}
IMAGE_QUALITY_VALUES = {"good", "medium", "hard"}


@dataclass(frozen=True)
class ImageProductRecord:
    product_id: str
    product_name: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    is_active: bool
    description: str = ""


@dataclass(frozen=True)
class ProductImageRecord:
    source_image_id: str
    source_product_id: str
    product_name: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    image_url: str
    db_image_type: str
    sort_order: str
    image_count: int

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImageQueryRecord:
    query_id: str
    mode: str
    source_product_id: str
    source_image_id: str
    image_url: str
    db_image_type: str
    semantic_image_type: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    image_quality: str
    manual_status: str
    notes: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImageGroundTruthRecord:
    query_id: str
    mode: str
    source_product_id: str
    source_image_id: str
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
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return ""


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active", "available"}


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


def load_products(path: Path) -> list[ImageProductRecord]:
    return [_product_from_row(row) for row in read_csv_rows(path)]


def _product_from_row(row: dict[str, str]) -> ImageProductRecord:
    return ImageProductRecord(
        product_id=first_non_empty(row, "product_id", "id", "external_id"),
        product_name=first_non_empty(row, "product_name", "product_display_name", "product_display_name_vi", "title", "name"),
        category=first_non_empty(row, "category", "category_name", "category_name_vi"),
        brand=first_non_empty(row, "brand", "brand_name"),
        color=first_non_empty(row, "color", "base_colour", "base_colour_vi", "colour1", "colour1_vi"),
        material=first_non_empty(row, "material", "material_vi"),
        gender=first_non_empty(row, "gender", "gender_vi"),
        is_active=parse_bool(first_non_empty(row, "is_active", "available", "active")),
        description=first_non_empty(row, "description", "description_vi"),
    )


def load_categories(path: Path) -> dict[str, dict[str, str]]:
    categories: dict[str, dict[str, str]] = {}
    for row in read_csv_rows(path):
        category_id = first_non_empty(row, "id", "category_id")
        if category_id:
            categories[category_id] = row
    return categories


def load_product_category_map(path: Path) -> dict[str, list[str]]:
    product_categories: dict[str, list[str]] = {}
    for row in read_csv_rows(path):
        product_id = first_non_empty(row, "product_id")
        category_id = first_non_empty(row, "category_id")
        if product_id and category_id:
            product_categories.setdefault(product_id, []).append(category_id)
    return product_categories


def enrich_product_categories(
    products: list[ImageProductRecord],
    product_categories: dict[str, list[str]],
    categories: dict[str, dict[str, str]],
) -> list[ImageProductRecord]:
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

    enriched: list[ImageProductRecord] = []
    for product in products:
        if has_text(product.category):
            enriched.append(product)
            continue
        ranked_rows = [categories[category_id] for category_id in product_categories.get(product.product_id, []) if category_id in categories]
        ranked_rows.sort(key=category_rank)
        resolved = category_name(ranked_rows[0]) if ranked_rows else ""
        enriched.append(ImageProductRecord(**{**asdict(product), "category": resolved}))
    return enriched


def load_image_records(products_csv: Path, product_images_csv: Path | None = None) -> list[ProductImageRecord]:
    products = load_products(products_csv)
    product_by_id = {product.product_id: product for product in products}
    rows: list[ProductImageRecord] = []

    if product_images_csv and product_images_csv.exists():
        image_rows = read_csv_rows(product_images_csv)
        image_count_by_product: dict[str, int] = {}
        for row in image_rows:
            product_id = first_non_empty(row, "product_id", "source_product_id")
            image_url = first_non_empty(row, "image_url", "url", "main_image")
            if not product_id or not image_url:
                continue
            image_count_by_product[product_id] = image_count_by_product.get(product_id, 0) + 1
        for index, row in enumerate(image_rows):
            product_id = first_non_empty(row, "product_id", "source_product_id")
            image_url = first_non_empty(row, "image_url", "url", "main_image")
            product = product_by_id.get(product_id)
            if not product or not image_url:
                continue
            rows.append(
                _image_record(
                    product,
                    source_image_id=first_non_empty(row, "source_image_id", "image_id", "id") or f"{product_id}:img:{index}",
                    image_url=image_url,
                    db_image_type=first_non_empty(row, "db_image_type", "image_type"),
                    sort_order=first_non_empty(row, "sort_order"),
                    image_count=image_count_by_product.get(product_id, 1),
                )
            )
        return rows

    for product in products:
        urls = _image_urls_from_product_row(product, next((row for row in read_csv_rows(products_csv) if first_non_empty(row, "product_id", "id", "external_id") == product.product_id), {}))
        for index, image_url in enumerate(urls):
            rows.append(
                _image_record(
                    product,
                    source_image_id=f"{product.product_id}:img:{index}",
                    image_url=image_url,
                    db_image_type="product_snapshot",
                    sort_order=str(index),
                    image_count=len(urls),
                )
            )
    return rows


def _image_urls_from_product_row(product: ImageProductRecord, row: dict[str, str]) -> list[str]:
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
                    if has_text(str(item)) and str(item) not in urls:
                        urls.append(str(item).strip())
                continue
            except json.JSONDecodeError:
                pass
        for value in re.split(r"[|,;]\s*", text):
            if has_text(value) and value not in urls:
                urls.append(value.strip())
    return urls


def _image_record(
    product: ImageProductRecord,
    *,
    source_image_id: str,
    image_url: str,
    db_image_type: str,
    sort_order: str,
    image_count: int,
) -> ProductImageRecord:
    return ProductImageRecord(
        source_image_id=source_image_id,
        source_product_id=product.product_id,
        product_name=product.product_name,
        category=product.category,
        brand=product.brand,
        color=product.color,
        material=product.material,
        gender=product.gender,
        image_url=image_url,
        db_image_type=db_image_type,
        sort_order=sort_order,
        image_count=image_count,
    )


def sample_images_for_queries(
    images: list[ProductImageRecord],
    *,
    total_count: int,
    seed: int,
    min_per_category: int,
    max_per_category: int,
) -> list[ProductImageRecord]:
    rng = random.Random(seed)
    grouped: dict[str, list[ProductImageRecord]] = {}
    for image in images:
        if image.image_url:
            grouped.setdefault(image.category or "unknown", []).append(image)
    if not grouped:
        return []

    counts = allocate_category_counts(grouped, total_count, min_per_category, max_per_category)
    sampled: list[ProductImageRecord] = []
    for category in sorted(counts):
        available = grouped.get(category, [])
        sampled.extend(rng.sample(available, min(counts[category], len(available))))
    if len(sampled) < total_count:
        remaining = [image for image in images if image not in sampled]
        rng.shuffle(remaining)
        sampled.extend(remaining[: total_count - len(sampled)])
    return sampled[:total_count]


def allocate_category_counts(
    grouped: dict[str, list[ProductImageRecord]],
    total_count: int,
    min_per_category: int,
    max_per_category: int,
) -> dict[str, int]:
    categories = sorted(grouped)
    target_total = min(total_count, sum(len(items) for items in grouped.values()))
    desired = {category: target_total * len(grouped[category]) / max(1, sum(len(items) for items in grouped.values())) for category in categories}
    counts = {
        category: min(max_per_category, len(grouped[category]), max(min_per_category, math.floor(desired[category])))
        for category in categories
    }

    def total_assigned() -> int:
        return sum(counts.values())

    while total_assigned() < target_total:
        changed = False
        for category in sorted(categories, key=lambda item: (desired[item] - math.floor(desired[item]), len(grouped[item]), item), reverse=True):
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
        for category in sorted(categories, key=lambda item: (counts[item] - min_per_category, counts[item], item), reverse=True):
            if counts[category] > min_per_category:
                counts[category] -= 1
                changed = True
                if total_assigned() <= target_total:
                    break
        if not changed:
            break
    return {category: count for category, count in counts.items() if count > 0}


def annotation_rows_from_images(images: list[ProductImageRecord]) -> list[dict[str, Any]]:
    return [
        {
            "source_image_id": image.source_image_id,
            "source_product_id": image.source_product_id,
            "image_url": image.image_url,
            "db_image_type": image.db_image_type,
            "sort_order": image.sort_order,
            "semantic_image_type": "unknown",
            "image_quality": "good",
            "review_status": "pending",
            "notes": "",
        }
        for image in images
    ]


def build_image_query_records(sampled_images: list[ProductImageRecord], annotation_rows: list[dict[str, str]]) -> list[ImageQueryRecord]:
    annotation_by_image_id = {row.get("source_image_id", ""): row for row in annotation_rows}
    queries: list[ImageQueryRecord] = []
    for index, image in enumerate(sampled_images, start=1):
        annotation = annotation_by_image_id.get(image.source_image_id, {})
        semantic_type = first_non_empty(annotation, "semantic_image_type") or "unknown"
        image_quality = first_non_empty(annotation, "image_quality") or "good"
        if semantic_type not in SEMANTIC_IMAGE_TYPES:
            semantic_type = "unknown"
        if image_quality not in IMAGE_QUALITY_VALUES:
            image_quality = "medium"
        queries.append(
            ImageQueryRecord(
                query_id=f"image-q{index:04d}",
                mode="image",
                source_product_id=image.source_product_id,
                source_image_id=image.source_image_id,
                image_url=image.image_url,
                db_image_type=image.db_image_type,
                semantic_image_type=semantic_type,
                category=image.category,
                brand=image.brand,
                color=image.color,
                material=image.material,
                gender=image.gender,
                image_quality=image_quality,
                manual_status=first_non_empty(annotation, "review_status") or "pending",
                notes=first_non_empty(annotation, "notes"),
            )
        )
    return queries


def image_candidate_grade(query_row: dict[str, str], product: ImageProductRecord) -> tuple[int, str]:
    if product.product_id == first_non_empty(query_row, "source_product_id"):
        return 3, "source_product_exact_match"
    category_score = attribute_match_score(first_non_empty(query_row, "category"), product.category)
    if category_score == 0:
        return 0, ""
    matched = []
    for key, value in (("brand", product.brand), ("color", product.color), ("material", product.material), ("gender", product.gender)):
        if attribute_match_score(first_non_empty(query_row, key), value) > 0:
            matched.append(key)
    if len(matched) >= 3:
        return 2, "visual_similar+" + "+".join(matched)
    if len(matched) >= 1:
        return 1, "category_related+" + "+".join(matched)
    return 1, "category_related"


def build_image_candidate_rows(query_row: dict[str, str], products: list[ImageProductRecord], *, max_candidates: int = 30) -> list[ImageGroundTruthRecord]:
    query_id = first_non_empty(query_row, "query_id")
    source_product_id = first_non_empty(query_row, "source_product_id")
    source_image_id = first_non_empty(query_row, "source_image_id")
    candidates: list[ImageGroundTruthRecord] = []
    scored: list[tuple[int, str, ImageProductRecord]] = []
    for product in products:
        grade, reason = image_candidate_grade(query_row, product)
        if grade > 0:
            scored.append((grade, reason, product))
    scored.sort(key=lambda item: (-item[0], item[2].product_id))
    for grade, reason, product in scored[:max_candidates]:
        candidates.append(
            ImageGroundTruthRecord(
                query_id=query_id,
                mode="image",
                source_product_id=source_product_id,
                source_image_id=source_image_id,
                relevant_product_id=product.product_id,
                relevance_grade=grade,
                match_reason=reason,
                source="sql_candidate",
                review_status="pending",
                notes="review_candidate_before_final_ground_truth",
            )
        )
    if not candidates:
        candidates.append(
            ImageGroundTruthRecord(
                query_id=query_id,
                mode="image",
                source_product_id=source_product_id,
                source_image_id=source_image_id,
                relevant_product_id="",
                relevance_grade=0,
                match_reason="no_sql_candidate_found",
                source="sql_candidate",
                review_status="pending",
                notes="manual_review_required",
            )
        )
    return candidates


def image_payload_from_url(image_url: str, timeout_seconds: int) -> dict[str, str]:
    request = urllib.request.Request(image_url, headers={"User-Agent": "search-eval-image-runner/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = response.read()
            content_type = response.headers.get_content_type() or mimetypes.guess_type(image_url)[0] or "image/jpeg"
    except urllib.error.URLError as exc:
        raise RuntimeError(f"image download failed: {exc}") from exc
    if not data:
        raise RuntimeError("image download returned empty body")
    return {
        "content_type": content_type,
        "data_base64": base64.b64encode(data).decode("ascii"),
        "filename": Path(urllib.request.url2pathname(image_url.split("?")[0])).name or "query-image",
    }


def call_image_search(base_url: str, endpoint: str, image_url: str, top_k: int, timeout_seconds: int) -> dict[str, Any]:
    image_payload = image_payload_from_url(image_url, timeout_seconds)
    return call_image_search_with_payload(base_url, endpoint, image_payload, top_k, timeout_seconds)


def call_image_search_with_payload(
    base_url: str,
    endpoint: str,
    image_payload: dict[str, Any],
    top_k: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    payload = json.dumps({"image": image_payload, "top_k": top_k}, ensure_ascii=False).encode("utf-8")
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
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"image search request failed with HTTP {exc.code}: {detail}") from exc


def json_response_from_image_search(raw_response: dict[str, Any], *, query_id: str, run_id: str, top_k: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, item in enumerate((raw_response.get("results") or [])[:top_k], start=1):
        item = item if isinstance(item, dict) else {}
        rows.append(
            {
                "run_id": run_id,
                "query_id": query_id,
                "mode": "image",
                "rank": rank,
                "product_id": first_non_empty(item, "product_id"),
                "score": item.get("score"),
                "raw_score_json": json.dumps(
                    {
                        "source": item.get("source"),
                        "detections": raw_response.get("detections"),
                        "warnings": raw_response.get("warnings"),
                        "product": item,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            }
        )
    return rows


def ndcg_at_k(relevances: list[int], ideal_relevances: list[int], k: int) -> float:
    dcg = 0.0
    for rank, relevance in enumerate(relevances[:k], start=1):
        if relevance > 0:
            dcg += (2**relevance - 1) / math.log2(rank + 1)
    ideal = sorted(ideal_relevances, reverse=True)
    idcg = 0.0
    for rank, relevance in enumerate(ideal[:k], start=1):
        if relevance > 0:
            idcg += (2**relevance - 1) / math.log2(rank + 1)
    return 0.0 if idcg == 0 else dcg / idcg


def mrr_from_ranks(relevance_ranks: list[int]) -> float:
    return 0.0 if not relevance_ranks else 1.0 / min(relevance_ranks)


def average_precision(ranked_product_ids: list[str], relevant_ids: set[str]) -> float:
    if not relevant_ids:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for rank, product_id in enumerate(ranked_product_ids, start=1):
        if product_id in relevant_ids:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / len(relevant_ids)
