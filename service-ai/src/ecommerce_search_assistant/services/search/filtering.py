from __future__ import annotations

from dataclasses import dataclass, field
import re
from collections.abc import Iterable, Mapping
from typing import Literal

from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.aliases import (
    BRAND_ALIASES,
    COLOR_ALIASES,
    GENDER_ALIASES,
    MATERIAL_ALIASES,
    USE_CASE_ALIASES,
)
from ecommerce_search_assistant.services.search.category_taxonomy import (
    CATEGORY_QUERY_ALIASES,
    category_filter_keys,
)
from ecommerce_search_assistant.services.search.canonicalization import (
    canonicalize_brand_key,
    canonicalize_category_keys,
    canonicalize_color_keys,
    canonicalize_gender_key,
    canonicalize_material_keys,
    canonicalize_size_keys,
    canonicalize_use_case_keys,
)
from ecommerce_search_assistant.services.search.matching import fuzzy_alias_match
from ecommerce_search_assistant.services.search.normalization import (
    contains_token,
    normalize_alias_key,
    normalize_metadata_text,
    normalize_query_text as normalize_query_value,
    repair_mojibake,
)
from ecommerce_search_assistant.services.search.parsers.price import (
    extract_price,
    normalize_word_price_amounts,
    parse_price_amount,
)
from ecommerce_search_assistant.services.search.parsers.size import (
    extract_sizes,
    is_valid_size,
)

Intent = Literal[
    "search_product",
    "recommend_product",
    "find_similar",
    "compare_products",
    "product_information",
    "ask_availability",
    "size_consultation",
    "order_support",
    "general_question",
    "small_talk",
    "ask_clarification",
]
CategoryMatchType = Literal["exact", "alias", "typo", "inferred"]


@dataclass(frozen=True)
class QueryAnalysis:
    original_query: str
    normalized_query: str
    corrected_query: str
    intent: Intent
    metadata: dict[str, object] = field(default_factory=dict)
    filters: SearchFilter = field(default_factory=SearchFilter)
    semantic_constraints: list[str] = field(default_factory=list)
    remaining_text: str = ""
    confidences: dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0
    candidate_categories: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    should_call_llm: bool = False
    catalog_title_query: str | None = None
    category_key: str | None = None
    category_confidence: float = 0.0
    category_evidence: str | None = None
    category_match_type: CategoryMatchType | None = None

    @property
    def semantic_query(self) -> str:
        values = self.semantic_constraints
        if not values and self.remaining_text:
            values = [self.remaining_text]
        if not values:
            values = [self.corrected_query]
        return _dedupe_join(values)

    @property
    def soft_constraints(self) -> list[str]:
        return self.semantic_constraints


@dataclass(frozen=True)
class CatalogMetadata:
    categories: frozenset[str] = frozenset()
    brands: frozenset[str] = frozenset()
    colors: frozenset[str] = frozenset()
    genders: frozenset[str] = frozenset()
    materials: frozenset[str] = frozenset()
    sizes: frozenset[str] = frozenset()
    normalized_titles: frozenset[str] = frozenset()
    title_product_ids: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    product_filter_payloads: Mapping[str, Mapping[str, object]] = field(
        default_factory=dict
    )
    min_price: float | None = None
    max_price: float | None = None

    @property
    def has_values(self) -> bool:
        return any(
            (
                self.categories,
                self.brands,
                self.colors,
                self.genders,
                self.materials,
                self.sizes,
                self.normalized_titles,
                self.min_price is not None,
                self.max_price is not None,
            )
        )


_TYPO_ALIASES = {
    'so co la': 'chocolate',
    # Controlled taxonomy/material corrections. Multi-word rules provide enough
    # context to avoid autocorrecting arbitrary catalog, brand, size or SKU text.
    "chn vay": "chan vay",
    "vay qun": "vay quan",
    "blose": "blouse",
    "jumpuit": "jumpsuit",
    "popin": "poplin",
    "hodie": "hoodie",
    "hoddie": "hoodie",
    "hoodi": "hoodie",
    "sniker": "sneaker",
    "sneker": "sneaker",
    "snicker": "sneaker",
    "adiads": "adidas",
    "addidas": "adidas",
    "adiddas": "adidas",
    "nik": "nike",
}

_COLOR_ALIASES = COLOR_ALIASES
_CATEGORY_ALIASES = dict(CATEGORY_QUERY_ALIASES)
_BRAND_ALIASES = BRAND_ALIASES
_MATERIAL_ALIASES = MATERIAL_ALIASES
_USE_CASE_ALIASES = USE_CASE_ALIASES

_USAGE_ALIASES = {
    "di hoc": "school",
    "di lam": "work",
    "cong so": "work",
    "di choi": "casual weekend",
    "cuoi tuan": "casual weekend",
    "chay bo": "running",
    "di chay": "running",
    "the thao": "sports",
    "tap gym": "gym",
    "leo nui": "hiking outdoor",
    "outdoor": "outdoor",
    "du lich": "travel",
}

_FIT_ALIASES = {
    "form rong": "oversized",
    "rong": "oversized",
    "oversize": "oversized",
    "oversized": "oversized",
    "slim fit": "slim fit",
    "om": "slim fit",
    "regular fit": "regular fit",
    "basic": "basic",
}

