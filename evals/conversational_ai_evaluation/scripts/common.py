from __future__ import annotations

import csv
import json
import math
import random
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

# Text-feasible question groups for the first conversational eval set.
# Availability follow-up and image/hybrid are excluded until live stock + sample
# images are wired (see README).
QUESTION_GROUPS = (
    "product_factual",
    "product_comparison",
    "product_recommendation",
    "followup_ordinal",
    "filter_refinement",
    "shop_knowledge",
    "unanswerable",
)

DEFAULT_GROUP_COUNTS: dict[str, int] = {
    "product_factual": 20,
    "product_comparison": 10,
    "product_recommendation": 20,
    "followup_ordinal": 5,
    "filter_refinement": 5,
    "shop_knowledge": 8,
    "unanswerable": 2,
}

# Guardrail violations pulled from `_assistant_reply_prompt`
# (service-ai services/gemini/service.py). Every reference answer seeds these into
# `answer_must_not_include` so the judge can score hallucination compliance.
GUARDRAIL_MUST_NOT_INCLUDE = (
    "bịa product_id không có trong danh sách trả về",
    "khẳng định tồn kho / còn hàng / hết hàng khi context không có",
    "khẳng định giá cuối hoặc mức giảm giá khi context không có",
    "lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt",
)


@dataclass(frozen=True)
class ConvProductRecord:
    product_id: str
    product_name: str
    product_name_vi: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    is_active: bool
    description: str
    version: str

    def to_row(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_name_vi": self.product_name_vi,
            "category": self.category,
            "brand": self.brand,
            "color": self.color,
            "material": self.material,
            "gender": self.gender,
            "is_active": str(self.is_active).lower(),
            "description": self.description,
            "version": self.version,
        }


@dataclass(frozen=True)
class ConvQuestionRecord:
    question_id: str
    session_id: str
    turn_index: int
    category: str
    question: str
    expected_answer_type: str
    entity_ids: str
    depends_on_history: bool
    difficulty: str
    manual_status: str
    notes: str
    reviewer: str = ""
    reviewed_at: str = ""
    review_notes: str = ""

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["depends_on_history"] = str(self.depends_on_history).lower()
        return row


@dataclass(frozen=True)
class ConvReferenceRecord:
    question_id: str
    reference_answer: str
    answer_must_include: str
    answer_must_not_include: str
    reference_source_ids: str
    review_status: str
    notes: str
    reviewer: str = ""
    reviewed_at: str = ""
    review_notes: str = ""

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConvEvidenceRecord:
    question_id: str
    evidence_id: str
    source_id: str
    evidence_text: str
    evidence_role: str
    required_level: str
    notes: str
    review_status: str = "pending"
    reviewer: str = ""
    reviewed_at: str = ""
    review_notes: str = ""

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def preserve_review_metadata_if_unchanged(
    generated: dict[str, Any],
    existing: dict[str, str] | None,
    *,
    content_fields: tuple[str, ...],
) -> dict[str, Any]:
    """Carry human review metadata only when generated semantic content is identical."""
    if existing is None or any(
        str(generated.get(field, "")) != str(existing.get(field, ""))
        for field in content_fields
    ):
        return generated
    for field in (
        "manual_status",
        "review_status",
        "reviewer",
        "reviewed_at",
        "review_notes",
    ):
        if field in generated:
            generated[field] = existing.get(field, generated[field])
    return generated


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


_COLOR_FAMILY_ALIASES: dict[str, tuple[str, ...]] = {
    "black": ("black", "den"),
    "white": ("white", "trang", "ivory", "ecru"),
    "brown": ("brown", "nau", "chocolate"),
    "yellow": ("yellow", "vang", "gold", "golden"),
    "red": ("red", "do"),
    "pink": ("pink", "hong"),
    "blue": ("blue", "xanh duong"),
    "green": ("green", "xanh la"),
    "purple": ("purple", "violet", "tim"),
    "gray": ("gray", "grey", "xam"),
    "beige": ("beige", "be"),
    "orange": ("orange", "cam"),
}


