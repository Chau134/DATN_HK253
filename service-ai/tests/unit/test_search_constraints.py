from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.constraints import resolve_search_constraints


def test_explicit_filters_stay_hard_while_inferred_metadata_is_soft() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="jacket", material="leather", gender="men"),
        llm_filters=SearchFilter(colors=["black"]),
        explicit_filters=SearchFilter(brand="zara"),
        confidences={"category": 0.99, "material": 0.75, "gender": 0.9},
    )

    assert resolved.hard_filters == SearchFilter(brand="zara")
    assert resolved.explicit_hard_filters == SearchFilter(brand="zara")
    assert resolved.soft_filters == SearchFilter(
        category="jacket",
        material="leather",
        gender="men",
        colors=["black"],
    )
    assert set(resolved.downgraded_fields) == {"category", "material", "gender", "colors"}


def test_deterministic_inferred_price_and_size_can_be_hard_and_retryable() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(max_price=500000, sizes=["M"]),
        llm_filters=None,
        explicit_filters=None,
        confidences={"price": 0.99, "size": 0.98},
        match_sources={"price": "regex", "size": "regex"},
    )

    assert resolved.hard_filters == SearchFilter(max_price=500000, sizes=["m"])
    assert resolved.has_inferred_hard_filters is True
    assert resolved.has_recoverable_inferred_hard_filters is True
    assert resolved.recovery_filters == SearchFilter(max_price=500000)


def test_dictionary_color_is_hard_and_retained_but_llm_color_stays_soft() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(colors=["dark indigo"]),
        llm_filters=SearchFilter(material="elastane"),
        explicit_filters=None,
        confidences={"color": 0.95, "material": 0.75},
        match_sources={"color": "dictionary", "material": "dictionary"},
        allow_color_hard=True,
    )

    assert resolved.hard_filters == SearchFilter(colors=["dark indigo"])
    assert resolved.recovery_filters == SearchFilter(colors=["dark indigo"])
    assert resolved.soft_filters == SearchFilter(
        colors=["dark indigo"],
        material="elastane",
    )
    assert resolved.has_recoverable_inferred_hard_filters is False


def test_dictionary_color_stays_soft_until_hard_filter_flag_is_enabled() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(colors=["purple"]),
        llm_filters=None,
        explicit_filters=None,
        confidences={"color": 0.95},
        match_sources={"color": "dictionary"},
    )

    assert resolved.hard_filters is None
    assert resolved.soft_filters == SearchFilter(colors=["purple"])


def test_explicit_price_is_never_relaxed() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="jacket"),
        llm_filters=None,
        explicit_filters=SearchFilter(max_price=100000),
    )

    assert resolved.explicit_hard_filters == SearchFilter(max_price=100000)
    assert resolved.has_inferred_hard_filters is False


def test_dictionary_category_is_hard_and_retained_during_recovery() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="shirt"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.99},
        match_sources={"category": "dictionary"},
        allow_category_hard=True,
    )

    assert resolved.hard_filters == SearchFilter(category="shirt")
    # Category remains a ranking signal, but a trusted phrase is also retained in
    # the recovery filter so other product types cannot enter the result set.
    assert resolved.soft_filters == SearchFilter(category="shirt")
    assert resolved.has_inferred_hard_filters is True
    assert resolved.has_recoverable_inferred_hard_filters is False
    assert resolved.recovery_filters == SearchFilter(category="shirt")


def test_dictionary_category_stays_soft_when_hard_not_allowed() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="shirt"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.99},
        match_sources={"category": "dictionary"},
    )

    assert resolved.hard_filters is None
    assert resolved.soft_filters == SearchFilter(category="shirt")
    assert resolved.has_inferred_hard_filters is False


def test_ambiguous_category_stays_soft_even_when_hard_allowed() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="shirt"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.99},
        match_sources={"category": "dictionary"},
        category_ambiguous=True,
        allow_category_hard=True,
    )

    assert resolved.hard_filters is None
    assert resolved.soft_filters == SearchFilter(category="shirt")


def test_fuzzy_category_is_not_hard_filtered() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="shirt"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.85},
        match_sources={"category": "fuzzy"},
        allow_category_hard=True,
    )

    assert resolved.hard_filters is None
    assert resolved.soft_filters == SearchFilter(category="shirt")


def test_typo_category_can_be_hard_but_is_recoverable() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="blouse"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.94},
        match_sources={"category": "typo"},
        allow_category_hard=True,
    )

    assert resolved.hard_filters == SearchFilter(category="blouse")
    assert resolved.recovery_filters is None
    assert resolved.has_recoverable_inferred_hard_filters is True
    assert resolved.constraints[0].match_type == "typo"


def test_recovery_relaxes_category_but_retains_certain_price_constraint() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="blouse", max_price=500000),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.94, "price": 0.99},
        match_sources={"category": "typo", "price": "regex"},
        allow_category_hard=True,
    )

    assert resolved.hard_filters == SearchFilter(category="blouse", max_price=500000)
    assert resolved.recovery_filters == SearchFilter(max_price=500000)


def test_alias_category_and_price_are_both_retained_during_recovery() -> None:
    resolved = resolve_search_constraints(
        rule_filters=SearchFilter(category="pants", max_price=1000000),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.97, "price": 0.92},
        match_sources={"category": "alias", "price": "regex"},
        allow_category_hard=True,
    )

    expected = SearchFilter(category="pants", max_price=1000000)
    assert resolved.hard_filters == expected
    assert resolved.recovery_filters == expected
    assert resolved.has_recoverable_inferred_hard_filters is False


def test_combined_color_match_mode_follows_hard_color_into_recovery() -> None:
    combined = SearchFilter(
        colors=["pink", "white"],
        color_match_mode="all",
    )
    resolved = resolve_search_constraints(
        rule_filters=combined,
        llm_filters=None,
        explicit_filters=None,
        confidences={"color": 0.99},
        match_sources={"color": "dictionary"},
        allow_color_hard=True,
    )

    assert resolved.hard_filters == combined
    assert resolved.recovery_filters == combined
