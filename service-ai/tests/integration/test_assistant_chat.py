from concurrent.futures import ThreadPoolExecutor
import sqlite3
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from ecommerce_search_assistant.schemas.chat import ChatRequest
from ecommerce_search_assistant.schemas.search import SearchFilter, SearchResponse, SearchResultItem
from ecommerce_search_assistant.services.assistant.factory import get_assistant_workflow
from ecommerce_search_assistant.infrastructure.springboot import SpringBootResult
from ecommerce_search_assistant.services.assistant.workflow import (
    AssistantWorkflow,
    _detect_answer_target,
    _extend_conversation_summary,
    _extract_exact_product_query,
    _filter_context_by_requested_color_shade,
    _is_filter_refinement,
    _apply_cheaper_price_ceiling,
    _contextual_filters,
    _remove_inherited_llm_refinement_filters,
    _route_intent_node,
    _structured_catalog_reply,
    _validated_referenced_product_ids,
    build_assistant_graph,
)
from ecommerce_search_assistant.services.search.service import CatalogCategoryCount


def test_llm_no_rag_evaluation_variant_bypasses_retrieval_routes() -> None:
    state = {"shop_knowledge_topic": "shipping", "intent": "product_search"}

    assert _route_intent_node("llm_no_rag")(state) == {"route": "non_product_answer"}
    assert _route_intent_node("rag")(state) == {"route": "shop_knowledge_answer"}


def test_structured_catalog_reply_uses_grounded_fields_for_factual_and_comparison() -> None:
    left = {
        "id": 1,
        "title_vi": "Áo đen",
        "base_colour_vi": "Đen",
        "material_vi": "Cotton",
        "gender_vi": "Nữ",
        "categories": [{"name_vi": "Áo thun"}],
    }
    right = {
        "id": 2,
        "title_vi": "Áo trắng",
        "base_colour_vi": "Trắng",
        "material_vi": "Linen",
        "gender_vi": "Nữ",
        "categories": [{"name_vi": "Áo sơ mi"}],
    }

    factual = _structured_catalog_reply(
        {"message": "Áo đen làm từ chất liệu gì?", "product_context": [left]}
    )
    comparison = _structured_catalog_reply(
        {
            "message": "So sánh hai áo",
            "catalog_title_queries": ["ao den", "ao trang"],
            "product_context": [left, right],
        }
    )

    assert factual == "Áo đen được làm từ chất liệu Cotton."
    assert comparison is not None
    assert "Áo đen" in comparison and "Áo trắng" in comparison
    assert "Cotton" in comparison and "Linen" in comparison
    assert "Điểm giống:" in comparison
    assert "Điểm khác:" in comparison


def test_structured_catalog_reply_compares_referenced_products_and_recommends() -> None:
    left = {
        "product_id": "263",
        "title_vi": "Áo sơ mi trắng ngà và đen",
        "base_colour": "Ecru / Black",
        "base_colour_vi": "Trắng ngà / Đen",
        "material_vi": "82% Viscose, 18% Polyamide",
        "gender_vi": "Nữ",
        "categories": [{"name_vi": "Áo sơ mi"}],
        "price": {"price": 999000},
    }
    right = {
        "product_id": "262",
        "title_vi": "Áo sơ mi đen",
        "base_colour": "Black",
        "base_colour_vi": "Đen",
        "material_vi": "82% Viscose, 18% Polyamide",
        "gender_vi": "Nữ",
        "categories": [{"name_vi": "Áo sơ mi"}],
        "price": {"price": 699000},
    }

    reply = _structured_catalog_reply(
        {
            "message": (
                "Trong các mẫu vừa rồi, hãy so sánh hai mẫu đầu tiên và "
                "gợi ý mẫu phù hợp hơn để đi làm."
            ),
            "intent": "compare_products",
            "referenced_product_ids": ["263", "262"],
            "conversation_memory": {
                "active_constraints": {"colors": ["black"]}
            },
            "product_context": [left, right],
        }
    )

    assert reply is not None
    assert "So sánh" in reply
    assert "Áo sơ mi trắng ngà và đen" in reply
    assert "Áo sơ mi đen" in reply
    assert "999.000 VND" in reply and "699.000 VND" in reply
    assert "Gợi ý: chọn Áo sơ mi đen để đi làm" in reply
    assert "khớp sát hơn với ưu tiên màu hiện tại" in reply
    assert "thấp hơn" in reply


def test_structured_catalog_reply_answers_price_and_variant_stock() -> None:
    product = {
        "id": 1035,
        "title_vi": "Bodysuit màu đen",
        "price": {
            "price": 599000,
            "discounted_price": 579000,
            "effective_price": 579000,
        },
        "variants": [
            {
                "option_value": "M",
                "unified_size": "M",
                "inventory_count": 50,
                "available": True,
                "active": True,
            }
        ],
    }

    price = _structured_catalog_reply(
        {"answer_target": "price", "product_context": [product]}
    )
    stock = _structured_catalog_reply(
        {
            "answer_target": "availability",
            "message": "Bodysuit màu đen size M còn hàng không?",
            "filters": {"sizes": ["m"]},
            "product_context": [product],
        }
    )

    assert price == (
        "Giá hiện tại của Bodysuit màu đen là 579.000 VND. "
        "Giá gốc là 599.000 VND."
    )
    assert stock == "Có, Bodysuit màu đen size M hiện còn hàng."


def test_structured_catalog_reply_refuses_missing_product_before_suggestions() -> None:
    reply = _structured_catalog_reply(
        {
            "answer_target": "exact_product",
            "exact_product_code": "MC-999999",
            "exact_match_resolved": False,
            "product_context": [
                {"id": 677, "title_vi": "Đầm midi màu khaki"},
            ],
        }
    )

    assert reply is not None
    assert reply.startswith("Không, shop không tìm thấy “MC-999999”")
    assert "sản phẩm tương tự" in reply
    assert reply.index("không tìm thấy") < reply.index("sản phẩm tương tự")


def test_cheaper_refinement_keeps_previous_constraints_and_adds_strict_ceiling() -> None:
    previous = SearchFilter(category="dress", colors=["red", "white"])
    current_llm = SearchFilter(category="dress")
    cleaned = _remove_inherited_llm_refinement_filters(
        message="rẻ hơn nữa có không?",
        llm_filters=current_llm,
        rule_filters=None,
    )
    contextual = _contextual_filters(
        message="rẻ hơn nữa có không?",
        current=cleaned or SearchFilter(),
        previous=previous,
    )
    refined = _apply_cheaper_price_ceiling(
        message="rẻ hơn nữa có không?",
        filters=contextual,
        previous_context=[
            {"price": {"effective_price": 579000}},
            {"price": {"effective_price": 779000}},
        ],
    )

    assert refined is not None
    assert refined.category == "dress"
    assert refined.colors == ["red", "white"]
    assert refined.max_price == 578999


