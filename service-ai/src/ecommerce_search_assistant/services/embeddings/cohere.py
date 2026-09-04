from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Literal

from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings


_COHERE_MAX_BATCH_SIZE = 96


@dataclass
class _CohereEmbeddingBase:
    settings: Settings = field(default_factory=get_settings)
    _client: Any | None = field(default=None, init=False, repr=False)

    def warmup(self) -> None:
        # Client creation validates local API-key configuration without consuming
        # a trial request. The first embedding call validates model access.
        self._get_client()

    def is_ready(self) -> bool:
        return self._client is not None

    def _get_client(self) -> Any:
        if self._client is None:
            if self.settings.cohere_api_key is None:
                raise RuntimeError("COHERE_API_KEY is required when EMBEDDING_PROVIDER=cohere")
            api_key = self.settings.cohere_api_key.get_secret_value().strip()
            if not api_key:
                raise RuntimeError("COHERE_API_KEY is empty")

            import cohere

            self._client = cohere.ClientV2(api_key=api_key)
        return self._client

    def _validate_vectors(self, vectors: Any, *, expected_count: int) -> list[list[float]]:
        if not isinstance(vectors, list) or len(vectors) != expected_count:
            actual_count = len(vectors) if isinstance(vectors, list) else 0
            raise RuntimeError(
                "Cohere returned an unexpected number of embeddings: "
                f"expected={expected_count} actual={actual_count}"
            )

        validated: list[list[float]] = []
        for raw_vector in vectors:
            vector = [float(value) for value in raw_vector]
            if len(vector) != self.settings.embedding_output_dimensionality:
                raise RuntimeError(
                    "Cohere embedding dimension does not match configuration: "
                    f"expected={self.settings.embedding_output_dimensionality} actual={len(vector)}"
                )
            validated.append(vector)
        return validated

    @property
    def _batch_size(self) -> int:
        return min(self.settings.embedding_batch_size, _COHERE_MAX_BATCH_SIZE)


@dataclass
class CohereTextEmbeddingService(_CohereEmbeddingBase):
    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(texts, input_type="search_document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed_texts([text], input_type="search_query")[0]

    def _embed_texts(
        self,
        texts: list[str],
        *,
        input_type: Literal["search_document", "search_query"],
    ) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            response = self._get_client().embed(
                model=self.settings.cohere_embedding_model_name,
                texts=batch,
                input_type=input_type,
                output_dimension=self.settings.embedding_output_dimensionality,
                embedding_types=["float"],
            )
            vectors.extend(self._validate_vectors(response.embeddings.float, expected_count=len(batch)))
        return vectors


@dataclass
class CohereImageEmbeddingService(_CohereEmbeddingBase):
    def embed_image(self, image: Image.Image) -> list[float]:
        return self.embed_documents([image])[0]

    def embed_batch(self, images: list[Image.Image]) -> list[list[float]]:
        return self.embed_documents(images)

    def embed_documents(self, images: list[Image.Image]) -> list[list[float]]:
        return self._embed_images(images, input_type="search_document")

    def embed_queries(self, images: list[Image.Image]) -> list[list[float]]:
        return self._embed_images(images, input_type="search_query")

    def _embed_images(
        self,
        images: list[Image.Image],
        *,
        input_type: Literal["search_document", "search_query"],
    ) -> list[list[float]]:
        if not images:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(images), self._batch_size):
            batch = images[start : start + self._batch_size]
            inputs = [
                {
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": _jpeg_data_uri(image)},
                        }
                    ]
                }
                for image in batch
            ]
            response = self._get_client().embed(
                model=self.settings.cohere_embedding_model_name,
                inputs=inputs,
                input_type=input_type,
                output_dimension=self.settings.embedding_output_dimensionality,
                embedding_types=["float"],
            )
            vectors.extend(self._validate_vectors(response.embeddings.float, expected_count=len(batch)))
        return vectors


def _jpeg_data_uri(image: Image.Image) -> str:
    source = image.convert("RGB")
    buffer = BytesIO()
    source.save(buffer, format="JPEG", quality=85, optimize=True)
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
