import pytest

from ecommerce_search_assistant.services.search.canonicalization import canonicalize_category_keys
from ecommerce_search_assistant.services.search.category_taxonomy import (
    CATEGORY_TAXONOMY,
    canonicalize_category_codes,
    category_filter_keys,
    category_keys_for_category,
)
from ecommerce_search_assistant.services.search.filtering import analyze_query


CATALOG_CASES = (
    ("shirt", "Shirts", "Áo sơ mi", ("shirt",), "shirt"),
    ("blouse_top", "Blouses & Fashion Tops", "Áo kiểu", ("blouse",), "blouse"),
    ("shirt_blouse", "Shirts & Blouses", "Áo sơ mi & áo kiểu", ("shirt", "blouse"), "áo sơ mi"),
    ("t-shirt", "T-shirts", "Áo thun", ("tshirt",), "áo thun"),
    (
        "tank_cami",
        "Tank, Cami & Halter Tops",
        "Áo hai dây, áo sát nách & áo yếm",
        ("tank top", "cami", "halter"),
        "áo yếm",
    ),
    ("bodysuit", "Bodysuits", "Bodysuit", ("bodysuit",), "bodysuit"),
    ("polo", "Polo Shirts", "Áo polo", ("polo",), "áo polo"),
    (
        "sweater_cardigan",
        "Knitwear & Cardigans",
        "Áo dệt kim",
        ("sweater", "cardigan"),
        "áo dệt kim",
    ),
    (
        "hoodie_sweatshirt",
        "Hoodies & Sweatshirts",
        "Áo hoodie & áo nỉ",
        ("hoodie", "sweatshirt"),
        "áo hoodie",
    ),
    ("pants", "Trousers", "Quần dài", ("trousers", "pants"), "quần tây"),
    ("jeans", "Jeans", "Quần jeans", ("jeans",), "quần jeans"),
    ("shorts", "Shorts", "Quần short", ("shorts",), "quần short"),
    ("skirt", "Skirts", "Chân váy", ("skirt",), "chân váy"),
    ("skort", "Skorts", "Váy quần", ("skort",), "váy quần"),
    ("leggings", "Leggings", "Quần legging", ("leggings",), "quần legging"),
    ("dress", "Dresses", "Váy & Đầm", ("dress",), "váy"),
    (
        "jumpsuit_romper",
        "Jumpsuits & Rompers",
        "Jumpsuit & áo liền quần",
        ("jumpsuit", "romper"),
        "jumpsuit",
    ),
    ("blazer_vest", "Blazers & Vests", "Blazer & áo vest", ("blazer", "vest"), "blazer"),
    ("jacket", "Jackets", "Áo khoác", ("jacket",), "áo khoác"),
)


@pytest.mark.parametrize(("code", "name", "name_vi", "expected_keys", "query"), CATALOG_CASES)
def test_seed_catalog_categories_share_keys_with_representative_queries(
    code: str,
    name: str,
    name_vi: str,
    expected_keys: tuple[str, ...],
    query: str,
) -> None:
    indexed_keys = category_keys_for_category(code, name, name_vi)
    query_category = analyze_query(query).filters.category
    query_keys = canonicalize_category_keys([query_category])

    assert indexed_keys == list(expected_keys)
    assert query_category is not None
    assert set(query_keys) & set(indexed_keys)


def test_every_registered_query_alias_can_be_used_as_a_hard_filter() -> None:
    for taxon in CATEGORY_TAXONOMY:
        indexed_keys = set(category_keys_for_category(taxon.canonical_code, None, None))
        for alias, expected_key in taxon.query_aliases:
            analysis = analyze_query(alias)
            query_keys = set(canonicalize_category_keys([analysis.filters.category]))

            assert analysis.filters.category == expected_key, (taxon.canonical_code, alias)
            assert query_keys & indexed_keys, (taxon.canonical_code, alias)