def test_cheaper_structured_reply_displays_grounded_prices() -> None:
    reply = _structured_catalog_reply(
        {
            "message": "rẻ hơn nữa có không?",
            "product_context": [
                {
                    "title_vi": "Đầm đen",
                    "base_colour_vi": "Đen",
                    "material_vi": "Cotton",
                    "gender_vi": "Nữ",
                    "categories": [{"name_vi": "Váy & Đầm"}],
                    "price": {"effective_price": 479000},
                }
            ],
        }
    )

    assert reply is not None
    assert "479.000 VND" in reply


def test_exact_product_query_extraction_preserves_catalog_entity() -> None:
    assert _extract_exact_product_query(
        "Sản phẩm Đầm mini phồng màu đen gấu bo chun hiện có giá bao nhiêu?",
        answer_target="price",
    ) == "Đầm mini phồng màu đen gấu bo chun"
    assert _extract_exact_product_query(
        "Đầm mini phồng màu đen gấu bo chun size S còn hàng không?",
        answer_target="availability",
    ) == "Đầm mini phồng màu đen gấu bo chun"


def test_catalog_existence_query_returns_affirmative_reply_for_matching_products() -> None:
    message = "Có bán áo sơ mi màu đen không?"

    assert _detect_answer_target(message) is None
    assert _detect_answer_target("Shop có bán mã MC-999999 không?") == "exact_product"
    reply = _structured_catalog_reply(
        {
            "message": message,
            "product_context": [
                {
                    "id": 23,
                    "title_vi": "Áo sơ mi màu đen safari dáng rủ rút eo",
                    "base_colour_vi": "Đen",
                }
            ],
        }
    )

    assert reply is not None
    assert reply.startswith("Có, shop có các sản phẩm phù hợp")
    assert "không tìm thấy" not in reply.casefold()


def test_complete_first_turn_availability_query_is_not_filter_refinement() -> None:
    assert not _is_filter_refinement(
        "Bodysuit màu đen cổ tim size M còn hàng không?",
        SearchFilter(category="bodysuit", colors=["black"], sizes=["m"]),
    )
    assert _is_filter_refinement(
        "Còn màu đỏ thì sao?",
        SearchFilter(colors=["red"]),
    )
    assert _is_filter_refinement(
        "Giữ các yêu cầu trên nhưng ưu tiên màu đen.",
        SearchFilter(colors=["black"]),
    )


def test_specific_color_shade_context_does_not_include_broad_family() -> None:
    context = [
        {"id": 1, "base_colour": "Wine", "base_colour_vi": "Đỏ rượu vang"},
        {"id": 2, "base_colour": "Red", "base_colour_vi": "Đỏ"},
    ]

    assert _filter_context_by_requested_color_shade(
        "Tôi cần Váy & Đầm màu Đỏ rượu vang cho Nữ",
        context,
    ) == [context[0]]
    assert _filter_context_by_requested_color_shade(
        "Tôi cần Váy & Đầm màu Đỏ cho Nữ",
        context,
    ) == context


def test_single_sand_color_does_not_trigger_sand_black_filter() -> None:
    context = [
        {"id": 1, "base_colour": "Sand", "base_colour_vi": "Màu cát"},
    ]

    assert _filter_context_by_requested_color_shade(
        "Sản phẩm Đầm sơ mi mini màu cát hiện có giá bao nhiêu?",
        context,
    ) == context

    combined = [
        {"id": 1, "base_colour": "Sand / Black", "base_colour_vi": "Màu cát / Đen"},
        {"id": 2, "base_colour": "Black", "base_colour_vi": "Đen"},
    ]
    assert _filter_context_by_requested_color_shade(
        "Tìm Áo kiểu màu Màu cát / Đen",
        combined,
    ) == [combined[0]]


from ecommerce_search_assistant.services.assistant.preferences import InMemoryUserPreferenceStore
from ecommerce_search_assistant.services.llm.service import QueryUnderstanding
from ecommerce_search_assistant.services.llm.service import BaseLlmService


class FakeAssistantSearchService:
    def search_text(self, request):
        del request
        return self._response("text")

    def search_image(self, request):
        del request
        return self._response("image")

    def search_hybrid(self, request):
        del request
        return self._response("hybrid")

    @staticmethod
    def _response(source: str) -> SearchResponse:
        results = [
            SearchResultItem(product_id="P-CHAT-1", score=0.95, source=source),
            SearchResultItem(product_id="P-CHAT-2", score=0.87, source=source),
        ]
        return SearchResponse(
            rewritten_query="rewritten assistant query",
            product_ids=[result.product_id for result in results],
            results=results,
        )


class FailingSpringBootClient:
    def get_products_by_ids(self, product_ids):
        del product_ids
        raise RuntimeError("spring boot down")

class RecordingAssistantSearchService:
    def __init__(self) -> None:
        self.text_requests: list[Any] = []
        self.image_requests: list[Any] = []
        self.hybrid_requests: list[Any] = []
        self.prepared_text_requests: list[dict[str, Any]] = []

    @staticmethod
    def catalog_category_counts() -> list[CatalogCategoryCount]:
        return [
            CatalogCategoryCount(code="dress", name_vi="Váy & đầm", count=192),
            CatalogCategoryCount(code="blouse_top", name_vi="Áo kiểu", count=154),
            CatalogCategoryCount(code="t-shirt", name_vi="Áo thun", count=153),
        ]

    def search_text(self, request):
        self.text_requests.append(request)
        return self._response("text", filters=request.filters)

    def search_text_prepared(
        self,
        *,
        rewritten_query: str,
        filters: SearchFilter | None,
        top_k: int | None = None,
        embedding_query: str | None = None,
        constraints: Any = None,
    ):
        self.prepared_text_requests.append(
            {
                "rewritten_query": rewritten_query,
                "filters": filters,
                "top_k": top_k,
                "embedding_query": embedding_query,
                "constraints": constraints,
            }
        )
        return self._response("text", filters=filters), {}

    def search_image(self, request):
        self.image_requests.append(request)
        return self._response("image", filters=request.filters)

    def search_hybrid(self, request):
        self.hybrid_requests.append(request)
        return self._response("hybrid", filters=request.filters)

    def search_hybrid_prepared(
        self,
        *,
        rewritten_query: str | None,
        original_query: str | None = None,
        image: Any,
        crop_box: Any,
        filters: SearchFilter | None,
        top_k: int | None = None,
        constraints: Any = None,
    ):
        self.hybrid_requests.append(
            {
                "rewritten_query": rewritten_query,
                "original_query": original_query,
                "image": image,
                "crop_box": crop_box,
                "top_k": top_k,
                "constraints": constraints,
            }
        )
        return self._response("hybrid", filters=filters)

    @staticmethod
    def _response(source: str, filters: SearchFilter | None = None) -> SearchResponse:
        results = [SearchResultItem(product_id="P-CHAT-1", score=0.95, source=source)]
        return SearchResponse(
            rewritten_query="rewritten assistant query",
            filters=filters,
            product_ids=[result.product_id for result in results],
            results=results,
        )


class EmptyRecordingAssistantSearchService(RecordingAssistantSearchService):
    @staticmethod
    def _response(source: str, filters: SearchFilter | None = None) -> SearchResponse:
        return SearchResponse(
            rewritten_query="rewritten assistant query",
            filters=filters,
            product_ids=[],
            results=[],
        )


