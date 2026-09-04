from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.filtering import (
    normalize_filter_values,
    normalize_gender,
)


def test_normalize_gender_maps_vietnamese_and_english_variants() -> None:
    assert normalize_gender("Nữ") == "women"
    assert normalize_gender("women") == "women"
    assert normalize_gender("Female") == "women"
    assert normalize_gender("Nam") == "men"
    assert normalize_gender("MEN") == "men"
    assert normalize_gender("unisex") == "unisex"


def test_normalize_gender_returns_none_for_unknown() -> None:
    assert normalize_gender(None) is None
    assert normalize_gender("") is None
    assert normalize_gender("khong biet") is None


def test_normalize_filter_values_canonicalizes_gender() -> None:
    normalized = normalize_filter_values(SearchFilter(gender="Nữ"))
    assert normalized is not None
    assert normalized.gender == "women"


def test_normalize_filter_values_drops_unrecognized_gender() -> None:
    normalized = normalize_filter_values(SearchFilter(gender="asdf"))
    assert normalized is not None
    assert normalized.gender is None
