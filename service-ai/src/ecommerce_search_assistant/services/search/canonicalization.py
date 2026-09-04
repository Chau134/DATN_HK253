from __future__ import annotations

from collections.abc import Iterable

from ecommerce_search_assistant.services.search.aliases import (
    BRAND_ALIASES,
    COLOR_ALIASES,
    GENDER_ALIASES,
    MATERIAL_ALIASES,
    SIZE_ALIASES,
    USE_CASE_ALIASES,
)
from ecommerce_search_assistant.services.search.category_taxonomy import (
    canonicalize_category_values,
)
from ecommerce_search_assistant.services.search.normalization import normalize_metadata_text

METADATA_SCHEMA_VERSION = 7
CANONICALIZER_VERSION = "2026-08-30.1"


def canonicalize_category_keys(values: Iterable[str | None]) -> list[str]:
    return canonicalize_category_values(values)


def canonicalize_brand_key(value: str | None) -> str | None:
    normalized = normalize_metadata_text(value)
    return BRAND_ALIASES.get(normalized, normalized or None)


# Single-word color-family tokens. A compound catalog value like "Hồng pastel",
# "dusty pink" or "pink marl" fragments into many distinct shades at index time;
# scanning its tokens for a known family collapses every shade to one key so a
# plain "màu hồng" query matches all of them.
_COLOR_FAMILY_TOKENS = {
    alias: canonical
    for alias, canonical in COLOR_ALIASES.items()
    if " " not in alias
}

# These tokens are safe only for catalog metadata. Their accent-stripped forms
# collide with ordinary Vietnamese query words (for example `do`, `cam`,
# `tim`), so they intentionally do not belong to the query alias registry.
_CATALOG_ONLY_COLOR_FAMILIES = {
    "aubergine": "purple",
    "cac sac tim": "purple",
    "lilac": "purple",
    "tim": "purple",
    "burgundy": "red",
    "cac sac do": "red",
    "do": "red",
    "golden": "yellow",
    "vang": "yellow",
    "cam": "orange",
    "multicoloured": "multicolor",
    "multicolored": "multicolor",
    "da mau": "multicolor",
}


def resolve_color_family(value: str | None) -> str | None:
    """Resolve a raw color value to its canonical family, or None if unknown."""
    normalized = normalize_metadata_text(value)
    if not normalized:
        return None
    exact = COLOR_ALIASES.get(normalized)
    if exact:
        return exact
    for token in normalized.split():
        family = _COLOR_FAMILY_TOKENS.get(token)
        if family:
            return family
    return None


def color_families(values: Iterable[str | None]) -> set[str]:
    """Resolve every raw value to its canonical family, dropping unknowns."""
    return {family for value in values if (family := resolve_color_family(value))}


def is_exact_color_shade(value: str | None, family: str) -> bool:
    """True when a raw color value IS the plain family (e.g. "Pink"/"Hồng" for
    the pink family), as opposed to a variant shade ("Hồng pastel", "dusty pink").
    Used to rank an exact color match above its shade variants."""
    normalized = normalize_metadata_text(value)
    if not normalized:
        return False
    return COLOR_ALIASES.get(normalized) == family


def canonicalize_color_keys(values: Iterable[str | None]) -> list[str]:
    keys: list[str] = []
    for value in values:
        normalized = normalize_metadata_text(value)
        if not normalized:
            continue
        # Prefer a full-phrase alias ("xanh da troi" -> light blue) before falling
        # back to a family-token scan, then keep the raw value for exact-shade
        # ranking when no family is recognised.
        exact = COLOR_ALIASES.get(normalized)
        if exact:
            keys.append(exact)
            continue
        family_matches = [
            _COLOR_FAMILY_TOKENS[token]
            for token in normalized.split()
            if token in _COLOR_FAMILY_TOKENS
        ]
        if family_matches:
            keys.extend(family_matches)
        else:
            keys.append(normalized)
    return _dedupe(keys)


def catalog_color_keys(values: Iterable[str | None]) -> list[str]:
    """Return catalog keys and mark products spanning multiple color families."""

    raw_values = list(values)
    keys = canonicalize_color_keys(raw_values)
    for value in raw_values:
        normalized = normalize_metadata_text(value)
        if not normalized:
            continue
        for phrase, family in _CATALOG_ONLY_COLOR_FAMILIES.items():
            if _contains_phrase(normalized, phrase):
                keys.append(family)
    keys = _dedupe(keys)
    distinct_families = {
        key
        for key in keys
        if key not in {"multicolor", "navy", "light blue"}
    }
    if "navy" in keys or "light blue" in keys:
        distinct_families.add("blue")
    if len(distinct_families) >= 2 and "multicolor" not in keys:
        keys.append("multicolor")
    return keys