class ComparisonRecordingSearchService(RecordingAssistantSearchService):
    def search_text_prepared(
        self,
        *,
        rewritten_query: str,
        filters: SearchFilter | None,
        top_k: int | None = None,
        embedding_query: str | None = None,
        constraints: Any = None,
    ):
        self.prepared_text_requests.append(
            {
                "rewritten_query": rewritten_query,
                "filters": filters,
                "top_k": top_k,
                "embedding_query": embedding_query,
                "constraints": constraints,
            }
        )
        product_id = (
            "P-CHAT-1" if "hoodie the thao" in (embedding_query or "") else "P-CHAT-2"
        )
        result = SearchResultItem(product_id=product_id, score=0.99, source="text")
        return (
            SearchResponse(
                rewritten_query=rewritten_query,
                product_ids=[product_id],
                results=[result],
            ),
            {},
        )


class FilterAwareLlmService:
    def analyze_user_query(
        self,
        message: str,
        locale: str = "vi-VN",
        conversation_context: str | None = None,
    ) -> QueryUnderstanding:
        del locale, conversation_context
        normalized = message.lower()
        category = "hoodie" if "hoodie" in normalized else None
        colors = None
        if "cream" in normalized or "kem" in normalized:
            colors = ["cream"]
        if "black" in normalized or "đen" in normalized:
            colors = ["black"]
        if "blue" in normalized or "xanh" in normalized:
            colors = ["blue"]
        max_price = 700000 if "700k" in normalized else None
        return QueryUnderstanding(
            intent="search_product",
            rewritten_query=f"rewritten {message}",
            filters=SearchFilter(category=category, colors=colors, max_price=max_price),
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
        del message, product_context, conversation_context, is_reference_followup
        if not search_results:
            return "need more context"
        return f"assistant reply for {search_results[0].product_id}"


class RecordingConversationLlmService(BaseLlmService):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.conversation_calls: list[tuple[str, str | None]] = []

    def generate_conversational_reply(
        self,
        message: str,
        conversation_context: str | None = None,
    ) -> str:
        self.conversation_calls.append((message, conversation_context))
        return f"social reply: {message}"


class PreferenceRecordingLlmService(FilterAwareLlmService):
    def __init__(self) -> None:
        self.analysis_contexts: list[str | None] = []

    def analyze_user_query(
        self,
        message: str,
        locale: str = "vi-VN",
        conversation_context: str | None = None,
    ) -> QueryUnderstanding:
        self.analysis_contexts.append(conversation_context)
        return super().analyze_user_query(message, locale, conversation_context)


def test_assistant_chat_handles_small_talk_without_product_search(
    app: FastAPI,
    client: TestClient,
    settings,
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    llm_service = RecordingConversationLlmService(settings=settings)
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=llm_service,
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-small-talk",
            "user_id": "user-1",
            "message": "hello",
            "locale": "vi-VN",
        },
    )
    second_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-small-talk",
            "user_id": "user-1",
            "message": "cảm ơn bạn",
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["message"] == "social reply: hello"
    assert first_response.json()["product_ids"] == []
    assert second_response.status_code == 200
    assert second_response.json()["message"] == "social reply: cảm ơn bạn"
    assert "user: hello" in (llm_service.conversation_calls[1][1] or "")
    assert "assistant: social reply: hello" in (llm_service.conversation_calls[1][1] or "")
    assert search_service.text_requests == []
    assert search_service.image_requests == []
    assert search_service.hybrid_requests == []
    assert fake_springboot_client.product_calls == []


