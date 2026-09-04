from functools import lru_cache
from threading import Lock

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.infrastructure.springboot import SpringBootClient
from ecommerce_search_assistant.services.assistant.checkpointer import build_checkpointer
from ecommerce_search_assistant.services.assistant.preferences import build_user_preference_store
from ecommerce_search_assistant.services.assistant.workflow import AssistantWorkflow, build_assistant_graph
from ecommerce_search_assistant.services.llm.factory import get_llm_service
from ecommerce_search_assistant.services.search.factory import get_search_service


_assistant_workflow_init_lock = Lock()


@lru_cache
def _get_assistant_workflow_cached() -> AssistantWorkflow:
    settings = get_settings()
    eval_trace_enabled = getattr(settings, "assistant_eval_trace_enabled", False)
    checkpointer_handle = build_checkpointer(settings)
    preference_store = build_user_preference_store(settings)
    graph = build_assistant_graph(
        checkpointer=checkpointer_handle.saver,
        llm_service=get_llm_service(),
        search_service=get_search_service(),
        springboot_client=SpringBootClient(settings=settings),
        preference_store=preference_store,
        recent_message_limit=settings.assistant_recent_message_limit,
        conversation_summary_max_chars=settings.assistant_conversation_summary_max_chars,
        conversation_context_max_chars=settings.assistant_conversation_context_max_chars,
        eval_trace_enabled=eval_trace_enabled,
        evaluation_variant=settings.assistant_evaluation_variant,
    )
    return AssistantWorkflow(
        graph=graph,
        checkpointer_handle=checkpointer_handle,
        eval_trace_enabled=eval_trace_enabled,
    )


def get_assistant_workflow() -> AssistantWorkflow:
    # functools.lru_cache is thread-safe for its cache bookkeeping, but it may
    # execute the wrapped function more than once when concurrent first calls
    # miss the cache. Serializing that first construction prevents two
    # SqliteSaver.setup() calls from racing on the same database.
    with _assistant_workflow_init_lock:
        return _get_assistant_workflow_cached()
