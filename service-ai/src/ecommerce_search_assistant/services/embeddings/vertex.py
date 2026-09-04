from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings


@dataclass
class _VertexGeminiEmbeddingBase:
    settings: Settings = field(default_factory=get_settings)
    _client: Any | None = field(default=None, init=False, repr=False)
    _types: Any | None = field(default=None, init=False, repr=False)

    def warmup(self) -> None:
        # Creating the SDK client only resolves configuration/credentials. It does not
        # download a model or perform an embedding request.
        self._get_client()

    def is_ready(self) -> bool:
        return self._client is not None

    def _get_client(self) -> tuple[Any, Any]:
        if self._client is None or self._types is None:
            api_key = self._load_api_key()
            if self.settings.embedding_provider == "gemini_api" and not api_key:
                raise RuntimeError(
                    "A Google Cloud API key is required when "
                    "EMBEDDING_PROVIDER=gemini_api"
                )
            if self.settings.embedding_provider == "vertex_ai" and not (
                api_key or self.settings.google_cloud_project
            ):
                raise RuntimeError(
                    "GOOGLE_CLOUD_PROJECT or a Google Cloud API key is required "
                    "when EMBEDDING_PROVIDER=vertex_ai"
                )

            from google import genai
            from google.genai import types

            client_options: dict[str, Any] = {
                "http_options": types.HttpOptions(
                    api_version=self.settings.google_genai_api_version
                ),
            }
            if self.settings.embedding_provider == "gemini_api":
                client_options["api_key"] = api_key
            else:
                client_options["vertexai"] = True
                if api_key:
                    client_options["api_key"] = api_key
                else:
                    client_options["project"] = self.settings.google_cloud_project
                    client_options["location"] = self.settings.google_cloud_location
            self._client = genai.Client(**client_options)
            self._types = types
        return self._client, self._types

    def _load_api_key(self) -> str | None:
        if self.settings.google_cloud_api_key is not None:
            value = self.settings.google_cloud_api_key.get_secret_value().strip()
            if value:
                return value

        if not self.settings.google_cloud_api_key_file:
            return None
        path = Path(self.settings.google_cloud_api_key_file).expanduser()
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Could not read GOOGLE_CLOUD_API_KEY_FILE: {path}") from exc
        if not value:
            raise RuntimeError(f"GOOGLE_CLOUD_API_KEY_FILE is empty: {path}")
        return value

    def _embed_contents(self, contents: list[Any]) -> list[list[float]]:
        if not contents:
            return []

        client, types = self._get_client()
        response = client.models.embed_content(
            model=self.settings.vertex_embedding_model_name,
            contents=contents,
            config=types.EmbedContentConfig(
                output_dimensionality=self.settings.embedding_output_dimensionality,
            ),
        )
        embeddings = response.embeddings or []
        if len(embeddings) != len(contents):
            raise RuntimeError(
                "Vertex AI returned an unexpected number of embeddings: "
                f"expected={len(contents)} actual={len(embeddings)}"
            )

        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = embedding.values
            if values is None:
                raise RuntimeError("Vertex AI returned an embedding without values")
            vector = [float(value) for value in values]
            if len(vector) != self.settings.embedding_output_dimensionality:
                raise RuntimeError(
                    "Vertex AI embedding dimension does not match configuration: "
                    f"expected={self.settings.embedding_output_dimensionality} actual={len(vector)}"
                )
            vectors.append(vector)
        return vectors


@dataclass
class VertexGeminiTextEmbeddingService(_VertexGeminiEmbeddingBase):
    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(
            [f"title: none | text: {text}" for text in texts]
        )

    def embed_query(self, text: str) -> list[float]:
        return self._embed_texts([f"task: search result | query: {text}"])[0]

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        _, types = self._get_client()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.settings.embedding_batch_size):
            batch = texts[start : start + self.settings.embedding_batch_size]
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=text)],
                )
                for text in batch
            ]
            vectors.extend(self._embed_contents(contents))
        return vectors


@dataclass
class VertexGeminiImageEmbeddingService(_VertexGeminiEmbeddingBase):
    def embed_image(self, image: Image.Image) -> list[float]:
        return self.embed_batch([image])[0]

    def embed_batch(self, images: list[Image.Image]) -> list[list[float]]:
        if not images:
            return []
        _, types = self._get_client()
        vectors: list[list[float]] = []
        batch_size = min(self.settings.embedding_batch_size, 6)
        for start in range(0, len(images), batch_size):
            batch = images[start : start + batch_size]
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=_png_bytes(image),
                            mime_type="image/png",
                        )
                    ],
                )
                for image in batch
            ]
            vectors.extend(self._embed_contents(contents))
        return vectors

    def embed_documents(self, images: list[Image.Image]) -> list[list[float]]:
        return self.embed_batch(images)

    def embed_queries(self, images: list[Image.Image]) -> list[list[float]]:
        return self.embed_batch(images)


def _png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