def test_assistant_chat_forces_quoted_product_factual_question_through_search(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    class GeneralQuestionLlm(FilterAwareLlmService):
        def analyze_user_query(self, message, locale="vi-VN", conversation_context=None):
            del locale, conversation_context
            return QueryUnderstanding(
                intent="general_question",
                rewritten_query=message,
                filters=SearchFilter(),
                needs_image_search=False,
                needs_text_search=False,
                clarifying_question=None,
            )

    class ResolvingSearchService(RecordingAssistantSearchService):
        def resolve_catalog_title_ids(self, titles):
            return {title: ["P-CHAT-1"] for title in titles}

    search_service = ResolvingSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=GeneralQuestionLlm(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-factual-title",
            "user_id": "user-1",
            "message": 'Sản phẩm "áo hoodie thể thao nam" có chất liệu gì?',
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    assert response.json()["product_ids"][0]["product_id"] == "P-CHAT-1"
    assert search_service.prepared_text_requests == []


def test_assistant_chat_retrieves_each_quoted_comparison_leg_independently(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    search_service = ComparisonRecordingSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-comparison",
            "user_id": "user-1",
            "message": (
                'So sánh "áo hoodie thể thao nam" và '
                '"áo sơ mi satin hoa nữ".'
            ),
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    assert [item["product_id"] for item in response.json()["product_ids"]] == [
        "P-CHAT-1",
        "P-CHAT-2",
    ]
    assert [
        request["embedding_query"]
        for request in search_service.prepared_text_requests
    ] == [
        "ao hoodie the thao nam",
        "ao so mi satin hoa nu",
    ]
    assert all(request["filters"] is None for request in search_service.prepared_text_requests)


def test_assistant_chat_resolves_each_unquoted_comparison_title_exactly(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    class ResolvingComparisonSearchService(RecordingAssistantSearchService):
        def resolve_catalog_title_ids(self, titles):
            mapping = {
                "bodysuit om mau nau co v khong tay": ["P-CHAT-1"],
                "quan dai ong suong mau nau chon lung vua": ["P-CHAT-2"],
            }
            return {title: mapping.get(title, []) for title in titles}

    search_service = ResolvingComparisonSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-comparison-unquoted",
            "user_id": "user-1",
            "message": (
                "So sánh Bodysuit ôm màu nâu cổ V không tay và "
                "Quần dài ống suông màu nâu chồn lưng vừa."
            ),
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    assert [item["product_id"] for item in response.json()["product_ids"]] == [
        "P-CHAT-1",
        "P-CHAT-2",
    ]
    assert search_service.prepared_text_requests == []


def test_assistant_chat_reserves_direct_resolution_slot_for_each_comparison_leg(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    class DirectComparisonSearchService(RecordingAssistantSearchService):
        def resolve_catalog_title_ids(self, titles):
            return {
                titles[0]: ["P-CHAT-1", "duplicate-1", "duplicate-2", "duplicate-3"],
                titles[1]: ["P-CHAT-2"],
            }

    search_service = DirectComparisonSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-comparison-direct-resolution",
            "user_id": "user-1",
            "message": (
                'So sánh "áo hoodie thể thao nam" và '
                '"áo sơ mi satin hoa nữ".'
            ),
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    returned_ids = [
        item["product_id"] for item in response.json()["product_ids"]
    ]
    assert returned_ids[:2] == ["P-CHAT-1", "P-CHAT-2"]
    assert len(returned_ids) == 3
    assert search_service.prepared_text_requests == []


def test_assistant_chat_does_not_generate_comparison_when_one_leg_is_missing(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    class MissingLegSearchService(ComparisonRecordingSearchService):
        def search_text_prepared(self, **kwargs):
            if "satin" in (kwargs.get("embedding_query") or ""):
                self.prepared_text_requests.append(kwargs)
                return SearchResponse(product_ids=[], results=[]), {}
            return super().search_text_prepared(**kwargs)

    search_service = MissingLegSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-comparison-missing-leg",
            "user_id": "user-1",
            "message": (
                'So sánh "áo hoodie thể thao nam" và '
                '"áo sơ mi satin hoa nữ".'
            ),
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    assert [item["product_id"] for item in response.json()["product_ids"]] == [
        "P-CHAT-1"
    ]
    assert "chưa lấy đủ dữ liệu" in response.json()["message"]
    assert response.json()["warnings"] == ["comparison_leg_unresolved"]


def test_assistant_chat_blocks_out_of_catalog_before_retrieval(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    for index, message in enumerate(
        (
            "Tìm giúp tôi tủ lạnh side-by-side 600 lít.",
            "Tôi cần thuốc kháng sinh điều trị viêm phổi.",
            "Gợi ý laptop gaming RTX 5090 giá rẻ.",
            "Có bán vé máy bay đi Tokyo ngày mai không?",
            "Tìm xe máy điện chạy được 300 km.",
        ),
        start=1,
    ):
        response = client.post(
            "/assistant/chat",
            json={
                "session_id": f"chat-thread-out-of-catalog-{index}",
                "user_id": "user-1",
                "message": message,
                "locale": "vi-VN",
            },
        )
        assert response.status_code == 200
        assert response.json()["product_ids"] == []
        assert "thời trang" in response.json()["message"]
        assert response.json().get("warnings") is None

    assert search_service.prepared_text_requests == []
    assert search_service.text_requests == []
    assert fake_springboot_client.product_calls == []


def test_assistant_chat_answers_published_shop_info_and_refuses_unknown_claims(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    published_questions = (
        ("Chào bạn, shop mình có tên gì nhỉ?", "Mystery Closet"),
        (
            "shop hiện tại có tên là gì? cho tôi vị trí của shop được không?",
            "260 Lý Thường Kiệt",
        ),
        (
            "shop hiện tại đang bán những loại sản phẩm nào?",
            "Áo kiểu (154)",
        ),
        ("Đơn hàng được giao trong bao lâu?", "1-2 ngày"),
        ("Tôi có thể đổi trả sản phẩm trong mấy ngày?", "07 ngày"),
        ("Thanh toán bằng phương thức nào?", "COD"),
        ("Shop có freeship cho đơn dưới 100k không?", "500.000đ"),
        ("Áo này có bảo hành mấy năm không?", "30 ngày"),
    )
    for index, (message, expected) in enumerate(published_questions, start=1):
        response = client.post(
            "/assistant/chat",
            json={
                "session_id": f"chat-thread-published-shop-info-{index}",
                "user_id": "user-1",
                "message": message,
                "locale": "vi-VN",
            },
        )
        assert response.status_code == 200
        assert response.json()["product_ids"] == []
        assert expected in response.json()["message"]
        assert "chưa hỗ trợ" not in response.json()["message"]
        assert "ví da" not in response.json()["message"].casefold()

    for index, message in enumerate(
        (
            "Sản phẩm này có được người nổi tiếng nào mặc chưa?",
            "Sản phẩm này có chắc chắn giúp tôi trông cao hơn không?",
        ),
        start=1,
    ):
        response = client.post(
            "/assistant/chat",
            json={
                "session_id": f"chat-thread-unsupported-claim-{index}",
                "user_id": "user-1",
                "message": message,
                "locale": "vi-VN",
            },
        )
        assert response.status_code == 200
        assert response.json()["product_ids"] == []
        assert "chưa hỗ trợ" in response.json()["message"]

    assert search_service.prepared_text_requests == []
    assert search_service.text_requests == []
    assert fake_springboot_client.product_calls == []


def test_assistant_chat_refines_previous_candidates_before_expanding_search(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    class CandidateRefinementSearchService(RecordingAssistantSearchService):
        def filter_catalog_product_ids(self, product_ids, filters):
            assert product_ids == ["P-CHAT-1"]
            assert filters == SearchFilter(category="hoodie", colors=["black"])
            return ["P-CHAT-1"]

    search_service = CandidateRefinementSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    first = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-candidate-refinement",
            "user_id": "user-1",
            "message": "tìm hoodie màu kem",
            "locale": "vi-VN",
        },
    )
    follow_up = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-candidate-refinement",
            "user_id": "user-1",
            "message": "màu đen thì sao",
            "locale": "vi-VN",
        },
    )

    assert first.status_code == 200
    assert follow_up.status_code == 200
    assert follow_up.json()["product_ids"][0]["product_id"] == "P-CHAT-1"
    assert len(search_service.prepared_text_requests) == 1


def test_assistant_chat_loads_explicit_preferences_across_sessions_without_crossing_users(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    llm_service = PreferenceRecordingLlmService()
    preference_store = InMemoryUserPreferenceStore()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=llm_service,
        search_service=RecordingAssistantSearchService(),  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
        preference_store=preference_store,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "preference-session-1",
            "user_id": "user-preference-1",
            "message": "Mình thích áo màu đen, ưu tiên form rộng",
            "locale": "vi-VN",
        },
    )
    second_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "preference-session-2",
            "user_id": "user-preference-1",
            "message": "Gợi ý theo gu của mình",
            "locale": "vi-VN",
        },
    )
    other_user_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "preference-session-3",
            "user_id": "user-preference-2",
            "message": "Gợi ý theo gu của mình",
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert other_user_response.status_code == 200
    assert "preferred_colors" in (llm_service.analysis_contexts[1] or "")
    assert "black" in (llm_service.analysis_contexts[1] or "")
    assert "form rộng" in (llm_service.analysis_contexts[1] or "")
    assert "long_term_user_preferences" not in (llm_service.analysis_contexts[2] or "")


def test_assistant_chat_correction_replaces_old_preference_across_sessions(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    llm_service = PreferenceRecordingLlmService()
    preference_store = InMemoryUserPreferenceStore()
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=llm_service,
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
        preference_store=preference_store,
        eval_trace_enabled=True,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(
        graph=graph,
        eval_trace_enabled=True,
    )

    first = client.post(
        "/assistant/chat",
        json={
            "session_id": "preference-correction-1",
            "user_id": "preference-correction-user",
            "request_id": "preference-request-1",
            "turn_sequence": 1,
            "message": "Mình thích áo màu đen",
            "locale": "vi-VN",
        },
    )
    corrected = client.post(
        "/assistant/chat",
        json={
            "session_id": "preference-correction-2",
            "user_id": "preference-correction-user",
            "request_id": "preference-request-2",
            "turn_sequence": 1,
            "message": "Không phải màu đen, đổi sang màu xanh",
            "locale": "vi-VN",
        },
    )
    search_count = len(search_service.prepared_text_requests)
    recalled = client.post(
        "/assistant/chat",
        json={
            "session_id": "preference-correction-3",
            "user_id": "preference-correction-user",
            "request_id": "preference-request-3",
            "turn_sequence": 1,
            "message": "Nhắc lại sở thích hiện tại của tôi",
            "locale": "vi-VN",
        },
    )

    assert first.status_code == corrected.status_code == recalled.status_code == 200
    profile = preference_store.get("preference-correction-user")
    assert profile.preferred_colors == ["blue"]
    assert profile.superseded_values["preferred_colors"] == ["black"]
    assert profile.style_notes == []
    assert "xanh" in recalled.json()["message"]
    assert "đen" not in recalled.json()["message"]
    assert len(search_service.prepared_text_requests) == search_count

    trace = corrected.json()["evaluation_trace"]
    assert trace["route"] == "text_search"
    assert trace["retrieved_context"]
    assert trace["stage_latencies_ms"]["total"] >= 0
    assert trace["session_id_hash"] != "preference-correction-2"
    assert trace["request_id_hash"] != "preference-request-2"
    assert "preference-correction-user" not in str(trace)


def test_assistant_chat_keeps_mixed_preferences_and_corrects_same_session(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    preference_store = InMemoryUserPreferenceStore()
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=PreferenceRecordingLlmService(),
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
        preference_store=preference_store,
        eval_trace_enabled=True,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(
        graph=graph,
        eval_trace_enabled=True,
    )
    session_id = "preference-long-session"
    user_id = "preference-long-user"
    messages = [
        "Mình thích hoodie nam màu đen, form rộng, ngân sách dưới 700 nghìn.",
        "Mình ưu tiên chất liệu cotton và tránh màu đỏ.",
        "Không phải màu đen nữa, đổi sang màu xanh.",
        "Tìm lại theo màu mới và gọi danh sách này là beta.",
        "Cái thứ 1 vừa rồi thì sao?",
        "Mình mặc size L, hãy ghi nhớ.",
        (
            "Tổng hợp tiêu chí hiện tại: loại áo, màu mới, màu đã bỏ, "
            "ngân sách, chất liệu, màu tránh và size."
        ),
    ]
    responses = [
        client.post(
            "/assistant/chat",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "request_id": f"preference-long-{index}",
                "turn_sequence": index,
                "message": message,
                "locale": "vi-VN",
            },
        )
        for index, message in enumerate(messages, start=1)
    ]

    assert all(response.status_code == 200 for response in responses)
    summary = responses[-1].json()["message"].lower()
    assert all(
        value in summary
        for value in (
            "hoodie",
            "màu hiện tại là xanh",
            "đã bỏ màu đen",
            "cotton",
            "màu đỏ",
            "size l",
            "700",
        )
    )
    profile = preference_store.get(user_id)
    assert profile.preferred_colors == ["blue"]
    assert profile.preferred_materials == ["cotton"]
    assert profile.preferred_sizes == ["l"]
    assert profile.style_notes == ["form rộng"]
    assert profile.avoidance_notes == ["màu đỏ"]
    assert responses[3].json()["product_ids"]
    assert responses[4].json()["product_ids"][0]["product_id"] == (
        responses[3].json()["product_ids"][0]["product_id"]
    )
    assert responses[4].json()["evaluation_trace"]["reference_resolution_source"] == "latest"
    searched_colors = [
        request["filters"].colors
        for request in search_service.prepared_text_requests
        if request["filters"] is not None and request["filters"].colors
    ]
    assert ["blue"] in searched_colors
    assert ["black", "blue"] not in searched_colors


def test_assistant_memory_accepts_only_product_references_from_previous_results() -> None:
    resolved = _validated_referenced_product_ids(
        ["P-CHAT-2", "invented-id", "P-CHAT-2"],
        [
            {"product_id": "P-CHAT-1"},
            {"product_id": "P-CHAT-2"},
        ],
    )

    assert resolved == ["P-CHAT-2"]


def test_assistant_memory_compacts_dropped_messages_with_a_hard_size_limit() -> None:
    summary = _extend_conversation_summary(
        "old preference: oversized",
        [
            {"role": "user", "content": "x" * 800},
            {"role": "assistant", "content": "y" * 800},
        ],
        500,
    )

    assert summary is not None
    assert len(summary) == 500
    assert "older details compacted" in summary


def test_assistant_chat_uses_fake_checkpointer_for_follow_up_memory(
    app: FastAPI,
    client: TestClient,
    assistant_workflow: AssistantWorkflow,
    fake_llm_service,
    fake_springboot_client,
) -> None:
    app.dependency_overrides[get_assistant_workflow] = lambda: assistant_workflow

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-1",
            "user_id": "user-1",
            "message": "find hoodie",
            "locale": "vi-VN",
        },
    )
    follow_up_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-1",
            "user_id": "user-1",
            "message": "cái thứ 1 còn màu trắng không?",
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["product_ids"][0]["product_id"] == "P-CHAT-1"
    assert follow_up_response.status_code == 200
    payload = follow_up_response.json()
    assert payload["product_ids"] == [
        {
            "product_id": "P-CHAT-1",
            "score": 1.0,
            "source": "hybrid",
        }
    ]
    assert payload["message"] == "assistant reply for P-CHAT-1"
    assert fake_springboot_client.product_calls == [["P-CHAT-1", "P-CHAT-2"], ["P-CHAT-1"]]
    assert fake_llm_service.conversation_contexts[0] is None
    assert "user: find hoodie" in (fake_llm_service.conversation_contexts[1] or "")
    assert "assistant: assistant reply for P-CHAT-1" in (
        fake_llm_service.conversation_contexts[1] or ""
    )


def test_assistant_chat_carries_previous_filters_for_short_refinement(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-filter-refinement",
            "user_id": "user-1",
            "message": "tìm hoodie màu kem dưới 700k",
            "locale": "vi-VN",
        },
    )
    follow_up_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-filter-refinement",
            "user_id": "user-1",
            "message": "màu đen thì sao",
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert follow_up_response.status_code == 200
    follow_up_filters = search_service.prepared_text_requests[-1]["filters"]
    assert follow_up_filters == SearchFilter(
        category="hoodie",
        colors=["black"],
        max_price=700000,
    )
    assert search_service.text_requests == []
    assert follow_up_response.json()["filters"] == {
        "category": "hoodie",
        "colors": ["black"],
        "max_price": 700000.0,
    }


