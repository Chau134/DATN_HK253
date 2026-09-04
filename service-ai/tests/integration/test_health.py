from fastapi.testclient import TestClient

from ecommerce_search_assistant.api.routes import health as health_module


class _ReadinessService:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    def is_ready(self) -> bool:
        return self.ready


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "test-ai-ecommerce-assistant",
        "environment": "test",
    }


def test_readiness_reports_models_not_loaded(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        health_module,
        "get_text_embedding_service",
        lambda: _ReadinessService(False),
    )
    monkeypatch.setattr(
        health_module,
        "get_image_embedding_service",
        lambda: _ReadinessService(False),
    )
    monkeypatch.setattr(
        health_module,
        "get_llm_service",
        lambda: _ReadinessService(True),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert body["models"]["text_embedding"] is False
    assert body["models"]["image_embedding"] is False
    assert body["models"]["yolo"] is False
    assert body["models"]["llm"] is True
    assert body["capabilities"] == {
        "text_search": False,
        "image_search": False,
        "assistant_llm": True,
    }
    assert body["capability"] is None
    assert body["evaluation_variant"] == "rag"
    # rerank_enabled defaults to False, so the reranker is not part of readiness.
    assert "reranker" not in body["models"]


def test_capability_readiness_is_independent(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        health_module,
        "get_text_embedding_service",
        lambda: _ReadinessService(True),
    )
    monkeypatch.setattr(
        health_module,
        "get_image_embedding_service",
        lambda: _ReadinessService(False),
    )
    monkeypatch.setattr(
        health_module,
        "get_llm_service",
        lambda: _ReadinessService(True),
    )

    text_response = client.get("/health/ready/text_search")
    image_response = client.get("/health/ready/image_search")
    llm_response = client.get("/health/ready/assistant_llm")

    assert text_response.status_code == 200
    assert text_response.json()["ready"] is True
    assert text_response.json()["capability"] == "text_search"
    assert image_response.status_code == 503
    assert image_response.json()["ready"] is False
    assert image_response.json()["capability"] == "image_search"
    assert llm_response.status_code == 200
    assert llm_response.json()["ready"] is True
    assert llm_response.json()["capability"] == "assistant_llm"
