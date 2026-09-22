from __future__ import annotations

import logging
import inspect
import re
import unicodedata
from dataclasses import dataclass, field
from hashlib import sha256
from threading import Lock, RLock
from time import monotonic
from typing import Any

from langgraph.graph import END, START, StateGraph

from ecommerce_search_assistant.core.metrics import assistant_metrics
from ecommerce_search_assistant.infrastructure.springboot import (
    SPRING_BOOT_UNAVAILABLE_WARNING,
    SpringBootClient,
)
from ecommerce_search_assistant.schemas.assistant import (
    AssistantChatResponse,
    AssistantEvaluationTrace,
    EvaluationTraceCandidate,
)
from ecommerce_search_assistant.schemas.chat import ChatRequest
from ecommerce_search_assistant.schemas.media import ImagePayload
from ecommerce_search_assistant.schemas.search import (
    HybridSearchRequest,
    ImageBoundingBox,
    ImageSearchRequest,
    SearchFilter,
    SearchResultItem,
    TextSearchRequest,
)
from ecommerce_search_assistant.services.assistant.state import AssistantState
from ecommerce_search_assistant.services.assistant.memory import (
    allowed_candidate_ids,
    detect_memory_intent,
    load_conversation_memory,
    resolve_candidate_reference,
    update_conversation_memory,
)
from ecommerce_search_assistant.services.assistant.preferences import (
    NullUserPreferenceStore,
    PreferenceVersionConflict,
    UserPreferenceStore,
    UserPreferenceUpdate,
)
from ecommerce_search_assistant.services.assistant.shop_knowledge import (
    resolve_shop_knowledge,
)
from ecommerce_search_assistant.services.llm.interfaces import LlmService
from ecommerce_search_assistant.services.llm.service import QueryUnderstanding
from ecommerce_search_assistant.services.search.constraints import resolve_search_constraints
from ecommerce_search_assistant.services.search.filtering import (
    analyze_query,
    detect_out_of_catalog_domain,
    extract_catalog_title_queries,
    merge_filters,
    merge_missing_filters,
)
from ecommerce_search_assistant.services.search.normalization import normalize_query_text
from ecommerce_search_assistant.services.search.routing import decide_search_route
from ecommerce_search_assistant.services.search.service import SearchService

logger = logging.getLogger(__name__)

_ORDINAL_PATTERNS = (
    (re.compile(r"\b(?:cai|cái|san pham|sản phẩm)?\s*(?:thu|thứ)\s*(\d+)\b", re.IGNORECASE), 1),
    (re.compile(r"\b(?:cai|cái)\s*(\d+)\b", re.IGNORECASE), 1),
)

_ATTACHED_IMAGE_REFERENCE_PHRASES = (
    "anh day",
    "anh nay",
    "cai nay",
    "do nay",
    "giong the nay",
    "giong vay",
    "hinh day",
    "hinh nay",
    "kieu nay",
    "mau nay",
    "mon nay",
    "nhu nay",
    "nhu vay",
    "san pham nay",
    "this item",
    "this model",
    "this one",
    "this product",
)

_ORDINAL_WORDS = {
    "đầu": 1,
    "dau": 1,
    "nhất": 1,
    "nhat": 1,
    "một": 1,
    "mot": 1,
    "hai": 2,
    "ba": 3,
    "bốn": 4,
    "bon": 4,
    "năm": 5,
    "nam": 5,
}


@dataclass
class AssistantWorkflow:
    graph: Any
    checkpointer_handle: Any | None = None
    eval_trace_enabled: bool = False
    _thread_locks: dict[str, RLock] = field(default_factory=dict, init=False, repr=False)
    _thread_locks_guard: Lock = field(default_factory=Lock, init=False, repr=False)

    def chat(self, request: ChatRequest) -> AssistantChatResponse:
        # Namespace checkpoint memory by both user and client-visible session so a
        # reused/guessed session ID cannot cross user boundaries.
        thread_id = f"{request.user_id}:{request.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        with self._thread_lock(thread_id):
            previous = self._checkpoint_values(config)
            if request.request_id:
                cached = previous.get("processed_requests", {}).get(request.request_id)
                if cached:
                    return AssistantChatResponse.model_validate(cached)
            if request.turn_sequence is not None:
                expected = int(previous.get("last_turn_sequence", 0)) + 1
                if request.turn_sequence != expected:
                    raise TurnSequenceConflict(expected=expected, received=request.turn_sequence)

            input_state: AssistantState = {
                "session_id": request.session_id,
                "user_id": request.user_id,
                "request_id": request.request_id,
                "turn_sequence": request.turn_sequence,
                "message": request.message or "",
                "image": request.image.model_dump() if request.image else None,
                "crop_box": request.crop_box.model_dump() if request.crop_box else None,
                "locale": request.locale,
            }
            started_at = monotonic()
            state = self.graph.invoke(input_state, config=config)
            total_duration = monotonic() - started_at
            stage_latencies = dict(state.get("stage_latencies_ms", {}))
            stage_latencies["total"] = round(total_duration * 1000, 3)
            state["stage_latencies_ms"] = stage_latencies
            turn_index = load_conversation_memory(state.get("conversation_memory")).turn_index
            assistant_metrics.observe_latency(
                turn_index=turn_index,
                duration_seconds=total_duration,
            )
            assistant_metrics.observe_turn(
                route=state.get("route", "unknown"),
                llm_call_count=state.get("llm_call_count", 0),
                springboot_call_count=state.get("springboot_call_count", 0),
                warnings=list(state.get("warnings", [])),
                stage_latencies_ms=stage_latencies,
            )
            return _response_from_state(
                state,
                request.session_id,
                include_evaluation_trace=self.eval_trace_enabled,
            )

    def _thread_lock(self, thread_id: str) -> RLock:
        with self._thread_locks_guard:
            return self._thread_locks.setdefault(thread_id, RLock())

    def _checkpoint_values(self, config: dict[str, Any]) -> dict[str, Any]:
        try:
            snapshot = self.graph.get_state(config)
            return dict(snapshot.values or {})
        except Exception:
            assistant_metrics.record_checkpoint_failure()
            logger.exception("assistant_checkpoint_read_failed")
            raise


class TurnSequenceConflict(ValueError):
    def __init__(self, *, expected: int, received: int) -> None:
        self.expected = expected
        self.received = received
        super().__init__(f"turn_sequence_conflict expected={expected} received={received}")


def _timed_node(name: str, node: Any):
    def wrapped(state: AssistantState) -> AssistantState:
        started_at = monotonic()
        updates = node(state)
        timings = {} if name == "start" else dict(state.get("stage_latencies_ms", {}))
        timings[name] = round((monotonic() - started_at) * 1000, 3)
        updates["stage_latencies_ms"] = timings
        return updates

    return wrapped


def build_assistant_graph(
    *,
    checkpointer: Any,
    llm_service: LlmService,
    search_service: SearchService,
    springboot_client: SpringBootClient,
    recent_message_limit: int = 12,
    conversation_summary_max_chars: int = 3000,
    conversation_context_max_chars: int = 8000,
    query_context_max_chars: int | None = None,
    preference_store: UserPreferenceStore | None = None,
    eval_trace_enabled: bool = False,
    evaluation_variant: str = "rag",
) -> Any:
    resolved_preference_store = preference_store or NullUserPreferenceStore()
    resolved_query_context_max_chars = min(
        conversation_context_max_chars,
        query_context_max_chars or conversation_context_max_chars,
    )
    builder = StateGraph(AssistantState)
    builder.add_node("start", _timed_node("start", _start))
    builder.add_node("load_context", _timed_node("load_context", _load_context(resolved_preference_store)))
    builder.add_node(
        "understand_query_with_llm",
        _timed_node(
            "understand_query",
            _understand_query_with_llm(
                llm_service,
                resolved_query_context_max_chars,
                search_service,
            ),
        ),
    )
    builder.add_node(
        "route_intent",
        _timed_node("route_intent", _route_intent_node(evaluation_variant)),
    )
    builder.add_node("text_search", _timed_node("text_search", _text_search(search_service)))
    builder.add_node("image_search", _timed_node("image_search", _image_search(search_service)))
    builder.add_node("hybrid_search", _timed_node("hybrid_search", _hybrid_search(search_service)))
    builder.add_node("clarification", _timed_node("clarification", _clarification))
    builder.add_node("memory_recall", _timed_node("memory_recall", _memory_recall_reply))
    builder.add_node(
        "conversation_reply",
        _timed_node(
            "conversation_reply",
            _conversation_reply(llm_service, conversation_context_max_chars),
        ),
    )
    builder.add_node("out_of_catalog_reply", _timed_node("out_of_catalog_reply", _out_of_catalog_reply))
    builder.add_node(
        "shop_knowledge_reply",
        _timed_node("shop_knowledge_reply", _shop_knowledge_reply(search_service)),
    )
    builder.add_node(
        "call_spring_boot_for_product_context",
        _timed_node("product_context", _call_spring_boot_for_product_context(springboot_client)),
    )
    builder.add_node(
        "generate_reply",
        _timed_node("generate_reply", _generate_reply(llm_service, conversation_context_max_chars)),
    )
    builder.add_node(
        "save_context",
        _timed_node(
            "save_context",
            _save_context(
                recent_message_limit,
                conversation_summary_max_chars,
                resolved_preference_store,
                eval_trace_enabled,
            ),
        ),
    )

    builder.add_edge(START, "start")
    builder.add_edge("start", "load_context")
    builder.add_edge("load_context", "understand_query_with_llm")
    builder.add_edge("understand_query_with_llm", "route_intent")
    builder.add_conditional_edges(
        "route_intent",
        _route_from_state,
        {
            "text_search": "text_search",
            "image_search": "image_search",
            "hybrid_search": "hybrid_search",
            "clarification": "clarification",
            "non_product_answer": "conversation_reply",
            "memory_recall": "memory_recall",
            "out_of_catalog_answer": "out_of_catalog_reply",
            "shop_knowledge_answer": "shop_knowledge_reply",
            "product_context": "call_spring_boot_for_product_context",
        },
    )
    builder.add_edge("text_search", "call_spring_boot_for_product_context")
    builder.add_edge("image_search", "call_spring_boot_for_product_context")
    builder.add_edge("hybrid_search", "call_spring_boot_for_product_context")
    builder.add_edge("clarification", "save_context")
    builder.add_edge("conversation_reply", "save_context")
    builder.add_edge("memory_recall", "save_context")
    builder.add_edge("out_of_catalog_reply", "save_context")
    builder.add_edge("shop_knowledge_reply", "save_context")
    builder.add_edge("call_spring_boot_for_product_context", "generate_reply")
    builder.add_edge("generate_reply", "save_context")
    builder.add_edge("save_context", END)
    return builder.compile(checkpointer=checkpointer)


def _start(state: AssistantState) -> AssistantState:
    return {
        "answer_target": None,
        "original_search_query": state.get("message", ""),
        "resolved_search_query": state.get("message", ""),
        "exact_product_query": None,
        "exact_product_code": None,
        "exact_match_resolved": None,
        "final_product_ids": [],
        "assistant_reply": "",
        "product_context": [],
        "out_of_catalog_domain": None,
        "shop_knowledge_topic": None,
        "shop_knowledge_answer": None,
        "referenced_product_ids": [],
        "warnings": [],
        "route": "text_search",
        "needs_image_search": False,
        "needs_text_search": False,
        "llm_call_count": 0,
        "springboot_call_count": 0,
        "stage_latencies_ms": {},
    }


def _resolve_catalog_identifiers(
    search_service: SearchService,
    identifiers: list[str],
) -> dict[str, list[str]]:
    resolver = getattr(search_service, "resolve_catalog_identifier_ids", None)
    if not callable(resolver) or not identifiers:
        return {identifier: [] for identifier in identifiers}
    try:
        resolved = resolver(identifiers)
    except Exception:
        logger.exception("assistant_catalog_identifier_resolution_failed")
        return {identifier: [] for identifier in identifiers}
    return {
        str(identifier): list(
            dict.fromkeys(str(value) for value in product_ids if value)
        )
        for identifier, product_ids in resolved.items()
    }


def _load_context(preference_store: UserPreferenceStore):
    def node(state: AssistantState) -> AssistantState:
        last_results = state.get("last_product_ids", [])
        message = state.get("message", "")
        if state.get("image") is not None and _references_attached_image(message):
            referenced, reference_source = [], "attached_image"
        else:
            referenced, reference_source = resolve_candidate_reference(
                message,
                state.get("conversation_memory"),
                last_results,
            )
        preferences: dict[str, Any] = {}
        preference_version = 0
        user_id = state.get("user_id", "").strip()
        if user_id:
            try:
                profile = preference_store.get(user_id)
                preferences = profile.prompt_payload()
                preference_version = profile.version
            except Exception:
                logger.exception("assistant_user_preferences_load_failed")
        return {
            "referenced_product_ids": referenced,
            "reference_resolution_source": reference_source,
            "user_preferences": preferences,
            "user_preference_version": preference_version,
        }

    return node


