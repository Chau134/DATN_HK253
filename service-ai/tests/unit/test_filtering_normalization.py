from ecommerce_search_assistant.services.search.canonicalization import (
    canonicalize_brand_key,
    canonicalize_color_keys,
)
from ecommerce_search_assistant.services.search.filtering import analyze_query
from ecommerce_search_assistant.services.search.normalization import (
    normalize_alias_key,
    normalize_metadata_text,
    normalize_query_text,
)


def test_query_normalization_preserves_meaningful_price_and_brand_punctuation() -> None:
    assert normalize_query_text("Áo H&M, giá 1,2tr - 1.5tr") == "ao h&m gia 1,2tr 1.5tr"
    assert normalize_query_text("500k-700k") == "500k-700k"


def test_metadata_normalization_handles_diacritics_and_common_mojibake() -> None:
    assert normalize_metadata_text("màu đen") == "mau den"
    assert normalize_metadata_text("mÃ u Ä‘en") == "mau den"
    assert normalize_alias_key("  Áo khoác  ") == "ao khoac"


def test_query_and_payload_values_share_canonical_keys() -> None:
    assert canonicalize_color_keys(["màu đen", "Black"]) == ["black"]
    assert canonicalize_brand_key("H & M") == "h&m"
    assert analyze_query("áo H&M màu đen").filters.brand == "h&m"


def test_vanilla_query_and_catalog_labels_share_one_exact_key() -> None:
    analysis = analyze_query("Tìm Áo thun màu Vani")

    assert analysis.filters.colors == ["vanilla"]
    assert canonicalize_color_keys(["Vanilla", "Vani"]) == ["vanilla"]
