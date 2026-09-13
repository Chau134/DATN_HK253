"""Image refinement intent. Only user text and request filters are inputs.

This module deliberately has no evaluation-data or product-ID dependencies.
Canonical metadata proves constraints; unavailable evidence never proves a match.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import math
from typing import Callable

from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.aliases import MATERIAL_ALIASES, COLOR_ALIASES
from ecommerce_search_assistant.services.search.canonicalization import (
    canonicalize_material_keys, canonicalize_use_case_keys, color_filter_keys,
)
from ecommerce_search_assistant.services.search.filtering import analyze_query, explicit_query_filters
from ecommerce_search_assistant.services.search.normalization import normalize_query_text, contains_token
from ecommerce_search_assistant.services.search.category_taxonomy import canonicalize_category_values, category_filter_keys


def values(payload: dict, key: str) -> set[str]:
    value = payload.get(key)
    return {str(v) for v in value} if isinstance(value, (list, tuple)) else {str(value)} if value else set()


def materials(text: str) -> list[str]:
    # canonicalize_material_keys also preserves unknown phrases: keep only
    # recognized atomic keys here, never an entire sentence as a material.
    atomic = set(MATERIAL_ALIASES.values()) | {
        "acrylic", "cashmere", "elastane", "linen", "nylon", "polyamide",
        "silk", "viscose", "cotton", "polyester", "wool", "leather",
    }
    text = re.sub(r"\bvai lanh\b", "linen", normalize_query_text(text))
    text = re.sub(r"\blua\b", "silk", text)
    return [v for v in canonicalize_material_keys([text]) if v in atomic]


def composition(text: str) -> dict[str, float]:
    result = {}
    for amount, name in re.findall(r"(\d+(?:[.,]\d+)?)\s*%\s*([^\d,%]+)", text):
        keys = materials(name)
        if keys:
            result[keys[0]] = float(amount.replace(",", "."))
    return result


@dataclass
class HybridIntent:
    query: str
    required: SearchFilter = field(default_factory=SearchFilter)
    preferred: SearchFilter = field(default_factory=SearchFilter)
    excluded: list[SearchFilter] = field(default_factory=list)
    material_mode: str = "all"
    usage_mode: str = "all"
    usage_phrases: list[str] = field(default_factory=list)
    color_options: list[tuple[list[str], str | None]] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)
    uncertain: list[str] = field(default_factory=list)
    explicit_fields: set[str] = field(default_factory=set)
    required_composition: dict[str, float] = field(default_factory=dict)

    def checks(self, payload: dict, basic: Callable) -> dict[str, bool]:
        checks = basic(payload, self.required)
        if self.required.category:
            names = values(payload, "category_names") | values(payload, "category_names_vi")
            if names:
                checks["category"] = bool(set(category_filter_keys([self.required.category])) & set(canonicalize_category_values(names)))
        colors = self.required.colors or []
        if colors:
            matches = [bool(set(color_filter_keys([color])) & values(payload, "color_keys")) for color in colors]
            checks["colors"] = all(matches) if self.required.color_match_mode == "all" else any(matches)
            if self.color_options:
                raw_colors = " ".join(normalize_query_text(str(payload.get(key) or "")) for key in ("base_colour", "base_colour_vi"))
                option_matches = [(not keys or bool(set(color_filter_keys(keys)) & values(payload, "color_keys"))) and (shade is None or contains_token(raw_colors, shade)) for keys, shade in self.color_options]
                checks["colors"] = all(option_matches) if self.required.color_match_mode == "all" else any(option_matches)
        if self.required.material:
            wanted = set(materials(self.required.material))
            actual = values(payload, "material_keys") | set(materials(str(payload.get("material") or payload.get("material_vi") or "")))
            checks["material"] = bool(wanted) and (wanted <= actual if self.material_mode == "all" else bool(wanted & actual))
        if self.required_composition:
            actual_composition = composition(str(payload.get("material") or payload.get("material_vi") or ""))
            checks["material_composition"] = all(actual_composition.get(key) == amount for key, amount in self.required_composition.items())
        if self.required.use_cases:
            wanted = set(canonicalize_use_case_keys(self.required.use_cases))
            actual = values(payload, "use_case_keys")
            checks["use_cases"] = bool(wanted) and (wanted <= actual if self.usage_mode == "all" else bool(wanted & actual))
            # Several literal activities map to the same broad canonical key.
            # Where the user names them, verify the actual catalog description.
            if self.usage_phrases:
                usage = normalize_query_text(str(payload.get("product_usage_vi") or ""))
                matches = [contains_token(usage, phrase) for phrase in self.usage_phrases]
                checks["use_cases"] = all(matches) if self.usage_mode == "all" else any(matches)
        for index, forbidden in enumerate(self.excluded):
            forbidden_checks = basic(payload, forbidden)
            # Missing metadata does not establish that a forbidden value is absent.
            keys = {"colors": "color_keys", "material": "material_keys", "use_cases": "use_case_keys", "category": "category_keys"}
            known = all(bool(values(payload, keys[k])) for k in forbidden_checks if k in keys)
            checks[f"excluded_{index}"] = known and bool(forbidden_checks) and not all(forbidden_checks.values())
        if self.uncertain:
            checks["unresolved_required"] = False
        return checks


def parse_hybrid_intent(query: str | None, explicit: SearchFilter | None = None) -> HybridIntent:
    text = normalize_query_text(query or "")
    # Replacement source is discarded only when there is a destination marker.
    text = re.sub(r"\b(?:doi\s+tu|tu\s+(?=mau\b|chat lieu\b))\s*.+?\s+sang\s+", "", text)
    intent = HybridIntent(query=text)
    if re.search(r"\bkhong\s+(?:duoi|tren)\b", text):
        intent.uncertain.append("unsupported_negated_price")
    positive = text
    preferred_parts: list[str] = []
    # Preference ends at the next explicit attribute marker. A later hard price
    # must not become optional because an earlier clause said 'uu tien'.
    preference = re.compile(r"\b(?:uu tien|neu co|preferably)\s+(.+?)(?=\s+(?:nhung|gia|duoi|tren|mau|chat lieu|bat buoc|phai)\b|$)")
    for match in preference.finditer(text):
        preferred_parts.append(match.group(1))
    positive = preference.sub(" ", positive)
    # Negative attribute phrases end before the next positive requirement.
    negative = re.compile(r"\b(?:khong(?!\s+(?:qua|duoi|tren)\b)(?: phai)?|tru|ngoai tru)\s+(.+?)(?=\s+(?:nhung|ma|doi|phai|gia|duoi|tren|phu hop)\b|$)")
    for match in negative.finditer(positive):
        part = match.group(1)
        parsed = analyze_query(part, typo_correction_enabled=False).filters
        fields = parsed.model_dump(exclude_none=True)
        if not fields:
            intent.uncertain.append("unresolved_negation")
        else:
            intent.excluded.append(parsed)
    positive = negative.sub(" ", positive)
    try:
        analysis = analyze_query(positive, typo_correction_enabled=False)
    except ValueError:
        intent.uncertain.append("contradictory_constraints")
        return intent
    literal = explicit_query_filters(analysis)
    data = literal.model_dump(exclude_none=True) if literal else {}
    # Category belongs to the product clause. After accent normalization, the
    # adjective 'đậm' becomes 'dam' and must not introduce the category 'đầm'.
    product_clause = re.split(r"\b(?:giong anh|nhu anh|nhung|doi sang|mau|chat lieu|gia)\b", positive, maxsplit=1)[0]
    product_analysis = analyze_query(product_clause, typo_correction_enabled=False)
    product_literal = explicit_query_filters(product_analysis)
    if product_literal and product_literal.category:
        data["category"] = product_literal.category
    for name in ("min_price", "max_price", "sizes", "brand", "gender"):
        value = getattr(analysis.filters, name)
        if value is not None:
            data[name] = value
    # Do not promote incidental words in material names (e.g. 'vải lanh')
    # into mandatory seasons/activities through the general-purpose parser.
    activity_phrases = [phrase for phrase in ("di choi", "di lam", "dao pho", "hen ho", "du tiec", "hang ngay", "du lich", "mua dong", "mua he") if contains_token(positive, phrase)]
    usage_clause = re.search(r"\b(?:phu hop|dung de)\s+(.+?)(?=\s+(?:chat lieu|gia|duoi|tren|mau)\b|$)", positive)
    use_cases = canonicalize_use_case_keys([usage_clause.group(1)] if usage_clause else activity_phrases)
    if use_cases:
        data["use_cases"] = use_cases
        # User-confirmed contract: an unqualified list of occasions is a set
        # of alternatives. Explicit conjunction/all requirements remain strict.
        usage_text = usage_clause.group(1) if usage_clause else positive
        explicitly_all = bool(re.search(r"\b(?:tat ca|ca (?:hai|ba|bon|\d+)|dong thoi)\b", usage_text))
        if usage_clause and re.search(r"\bdong thoi\s*$", positive[:usage_clause.start()]):
            explicitly_all = True
        intent.usage_mode = ("all" if explicitly_all else "any" if contains_token(usage_text, "hoac")
                             else "all" if contains_token(usage_text, "va") else "any")
    # Retain ALL mentioned fibers rather than the legacy parser's first match.
    material_clause = re.search(r"\b(?:chat lieu|vai)\s+(.+?)(?=\s+(?:phu hop|gia|duoi|tren|mau)\b|$)", positive)
    material_text = material_clause.group(1) if material_clause else str(data.get("material") or "")
    if not material_clause and material_text and material_text in positive:
        material_text = positive[positive.index(material_text):]
    found = materials(material_text)
    if found:
        data["material"] = ", ".join(found)
        intent.material_mode = "any" if contains_token(material_text, "hoac") else "all"
    elif material_clause:
        intent.uncertain.append("unresolved_material")
    color_clause = re.search(r"\bmau\s+(?!(?:giong|nhu|nay|kia)\b)(.+?)(?=\s+(?:chat lieu|phu hop|gia|duoi|tren|uu tien|size|co size|giong|nhu|nhe|nha)\b|$)", positive)
    if re.search(r"\bmẫu\b", (query or "").lower()) and not re.search(r"\bmàu\b", (query or "").lower()):
        color_clause = None
    if color_clause:
        color_text = color_clause.group(1)
        pieces = [p.removeprefix("mau ").strip() for p in re.split(r"\s+(?:va|hoac)\s+", color_text)]
        parsed_colors = []
        for piece in pieces:
            exact_color = COLOR_ALIASES.get(piece) or COLOR_ALIASES.get("mau " + piece)
            option_keys = [exact_color] if exact_color else analyze_query("mau " + piece, typo_correction_enabled=False).filters.colors or []
            parsed_colors.extend(option_keys or [piece])
            intent.color_options.append((option_keys, None if exact_color else piece))
        if parsed_colors:
            data["colors"] = list(dict.fromkeys(parsed_colors))
    if data.get("colors"):
        color_logic_text = color_clause.group(1) if color_clause else ""
        data["color_match_mode"] = "any" if contains_token(color_logic_text, "hoac") else "all" if contains_token(color_logic_text, "va") else "any"
    if data.get("use_cases"):
        intent.usage_phrases = [phrase for phrase in ("di choi", "di lam", "dao pho", "hen ho", "du tiec", "hang ngay", "du lich") if contains_token(positive, phrase)]
    # Preserve price operator semantics at exact boundaries for float prices.
    if data.get("max_price") is not None and contains_token(positive, "duoi"):
        data["max_price"] = math.nextafter(data["max_price"], -math.inf)
    if data.get("min_price") is not None and contains_token(positive, "tren"):
        data["min_price"] = math.nextafter(data["min_price"], math.inf)
    for name in data:
        intent.evidence[name] = positive
    for match in re.finditer(r"\d+(?:[.,]\d+)?\s*%\s*[^\d,%]+", query or ""):
        if normalize_query_text(match.group()).strip() in positive:
            intent.required_composition.update(composition(match.group()))
    explicit_data = explicit.model_dump(exclude_none=True) if explicit else {}
    intent.explicit_fields = set(explicit_data)
    data.update(explicit_data)
    if "material" in explicit_data:
        intent.required_composition = {}
        intent.material_mode = "any"  # Existing API semantics.
        intent.uncertain = [v for v in intent.uncertain if v != "unresolved_material"]
    if "use_cases" in explicit_data:
        intent.usage_mode, intent.usage_phrases = "any", []
    if "colors" in explicit_data:
        intent.color_options = []
        data["color_match_mode"] = explicit_data.get("color_match_mode", "any")
        intent.uncertain = [v for v in intent.uncertain if v != "unresolved_color"]
    # Explicit API filters own their fields, including conflicting text negation.
    intent.excluded = [SearchFilter(**{k: v for k, v in ex.model_dump(exclude_none=True).items() if k not in explicit_data}) for ex in intent.excluded]
    intent.excluded = [ex for ex in intent.excluded if ex.model_dump(exclude_none=True)]
    try:
        intent.required = SearchFilter(**data)
    except ValueError:
        intent.uncertain.append("contradictory_constraints")
        return intent
    intent.preferred = analyze_query(" ".join(preferred_parts), typo_correction_enabled=False).filters
    preferred_materials = materials(" ".join(preferred_parts))
    if preferred_materials:
        intent.preferred.material = ", ".join(preferred_materials)
    return intent