def _understand_query_with_llm(
    llm_service: LlmService,
    context_max_chars: int,
    search_service: SearchService | None = None,
):
    def node(state: AssistantState) -> AssistantState:
        message = state.get("message", "")
        if not message.strip():
            return {
                "rewritten_query": None,
                "filters": {},
                "clarifying_question": None,
                "needs_image_search": state.get("image") is not None,
                "needs_text_search": False,
            }
        memory_intent = detect_memory_intent(message)
        if memory_intent:
            return {
                "intent": memory_intent,
                "rewritten_query": message,
                "filters": {},
                "rule_filters": {},
                "llm_filters": {},
                "clarifying_question": None,
                "needs_image_search": False,
                "needs_text_search": False,
            }
        shop_knowledge = resolve_shop_knowledge(message)
        if shop_knowledge is not None:
            return {
                "intent": "general_question",
                "answer_target": "shop_policy",
                "rewritten_query": message,
                "filters": {},
                "rule_filters": {},
                "llm_filters": {},
                "clarifying_question": None,
                "needs_image_search": False,
                "needs_text_search": False,
                "out_of_catalog_domain": None,
                "shop_knowledge_topic": shop_knowledge.topic,
                "shop_knowledge_answer": shop_knowledge.answer,
            }
        reference_source = state.get("reference_resolution_source", "none")
        if reference_source.startswith("unresolved:"):
            clarification = (
                _missing_context_question(message)
                if reference_source == "unresolved:ordinal"
                else (
                    "Mình không còn đủ dữ liệu của danh sách được nhắc tới. "
                    "Bạn gửi lại tên hoặc danh sách sản phẩm giúp mình nhé."
                )
            )
            return {
                "intent": "ask_clarification",
                "rewritten_query": message,
                "filters": {},
                "rule_filters": {},
                "llm_filters": {},
                "clarifying_question": clarification,
                "needs_image_search": False,
                "needs_text_search": False,
            }
        started_at = monotonic()
        analysis = analyze_query(message)
        answer_target = _detect_answer_target(message)
        exact_product_code = _extract_exact_product_code(message)
        exact_product_query = _extract_exact_product_query(
            message,
            answer_target=answer_target,
        )
        # A new image attached to this turn supersedes product references from
        # prior turns, including referenced IDs inferred by the LLM.
        image_resolves_product_reference = (
            state.get("image") is not None
            and (
                analysis.intent == "find_similar"
                or _references_attached_image(message)
            )
        )
        if image_resolves_product_reference:
            # Phrases such as "shop có mẫu này không?" refer to the attached
            # image, not to a literal catalog title that should use exact lookup.
            answer_target = None
            exact_product_code = None
            exact_product_query = None
        catalog_title_queries = extract_catalog_title_queries(message)
        factual_title_query = (
            _extract_unquoted_factual_title(message)
            if not catalog_title_queries
            else None
        )
        if factual_title_query:
            catalog_title_queries = [factual_title_query]
        if exact_product_query and not catalog_title_queries:
            catalog_title_queries = [exact_product_query]
        catalog_title_query = (
            analysis.catalog_title_query
            or factual_title_query
            or exact_product_query
        )
        out_of_catalog_domain = detect_out_of_catalog_domain(message)
        raw_match_sources = analysis.metadata.get("match_sources", {})
        if out_of_catalog_domain:
            logger.info(
                "assistant_domain_rejected correlation_id=%s domain=%s total=%.1fms",
                state.get("session_id"),
                out_of_catalog_domain,
                (monotonic() - started_at) * 1000,
            )
            return {
                "original_search_query": message,
                "resolved_search_query": message,
                "catalog_title_query": catalog_title_query,
                "catalog_title_queries": catalog_title_queries,
                "answer_target": answer_target,
                "exact_product_query": exact_product_query,
                "exact_product_code": exact_product_code,
                "out_of_catalog_domain": out_of_catalog_domain,
                "rule_filters": {},
                "llm_filters": {},
                "filter_confidences": analysis.confidences,
                "filter_match_sources": (
                    {
                        str(key): str(value)
                        for key, value in raw_match_sources.items()
                    }
                    if isinstance(raw_match_sources, dict)
                    else {}
                ),
                "intent": "general_question",
                "rewritten_query": message,
                "filters": {},
                "clarifying_question": None,
                "needs_image_search": False,
                "needs_text_search": False,
            }
        locale = state.get("locale", "vi-VN")
        query_context = (
            _conversation_context(state, context_max_chars)
            if _query_requires_conversation_context(state, message, analysis)
            else None
        )
        cached_understanding = (
            getattr(search_service, "_understand_query_cached", None)
            if query_context is None
            else None
        )
        if callable(cached_understanding):
            understanding = cached_understanding(message, locale=locale)
        else:
            understanding = llm_service.analyze_user_query(
                message,
                locale=locale,
                conversation_context=query_context,
            )
        understanding = _prefer_rule_based_product_route(understanding, analysis)
        current_rule_filters = _sanitize_current_turn_filters(state, analysis.filters)
        current_llm_filters = _sanitize_current_turn_filters(
            state,
            understanding.filters,
        )
        current_rule_filters = _with_color_match_mode(message, current_rule_filters)
        current_llm_filters = _remove_inherited_llm_refinement_filters(
            message=message,
            llm_filters=current_llm_filters,
            rule_filters=current_rule_filters,
        )
        current_llm_filters = _with_color_match_mode(message, current_llm_filters)
        relative_filters = _resolved_relative_filters(
            state,
            current_llm_filters,
        )
        understanding = understanding.model_copy(
            update={
                "filters": relative_filters or current_llm_filters or SearchFilter(),
                "intent": (
                    "search_product" if relative_filters else understanding.intent
                ),
                "needs_text_search": (
                    True if relative_filters else understanding.needs_text_search
                ),
                "clarifying_question": (
                    None if relative_filters else understanding.clarifying_question
                ),
            }
        )
        filter_refinement_requested = _is_filter_refinement(
            message,
            current_rule_filters or current_llm_filters,
        ) and _extract_ordinal_index(message) is None
        if image_resolves_product_reference or filter_refinement_requested:
            # Filter refinements describe a new result set. Referenced IDs
            # inferred from conversation history must not divert the turn to
            # the product-context route and skip search.
            referenced_product_ids = []
        else:
            llm_referenced_product_ids = _validated_referenced_product_ids(
                understanding.referenced_product_ids,
                state.get("last_product_ids", []),
                state.get("conversation_memory"),
            )
            referenced_product_ids = (
                llm_referenced_product_ids
                or list(state.get("referenced_product_ids", []))
            )
        reference_update = {"referenced_product_ids": referenced_product_ids}
        warning_update = {
            "warnings": _dedupe_strings(
                list(state.get("warnings", []))
                + _consume_llm_warnings(
                    llm_service,
                    correlation_id=state.get("session_id"),
                )
            )
        }
        provenance_update: AssistantState = {
            "answer_target": answer_target,
            "original_search_query": message,
            "resolved_search_query": (
                catalog_title_query
                or analysis.semantic_query
                or analysis.corrected_query
                or message
            ),
            "rule_intent": analysis.intent,
            "catalog_title_query": catalog_title_query,
            "catalog_title_queries": catalog_title_queries,
            "exact_product_query": exact_product_query,
            "exact_product_code": exact_product_code,
            "out_of_catalog_domain": out_of_catalog_domain,
            "rule_filters": (
                current_rule_filters.model_dump(exclude_none=True)
                if current_rule_filters
                else {}
            ),
            "llm_filters": understanding.filters.model_dump(exclude_none=True),
            "filter_confidences": analysis.confidences,
            "filter_match_sources": (
                {str(key): str(value) for key, value in raw_match_sources.items()}
                if isinstance(raw_match_sources, dict)
                else {}
            ),
        }
        logger.info(
            "assistant_understand_latency total=%.1fms llm_call_count=%d",
            (monotonic() - started_at) * 1000,
            state.get("llm_call_count", 0) + 1,
        )
        if understanding.clarifying_question and not image_resolves_product_reference:
            return {
                **reference_update,
                **warning_update,
                **provenance_update,
                "intent": understanding.intent,
                "rewritten_query": understanding.rewritten_query,
                "filters": understanding.filters.model_dump(exclude_none=True),
                "clarifying_question": understanding.clarifying_question,
                "needs_image_search": understanding.needs_image_search,
                "needs_text_search": understanding.needs_text_search,
                "llm_call_count": state.get("llm_call_count", 0) + 1,
            }
        previous_filters = _last_filter_from_state(state)
        if _missing_required_context(
            message=message,
            current=understanding.filters,
            previous_filters=previous_filters,
            previous_results=state.get("last_product_ids", []),
        ) and not image_resolves_product_reference:
            return {
                **reference_update,
                **warning_update,
                **provenance_update,
                "intent": "ask_clarification",
                "rewritten_query": understanding.rewritten_query,
                "filters": understanding.filters.model_dump(exclude_none=True),
                "clarifying_question": _missing_context_question(message),
                "needs_image_search": False,
                "needs_text_search": False,
                "llm_call_count": state.get("llm_call_count", 0) + 1,
            }
        filters = _contextual_filters(
            message=message,
            current=understanding.filters,
            previous=previous_filters,
        )
        filters = _apply_cheaper_price_ceiling(
            message=message,
            filters=filters,
            previous_context=state.get("last_product_context", []),
        )
        return {
            **reference_update,
            **warning_update,
            **provenance_update,
            "intent": (
                "search_product"
                if image_resolves_product_reference
                else understanding.intent
            ),
            "rewritten_query": understanding.rewritten_query or analysis.semantic_query,
            "filters": filters.model_dump(exclude_none=True) if filters else {},
            "clarifying_question": (
                None
                if image_resolves_product_reference
                else understanding.clarifying_question
            ),
            "needs_image_search": (
                True
                if image_resolves_product_reference
                else understanding.needs_image_search
            ),
            "needs_text_search": (
                True
                if image_resolves_product_reference
                else understanding.needs_text_search
            ),
            "llm_call_count": state.get("llm_call_count", 0) + 1,
        }

    return node


def _prefer_rule_based_product_route(
    understanding: QueryUnderstanding,
    analysis: Any,
) -> QueryUnderstanding:
    """Keep explicit catalog questions on retrieval when the LLM calls them general chat."""
    if understanding.intent not in {"general_question", "small_talk"}:
        return understanding
    if not analysis.filters.category or analysis.intent not in {
        "search_product",
        "recommend_product",
        "find_similar",
        "compare_products",
        "product_information",
        "ask_availability",
        "size_consultation",
    }:
        return understanding
    intent = "compare_products" if analysis.intent == "compare_products" else "search_product"
    return understanding.model_copy(
        update={
            "intent": intent,
            "needs_text_search": True,
            "clarifying_question": None,
        }
    )


def _route_intent_node(evaluation_variant: str = "rag"):
    def route(state: AssistantState) -> AssistantState:
        if evaluation_variant == "llm_no_rag":
            return {"route": "non_product_answer"}
        return _rag_route_intent(state)

    return route


def _rag_route_intent(state: AssistantState) -> AssistantState:
    if state.get("shop_knowledge_topic"):
        return {"route": "shop_knowledge_answer"}
    current_image_is_reference = (
        state.get("image") is not None
        and _references_attached_image(state.get("message", ""))
    )
    if state.get("referenced_product_ids") and not current_image_is_reference:
        return {"route": "product_context"}
    if state.get("intent") in {"memory_recall", "conversation_summary"}:
        return {"route": "memory_recall"}
    if state.get("clarifying_question"):
        return {"route": "clarification"}
    if state.get("out_of_catalog_domain"):
        return {"route": "out_of_catalog_answer"}
    if state.get("catalog_title_query"):
        return {"route": "text_search"}
    decision = decide_search_route(
        query=state.get("message", ""),
        has_image=state.get("image") is not None,
        request_filters=_filter_from_state(state),
        understanding=_understanding_from_state(state),
    )
    return {"route": decision.route}


def _route_from_state(state: AssistantState) -> str:
    return state.get("route", "text_search")