def test_category_code_is_the_primary_identity_and_names_are_legacy_fallbacks() -> None:
    assert category_keys_for_category("shirt", "Shirts & Blouses", "Áo sơ mi & áo kiểu") == [
        "shirt"
    ]
    assert category_keys_for_category(
        "blouse_top", "Shirts & Blouses", "Áo sơ mi & áo kiểu"
    ) == ["blouse"]
    assert category_keys_for_category("shirt_blouse", "Jackets", "Áo khoác") == ["shirt", "blouse"]
    assert category_keys_for_category(None, "Shirts & Blouses", "Áo sơ mi & áo kiểu") == [
        "shirt",
        "blouse",
    ]
    assert canonicalize_category_codes(["SHIRT_BLOUSE", "shirt_blouse"]) == ["shirt_blouse"]


def test_gilet_variants_share_the_vest_key() -> None:
    for query in ("áo gi lê", "gi lê", "gile", "áo gile", "ghi lê"):
        assert analyze_query(query).filters.category == "vest"


def test_legacy_tank_cami_labels_keep_all_current_filter_keys() -> None:
    assert category_keys_for_category(
        None, "Tank & Cami Tops", "Áo hai dây & áo ba lỗ"
    ) == ["tank top", "cami", "halter"]


@pytest.mark.parametrize("query_key", ("tank top", "cami", "halter"))
def test_tank_cami_query_keys_match_legacy_and_current_payloads(query_key: str) -> None:
    assert {"tank top", "cami", "halter"} <= set(category_filter_keys([query_key]))


@pytest.mark.parametrize(
    "name_vi", ("Áo dệt kim", "Áo dệt kim & cardigan", "Áo len & cardigan")
)
def test_current_and_legacy_knitwear_labels_keep_filter_keys(name_vi: str) -> None:
    assert category_keys_for_category(None, None, name_vi) == [
        "sweater",
        "cardigan",
    ]


def test_broad_long_pants_query_expands_to_long_bottom_categories_only() -> None:
    analysis = analyze_query("quần dài màu đen")
    keys = set(category_filter_keys([analysis.filters.category]))

    assert analysis.filters.category == "long_pants"
    assert {"trousers", "pants", "jeans", "leggings", "sweatpants"} <= keys
    assert keys.isdisjoint({"shorts", "skort", "skirt"})


def test_specific_leggings_query_does_not_expand_to_other_pants() -> None:
    analysis = analyze_query("quần legging cạp cao đen")

    assert analysis.filters.category == "leggings"
    assert category_filter_keys([analysis.filters.category]) == ["leggings"]


def test_winter_top_query_expands_to_warm_outerwear_categories() -> None:
    analysis = analyze_query("áo mặc mùa đông")
    keys = set(category_filter_keys([analysis.filters.category]))

    assert analysis.filters.category == "winter_outerwear"
    assert {"jacket", "coat", "hoodie", "sweatshirt", "sweater", "cardigan"} <= keys
    assert keys.isdisjoint({"shirt", "blouse", "tshirt", "bodysuit", "dress"})
    assert "winter" in analysis.semantic_constraints


def test_specific_winter_sweater_query_keeps_leaf_category() -> None:
    analysis = analyze_query("áo len mặc mùa đông")
    keys = set(category_filter_keys([analysis.filters.category]))

    assert analysis.filters.category == "sweater"
    assert "sweater" in keys
    assert keys.isdisjoint({"jacket", "coat", "hoodie", "sweatshirt"})


def test_generic_work_top_query_expands_to_office_categories() -> None:
    analysis = analyze_query("Tôi muốn áo mặc đi làm")
    keys = set(category_filter_keys([analysis.filters.category]))

    assert analysis.filters.category == "office_tops"
    assert {"shirt", "blouse", "blazer", "vest", "polo", "sweater", "cardigan"} <= keys
    assert keys.isdisjoint({"tshirt", "tank top", "cami", "bodysuit", "hoodie", "dress"})
    assert "work" in analysis.semantic_constraints


def test_specific_work_tshirt_query_keeps_tshirt_category() -> None:
    analysis = analyze_query("áo thun mặc đi làm")

    assert analysis.filters.category == "tshirt"
    assert category_filter_keys([analysis.filters.category]) == ["tshirt"]
