from typing import Any

import pytest

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.services.embeddings.cohere import CohereTextEmbeddingService
from ecommerce_search_assistant.services.embeddings.factory import (
    get_image_embedding_service,
    get_text_embedding_service,
)


class _Embeddings:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.float = vectors


class _Response:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.embeddings = _Embeddings(vectors)


class _FakeCohereClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def embed(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        inputs = kwargs.get("texts") or kwargs.get("inputs") or []
        dimensions = kwargs["output_dimension"]
        return _Response([[float(index)] * dimensions for index, _ in enumerate(inputs, start=1)])


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        EMBEDDING_PROVIDER="cohere",
        COHERE_API_KEY="trial-key",
        COHERE_EMBEDDING_MODEL_NAME="embed-v4.0",
        EMBEDDING_OUTPUT_DIMENSIONALITY=256,
        QDRANT_TEXT_VECTOR_SIZE=256,
        QDRANT_IMAGE_VECTOR_SIZE=256,
        EMBEDDING_BATCH_SIZE=2,
    )


def test_cohere_text_embedding_uses_retrieval_input_types_and_batches() -> None:
    service = CohereTextEmbeddingService(settings=_settings())
    client = _FakeCohereClient()
    service._client = client

    documents = service.embed_documents(["ao hoodie den", "black hoodie", "ao khoac"])
    query = service.embed_query("tim ao hoodie mau den")

    assert len(documents) == 3
    assert len(query) == 256
    assert [call["input_type"] for call in client.calls] == [
        "search_document",
        "search_document",
        "search_query",
    ]
    assert all(call["model"] == "embed-v4.0" for call in client.calls)
    assert all(call["embedding_types"] == ["float"] for call in client.calls)


def test_cohere_provider_requires_api_key() -> None:
    service = CohereTextEmbeddingService(
        settings=Settings(
            _env_file=None,
            EMBEDDING_PROVIDER="cohere",
            COHERE_API_KEY="",
        )
    )

    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        service.warmup()


def test_embedding_factory_selects_direct_cohere(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "cohere")
    monkeypatch.setenv("COHERE_API_KEY", "trial-key")
    monkeypatch.setenv("EMBEDDING_OUTPUT_DIMENSIONALITY", "1536")
    monkeypatch.setenv("QDRANT_TEXT_VECTOR_SIZE", "1536")
    monkeypatch.setenv("QDRANT_IMAGE_VECTOR_SIZE", "1536")
    get_settings.cache_clear()
    get_text_embedding_service.cache_clear()
    get_image_embedding_service.cache_clear()

    assert get_text_embedding_service().__class__.__name__ == "CohereTextEmbeddingService"
    assert get_image_embedding_service().__class__.__name__ == "CohereImageEmbeddingService"

    get_text_embedding_service.cache_clear()
    get_image_embedding_service.cache_clear()
    get_settings.cache_clear()
