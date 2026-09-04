from ecommerce_search_assistant.services.assistant.memory import (
    detect_memory_intent,
    resolve_candidate_reference,
    update_conversation_memory,
)
from ecommerce_search_assistant.services.assistant.workflow import _memory_recall_reply


def test_empty_memory_recall_explicitly_says_there_is_no_saved_memory() -> None:
    result = _memory_recall_reply(
        {
            "conversation_memory": None,
            "user_preferences": {},
            "intent": "memory_recall",
        }
    )

    assert "chưa có" in result["assistant_reply"]
    assert result["final_product_ids"] == []


def test_structured_memory_supersedes_constraints_and_resolves_named_anchors() -> None:
    first = update_conversation_memory(
        None,
        message="Tìm hoodie màu đen, gọi danh sách này là alpha",
        intent="search_product",
        filters={"category": "hoodie", "colors": ["black"], "max_price": 700000},
        final_product_ids=[{"product_id": "A"}, {"product_id": "B"}],
        route="text_search",
        clarifying_question=None,
        assistant_reply="Có hai mẫu.",
        summary_compacted=False,
    )
    corrected = update_conversation_memory(
        first.model_dump(),
        message="Không phải màu đen, đổi sang màu xanh",
        intent="search_product",
        filters={"category": "hoodie", "colors": ["blue"], "max_price": 700000},
        final_product_ids=[{"product_id": "C"}, {"product_id": "D"}],
        route="text_search",
        clarifying_question=None,
        assistant_reply="Đã đổi sang xanh.",
        summary_compacted=True,
    )

    assert corrected.active_constraints["colors"] == ["blue"]
    assert corrected.superseded_values["colors"] == [["black"]]
    assert corrected.summary_compaction_count == 1
    assert resolve_candidate_reference(
        "cái thứ 1 trong danh sách alpha",
        corrected.model_dump(),
        [],
    ) == (["A"], "named:alpha")
    assert resolve_candidate_reference(
        "cái thứ 2 vừa rồi",
        corrected.model_dump(),
        [],
    ) == (["D"], "latest")


def test_structured_memory_keeps_middle_sentinel_after_transcript_compaction() -> None:
    memory = None
    for turn in range(1, 25):
        filters = {"material": "cotton"} if turn == 12 else {}
        memory = update_conversation_memory(
            memory.model_dump() if memory else None,
            message="Mình ưu tiên chất liệu cotton" if turn == 12 else f"filler {turn}",
            intent="general_question",
            filters=filters,
            final_product_ids=[],
            route="non_product_answer",
            clarifying_question=None,
            assistant_reply="ok",
            summary_compacted=turn > 4,
        )

    assert memory is not None
    assert memory.active_constraints["material"] == "cotton"
    assert memory.preferences["material"] == "cotton"
    assert memory.turn_index == 24


def test_memory_only_intents_are_detected_without_hijacking_new_search() -> None:
    assert detect_memory_intent("Nhắc lại sở thích hiện tại của tôi") == "memory_recall"
    assert detect_memory_intent("Tổng hợp cuộc trò chuyện") == "conversation_summary"
    assert detect_memory_intent("Nhắc lại rồi tìm sản phẩm mới") is None


def test_named_anchor_can_be_created_after_results_and_missing_anchor_is_unresolved() -> None:
    first = update_conversation_memory(
        None,
        message="Tìm hoodie",
        intent="search_product",
        filters={"category": "hoodie"},
        final_product_ids=[{"product_id": "A"}, {"product_id": "B"}],
        route="text_search",
        clarifying_question=None,
        assistant_reply="Có hai mẫu.",
        summary_compacted=False,
    )
    named = update_conversation_memory(
        first.model_dump(),
        message="Gọi danh sách này là alpha",
        intent="general_question",
        filters={},
        final_product_ids=[],
        route="non_product_answer",
        clarifying_question=None,
        assistant_reply="Đã lưu.",
        summary_compacted=False,
    )

    assert resolve_candidate_reference(
        "cái thứ 2 trong danh sách alpha", named.model_dump(), []
    ) == (["B"], "named:alpha")
    assert resolve_candidate_reference(
        "cái thứ 1 trong danh sách beta", named.model_dump(), []
    ) == ([], "unresolved:named:beta")
