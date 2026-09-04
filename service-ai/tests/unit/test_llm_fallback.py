from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.schemas.search import SearchResultItem
from types import SimpleNamespace

import pytest

from ecommerce_search_assistant.services.llm.service import BaseLlmService


def test_filter_extraction_and_understanding_without_remote_provider(settings: Settings) -> None:
    service = BaseLlmService(settings=settings)

    understanding = service.analyze_user_query("black hoodie under 500k", locale="vi-VN")
    filters = service.extract_filters("black hoodie under 500k")
    expected_filters = {
        "category": "hoodie",
        "colors": ["black"],
        "max_price": 500000.0,
    }

    assert understanding.rewritten_query == "black hoodie under 500k"
    assert understanding.intent == "search_product"
    assert understanding.needs_text_search is True
    assert understanding.filters.model_dump(exclude_none=True) == expected_filters
    assert filters.model_dump(exclude_none=True) == expected_filters


def test_llm_fallback_routes_greeting_to_natural_conversation_without_search(settings: Settings) -> None:
    service = BaseLlmService(settings=settings)

    understanding = service.analyze_user_query("hello", locale="vi-VN")

    assert understanding.intent == "small_talk"
    assert understanding.clarifying_question is None
    assert understanding.needs_text_search is False
    assert understanding.needs_image_search is False
    assert understanding.filters.model_dump(exclude_none=True) == {}
    assert service.generate_conversational_reply("hello").startswith("Chào bạn")


def test_llm_fallback_responds_to_thanks_without_forcing_product_questions(settings: Settings) -> None:
    service = BaseLlmService(settings=settings)

    understanding = service.analyze_user_query("cảm ơn bạn", locale="vi-VN")

    assert understanding.intent == "small_talk"
    assert service.generate_conversational_reply("cảm ơn bạn").startswith("Không có gì")


def test_llm_fallback_searches_broad_shopping_requests(settings: Settings) -> None:
    service = BaseLlmService(settings=settings)

    understanding = service.analyze_user_query("Có món nào đẹp không?", locale="vi-VN")

    assert understanding.intent == "search_product"
    assert understanding.clarifying_question is None
    assert understanding.needs_text_search is True


def test_grounded_fallback_reply_uses_product_context(settings: Settings) -> None:
    service = BaseLlmService(settings=settings)

    reply = service.generate_assistant_reply(
        message="tìm áo",
        search_results=[SearchResultItem(product_id="47", score=0.9, source="text")],
        product_context=[
            {
                "product_id": "47",
                "title_vi": "Áo sơ mi satin hoa nữ",
                "brand": "Zara",
                "effective_price": 499000,
                "available": True,
            }
        ],
    )

    assert "Áo sơ mi satin hoa nữ" in reply
    assert "Zara" in reply
    assert "499,000" in reply
    assert "Mẫu 47" not in reply
    assert service.consume_warnings() == [
        "llm_reply_fallback",
        "llm_reply_generation_error",
    ]


class _EnabledReplyService(BaseLlmService):
    def __init__(self, *args, outputs, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.outputs = list(outputs)
        self.calls = 0

    @property
    def is_enabled(self) -> bool:
        return True

    def _generate_json(self, prompt, schema):
        del prompt, schema
        self.calls += 1
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(reply=output)


def test_reply_schema_failure_retries_once_then_recovers(settings: Settings) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=[
            ValueError("response was not valid JSON"),
            "Áo sơ mi satin hoa nữ có chất liệu polyester.",
        ],
    )

    reply = service.generate_assistant_reply(
        message='Giới thiệu "áo sơ mi satin hoa nữ".',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {
                "product_id": "1",
                "title_vi": "Áo sơ mi satin hoa nữ",
                "material_vi": "polyester",
            }
        ],
    )

    assert reply == "Áo sơ mi satin hoa nữ có chất liệu polyester."
    assert service.calls == 2
    assert service.consume_warnings() == []


@pytest.mark.parametrize(
    "generated_reply",
    [
        "Áo sơ mi satin hoa nữ có mã sản phẩm 1.",
        "Áo sơ mi satin hoa nữ có mã SP là 1.",
        "Áo sơ mi satin hoa nữ có product ID: 1.",
        "Áo sơ mi satin hoa nữ có ID sản phẩm 1.",
        "Áo sơ mi satin hoa nữ có mã: 1.",
    ],
)
def test_grounding_validator_accepts_supported_product_id_labels(
    settings: Settings,
    generated_reply: str,
) -> None:
    service = _EnabledReplyService(settings=settings, outputs=[generated_reply])

    reply = service.generate_assistant_reply(
        message='Giới thiệu "áo sơ mi satin hoa nữ".',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {"product_id": "1", "title_vi": "Áo sơ mi satin hoa nữ"}
        ],
    )

    assert reply == generated_reply
    assert service.consume_warnings() == []