_SEASON_ALIASES = {
    "mua he": "summer",
    "ngay he": "summer",
    "he": "summer",
    "mua dong": "winter",
    "thu dong": "winter",
    "troi lanh": "winter",
    "lanh": "winter",
    "mua mua": "rainy",
    "chong nuoc": "rainy water resistant",
}

_PATTERN_ALIASES = {
    "tron": "solid",
    "basic tron": "solid",
    "ke soc": "striped",
    "soc": "striped",
    "caro": "checkered",
    "hoa": "floral",
    "in chu": "graphic",
    "graphic": "graphic",
}

_TECHNOLOGY_ALIASES = {
    "chong nuoc": "water resistant",
    "waterproof": "waterproof",
    "thoang khi": "breathable",
    "breathable": "breathable",
    "giu am": "warm",
    "co gian": "stretch",
    "stretch": "stretch",
    "windproof": "windproof",
    "chong gio": "windproof",
}

_GENDER_ALIASES = GENDER_ALIASES
_FILLER_WORDS_PATTERN = re.compile(
    r"\b(?:"
    r"tim|can|mua|cho|minh|toi|em|anh|chi|ban|shop|oi|nhe|nha|giup|voi|"
    r"loai|cai|mau|mau nao|san pham|hang|do|mon|gia|kieu|dang|phu hop|mac|"
    r"co|nao|nao la|duoc|khong|nua|them|mot|vai"
    r")\b"
)
_NON_CATEGORY_HOMOGRAPH_PATTERN = re.compile(r"(?<!\w)vậy(?!\w)", re.IGNORECASE)

_LEGGINGS_HOMOGRAPH_PATTERN = re.compile(
    r'(?<!\w)quần\s+bó(?!\w)',
    re.IGNORECASE,
)


_OUT_OF_CATALOG_DOMAINS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "medical",
        (
            "khang sinh",
            "dieu tri",
            "viem phoi",
            "bac si",
            "duoc pham",
            "thuoc giam dau",
            "thuoc cam",
        ),
    ),
    (
        "travel_service",
        (
            "ve may bay",
            "chuyen bay",
            "dat ve",
            "khach san",
            "tour du lich",
        ),
    ),
    (
        "electronics",
        (
            "laptop",
            "may tinh",
            "dien thoai",
            "smartphone",
            "rtx",
            "card do hoa",
        ),
    ),
    (
        "appliance",
        (
            "tu lanh",
            "may giat",
            "may rua bat",
            "dieu hoa",
            "may lanh",
        ),
    ),
    (
        "vehicle",
        (
            "xe may",
            "xe may dien",
            "o to",
            "xe hoi",
            "xe dap dien",
        ),
    ),
    (
        "shop_policy",
        (
            "giao trong bao lau",
            "doi tra san pham",
            "thanh toan bang",
            "giao trong 10 phut",
            "freeship",
            "bao hanh",
        ),
    ),
    (
        "unsupported_claim",
        (
            "nguoi noi tieng",
            "chac chan giup",
        ),
    ),
    (
        "shop_policy",
        (
            "giao trong bao lau",
            "doi tra san pham",
            "thanh toan bang",
            "giao trong 10 phut",
            "freeship",
            "bao hanh",
        ),
    ),
    (
        "unsupported_claim",
        (
            "nguoi noi tieng",
            "chac chan giup",
        ),
    ),
)

# High-precision feasibility checks for requests that otherwise look like a
# normal fashion query.  Each phrase is only blocking when the current catalog
# has no title containing it, so a future catalog expansion automatically makes
# the request searchable without changing this list.
_CATALOG_FEASIBILITY_PHRASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("negative_ood", ("giay truot tuyet", "ski boots", "ski boot")),
    (
        "negative_impossible",
        (
            "chong dan",
            "bulletproof",
            "dinh kim cuong",
            "gan kim cuong",
            "diamond studded",
        ),
    ),
)


