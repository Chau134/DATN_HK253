from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ecommerce_search_assistant.services.search.normalization import normalize_metadata_text


@dataclass(frozen=True)
class CategoryTaxon:
    canonical_code: str
    query_aliases: tuple[tuple[str, str], ...]
    identity_aliases: tuple[str, ...] = ()

    @property
    def search_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(key for _, key in self.query_aliases))


def _aliases(key: str, *values: str) -> tuple[tuple[str, str], ...]:
    return tuple((value, key) for value in values)


CATEGORY_TAXONOMY: tuple[CategoryTaxon, ...] = (
    CategoryTaxon(
        "shirt",
        _aliases("shirt", "shirt", "shirts"),
        ("Shirts", "Áo sơ mi"),
    ),
    CategoryTaxon(
        "blouse_top",
        _aliases(
            "blouse",
            "blouse",
            "blouses",
            "ao blouse",
            "fashion top",
            "fashion tops",
            "crop top",
            "ao crop",
            "ao crop top",
        ),
        ("Blouses & Fashion Tops", "Áo kiểu"),
    ),
    # Retain the former combined code and labels for already-indexed payloads and
    # callers that have not migrated to the split catalog yet.
    CategoryTaxon(
        "shirt_blouse",
        _aliases("shirt", "shirt", "shirts", "áo sơ mi", "sơ mi công sở", "sơ mi tay dài", "sơ mi tay ngắn")
        + _aliases("blouse", "blouse", "blouses", "áo kiểu"),
        ("Shirts & Blouses", "Áo sơ mi & áo kiểu"),
    ),
    CategoryTaxon(
        "t-shirt",
        _aliases(
            "tshirt",
            "tshirt",
            "tshirts",
            "t-shirt",
            "t-shirts",
            "t shirt",
            "tee",
            "tee shirt",
            "tee-shirt",
            "graphic tee",
            "basic tee",
            "áo tee",
            "áo thun",
            "áo phông",
            "thun",
            "phông",
        ),
        ("T-shirts",),
    ),
    CategoryTaxon(
        "tank_cami",
        _aliases("tank top", "tank", "tank top", "tank tops", "áo ba lỗ", "ba lỗ", "áo sát nách")
        + _aliases("cami", "cami", "cami top", "cami tops", "camisole", "áo hai dây", "hai dây", "áo dây")
        + _aliases("halter", "halter", "halter top", "halter tops", "áo yếm", "cổ yếm"),
        (
            "Tank, Cami & Halter Tops",
            "Áo hai dây, áo sát nách & áo yếm",
            # Legacy catalog labels remain valid while existing vectors are re-indexed.
            "Tank & Cami Tops",
            "Áo hai dây & áo ba lỗ",
        ),
    ),
    CategoryTaxon(
        "bodysuit",
        _aliases("bodysuit", "bodysuit", "bodysuits", "body suit", "áo body"),
        ("Bodysuits",),
    ),
    CategoryTaxon(
        "polo",
        _aliases("polo", "polo", "polo shirt", "polo shirts", "polo tee", "áo polo", "áo cá sấu", "áo cổ bẻ", "áo cổ trụ"),
        ("Polo Shirts",),
    ),
    CategoryTaxon(
        "sweater_cardigan",
        _aliases("sweater", "sweater", "sweaters", "knitwear", "áo knit", "áo dệt kim", "áo len")
        + _aliases("cardigan", "cardigan", "cardigans", "áo cardigan", "cardigan len"),
        (
            "Knitwear & Cardigans",
            "Áo dệt kim",
            # Legacy labels remain valid until existing vector payloads are re-indexed.
            "Áo dệt kim & cardigan",
            "Sweaters & Cardigans",
            "Áo len & cardigan",
        ),
    ),
    CategoryTaxon(
        "hoodie_sweatshirt",
        _aliases("hoodie", "hoodie", "hoodies", "áo hoodie", "áo nỉ có mũ", "áo có mũ")
        + _aliases("sweatshirt", "sweatshirt", "sweatshirts", "áo nỉ", "áo chui đầu", "áo nỉ chui đầu"),
        ("Hoodies & Sweatshirts", "Áo hoodie & áo nỉ"),
    ),
    CategoryTaxon(
        "pants",
        _aliases("trousers", "trouser", "trousers", "slacks", "chinos", "chino")
        + _aliases("pants", "pants", "quần tây", "quần kaki", "quần công sở"),
        ("Trousers", "Quần dài"),
    ),
    CategoryTaxon(
        "jeans",
        _aliases("jeans", "jean", "jeans", "denim pants", "denim jeans", "quần jean", "quần jeans", "quần bò"),
        ("Jeans", "Quần jeans"),
    ),
    CategoryTaxon(
        "shorts",
        _aliases("shorts", "short", "shorts", "bermuda", "quần short", "quần shorts", "quần ngắn"),
        ("Shorts", "Quần short"),
    ),
    CategoryTaxon(
        "skirt",
        _aliases("skirt", "skirt", "skirts", "mini skirt", "midi skirt", "maxi skirt", "chân váy"),
        ("Skirts", "Chân váy"),
    ),
    CategoryTaxon(
        "skort",
        _aliases("skort", "skort", "skorts", "váy quần", "quần váy"),
        ("Skorts", "Váy quần"),
    ),
    CategoryTaxon(
        "leggings",
        _aliases("leggings", "legging", "leggings", "tights", "yoga pants", "quần legging", "quần leggings", "quần ôm"),
        ("Leggings", "Quần legging"),
    ),
    CategoryTaxon(
        "dress",
        _aliases(
            "dress",
            "dress",
            "dresses",
            "maxi dress",
            "midi dress",
            "mini dress",
            "váy",
            "đầm",
            "váy liền",
            "váy liền thân",
            "váy công sở",
        ),
        ("Dresses", "Váy & Đầm"),
    ),
    CategoryTaxon(
        "jumpsuit_romper",
        _aliases(
            "jumpsuit",
            "jumpsuit",
            "jumpsuits",
            "đầm jumpsuit",
            "đồ bay",
            "jumpsuit nữ",
            "áo liền quần",
        )
        + _aliases("romper", "romper", "rompers"),
        ("Jumpsuits & Rompers", "Jumpsuit & áo liền quần"),
    ),
    CategoryTaxon(
        "blazer_vest",
        _aliases("blazer", "blazer", "blazers", "áo blazer", "suit jacket")
        + _aliases(
            "vest",
            "vest",
            "vests",
            "áo vest",
            "áo khoác vest",
            "ghi lê",
            "gi lê",
            "áo gi lê",
            "gile",
            "áo gile",
            "waistcoat",
        ),
        ("Blazers & Vests", "Blazer & áo vest"),
    ),
    CategoryTaxon(
        "jacket",
        _aliases(
            "jacket",
            "jacket",
            "jackets",
            "bomber",
            "windbreaker",
            "parka",
            "áo khoác",
            "áo gió",
            "áo bomber",
            "áo khoác nhẹ",
        ),
        ("Jackets", "Áo khoác"),
    ),
    # Categories supported by the search API but not present in the current seed taxonomy.
    CategoryTaxon(
        "jacket_coat",
        _aliases("jacket", "jacket coat") + _aliases("coat", "coat", "coats"),
        ("Jackets & Coats",),
    ),
    CategoryTaxon(
        "sneakers",
        _aliases("sneakers", "sneaker", "sneakers", "giày sneaker", "giày thể thao"),
    ),
    CategoryTaxon("running_shoes", _aliases("running shoes", "running shoes", "giày chạy")),
    CategoryTaxon("backpack", _aliases("backpack", "backpack", "balo", "balo laptop")),
    CategoryTaxon("boots", _aliases("boots", "boot", "boots", "giày boot")),
    CategoryTaxon("sandals", _aliases("sandals", "sandal", "sandals")),
    CategoryTaxon("heels", _aliases("heels", "heel", "heels", "giày cao gót")),
    CategoryTaxon("watch", _aliases("watch", "watch", "watches", "đồng hồ")),
    CategoryTaxon("handbag", _aliases("handbag", "handbag", "handbags", "túi xách")),
    CategoryTaxon("wallet", _aliases("wallet", "wallet", "wallets", "ví")),
    CategoryTaxon("belt", _aliases("belt", "belt", "belts", "thắt lưng")),
    CategoryTaxon("cap", _aliases("cap", "cap", "caps", "mũ")),
    CategoryTaxon("scarf", _aliases("scarf", "scarf", "scarves", "khăn")),
    CategoryTaxon("sunglasses", _aliases("sunglasses", "sunglasses", "kính râm")),
    CategoryTaxon("sweatpants", _aliases("sweatpants", "sweatpants", "quần jogger")),
)

