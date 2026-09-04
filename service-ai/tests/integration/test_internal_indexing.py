from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_search_assistant.services.indexing.factory import get_product_indexing_service
from ecommerce_search_assistant.services.indexing.product import ProductIndexingService


def test_internal_batch_index_endpoint_uses_in_memory_fakes(
    app: FastAPI,
    client: TestClient,
    indexing_service: ProductIndexingService,
    fake_qdrant_client,
) -> None:
    app.dependency_overrides[get_product_indexing_service] = lambda: indexing_service

    response = client.post(
        "/internal/index/products/batch",
        headers={"X-Internal-API-Key": "test-internal-key"},
        json={
            "items": [
                {
                    "product_id": "P-INDEX-1",
                    "product_display_name": "Indexed Hoodie",
                    "description": "Offline test fixture",
                    "image_urls": ["https://assets.test/indexed-hoodie.png"],
                    "selling_price": 320000,
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "indexed_count": 1,
        "failed_count": 0,
        "image_indexed_count": 1,
        "image_failed_count": 0,
        "failures": [],
    }
    assert [call["collection_name"] for call in fake_qdrant_client.upserts] == [
        "product_text_vectors",
        "product_image_vectors",
    ]


def test_product_update_deletes_old_text_and_image_points_before_writing_new_embedding(
    app: FastAPI,
    client: TestClient,
    indexing_service: ProductIndexingService,
    fake_qdrant_client,
) -> None:
    app.dependency_overrides[get_product_indexing_service] = lambda: indexing_service

    response = client.post(
        "/internal/index/products/P-UPDATE-1",
        headers={"X-Internal-API-Key": "test-internal-key"},
        json={
            "product_id": "P-UPDATE-1",
            "product_display_name": "Black Jackets & Coats",
            "base_colour": "Black",
            "gender": "Unisex Adult",
            "categories": [{"category_name": "Jackets & Coats"}],
            "image_urls": [],
        },
    )

    assert response.status_code == 200
    assert [call["collection_name"] for call in fake_qdrant_client.deletes] == [
        "product_text_vectors",
        "product_image_vectors",
    ]
    payload = fake_qdrant_client.upserts[0]["points"][0].payload
    assert payload["category_keys"] == ["jacket", "coat"]
    assert payload["color_keys"] == ["black"]
    assert payload["audience_keys"] == ["unisex", "men", "women"]
