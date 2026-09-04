import json
import os
from base64 import b64decode
from io import BytesIO
from typing import Any

from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.services.embeddings.bedrock import (
    BedrockCohereImageEmbeddingService,
    BedrockCohereTextEmbeddingService,
    _normalize_bedrock_bearer_token,
)
from ecommerce_search_assistant.services.embeddings.factory import (
    get_image_embedding_service,
    get_text_embedding_service,
)


class _Body:
    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    def read(self) -> bytes:
        return json.dumps(self._value).encode("utf-8")


class _FakeBedrockClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke_model(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        body = json.loads(kwargs["body"])
        inputs = body.get("texts") or body.get("images") or []
        dimensions = body["output_dimension"]
        return {
            "body": _Body(
                {
                    "response_type": "embeddings_by_type",
                    "embeddings": {
                        "float": [
                            [float(index)] * dimensions
                            for index, _ in enumerate(inputs, start=1)
                        ]
                    },
                }
            )
        }


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        EMBEDDING_PROVIDER="bedrock",
        BEDROCK_EMBEDDING_MODEL_ID="cohere.embed-v4:0",
        EMBEDDING_OUTPUT_DIMENSIONALITY=256,
        QDRANT_TEXT_VECTOR_SIZE=256,
        QDRANT_IMAGE_VECTOR_SIZE=256,
        EMBEDDING_BATCH_SIZE=2,
        BEDROCK_EMBEDDING_MIN_REQUEST_INTERVAL_SECONDS=0,
        BEDROCK_EMBEDDING_THROTTLE_BACKOFF_SECONDS=0,
        BEDROCK_EMBEDDING_THROTTLE_MAX_BACKOFF_SECONDS=0,
    )


def test_bedrock_text_embedding_uses_retrieval_input_types_and_batches() -> None:
    service = BedrockCohereTextEmbeddingService(settings=_settings())
    client = _FakeBedrockClient()
    service._client = client
    assert service.is_ready() is False

    documents = service.embed_documents(["ao hoodie den", "black hoodie", "ao khoac"])
    query = service.embed_query("tìm áo hoodie màu đen")

    assert len(documents) == 3
    assert len(query) == 256
    assert [json.loads(call["body"])["input_type"] for call in client.calls] == [
        "search_document",
        "search_document",
        "search_query",
    ]
    assert all(call["modelId"] == "cohere.embed-v4:0" for call in client.calls)
    assert service.is_ready() is True


def test_bedrock_embedding_readiness_tracks_successful_runtime_call() -> None:
    service = BedrockCohereTextEmbeddingService(settings=_settings())
    client = _FakeBedrockClient()
    service._client = client

    service.warmup()
    assert service.is_ready() is True

    class _FailingClient:
        def invoke_model(self, **kwargs: Any) -> dict[str, Any]:
            del kwargs
            raise RuntimeError("provider unavailable")

    service._client = _FailingClient()
    try:
        service.embed_query("test")
    except RuntimeError:
        pass

    assert service.is_ready() is False


def test_bedrock_query_embedding_cache_avoids_duplicate_provider_calls() -> None:
    settings = _settings().model_copy(update={
        "text_query_embedding_cache_ttl_seconds": 60,
        "text_query_embedding_cache_size": 2,
    })
    service = BedrockCohereTextEmbeddingService(settings=settings)
    client = _FakeBedrockClient()
    service._client = client

    first = service.embed_query("  Áo THUN nâu ")
    second = service.embed_query("áo thun nâu")

    assert first == second
    assert first is not second
    assert len(client.calls) == 1


def test_empty_embedding_bearer_token_is_removed(monkeypatch) -> None:
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "   ")

    _normalize_bedrock_bearer_token()

    assert "AWS_BEARER_TOKEN_BEDROCK" not in os.environ


def test_bedrock_image_embedding_sends_jpeg_data_uris_with_correct_input_type() -> None:
    service = BedrockCohereImageEmbeddingService(settings=_settings())
    client = _FakeBedrockClient()
    service._client = client
    image = Image.new("RGBA", (1024, 256), color=(10, 20, 30, 128))

    document = service.embed_documents([image])[0]
    query = service.embed_queries([image])[0]

    document_body = json.loads(client.calls[0]["body"])
    query_body = json.loads(client.calls[1]["body"])
    assert len(document) == 256
    assert len(query) == 256
    assert document_body["images"][0].startswith("data:image/jpeg;base64,")
    encoded = document_body["images"][0].split(",", maxsplit=1)[1]
    embedded_image = Image.open(BytesIO(b64decode(encoded)))
    assert embedded_image.size == (512, 128)
    assert document_body["input_type"] == "search_document"
    assert query_body["input_type"] == "search_query"


def test_embedding_factory_selects_bedrock(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bedrock")
    monkeypatch.setenv("EMBEDDING_OUTPUT_DIMENSIONALITY", "1536")
    monkeypatch.setenv("QDRANT_TEXT_VECTOR_SIZE", "1536")
    monkeypatch.setenv("QDRANT_IMAGE_VECTOR_SIZE", "1536")
    get_settings.cache_clear()
    get_text_embedding_service.cache_clear()
    get_image_embedding_service.cache_clear()

    assert isinstance(get_text_embedding_service(), BedrockCohereTextEmbeddingService)
    assert isinstance(get_image_embedding_service(), BedrockCohereImageEmbeddingService)

    get_text_embedding_service.cache_clear()
    get_image_embedding_service.cache_clear()
    get_settings.cache_clear()
