import pytest
from qdrant_client import QdrantClient, models

from ecommerce_search_assistant.schemas.product import ProductIndexItem
from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.indexing.product import _product_payload
from ecommerce_search_assistant.services.search.filtering import analyze_query
from ecommerce_search_assistant.services.search.service import _build_qdrant_filter


def test_vietnamese_jacket_query_matches_canonical_payload_in_local_qdrant() -> None:
    client = QdrantClient(location=":memory:")
    collection_name = "canonical-products"
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    product = ProductIndexItem(
        product_id="P-JACKET-1",
        product_display_name="Black Jackets & Coats",
        categories=[{"category_name": "Jackets & Coats"}],
        base_colour="Black",
        gender="Unisex Adult",
        active=True,
        image_urls=[],
    )
    client.upsert(
        collection_name=collection_name,
        points=[models.PointStruct(id=1, vector=[1.0, 0.0], payload=_product_payload(product))],
        wait=True,
    )

    response = client.query_points(
        collection_name=collection_name,
        query=[1.0, 0.0],
        query_filter=_build_qdrant_filter(
            SearchFilter(category="áo khoác", gender="nam", colors=["màu đen"])
        ),
        limit=5,
        with_payload=True,
    )

    assert [point.payload["product_id"] for point in response.points] == ["P-JACKET-1"]


@pytest.mark.parametrize(
    ("code", "name", "name_vi", "query"),
    (
        ("shirt_blouse", "Shirts & Blouses", "Áo sơ mi & áo kiểu", "áo sơ mi"),
        ("polo", "Polo Shirts", "Áo polo", "áo polo"),
        ("sweater_cardigan", "Sweaters & Cardigans", "Áo len & cardigan", "áo cardigan"),
        ("hoodie_sweatshirt", "Hoodies & Sweatshirts", "Áo hoodie & áo nỉ", "áo hoodie"),
        ("dress", "Dresses", "Váy & Đầm", "váy"),
        ("blazer_vest", "Blazers & Vests", "Blazer & áo vest", "blazer"),
    ),
)
def test_previously_mismatched_categories_return_qdrant_candidates(
    code: str,
    name: str,
    name_vi: str,
    query: str,
) -> None:
    client = QdrantClient(location=":memory:")
    collection_name = "category-regression"
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    product = ProductIndexItem(
        product_id=f"P-{code}",
        product_display_name=name,
        categories=[
            {
                "category_code": code,
                "category_level": "article_type",
                "category_name": name,
                "category_name_vi": name_vi,
            }
        ],
        active=True,
    )
    client.upsert(
        collection_name=collection_name,
        points=[models.PointStruct(id=1, vector=[1.0, 0.0], payload=_product_payload(product))],
        wait=True,
    )

    response = client.query_points(
        collection_name=collection_name,
        query=[1.0, 0.0],
        query_filter=_build_qdrant_filter(analyze_query(query).filters),
        limit=5,
        with_payload=True,
    )

    assert [point.payload["product_id"] for point in response.points] == [f"P-{code}"]
