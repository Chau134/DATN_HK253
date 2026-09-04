from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass, field
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.infrastructure.springboot import SpringBootResult
from ecommerce_search_assistant.main import create_app
from ecommerce_search_assistant.schemas.search import SearchFilter, SearchResponse, SearchResultItem
from ecommerce_search_assistant.services.assistant.workflow import AssistantWorkflow, build_assistant_graph
from ecommerce_search_assistant.services.cropping.yolo import CropResult
from ecommerce_search_assistant.services.embeddings.mock import MockImageEmbeddingService, MockTextEmbeddingService
from ecommerce_search_assistant.services.reranking.mock import MockRerankService
from ecommerce_search_assistant.services.llm.service import QueryUnderstanding
from ecommerce_search_assistant.services.indexing.product import ProductIndexingService
from ecommerce_search_assistant.services.search.service import SearchService


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Settings:
    env_values = {
        "APP_NAME": "test-ai-ecommerce-assistant",
        "APP_ENV": "test",
        "APP_HOST": "127.0.0.1",
        "APP_PORT": "8001",
        "INTERNAL_API_KEY": "test-internal-key",
        "SPRINGBOOT_API_KEY": "test-spring-key",
        "SPRINGBOOT_BASE_URL": "http://spring.test",
        "QDRANT_TEXT_VECTOR_SIZE": "8",
        "QDRANT_IMAGE_VECTOR_SIZE": "8",
        "QDRANT_TEXT_COLLECTION": "product_text_vectors",
        "QDRANT_IMAGE_COLLECTION": "product_image_vectors",
        "EMBEDDING_PROVIDER": "local",
        "EMBEDDING_DEVICE": "cpu",
        "MAX_UPLOAD_MB": "1",
        "ALLOWED_IMAGE_MIME_TYPES": "image/png,image/jpeg",
        "SQLITE_CHECKPOINT_PATH": str(tmp_path / "checkpoints.sqlite"),
    }
    for name, value in env_values.items():
        monkeypatch.setenv(name, value)

    get_settings.cache_clear()
    resolved_settings = Settings(_env_file=None)
    yield resolved_settings
    get_settings.cache_clear()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    application = create_app(settings)
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def pil_image() -> Image.Image:
    return Image.new("RGB", (8, 8), color=(20, 40, 60))


@pytest.fixture
def image_payload(pil_image: Image.Image) -> dict[str, str]:
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    return {
        "content_type": "image/png",
        "data_base64": b64encode(buffer.getvalue()).decode("ascii"),
        "filename": "fixture.png",
    }


@dataclass
class FakeQdrantClient:
    upserts: list[dict[str, Any]] = field(default_factory=list)
    deletes: list[dict[str, Any]] = field(default_factory=list)
    queries: list[dict[str, Any]] = field(default_factory=list)

    def query_points(self, collection_name: str, **kwargs: Any) -> SimpleNamespace:
        self.queries.append({"collection_name": collection_name, **kwargs})
        if "text" in collection_name:
            candidates = (("P-TEXT", 0.93), ("P-SHARED", 0.84))
        else:
            candidates = (("P-IMAGE", 0.96), ("P-SHARED", 0.89))
        points = [
            SimpleNamespace(
                payload={
                    "product_id": product_id,
                    "embedding_text": f"document for {product_id}",
                    "category_keys": ["hoodie"],
                    "color_keys": ["black"],
                    "material_keys": ["leather"],
                    "audience_keys": ["women"],
                    "use_case_keys": ["office"],
                },
                score=score,
            )
            for product_id, score in candidates
        ]
        return SimpleNamespace(points=points)

    def scroll(self, collection_name: str, **kwargs: Any) -> tuple[list[SimpleNamespace], None]:
        self.queries.append({"collection_name": collection_name, "scroll": True, **kwargs})
        points = [
            SimpleNamespace(
                payload={
                    "category_names": ["tshirt", "hoodie", "running shoes", "jacket"],
                    "category_names_vi": ["ao thun", "ao hoodie", "ao khoac"],
                    "brand_name": "adidas",
                    "gender": "unisex",
                    "gender_vi": "unisex",
                    "base_colour": "black",
                    "base_colour_vi": "den",
                    "option_value": ["M", "L"],
                    "unified_size": ["M", "L"],
                    "selling_price": 500000,
                }
            )
        ]
        return points, None

    def upsert(self, collection_name: str, points: list[Any], wait: bool = True) -> None:
        self.upserts.append(
            {
                "collection_name": collection_name,
                "points": points,
                "wait": wait,
            }
        )

    def delete(self, collection_name: str, points_selector: Any, wait: bool = True) -> None:
        self.deletes.append(
            {
                "collection_name": collection_name,
                "points_selector": points_selector,
                "wait": wait,
            }
        )


