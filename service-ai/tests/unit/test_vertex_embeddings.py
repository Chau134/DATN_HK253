from types import SimpleNamespace

from PIL import Image

from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.services.embeddings.vertex import (
    VertexGeminiImageEmbeddingService,
    VertexGeminiTextEmbeddingService,
)


class _FakePart:
    @staticmethod
    def from_text(*, text: str):
        return {"text": text}

    @staticmethod
    def from_bytes(*, data: bytes, mime_type: str):
        return {"data": data, "mime_type": mime_type}


class _FakeContent:
    def __init__(self, *, role: str, parts: list[dict]) -> None:
        self.role = role
        self.parts = parts


class _FakeEmbedContentConfig:
    def __init__(self, *, output_dimensionality: int) -> None:
        self.output_dimensionality = output_dimensionality


class _FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def embed_content(self, **kwargs):
        self.calls.append(kwargs)
        dimensions = kwargs["config"].output_dimensionality
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[float(index)] * dimensions)
                for index, _ in enumerate(kwargs["contents"], start=1)
            ]
        )


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        EMBEDDING_PROVIDER="gemini_api",
        GOOGLE_CLOUD_PROJECT="test-project",
        EMBEDDING_OUTPUT_DIMENSIONALITY=128,
        QDRANT_TEXT_VECTOR_SIZE=128,
        QDRANT_IMAGE_VECTOR_SIZE=128,
    )


def _install_fake_sdk(service):
    models = _FakeModels()
    service._client = SimpleNamespace(models=models)
    service._types = SimpleNamespace(
        Content=_FakeContent,
        Part=_FakePart,
        EmbedContentConfig=_FakeEmbedContentConfig,
    )
    return models


def test_vertex_text_embedding_uses_gemini_embedding_2_retrieval_prefixes() -> None:
    service = VertexGeminiTextEmbeddingService(settings=_settings())
    models = _install_fake_sdk(service)

    query = service.embed_query("hoodie den")
    documents = service.embed_documents(["Ao hoodie cotton", "Ao khoac ni"])

    assert len(query) == 128
    assert len(documents) == 2
    assert models.calls[0]["model"] == "gemini-embedding-2"
    assert models.calls[0]["contents"][0].parts == [
        {"text": "task: search result | query: hoodie den"}
    ]
    assert models.calls[1]["contents"][0].parts == [
        {"text": "title: none | text: Ao hoodie cotton"}
    ]


def test_vertex_image_embedding_sends_png_without_loading_local_model() -> None:
    service = VertexGeminiImageEmbeddingService(settings=_settings())
    models = _install_fake_sdk(service)

    vector = service.embed_image(Image.new("RGB", (4, 4), color="black"))

    part = models.calls[0]["contents"][0].parts[0]
    assert len(vector) == 128
    assert part["mime_type"] == "image/png"
    assert part["data"].startswith(b"\x89PNG")


def test_vertex_embedding_reads_api_key_from_secret_file(tmp_path) -> None:
    key_file = tmp_path / "vertex-api-key"
    key_file.write_text("temporary-test-key\n", encoding="utf-8")
    settings = _settings().model_copy(
        update={
            "google_cloud_project": None,
            "google_cloud_api_key_file": str(key_file),
        }
    )

    service = VertexGeminiTextEmbeddingService(settings=settings)

    assert service._load_api_key() == "temporary-test-key"