_CATEGORY_DISPLAY_NAMES_VI: dict[str, str] = {
    "shirt": "Áo sơ mi",
    "blouse_top": "Áo kiểu",
    "shirt_blouse": "Áo sơ mi & áo kiểu",
    "t-shirt": "Áo thun",
    "tank_cami": "Áo hai dây, áo sát nách & áo yếm",
    "bodysuit": "Bodysuit",
    "polo": "Áo polo",
    "sweater_cardigan": "Áo dệt kim & cardigan",
    "hoodie_sweatshirt": "Áo hoodie & áo nỉ",
    "pants": "Quần dài",
    "jeans": "Quần jeans",
    "shorts": "Quần short",
    "skirt": "Chân váy",
    "skort": "Váy quần",
    "leggings": "Quần legging",
    "dress": "Váy & đầm",
    "jumpsuit_romper": "Jumpsuit & áo liền quần",
    "blazer_vest": "Blazer & áo vest",
    "jacket": "Áo khoác",
}


def normalize_category_text(value: str | None) -> str:
    return normalize_metadata_text(value)


def category_display_name_vi(value: str) -> str:
    raw_code = value.strip().casefold()
    normalized = normalize_category_text(value)
    return _CATEGORY_DISPLAY_NAMES_VI.get(
        raw_code,
        _CATEGORY_DISPLAY_NAMES_VI.get(normalized, value.strip()),
    )