def test_assistant_chat_carries_previous_filters_for_explicit_long_refinement(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(
        graph=graph
    )

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-explicit-long-refinement",
            "user_id": "user-1",
            "message": "tìm hoodie màu kem dưới 700k",
            "locale": "vi-VN",
        },
    )
    follow_up_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-explicit-long-refinement",
            "user_id": "user-1",
            "message": "Giữ các yêu cầu trên nhưng ưu tiên màu đen.",
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert follow_up_response.status_code == 200
    prepared = search_service.prepared_text_requests[-1]
    expected_filters = SearchFilter(
        category="hoodie",
        colors=["black"],
        max_price=700000,
    )
    assert prepared["filters"] == expected_filters
    assert prepared["constraints"].hard_filters == expected_filters
    assert follow_up_response.json()["filters"] == {
        "category": "hoodie",
        "colors": ["black"],
        "max_price": 700000.0,
    }


def test_assistant_chat_searches_again_for_cheaper_follow_up(
    app: FastAPI,
    client: TestClient,
) -> None:
    class HistoryBiasedLlmService(FilterAwareLlmService):
        def analyze_user_query(self, message, locale="vi-VN", conversation_context=None):
            understanding = super().analyze_user_query(
                message,
                locale=locale,
                conversation_context=conversation_context,
            )
            if "rẻ hơn" not in message.lower():
                return understanding
            return understanding.model_copy(
                update={
                    "filters": SearchFilter(category="hoodie", colors=["cream"]),
                    # Reproduce the production LLM mistake that previously
                    # diverted this refinement to the product-context route.
                    "referenced_product_ids": ["P-CHAT-1"],
                }
            )

    class PricedSpringBootClient:
        def __init__(self) -> None:
            self.product_calls: list[list[str]] = []

        def get_products_by_ids(self, product_ids):
            self.product_calls.append(list(product_ids))
            return SpringBootResult(
                data=[
                    {
                        "product_id": product_id,
                        "title": f"Product {product_id}",
                        "price": {"effective_price": 579000},
                    }
                    for product_id in product_ids
                ]
            )

    search_service = RecordingAssistantSearchService()
    springboot_client = PricedSpringBootClient()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=HistoryBiasedLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=springboot_client,  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-cheaper-refinement",
            "user_id": "user-1",
            "message": "tìm hoodie màu kem",
            "locale": "vi-VN",
        },
    )
    follow_up_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-cheaper-refinement",
            "user_id": "user-1",
            "message": "rẻ hơn nữa có không?",
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert follow_up_response.status_code == 200
    assert len(search_service.prepared_text_requests) == 2
    follow_up_filters = search_service.prepared_text_requests[-1]["filters"]
    assert follow_up_filters == SearchFilter(
        category="hoodie",
        colors=["cream"],
        max_price=578999,
    )
    assert follow_up_response.json()["filters"]["max_price"] == 578999.0


