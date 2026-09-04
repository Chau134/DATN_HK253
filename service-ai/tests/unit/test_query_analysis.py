import pytest

from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.canonicalization import (
    catalog_color_keys,
    color_filter_keys,
)
from ecommerce_search_assistant.services.search.filtering import (
    CatalogMetadata,
    analyze_query,
    detect_catalog_feasibility_rejection,
    detect_out_of_catalog_domain,
    explicit_query_filters,
    merge_missing_filters,
    sanitize_llm_attribute_filters,
    normalize_query_text,
    validate_metadata,
)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Tôi cần thuốc kháng sinh điều trị viêm phổi", "medical"),
        ("Áo hai dây màu nâu voan thêu cổ v sâu thuộc danh mục nào?", None),
        ("Tôi cần áo thun màu nâu thuốc lá cho nữ", None),
    ],
)
def test_out_of_catalog_domain_does_not_confuse_fashion_homographs(
    query: str,
    expected: str | None,
) -> None:
    assert detect_out_of_catalog_domain(query) == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("giay truot tuyet mau bac cho mua he", "negative_ood"),
        ("vay cuoi dinh kim cuong chong nuoc", "negative_impossible"),
        ("ao so mi kim loai chong dan", "negative_impossible"),
        ("ao khoac chong nuoc", None),
        ("ao chong nang", None),
        ("dam dinh da", None),
    ],
)
def test_catalog_feasibility_rejection_is_high_precision(
    query: str,
    expected: str | None,
) -> None:
    assert detect_catalog_feasibility_rejection(query, CatalogMetadata()) == expected


def test_catalog_feasibility_allows_phrase_when_inventory_supports_it() -> None:
    catalog = CatalogMetadata(normalized_titles=frozenset({"vay cuoi dinh kim cuong"}))

    assert detect_catalog_feasibility_rejection("vay cuoi dinh kim cuong", catalog) is None


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "tìm jumpsuit giống ảnh nhưng màu xanh dương",
            SearchFilter(category="jumpsuit", colors=["blue"]),
        ),
        (
            "tìm áo thun giống ảnh nhưng màu đa màu",
            SearchFilter(category="tshirt", colors=["multicolor"]),
        ),
        (
            "tìm blouse giống ảnh nhưng chất liệu viscose",
            SearchFilter(category="blouse", material="viscose"),
        ),
        (
            "tìm áo gile giống ảnh nhưng chất liệu elastane",
            SearchFilter(category="vest", material="elastane"),
        ),
    ],
)
def test_structured_hybrid_literals_become_explicit_filters(
    query: str,
    expected: SearchFilter,
) -> None:
    assert explicit_query_filters(analyze_query(query)) == expected


def test_llm_cannot_invent_color_or_material_absent_from_query() -> None:
    sanitized = sanitize_llm_attribute_filters(
        SearchFilter(colors=["red"], material="leather", gender="women"),
        SearchFilter(category="tshirt", colors=["multicolor"]),
    )

    assert sanitized == SearchFilter(colors=["multicolor"], gender="women")


def test_specific_use_is_canonicalized_for_hybrid_ranking() -> None:
    assert analyze_query("tìm áo giống ảnh để thu đông").filters.use_cases == [
        "winter"
    ]


def test_multicolor_alias_survives_legacy_catalog_validation() -> None:
    analysis = analyze_query(
        "tìm áo thun giống ảnh nhưng màu đa màu",
        CatalogMetadata(colors=frozenset({"da mau"})),
    )

    assert analysis.filters.colors == ["multicolor"]
    assert "invalid_color" not in analysis.warnings


def test_color_filter_expands_broad_blue_but_keeps_navy_specific() -> None:
    assert color_filter_keys(["blue"]) == ["blue", "navy", "light blue"]
    assert color_filter_keys(["navy"]) == ["navy"]


def test_catalog_marks_multiple_color_families_as_multicolor() -> None:
    assert catalog_color_keys(["green", "blue"]) == [
        "green",
        "blue",
        "multicolor",
    ]


def test_normalize_query_text_standardizes_separators() -> None:
    assert normalize_query_text("ao-hoodie   den/ trang") == "ao hoodie den trang"


def test_query_analysis_classifies_standalone_small_talk_without_treating_it_as_search() -> None:
    assert analyze_query("hello").intent == "small_talk"
    assert analyze_query("cảm ơn bạn").intent == "small_talk"
    assert analyze_query("hello, tìm áo hoodie đen").intent == "search_product"