def _text_search(search_service: SearchService):
    def node(state: AssistantState) -> AssistantState:
        started_at = monotonic()
        comparison_titles = state.get("catalog_title_queries", [])
        exact_lookup_requested = bool(
            state.get("exact_product_query") or state.get("exact_product_code")
        )
        exact_code = state.get("exact_product_code")
        if exact_code:
            identifier_ids = _resolve_catalog_identifiers(search_service, [exact_code]).get(
                exact_code,
                [],
            )
            if identifier_ids:
                results = [
                    SearchResultItem(
                        product_id=product_id,
                        score=1.0,
                        source="text",
                    ).model_dump()
                    for product_id in identifier_ids[:5]
                ]
                return {
                    "final_product_ids": results,
                    "rewritten_query": exact_code,
                    "filters": state.get("filters"),
                    "exact_match_resolved": True,
                    "warnings": _search_warnings(state, results),
                }
        resolved_titles = _resolve_catalog_titles(
            search_service,
            comparison_titles,
            exact_only=exact_lookup_requested and len(comparison_titles) == 1,
        )
        if len(comparison_titles) < 2 and state.get("rule_intent") == "compare_products":
            comparison_titles, resolved_titles = _resolve_unquoted_comparison_titles(
                search_service,
                state.get("message", ""),
            )
        if comparison_titles and all(resolved_titles.get(title) for title in comparison_titles):
            results: list[dict[str, Any]] = []
            seen_ids: set[str] = set()
            ordered_ids: list[str] = []
            # Reserve one slot per title first, then use remaining slots for
            # equivalent-title duplicates without exceeding Top 5.
            for title in comparison_titles:
                product_id = resolved_titles[title][0]
                if product_id not in seen_ids:
                    ordered_ids.append(product_id)
                    seen_ids.add(product_id)
            for title in comparison_titles:
                for product_id in resolved_titles[title][1:]:
                    if product_id not in seen_ids:
                        ordered_ids.append(product_id)
                        seen_ids.add(product_id)
                    if len(ordered_ids) >= 5:
                        break
                if len(ordered_ids) >= 5:
                    break
            results = [
                SearchResultItem(
                    product_id=product_id,
                    score=1.0,
                    source="text",
                ).model_dump()
                for product_id in ordered_ids[:5]
            ]
            logger.info(
                "assistant_catalog_title_resolved total=%.1fms title_count=%d result_count=%d embedding_skipped=true",
                (monotonic() - started_at) * 1000,
                len(comparison_titles),
                len(results),
            )
            return {
                "final_product_ids": results,
                "rewritten_query": " | ".join(comparison_titles),
                "catalog_title_queries": comparison_titles,
                "filters": state.get("filters"),
                "comparison_provenance": resolved_titles,
                "exact_match_resolved": True if exact_lookup_requested else None,
                "warnings": _search_warnings(state, results),
            }
        if len(comparison_titles) >= 2:
            return _comparison_text_search(
                state=state,
                search_service=search_service,
                titles=comparison_titles[:2],
                started_at=started_at,
            )
        rewritten_query = state.get("rewritten_query") or state.get("message", "")
        llm_filters = _filter_from_state(state)
        rule_filters = _filter_from_dict(state.get("rule_filters"))
        filters = merge_missing_filters(rule_filters, llm_filters)
        refinement_explicit_filters = (
            filters
            if _is_filter_refinement(state.get("message", ""), rule_filters)
            else None
        )
        constraints = resolve_search_constraints(
            rule_filters=rule_filters,
            llm_filters=llm_filters,
            explicit_filters=refinement_explicit_filters,
            confidences=state.get("filter_confidences", {}),
            match_sources=state.get("filter_match_sources", {}),
            # A quoted catalog title is already precise and should not be
            # constrained by an inferred taxonomy label. For ordinary category
            # searches, match the text-search endpoint and enforce trusted aliases.
            allow_category_hard=not bool(state.get("catalog_title_query")),
            allow_color_hard=True,
        )
        refined_results = _refine_previous_candidates(
            search_service=search_service,
            state=state,
            filters=filters,
            current_rule_filters=rule_filters,
        )
        if refined_results:
            logger.info(
                "assistant_candidate_refinement total=%.1fms previous_count=%d refined_count=%d embedding_skipped=true",
                (monotonic() - started_at) * 1000,
                len(state.get("last_product_ids", [])),
                len(refined_results),
            )
            return {
                "final_product_ids": refined_results,
                "rewritten_query": rewritten_query,
                "filters": (
                    filters.model_dump(exclude_none=True) if filters else {}
                ),
                "warnings": _search_warnings(state, refined_results),
            }
        embedding_query = state.get("resolved_search_query") or state.get("message", "")
        if hasattr(search_service, "search_text_prepared"):
            response, timings = _call_text_search_prepared(
                search_service,
                rewritten_query=rewritten_query,
                filters=filters,
                embedding_query=embedding_query,
                constraints=constraints,
                top_k=1 if _is_product_factual_question(state.get("message", "")) else None,
            )
        else:
            response = search_service.search_text(
                TextSearchRequest(query=embedding_query, filters=constraints.hard_filters)
            )
            timings = {}
        logger.info(
            "assistant_text_search_latency total=%.1fms used_prepared=%s",
            (monotonic() - started_at) * 1000,
            hasattr(search_service, "search_text_prepared"),
        )
        results = [result.model_dump() for result in response.results]
        warnings = _search_warnings(state, results)
        if timings.get("recovery_triggered"):
            warnings = _dedupe_strings(warnings + ["search_recovery_used"])
        elif not results and state.get("catalog_title_query"):
            warnings = _dedupe_strings(warnings + ["search_recovery_exhausted"])
        return {
            "final_product_ids": results,
            "rewritten_query": response.rewritten_query,
            "filters": response.filters.model_dump(exclude_none=True) if response.filters else state.get("filters"),
            "exact_match_resolved": False if exact_lookup_requested else None,
            "warnings": warnings,
        }

    return node


def _resolve_catalog_titles(
    search_service: SearchService,
    titles: list[str],
    *,
    exact_only: bool = False,
) -> dict[str, list[str]]:
    resolver = getattr(
        search_service,
        "resolve_exact_catalog_title_ids" if exact_only else "resolve_catalog_title_ids",
        None,
    )
    if not callable(resolver) and exact_only:
        resolver = getattr(search_service, "resolve_catalog_title_ids", None)
    if not callable(resolver) or not titles:
        return {}
    try:
        resolved = resolver(titles)
    except Exception:
        logger.exception("assistant_catalog_title_resolution_failed")
        return {}
    return {
        str(title): list(dict.fromkeys(str(value) for value in product_ids if value))
        for title, product_ids in resolved.items()
    }


def _refine_previous_candidates(
    *,
    search_service: SearchService,
    state: AssistantState,
    filters: SearchFilter | None,
    current_rule_filters: SearchFilter | None,
) -> list[dict[str, Any]]:
    previous = state.get("last_product_ids", [])
    if (
        not previous
        or current_rule_filters is None
        or not _is_filter_refinement(state.get("message", ""), current_rule_filters)
    ):
        return []
    refine = getattr(search_service, "filter_catalog_product_ids", None)
    if not callable(refine):
        return []
    previous_ids = [
        str(item["product_id"])
        for item in previous
        if item.get("product_id") is not None
    ]
    try:
        matched_ids = set(str(value) for value in refine(previous_ids, filters))
    except Exception:
        logger.exception("assistant_candidate_refinement_failed")
        return []
    return [
        item
        for item in previous
        if str(item.get("product_id")) in matched_ids
    ][:5]


def _comparison_text_search(
    *,
    state: AssistantState,
    search_service: SearchService,
    titles: list[str],
    started_at: float,
) -> AssistantState:
    """Retrieve each comparison entity independently and reserve one slot per leg."""
    responses: list[Any] = []
    timings_by_leg: list[dict[str, float]] = []
    unconstrained = resolve_search_constraints(
        rule_filters=None,
        llm_filters=None,
        explicit_filters=None,
        confidences={},
        match_sources={},
    )
    for title in titles:
        if hasattr(search_service, "search_text_prepared"):
            response, timings = _call_text_search_prepared(
                search_service,
                rewritten_query=title,
                filters=None,
                embedding_query=title,
                constraints=unconstrained,
                top_k=5,
            )
        else:
            response = search_service.search_text(
                TextSearchRequest(query=title, top_k=5)
            )
            timings = {}
        responses.append(response)
        timings_by_leg.append(timings)

    per_leg_results = [list(response.results) for response in responses]
    merged: list[SearchResultItem] = []
    seen_ids: set[str] = set()

    # First reserve a result for every resolved leg, then fill remaining Top 5
    # slots by rank/score without allowing one leg to crowd out the other.
    for results in per_leg_results:
        if results:
            candidate = results[0]
            if str(candidate.product_id) not in seen_ids:
                merged.append(candidate)
                seen_ids.add(str(candidate.product_id))
    remaining = sorted(
        (
            (rank, candidate)
            for results in per_leg_results
            for rank, candidate in enumerate(results[1:], start=2)
            if str(candidate.product_id) not in seen_ids
        ),
        key=lambda item: (item[0], -item[1].score),
    )
    for _, candidate in remaining:
        product_id = str(candidate.product_id)
        if product_id in seen_ids:
            continue
        merged.append(candidate)
        seen_ids.add(product_id)
        if len(merged) >= 5:
            break

    results = [result.model_dump() for result in merged[:5]]
    warnings = _search_warnings(state, results)
    if any(timing.get("recovery_triggered") for timing in timings_by_leg):
        warnings = _dedupe_strings(warnings + ["search_recovery_used"])
    if any(not leg for leg in per_leg_results):
        warnings = _dedupe_strings(warnings + ["comparison_leg_unresolved"])
    logger.info(
        "assistant_comparison_search_latency total=%.1fms leg_count=%d resolved_leg_count=%d result_count=%d",
        (monotonic() - started_at) * 1000,
        len(titles),
        sum(bool(leg) for leg in per_leg_results),
        len(results),
    )
    return {
        "final_product_ids": results,
        "rewritten_query": " | ".join(titles),
        "filters": state.get("filters"),
        "comparison_provenance": {
            title: [str(result.product_id) for result in leg]
            for title, leg in zip(titles, per_leg_results, strict=True)
        },
        "warnings": warnings,
    }


def _image_search(search_service: SearchService):
    def node(state: AssistantState) -> AssistantState:
        image_payload = _image_payload_from_state(state)
        if image_payload is None:
            return {"final_product_ids": []}
        response = search_service.search_image(
            ImageSearchRequest(
                image=image_payload,
                crop_box=_crop_box_from_state(state),
                filters=_filter_from_state(state),
            )
        )
        results = [result.model_dump() for result in response.results]
        return {
            "final_product_ids": results,
            "filters": response.filters.model_dump(exclude_none=True) if response.filters else state.get("filters"),
            "warnings": _search_warnings(state, results),
        }

    return node


def _hybrid_search(search_service: SearchService):
    def node(state: AssistantState) -> AssistantState:
        image_payload = _image_payload_from_state(state)
        rewritten_query = state.get("rewritten_query") or state.get("message")
        llm_filters = _filter_from_state(state)
        rule_filters = _filter_from_dict(state.get("rule_filters"))
        filters = merge_missing_filters(rule_filters, llm_filters)
        constraints = resolve_search_constraints(
            rule_filters=rule_filters,
            llm_filters=llm_filters,
            explicit_filters=None,
            confidences=state.get("filter_confidences", {}),
            match_sources=state.get("filter_match_sources", {}),
        )
        crop_box = _crop_box_from_state(state)
        if hasattr(search_service, "search_hybrid_prepared"):
            response = search_service.search_hybrid_prepared(
                rewritten_query=rewritten_query,
                original_query=state.get("resolved_search_query") or state.get("message"),
                image=image_payload,
                crop_box=crop_box,
                filters=filters,
                constraints=constraints,
            )
        else:
            response = search_service.search_hybrid(
                HybridSearchRequest(
                    query=rewritten_query,
                    image=image_payload,
                    crop_box=crop_box,
                    filters=filters,
                )
            )
        results = [result.model_dump() for result in response.results]
        return {
            "final_product_ids": results,
            "rewritten_query": response.rewritten_query,
            "filters": response.filters.model_dump(exclude_none=True) if response.filters else state.get("filters"),
            "warnings": _search_warnings(state, results),
        }

    return node


def _clarification(state: AssistantState) -> AssistantState:
    return {
        "assistant_reply": state.get("clarifying_question") or "Bạn muốn tìm sản phẩm theo màu, size, giá hay kiểu dáng nào?",
        "final_product_ids": [],
    }


def _memory_recall_reply(state: AssistantState) -> AssistantState:
    memory = load_conversation_memory(state.get("conversation_memory"))
    preferences = dict(state.get("user_preferences", {}))
    active = dict(memory.active_constraints)
    decisions = list(memory.confirmed_decisions)
    parts: list[str] = []
    if preferences:
        parts.append(f"Sở thích hiện tại: {_format_memory_mapping(preferences)}.")
    if active:
        parts.append(f"Tiêu chí đang dùng: {_format_memory_mapping(active)}.")
    if decisions:
        parts.append("Lựa chọn đã xác nhận: " + "; ".join(decisions[-3:]) + ".")
    normalized_message = _normalize_preference_text(state.get("message", ""))
    if (
        state.get("intent") == "conversation_summary"
        and "mau da bo" in normalized_message
    ):
        color_history = memory.superseded_values.get("colors", [])
        old_colors = _flatten_memory_values(color_history)
        current_colors = _flatten_memory_values(active.get("colors", []))
        if current_colors:
            parts.append(
                "Màu hiện tại là "
                + ", ".join(_localize_memory_value(value) for value in current_colors)
                + "."
            )
        if old_colors:
            parts.append(
                "Đã bỏ màu "
                + ", ".join(_localize_memory_value(value) for value in old_colors)
                + "."
            )
    if not parts:
        reply = "Mình chưa có sở thích hoặc lựa chọn nào được ghi nhớ từ cuộc trò chuyện này."
    elif state.get("intent") == "conversation_summary":
        reply = "Tóm tắt: " + " ".join(parts)
    else:
        reply = " ".join(parts)
    return {
        "assistant_reply": reply,
        "final_product_ids": [],
        "product_context": [],
    }