def test_assistant_chat_prefers_exact_vanilla_rule_over_llm_lavender(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    class LavenderGuessLlmService(FilterAwareLlmService):
        def analyze_user_query(self, message, locale="vi-VN", conversation_context=None):
            del locale, conversation_context
            return QueryUnderstanding(
                intent="search_product",
                rewritten_query=message,
                filters=SearchFilter(category="tshirt", colors=["lavender"]),
                needs_image_search=False,
                needs_text_search=True,
                clarifying_question=None,
            )

    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=LavenderGuessLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-vanilla",
            "user_id": "user-1",
            "message": "Tìm Áo thun màu Vani",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    assert search_service.prepared_text_requests[-1]["filters"] == SearchFilter(
        category="tshirt",
        colors=["vanilla"],
    )
    assert response.json()["filters"]["colors"] == ["vanilla"]


def test_assistant_chat_preserves_quoted_title_and_softens_inferred_filters(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-exact-title",
            "user_id": "user-1",
            "message": 'Hãy tìm sản phẩm "Áo sơ mi satin hoa nữ".',
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    prepared = search_service.prepared_text_requests[0]
    assert prepared["embedding_query"] == "ao so mi satin hoa nu"
    assert prepared["constraints"].hard_filters is None
    assert prepared["constraints"].soft_filters is not None
    assert prepared["constraints"].soft_filters.category == "shirt"
    assert prepared["constraints"].soft_filters.gender == "women"


def test_assistant_chat_does_not_share_memory_between_users_with_same_session_id(
    app: FastAPI,
    client: TestClient,
    assistant_workflow: AssistantWorkflow,
) -> None:
    app.dependency_overrides[get_assistant_workflow] = lambda: assistant_workflow

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "shared-client-session",
            "user_id": "user-1",
            "message": "find hoodie",
            "locale": "vi-VN",
        },
    )
    other_user_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "shared-client-session",
            "user_id": "user-2",
            "message": "cái thứ 1 còn màu trắng không?",
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert other_user_response.status_code == 200
    assert other_user_response.json()["product_ids"] == []
    assert "chưa có danh sách sản phẩm trước đó" in other_user_response.json()["message"]


