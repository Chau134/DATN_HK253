from types import SimpleNamespace

from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.filtering import CatalogMetadata
from ecommerce_search_assistant.services.search.service import SearchService


def _service_with_metadata(metadata: CatalogMetadata) -> SearchService:
    service = object.__new__(SearchService)
    service._catalog_metadata = lambda: metadata  # type: ignore[method-assign]
    return service


def test_catalog_title_resolution_handles_exact_and_unambiguous_typo() -> None:
    service = _service_with_metadata(
        CatalogMetadata(
            normalized_titles=frozenset(
                {"ao hoodie the thao nam", "ao so mi satin hoa nu"}
            ),
            title_product_ids={
                "ao hoodie the thao nam": ("20",),
                "ao so mi satin hoa nu": ("1",),
            },
        )
    )

    resolved = service.resolve_catalog_title_ids(
        ["ao hoodie the thao nam", "ao so mi satn hoa nu"]
    )

    assert resolved == {
        "ao hoodie the thao nam": ["20"],
        "ao so mi satn hoa nu": ["1"],
    }


def test_exact_catalog_title_resolution_never_binds_a_neighboring_product() -> None:
    service = _service_with_metadata(
        CatalogMetadata(
            normalized_titles=frozenset({"ao khoac mau nau dam"}),
            title_product_ids={"ao khoac mau nau dam": ("10",)},
        )
    )

    resolved = service.resolve_exact_catalog_title_ids(
        ["Áo khoác Sao Hỏa phiên bản 2099"]
    )

    assert resolved == {"Áo khoác Sao Hỏa phiên bản 2099": []}


def test_catalog_candidate_filter_uses_cached_product_payloads() -> None:
    service = _service_with_metadata(
        CatalogMetadata(
            product_filter_payloads={
                "1": {
                    "category_keys": ["shirt"],
                    "color_keys": ["black"],
                },
                "2": {
                    "category_keys": ["shirt"],
                    "color_keys": ["white"],
                },
            }
        )
    )

    matched = service.filter_catalog_product_ids(
        ["1", "2"],
        SearchFilter(category="shirt", colors=["black"]),
    )

    assert matched == ["1"]


def test_catalog_category_counts_uses_active_available_qdrant_facets() -> None:
    class FacetClient:
        def __init__(self) -> None:
            self.request = None

        def facet(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(
                hits=[
                    SimpleNamespace(value="t-shirt", count=153),
                    SimpleNamespace(value="dress", count=192),
                    SimpleNamespace(value="blouse_top", count=154),
                ]
            )

    client = FacetClient()
    service = object.__new__(SearchService)
    service.settings = SimpleNamespace(qdrant_text_collection="catalog")
    service.qdrant_client = client

    categories = service.catalog_category_counts()

    assert [(item.code, item.name_vi, item.count) for item in categories] == [
        ("dress", "Váy & đầm", 192),
        ("blouse_top", "Áo kiểu", 154),
        ("t-shirt", "Áo thun", 153),
    ]
    assert client.request["collection_name"] == "catalog"
    assert client.request["key"] == "category_codes"
    assert client.request["exact"] is True
    assert {
        condition.key
        for condition in client.request["facet_filter"].must
    } == {"active", "available"}