@dataclass
class FakeYoloCropService:
    def detect_and_crop(self, image: Image.Image) -> list[CropResult]:
        width, height = image.size
        return [
            CropResult(
                image=image.copy(),
                bbox=(0, 0, width, height),
                confidence=0.9,
                class_id=0,
                is_fallback=False,
            )
        ]


@dataclass
class FakeImageLoader:
    image: Image.Image

    def load_from_url(self, _: str) -> Image.Image:
        return self.image.copy()


class FakeLlmService:
    def __init__(self) -> None:
        self.analyze_calls: list[tuple[str, str]] = []
        self.conversation_contexts: list[str | None] = []
        self.reply_contexts: list[str | None] = []

    def analyze_user_query(
        self,
        message: str,
        locale: str = "vi-VN",
        conversation_context: str | None = None,
    ) -> QueryUnderstanding:
        self.analyze_calls.append((message, locale))
        self.conversation_contexts.append(conversation_context)
        normalized = message.lower()
        colors = ["white"] if "white" in normalized or "trắng" in normalized else None
        return QueryUnderstanding(
            intent="search_product",
            rewritten_query=f"rewritten {message}",
            filters=SearchFilter(colors=colors),
            needs_image_search=False,
            needs_text_search=True,
            clarifying_question=None,
        )

    def generate_assistant_reply(
        self,
        message: str,
        search_results: list[SearchResultItem],
        product_context: list[dict[str, Any]],
        conversation_context: str | None = None,
        is_reference_followup: bool = False,
    ) -> str:
        del message, product_context, is_reference_followup
        self.reply_contexts.append(conversation_context)
        if not search_results:
            return "need more context"
        return f"assistant reply for {search_results[0].product_id}"


@dataclass
class FakeSpringBootClient:
    product_calls: list[list[str]] = field(default_factory=list)

    def get_products_by_ids(self, product_ids: list[str]) -> SpringBootResult[list[dict[str, Any]]]:
        self.product_calls.append(list(product_ids))
        return SpringBootResult(
            data=[{"product_id": product_id, "title": f"Product {product_id}"} for product_id in product_ids]
        )

class FakeAssistantSearchService:
    def search_text(self, _: Any) -> SearchResponse:
        return self._response("text")

    def search_image(self, _: Any) -> SearchResponse:
        return self._response("image")

    def search_hybrid(self, _: Any) -> SearchResponse:
        return self._response("hybrid")

    @staticmethod
    def _response(source: str) -> SearchResponse:
        results = [
            SearchResultItem(product_id="P-CHAT-1", score=0.95, source=source),
            SearchResultItem(product_id="P-CHAT-2", score=0.87, source=source),
        ]
        return SearchResponse(
            rewritten_query="rewritten assistant query",
            filters=None,
            product_ids=[result.product_id for result in results],
            results=results,
        )


@pytest.fixture
def fake_qdrant_client() -> FakeQdrantClient:
    return FakeQdrantClient()


@pytest.fixture
def fake_llm_service() -> FakeLlmService:
    return FakeLlmService()


@pytest.fixture
def search_service(
    settings: Settings,
    fake_qdrant_client: FakeQdrantClient,
    fake_llm_service: FakeLlmService,
) -> SearchService:
    return SearchService(
        settings=settings,
        qdrant_client=fake_qdrant_client,  # type: ignore[arg-type]
        text_embedding_service=MockTextEmbeddingService(dimensions=8),
        image_embedding_service=MockImageEmbeddingService(dimensions=8),
        yolo_crop_service=FakeYoloCropService(),  # type: ignore[arg-type]
        llm_service=fake_llm_service,  # type: ignore[arg-type]
        rerank_service=MockRerankService(),  # type: ignore[arg-type]
    )


@pytest.fixture
def indexing_service(
    settings: Settings,
    fake_qdrant_client: FakeQdrantClient,
    pil_image: Image.Image,
) -> ProductIndexingService:
    return ProductIndexingService(
        settings=settings,
        qdrant_client=fake_qdrant_client,  # type: ignore[arg-type]
        text_embedding_service=MockTextEmbeddingService(dimensions=8),
        image_embedding_service=MockImageEmbeddingService(dimensions=8),
        yolo_crop_service=FakeYoloCropService(),  # type: ignore[arg-type]
        image_loader=FakeImageLoader(pil_image),  # type: ignore[arg-type]
    )


@pytest.fixture
def fake_springboot_client() -> FakeSpringBootClient:
    return FakeSpringBootClient()


@pytest.fixture
def assistant_workflow(
    fake_llm_service: FakeLlmService,
    fake_springboot_client: FakeSpringBootClient,
) -> AssistantWorkflow:
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=fake_llm_service,  # type: ignore[arg-type]
        search_service=FakeAssistantSearchService(),  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,  # type: ignore[arg-type]
    )
    return AssistantWorkflow(graph=graph)