def test_assistant_chat_routes_image_only_without_query_understanding(
    app: FastAPI,
    client: TestClient,
    fake_llm_service,
    fake_springboot_client,
    image_payload: dict[str, str],
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=fake_llm_service,
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-image-only",
            "user_id": "user-1",
            "image": image_payload,
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"][0]["source"] == "image"
    assert len(search_service.image_requests) == 1
    assert search_service.prepared_text_requests == []
    assert search_service.hybrid_requests == []
    assert fake_llm_service.analyze_calls == []


def test_assistant_chat_routes_generic_image_reference_to_image_search(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
    image_payload: dict[str, str],
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-image-reference",
            "user_id": "user-1",
            "message": "tìm giống ảnh này",
            "image": image_payload,
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"][0]["source"] == "image"
    assert len(search_service.image_requests) == 1
    assert search_service.prepared_text_requests == []


def test_assistant_chat_forces_unquoted_product_factual_question_through_search(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    class GeneralQuestionLlm(FilterAwareLlmService):
        def analyze_user_query(self, message, locale="vi-VN", conversation_context=None):
            del locale, conversation_context
            return QueryUnderstanding(
                intent="general_question",
                rewritten_query=message,
                filters=SearchFilter(category="bodysuit", colors=["black"]),
                needs_image_search=False,
                needs_text_search=False,
                clarifying_question=None,
            )

    class ResolvingSearchService(RecordingAssistantSearchService):
        def __init__(self) -> None:
            super().__init__()
            self.resolved_titles: list[str] = []

        def resolve_catalog_title_ids(self, titles):
            self.resolved_titles.extend(titles)
            return {
                title: ["P-CHAT-1"]
                for title in titles
                if title == "bodysuit mau den co tim gong nang phoi tuong phan"
            }

    search_service = ResolvingSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=GeneralQuestionLlm(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-factual-unquoted",
            "user_id": "user-1",
            "message": "Bodysuit màu đen cổ tim gọng nâng phối tương phản có màu gì?",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    assert response.json()["product_ids"][0]["product_id"] == "P-CHAT-1"
    assert search_service.resolved_titles == [
        "bodysuit mau den co tim gong nang phoi tuong phan"
    ]
    assert search_service.prepared_text_requests == []
    assert search_service.hybrid_requests == []


def test_assistant_chat_uses_attached_image_instead_of_asking_for_it_again(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
    image_payload: dict[str, str],
) -> None:
    class IncorrectlyClarifyingLlmService(FilterAwareLlmService):
        def analyze_user_query(self, message, locale="vi-VN", conversation_context=None):
            del locale, conversation_context
            return QueryUnderstanding(
                intent="ask_clarification",
                rewritten_query=message,
                filters=SearchFilter(),
                needs_image_search=False,
                needs_text_search=False,
                clarifying_question=(
                    "Bạn có thể cho mình biết mẫu áo nào bạn muốn tìm tương tự không? "
                    "Vui lòng cung cấp mô tả hoặc hình ảnh."
                ),
            )

    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=IncorrectlyClarifyingLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    messages = (
        "shop có áo giống vậy không?",
        "shop có bán mẫu này không?",
    )
    for index, message in enumerate(messages):
        response = client.post(
            "/assistant/chat",
            json={
                "session_id": f"chat-thread-attached-image-reference-{index}",
                "user_id": "user-1",
                "message": message,
                "image": image_payload,
                "locale": "vi-VN",
            },
        )

        assert response.status_code == 200
        assert response.json()["product_ids"][0]["source"] == "hybrid"

    assert len(search_service.hybrid_requests) == len(messages)
    assert all(request["image"] is not None for request in search_service.hybrid_requests)
    assert search_service.image_requests == []
    assert search_service.prepared_text_requests == []

    response_without_image = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-missing-image-reference",
            "user_id": "user-1",
            "message": "shop có bán mẫu này không?",
            "locale": "vi-VN",
        },
    )
    assert response_without_image.status_code == 200
    assert response_without_image.json()["product_ids"] == []
    assert "cung cấp mô tả hoặc hình ảnh" in response_without_image.json()["message"]


def test_assistant_chat_new_image_supersedes_previous_product_reference(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
    image_payload: dict[str, str],
) -> None:
    class HistoryBiasedLlmService(FilterAwareLlmService):
        def analyze_user_query(self, message, locale="vi-VN", conversation_context=None):
            understanding = super().analyze_user_query(
                message,
                locale=locale,
                conversation_context=conversation_context,
            )
            if "mẫu này" not in message:
                return understanding
            return QueryUnderstanding(
                intent="search_product",
                rewritten_query=message,
                filters=SearchFilter(),
                needs_image_search=False,
                needs_text_search=True,
                clarifying_question=None,
                referenced_product_ids=["P-CHAT-1"],
            )

    class ImageAwareSearchService(RecordingAssistantSearchService):
        def search_hybrid_prepared(
            self,
            *,
            rewritten_query,
            original_query=None,
            image,
            crop_box,
            filters,
            top_k=None,
            constraints=None,
        ):
            self.hybrid_requests.append(
                {
                    "rewritten_query": rewritten_query,
                    "original_query": original_query,
                    "image": image,
                    "crop_box": crop_box,
                    "top_k": top_k,
                    "constraints": constraints,
                }
            )
            product_id = "P-CHAT-2" if image.filename == "second.jpg" else "P-CHAT-1"
            result = SearchResultItem(product_id=product_id, score=0.95, source="hybrid")
            return SearchResponse(
                rewritten_query=rewritten_query,
                filters=filters,
                product_ids=[product_id],
                results=[result],
            )

    search_service = ImageAwareSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=HistoryBiasedLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)
    first_image = {**image_payload, "filename": "first.jpg"}
    second_image = {**image_payload, "filename": "second.jpg"}

    first_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-new-image",
            "user_id": "user-1",
            "message": "tìm mẫu tương tự",
            "image": first_image,
            "locale": "vi-VN",
        },
    )
    second_response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-new-image",
            "user_id": "user-1",
            "message": "shop có bán mẫu này không?",
            "image": second_image,
            "locale": "vi-VN",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["product_ids"][0]["product_id"] == "P-CHAT-1"
    assert second_response.status_code == 200
    assert second_response.json()["product_ids"][0] == {
        "product_id": "P-CHAT-2",
        "score": 0.95,
        "source": "hybrid",
    }
    assert [request["image"].filename for request in search_service.hybrid_requests] == [
        "first.jpg",
        "second.jpg",
    ]
    assert fake_springboot_client.product_calls == [["P-CHAT-1"], ["P-CHAT-2"]]