def _resolve_unquoted_comparison_titles(
    search_service: SearchService,
    message: str,
) -> tuple[list[str], dict[str, list[str]]]:
    normalized = normalize_query_text(message).strip(" .?!")
    normalized = re.sub(r"^so sanh\s+", "", normalized, count=1)
    pairs = [
        (normalized[: match.start()].strip(" ,"), normalized[match.end() :].strip(" ,"))
        for match in re.finditer(r"\s+va\s+", normalized)
    ]
    candidates = list(
        dict.fromkeys(title for pair in pairs for title in pair if len(title) >= 2)
    )
    resolved = _resolve_catalog_titles(search_service, candidates)
    for left, right in pairs:
        if resolved.get(left) and resolved.get(right):
            titles = [left, right]
            return titles, {title: resolved[title] for title in titles}
    return [], {}


def _is_product_factual_question(message: str) -> bool:
    normalized = normalize_query_text(message)
    return any(
        phrase in normalized
        for phrase in (
            "co mau gi",
            "lam tu chat lieu gi",
            "phu hop cho nam hay nu",
            "thuoc danh muc nao",
            "gia bao nhieu",
            "con hang khong",
            "het hang khong",
        )
    )


def _detect_answer_target(message: str) -> str | None:
    normalized = normalize_query_text(message)
    if any(
        phrase in normalized
        for phrase in ("gia bao nhieu", "bao nhieu tien", "gia hien tai")
    ):
        return "price"
    if any(
        phrase in normalized
        for phrase in ("con hang khong", "het hang khong", "co san khong")
    ):
        return "availability"
    if _extract_exact_product_code(message):
        return "exact_product"
    if _is_catalog_existence_query(message):
        return None
    if re.match(
        r"^\s*(?:shop\s+)?c[oó]\s+.+?\s+kh[oô]ng\b",
        message,
        re.IGNORECASE,
    ):
        return "exact_product"
    return None


def _is_catalog_existence_query(message: str) -> bool:
    normalized = normalize_query_text(message).strip()
    return bool(re.match(
        r"^(?:shop\s+)?co\s+ban\s+.+?\s+khong$",
        normalized,
    ))


def _extract_exact_product_code(message: str) -> str | None:
    match = re.search(
        r"\b(?:m[aã]|code)\s*[:#-]?\s*([a-z]{1,12}-\d{2,})\b",
        message,
        re.IGNORECASE,
    )
    return match.group(1).upper() if match else None


def _extract_exact_product_query(
    message: str,
    *,
    answer_target: str | None,
) -> str | None:
    text = re.sub(r"\s+", " ", message).strip()
    patterns: tuple[str, ...]
    if answer_target == "price":
        patterns = (
            r"^(?:sản phẩm\s+)?(.+?)\s+(?:hiện\s+)?có\s+giá\s+bao\s+nhiêu[?.!]*$",
            r"^(?:giá\s+của\s+)?(.+?)\s+(?:là|bao nhiêu)[?.!]*$",
        )
    elif answer_target == "availability":
        patterns = (
            r"^(.+?)\s+size\s+[a-z0-9-]+\s+(?:còn|hết)\s+hàng\s+không[?.!]*$",
            r"^(.+?)\s+size\s+[a-z0-9-]+\s+có\s+sẵn\s+không[?.!]*$",
        )
    elif answer_target == "exact_product":
        patterns = (
            r"^(?:shop\s+)?có\s+(.+?)\s+không[?.!]*(?:\s+nếu\s+.*)?$",
            r"^(?:cho\s+(?:tôi|mình|em)\s+)?(?:thông\s+tin\s+)?(?:sản\s+phẩm\s+)?(.+?)\s+mã\s+[a-z]{1,12}-\d{2,}.*$",
        )
    else:
        return None
    for pattern in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).strip(' \\t.,;:!?"”')
            return title if len(title.split()) >= 2 else None
    return None


def _extract_unquoted_factual_title(message: str) -> str | None:
    """Extract the product title preceding a factual-question suffix.

    Factual eval and real shoppers commonly paste an exact catalog title without
    quotes. Resolving that title deterministically avoids entity drift caused by
    query rewriting and attribute extraction from the question suffix.
    """
    normalized = normalize_query_text(message)
    suffixes = (
        "co mau gi",
        "lam tu chat lieu gi",
        "co chat lieu gi",
        "phu hop cho nam hay nu",
        "thuoc danh muc nao",
    )
    for suffix in suffixes:
        marker = f" {suffix}"
        if not normalized.endswith(marker):
            continue
        title = normalized[: -len(marker)].strip()
        title = re.sub(r"^(?:san pham|mau san pham)\s+", "", title).strip()
        if len(title.split()) >= 2 and title not in {"san pham nay", "mau nay"}:
            return title
    return None


def _format_memory_mapping(values: dict[str, Any]) -> str:
    labels = {
        "preferred_categories": "danh mục",
        "preferred_brands": "thương hiệu",
        "preferred_colors": "màu",
        "preferred_sizes": "size",
        "preferred_materials": "chất liệu",
        "preferred_gender": "giới tính",
        "budget_min": "giá tối thiểu",
        "budget_max": "giá tối đa",
        "style_notes": "phong cách",
        "avoidance_notes": "cần tránh",
        "category": "danh mục",
        "brand": "thương hiệu",
        "colors": "màu",
        "sizes": "size",
        "material": "chất liệu",
        "gender": "giới tính",
        "min_price": "giá tối thiểu",
        "max_price": "giá tối đa",
    }
    rendered = []
    for key, value in values.items():
        if value in (None, [], ""):
            continue
        if isinstance(value, list):
            text = ", ".join(_localize_memory_value(item) for item in value)
        else:
            text = _localize_memory_value(value)
        rendered.append(f"{labels.get(key, key)} {text}")
    return "; ".join(rendered) or "chưa có dữ liệu"


def _localize_memory_value(value: Any) -> str:
    aliases = {
        "black": "đen",
        "blue": "xanh",
        "red": "đỏ",
        "gray": "xám",
        "grey": "xám",
        "white": "trắng",
        "brown": "nâu",
        "green": "xanh lá",
        "purple": "tím",
        "men": "nam",
        "women": "nữ",
        "unisex": "unisex",
    }
    text = str(value).strip()
    localized = aliases.get(text.lower(), text)
    return localized.upper() if text.lower() in {"xs", "s", "m", "l", "xl", "xxl"} else localized


def _flatten_memory_values(values: Any) -> list[Any]:
    flattened: list[Any] = []
    for value in values if isinstance(values, list) else [values]:
        if isinstance(value, list):
            flattened.extend(value)
        elif value not in (None, ""):
            flattened.append(value)
    return list(dict.fromkeys(flattened))


def _conversation_reply(llm_service: LlmService, context_max_chars: int):
    def node(state: AssistantState) -> AssistantState:
        started_at = monotonic()
        reply = llm_service.generate_conversational_reply(
            message=state.get("message", ""),
            conversation_context=_conversation_context(state, context_max_chars),
        )
        llm_call_count = state.get("llm_call_count", 0) + 1
        logger.info(
            "assistant_conversation_reply_latency total=%.1fms llm_call_count=%d intent=%s",
            (monotonic() - started_at) * 1000,
            llm_call_count,
            state.get("intent"),
        )
        warnings = _dedupe_strings(
            list(state.get("warnings", []))
            + _consume_llm_warnings(
                llm_service,
                correlation_id=state.get("session_id"),
            )
        )
        return {
            "assistant_reply": reply,
            "final_product_ids": [],
            "llm_call_count": llm_call_count,
            "warnings": warnings,
        }

    return node


def _out_of_catalog_reply(state: AssistantState) -> AssistantState:
    domain = state.get("out_of_catalog_domain")
    replies = {
        "medical": (
            "Em không thể tư vấn thuốc hoặc điều trị y tế. "
            "Trợ lý này chỉ hỗ trợ tìm và so sánh sản phẩm thời trang trong catalog."
        ),
        "travel_service": (
            "Catalog hiện không có vé máy bay hay dịch vụ du lịch. "
            "Em chỉ hỗ trợ mua sắm và tư vấn sản phẩm thời trang."
        ),
        "electronics": (
            "Catalog hiện không có sản phẩm điện tử hoặc máy tính. "
            "Em chỉ hỗ trợ tìm và so sánh sản phẩm thời trang."
        ),
        "appliance": (
            "Catalog hiện không có đồ gia dụng. "
            "Em chỉ hỗ trợ tìm và so sánh sản phẩm thời trang."
        ),
        "vehicle": (
            "Catalog hiện không có phương tiện hoặc xe điện. "
            "Em chỉ hỗ trợ tìm và so sánh sản phẩm thời trang."
        ),
        "shop_policy": (
            "Hiện tại trợ lý chưa hỗ trợ dữ liệu chính sách này trong hệ thống. "
            "Bạn vui lòng kiểm tra trang chính sách của shop hoặc liên hệ CSKH để được xác nhận."
        ),
        "unsupported_claim": (
            "Hiện tại trợ lý chưa hỗ trợ xác minh thông tin này từ catalog. "
            "Mình không muốn khẳng định khi chưa có dữ liệu đáng tin cậy."
        ),
    }
    return {
        "assistant_reply": replies.get(
            domain,
            "Yêu cầu này nằm ngoài catalog thời trang mà em có thể hỗ trợ.",
        ),
        "final_product_ids": [],
        "product_context": [],
    }


def _shop_knowledge_reply(search_service: SearchService):
    def node(state: AssistantState) -> AssistantState:
        if state.get("shop_knowledge_topic") != "catalog_overview":
            return {
                "assistant_reply": state.get("shop_knowledge_answer", ""),
                "final_product_ids": [],
                "product_context": [],
            }

        warnings = list(state.get("warnings", []))
        try:
            categories = search_service.catalog_category_counts()
        except Exception:
            logger.exception("assistant_catalog_overview_load_failed")
            categories = []
            warnings.append("catalog_overview_unavailable")

        if not categories:
            reply = (
                "Hiện tại mình chưa đọc được danh mục sản phẩm đang bán từ catalog, "
                "nên chưa thể liệt kê chính xác và không muốn tự suy đoán."
            )
        else:
            category_text = ", ".join(
                f"{category.name_vi} ({category.count})"
                for category in categories
            )
            reply = (
                f"Theo catalog hiện tại, shop có {len(categories)} loại sản phẩm đang bán: "
                f"{category_text}. Danh sách này được lấy trực tiếp từ các sản phẩm active "
                "và còn bán trong hệ thống."
            )
        return {
            "assistant_reply": reply,
            "final_product_ids": [],
            "product_context": [],
            "warnings": _dedupe_strings(warnings),
        }

    return node


def _call_spring_boot_for_product_context(springboot_client: SpringBootClient):
    def node(state: AssistantState) -> AssistantState:
        started_at = monotonic()
        client_settings = getattr(springboot_client, "settings", None)
        context_limit = getattr(client_settings, "assistant_product_context_limit", 5)
        recommendation_limit = getattr(
            client_settings,
            "assistant_recommendation_limit",
            3,
        )
        displayed_product_limit = min(context_limit, recommendation_limit)
        if state.get("referenced_product_ids"):
            product_ids = state["referenced_product_ids"]
            final_product_ids = [
                {"product_id": product_id, "score": 1.0, "source": "hybrid"}
                for product_id in product_ids
            ]
        else:
            final_product_ids = state.get("final_product_ids", [])
        # The reply prompt recommends every provided candidate. Keep the API
        # product cards, prompt candidates, context and conversation memory on
        # the same bounded list so "ba mẫu" can never accompany five images.
        final_product_ids = final_product_ids[:displayed_product_limit]
        product_ids = [item["product_id"] for item in final_product_ids]

        product_context: list[dict[str, Any]] = []
        warnings: list[str] = list(state.get("warnings", []))
        springboot_call_count = 0
        try:
            if product_ids:
                metadata_result = springboot_client.get_products_by_ids(product_ids)
                springboot_call_count += 1
                product_context.extend(_compact_product_context(metadata_result.data))
                warnings.extend(metadata_result.warnings)
        except Exception:
            logger.exception("assistant_product_context_load_failed")
            warnings.append(SPRING_BOOT_UNAVAILABLE_WARNING)
        unfiltered_context_count = len(product_context)
        product_context = _filter_context_by_requested_color_shade(
            state.get("message", ""),
            product_context,
        )
        if len(product_context) != unfiltered_context_count:
            allowed_ids = {
                str(item.get("product_id") or item.get("id"))
                for item in product_context
                if item.get("product_id") is not None or item.get("id") is not None
            }
            final_product_ids = [
                item
                for item in final_product_ids
                if str(item.get("product_id")) in allowed_ids
            ]
            warnings.append("exact_color_shade_filter_applied")
            if not product_context:
                warnings.append("no_search_results")
        total_springboot_calls = state.get("springboot_call_count", 0) + springboot_call_count
        logger.info(
            "assistant_product_context_latency total=%.1fms requested_product_count=%d context_product_count=%d "
            "springboot_call_count=%d",
            (monotonic() - started_at) * 1000,
            len(product_ids),
            len(product_context),
            total_springboot_calls,
        )
        return {
            "final_product_ids": final_product_ids,
            "product_context": product_context,
            "warnings": _dedupe_strings(warnings),
            "springboot_call_count": total_springboot_calls,
            "product_context_limit": context_limit,
        }

    return node


