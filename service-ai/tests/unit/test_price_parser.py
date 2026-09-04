import pytest

from ecommerce_search_assistant.services.search.filtering import analyze_query
from ecommerce_search_assistant.services.search.parsers.price import (
    extract_price,
    parse_price_amount,
)


@pytest.mark.parametrize(
    ("query", "expected_min", "expected_max"),
    (
        ("duoi 300k", None, 300000.0),
        ("300.000d tro xuong", None, 300000.0),
        ("tu 500k den 1tr", 500000.0, 1000000.0),
        ("500k-700k", 500000.0, 700000.0),
        ("khong qua 1,2 trieu", None, 1200000.0),
        ("tren 300.000 vnd", 300000.0, None),
        ("UNDER 50", None, 50000.0),
    ),
)
def test_extract_price_supports_vietnamese_and_english_formats(
    query: str,
    expected_min: float | None,
    expected_max: float | None,
) -> None:
    result = extract_price(query)

    assert result.min_price == expected_min
    assert result.max_price == expected_max


def test_mixed_million_and_around_price_are_normalized() -> None:
    result = extract_price("tam 1m5")

    assert parse_price_amount("1m5") == 1500000.0
    assert result.min_price == 1200000.0
    assert result.max_price == 1800000.0


def test_price_range_connector_is_not_extracted_as_black_color() -> None:
    analysis = analyze_query("tu 500k den 1tr")

    assert analysis.filters.colors is None
    assert analysis.filters.min_price == 500000.0
    assert analysis.filters.max_price == 1000000.0


@pytest.mark.parametrize(
    ("literal", "expected_min", "expected_max"),
    (
        ("dưới 200k", None, 200000.0),
        ("200k đến 500k", 200000.0, 500000.0),
        ("500k đến 1 triệu", 500000.0, 1000000.0),
        ("1-2 triệu", 1000000.0, 2000000.0),
        ("trên 2 triệu", 2000000.0, None),
    ),
)
def test_hybrid_price_literals_are_preserved_with_product_constraints(
    literal: str,
    expected_min: float | None,
    expected_max: float | None,
) -> None:
    analysis = analyze_query(f"tìm quần dài giống ảnh, chất liệu polyester, giá {literal}")

    assert analysis.filters.material == "polyester"
    assert analysis.filters.min_price == expected_min
    assert analysis.filters.max_price == expected_max