def test_assistant_chat_clarifies_context_dependent_message_without_history(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-no-context",
            "user_id": "user-1",
            "message": "màu đen thì sao",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"] == []
    assert "ngữ cảnh" in payload["message"]
    assert search_service.text_requests == []


def test_assistant_chat_routes_mens_jacket_queries_as_new_text_search(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
    settings,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=BaseLlmService(settings=settings),
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    for index, message in enumerate(
        ("Goi y ao khoac nam mau den", "Tim ao khoac nam mau den"),
        start=1,
    ):
        response = client.post(
            "/assistant/chat",
            json={
                "session_id": f"chat-thread-mens-jacket-{index}",
                "user_id": "user-1",
                "message": message,
                "locale": "vi-VN",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["product_ids"][0]["product_id"] == "P-CHAT-1"
        assert payload["filters"] == {
            "category": "jacket",
            "colors": ["black"],
            "gender": "men",
        }

    assert len(search_service.prepared_text_requests) == 2


def test_assistant_chat_hard_filters_generic_work_top_query_to_office_categories(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
    settings,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=BaseLlmService(settings=settings),
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-office-tops",
            "user_id": "user-1",
            "message": "Tôi muốn áo mặc đi làm",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    prepared = search_service.prepared_text_requests[0]
    assert prepared["filters"].category == "office_tops"
    assert prepared["constraints"].hard_filters == SearchFilter(category="office_tops")
    assert prepared["constraints"].recovery_filters == SearchFilter(category="office_tops")


def test_assistant_chat_explains_empty_text_search_without_history_clarification(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
    settings,
) -> None:
    search_service = EmptyRecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=BaseLlmService(settings=settings),
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-empty-shirt-search",
            "user_id": "user-1",
            "message": "Ao so mi trang",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"] == []
    assert payload["warnings"] == ["llm_query_understanding_fallback", "no_search_results"]
    assert "đã thử tìm theo mô tả" in payload["message"]
    assert len(search_service.prepared_text_requests) == 1
    assert search_service.text_requests == []
    assert fake_springboot_client.product_calls == []


def test_assistant_chat_still_clarifies_ordinal_availability_without_history(
    app: FastAPI,
    client: TestClient,
    fake_springboot_client,
    settings,
) -> None:
    search_service = RecordingAssistantSearchService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=BaseLlmService(settings=settings),
        search_service=search_service,  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-ordinal-no-history",
            "user_id": "user-1",
            "message": "San pham thu 2 con hang khong?",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"] == []
    assert "tham chi" in payload["message"].lower()
    assert search_service.prepared_text_requests == []
    assert search_service.text_requests == []


def test_assistant_chat_returns_only_the_candidates_described_by_the_reply(
    app: FastAPI,
    client: TestClient,
    fake_llm_service,
    fake_springboot_client,
) -> None:
    class ManyResultsSearchService:
        def search_text_prepared(self, *, rewritten_query, filters, top_k=None):
            del rewritten_query, filters, top_k
            results = [
                SearchResultItem(product_id=f"P-CHAT-{index}", score=1.0 - index / 100, source="text")
                for index in range(1, 8)
            ]
            return SearchResponse(product_ids=[item.product_id for item in results], results=results), {}

    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=fake_llm_service,
        search_service=ManyResultsSearchService(),  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-context-limit",
            "user_id": "user-1",
            "message": "find hoodie",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    assert len(response.json()["product_ids"]) == 3
    assert fake_springboot_client.product_calls == [
        ["P-CHAT-1", "P-CHAT-2", "P-CHAT-3"]
    ]


def test_assistant_chat_three_dress_reply_has_three_product_cards(
    app: FastAPI,
    client: TestClient,
    fake_llm_service,
    fake_springboot_client,
) -> None:
    class FiveDressResultsSearchService:
        def search_text_prepared(self, *, rewritten_query, filters, top_k=None):
            del rewritten_query, filters, top_k
            results = [
                SearchResultItem(
                    product_id=f"P-DRESS-{index}",
                    score=1.0 - index / 100,
                    source="text",
                )
                for index in range(1, 6)
            ]
            return SearchResponse(
                product_ids=[item.product_id for item in results],
                results=results,
            ), {}

    fake_llm_service.generate_assistant_reply = lambda **_: (
        "Chào anh/chị, em đã chọn ra ba mẫu váy phù hợp cho việc đi biển."
    )
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=fake_llm_service,
        search_service=FiveDressResultsSearchService(),  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-beach-dress-count",
            "user_id": "user-1",
            "message": "Tôi cần váy đi biển",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "ba mẫu váy" in payload["message"]
    assert len(payload["product_ids"]) == 3
    assert fake_springboot_client.product_calls == [
        ["P-DRESS-1", "P-DRESS-2", "P-DRESS-3"]
    ]


def test_assistant_chat_returns_qdrant_candidates_with_warning_when_spring_boot_fails(
    app: FastAPI,
    client: TestClient,
    fake_llm_service,
) -> None:
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=fake_llm_service,
        search_service=FakeAssistantSearchService(),
        springboot_client=FailingSpringBootClient(),
    )
    app.dependency_overrides[get_assistant_workflow] = lambda: AssistantWorkflow(graph=graph)

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "chat-thread-spring-fail",
            "user_id": "user-1",
            "message": "find hoodie",
            "locale": "vi-VN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_ids"] == [
        {
            "product_id": "P-CHAT-1",
            "score": 0.95,
            "source": "text",
        },
        {
            "product_id": "P-CHAT-2",
            "score": 0.87,
            "source": "text",
        },
    ]
    assert payload["warnings"] == ["spring_boot_unavailable"]
    assert payload["message"].startswith("Em đã tìm thấy 2 sản phẩm phù hợp")
    assert "Sản phẩm mã" not in payload["message"]
    assert "llm_reply_fallback" not in payload["warnings"]
    assert "llm_reply_grounding_validation_failed" not in payload["warnings"]
    assert fake_llm_service.reply_contexts == []


def test_assistant_chat_is_idempotent_and_serializes_same_thread_requests(
    fake_springboot_client,
) -> None:
    search_service = RecordingAssistantSearchService()
    workflow = AssistantWorkflow(
        graph=build_assistant_graph(
            checkpointer=InMemorySaver(),
            llm_service=FilterAwareLlmService(),  # type: ignore[arg-type]
            search_service=search_service,  # type: ignore[arg-type]
            springboot_client=fake_springboot_client,
        )
    )
    request = ChatRequest(
        session_id="idempotent-thread",
        user_id="idempotent-user",
        request_id="request-1",
        turn_sequence=1,
        message="tìm hoodie màu đen",
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: workflow.chat(request), range(2)))

    assert responses[0] == responses[1]
    assert len(search_service.prepared_text_requests) == 1
    assert fake_springboot_client.product_calls == [["P-CHAT-1"]]


def test_assistant_chat_rejects_out_of_order_turn_sequence(
    app: FastAPI,
    client: TestClient,
    assistant_workflow: AssistantWorkflow,
) -> None:
    app.dependency_overrides[get_assistant_workflow] = lambda: assistant_workflow

    response = client.post(
        "/assistant/chat",
        json={
            "session_id": "ordered-thread",
            "user_id": "ordered-user",
            "request_id": "request-2",
            "turn_sequence": 2,
            "message": "find hoodie",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "turn_sequence_conflict",
        "expected": 1,
        "received": 2,
    }


def test_assistant_sqlite_checkpoint_survives_workflow_restart(
    tmp_path,
    fake_springboot_client,
) -> None:
    checkpoint_path = tmp_path / "assistant-checkpoints.sqlite3"
    first_connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    first_saver = SqliteSaver(first_connection)
    first_saver.setup()
    first_llm = PreferenceRecordingLlmService()
    first_workflow = AssistantWorkflow(
        graph=build_assistant_graph(
            checkpointer=first_saver,
            llm_service=first_llm,  # type: ignore[arg-type]
            search_service=RecordingAssistantSearchService(),  # type: ignore[arg-type]
            springboot_client=fake_springboot_client,
        )
    )
    first_workflow.chat(
        ChatRequest(
            session_id="persistent-thread",
            user_id="persistent-user",
            request_id="persistent-request-1",
            turn_sequence=1,
            message="tìm hoodie màu đen",
        )
    )
    first_connection.close()

    second_connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    second_saver = SqliteSaver(second_connection)
    second_saver.setup()
    second_llm = PreferenceRecordingLlmService()
    second_workflow = AssistantWorkflow(
        graph=build_assistant_graph(
            checkpointer=second_saver,
            llm_service=second_llm,  # type: ignore[arg-type]
            search_service=RecordingAssistantSearchService(),  # type: ignore[arg-type]
            springboot_client=fake_springboot_client,
        )
    )

    response = second_workflow.chat(
        ChatRequest(
            session_id="persistent-thread",
            user_id="persistent-user",
            request_id="persistent-request-2",
            turn_sequence=2,
            message="màu đen thì sao",
        )
    )

    assert response.filters == SearchFilter(category="hoodie", colors=["black"])
    assert "user: tìm hoodie màu đen" in (second_llm.analysis_contexts[0] or "")
    second_connection.close()


def test_assistant_forces_compaction_and_passes_structured_state_to_llm(
    fake_springboot_client,
) -> None:
    llm_service = PreferenceRecordingLlmService()
    graph = build_assistant_graph(
        checkpointer=InMemorySaver(),
        llm_service=llm_service,  # type: ignore[arg-type]
        search_service=RecordingAssistantSearchService(),  # type: ignore[arg-type]
        springboot_client=fake_springboot_client,
        recent_message_limit=2,
        conversation_summary_max_chars=120,
    )
    workflow = AssistantWorkflow(graph=graph)

    messages = [
        "tìm hoodie màu đen",
        "cảm ơn bạn " + "x" * 80,
        "tư vấn phối đồ " + "y" * 80,
        "hướng dẫn bảo quản " + "z" * 80,
        "nhắc lại tiêu chí ban đầu",
    ]
    for turn_sequence, message in enumerate(messages, start=1):
        workflow.chat(
            ChatRequest(
                session_id="forced-compaction",
                user_id="forced-compaction-user",
                request_id=f"forced-{turn_sequence}",
                turn_sequence=turn_sequence,
                message=message,
            )
        )

    snapshot = graph.get_state(
        {"configurable": {"thread_id": "forced-compaction-user:forced-compaction"}}
    ).values
    assert len(snapshot["recent_messages"]) == 2
    assert len(snapshot["conversation_summary"]) == 120
    assert snapshot["conversation_memory"]["summary_compaction_count"] >= 1
    final_context = llm_service.analysis_contexts[-1] or ""
    assert "active_constraints" in final_context
    assert "'category': 'hoodie'" in final_context
    assert "'colors': ['black']" in final_context
