from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.service import _build_qdrant_filter


def test_qdrant_filter_uses_indexed_payload_fields() -> None:
    qdrant_filter = _build_qdrant_filter(
        SearchFilter(
            category="hoodie",
            gender="women",
            brand="Codex",
            colors=["black"],
            sizes=["M"],
            min_price=100000,
            max_price=500000,
        )
    )

    keys = [getattr(condition, "key", None) for condition in qdrant_filter.must]

    assert keys == [
        "active",
        "category_keys",
        "audience_keys",
        "brand_key",
        "color_keys",
        "size_keys",
        "selling_price",
    ]


def test_qdrant_filter_category_uses_same_canonical_key_for_vietnamese() -> None:
    qdrant_filter = _build_qdrant_filter(SearchFilter(category="ao so mi"))

    condition = qdrant_filter.must[1]
    assert condition.key == "category_keys"
    assert condition.match.any == ["shirt", "shirts blouses", "ao so mi ao kieu"]


def test_qdrant_filter_omits_gender_when_absent() -> None:
    qdrant_filter = _build_qdrant_filter(SearchFilter(category="hoodie"))

    keys = [getattr(condition, "key", None) for condition in qdrant_filter.must]

    assert len(qdrant_filter.must) == 2


def test_qdrant_filter_omits_soft_attributes_when_enabled() -> None:
    qdrant_filter = _build_qdrant_filter(
        SearchFilter(category="hoodie", gender="women", colors=["black"], sizes=["M"]),
        soft_attributes=True,
    )

    keys = [getattr(condition, "key", None) for condition in qdrant_filter.must]

    assert len(qdrant_filter.must) == 3
    size_filter = qdrant_filter.must[-1]
    assert size_filter.key == "size_keys"
    assert size_filter.match.any == ["m"]


def test_qdrant_filter_requires_every_color_for_combined_colorway() -> None:
    qdrant_filter = _build_qdrant_filter(
        SearchFilter(colors=["pink", "white"], color_match_mode="all")
    )

    color_conditions = [
        condition for condition in qdrant_filter.must if condition.key == "color_keys"
    ]
    assert [condition.match.value for condition in color_conditions] == ["pink", "white"]