def test_query_analysis_extracts_metadata_and_semantic_constraints() -> None:
    analysis = analyze_query("hodie adiads den mac di chay form rong duoi 700k")

    assert analysis.corrected_query == "hoodie adidas den mac di chay form rong duoi 700k"
    assert analysis.filters.category == "hoodie"
    assert analysis.filters.brand == "adidas"
    assert analysis.filters.colors == ["black"]
    assert analysis.filters.max_price == 700000.0
    assert "running" in analysis.semantic_constraints
    assert "oversized" in analysis.semantic_constraints
    assert analysis.soft_constraints == analysis.semantic_constraints
    assert analysis.semantic_query == "running oversized"
    assert analysis.confidences["category"] == 0.94
    assert analysis.category_match_type == "typo"
    assert analysis.confidences["brand"] == 0.99


def test_semantic_query_does_not_repeat_hard_filters_when_soft_constraints_exist() -> None:
    analysis = analyze_query("ao hoodie adidas den mac di chay")

    assert analysis.filters.category == "hoodie"
    assert analysis.filters.brand == "adidas"
    assert analysis.filters.colors == ["black"]
    assert analysis.semantic_query == "running"


def test_query_analysis_parses_around_price_and_premium_segment() -> None:
    analysis = analyze_query("giay chay premium tam 2tr")

    assert analysis.filters.category == "running shoes"
    assert analysis.filters.min_price == 1600000.0
    assert analysis.filters.max_price == 2400000.0
    assert "premium" in analysis.semantic_constraints


def test_query_analysis_keeps_soft_category_conflict() -> None:
    analysis = analyze_query("ao khoac hoodie den")

    assert analysis.filters.category == "jacket"
    assert "hoodie" in analysis.candidate_categories
    assert "jacket" in analysis.candidate_categories
    assert "hoodie style" in analysis.semantic_constraints
    assert "ambiguous_category" in analysis.warnings
    assert analysis.should_call_llm is True


def test_query_analysis_uses_standalone_price_amount_with_unit() -> None:
    analysis = analyze_query("giay chay 2tr")

    assert analysis.filters.min_price == 1600000.0
    assert analysis.filters.max_price == 2400000.0
    assert "around" in analysis.semantic_constraints


def test_query_analysis_cleans_filler_remaining_text() -> None:
    analysis = analyze_query("shop oi tim giup minh ao hoodie den voi nhe")

    assert analysis.remaining_text == ""
    assert analysis.filters.category == "hoodie"
    assert analysis.filters.colors == ["black"]


def test_query_analysis_extracts_quoted_catalog_title() -> None:
    analysis = analyze_query('Hãy tìm và giới thiệu sản phẩm "Áo kiểu len cổ polo cam".')

    assert analysis.catalog_title_query == "ao kieu len co polo cam"


def test_long_color_phrase_does_not_leak_into_material() -> None:
    analysis = analyze_query("áo sơ mi xanh da trời")

    assert analysis.filters.colors == ["light blue", "blue"]
    assert analysis.filters.material is None


def test_dark_indigo_vietnamese_shade_is_canonicalized_deterministically() -> None:
    analysis = analyze_query("váy màu chàm đậm chất liệu elastane")

    assert analysis.filters.colors == ["dark indigo"]
    assert analysis.metadata["match_sources"]["color"] == "dictionary"


def test_product_head_noun_wins_over_accessory_phrase() -> None:
    analysis = analyze_query("jumpsuit nữ kèm thắt lưng")

    assert analysis.filters.category == "jumpsuit"


@pytest.mark.parametrize(
    "query",
    [
        "tìm kiểu giống vậy",
        "tìm sản phẩm như vậy",
    ],
)
def test_vay_context_reference_is_not_misread_as_dress(query: str) -> None:
    analysis = analyze_query(query)

    assert analysis.filters.category is None
    assert analysis.category_evidence is None
    assert analysis.candidate_categories == []
    assert explicit_query_filters(analysis) is None


def test_real_vay_category_survives_next_to_context_reference() -> None:
    analysis = analyze_query("tìm váy giống vậy")

    assert analysis.filters.category == "dress"
    assert analysis.category_evidence == "vay"
    assert analysis.candidate_categories == ["dress"]
    assert explicit_query_filters(analysis) == SearchFilter(category="dress")


def test_combined_catalog_category_label_is_one_unambiguous_category() -> None:
    analysis = analyze_query("blazer & áo vest cho nữ")

    assert analysis.filters == SearchFilter(category="blazer", gender="women")
    assert analysis.category_evidence == "blazer ao vest"
    assert analysis.candidate_categories == ["blazer"]
    assert "ambiguous_category" not in analysis.warnings
    assert explicit_query_filters(analysis) == SearchFilter(category="blazer")