def test_grounding_validator_ignores_id_as_an_ordinary_label(
    settings: Settings,
) -> None:
    generated_reply = (
        "ID của áo sơ mi satin hoa nữ được lưu trong thông tin sản phẩm."
    )
    service = _EnabledReplyService(settings=settings, outputs=[generated_reply])

    reply = service.generate_assistant_reply(
        message='Giới thiệu "áo sơ mi satin hoa nữ".',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {"product_id": "1", "title_vi": "Áo sơ mi satin hoa nữ"}
        ],
    )

    assert reply == generated_reply
    assert service.consume_warnings() == []


def test_grounding_validator_does_not_treat_den_as_black(
    settings: Settings,
) -> None:
    generated_reply = (
        "Áo sơ mi satin hoa nữ mang đến phong cách thanh lịch."
    )
    service = _EnabledReplyService(settings=settings, outputs=[generated_reply])

    reply = service.generate_assistant_reply(
        message='Giới thiệu "áo sơ mi satin hoa nữ".',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {"product_id": "1", "title_vi": "Áo sơ mi satin hoa nữ"}
        ],
    )

    assert reply == generated_reply
    assert service.consume_warnings() == []


@pytest.mark.parametrize(
    ("generated_reply", "context_color"),
    [
        ("Áo len cổ polo có màu cam.", "Cam"),
        ("Áo len cổ polo có màu nâu.", "Brown"),
        ("Áo len cổ polo có màu đỏ.", "Red"),
    ],
)
def test_grounding_validator_accepts_bilingual_color_equivalence(
    settings: Settings,
    generated_reply: str,
    context_color: str,
) -> None:
    service = _EnabledReplyService(settings=settings, outputs=[generated_reply])

    reply = service.generate_assistant_reply(
        message='Giới thiệu "áo len cổ polo".',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {
                "product_id": "1",
                "title_vi": "Áo len cổ polo",
                "base_colour_vi": context_color,
            }
        ],
    )

    assert reply == generated_reply
    assert service.consume_warnings() == []


def test_grounding_validator_accepts_negated_unsupported_color(
    settings: Settings,
) -> None:
    generated_reply = (
        "Hiện em chưa tìm thấy mẫu nào màu trắng khớp hoàn toàn; "
        "áo len cổ polo màu cam là lựa chọn gần nhất."
    )
    service = _EnabledReplyService(settings=settings, outputs=[generated_reply])

    reply = service.generate_assistant_reply(
        message="Ưu tiên màu trắng.",
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {
                "product_id": "1",
                "title_vi": "Áo len cổ polo",
                "base_colour_vi": "Cam",
            }
        ],
    )

    assert reply == generated_reply
    assert service.consume_warnings() == []


def test_comparison_grounding_accepts_distinctive_short_product_names(
    settings: Settings,
) -> None:
    generated_reply = "Đầm maxi hợp dự tiệc, còn cardigan hợp mặc hằng ngày."
    service = _EnabledReplyService(settings=settings, outputs=[generated_reply])

    reply = service.generate_assistant_reply(
        message=(
            'So sánh "đầm maxi cổ cao nữ" và "áo cardigan len phối nữ".'
        ),
        search_results=[
            SearchResultItem(product_id="2", score=0.9, source="text"),
            SearchResultItem(product_id="6", score=0.9, source="text"),
        ],
        product_context=[
            {"product_id": "2", "title_vi": "Đầm maxi cổ cao nữ"},
            {"product_id": "6", "title_vi": "Áo cardigan len phối nữ"},
        ],
    )

    assert reply == generated_reply
    assert service.consume_warnings() == []


def test_grounding_validator_removes_unsupported_price_sentence(
    settings: Settings,
) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=[
            (
                "Áo sơ mi satin hoa nữ được làm từ polyester. "
                "Sản phẩm đang giảm còn 479.000 VND. "
                "Bạn muốn xem màu hay size?"
            )
        ],
    )

    reply = service.generate_assistant_reply(
        message='Giới thiệu "áo sơ mi satin hoa nữ".',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {
                "product_id": "1",
                "title_vi": "Áo sơ mi satin hoa nữ",
                "material_vi": "polyester",
            }
        ],
    )

    assert "polyester" in reply
    assert "479.000" not in reply
    assert service.consume_warnings() == []


def test_grounding_validator_rejects_unsupported_material_with_reason_code(
    settings: Settings,
) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=["Áo sơ mi satin hoa nữ được làm từ linen."],
    )

    reply = service.generate_assistant_reply(
        message='Sản phẩm "áo sơ mi satin hoa nữ" có chất liệu gì?',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[
            {
                "product_id": "1",
                "title_vi": "Áo sơ mi satin hoa nữ",
                "material_vi": "polyester",
            }
        ],
    )

    assert "linen" not in reply
    assert "Áo sơ mi satin hoa nữ" in reply
    assert service.consume_warnings() == [
        "llm_reply_fallback",
        "llm_reply_grounding_validation_failed",
    ]


