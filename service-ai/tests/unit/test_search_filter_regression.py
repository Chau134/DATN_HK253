import pytest

from ecommerce_search_assistant.services.search.filtering import analyze_query


@pytest.mark.parametrize(
    ("query", "expected_filters", "expected_semantic"),
    (
        (
            "ao den nu duoi 500k",
            {"colors": ["black"], "gender": "women", "max_price": 500000.0},
            set(),
        ),
        (
            "giay sneaker size 42",
            {"category": "sneakers", "sizes": ["42"]},
            set(),
        ),
        (
            "do di lam form rong mau trang",
            {"colors": ["white"]},
            {"work", "oversized"},
        ),
        (
            "addidas sneaker nam",
            {"category": "sneakers", "brand": "adidas", "gender": "men"},
            set(),
        ),
        (
            "mau dep di choi cuoi tuan",
            {},
            {"casual weekend"},
        ),
    ),
)
def test_vietnamese_ecommerce_query_regression(
    query: str,
    expected_filters: dict[str, object],
    expected_semantic: set[str],
) -> None:
    analysis = analyze_query(query)
    actual_filters = analysis.filters.model_dump(exclude_none=True)

    for field, expected in expected_filters.items():
        assert actual_filters[field] == expected
    assert expected_semantic.issubset(analysis.semantic_constraints)