def test_text_search_miss_regressions_use_controlled_category_corrections() -> None:
    cases = (
        ("chn váy xòe", "chan vay xoe", "skirt", "typo", "chan vay"),
        (
            "áo blose sọc cổ vest hồng",
            "ao blouse soc co vest hong",
            "blouse",
            "typo",
            "ao blouse",
        ),
        ("đầm jumpuit caro", "dam jumpsuit caro", "jumpsuit", "typo", "dam jumpsuit"),
        (
            "áo crop tay phồng vải popin",
            "ao crop tay phong vai poplin",
            "blouse",
            "alias",
            "ao crop",
        ),
        ("áo gi lê vai nâng", "ao gi le vai nang", "vest", "alias", "ao gi le"),
        (
            "váy qun dài kẻ sọc",
            "vay quan dai ke soc",
            "skort",
            "typo",
            "vay quan",
        ),
    )

    for query, corrected, category, match_type, evidence in cases:
        analysis = analyze_query(query)

        assert analysis.corrected_query == corrected
        assert analysis.filters.category == category
        assert analysis.category_key == category
        assert analysis.category_confidence >= 0.9
        assert analysis.category_match_type == match_type
        assert analysis.category_evidence == evidence
        assert analysis.candidate_categories == [category]

    blouse = analyze_query("áo blose sọc cổ vest hồng")
    assert "vest" not in blouse.candidate_categories
    assert "soc" in blouse.corrected_query
    assert "hong" in blouse.corrected_query

    crop = analyze_query("áo crop tay phồng vải popin")
    assert crop.filters.material == "poplin"
    assert crop.metadata["match_sources"]["material"] == "dictionary"


def test_typo_correction_can_be_rolled_back_independently() -> None:
    analysis = analyze_query("chn váy xòe", typo_correction_enabled=False)

    assert analysis.corrected_query == "chn vay xoe"
    assert analysis.filters.category == "dress"
    assert not any(warning.startswith("spell_corrected:") for warning in analysis.warnings)


def test_merge_missing_filters_keeps_rule_based_values() -> None:
    merged = merge_missing_filters(
        SearchFilter(category="hoodie", colors=["black"], max_price=300000.0),
        SearchFilter(category="jacket", colors=["white"], brand="zara"),
    )

    assert merged == SearchFilter(
        category="hoodie",
        colors=["black"],
        brand="zara",
        max_price=300000.0,
    )


def test_validate_metadata_drops_invalid_filter_values() -> None:
    filters, warnings = validate_metadata(
        SearchFilter(
            colors=["black", "not-a-color"],
            gender="robot",
            material="carbon",
            sizes=["M", "bad-size"],
        )
    )

    assert filters.colors == ["black"]
    assert filters.gender is None
    assert filters.material is None
    assert filters.sizes == ["M"]
    assert warnings == ["invalid_color", "invalid_gender", "invalid_material", "invalid_size"]


def test_validate_metadata_uses_catalog_values_when_available() -> None:
    catalog = CatalogMetadata(
        categories=frozenset({"hoodies"}),
        brands=frozenset({"zara"}),
        colors=frozenset({"black"}),
        genders=frozenset({"women"}),
        sizes=frozenset({"m"}),
        min_price=100000.0,
        max_price=900000.0,
    )

    filters, warnings = validate_metadata(
        SearchFilter(
            category="hoodie",
            brand="adidas",
            colors=["black", "white"],
            gender="men",
            sizes=["M", "L"],
            min_price=1000000.0,
        ),
        catalog,
    )

    assert filters.category == "hoodie"
    assert filters.brand is None
    assert filters.colors == ["black"]
    assert filters.gender is None
    assert filters.sizes == ["M"]
    assert filters.min_price is None
    assert warnings == [
        "invalid_brand",
        "invalid_color",
        "invalid_gender",
        "invalid_size",
        "price_outside_catalog",
    ]


def test_validate_metadata_drops_price_bound_outside_catalog() -> None:
    catalog = CatalogMetadata(min_price=100000.0, max_price=900000.0)

    filters, warnings = validate_metadata(SearchFilter(max_price=50000.0), catalog)

    assert filters.max_price is None
    assert warnings == ["price_outside_catalog"]


def test_catalog_validation_recognizes_unsupported_canada_goose_brand() -> None:
    analysis = analyze_query(
        "áo lông cừu Canada Goose",
        CatalogMetadata(brands=frozenset({"zara"})),
    )

    assert analysis.filters.brand is None
    assert "invalid_brand" in analysis.warnings


def test_floral_pattern_is_not_misclassified_as_an_invalid_color() -> None:
    analysis = analyze_query(
        "áo sơ mi satin hoa nữ",
        CatalogMetadata(
            categories=frozenset({"shirt"}),
            genders=frozenset({"women"}),
            colors=frozenset({"multicoloured"}),
        ),
    )

    assert analysis.filters.colors is None
    assert "invalid_color" not in analysis.warnings
    assert analysis.metadata["pattern"] == ["floral"]
