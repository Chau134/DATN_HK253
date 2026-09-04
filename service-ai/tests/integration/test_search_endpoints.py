import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_search_assistant.services.search.factory import get_search_service
from ecommerce_search_assistant.services.search.service import SearchService


def test_text_search_endpoint_rewrites_query_and_applies_filters(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    fake_llm_service,
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service

    response = client.post("/search/text", json={"query": "black hoodie", "filters": {"colors": ["black"]}})

    assert response.status_code == 200
    payload = response.json()
    assert payload["rewritten_query"] == "rewritten black hoodie"
    assert payload["filters"] == {"category": "hoodie", "colors": ["black"]}
    assert payload["product_ids"] == ["P-TEXT", "P-SHARED"]
    assert payload["results"][0]["source"] == "text"
    assert fake_llm_service.analyze_calls == [("black hoodie", "vi-VN")]


def test_auto_search_routes_text_query_to_text_search(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    fake_llm_service,
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service
    search_service.settings = search_service.settings.model_copy(
        update={"text_llm_fast_path_enabled": False}
    )

    response = client.post("/search/auto", json={"query": "black hoodie", "top_k": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "text_search"
    assert payload["rewritten_query"] == "rewritten black hoodie"
    assert payload["results"][0]["source"] == "text"
    assert fake_llm_service.analyze_calls == [("black hoodie", "vi-VN")]


def test_auto_search_routes_image_only_without_llm(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    fake_llm_service,
    image_payload: dict[str, str],
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service

    response = client.post("/search/auto", json={"image": image_payload})

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "image_search"
    assert payload["results"][0]["source"] == "image"
    assert fake_llm_service.analyze_calls == []


def test_auto_search_routes_generic_image_reference_to_image_search(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    image_payload: dict[str, str],
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service

    response = client.post(
        "/search/auto",
        json={"query": "tìm giống ảnh này", "image": image_payload},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "image_search"
    assert payload["results"][0]["source"] == "image"


def test_image_search_endpoint_uses_mock_yolo_and_image_embedding(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    image_payload: dict[str, str],
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service

    response = client.post("/search/image", json={"image": image_payload})

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"] == ["P-IMAGE", "P-SHARED"]
    assert payload["results"][0]["source"] == "image"
    assert payload["detections"][0]["bbox"] == {"left": 0, "top": 0, "right": 8, "bottom": 8}


def test_image_detection_endpoint_returns_yolo_boxes(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    image_payload: dict[str, str],
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service

    response = client.post("/search/image/detections", json={"image": image_payload})

    assert response.status_code == 200
    payload = response.json()
    assert payload["image_width"] == 8
    assert payload["image_height"] == 8
    assert payload["detections"][0]["bbox"] == {"left": 0, "top": 0, "right": 8, "bottom": 8}


def test_image_search_endpoint_accepts_user_crop_box(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    image_payload: dict[str, str],
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service

    response = client.post(
        "/search/image",
        json={
            "image": image_payload,
            "crop_box": {"left": 1, "top": 2, "right": 7, "bottom": 6},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"] == ["P-IMAGE", "P-SHARED"]
    assert payload["detections"][0]["bbox"] == {"left": 1, "top": 2, "right": 7, "bottom": 6}


def test_hybrid_search_endpoint_merges_text_and_image_candidates(
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    image_payload: dict[str, str],
) -> None:
    app.dependency_overrides[get_search_service] = lambda: search_service

    response = client.post(
        "/search/hybrid",
        json={"query": "black hoodie", "image": image_payload},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rewritten_query"] == "rewritten black hoodie"
    assert payload["product_ids"][0] == "P-SHARED"
    assert payload["results"][0]["source"] == "hybrid"


@pytest.mark.parametrize(
    ("endpoint", "base_payload"),
    [
        ("/search/text", {"query": "black hoodie"}),
        ("/search/auto", {"query": "black hoodie"}),
        ("/search/image", {}),
        ("/search/hybrid", {"query": "black hoodie"}),
    ],
)
def test_search_endpoints_reject_top_k_above_runtime_limit(
    endpoint: str,
    base_payload: dict[str, object],
    app: FastAPI,
    client: TestClient,
    search_service: SearchService,
    image_payload: dict[str, str],
) -> None:
    search_service.settings = search_service.settings.model_copy(update={"max_search_top_k": 2})
    app.dependency_overrides[get_search_service] = lambda: search_service
    payload = {**base_payload, "top_k": 3}
    if endpoint == "/search/image":
        payload["image"] = image_payload

    response = client.post(endpoint, json=payload)

    assert response.status_code == 422
    assert "MAX_SEARCH_TOP_K=2" in response.json()["detail"]


def test_search_schema_rejects_top_k_above_absolute_cap(client: TestClient) -> None:
    response = client.post("/search/text", json={"query": "black hoodie", "top_k": 101})

    assert response.status_code == 422