def _generate_reply(llm_service: LlmService, context_max_chars: int):
    def node(state: AssistantState) -> AssistantState:
        started_at = monotonic()
        results = [_result_from_dict(item) for item in state.get("final_product_ids", [])]
        product_context = state.get("product_context", [])
        comparison_titles = state.get("catalog_title_queries", [])
        comparison_requested = _is_comparison_turn(state)
        if (
            comparison_requested
            and (
                "comparison_leg_unresolved" in state.get("warnings", [])
                or len(state.get("product_context", [])) < 2
            )
        ):
            return {
                "assistant_reply": _missing_comparison_context_reply(comparison_titles),
                "llm_call_count": state.get("llm_call_count", 0),
                "warnings": state.get("warnings", []),
            }
        if results and not product_context:
            logger.warning(
                "assistant_reply_skipped_missing_product_context result_count=%d",
                len(results),
            )
            return {
                "assistant_reply": (
                    f"Em đã tìm thấy {len(results)} sản phẩm phù hợp và hiển thị bên dưới. "
                    "Hiện em chưa tải đủ thông tin chi tiết để mô tả chính xác; "
                    "bạn có thể mở từng sản phẩm để xem thêm nhé."
                ),
                "llm_call_count": state.get("llm_call_count", 0),
                "warnings": state.get("warnings", []),
            }
        structured_reply = _structured_catalog_reply(state)
        if structured_reply:
            logger.info(
                "assistant_generate_reply_latency total=%.1fms llm_call_count=%d result_count=%d "
                "context_count=%d structured=true",
                (monotonic() - started_at) * 1000,
                state.get("llm_call_count", 0),
                len(results),
                len(state.get("product_context", [])),
            )
            return {
                "assistant_reply": structured_reply,
                "llm_call_count": state.get("llm_call_count", 0),
                "warnings": state.get("warnings", []),
            }
        reply = llm_service.generate_assistant_reply(
            message=state.get("message", ""),
            search_results=results,
            product_context=product_context,
            conversation_context=_conversation_context(state, context_max_chars),
            is_reference_followup=bool(state.get("referenced_product_ids")),
        )
        llm_call_count = state.get("llm_call_count", 0) + 1
        logger.info(
            "assistant_generate_reply_latency total=%.1fms llm_call_count=%d result_count=%d context_count=%d",
            (monotonic() - started_at) * 1000,
            llm_call_count,
            len(results),
            len(state.get("product_context", [])),
        )
        warnings = _dedupe_strings(
            list(state.get("warnings", []))
            + _consume_llm_warnings(
                llm_service,
                correlation_id=state.get("session_id"),
            )
        )
        return {
            "assistant_reply": reply,
            "llm_call_count": llm_call_count,
            "warnings": warnings,
        }

    return node


def _structured_catalog_reply(state: AssistantState) -> str | None:
    raw_context = [
        item for item in state.get("product_context", []) if isinstance(item, dict)
    ]
    context = [
        item for item in raw_context
        if isinstance(item, dict) and _has_structured_product_context(item)
    ]
    if state.get("exact_match_resolved") is False:
        return _missing_exact_product_reply(state, raw_context)
    answer_target = state.get("answer_target")
    if answer_target == "price":
        return _structured_price_reply(raw_context)
    if answer_target == "availability":
        return _structured_availability_reply(state, raw_context)
    if answer_target == "exact_product" and raw_context:
        product = raw_context[0]
        return (
            "Có, shop có sản phẩm "
            f"{_context_value(product, 'title_vi', 'title')}."
        )
    cheaper_refinement = _is_cheaper_refinement(state.get("message", ""))
    if not context and cheaper_refinement:
        return "Mình chưa tìm thấy sản phẩm nào rẻ hơn các lựa chọn ở lượt trước."
    if not context:
        return None
    message = state.get("message", "")
    normalized = normalize_query_text(message)
    if _is_catalog_existence_query(message):
        suggestions = "; ".join(
            f"{index}. {_context_value(product, 'title_vi', 'title')}"
            for index, product in enumerate(context[:3], start=1)
        )
        return (
            "Có, shop có các sản phẩm phù hợp với yêu cầu của bạn: "
            f"{suggestions}."
        )
    if _is_product_factual_question(message):
        product = context[0]
        title = _context_value(product, "title_vi", "title")
        if "co mau gi" in normalized:
            return f"{title} có màu {_context_value(product, 'base_colour_vi', 'base_colour')}."
        if "lam tu chat lieu gi" in normalized:
            return f"{title} được làm từ chất liệu {_context_value(product, 'material_vi', 'material')}."
        if "phu hop cho nam hay nu" in normalized:
            return f"{title} phù hợp cho {_context_value(product, 'gender_vi', 'gender')}."
        if "thuoc danh muc nao" in normalized:
            return f"{title} thuộc danh mục {_context_category(product)}."
    if _is_comparison_turn(state) and len(context) >= 2:
        left, right = context[:2]
        left_title = _context_value(left, "title_vi", "title")
        right_title = _context_value(right, "title_vi", "title")
        comparison_summary = _structured_comparison_summary(left, right)
        recommendation = _structured_comparison_recommendation(state, left, right)
        return (
            f"So sánh {left_title} và {right_title}: "
            f"{left_title} thuộc danh mục {_context_category(left)}, "
            f"có màu {_context_value(left, 'base_colour_vi', 'base_colour')}, "
            f"chất liệu {_context_value(left, 'material_vi', 'material')}; "
            f"{right_title} thuộc danh mục {_context_category(right)}, "
            f"có màu {_context_value(right, 'base_colour_vi', 'base_colour')}, "
            f"chất liệu {_context_value(right, 'material_vi', 'material')}. "
            f"{comparison_summary}{recommendation}"
        )
    if state.get("referenced_product_ids"):
        product = context[0]
        title = _context_value(product, "title_vi", "title")
        return (
            f"{title} thuộc danh mục {_context_category(product)}, "
            f"có màu {_context_value(product, 'base_colour_vi', 'base_colour')}, "
            f"chất liệu {_context_value(product, 'material_vi', 'material')} và "
            f"phù hợp cho {_context_value(product, 'gender_vi', 'gender')}."
        )
    category = _context_category(context[0])
    options = []
    for index, product in enumerate(context[:3], start=1):
        price_text = ""
        if cheaper_refinement:
            effective_price = _effective_context_price(product)
            if effective_price is not None:
                price_text = f", giá {_format_vnd(effective_price)}"
        options.append(
            f"{index}. {_context_value(product, 'title_vi', 'title')} — "
            f"màu {_context_value(product, 'base_colour_vi', 'base_colour')}, "
            f"chất liệu {_context_value(product, 'material_vi', 'material')}, "
            f"phù hợp cho {_context_value(product, 'gender_vi', 'gender')}"
            f"{price_text}"
        )
    return f"Gợi ý các sản phẩm {category} phù hợp nhu cầu: " + "; ".join(options) + "."


def _structured_comparison_summary(
    left: dict[str, Any],
    right: dict[str, Any],
) -> str:
    dimensions: list[tuple[str, str, str]] = [
        ("danh mục", _context_category(left), _context_category(right)),
        (
            "màu",
            _context_value(left, "base_colour_vi", "base_colour"),
            _context_value(right, "base_colour_vi", "base_colour"),
        ),
        (
            "chất liệu",
            _context_value(left, "material_vi", "material"),
            _context_value(right, "material_vi", "material"),
        ),
    ]
    left_price = _comparison_price(left)
    right_price = _comparison_price(right)
    if left_price is not None and right_price is not None:
        dimensions.append(("giá", _format_vnd(left_price), _format_vnd(right_price)))
    similarities: list[str] = []
    differences: list[str] = []
    for label, left_value, right_value in dimensions:
        if normalize_query_text(str(left_value)) == normalize_query_text(str(right_value)):
            similarities.append(f"cùng {label} {left_value}")
        else:
            differences.append(f"{label}: {left_value} so với {right_value}")
    similarity_text = (
        ", ".join(similarities)
        if similarities
        else "không có danh mục, màu hoặc chất liệu nào trùng hoàn toàn"
    )
    difference_text = (
        "; ".join(differences)
        if differences
        else "không có khác biệt trong các tiêu chí này"
    )
    return f"Điểm giống: {similarity_text}. Điểm khác: {difference_text}."


def _is_comparison_turn(state: AssistantState) -> bool:
    if (
        state.get("intent") == "compare_products"
        or state.get("rule_intent") == "compare_products"
    ):
        return True
    normalized = normalize_query_text(state.get("message", ""))
    return any(phrase in normalized for phrase in ("so sanh", "compare"))


def _missing_comparison_context_reply(comparison_titles: list[str]) -> str:
    if len(comparison_titles) >= 2:
        return (
            "Em chưa lấy đủ dữ liệu để so sánh cả "
            f'"{comparison_titles[0]}" và "{comparison_titles[1]}". '
            "Bạn kiểm tra lại tên hai sản phẩm giúp em nhé."
        )
    return (
        "Em chưa lấy đủ dữ liệu của hai sản phẩm được nhắc tới để so sánh. "
        "Bạn gửi lại tên hoặc danh sách sản phẩm giúp em nhé."
    )


def _structured_comparison_recommendation(
    state: AssistantState,
    left: dict[str, Any],
    right: dict[str, Any],
) -> str:
    normalized_message = normalize_query_text(state.get("message", ""))
    if not any(
        phrase in normalized_message
        for phrase in ("goi y", "phu hop hon", "nen chon", "recommend", "which one")
    ):
        return ""

    memory = load_conversation_memory(state.get("conversation_memory"))
    requested_colors = memory.active_constraints.get("colors") or []
    if not isinstance(requested_colors, list):
        requested_colors = [requested_colors]
    left_color_score = _preferred_color_match_score(left, requested_colors)
    right_color_score = _preferred_color_match_score(right, requested_colors)
    left_price = _comparison_price(left)
    right_price = _comparison_price(right)

    chosen = left
    chosen_price, other_price = left_price, right_price
    reasons: list[str] = []
    if right_color_score > left_color_score:
        chosen = right
        chosen_price, other_price = right_price, left_price
        reasons.append("khớp sát hơn với ưu tiên màu hiện tại")
    elif left_color_score > right_color_score:
        reasons.append("khớp sát hơn với ưu tiên màu hiện tại")
    elif (
        left_price is not None
        and right_price is not None
        and right_price < left_price
    ):
        chosen = right
        chosen_price, other_price = right_price, left_price

    if (
        chosen_price is not None
        and other_price is not None
        and chosen_price < other_price
    ):
        reasons.append(
            f"giá {_format_vnd(chosen_price)}, thấp hơn {_format_vnd(other_price)}"
        )
    if not reasons:
        reasons.append("các thuộc tính công bố phù hợp tương đương và mẫu này được xếp trước")

    chosen_title = _context_value(chosen, "title_vi", "title")
    purpose = " để đi làm" if "di lam" in normalized_message else ""
    return (
        f" Gợi ý: chọn {chosen_title}{purpose} vì "
        f"{' và '.join(dict.fromkeys(reasons))}."
    )


def _preferred_color_match_score(
    product: dict[str, Any],
    requested_colors: list[Any],
) -> int:
    if not requested_colors:
        return 0
    fields = [
        normalize_query_text(str(product.get(field_name, "")))
        for field_name in ("base_colour", "base_colour_vi", "colors", "colors_vi")
    ]
    score = 0
    for value in requested_colors:
        aliases = {
            normalize_query_text(str(value)),
            normalize_query_text(_localize_memory_value(value)),
        }
        aliases.discard("")
        if any(field in aliases for field in fields):
            score = max(score, 2)
        elif any(alias in field for alias in aliases for field in fields):
            score = max(score, 1)
    return score


def _comparison_price(product: dict[str, Any]) -> float | None:
    price = product.get("price") if isinstance(product.get("price"), dict) else {}
    value = price.get("price") or price.get("effective_price") or price.get("discounted_price")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _structured_price_reply(context: list[dict[str, Any]]) -> str:
    if not context:
        return "Mình chưa có đủ dữ liệu giá của sản phẩm này để xác nhận."
    product = context[0]
    title = _context_value(product, "title_vi", "title")
    price = product.get("price") if isinstance(product.get("price"), dict) else {}
    effective = price.get("effective_price") or price.get("discounted_price") or price.get("price")
    original = price.get("price")
    if effective is None:
        return f"Mình chưa có đủ dữ liệu giá của {title} để xác nhận."
    reply = f"Giá hiện tại của {title} là {_format_vnd(effective)}."
    if original is not None and round(float(original)) != round(float(effective)):
        reply += f" Giá gốc là {_format_vnd(original)}."
    return reply