def analyze_query(
    message: str,
    catalog_metadata: CatalogMetadata | None = None,
    *,
    typo_correction_enabled: bool = True,
) -> QueryAnalysis:
    normalized = normalize_query_text(message)
    corrected, spelling_warnings = (
        correct_spelling(normalized)
        if typo_correction_enabled
        else (normalized, [])
    )
    corrected = normalize_word_price_amounts(corrected)
    category_source_text = _category_source_text(
        message,
        typo_correction_enabled=typo_correction_enabled,
    )
    filter_hints, metadata, matched_terms, metadata_confidences, extraction_warnings = _extract_metadata(
        corrected,
        catalog_metadata,
        category_source_text=category_source_text,
    )
    category_evidence = str(metadata.get("category_evidence") or "") or None
    category_match_type = metadata.get("category_match_type")
    if (
        category_evidence
        and category_match_type in {"exact", "alias"}
        and _evidence_uses_spelling_correction(category_evidence, spelling_warnings)
    ):
        category_match_type = "typo"
        metadata["category_match_type"] = "typo"
        raw_sources = metadata.setdefault("match_sources", {})
        if isinstance(raw_sources, dict):
            raw_sources["category"] = "typo"
        metadata_confidences["category"] = min(
            0.94,
            max(0.9, metadata_confidences.get("category", 0.0)),
        )
    price_filter, price_metadata, price_terms, price_confidence = extract_price_filters(corrected)
    filters = merge_filters(filter_hints, price_filter) or SearchFilter()
    metadata.update(price_metadata)
    matched_terms.extend(price_terms)
    if price_confidence:
        match_sources = metadata.setdefault("match_sources", {})
        if isinstance(match_sources, dict):
            match_sources["price"] = "regex"

    intent, intent_confidence = detect_intent(corrected, metadata)
    filters, conflict_warnings, candidate_categories = resolve_filter_conflicts(
        filters,
        corrected,
        category_source_text=category_source_text,
    )
    filters, validation_warnings = validate_metadata(filters, catalog_metadata)
    semantic_constraints = extract_semantic_constraints(
        corrected,
        matched_terms,
        metadata,
        primary_category=filters.category,
        candidate_categories=candidate_categories,
    )
    remaining_text = build_remaining_text(corrected, matched_terms)
    confidences = {
        **metadata_confidences,
        "price": price_confidence,
        "intent": intent_confidence,
    }
    analysis_warnings = extraction_warnings + conflict_warnings + validation_warnings
    overall_confidence = score_overall_confidence(confidences, remaining_text, analysis_warnings)
    should_call = should_call_llm(
        intent=intent,
        remaining_text=remaining_text,
        confidences=confidences,
        warnings=analysis_warnings,
        semantic_constraints=semantic_constraints,
    )
    return QueryAnalysis(
        original_query=message,
        normalized_query=normalized,
        corrected_query=corrected,
        intent=intent,
        metadata={**metadata, **filters.model_dump(exclude_none=True)},
        filters=filters,
        semantic_constraints=semantic_constraints,
        remaining_text=remaining_text,
        confidences=confidences,
        overall_confidence=overall_confidence,
        candidate_categories=candidate_categories,
        warnings=spelling_warnings + analysis_warnings,
        should_call_llm=should_call,
        catalog_title_query=extract_catalog_title_query(message),
        category_key=filters.category,
        category_confidence=confidences.get("category", 0.0),
        category_evidence=category_evidence,
        category_match_type=(
            category_match_type
            if category_match_type in {"exact", "alias", "typo", "inferred"}
            else None
        ),
    )


def extract_catalog_title_query(message: str) -> str | None:
    """Extract an explicitly quoted catalog title without surrounding request filler."""
    titles = extract_catalog_title_queries(message)
    return titles[0] if titles else None


def extract_catalog_title_queries(message: str) -> list[str]:
    """Extract all distinct quoted catalog entities in their original order."""
    titles = (
        normalize_query_text(match.group(1).strip())
        for match in re.finditer(r'["“”]([^"“”]{2,300})["“”]', message)
    )
    return list(dict.fromkeys(title for title in titles if title))


def detect_out_of_catalog_domain(message: str) -> str | None:
    """Return a high-precision non-fashion domain without invoking retrieval."""
    normalized = normalize_query_text(message)
    padded = f" {normalized} "
    for domain, phrases in _OUT_OF_CATALOG_DOMAINS:
        if any(f" {phrase} " in padded for phrase in phrases):
            return domain
    return None


def detect_catalog_feasibility_rejection(
    message: str,
    catalog_metadata: CatalogMetadata,
) -> str | None:
    """Return a conservative rejection reason for an unsupported catalog request.

    This deliberately checks explicit multi-token phrases rather than applying
    a similarity threshold.  A phrase stops being a rejection signal as soon as
    it occurs in a catalog title, which preserves recall when inventory grows.
    """
    if detect_out_of_catalog_domain(message):
        return "negative_ood"

    normalized = normalize_query_text(message)
    padded = f" {normalized} "
    for reason, phrases in _CATALOG_FEASIBILITY_PHRASES:
        matched = next((phrase for phrase in phrases if f" {phrase} " in padded), None)
        if matched is None:
            continue
        if any(f" {matched} " in f" {title} " for title in catalog_metadata.normalized_titles):
            continue
        return reason
    return None


def normalize_query_text(message: str) -> str:
    return normalize_query_value(message)


