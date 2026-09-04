from ecommerce_search_assistant.services.search.aliases import BRAND_ALIASES
from ecommerce_search_assistant.services.search.filtering import analyze_query
from ecommerce_search_assistant.services.search.matching import fuzzy_alias_match


def test_fuzzy_matching_recovers_guarded_brand_and_category_typos() -> None:
    analysis = analyze_query("adids sneakr nam")

    assert analysis.filters.brand == "adidas"
    assert analysis.filters.category == "sneakers"
    assert analysis.filters.gender == "men"
    assert analysis.metadata["match_sources"]["brand"] == "fuzzy"
    assert analysis.metadata["match_sources"]["category"] == "fuzzy"


def test_fuzzy_matching_rejects_low_similarity_text() -> None:
    assert fuzzy_alias_match("beautiful weekend outfit", BRAND_ALIASES).value is None


def test_fuzzy_matching_reports_close_candidates_as_ambiguous() -> None:
    result = fuzzy_alias_match(
        "abcd",
        {"abce": "first", "abcf": "second"},
        threshold=0.7,
    )

    assert result.value is None
    assert result.ambiguous is True