def catalog_product_color_keys(
    base_colour: str | None,
    base_colour_vi: str | None,
) -> list[str]:
    """Canonicalize the authoritative catalog color, with locale as fallback.

    The translated label may describe a nearby shade rather than the exact
    catalog color (for example White translated as Trắng ngà). Combining both
    labels would incorrectly make that product match both white and cream.
    """

    primary = base_colour if normalize_metadata_text(base_colour) else base_colour_vi
    return catalog_color_keys([primary])


def color_filter_keys(values: Iterable[str | None]) -> list[str]:
    """Expand a broad blue request to its accepted catalog shades."""

    keys = canonicalize_color_keys(values)
    expanded: list[str] = []
    for key in keys:
        expanded.extend(("blue", "navy", "light blue") if key == "blue" else (key,))
    return _dedupe(expanded)


def canonicalize_material_keys(values: Iterable[str | None]) -> list[str]:
    keys: list[str] = []
    atomic_materials = set(MATERIAL_ALIASES.values()) | {
        "acrylic",
        "cashmere",
        "elastane",
        "linen",
        "nylon",
        "polyamide",
        "silk",
        "viscose",
    }
    aliases = sorted(MATERIAL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for value in values:
        normalized = normalize_metadata_text(value)
        if not normalized:
            continue
        direct = MATERIAL_ALIASES.get(normalized)
        if direct:
            keys.append(direct)
            continue
        matches: list[tuple[int, str]] = []
        for alias, canonical in aliases:
            if _contains_phrase(normalized, alias):
                matches.append((normalized.find(alias), canonical))
        for material in atomic_materials:
            if _contains_phrase(normalized, material):
                matches.append((normalized.find(material), material))
        if _contains_phrase(normalized, "sheep leather") or _contains_phrase(normalized, "sheepskin"):
            matches.append((normalized.find("sheep"), "leather"))
            matches.append((normalized.find("sheep"), "sheep-leather"))
        if _contains_phrase(normalized, "long cuu"):
            matches.append((normalized.find("long cuu"), "wool"))
        keys.extend(key for _, key in sorted(matches, key=lambda item: item[0]))
        # Preserve a simple unknown material, but never use an entire percentage
        # composition as its only canonical key.
        if not any(char.isdigit() for char in normalized) and not any(
            _contains_phrase(normalized, material) for material in atomic_materials
        ):
            keys.append(normalized)
    return _dedupe(keys)


def canonicalize_use_case_keys(values: Iterable[str | None]) -> list[str]:
    """Canonicalize catalog usage/season phrases into stable ranking keys."""

    keys: list[str] = []
    aliases = sorted(USE_CASE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for value in values:
        normalized = normalize_metadata_text(value)
        if not normalized:
            continue
        direct = USE_CASE_ALIASES.get(normalized)
        if direct:
            keys.append(direct)
            continue
        keys.extend(
            canonical
            for alias, canonical in aliases
            if _contains_phrase(normalized, alias)
        )
    return _dedupe(keys)


def canonicalize_size_keys(values: Iterable[str | None]) -> list[str]:
    keys: list[str] = []
    for value in values:
        normalized = normalize_metadata_text(value)
        if not normalized:
            continue
        normalized = SIZE_ALIASES.get(normalized, normalized.replace(" ", "-"))
        keys.append(normalized)
    return _dedupe(keys)


def canonicalize_gender_key(value: str | None) -> str | None:
    normalized = normalize_metadata_text(value)
    if not normalized:
        return None
    canonical = GENDER_ALIASES.get(normalized, normalized)
    return canonical if canonical in {"men", "women", "unisex"} else None


def audience_keys_for_gender(value: str | None) -> list[str]:
    canonical = canonicalize_gender_key(value)
    if canonical == "unisex":
        return ["unisex", "men", "women"]
    return [canonical] if canonical else []


def _canonicalize_values(values: Iterable[str | None], aliases: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for value in values:
        normalized = normalize_metadata_text(value)
        if normalized:
            keys.append(aliases.get(normalized, normalized))
    return _dedupe(keys)


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _contains_phrase(text: str, phrase: str) -> bool:
    padded = f" {text} "
    return f" {phrase} " in padded