def _structured_availability_reply(
    state: AssistantState,
    context: list[dict[str, Any]],
) -> str:
    if not context:
        return "Mình chưa có đủ dữ liệu tồn kho của sản phẩm này để xác nhận."
    product = context[0]
    title = _context_value(product, "title_vi", "title")
    requested_size = _requested_size(state)
    if not requested_size:
        return f"Bạn cho mình biết size cần kiểm tra của {title} nhé."
    variants = product.get("variants") if isinstance(product.get("variants"), list) else []
    variant = next(
        (
            item
            for item in variants
            if isinstance(item, dict)
            and str(
                item.get("unified_size") or item.get("option_value") or ""
            ).strip().casefold()
            == requested_size.casefold()
        ),
        None,
    )
    size_label = requested_size.upper()
    if variant is None:
        return f"Mình chưa có dữ liệu tồn kho size {size_label} của {title}."
    available = bool(variant.get("active", True)) and bool(variant.get("available"))
    inventory = variant.get("inventory_count")
    if inventory is not None:
        available = available and int(inventory) > 0
    if available:
        return f"Có, {title} size {size_label} hiện còn hàng."
    return f"Không, {title} size {size_label} hiện đã hết hàng."


def _missing_exact_product_reply(
    state: AssistantState,
    context: list[dict[str, Any]],
) -> str:
    requested = state.get("exact_product_code") or state.get("exact_product_query")
    label = f'“{requested}”' if requested else "sản phẩm bạn yêu cầu"
    refusal = f"Không, shop không tìm thấy {label} trong danh mục hiện tại."
    suggestions = [
        _context_value(item, "title_vi", "title")
        for item in context[:3]
        if item.get("title_vi") or item.get("title")
    ]
    if not suggestions:
        return refusal
    rendered = "; ".join(
        f"{index}. {title}" for index, title in enumerate(suggestions, start=1)
    )
    return f"{refusal} Bạn có thể tham khảo các sản phẩm tương tự: {rendered}."


def _requested_size(state: AssistantState) -> str | None:
    filters = state.get("filters") or {}
    sizes = filters.get("sizes") if isinstance(filters, dict) else None
    if isinstance(sizes, list) and sizes:
        return str(sizes[0]).strip()
    match = re.search(r"\bsize\s+([a-z0-9-]+)\b", state.get("message", ""), re.IGNORECASE)
    return match.group(1) if match else None


def _format_vnd(value: Any) -> str:
    amount = round(float(value))
    return f"{amount:,}".replace(",", ".") + " VND"


def _has_structured_product_context(product: dict[str, Any]) -> bool:
    has_title = any(product.get(key) not in (None, "") for key in ("title_vi", "title"))
    has_attributes = any(
        product.get(key) not in (None, "")
        for key in (
            "base_colour_vi",
            "base_colour",
            "material_vi",
            "material",
            "gender_vi",
            "gender",
        )
    )
    return bool(has_title and (has_attributes or product.get("categories")))


