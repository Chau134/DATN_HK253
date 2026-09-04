import pytest

from ecommerce_search_assistant.services.search.parsers.size import extract_sizes, is_valid_size


@pytest.mark.parametrize(
    ("query", "expected"),
    (
        ("size m", ("m",)),
        ("size XL", ("xl",)),
        ("giay size 42", ("42",)),
        ("42", ("42",)),
        ("one size", ("one size",)),
        ("free size", ("one size",)),
    ),
)
def test_extract_sizes_supports_alpha_numeric_and_one_size(query: str, expected: tuple[str, ...]) -> None:
    assert extract_sizes(query).values == expected


def test_size_parser_does_not_parse_price_fragments() -> None:
    assert extract_sizes("300.000d va 1m5").values == ()
    assert is_valid_size("bad-size") is False