def _build_lookups() -> tuple[
    dict[str, tuple[str, ...]],
    dict[str, str],
    dict[str, CategoryTaxon],
]:
    aliases_to_keys: dict[str, tuple[str, ...]] = {}
    query_aliases: dict[str, str] = {}
    codes: dict[str, CategoryTaxon] = {}

    for taxon in CATEGORY_TAXONOMY:
        normalized_code = normalize_category_text(taxon.canonical_code)
        codes[normalized_code] = taxon
        aliases_to_keys[normalized_code] = taxon.search_keys
        query_aliases[normalized_code] = taxon.search_keys[0]

        for alias, key in taxon.query_aliases:
            normalized = normalize_category_text(alias)
            existing = aliases_to_keys.get(normalized)
            if existing is not None and key not in existing:
                raise ValueError(f"conflicting category alias: {alias}")
            aliases_to_keys[normalized] = (key,)
            query_aliases[normalized] = key

        for alias in taxon.identity_aliases:
            normalized = normalize_category_text(alias)
            aliases_to_keys[normalized] = taxon.search_keys
            query_aliases.setdefault(normalized, taxon.search_keys[0])

    return aliases_to_keys, query_aliases, codes


_ALIASES_TO_KEYS, CATEGORY_QUERY_ALIASES, _CODE_TO_TAXON = _build_lookups()

# Conversational category names are query aliases only. They deliberately do
# not change canonical catalog labels or the payload schema.
CATEGORY_QUERY_ALIASES.update(
    {
        normalize_category_text('do lien than'): 'bodysuit',
        normalize_category_text('ao lien than'): 'bodysuit',
    }
)

# "Quần dài" is a browse intent spanning several leaf catalog categories, not
# just the narrower Trousers category. Keep the leaf aliases (quần tây,
# leggings, jeans, ...) precise and expand only this broad Vietnamese phrase.
CATEGORY_QUERY_ALIASES[normalize_category_text("quần dài")] = "long_pants"
_ALIASES_TO_KEYS[normalize_category_text("long_pants")] = ("long_pants",)

