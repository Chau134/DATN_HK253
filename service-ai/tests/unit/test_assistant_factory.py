from concurrent.futures import ThreadPoolExecutor
import time
from types import SimpleNamespace

from ecommerce_search_assistant.services.assistant import factory


def test_assistant_workflow_is_built_once_under_concurrent_first_calls(
    monkeypatch,
) -> None:
    factory._get_assistant_workflow_cached.cache_clear()
    sentinel = object()
    build_count = 0

    def build_once():
        nonlocal build_count
        build_count += 1
        time.sleep(0.05)
        return SimpleNamespace(saver=None)

    settings = SimpleNamespace(
        assistant_recent_message_limit=10,
        assistant_conversation_summary_max_chars=1_000,
        assistant_conversation_context_max_chars=2_000,
        assistant_evaluation_variant="rag",
    )
    monkeypatch.setattr(factory, "get_settings", lambda: settings)
    monkeypatch.setattr(
        factory,
        "build_checkpointer",
        lambda settings: build_once(),
    )
    monkeypatch.setattr(
        factory,
        "build_user_preference_store",
        lambda settings: None,
    )
    monkeypatch.setattr(
        factory,
        "build_assistant_graph",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        factory,
        "AssistantWorkflow",
        lambda **kwargs: sentinel,
    )
    monkeypatch.setattr(factory, "get_llm_service", lambda: None)
    monkeypatch.setattr(factory, "get_search_service", lambda: None)
    monkeypatch.setattr(factory, "SpringBootClient", lambda settings: None)

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(
                executor.map(lambda _: factory.get_assistant_workflow(), range(8))
            )
    finally:
        factory._get_assistant_workflow_cached.cache_clear()

    assert results == [sentinel] * 8
    assert build_count == 1
