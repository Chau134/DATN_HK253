from ecommerce_search_assistant.services.search.canonicalization import (
    audience_keys_for_gender,
    canonicalize_brand_key,
    catalog_color_keys,
    canonicalize_category_keys,
    canonicalize_color_keys,
    catalog_product_color_keys,
    canonicalize_material_keys,
    canonicalize_size_keys,
    is_exact_color_shade,
    resolve_color_family,
)


def test_index_and_query_category_aliases_share_keys() -> None:
    indexed = canonicalize_category_keys(["Jackets & Coats", "Áo khoác"])

    assert indexed == ["jacket", "coat"]
    assert canonicalize_category_keys(["jacket"]) == ["jacket"]


def test_color_material_brand_and_size_are_canonicalized_by_domain() -> None:
    assert canonicalize_color_keys(["Black", "màu đen"]) == ["black"]
    assert canonicalize_material_keys(["Da", "Leather"]) == ["leather"]
    assert canonicalize_brand_key("H & M") == "h&m"
    assert canonicalize_size_keys(["M", "EU M", "One Size"]) == ["m", "eu-m", "one-size"]


def test_unisex_product_is_searchable_for_each_supported_audience() -> None:
    assert audience_keys_for_gender("Unisex Adult") == ["unisex", "men", "women"]


def test_material_composition_is_split_into_atomic_search_keys() -> None:
    assert canonicalize_material_keys(["42% acrylic 30% polyamide 5% wool"]) == [
        "acrylic",
        "polyamide",
        "wool",
    ]
    assert canonicalize_material_keys(["100% sheep leather"]) == ["leather", "sheep-leather"]
    assert canonicalize_material_keys(["58% Ramie, 42% Lyocell"]) == ["ramie", "lyocell"]
    assert canonicalize_material_keys(["87% Lyocell, 13% Gai dầu"]) == ["lyocell", "hemp"]


def test_color_shade_variants_collapse_to_one_family_key() -> None:
    # Every pink shade in the catalog must index under the single "pink" family so a
    # plain "màu hồng" query matches all of them instead of one fragment.
    assert canonicalize_color_keys(["Pink"]) == ["pink"]
    assert canonicalize_color_keys(["Hồng pastel"]) == ["pink"]
    assert canonicalize_color_keys(["dusty pink"]) == ["pink"]
    assert canonicalize_color_keys(["Hồng phấn nhạt"]) == ["pink"]
    assert canonicalize_color_keys(["pink marl"]) == ["pink"]


def test_full_phrase_blue_alias_wins_over_bare_family_token() -> None:
    # "xanh da troi" must resolve to light blue, not the bare "xanh" -> blue family.
    assert canonicalize_color_keys(["xanh da troi"]) == ["light blue"]
    assert canonicalize_color_keys(["navy blue"]) == ["navy"]


def test_ivory_shades_are_not_indexed_as_plain_white() -> None:
    assert catalog_color_keys(["Ecru", "Trắng ngà"]) == ["cream"]
    assert catalog_color_keys(["Ivory", "Trắng ngà"]) == ["cream"]
    assert catalog_color_keys(["White", "Trắng"]) == ["white"]
    assert catalog_product_color_keys("Ecru", "Trắng ngà") == ["cream"]
    assert catalog_product_color_keys("White", "Trắng ngà") == ["white"]
    assert catalog_product_color_keys("Ecru / Yellow", "Trắng ngà / Vàng") == [
        "cream",
        "yellow",
        "multicolor",
    ]


def test_unknown_color_is_preserved_as_its_own_key() -> None:
    assert canonicalize_color_keys(["chartreuse"]) == ["chartreuse"]


def test_catalog_only_color_families_bridge_legacy_shades_to_query_keys() -> None:
    assert "purple" in catalog_color_keys(["Aubergine", "Tím cà"])
    assert "yellow" in catalog_color_keys(["Golden", "Vàng ánh kim"])
    assert "multicolor" in catalog_color_keys(["Multicoloured", "Đa màu"])


def test_resolve_color_family_matches_shades_and_ignores_unknown() -> None:
    assert resolve_color_family("Hồng pastel") == "pink"
    assert resolve_color_family("dusty pink") == "pink"
    assert resolve_color_family("chartreuse") is None


def test_is_exact_color_shade_only_true_for_plain_family() -> None:
    assert is_exact_color_shade("Pink", "pink") is True
    assert is_exact_color_shade("Hồng", "pink") is True
    # A variant shade shares the family but is NOT the plain color.
    assert is_exact_color_shade("Hồng pastel", "pink") is False
    assert is_exact_color_shade("dusty pink", "pink") is False