def color_family_keys(value: str | None) -> set[str]:
    normalized = normalize_text(value)
    padded = f" {normalized} "
    return {
        family
        for family, aliases in _COLOR_FAMILY_ALIASES.items()
        if any(f" {alias} " in padded for alias in aliases)
    }


def colors_match_runtime_semantics(expected: str | None, candidate: str | None) -> bool:
    if not has_text(expected):
        return True
    if normalize_text(expected) == normalize_text(candidate):
        return True
    expected_families = color_family_keys(expected)
    candidate_families = color_family_keys(candidate)
    return bool(expected_families and expected_families & candidate_families)


# Catalog values are English (Zara data), but real Vietnamese shoppers type
# "áo sơ mi" not "Shirts & Blouses". These maps translate ONLY the question text so
# it reads like a real user query; the CSV attribute columns keep the raw catalog values.
_CATEGORY_VI: dict[str, str] = {
    "dresses": "váy",
    "dress": "váy",
    "shirts blouses": "áo sơ mi",
    "shirt blouse": "áo sơ mi",
    "shirts": "áo sơ mi",
    "shirt": "áo sơ mi",
    "blouses": "áo kiểu",
    "t shirts": "áo thun",
    "tshirts": "áo thun",
    "tshirt": "áo thun",
    "tops": "áo",
    "top": "áo",
    "sweaters cardigans": "áo len",
    "sweaters": "áo len",
    "sweater": "áo len",
    "cardigans": "áo cardigan",
    "knitwear": "đồ len",
    "hoodies": "áo hoodie",
    "hoodie": "áo hoodie",
    "sweatshirts": "áo nỉ",
    "jackets": "áo khoác",
    "jacket": "áo khoác",
    "coats": "áo khoác dài",
    "blazers": "áo blazer",
    "jeans": "quần jean",
    "trousers": "quần dài",
    "pants": "quần dài",
    "shorts": "quần short",
    "skirts": "chân váy",
    "skirt": "chân váy",
    "jumpsuits": "áo liền quần",
    "polo shirts": "áo polo",
    "polos": "áo polo",
    "shoes": "giày",
    "sneakers": "giày thể thao",
    "boots": "bốt",
    "sandals": "dép sandal",
    "heels": "giày cao gót",
    "bags": "túi xách",
    "bag": "túi xách",
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


def load_conv_products(path: Path) -> list[ConvProductRecord]:
    rows = read_csv_rows(path)
    return [_conv_product_from_row(row) for row in rows]


def _conv_product_from_row(row: dict[str, str]) -> ConvProductRecord:
    return ConvProductRecord(
        product_id=first_non_empty(row, "product_id", "id", "external_id"),
        product_name=first_non_empty(row, "product_name", "product_display_name", "title", "name"),
        product_name_vi=first_non_empty(row, "product_name_vi", "product_display_name_vi", "title_vi"),
        category=first_non_empty(row, "category", "category_name", "category_name_vi"),
        brand=first_non_empty(row, "brand", "brand_name"),
        color=first_non_empty(row, "color", "base_colour", "base_colour_vi", "colour1", "colour1_vi"),
        material=first_non_empty(row, "material", "material_vi"),
        gender=first_non_empty(row, "gender", "gender_vi"),
        is_active=parse_bool(first_non_empty(row, "is_active", "available", "active")),
        description=first_non_empty(row, "description", "description_vi"),
        version=first_non_empty(row, "version"),
    )


def group_products_by_category(products: list[ConvProductRecord]) -> dict[str, list[ConvProductRecord]]:
    grouped: dict[str, list[ConvProductRecord]] = {}
    for product in products:
        category = product.category or "unknown"
        grouped.setdefault(category, []).append(product)
    return grouped


def allocate_category_counts(products: list[ConvProductRecord], total_count: int, min_per_category: int, max_per_category: int) -> dict[str, int]:
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


def sample_products_for_queries(
    products: list[ConvProductRecord],
    *,
    total_positive_count: int,
    seed: int,
    min_per_category: int,
    max_per_category: int,
) -> list[ConvProductRecord]:
    rng = random.Random(seed)
    active_products = [product for product in products if product.is_active]
    grouped = group_products_by_category(active_products)
    if not grouped:
        return []

    category_counts = allocate_category_counts(active_products, total_positive_count, min_per_category, max_per_category)
    sampled: list[ConvProductRecord] = []
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


def product_display(product: ConvProductRecord) -> str:
    """Vietnamese-facing product name for question/answer text."""
    return product.product_name_vi or product.product_name or product.product_id


def category_vi(product: ConvProductRecord) -> str:
    return _vi(product.category, _CATEGORY_VI) or product.category


def color_vi(product: ConvProductRecord) -> str:
    return _vi(product.color, _COLOR_VI) or product.color


def gender_vi(product: ConvProductRecord) -> str:
    return _vi(product.gender, _GENDER_VI) or product.gender


def material_vi(product: ConvProductRecord) -> str:
    return _material_vi(product.material) or product.material


# ---------------------------------------------------------------------------
# Question generation (02)
# ---------------------------------------------------------------------------

_FACTUAL_TEMPLATES: dict[str, str] = {
    "color": "{name} có màu gì?",
    "material": "{name} làm từ chất liệu gì?",
    "gender": "{name} phù hợp cho nam hay nữ?",
    "category": "{name} thuộc danh mục nào?",
}
_FACTUAL_ATTR_ORDER = ("color", "material", "gender", "category")

_ORDINAL_TEMPLATES = (
    ("cái thứ 2 thì sao?", 2),
    ("mẫu đầu tiên thế nào?", 1),
    ("cái thứ 3 có gì đặc biệt?", 3),
)
_FILTER_REFINEMENT_TEMPLATES = (
    "màu đen thì sao?",
    "rẻ hơn nữa có không?",
    "màu trắng thì sao?",
)
_SHOP_KNOWLEDGE_CASES = (
    (
        "shop_identity_and_location",
        "Shop hiện tại có tên là gì? Cho tôi vị trí của shop được không?",
    ),
    ("catalog_overview", "Shop hiện tại đang bán những loại sản phẩm nào?"),
    ("shipping_time_policy", "Đơn hàng được giao trong bao lâu?"),
    ("return_policy", "Tôi có thể đổi trả sản phẩm trong mấy ngày?"),
    ("payment_methods", "Thanh toán bằng phương thức nào?"),
    ("express_shipping_policy", "Shop có giao trong 10 phút không?"),
    ("shipping_fee_policy", "Shop có freeship cho đơn dưới 100k không?"),
    ("warranty_policy", "Sản phẩm của shop được bảo hành trong bao lâu?"),
)
_UNANSWERABLE_TEMPLATES_STATIC = (
    "Sản phẩm này có chắc chắn giúp tôi trông cao hơn không?",
)
_UNANSWERABLE_TEMPLATES_PRODUCT = (
    "{name} có được người nổi tiếng nào mặc chưa?",
)

_CATALOG_CATEGORY_DISPLAY_VI = {
    "Váy & Đầm": "Váy & đầm",
    "Áo dệt kim": "Áo dệt kim & cardigan",
}


def _available_factual_attrs(product: ConvProductRecord) -> list[str]:
    attrs: list[str] = []
    if has_text(product.color):
        attrs.append("color")
    if has_text(product.material) and _material_vi(product.material):
        attrs.append("material")
    if has_text(product.gender):
        attrs.append("gender")
    if has_text(product.category):
        attrs.append("category")
    return attrs


def _recommendation_text(product: ConvProductRecord) -> str:
    cat = category_vi(product)
    phrase = _color_phrase(color_vi(product)) if has_text(product.color) else ""
    gender = gender_vi(product) if has_text(product.gender) else ""
    if cat and phrase and gender:
        return f"Tôi cần {cat} {phrase} cho {gender}, có gợi ý nào không?"
    if cat and phrase:
        return f"Tôi cần {cat} {phrase}, có gợi ý nào không?"
    if cat and gender:
        return f"Tôi cần {cat} cho {gender}, có gợi ý nào không?"
    if cat:
        return f"Có {cat} nào đáng mua không?"
    return "Tư vấn giúp tôi sản phẩm phù hợp."


def _search_text(product: ConvProductRecord) -> str:
    cat = category_vi(product)
    phrase = _color_phrase(color_vi(product)) if has_text(product.color) else ""
    if cat and phrase:
        return f"Tìm {cat} {phrase}"
    if cat:
        return f"Tìm {cat}"
    return product_display(product)


def _sample(products: list[ConvProductRecord], count: int, seed: int) -> list[ConvProductRecord]:
    if count <= 0:
        return []
    return sample_products_for_queries(
        products,
        total_positive_count=count,
        seed=seed,
        min_per_category=0,
        max_per_category=max(1, count),
    )


def build_question_records(
    products: list[ConvProductRecord],
    *,
    seed: int,
    group_counts: dict[str, int],
) -> list[ConvQuestionRecord]:
    records: list[ConvQuestionRecord] = []

    # Product factual QA -----------------------------------------------------
    factual_n = group_counts.get("product_factual", 0)
    factual_products = _sample(products, factual_n, seed + 1)
    for index, product in enumerate(factual_products, start=1):
        available = _available_factual_attrs(product)
        if not available:
            continue
        attr = _FACTUAL_ATTR_ORDER[(index - 1) % len(_FACTUAL_ATTR_ORDER)]
        if attr not in available:
            attr = available[0]
        session_id = f"conv-fact-{index:04d}"
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t0",
                session_id=session_id,
                turn_index=0,
                category="product_factual",
                question=_FACTUAL_TEMPLATES[attr].format(name=product_display(product)),
                expected_answer_type=f"attribute_{attr}",
                entity_ids=product.product_id,
                depends_on_history=False,
                difficulty="easy",
                manual_status="pending",
                notes=f"attr={attr}",
            )
        )

    # Product comparison -----------------------------------------------------
    comparison_n = group_counts.get("product_comparison", 0)
    comparison_products = _sample(products, comparison_n * 2, seed + 2)
    for index in range(comparison_n):
        left = index * 2
        right = left + 1
        if right >= len(comparison_products):
            break
        product_a = comparison_products[left]
        product_b = comparison_products[right]
        session_id = f"conv-cmp-{index + 1:04d}"
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t0",
                session_id=session_id,
                turn_index=0,
                category="product_comparison",
                question=f"So sánh {product_display(product_a)} và {product_display(product_b)}.",
                expected_answer_type="comparison",
                entity_ids=f"{product_a.product_id};{product_b.product_id}",
                depends_on_history=False,
                difficulty="medium",
                manual_status="pending",
                notes="compare_two_products",
            )
        )

    # Product recommendation -------------------------------------------------
    recommendation_n = group_counts.get("product_recommendation", 0)
    recommendation_products = _sample(products, recommendation_n, seed + 3)
    for index, product in enumerate(recommendation_products, start=1):
        session_id = f"conv-rec-{index:04d}"
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t0",
                session_id=session_id,
                turn_index=0,
                category="product_recommendation",
                question=_recommendation_text(product),
                expected_answer_type="recommendation",
                entity_ids=product.product_id,
                depends_on_history=False,
                difficulty="medium",
                manual_status="pending",
                notes="criteria_based_reference",
            )
        )

    # Follow-up ordinal (2-turn sessions) ------------------------------------
    ordinal_n = group_counts.get("followup_ordinal", 0)
    ordinal_products = _sample(products, ordinal_n, seed + 4)
    for index, product in enumerate(ordinal_products, start=1):
        session_id = f"conv-ord-{index:04d}"
        ordinal_text, ordinal_idx = _ORDINAL_TEMPLATES[(index - 1) % len(_ORDINAL_TEMPLATES)]
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t0",
                session_id=session_id,
                turn_index=0,
                category="followup_ordinal",
                question=_search_text(product),
                expected_answer_type="search_initial",
                entity_ids=product.product_id,
                depends_on_history=False,
                difficulty="medium",
                manual_status="pending",
                notes="initial_search_turn",
            )
        )
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t1",
                session_id=session_id,
                turn_index=1,
                category="followup_ordinal",
                question=ordinal_text,
                expected_answer_type="ordinal_reference",
                entity_ids="",
                depends_on_history=True,
                difficulty="hard",
                manual_status="pending",
                notes=f"ordinal_index={ordinal_idx}",
            )
        )

    # Filter refinement (2-turn sessions) ------------------------------------
    filter_n = group_counts.get("filter_refinement", 0)
    filter_products = _sample(products, filter_n, seed + 5)
    for index, product in enumerate(filter_products, start=1):
        session_id = f"conv-flt-{index:04d}"
        refinement_text = _FILTER_REFINEMENT_TEMPLATES[(index - 1) % len(_FILTER_REFINEMENT_TEMPLATES)]
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t0",
                session_id=session_id,
                turn_index=0,
                category="filter_refinement",
                question=_search_text(product),
                expected_answer_type="search_initial",
                entity_ids=product.product_id,
                depends_on_history=False,
                difficulty="medium",
                manual_status="pending",
                notes="initial_search_turn",
            )
        )
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t1",
                session_id=session_id,
                turn_index=1,
                category="filter_refinement",
                question=refinement_text,
                expected_answer_type="filter_refinement",
                entity_ids="",
                depends_on_history=True,
                difficulty="hard",
                manual_status="pending",
                notes="inherit_previous_filters",
            )
        )

    # Deterministic shop/footer knowledge ------------------------------------
    shop_knowledge_n = group_counts.get("shop_knowledge", 0)
    for index, (answer_type, question_text) in enumerate(
        _SHOP_KNOWLEDGE_CASES[:shop_knowledge_n], start=1
    ):
        session_id = f"conv-shop-{index:04d}"
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t0",
                session_id=session_id,
                turn_index=0,
                category="shop_knowledge",
                question=question_text,
                expected_answer_type=answer_type,
                entity_ids="",
                depends_on_history=False,
                difficulty="easy" if index <= 2 else "medium",
                manual_status="pending",
                notes="expected_deterministic_shop_knowledge",
            )
        )

    # Unanswerable / out-of-scope --------------------------------------------
    unanswerable_n = group_counts.get("unanswerable", 0)
    unanswerable_products = _sample(products, unanswerable_n, seed + 6)
    for index in range(unanswerable_n):
        # v2 prevents stale approval metadata from the former policy-refusal
        # cases being carried onto this deliberately smaller unsupported set.
        session_id = f"conv-una-v2-{index + 1:04d}"
        static_count = len(_UNANSWERABLE_TEMPLATES_STATIC)
        if index < static_count:
            question_text = _UNANSWERABLE_TEMPLATES_STATIC[index]
        else:
            template = _UNANSWERABLE_TEMPLATES_PRODUCT[(index - static_count) % len(_UNANSWERABLE_TEMPLATES_PRODUCT)]
            product = unanswerable_products[index % len(unanswerable_products)] if unanswerable_products else None
            name = product_display(product) if product else "Sản phẩm này"
            question_text = template.format(name=name)
        records.append(
            ConvQuestionRecord(
                question_id=f"{session_id}-t0",
                session_id=session_id,
                turn_index=0,
                category="unanswerable",
                question=question_text,
                expected_answer_type="refusal",
                entity_ids="",
                depends_on_history=False,
                difficulty="hard",
                manual_status="pending",
                notes="expected_refusal_not_supported",
            )
        )

    return records