def correct_spelling(normalized: str) -> tuple[str, list[str]]:
    corrected = normalized
    warnings: list[str] = []
    for typo, replacement in sorted(
        _TYPO_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        updated = re.sub(rf"(?<![a-z0-9]){re.escape(typo)}(?![a-z0-9])", replacement, corrected)
        if updated != corrected:
            warnings.append(f"spell_corrected:{typo}->{replacement}")
            corrected = updated
    return corrected, warnings


def extract_metadata(text: str) -> tuple[SearchFilter, dict[str, object], list[str], dict[str, float]]:
    filters, metadata, matched_terms, confidences, _ = _extract_metadata(text)
    return filters, metadata, matched_terms, confidences


def _extract_metadata(
    text: str,
    catalog_metadata: CatalogMetadata | None = None,
    *,
    category_source_text: str | None = None,
) -> tuple[SearchFilter, dict[str, object], list[str], dict[str, float], list[str]]:
    metadata: dict[str, object] = {}
    matched_terms: list[str] = []
    confidences: dict[str, float] = {}
    warnings: list[str] = []
    match_sources: dict[str, str] = {}
    extraction_text = _remove_terms(text, extract_price(text).matched_terms)

    category_extraction_source = (
        _remove_terms(
            category_source_text,
            extract_price(category_source_text).matched_terms,
        )
        if category_source_text is not None
        else extraction_text
    )
    category_text = _category_extraction_text(category_extraction_source)
    category, category_terms = _extract_primary_alias_with_terms(category_text, _CATEGORY_ALIASES)
    brand_aliases = dict(_BRAND_ALIASES)
    if catalog_metadata:
        brand_aliases.update(
            (normalize_alias_key(brand), canonicalize_brand_key(brand) or brand)
            for brand in catalog_metadata.brands
        )
    brand, brand_terms = _extract_alias_with_terms(extraction_text, brand_aliases)
    colors, color_terms = _extract_aliases_with_terms(extraction_text, _COLOR_ALIASES)
    gender, gender_terms = _extract_alias_with_terms(extraction_text, _GENDER_ALIASES)
    # A long color phrase owns its complete token span. This prevents the `da`
    # in `xanh da troi` from being interpreted as leather.
    material_text = _remove_terms(extraction_text, color_terms)
    material, material_terms = _extract_alias_with_terms(material_text, _MATERIAL_ALIASES)
    usages, usage_terms = _extract_aliases_with_terms(extraction_text, _USAGE_ALIASES)
    fits, fit_terms = _extract_aliases_with_terms(extraction_text, _FIT_ALIASES)
    seasons, season_terms = _extract_aliases_with_terms(extraction_text, _SEASON_ALIASES)
    patterns, pattern_terms = _extract_aliases_with_terms(extraction_text, _PATTERN_ALIASES)
    technologies, technology_terms = _extract_aliases_with_terms(extraction_text, _TECHNOLOGY_ALIASES)
    size_extraction = extract_sizes(extraction_text)

    if not category:
        fuzzy_category = fuzzy_alias_match(category_text, _CATEGORY_ALIASES)
        if fuzzy_category.ambiguous:
            warnings.append("ambiguous_fuzzy_match")
        elif fuzzy_category.value:
            category = fuzzy_category.value
            category_terms = [fuzzy_category.query_term or fuzzy_category.alias or ""]
            confidences["category"] = round(fuzzy_category.confidence * 0.9, 3)
            match_sources["category"] = "fuzzy"
            metadata["category_match_type"] = "inferred"
            metadata["category_evidence"] = (
                fuzzy_category.query_term or fuzzy_category.alias or ""
            )
            metadata.setdefault("fuzzy_matches", {})["category"] = {
                "query": fuzzy_category.query_term,
                "alias": fuzzy_category.alias,
            }

    if not brand:
        fuzzy_brand = fuzzy_alias_match(extraction_text, brand_aliases)
        if fuzzy_brand.ambiguous:
            warnings.append("ambiguous_fuzzy_match")
        elif fuzzy_brand.value:
            brand = fuzzy_brand.value
            brand_terms = [fuzzy_brand.query_term or fuzzy_brand.alias or ""]
            confidences["brand"] = round(fuzzy_brand.confidence * 0.9, 3)
            match_sources["brand"] = "fuzzy"
            metadata.setdefault("fuzzy_matches", {})["brand"] = {
                "query": fuzzy_brand.query_term,
                "alias": fuzzy_brand.alias,
            }

    matched_terms.extend(
        category_terms
        + brand_terms
        + color_terms
        + gender_terms
        + material_terms
        + usage_terms
        + fit_terms
        + season_terms
        + pattern_terms
        + technology_terms
        + list(size_extraction.matched_terms)
    )
    if category:
        metadata["category"] = category
        evidence = next((term for term in category_terms if term), "")
        match_type: CategoryMatchType = (
            "exact"
            if evidence and normalize_alias_key(evidence) == normalize_alias_key(category)
            else "alias"
        )
        confidences.setdefault("category", 0.99 if match_type == "exact" else 0.97)
        match_sources.setdefault("category", match_type)
        metadata.setdefault("category_match_type", match_type)
        metadata.setdefault("category_evidence", evidence)
    if brand:
        metadata["brand"] = brand
        confidences.setdefault("brand", 0.99)
        match_sources.setdefault("brand", "dictionary")
    if colors:
        metadata["colors"] = colors
        confidences["color"] = 0.95
        match_sources["color"] = "dictionary"
    if gender:
        metadata["gender"] = gender
        confidences["gender"] = 0.9
        match_sources["gender"] = "dictionary"
    if material:
        metadata["material"] = material
        confidences["material"] = 0.75
        match_sources["material"] = "dictionary"
    if usages:
        metadata["usage"] = usages
        confidences["usage"] = 0.72
    if fits:
        metadata["fit"] = fits
        confidences["fit"] = 0.85
    if seasons:
        metadata["season"] = seasons
        confidences["season"] = 0.76
    if patterns:
        metadata["pattern"] = patterns
        confidences["pattern"] = 0.8
    if technologies:
        metadata["technology"] = technologies
        confidences["technology"] = 0.76
    if size_extraction.values:
        metadata["sizes"] = [size.upper() for size in size_extraction.values]
        confidences["size"] = size_extraction.confidence
        match_sources["size"] = "regex"
    if match_sources:
        metadata["match_sources"] = match_sources

    return (
        SearchFilter(
            category=category,
            brand=brand,
            colors=colors or None,
            use_cases=canonicalize_use_case_keys([*usages, *seasons]) or None,
            sizes=[size.upper() for size in size_extraction.values] or None,
            gender=gender,
            material=material,
        ),
        metadata,
        matched_terms,
        confidences,
        list(dict.fromkeys(warnings)),
    )


def extract_price_filters(text: str) -> tuple[SearchFilter, dict[str, object], list[str], float]:
    extraction = extract_price(text)
    metadata = dict(extraction.metadata)
    confidence = extraction.confidence

    if any(_contains_token(text, token) for token in ("gia re", "re", "budget")):
        metadata["price_segment"] = "budget"
        metadata["sort"] = "price_asc"
        confidence = max(confidence, 0.7)
    if any(_contains_token(text, token) for token in ("cao cap", "premium", "hang xịn", "hang xin")):
        metadata["price_segment"] = "premium"
        confidence = max(confidence, 0.7)

    return (
        SearchFilter(min_price=extraction.min_price, max_price=extraction.max_price),
        metadata,
        list(extraction.matched_terms),
        confidence,
    )


def detect_intent(text: str, metadata: Mapping[str, object] | None = None) -> tuple[Intent, float]:
    del metadata
    if any(phrase in text for phrase in ("don hang", "giao hang", "van chuyen", "doi tra", "hoan tien")):
        return "order_support", 0.9
    if any(phrase in text for phrase in ("size nao", "chon size", "tu van size", "size phu hop")):
        return "size_consultation", 0.86
    if any(phrase in text for phrase in ("giong", "tuong tu", "similar", "look like", "mau nao giong")):
        return "find_similar", 0.86
    if any(phrase in text for phrase in ("so sanh", "compare", "khac nhau")):
        return "compare_products", 0.86
    if any(phrase in text for phrase in ("con hang", "het hang", "available", "stock")):
        return "ask_availability", 0.84
    if any(phrase in text for phrase in ("thong tin", "chat lieu", "bao hanh", "chi tiet")):
        return "product_information", 0.76
    if any(phrase in text for phrase in ("goi y", "tu van", "nen mua", "recommend")):
        return "recommend_product", 0.78
    if is_small_talk(text):
        return "small_talk", 0.96
    return "search_product", 0.72


def resolve_filter_conflicts(
    filters: SearchFilter,
    text: str,
    *,
    category_source_text: str | None = None,
) -> tuple[SearchFilter, list[str], list[str]]:
    warnings: list[str] = []
    candidate_categories = _extract_non_overlapping_category_candidates(
        _category_extraction_text(category_source_text if category_source_text is not None else text),
    )
    data = filters.model_dump(exclude_none=True)
    if len(candidate_categories) > 1:
        warnings.append("ambiguous_category")
    if filters.min_price is not None and filters.max_price is not None and filters.min_price > filters.max_price:
        data["min_price"], data["max_price"] = filters.max_price, filters.min_price
        warnings.append("hard_conflict:price_range_swapped")
    return SearchFilter(**data), warnings, candidate_categories


def validate_metadata(
    filters: SearchFilter,
    catalog_metadata: CatalogMetadata | None = None,
) -> tuple[SearchFilter, list[str]]:
    warnings: list[str] = []
    data = filters.model_dump(exclude_none=True)
    catalog = catalog_metadata if catalog_metadata and catalog_metadata.has_values else None

    if filters.category and not _valid_catalog_category(
        filters.category,
        catalog.categories if catalog else None,
    ):
        data.pop("category", None)
        warnings.append("invalid_category")
    if filters.brand and not _valid_catalog_or_alias(filters.brand, _BRAND_ALIASES, catalog.brands if catalog else None):
        data.pop("brand", None)
        warnings.append("invalid_brand")
    if filters.colors:
        valid_colors = [
            color
            for color in filters.colors
            if _valid_catalog_or_alias(color, _COLOR_ALIASES, catalog.colors if catalog else None)
        ]
        if len(valid_colors) != len(filters.colors):
            warnings.append("invalid_color")
        if valid_colors:
            data["colors"] = valid_colors
        else:
            data.pop("colors", None)
    if filters.gender and not _valid_catalog_or_alias(filters.gender, _GENDER_ALIASES, catalog.genders if catalog else None):
        data.pop("gender", None)
        warnings.append("invalid_gender")
    if filters.material and not _valid_catalog_or_alias(filters.material, _MATERIAL_ALIASES, catalog.materials if catalog else None):
        data.pop("material", None)
        warnings.append("invalid_material")
    if filters.sizes:
        valid_sizes = [
            size
            for size in filters.sizes
            if _is_valid_size(size) and _valid_catalog_size(size, catalog.sizes if catalog else None)
        ]
        if len(valid_sizes) != len(filters.sizes):
            warnings.append("invalid_size")
        if valid_sizes:
            data["sizes"] = valid_sizes
        else:
            data.pop("sizes", None)
    min_price = data.get("min_price")
    max_price = data.get("max_price")
    if min_price is not None and max_price is not None and float(min_price) > float(max_price):
        data["min_price"], data["max_price"] = max_price, min_price
        warnings.append("invalid_price_range_swapped")
    if catalog:
        min_price = data.get("min_price")
        max_price = data.get("max_price")
        if catalog.max_price is not None and min_price is not None and float(min_price) > catalog.max_price:
            warnings.append("price_outside_catalog")
            data.pop("min_price", None)
        if catalog.min_price is not None and max_price is not None and float(max_price) < catalog.min_price:
            if "price_outside_catalog" not in warnings:
                warnings.append("price_outside_catalog")
            data.pop("max_price", None)
    return SearchFilter(**data), list(dict.fromkeys(warnings))


def extract_semantic_constraints(
    text: str,
    matched_terms: Iterable[str],
    metadata: Mapping[str, object],
    *,
    primary_category: str | None = None,
    candidate_categories: Iterable[str] = (),
) -> list[str]:
    constraints: list[str] = []
    for key in ("usage", "fit", "season", "pattern", "technology", "price_segment"):
        value = metadata.get(key)
        if isinstance(value, list):
            constraints.extend(str(item) for item in value)
        elif value:
            constraints.append(str(value))
    constraints.extend(
        f"{category} style"
        for category in candidate_categories
        if category and category != primary_category
    )
    remaining = build_remaining_text(text, matched_terms)
    if remaining and len(remaining.split()) <= 5:
        constraints.append(remaining)
    return _dedupe(constraints)


def build_remaining_text(text: str, matched_terms: Iterable[str]) -> str:
    remaining = _remove_terms(text, matched_terms)
    remaining = _FILLER_WORDS_PATTERN.sub(" ", remaining)
    return re.sub(r"\s+", " ", remaining).strip()


def _remove_terms(text: str, matched_terms: Iterable[str]) -> str:
    remaining = text
    for term in sorted(set(matched_terms), key=len, reverse=True):
        if not term:
            continue
        remaining = re.sub(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", " ", remaining)
    return re.sub(r"\s+", " ", remaining).strip()


def score_overall_confidence(
    confidences: Mapping[str, float],
    remaining_text: str,
    warnings: Iterable[str],
) -> float:
    if not confidences:
        return 0.35 if remaining_text else 0.0
    score = sum(confidences.values()) / len(confidences)
    if remaining_text and len(remaining_text.split()) > 4:
        score -= 0.15
    if list(warnings):
        score -= 0.1
    return max(0.0, min(1.0, score))


def should_call_llm(
    *,
    intent: Intent,
    remaining_text: str,
    confidences: Mapping[str, float],
    warnings: Iterable[str],
    semantic_constraints: list[str],
) -> bool:
    if intent in {"order_support", "size_consultation", "product_information", "general_question"}:
        return True
    if any(warning in {"ambiguous_category", "ambiguous_fuzzy_match"} for warning in warnings):
        return True
    if any(warning.startswith("invalid_") for warning in warnings):
        return False
    if remaining_text and len(remaining_text.split()) > 3:
        return True
    if any(score < 0.6 for score in confidences.values()):
        return True
    return bool(semantic_constraints and not confidences.get("usage") and len(remaining_text.split()) > 1)


def normalize_gender(value: str | None) -> str | None:
    if not value:
        return None
    normalized = _normalize_text(value)
    return _GENDER_ALIASES.get(normalized)


def extract_filter_hints(message: str) -> SearchFilter:
    return analyze_query(message).filters


def explicit_query_filters(analysis: QueryAnalysis | None) -> SearchFilter | None:
    """Return deterministic category/color/material constraints written in text."""

    if analysis is None:
        return None
    raw_sources = analysis.metadata.get("match_sources", {})
    sources = raw_sources if isinstance(raw_sources, Mapping) else {}
    data: dict[str, object] = {}
    ambiguous_category = any(
        warning in {"ambiguous_category", "ambiguous_fuzzy_match"}
        for warning in analysis.warnings
    )
    if (
        analysis.filters.category
        and not ambiguous_category
        and sources.get("category") in {"dictionary", "exact", "alias", "typo"}
    ):
        data["category"] = analysis.filters.category
    if analysis.filters.colors and sources.get("color") == "dictionary":
        data["colors"] = analysis.filters.colors
    if analysis.filters.material and sources.get("material") == "dictionary":
        data["material"] = analysis.filters.material
    return SearchFilter(**data) if data else None


def sanitize_llm_attribute_filters(
    llm_filters: SearchFilter | None,
    rule_filters: SearchFilter | None,
) -> SearchFilter | None:
    """Prevent the LLM from inventing color/material values absent from text."""

    if llm_filters is None:
        return None
    data = llm_filters.model_dump(exclude_none=True)
    rule_data = (
        normalize_filter_values(rule_filters).model_dump(exclude_none=True)
        if rule_filters is not None
        else {}
    )
    for field_name in ("colors", "material"):
        if field_name not in rule_data:
            data.pop(field_name, None)
        elif field_name in data:
            # Rule extraction is the source of truth for literal attributes.
            data[field_name] = rule_data[field_name]
    return normalize_filter_values(SearchFilter(**data)) if data else None


def normalize_filter_values(filters: SearchFilter | None) -> SearchFilter | None:
    if filters is None:
        return None

    data = filters.model_dump(exclude_none=True)
    if filters.category:
        category_keys = canonicalize_category_keys([filters.category])
        if category_keys:
            data["category"] = category_keys[0]
        else:
            data.pop("category", None)
    if filters.brand:
        brand_key = canonicalize_brand_key(filters.brand)
        if brand_key:
            data["brand"] = brand_key
        else:
            data.pop("brand", None)
    if filters.colors:
        color_keys = canonicalize_color_keys(filters.colors)
        if color_keys:
            data["colors"] = color_keys
        else:
            data.pop("colors", None)
    if filters.use_cases:
        use_case_keys = canonicalize_use_case_keys(filters.use_cases)
        if use_case_keys:
            data["use_cases"] = use_case_keys
        else:
            data.pop("use_cases", None)
    if filters.sizes:
        size_keys = canonicalize_size_keys(filters.sizes)
        if size_keys:
            data["sizes"] = size_keys
        else:
            data.pop("sizes", None)
    if filters.gender:
        canonical_gender = canonicalize_gender_key(filters.gender)
        if canonical_gender:
            data["gender"] = canonical_gender
        else:
            data.pop("gender", None)
    if filters.material:
        material_keys = canonicalize_material_keys([filters.material])
        if material_keys:
            data["material"] = material_keys[0]
        else:
            data.pop("material", None)
    return SearchFilter(**data)


def merge_filters(base: SearchFilter | None, override: SearchFilter | None) -> SearchFilter | None:
    if base is None:
        return normalize_filter_values(override)
    if override is None:
        return normalize_filter_values(base)

    merged = base.model_dump(exclude_none=True)
    merged.update(override.model_dump(exclude_none=True))
    return normalize_filter_values(SearchFilter(**merged))


def merge_missing_filters(base: SearchFilter | None, additions: SearchFilter | None) -> SearchFilter | None:
    """Merge filters without letting lower-priority extraction overwrite known constraints."""
    if base is None:
        return normalize_filter_values(additions)
    if additions is None:
        return normalize_filter_values(base)

    merged = base.model_dump(exclude_none=True)
    for key, value in additions.model_dump(exclude_none=True).items():
        if key not in merged:
            merged[key] = value
    return normalize_filter_values(SearchFilter(**merged))


def _parse_price_amount(amount_text: str, unit: str | None) -> float:
    return parse_price_amount(f"{amount_text}{unit or ''}")


def _extract_standalone_price(text: str) -> tuple[float, str] | None:
    extraction = extract_price(text)
    if extraction.min_price is not None and extraction.max_price is not None and extraction.matched_terms:
        return (extraction.min_price + extraction.max_price) / 2, extraction.matched_terms[0]
    return None


def _extract_alias(normalized: str, aliases: dict[str, str]) -> str | None:
    value, _ = _extract_alias_with_terms(normalized, aliases)
    return value


def _extract_aliases(normalized: str, aliases: dict[str, str]) -> list[str]:
    values, _ = _extract_aliases_with_terms(normalized, aliases)
    return values


def _extract_alias_with_terms(normalized: str, aliases: dict[str, str]) -> tuple[str | None, list[str]]:
    for alias, value in _sorted_aliases(aliases):
        if _contains_token(normalized, alias):
            return value, [alias]
    return None, []


def _extract_primary_alias_with_terms(
    normalized: str,
    aliases: dict[str, str],
) -> tuple[str | None, list[str]]:
    """Choose the first product head noun; use the longest alias only for ties."""
    matches: list[tuple[int, int, str, str]] = []
    for alias, value in aliases.items():
        match = re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", normalized)
        if match:
            matches.append((match.start(), -len(alias), value, alias))
    if not matches:
        return None, []
    _, _, value, alias = min(matches)
    return value, [alias]


def _category_extraction_text(text: str) -> str:
    """Mask attribute phrases that otherwise look like product head nouns."""
    # Catalog display labels use separators such as ``Blazer & áo vest`` while
    # category aliases are stored in punctuation-free normalized form.  Treat
    # the separator as whitespace so the full combined identity alias wins over
    # its two overlapping leaf aliases and is not marked ambiguous.
    normalized_separators = re.sub(r"\s*(?:&|/)\s*", " ", text)
    return _remove_terms(normalized_separators, ("co vest", "tay phong"))


def _category_source_text(
    message: str,
    *,
    typo_correction_enabled: bool,
) -> str:
    """Normalize category evidence without collapsing Vietnamese ``vậy`` into ``váy``."""

    repaired = _LEGGINGS_HOMOGRAPH_PATTERN.sub(
        ' leggings ',
        repair_mojibake(message),
    )
    without_context_reference = _NON_CATEGORY_HOMOGRAPH_PATTERN.sub(" ", repaired)
    normalized = normalize_query_text(without_context_reference)
    if not typo_correction_enabled:
        return normalized
    corrected, _ = correct_spelling(normalized)
    return corrected


def _extract_non_overlapping_category_candidates(text: str) -> list[str]:
    """Prefer the longest category phrase before considering real conflicts."""
    matches: list[tuple[int, int, str]] = []
    for alias, value in _CATEGORY_ALIASES.items():
        for match in re.finditer(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
            text,
        ):
            matches.append((match.start(), match.end(), value))
    selected: list[tuple[int, int, str]] = []
    for start, end, value in sorted(
        matches,
        key=lambda item: (-(item[1] - item[0]), item[0]),
    ):
        if any(start < chosen_end and end > chosen_start for chosen_start, chosen_end, _ in selected):
            continue
        selected.append((start, end, value))
    return _dedupe(value for _, _, value in sorted(selected))


def _evidence_uses_spelling_correction(
    evidence: str,
    spelling_warnings: Iterable[str],
) -> bool:
    for warning in spelling_warnings:
        if not warning.startswith("spell_corrected:") or "->" not in warning:
            continue
        _, correction = warning.split(":", 1)
        _source, replacement = correction.split("->", 1)
        if contains_token(evidence, replacement) or replacement in evidence:
            return True
    return False


def _extract_aliases_with_terms(normalized: str, aliases: dict[str, str]) -> tuple[list[str], list[str]]:
    pairs = [
        (value, alias)
        for alias, value in _sorted_aliases(aliases)
        if _contains_token(normalized, alias)
    ]
    return _dedupe(value for value, _ in pairs), [alias for _, alias in pairs]


def _extract_sizes(text: str) -> list[str]:
    return list(extract_sizes(text).values)


def _is_valid_size(size: str) -> bool:
    return is_valid_size(size)


def _valid_catalog_or_alias(
    value: str,
    aliases: Mapping[str, str],
    catalog_values: frozenset[str] | None,
    *,
    allow_partial_catalog_match: bool = False,
) -> bool:
    if not catalog_values:
        return _normalize_alias(value, dict(aliases)) in set(aliases.values())
    normalized = _normalize_catalog_value(value)
    normalized_catalog = {
        _normalize_alias(str(candidate), dict(aliases))
        for candidate in catalog_values
    }
    if normalized in normalized_catalog:
        return True
    if not allow_partial_catalog_match:
        return False
    singular = normalized.removesuffix("s")
    return any(
        singular == candidate.removesuffix("s")
        or singular in candidate
        or candidate.removesuffix("s") in singular
        for candidate in normalized_catalog
    )


def _valid_catalog_category(value: str, catalog_values: frozenset[str] | None) -> bool:
    if not catalog_values:
        return value in set(_CATEGORY_ALIASES.values())
    normalized_catalog = frozenset(_normalize_catalog_value(candidate) for candidate in catalog_values)
    if set(category_filter_keys([value])).intersection(normalized_catalog):
        return True
    return _valid_catalog_or_alias(
        value,
        _CATEGORY_ALIASES,
        normalized_catalog,
        allow_partial_catalog_match=True,
    )


def _valid_catalog_size(size: str, catalog_sizes: frozenset[str] | None) -> bool:
    if not catalog_sizes:
        return True
    return bool(set(canonicalize_size_keys([size])).intersection(canonicalize_size_keys(catalog_sizes)))


def _normalize_catalog_value(value: object) -> str:
    return normalize_metadata_text(str(value))


def _normalize_alias(value: str, aliases: dict[str, str]) -> str:
    normalized = normalize_alias_key(value)
    return aliases.get(normalized, normalized)


def _sorted_aliases(aliases: dict[str, str]) -> list[tuple[str, str]]:
    return sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True)


def _contains_token(text: str, token: str) -> bool:
    return contains_token(text, token)


def _normalize_text(value: str) -> str:
    return normalize_metadata_text(value)


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _dedupe_join(values: Iterable[str]) -> str:
    return " ".join(_dedupe(value.strip() for value in values if value and value.strip()))


def is_small_talk(normalized: str) -> bool:
    compact = re.sub(r"[^a-z0-9 ]+", "", normalized).strip()
    standalone_phrases = {
        "hello",
        "hi",
        "hey",
        "alo",
        "alo shop",
        "hello shop",
        "hi shop",
        "xin chao",
        "xin chao ban",
        "chao",
        "chao ban",
        "chao em",
        "chao anh",
        "chao chi",
        "chao shop",
        "shop oi",
        "ban oi",
        "co ai khong",
        "co ai o do khong",
        "good morning",
        "good afternoon",
        "good evening",
        "cam on",
        "cam on ban",
        "cam on em",
        "cam on shop",
        "cam on nhe",
        "ok cam on",
        "thank you",
        "thanks",
        "bye",
        "goodbye",
        "tam biet",
        "hen gap lai",
        "chuc ngu ngon",
        "ban khoe khong",
        "khoe khong",
        "ban lam duoc gi",
        "ban co the lam gi",
        "shop giup duoc gi",
        "quen so thich cua toi",
        "quen so thich cua minh",
        "xoa so thich cua toi",
        "xoa so thich cua minh",
        "xoa bo nho cua toi",
        "xoa bo nho cua minh",
        "forget my preferences",
        "clear my preferences",
    }
    return compact in standalone_phrases