for _winter_alias in ("áo mặc mùa đông", "áo mùa đông", "áo mặc trời lạnh"):
    CATEGORY_QUERY_ALIASES[normalize_category_text(_winter_alias)] = "winter_outerwear"
_ALIASES_TO_KEYS[normalize_category_text("winter_outerwear")] = ("winter_outerwear",)

for _office_alias in ("áo mặc đi làm", "áo đi làm", "áo công sở", "áo mặc công sở"):
    CATEGORY_QUERY_ALIASES[normalize_category_text(_office_alias)] = "office_tops"
_ALIASES_TO_KEYS[normalize_category_text("office_tops")] = ("office_tops",)

_CATEGORY_FILTER_EXPANSIONS: dict[str, tuple[str, ...]] = {
    # tank_cami is one catalog category whose older schema-v6 payloads can carry
    # only "tank top"/"cami" even when the title is a halter top. Treat its
    # three leaf query keys as siblings so current queries remain compatible
    # with both old payloads and schema-v7 payloads emitted by the indexer.
    "tank top": ("tank top", "cami", "halter"),
    "cami": ("cami", "tank top", "halter"),
    "halter": ("halter", "tank top", "cami"),
    "long_pants": ("trousers", "pants", "jeans", "leggings", "sweatpants"),
    "winter_outerwear": (
        "jacket",
        "coat",
        "hoodie",
        "sweatshirt",
        "sweater",
        "cardigan",
    ),
    "office_tops": (
        "shirt",
        "blouse",
        "blazer",
        "vest",
        "polo",
        "sweater",
        "cardigan",
    ),
}


def canonicalize_category_values(values: Iterable[str | None]) -> list[str]:
    keys: list[str] = []
    for value in values:
        normalized = normalize_category_text(value)
        if normalized:
            keys.extend(_ALIASES_TO_KEYS.get(normalized, (normalized,)))
    return list(dict.fromkeys(keys))


def category_filter_keys(values: Iterable[str | None]) -> list[str]:
    """Return current keys plus exact payload keys emitted before schema version 3."""
    keys = canonicalize_category_values(values)
    expanded_keys = [
        expanded
        for key in keys
        for expanded in _CATEGORY_FILTER_EXPANSIONS.get(key, (key,))
    ]
    legacy_keys: list[str] = []
    requested = set(expanded_keys)
    for taxon in CATEGORY_TAXONOMY:
        if requested.intersection(taxon.search_keys):
            legacy_keys.extend(
                normalized
                for alias in taxon.identity_aliases
                if (normalized := normalize_category_text(alias))
                and len(_ALIASES_TO_KEYS.get(normalized, ())) > 1
            )
    return list(dict.fromkeys([*expanded_keys, *legacy_keys]))


def category_keys_for_category(
    category_code: str | None,
    category_name: str | None,
    category_name_vi: str | None,
) -> list[str]:
    taxon = _CODE_TO_TAXON.get(normalize_category_text(category_code))
    if taxon is not None:
        return list(taxon.search_keys)
    return canonicalize_category_values((category_name, category_name_vi, category_code))


def canonicalize_category_codes(values: Iterable[str | None]) -> list[str]:
    codes: list[str] = []
    for value in values:
        if not value or not value.strip():
            continue
        taxon = _CODE_TO_TAXON.get(normalize_category_text(value))
        codes.append(taxon.canonical_code if taxon else value.strip().casefold())
    return list(dict.fromkeys(codes))


def category_aliases_for_keys(values: Iterable[str | None]) -> list[str]:
    """Return normalized query aliases for canonical payload category keys."""
    requested = set(canonicalize_category_values(values))
    aliases: list[str] = []
    for taxon in CATEGORY_TAXONOMY:
        if not requested.intersection(taxon.search_keys):
            continue
        aliases.extend(normalize_category_text(alias) for alias, _ in taxon.query_aliases)
    return list(dict.fromkeys(alias for alias in aliases if alias))