def test_comparison_reply_must_name_both_context_products(settings: Settings) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=["Áo hoodie thể thao nam phù hợp hơn."],
    )

    reply = service.generate_assistant_reply(
        message=(
            'So sánh "áo hoodie thể thao nam" và "áo sơ mi satin hoa nữ".'
        ),
        search_results=[
            SearchResultItem(product_id="20", score=0.9, source="text"),
            SearchResultItem(product_id="1", score=0.9, source="text"),
        ],
        product_context=[
            {"product_id": "20", "title_vi": "Áo hoodie thể thao nam"},
            {"product_id": "1", "title_vi": "Áo sơ mi satin hoa nữ"},
        ],
    )

    assert "Áo hoodie thể thao nam" in reply
    assert "Áo sơ mi satin hoa nữ" in reply
    assert service.consume_warnings() == [
        "llm_reply_fallback",
        "llm_reply_grounding_validation_failed",
    ]


@pytest.mark.parametrize(
    ("generated_reply", "context"),
    [
        (
            "Áo cotton mã 2 có màu đen.",
            {"product_id": "1", "title_vi": "Áo cotton", "base_colour_vi": "đen"},
        ),
        (
            "Áo cotton có giá 999,000 VND.",
            {"product_id": "1", "title_vi": "Áo cotton", "price": 499000},
        ),
        (
            "Áo cotton đang còn hàng.",
            {"product_id": "1", "title_vi": "Áo cotton", "available": False},
        ),
        (
            "Áo cotton có màu xanh.",
            {"product_id": "1", "title_vi": "Áo cotton", "base_colour_vi": "đen"},
        ),
    ],
)
def test_grounding_validator_rejects_unsupported_structured_claims(
    settings: Settings,
    generated_reply: str,
    context: dict,
) -> None:
    service = _EnabledReplyService(settings=settings, outputs=[generated_reply])

    service.generate_assistant_reply(
        message='Giới thiệu "áo cotton".',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[context],
    )

    assert service.consume_warnings() == [
        "llm_reply_fallback",
        "llm_reply_grounding_validation_failed",
    ]


def test_empty_product_context_never_returns_generated_factual_claim(
    settings: Settings,
) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=["Áo cotton này làm từ linen và đang còn hàng."],
    )

    reply = service.generate_assistant_reply(
        message='Sản phẩm "áo cotton" có chất liệu gì?',
        search_results=[SearchResultItem(product_id="1", score=0.9, source="text")],
        product_context=[],
    )

    assert "linen" not in reply
    assert "còn hàng" not in reply
    assert service.consume_warnings() == [
        "llm_reply_fallback",
        "llm_reply_grounding_validation_failed",
    ]


def test_reference_followup_single_product_skips_product_identity(
    settings: Settings,
) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=["Dạ mẫu số 2 hiện còn hàng ạ."],
    )

    reply = service.generate_assistant_reply(
        message="mẫu thứ 2 còn hàng không?",
        search_results=[SearchResultItem(product_id="2", score=0.9, source="text")],
        product_context=[
            {"product_id": "2", "title_vi": "Đầm maxi cổ cao nữ", "available": True}
        ],
        is_reference_followup=True,
    )

    assert reply == "Dạ mẫu số 2 hiện còn hàng ạ."
    assert service.consume_warnings() == []


def test_search_turn_still_requires_product_identity(
    settings: Settings,
) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=["Dạ mẫu số 2 hiện còn hàng ạ."],
    )

    service.generate_assistant_reply(
        message="mẫu thứ 2 còn hàng không?",
        search_results=[SearchResultItem(product_id="2", score=0.9, source="text")],
        product_context=[
            {"product_id": "2", "title_vi": "Đầm maxi cổ cao nữ", "available": True}
        ],
    )

    assert service.consume_warnings() == [
        "llm_reply_fallback",
        "llm_reply_grounding_validation_failed",
    ]


def test_reference_followup_still_guards_stock_claim(
    settings: Settings,
) -> None:
    service = _EnabledReplyService(
        settings=settings,
        outputs=["Dạ mẫu số 2 hiện còn hàng ạ."],
    )

    service.generate_assistant_reply(
        message="mẫu thứ 2 còn hàng không?",
        search_results=[SearchResultItem(product_id="2", score=0.9, source="text")],
        product_context=[
            {"product_id": "2", "title_vi": "Đầm maxi cổ cao nữ", "available": False}
        ],
        is_reference_followup=True,
    )

    assert service.consume_warnings() == [
        "llm_reply_fallback",
        "llm_reply_grounding_validation_failed",
    ]
