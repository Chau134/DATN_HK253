from __future__ import annotations

from base64 import b64encode
from collections import OrderedDict
from dataclasses import dataclass, field
from io import BytesIO
import json
import os
from threading import Lock, RLock
from time import monotonic, sleep
from typing import Any, Literal

from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings


_COHERE_MAX_BATCH_SIZE = 96
_REQUEST_RATE_LOCK = Lock()
_NEXT_REQUEST_AT = 0.0
_THROTTLE_ERROR_CODES = {"ThrottlingException", "TooManyRequestsException"}


def _normalize_bedrock_bearer_token() -> None:
    variable = "AWS_BEARER_TOKEN_BEDROCK"
    token = os.environ.get(variable)
    if token is not None:
        normalized = token.strip()
        if normalized:
            os.environ[variable] = normalized
        else:
            os.environ.pop(variable, None)


@dataclass
class _BedrockCohereEmbeddingBase:
    settings: Settings = field(default_factory=get_settings)
    _client: Any | None = field(default=None, init=False, repr=False)
    _runtime_ready: bool = field(default=False, init=False, repr=False)

    def warmup(self) -> None:
        raise NotImplementedError

    def is_ready(self) -> bool:
        return self._runtime_ready

    def _get_client(self) -> Any:
        if self._client is None:
            _normalize_bedrock_bearer_token()

            import boto3
            from botocore.config import Config

            kwargs: dict[str, Any] = {
                "region_name": self.settings.bedrock_region,
                "config": Config(
                    connect_timeout=self.settings.bedrock_timeout_seconds,
                    read_timeout=self.settings.bedrock_timeout_seconds,
                    retries={
                        "max_attempts": self.settings.bedrock_retry_attempts,
                        "mode": "standard",
                    },
                ),
            }
            if self.settings.bedrock_endpoint_url:
                kwargs["endpoint_url"] = self.settings.bedrock_endpoint_url
            self._client = boto3.client("bedrock-runtime", **kwargs)
        return self._client

    def _invoke(self, body: dict[str, Any], *, expected_count: int) -> list[list[float]]:
        self._runtime_ready = False
        try:
            from botocore.exceptions import ClientError
        except ModuleNotFoundError:  # Allows injected/fake clients in minimal test environments.
            class ClientError(Exception):
                pass

        response = None
        for attempt in range(self.settings.bedrock_embedding_throttle_retry_attempts + 1):
            _wait_for_request_slot(
                self.settings.bedrock_embedding_min_request_interval_seconds
            )
            try:
                response = self._get_client().invoke_model(
                    modelId=self.settings.bedrock_embedding_model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body),
                )
                break
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                if (
                    error_code not in _THROTTLE_ERROR_CODES
                    or attempt >= self.settings.bedrock_embedding_throttle_retry_attempts
                ):
                    raise
                delay = min(
                    self.settings.bedrock_embedding_throttle_backoff_seconds * (2**attempt),
                    self.settings.bedrock_embedding_throttle_max_backoff_seconds,
                )
                sleep(delay)

        if response is None:  # pragma: no cover - defensive; loop either returns or raises.
            raise RuntimeError("Bedrock Cohere embedding request did not return a response")
        payload = json.loads(response["body"].read())
        embeddings = payload.get("embeddings", {})
        raw_vectors = embeddings.get("float") if isinstance(embeddings, dict) else None
        if not isinstance(raw_vectors, list) or len(raw_vectors) != expected_count:
            actual_count = len(raw_vectors) if isinstance(raw_vectors, list) else 0
            raise RuntimeError(
                "Bedrock Cohere returned an unexpected number of embeddings: "
                f"expected={expected_count} actual={actual_count}"
            )

        vectors: list[list[float]] = []
        for raw_vector in raw_vectors:
            vector = [float(value) for value in raw_vector]
            if len(vector) != self.settings.embedding_output_dimensionality:
                raise RuntimeError(
                    "Bedrock Cohere embedding dimension does not match configuration: "
                    f"expected={self.settings.embedding_output_dimensionality} "
                    f"actual={len(vector)}"
                )
            vectors.append(vector)
        self._runtime_ready = True
        return vectors

    @property
    def _batch_size(self) -> int:
        return min(self.settings.embedding_batch_size, _COHERE_MAX_BATCH_SIZE)


@dataclass
class BedrockCohereTextEmbeddingService(_BedrockCohereEmbeddingBase):
    _query_cache: OrderedDict[str, tuple[float, list[float]]] = field(
        default_factory=OrderedDict,
        init=False,
        repr=False,
    )
    _query_cache_lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def warmup(self) -> None:
        self.embed_query("catalog search readiness probe")

    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(texts, input_type="search_document")

    def embed_query(self, text: str) -> list[float]:
        cache_size = self.settings.text_query_embedding_cache_size
        cache_ttl = self.settings.text_query_embedding_cache_ttl_seconds
        key = " ".join(text.casefold().split())
        now = monotonic()
        if cache_size and cache_ttl:
            with self._query_cache_lock:
                cached = self._query_cache.get(key)
                if cached is not None and cached[0] > now:
                    self._query_cache.move_to_end(key)
                    return list(cached[1])
                if cached is not None:
                    self._query_cache.pop(key, None)

        vector = self._embed_texts([text], input_type="search_query")[0]
        if cache_size and cache_ttl:
            with self._query_cache_lock:
                self._query_cache[key] = (monotonic() + cache_ttl, list(vector))
                self._query_cache.move_to_end(key)
                while len(self._query_cache) > cache_size:
                    self._query_cache.popitem(last=False)
        return vector

    def _embed_texts(
        self,
        texts: list[str],
        *,
        input_type: Literal["search_document", "search_query"],
    ) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            vectors.extend(
                self._invoke(
                    {
                        "texts": batch,
                        "input_type": input_type,
                        "embedding_types": ["float"],
                        "output_dimension": self.settings.embedding_output_dimensionality,
                        "truncate": "RIGHT",
                    },
                    expected_count=len(batch),
                )
            )
        return vectors


@dataclass
class BedrockCohereImageEmbeddingService(_BedrockCohereEmbeddingBase):
    def warmup(self) -> None:
        self.embed_queries([Image.new("RGB", (8, 8), color=(127, 127, 127))])

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
        vectors: list[list[float]] = []
        for start in range(0, len(images), self._batch_size):
            batch = images[start : start + self._batch_size]
            image_data_uris = [
                _jpeg_data_uri(
                    image,
                    max_side=self.settings.bedrock_embedding_image_max_side,
                )
                for image in batch
            ]
            vectors.extend(
                self._invoke(
                    {
                        "images": image_data_uris,
                        "input_type": input_type,
                        "embedding_types": ["float"],
                        "output_dimension": self.settings.embedding_output_dimensionality,
                    },
                    expected_count=len(batch),
                )
            )
        return vectors


def _wait_for_request_slot(minimum_interval_seconds: float) -> None:
    global _NEXT_REQUEST_AT

    with _REQUEST_RATE_LOCK:
        delay = max(0.0, _NEXT_REQUEST_AT - monotonic())
        if delay:
            sleep(delay)
        _NEXT_REQUEST_AT = monotonic() + minimum_interval_seconds


def _jpeg_data_uri(image: Image.Image, *, max_side: int) -> str:
    source = image.convert("RGB")
    if max(source.size) > max_side:
        source.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    source.save(buffer, format="JPEG", quality=85, optimize=True)
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