# ---------------------------------------------------------------------------
# Reference answer + required evidence generation (03)
# ---------------------------------------------------------------------------

def _guardrail_block(extra: list[str] | None = None) -> str:
    items = list(GUARDRAIL_MUST_NOT_INCLUDE)
    if extra:
        items.extend(extra)
    return " | ".join(items)


def _ordinal_index_from_notes(notes: str) -> str:
    match = re.search(r"ordinal_index=(\d+)", notes)
    return match.group(1) if match else "được chỉ định"


def build_reference_and_evidence(
    question_row: dict[str, str],
    products_by_id: dict[str, ConvProductRecord],
) -> tuple[ConvReferenceRecord, list[ConvEvidenceRecord]]:
    question_id = first_non_empty(question_row, "question_id")
    answer_type = first_non_empty(question_row, "expected_answer_type")
    entity_ids_raw = first_non_empty(question_row, "entity_ids")
    notes = first_non_empty(question_row, "notes")
    ids = [value.strip() for value in re.split(r"[;,]", entity_ids_raw) if value.strip()]
    products = [products_by_id[pid] for pid in ids if pid in products_by_id]

    evidence: list[ConvEvidenceRecord] = []

    def add_evidence(source_id: str, text: str, role: str, level: str, note: str) -> None:
        evidence.append(
            ConvEvidenceRecord(
                question_id=question_id,
                evidence_id=f"{question_id}-e{len(evidence) + 1}",
                source_id=source_id,
                evidence_text=text,
                evidence_role=role,
                required_level=level,
                notes=note,
            )
        )

    reference_answer = ""
    must_include = ""
    extra_must_not: list[str] = []
    source_ids = ";".join(ids)

    if answer_type.startswith("attribute_") and products:
        product = products[0]
        name = product_display(product)
        attr = answer_type.split("_", 1)[1]
        if attr == "color":
            phrase = _color_phrase(color_vi(product))
            reference_answer = f"{name} có {phrase}."
            must_include = color_vi(product)
            add_evidence(product.product_id, f"color={product.color}", "primary", "must_have", "attribute_color")
        elif attr == "material":
            material = material_vi(product)
            reference_answer = f"{name} được làm từ chất liệu {material}."
            must_include = material
            add_evidence(product.product_id, f"material={product.material}", "primary", "must_have", "attribute_material")
        elif attr == "gender":
            gender = gender_vi(product)
            reference_answer = f"{name} phù hợp cho {gender}."
            must_include = gender
            add_evidence(product.product_id, f"gender={product.gender}", "primary", "must_have", "attribute_gender")
        else:  # category
            category = category_vi(product)
            reference_answer = f"{name} thuộc danh mục {category}."
            must_include = category
            add_evidence(product.product_id, f"category={product.category}", "primary", "must_have", "attribute_category")

    elif answer_type == "comparison" and len(products) >= 2:
        product_a, product_b = products[0], products[1]
        name_a, name_b = product_display(product_a), product_display(product_b)
        reference_answer = (
            f"So sánh {name_a} và {name_b}: {name_a} thuộc danh mục {category_vi(product_a)}, "
            f"{_color_phrase(color_vi(product_a))}, chất liệu {material_vi(product_a)}; "
            f"{name_b} thuộc danh mục {category_vi(product_b)}, {_color_phrase(color_vi(product_b))}, "
            f"chất liệu {material_vi(product_b)}. Cần nêu rõ điểm giống và khác về danh mục, màu và chất liệu."
        )
        must_include = f"{name_a}; {name_b}"
        add_evidence(product_a.product_id, f"category={product_a.category}; color={product_a.color}; material={product_a.material}", "primary", "must_have", "compare_product_a")
        add_evidence(product_b.product_id, f"category={product_b.category}; color={product_b.color}; material={product_b.material}", "primary", "must_have", "compare_product_b")

    elif answer_type in ("recommendation", "search_initial") and products:
        product = products[0]
        category = category_vi(product)
        reference_answer = (
            f"Gợi ý các sản phẩm {category} phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do "
            f"dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: {product_display(product)}."
        )
        must_include = category
        valid_products = [
            candidate
            for candidate in products_by_id.values()
            if candidate.is_active
            and candidate.category == product.category
            and colors_match_runtime_semantics(product.color, candidate.color)
            and (not has_text(product.gender) or candidate.gender == product.gender)
        ]
        source_ids = ";".join(candidate.product_id for candidate in valid_products)
        add_evidence(
            "",
            (
                f"category={product.category}; color={product.color}; "
                f"gender={product.gender}; valid_source_count={len(valid_products)}"
            ),
            "constraint",
            "must_have",
            (
                "recommendation_valid_source_set"
                if answer_type == "recommendation"
                else "initial_search_valid_source_set"
            ),
        )
        if has_text(product.color):
            add_evidence(product.product_id, f"color={product.color}", "supporting", "nice_to_have", "recommendation_color")

    elif answer_type == "ordinal_reference":
        ordinal = _ordinal_index_from_notes(notes)
        reference_answer = (
            f"Chatbot phải tham chiếu đúng sản phẩm thứ {ordinal} trong danh sách sản phẩm ở lượt trước "
            f"và trả lời chi tiết về sản phẩm đó, không hỏi lại khi đã có ngữ cảnh."
        )
        add_evidence("", f"Sản phẩm thứ {ordinal} của lượt trước phải nằm trong ngữ cảnh hội thoại", "constraint", "must_have", "requires_previous_turn_context")

    elif answer_type == "filter_refinement":
        reference_answer = (
            "Chatbot phải kế thừa filter của lượt trước (danh mục, khoảng giá) và áp dụng thêm hoặc thay thế "
            "filter mới từ câu này (màu sắc hoặc giá), rồi trả về sản phẩm phù hợp với ngữ cảnh đã gộp."
        )
        add_evidence("", "Filter của lượt trước phải được giữ và merge với filter mới của lượt này", "constraint", "must_have", "requires_previous_filters")

    elif answer_type == "shop_identity_and_location":
        reference_answer = (
            "Shop có tên là Mystery Closet (trang giới thiệu dùng tên Mystery Closet Store). "
            "Địa chỉ shop là 260 Lý Thường Kiệt, Phường 14, Quận 10, TP. HCM, Việt Nam."
        )
        must_include = "Mystery Closet;260 Lý Thường Kiệt;Quận 10;TP. HCM"
        add_evidence(
            "",
            "Footer: Mystery Closet; địa chỉ 260 Lý Thường Kiệt, Phường 14, Quận 10, TP. HCM",
            "constraint",
            "must_have",
            "footer_identity_and_contact",
        )

    elif answer_type == "catalog_overview":
        category_counts: dict[str, int] = {}
        for product in products_by_id.values():
            if product.is_active and has_text(product.category):
                display = _CATALOG_CATEGORY_DISPLAY_VI.get(product.category, product.category)
                category_counts[display] = category_counts.get(display, 0) + 1
        ordered_categories = sorted(
            category_counts.items(), key=lambda item: (-item[1], item[0].casefold())
        )
        rendered = ", ".join(f"{name} ({count})" for name, count in ordered_categories)
        reference_answer = (
            f"Theo catalog snapshot hiện tại, shop có {len(ordered_categories)} loại sản phẩm "
            f"đang bán: {rendered}. Không được tự thêm danh mục không xuất hiện trong catalog."
        )
        must_include = ";".join(name for name, _ in ordered_categories[:5])
        extra_must_not = ["ví da", "túi xách", "balo", "giày dép", "phụ kiện thời trang"]
        add_evidence(
            "",
            f"active catalog category counts: {rendered}",
            "constraint",
            "must_have",
            "catalog_snapshot_category_facets",
        )

    elif answer_type == "shipping_time_policy":
        reference_answer = (
            "Đơn được xử lý trong 24 giờ làm việc. Sau khi bàn giao, thời gian dự kiến là "
            "1-2 ngày làm việc ở nội thành Hà Nội/TP.HCM, 3-5 ngày ở tỉnh thành khác và "
            "5-7 ngày tại miền núi, hải đảo."
        )
        must_include = "1-2 ngày;3-5 ngày;5-7 ngày"
        add_evidence("", reference_answer, "constraint", "must_have", "shipping_policy")

    elif answer_type == "return_policy":
        reference_answer = (
            "Khách hàng có thể yêu cầu đổi trả trong 07 ngày kể từ ngày nhận hàng nếu sản "
            "phẩm còn tem nhãn, chưa sử dụng/giặt ủi và đủ điều kiện theo chính sách."
        )
        must_include = "07 ngày"
        add_evidence("", reference_answer, "constraint", "must_have", "return_policy")

    elif answer_type == "payment_methods":
        reference_answer = (
            "Mystery Closet hỗ trợ COD, chuyển khoản ngân hàng, thẻ Visa/MasterCard/JCB, "
            "ví MoMo/ZaloPay/VNPay và QR Code."
        )
        must_include = "COD;chuyển khoản;Visa;MoMo"
        add_evidence("", reference_answer, "constraint", "must_have", "payment_policy")

    elif answer_type == "express_shipping_policy":
        reference_answer = (
            "Shop có giao hỏa tốc trong ngày tại nội thành Hà Nội và TP.HCM, phí từ 50.000đ "
            "đến 100.000đ. Chính sách không công bố dịch vụ giao trong 10 phút."
        )
        must_include = "hỏa tốc trong ngày;Hà Nội;TP.HCM;không công bố dịch vụ giao trong 10 phút"
        add_evidence("", reference_answer, "constraint", "must_have", "express_shipping_policy")

    elif answer_type == "shipping_fee_policy":
        reference_answer = (
            "Shop miễn phí vận chuyển từ 500.000đ tại nội thành Hà Nội/TP.HCM hoặc từ "
            "1.000.000đ toàn quốc theo điều kiện công bố; đơn dưới 100.000đ không đạt ngưỡng freeship."
        )
        must_include = "500.000đ;1.000.000đ;đơn dưới 100.000đ"
        add_evidence("", reference_answer, "constraint", "must_have", "shipping_fee_policy")

    elif answer_type == "warranty_policy":
        reference_answer = (
            "Quần áo và phụ kiện được bảo hành 30 ngày, giày dép được bảo hành 60 ngày kể "
            "từ ngày mua, trong phạm vi điều kiện bảo hành của Mystery Closet."
        )
        must_include = "30 ngày;60 ngày"
        add_evidence("", reference_answer, "constraint", "must_have", "warranty_policy")

    elif answer_type == "refusal":
        reference_answer = (
            "Hiện tại shop chưa hỗ trợ thông tin này trong hệ thống tư vấn. Em xin phép chưa thể trả lời chắc chắn; "
            "anh/chị vui lòng kiểm tra trang chính sách của shop hoặc liên hệ CSKH để được hỗ trợ."
        )
        must_include = "chưa hỗ trợ"
        extra_must_not = [
            "bịa chính sách vận chuyển/đổi trả/thanh toán chưa có trong hệ thống",
            "cam kết sai về công dụng sản phẩm",
        ]
        add_evidence(
            "",
            "Không có dữ liệu catalog/footer/chính sách để xác nhận tuyên bố trong câu hỏi.",
            "constraint",
            "must_have",
            "unsupported_claim_requires_refusal",
        )

    else:
        # Fallback for rows whose entity products were not found in the snapshot.
        reference_answer = "Cần review thủ công: không dựng được reference answer tự động cho câu này."
        source_ids = ""

    return (
        ConvReferenceRecord(
            question_id=question_id,
            reference_answer=reference_answer,
            answer_must_include=must_include,
            answer_must_not_include=_guardrail_block(extra_must_not),
            reference_source_ids=source_ids,
            review_status="pending",
            notes=f"auto_generated:{answer_type}",
        ),
        evidence,
    )