def _context_value(product: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = product.get(key)
        if value not in (None, ""):
            return str(value)
    return "chưa có dữ liệu"


def _context_category(product: dict[str, Any]) -> str:
    categories = product.get("categories")
    if isinstance(categories, list):
        for category in categories:
            if isinstance(category, dict):
                value = category.get("name_vi") or category.get("name")
                if value:
                    return str(value)
    return _context_value(product, "category_vi", "category")


def _save_context(
    recent_message_limit: int,
    summary_max_chars: int,
    preference_store: UserPreferenceStore,
    eval_trace_enabled: bool,
):
    def node(state: AssistantState) -> AssistantState:
        final_product_ids = state.get("final_product_ids", [])
        updates: AssistantState = {"image": None, "crop_box": None}
        if final_product_ids:
            updates["last_product_ids"] = final_product_ids
        product_context = state.get("product_context", [])
        if final_product_ids and product_context:
            updates["last_product_context"] = product_context
        filters = state.get("filters")
        if filters:
            updates["last_filters"] = filters

        new_messages = _current_turn_messages(state)
        combined_messages = [*state.get("recent_messages", []), *new_messages]
        dropped_messages = combined_messages[:-recent_message_limit]
        updates["recent_messages"] = combined_messages[-recent_message_limit:]
        summary_compacted = _summary_requires_compaction(
            state.get("conversation_summary"),
            dropped_messages,
            summary_max_chars,
        )
        updates["conversation_summary"] = _extend_conversation_summary(
            state.get("conversation_summary"),
            dropped_messages,
            summary_max_chars,
        )
        preferences, preference_warning, preference_version = _save_long_term_preferences(
            state,
            preference_store,
        )
        updates["user_preferences"] = preferences
        updates["user_preference_version"] = preference_version
        if preference_warning:
            updates["warnings"] = _dedupe_strings(
                [*state.get("warnings", []), preference_warning]
            )
            if preference_warning == "preference_update_unresolved":
                updates["assistant_reply"] = (
                    "Mình chưa xác định được bạn muốn sửa sở thích nào và giá trị mới là gì. "
                    "Bạn nói rõ giúp mình, ví dụ: ‘đổi màu ưa thích sang xanh’."
                )
        memory = update_conversation_memory(
            state.get("conversation_memory"),
            message=state.get("message", ""),
            intent=state.get("intent"),
            filters=_memory_filters_for_turn(state),
            final_product_ids=final_product_ids,
            route=state.get("route", "unknown"),
            clarifying_question=state.get("clarifying_question"),
            assistant_reply=state.get("assistant_reply", ""),
            summary_compacted=summary_compacted,
        )
        updates["conversation_memory"] = memory.model_dump()
        if state.get("turn_sequence") is not None:
            updates["last_turn_sequence"] = int(state["turn_sequence"])
        if state.get("request_id"):
            processed = dict(state.get("processed_requests", {}))
            cached_state = {**state, **updates}
            processed[state["request_id"]] = _response_payload_from_state(
                cached_state,
                include_evaluation_trace=eval_trace_enabled,
            )
            updates["processed_requests"] = dict(list(processed.items())[-50:])

        summary = updates["conversation_summary"] or ""
        assistant_metrics.observe_memory(
            turn_index=memory.turn_index,
            recent_message_count=len(updates["recent_messages"]),
            summary_chars=len(summary),
            summary_compaction_count=memory.summary_compaction_count,
            summary_max_chars=summary_max_chars,
            memory_sources=_memory_sources_used(state),
            reference_resolution_source=state.get("reference_resolution_source", "none"),
        )

        logger.info(
            "assistant_chat_metrics route=%s llm_call_count=%d springboot_call_count=%d "
            "final_product_count=%d conversation_turn_index=%d recent_message_count=%d "
            "summary_chars=%d summary_compaction_count=%d memory_source_used=%s "
            "reference_resolution_source=%s",
            state.get("route"),
            state.get("llm_call_count", 0),
            state.get("springboot_call_count", 0),
            len(final_product_ids),
            memory.turn_index,
            len(updates["recent_messages"]),
            len(summary),
            memory.summary_compaction_count,
            ",".join(_memory_sources_used(state)),
            state.get("reference_resolution_source", "none"),
        )
        return updates

    return node


def _conversation_context(state: AssistantState, max_chars: int) -> str | None:
    sections: list[str] = [
        "Memory precedence (highest to lowest): current explicit user turn > "
        "structured active state > recent transcript > older summary > long-term preference. "
        "Never reuse values listed as superseded."
    ]
    memory = _memory_for_prompt(state)
    memory_payload = memory.prompt_payload()
    if memory_payload:
        sections.append(f"Structured active state:\n{memory_payload}")

    recent_messages = state.get("recent_messages", [])
    if recent_messages:
        transcript = "\n".join(
            f"{message.get('role', 'unknown')}: {message.get('content', '')}"
            for message in recent_messages
            if message.get("content")
            and not _contains_superseded_value(str(message.get("content")), memory)
        )
        if transcript:
            sections.append(f"Recent conversation:\n{transcript}")

    summary = state.get("conversation_summary")
    if summary:
        filtered_summary = "\n".join(
            line
            for line in summary.splitlines()
            if not _contains_superseded_value(line, memory)
        )
        if filtered_summary:
            sections.append(
                f"Older conversation summary (lower priority):\n{filtered_summary}"
            )

    structured_context: list[str] = []
    if state.get("user_preferences"):
        structured_context.append(
            "long_term_user_preferences_untrusted="
            f"{state['user_preferences']}"
        )
    if structured_context:
        sections.append("Long-term preference (lowest priority):\n" + "\n".join(structured_context))

    if len(sections) == 1:
        return None
    context = "\n\n".join(sections)
    return context[:max_chars]


def _query_requires_conversation_context(
    state: AssistantState,
    message: str,
    analysis: Any,
) -> bool:
    """Use conversational memory only when the current turn actually depends on it."""
    reference_source = state.get("reference_resolution_source", "none")
    return bool(
        state.get("user_preferences")
        or state.get("referenced_product_ids")
        or (state.get("recent_messages") and not analysis.filters.category)
        or reference_source not in {"none", "attached_image"}
        or _extract_ordinal_index(message) is not None
        or _is_filter_refinement(message, analysis.filters)
    )


def _memory_for_prompt(state: AssistantState):
    memory = load_conversation_memory(state.get("conversation_memory")).model_copy(deep=True)
    normalized = _normalize_preference_text(state.get("message", ""))
    if not any(
        cue in normalized
        for cue in (
            "khong phai",
            "doi sang",
            "thay bang",
            "sua lai",
            "actually",
            "instead",
        )
    ):
        return memory
    for field_name, value in (state.get("filters") or {}).items():
        if value in (None, [], ""):
            continue
        old_value = memory.active_constraints.get(field_name)
        if old_value is not None and old_value != value:
            history = memory.superseded_values.setdefault(field_name, [])
            if old_value not in history:
                history.append(old_value)
        memory.active_constraints[field_name] = value
        if field_name in memory.preferences:
            memory.preferences[field_name] = value
    return memory


def _contains_superseded_value(text: str, memory: Any) -> bool:
    normalized = _normalize_preference_text(text)
    aliases = {
        "black": ("black", "den"),
        "blue": ("blue", "xanh duong", "xanh"),
        "white": ("white", "trang"),
        "red": ("red", "do"),
        "green": ("green", "xanh la"),
    }
    for values in memory.superseded_values.values():
        flattened = values if isinstance(values, list) else [values]
        for raw_value in flattened:
            nested = raw_value if isinstance(raw_value, list) else [raw_value]
            for value in nested:
                normalized_value = _normalize_preference_text(str(value))
                candidates = aliases.get(normalized_value, (normalized_value,))
                if any(
                    candidate
                    and re.search(rf"\b{re.escape(candidate)}\b", normalized)
                    for candidate in candidates
                ):
                    return True
    return False


def _current_turn_messages(state: AssistantState) -> list[dict[str, str]]:
    user_content = state.get("message", "").strip()
    if not user_content and state.get("image") is not None:
        user_content = "[User sent a product image]"

    messages: list[dict[str, str]] = []
    if user_content:
        messages.append({"role": "user", "content": user_content[:4000]})
    assistant_content = state.get("assistant_reply", "").strip()
    if assistant_content:
        messages.append({"role": "assistant", "content": assistant_content[:4000]})
    return messages


def _extend_conversation_summary(
    existing: str | None,
    dropped_messages: list[dict[str, str]],
    max_chars: int,
) -> str | None:
    if not dropped_messages:
        return existing
    dropped_text = "\n".join(
        f"{message.get('role', 'unknown')}: {message.get('content', '')}"
        for message in dropped_messages
        if message.get("content")
    )
    combined = "\n".join(part for part in (existing, dropped_text) if part)
    if len(combined) <= max_chars:
        return combined

    marker = "\n...[older details compacted]...\n"
    available = max_chars - len(marker)
    prefix_length = max(0, available // 3)
    suffix_length = max(0, available - prefix_length)
    return f"{combined[:prefix_length]}{marker}{combined[-suffix_length:]}"


def _summary_requires_compaction(
    existing: str | None,
    dropped_messages: list[dict[str, str]],
    max_chars: int,
) -> bool:
    if not dropped_messages:
        return False
    dropped_text = "\n".join(
        f"{message.get('role', 'unknown')}: {message.get('content', '')}"
        for message in dropped_messages
        if message.get("content")
    )
    return len("\n".join(part for part in (existing, dropped_text) if part)) > max_chars


def _image_payload_from_state(state: AssistantState) -> ImagePayload | None:
    image = state.get("image")
    if image is None:
        return None
    return ImagePayload(**image)


def _crop_box_from_state(state: AssistantState) -> ImageBoundingBox | None:
    crop_box = state.get("crop_box")
    if crop_box is None:
        return None
    return ImageBoundingBox(**crop_box)


def _filter_from_state(state: AssistantState) -> SearchFilter | None:
    filters = state.get("filters")
    if not filters:
        return None
    return SearchFilter(**filters)


def _filter_from_dict(filters: dict[str, Any] | None) -> SearchFilter | None:
    return SearchFilter(**filters) if filters else None


def _call_text_search_prepared(
    search_service: SearchService,
    **kwargs: Any,
) -> tuple[Any, dict[str, float]]:
    """Pass provenance-aware arguments while retaining compatibility with lightweight adapters."""
    method = search_service.search_text_prepared
    parameters = inspect.signature(method).parameters
    accepts_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    supported = kwargs if accepts_kwargs else {
        key: value for key, value in kwargs.items() if key in parameters
    }
    return method(**supported)


def _consume_llm_warnings(
    llm_service: LlmService,
    *,
    correlation_id: str | None = None,
) -> list[str]:
    consume = getattr(llm_service, "consume_warnings", None)
    if not callable(consume):
        return []
    try:
        warnings = [str(value) for value in consume() if value]
        for warning in warnings:
            logger.info(
                "assistant_llm_warning correlation_id=%s reason=%s",
                correlation_id,
                warning,
            )
        return warnings
    except Exception:
        logger.debug("llm_warning_consume_failed", exc_info=True)
        return []


def _last_filter_from_state(state: AssistantState) -> SearchFilter | None:
    filters = state.get("last_filters")
    if not filters:
        return None
    return SearchFilter(**filters)


def _understanding_from_state(state: AssistantState) -> QueryUnderstanding | None:
    intent = state.get("intent")
    if not intent:
        return None
    return QueryUnderstanding(
        intent=intent,  # type: ignore[arg-type]
        rewritten_query=state.get("rewritten_query") or state.get("message", ""),
        filters=_filter_from_state(state) or SearchFilter(),
        needs_image_search=state.get("needs_image_search", False),
        needs_text_search=state.get("needs_text_search", False),
        clarifying_question=state.get("clarifying_question"),
    )


def _contextual_filters(
    *,
    message: str,
    current: SearchFilter,
    previous: SearchFilter | None,
) -> SearchFilter | None:
    if previous is None:
        return current
    if not _is_filter_refinement(message, current):
        return current
    return merge_filters(previous, current)


def _missing_required_context(
    *,
    message: str,
    current: SearchFilter,
    previous_filters: SearchFilter | None,
    previous_results: list[dict[str, Any]],
) -> bool:
    if _extract_ordinal_index(message.lower()) is not None:
        return not previous_results
    return previous_filters is None and _is_filter_refinement(message, current)


def _missing_context_question(message: str) -> str:
    if _extract_ordinal_index(message.lower()) is not None:
        return "Mình chưa có danh sách sản phẩm trước đó để tham chiếu. Bạn muốn tìm sản phẩm nào?"
    return "Mình chưa có ngữ cảnh trước đó. Bạn muốn tìm loại sản phẩm nào và ngân sách bao nhiêu?"


def _references_attached_image(message: str) -> bool:
    normalized = f" {normalize_query_text(message)} "
    return any(
        f" {phrase} " in normalized
        for phrase in _ATTACHED_IMAGE_REFERENCE_PHRASES
    )


def _is_filter_refinement(message: str, current: SearchFilter | None) -> bool:
    normalized = normalize_query_text(message)
    explicitly_reuses_context = any(
        phrase in normalized
        for phrase in (
            "giu cac yeu cau tren",
            "giu cac yeu cau truoc",
            "giu nguyen yeu cau",
            "giu nguyen cac yeu cau",
            "giu cac tieu chi tren",
            "giu cac tieu chi truoc",
            "giu nguyen tieu chi",
            "giu nguyen cac tieu chi",
            "giu nhu tren",
            "giu nhu cu",
            "van giu cac yeu cau",
            "van giu cac tieu chi",
            "keep the previous requirements",
            "keep previous requirements",
            "keeping the previous requirements",
            "same requirements as above",
            "keep the previous criteria",
            "keep previous criteria",
            "same criteria as above",
        )
    )
    if (
        explicitly_reuses_context
        or _is_cheaper_refinement(message)
        or "thi sao" in normalized
    ):
        return True
    if current is None:
        return bool(re.search(r"\bcon\b", normalized))
    current_filters = current.model_dump(exclude_none=True)
    if not current_filters:
        return False
    # A complete first-turn product query can contain "còn" as part of
    # "còn hàng không?". Category/brand/material make it self-contained,
    # so it must not be treated as a refinement requiring conversation history.
    if current.category or current.brand or current.material:
        return False
    if re.search(r"\bcon\b", normalized):
        return True
    return len(normalized.split()) <= 5


def _is_cheaper_refinement(message: str) -> bool:
    normalized = normalize_query_text(message)
    return any(
        phrase in normalized
        for phrase in ("re hon", "gia thap hon", "gia mem hon", "cheaper", "lower price")
    )


def _remove_inherited_llm_refinement_filters(
    *,
    message: str,
    llm_filters: SearchFilter | None,
    rule_filters: SearchFilter | None,
) -> SearchFilter | None:
    if llm_filters is None or not _is_filter_refinement(message, rule_filters):
        return llm_filters
    data = llm_filters.model_dump(exclude_none=True)
    rule_data = rule_filters.model_dump(exclude_none=True) if rule_filters else {}
    for field_name in SearchFilter.model_fields:
        if field_name not in rule_data:
            data.pop(field_name, None)
    return SearchFilter.model_validate(data) if data else None


def _with_color_match_mode(
    message: str,
    filters: SearchFilter | None,
) -> SearchFilter | None:
    if filters is None or not filters.colors or len(filters.colors) < 2:
        return filters
    normalized = normalize_query_text(message)
    requires_all = "/" in message or (
        " va " in f" {normalized} " and " hoac " not in f" {normalized} "
    )
    if not requires_all:
        return filters
    return filters.model_copy(update={"color_match_mode": "all"})


def _apply_cheaper_price_ceiling(
    *,
    message: str,
    filters: SearchFilter | None,
    previous_context: list[dict[str, Any]],
) -> SearchFilter | None:
    if not _is_cheaper_refinement(message):
        return filters
    prices = [
        price
        for item in previous_context
        if isinstance(item, dict)
        for price in [_effective_context_price(item)]
        if price is not None
    ]
    if not prices:
        return filters
    data = filters.model_dump(exclude_none=True) if filters else {}
    ceiling = max(0.0, min(prices) - 1.0)
    data["max_price"] = ceiling
    if data.get("min_price") is not None and float(data["min_price"]) > ceiling:
        data.pop("min_price", None)
    return SearchFilter.model_validate(data)


def _effective_context_price(product: dict[str, Any]) -> float | None:
    price = product.get("price") if isinstance(product.get("price"), dict) else {}
    value = price.get("effective_price") or price.get("discounted_price") or price.get("price")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _result_from_dict(item: dict[str, Any]) -> SearchResultItem:
    return SearchResultItem(**item)


def _response_from_state(
    state: AssistantState,
    session_id: str,
    *,
    include_evaluation_trace: bool = False,
) -> AssistantChatResponse:
    product_ids = [_result_from_dict(item) for item in state.get("final_product_ids", [])]
    return AssistantChatResponse(
        session_id=session_id,
        message=state.get("assistant_reply", ""),
        product_ids=product_ids,
        filters=_filter_from_state(state),
        rewritten_query=state.get("rewritten_query"),
        warnings=state.get("warnings") or None,
        evaluation_trace=(
            _evaluation_trace_from_state(state)
            if include_evaluation_trace
            else None
        ),
    )


def _response_payload_from_state(
    state: AssistantState,
    *,
    include_evaluation_trace: bool = False,
) -> dict[str, Any]:
    return _response_from_state(
        state,
        state.get("session_id", ""),
        include_evaluation_trace=include_evaluation_trace,
    ).model_dump(mode="json")


def _evaluation_trace_from_state(state: AssistantState) -> AssistantEvaluationTrace:
    warnings = list(state.get("warnings", []))
    candidates = []
    for rank, item in enumerate(state.get("final_product_ids", []), start=1):
        product_id = item.get("product_id")
        if product_id is None:
            continue
        score = item.get("score")
        candidates.append(
            EvaluationTraceCandidate(
                product_id=str(product_id),
                score=float(score) if isinstance(score, (int, float)) else None,
                rank=rank,
                source=str(item.get("source")) if item.get("source") else None,
            )
        )
    return AssistantEvaluationTrace(
        request_id_hash=_trace_hash(state.get("request_id")),
        session_id_hash=_trace_hash(state.get("session_id")) or _trace_hash("missing") or "",
        turn_sequence=state.get("turn_sequence"),
        route=state.get("route", "unknown"),
        intent=state.get("intent"),
        rewritten_query=state.get("rewritten_query"),
        rule_filters=dict(state.get("rule_filters") or {}),
        llm_filters=dict(state.get("llm_filters") or {}),
        effective_filters=dict(state.get("filters") or {}),
        retrieved_candidates=candidates,
        retrieved_context=_redacted_evaluation_context(state.get("product_context", [])),
        referenced_product_ids=list(state.get("referenced_product_ids", [])),
        reference_resolution_source=state.get("reference_resolution_source", "none"),
        memory_sources=_memory_sources_used(state),
        warnings=warnings,
        fallback_reasons=[
            warning
            for warning in warnings
            if any(marker in warning for marker in ("fallback", "failed", "unavailable"))
        ],
        stage_latencies_ms={
            str(key): round(float(value), 3)
            for key, value in state.get("stage_latencies_ms", {}).items()
        },
    )


def _redacted_evaluation_context(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Product catalog evidence is allow-listed by _compact_product_context; no
    # transcript, user ID, session ID, request headers, or preference notes enter it.
    return _compact_product_context(products)


def _trace_hash(value: object | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return sha256(str(value).strip().encode("utf-8")).hexdigest()[:16]


def _resolve_referenced_product_ids(message: str, last_results: list[dict[str, Any]]) -> list[str]:
    if not last_results:
        return []

    normalized = message.lower()
    index = _extract_ordinal_index(normalized)
    if index is None and len(last_results) == 1 and _has_singular_product_reference(normalized):
        product_id = last_results[0].get("product_id")
        return [str(product_id)] if product_id else []
    if index is None:
        return []
    if index < 1 or index > len(last_results):
        return []
    product_id = last_results[index - 1].get("product_id")
    return [str(product_id)] if product_id else []


def _validated_referenced_product_ids(
    candidate_ids: list[str],
    last_results: list[dict[str, Any]],
    conversation_memory: dict[str, Any] | None = None,
) -> list[str]:
    allowed_ids = allowed_candidate_ids(conversation_memory, last_results)
    return list(
        dict.fromkeys(
            str(candidate_id)
            for candidate_id in candidate_ids
            if str(candidate_id) in allowed_ids
        )
    )


def _has_singular_product_reference(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "cái đó",
            "cai do",
            "mẫu đó",
            "mau do",
            "sản phẩm đó",
            "san pham do",
            "mẫu vừa rồi",
            "mau vua roi",
            "sản phẩm vừa rồi",
            "san pham vua roi",
            "nó còn",
            "no con",
            "nó có",
            "no co",
            "that one",
            "it available",
        )
    )


def _extract_ordinal_index(message: str) -> int | None:
    normalized = _normalize_reference_text(message)
    for pattern, group_index in _ORDINAL_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return int(match.group(group_index))
    for word, index in _ORDINAL_WORDS.items():
        normalized_word = _normalize_reference_text(word)
        if re.search(
            rf"\b(?:thu\s+|(?:cai|mau|san pham)\s+(?:thu\s+)?){re.escape(normalized_word)}\b",
            normalized,
            re.IGNORECASE,
        ):
            return index
    return None


def _normalize_reference_text(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("đ", "d").replace("Ä‘", "d").replace("Ã„â€˜", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text)


def _dedupe_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _search_warnings(state: AssistantState, results: list[dict[str, Any]]) -> list[str]:
    warnings = list(state.get("warnings", []))
    if not results:
        warnings.append("no_search_results")
    return _dedupe_strings(warnings)


def _compact_product_context(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed_keys = {
        "product_id",
        "id",
        "title",
        "name",
        "title_vi",
        "brand",
        "gender",
        "gender_vi",
        "base_colour",
        "base_colour_vi",
        "material",
        "material_vi",
        "price",
        "discounted_price",
        "effective_price",
        "currency",
        "colors",
        "colors_vi",
        "sizes",
        "available",
        "total_stock",
        "description",
        "description_vi",
        "variants",
        "categories",
        "category_names",
        "category_names_vi",
        "availability",
    }
    compacted: list[dict[str, Any]] = []
    for product in products:
        compacted.append(
            {
                key: _compact_context_value(value)
                for key, value in product.items()
                if key in allowed_keys and value is not None
            }
        )
    return compacted


_CONTEXT_COLOR_SHADE_RULES: tuple[
    tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...
] = (
    (("do ruou vang",), ("do ruou vang", "wine"), ()),
    (("nau dam",), ("nau dam", "dark brown"), ()),
    (("vang anh kim",), ("vang anh kim", "golden", "metallic gold"), ()),
    (("nau soc",), ("nau soc", "brown stripe", "brown stripes"), ()),
    (("hong pastel",), ("hong pastel", "pastel pink"), ()),
    (("nau thuoc la",), ("nau thuoc la", "tobacco brown"), ()),
    (("xam than",), ("xam than", "charcoal gray", "charcoal grey"), ()),
    (("mau cat den", "mau cat va den", "sand black", "sand and black"), (), ("mau cat", "den")),
)


def _filter_context_by_requested_color_shade(
    message: str,
    context: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_message = normalize_query_text(message)
    rule = next(
        (
            (accepted_any, accepted_all)
            for triggers, accepted_any, accepted_all in _CONTEXT_COLOR_SHADE_RULES
            if any(trigger in normalized_message for trigger in triggers)
        ),
        None,
    )
    if rule is None:
        return context
    accepted_any, accepted_all = rule
    filtered: list[dict[str, Any]] = []
    for product in context:
        raw_color = " ".join(
            normalize_query_text(str(product.get(field_name, "")))
            for field_name in ("base_colour", "base_colour_vi", "colors", "colors_vi")
        )
        matches_any = bool(accepted_any) and any(
            phrase in raw_color for phrase in accepted_any
        )
        matches_all = bool(accepted_all) and all(
            phrase in raw_color for phrase in accepted_all
        )
        if matches_any or matches_all:
            filtered.append(product)
    return filtered


def _compact_context_value(value: Any) -> Any:
    if isinstance(value, str):
        return value[:300]
    if isinstance(value, list):
        return value[:12]
    return value


def _save_long_term_preferences(
    state: AssistantState,
    preference_store: UserPreferenceStore,
) -> tuple[dict[str, Any], str | None, int]:
    user_id = state.get("user_id", "").strip()
    if not user_id:
        return (
            state.get("user_preferences", {}),
            None,
            state.get("user_preference_version", 0),
        )

    message = state.get("message", "")
    normalized = _normalize_preference_text(message)
    try:
        if _requests_preference_reset(normalized):
            preference_store.clear(user_id)
            logger.info("assistant_user_preferences_cleared")
            return {}, None, 0

        update, unresolved = _preference_update(
            message,
            normalized,
            _current_turn_preference_filters(state, normalized),
        )
        if unresolved:
            return (
                state.get("user_preferences", {}),
                "preference_update_unresolved",
                state.get("user_preference_version", 0),
            )
        if update is None:
            return (
                state.get("user_preferences", {}),
                None,
                state.get("user_preference_version", 0),
            )
        update = _remove_superseded_values_from_update(
            update,
            state.get("user_preferences", {}),
        )
        if update is None:
            return (
                state.get("user_preferences", {}),
                "preference_update_unresolved",
                state.get("user_preference_version", 0),
            )
        update = update.model_copy(
            update={
                "source_turn_sequence": state.get("turn_sequence"),
                "source_session_hash": _trace_hash(state.get("session_id")),
                "source_request_hash": _trace_hash(state.get("request_id")),
            }
        )
        expected_version = state.get("user_preference_version", 0)
        try:
            profile = preference_store.merge(
                user_id,
                update,
                expected_version=expected_version,
            )
        except PreferenceVersionConflict:
            latest = preference_store.get(user_id)
            profile = preference_store.merge(
                user_id,
                update,
                expected_version=latest.version,
            )
        logger.info(
            "assistant_user_preferences_updated field_count=%d",
            len(profile.prompt_payload()),
        )
        return profile.prompt_payload(), None, profile.version
    except Exception:
        logger.exception("assistant_user_preferences_save_failed")
        return (
            state.get("user_preferences", {}),
            "preference_update_failed",
            state.get("user_preference_version", 0),
        )


def _preference_update(
    message: str,
    normalized: str,
    filters: SearchFilter | None,
) -> tuple[UserPreferenceUpdate | None, bool]:
    positive_cues = (
        "toi thich",
        "minh thich",
        "em thich",
        "toi uu tien",
        "minh uu tien",
        "gu cua toi",
        "gu cua minh",
        "toi thuong mac",
        "minh thuong mac",
        "toi hay mac",
        "minh hay mac",
        "size cua toi",
        "size cua minh",
        "toi mac size",
        "minh mac size",
        "ngan sach cua toi",
        "ngan sach cua minh",
        "tam gia cua toi",
        "tam gia cua minh",
        "i like",
        "i prefer",
        "my size",
        "my budget",
        "doi so thich",
        "sua so thich",
        "change my preference",
        "update my preference",
    )
    negative_cues = (
        "toi khong thich",
        "minh khong thich",
        "toi khong muon",
        "minh khong muon",
        "tranh mau",
        "do not recommend",
        "i dislike",
    )
    correction_cues = (
        "doi so thich",
        "sua so thich",
        "khong phai",
        "thay bang",
        "doi sang",
        "sua lai",
        "actually",
        "instead",
        "change to",
    )
    is_negative = any(cue in normalized for cue in negative_cues)
    is_correction = any(cue in normalized for cue in correction_cues)
    if (
        not is_negative
        and not is_correction
        and not any(cue in normalized for cue in positive_cues)
    ):
        return None, False

    resolved = filters or SearchFilter()
    avoided_colors = (
        _avoided_color_values(normalized, list(resolved.colors or []))
        if is_negative and _mentions_avoided_color(normalized)
        else []
    )
    preferred_colors = [
        color for color in (resolved.colors or []) if color not in avoided_colors
    ]
    avoidance_notes = [
        f"màu {_localize_memory_value(color)}" for color in avoided_colors
    ]
    if is_negative and not avoidance_notes:
        note = message.strip()[:300]
        avoidance_notes = [note] if note else []
    replace_fields: set[str] = set()
    if is_correction:
        if resolved.category:
            replace_fields.add("preferred_categories")
        if resolved.brand:
            replace_fields.add("preferred_brands")
        if preferred_colors:
            replace_fields.add("preferred_colors")
        if resolved.sizes:
            replace_fields.add("preferred_sizes")
        if resolved.material:
            replace_fields.add("preferred_materials")
        if resolved.gender:
            replace_fields.add("preferred_gender")
        if resolved.min_price is not None:
            replace_fields.add("budget_min")
        if resolved.max_price is not None:
            replace_fields.add("budget_max")
    has_structured_value = any(
        value not in (None, [], "")
        for value in (
            resolved.category,
            resolved.brand,
            preferred_colors,
            resolved.sizes,
            resolved.material,
            resolved.gender,
            resolved.min_price,
            resolved.max_price,
        )
    )
    if is_correction and not has_structured_value:
        return None, True
    return UserPreferenceUpdate(
        preferred_categories=[resolved.category] if resolved.category else [],
        preferred_brands=[resolved.brand] if resolved.brand else [],
        preferred_colors=preferred_colors,
        preferred_sizes=list(resolved.sizes or []),
        preferred_materials=[resolved.material] if resolved.material else [],
        preferred_gender=resolved.gender,
        budget_min=resolved.min_price,
        budget_max=resolved.max_price,
        style_notes=_preference_style_notes(normalized) if not is_correction else [],
        avoidance_notes=avoidance_notes,
        replace_fields=replace_fields,
    ), False


def _current_turn_preference_filters(
    state: AssistantState,
    normalized: str,
) -> SearchFilter | None:
    filters = _filter_from_dict(state.get("rule_filters"))
    if filters is None:
        return None
    data = filters.model_dump(exclude_none=True)
    # Short Vietnamese phrases such as "ghi nhớ" can collide with catalog
    # aliases ("ghi" = gray). A preference color must have an explicit color cue.
    if "colors" in data and not re.search(r"\b(?:mau|color|colour)\b", normalized):
        data.pop("colors", None)
    return SearchFilter.model_validate(data) if data else None


def _sanitize_current_turn_filters(
    state: AssistantState,
    filters: SearchFilter | None,
) -> SearchFilter | None:
    if filters is None:
        return None
    normalized = _normalize_preference_text(state.get("message", ""))
    data = filters.model_dump(exclude_none=True)
    if "colors" in data and not re.search(r"\b(?:mau|color|colour)\b", normalized):
        data.pop("colors", None)
    if _mentions_avoided_color(normalized):
        data.pop("colors", None)
    if any(
        cue in normalized
        for cue in ("khong phai", "doi sang", "thay bang", "sua lai", "actually", "instead")
    ):
        active = load_conversation_memory(
            state.get("conversation_memory")
        ).active_constraints
        for field_name in ("colors", "sizes", "use_cases"):
            incoming = data.get(field_name)
            if not isinstance(incoming, list):
                continue
            old_values = active.get(field_name, [])
            old_set = set(old_values if isinstance(old_values, list) else [old_values])
            remaining = [value for value in incoming if value not in old_set]
            if remaining:
                data[field_name] = remaining
            else:
                data.pop(field_name, None)
    return SearchFilter.model_validate(data) if data else None


def _resolved_relative_filters(
    state: AssistantState,
    current: SearchFilter | None,
) -> SearchFilter | None:
    normalized = _normalize_preference_text(state.get("message", ""))
    if not any(
        phrase in normalized
        for phrase in (
            "mau moi",
            "tieu chi hien tai",
            "dung tieu chi",
            "theo gu hien tai",
            "current color",
            "current criteria",
        )
    ):
        return None
    active = load_conversation_memory(
        state.get("conversation_memory")
    ).active_constraints
    if not active:
        return None
    inherited = _filter_from_dict(active)
    if inherited is None:
        return None
    return merge_filters(inherited, current) if current else inherited


def _memory_filters_for_turn(state: AssistantState) -> dict[str, Any]:
    if state.get("intent") in {"memory_recall", "conversation_summary"}:
        return {}
    normalized = _normalize_preference_text(state.get("message", ""))
    filters = _current_turn_preference_filters(state, normalized)
    if filters is None:
        return {}
    data = filters.model_dump(exclude_none=True)
    if _mentions_avoided_color(normalized):
        data.pop("colors", None)
    if any(
        cue in normalized
        for cue in ("khong phai", "doi sang", "thay bang", "sua lai", "actually", "instead")
    ):
        active = load_conversation_memory(
            state.get("conversation_memory")
        ).active_constraints
        for field_name in ("colors", "sizes", "use_cases"):
            incoming = data.get(field_name)
            if not isinstance(incoming, list):
                continue
            old_values = active.get(field_name, [])
            old_set = set(old_values if isinstance(old_values, list) else [old_values])
            remaining = [value for value in incoming if value not in old_set]
            if remaining:
                data[field_name] = remaining
            else:
                data.pop(field_name, None)
    return data


def _mentions_avoided_color(normalized: str) -> bool:
    return bool(
        re.search(
            r"\b(?:tranh mau|khong thich mau|khong muon mau|avoid(?: the)? colou?r)\b",
            normalized,
        )
    )


def _avoided_color_values(normalized: str, resolved_colors: list[str]) -> list[str]:
    if resolved_colors:
        return resolved_colors
    aliases = (
        ("den", "black"),
        ("xanh", "blue"),
        ("do", "red"),
        ("xam", "gray"),
        ("ghi", "gray"),
        ("trang", "white"),
        ("nau", "brown"),
        ("tim", "purple"),
    )
    return list(
        dict.fromkeys(
            canonical
            for alias, canonical in aliases
            if re.search(rf"\b{re.escape(alias)}\b", normalized)
        )
    )


def _preference_style_notes(normalized: str) -> list[str]:
    notes: list[str] = []
    if any(phrase in normalized for phrase in ("form rong", "oversize", "oversized")):
        notes.append("form rộng")
    if any(phrase in normalized for phrase in ("form om", "slim fit")):
        notes.append("form ôm")
    return notes


def _remove_superseded_values_from_update(
    update: UserPreferenceUpdate,
    active_preferences: dict[str, Any],
) -> UserPreferenceUpdate | None:
    changes: dict[str, Any] = {}
    list_fields = (
        "preferred_categories",
        "preferred_brands",
        "preferred_colors",
        "preferred_sizes",
        "preferred_materials",
    )
    for field_name in list_fields:
        if field_name not in update.replace_fields:
            continue
        incoming = list(getattr(update, field_name))
        active = set(active_preferences.get(field_name) or [])
        remaining = [value for value in incoming if value not in active]
        if remaining:
            changes[field_name] = remaining
        elif incoming:
            return None
    return update.model_copy(update=changes) if changes else update


def _requests_preference_reset(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "quen so thich cua toi",
            "quen so thich cua minh",
            "xoa so thich cua toi",
            "xoa so thich cua minh",
            "xoa bo nho cua toi",
            "xoa bo nho cua minh",
            "forget my preferences",
            "clear my preferences",
        )
    )


def _normalize_preference_text(value: str) -> str:
    text = value.strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text)


def _memory_sources_used(state: AssistantState) -> list[str]:
    sources: list[str] = []
    if load_conversation_memory(state.get("conversation_memory")).prompt_payload():
        sources.append("structured_active_state")
    if state.get("recent_messages"):
        sources.append("recent_transcript")
    if state.get("conversation_summary"):
        sources.append("semantic_summary")
    if state.get("user_preferences"):
        sources.append("long_term_preference")
    return sources or ["none"]
