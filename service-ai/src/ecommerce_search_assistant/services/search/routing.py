from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import unicodedata

from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.llm.interfaces import LlmService
from ecommerce_search_assistant.services.llm.service import QueryUnderstanding
from ecommerce_search_assistant.services.search.filtering import merge_filters

SearchRoute = Literal["text_search", "image_search", "hybrid_search", "clarification", "non_product_answer"]


@dataclass(frozen=True)
class SearchRouteDecision:
    route: SearchRoute
    intent: str | None = None
    rewritten_query: str | None = None
    filters: SearchFilter | None = None
    needs_image_search: bool = False
    needs_text_search: bool = False
    clarifying_question: str | None = None
    analyzed: bool = False


def decide_search_route(
    *,
    query: str | None,
    has_image: bool,
    request_filters: SearchFilter | None = None,
    llm_service: LlmService | None = None,
    locale: str = "vi-VN",
    understanding: QueryUnderstanding | None = None,
) -> SearchRouteDecision:
    text = (query or "").strip()
    analyzed = False
    if text and understanding is None and llm_service is not None:
        understanding = llm_service.analyze_user_query(text, locale=locale)
        analyzed = True

    if not text and not has_image:
        return SearchRouteDecision(route="clarification", filters=request_filters)

    if not text and has_image:
        return SearchRouteDecision(route="image_search", filters=request_filters)

    if understanding is None:
        route: SearchRoute = "hybrid_search" if has_image else "text_search"
        return SearchRouteDecision(
            route=route,
            rewritten_query=text or None,
            filters=request_filters,
            needs_image_search=has_image,
            needs_text_search=bool(text),
        )

    filters = merge_filters(understanding.filters, request_filters)
    if understanding.clarifying_question:
        return _decision(
            "clarification",
            understanding=understanding,
            filters=filters,
            analyzed=analyzed,
        )

    if understanding.intent in {
        "general_question",
        "small_talk",
        "memory_recall",
        "conversation_summary",
    }:
        return _decision(
            "non_product_answer",
            understanding=understanding,
            filters=filters,
            analyzed=analyzed,
        )

    image_reference_only = _is_image_reference_only(text)
    if has_image:
        if image_reference_only or (understanding.needs_image_search and not understanding.needs_text_search):
            return _decision("image_search", understanding=understanding, filters=filters, analyzed=analyzed)
        if understanding.needs_image_search or understanding.needs_text_search:
            return _decision("hybrid_search", understanding=understanding, filters=filters, analyzed=analyzed)
        return _decision("image_search", understanding=understanding, filters=filters, analyzed=analyzed)

    if image_reference_only or (understanding.needs_image_search and not understanding.needs_text_search):
        return _decision("clarification", understanding=understanding, filters=filters, analyzed=analyzed)

    return _decision("text_search", understanding=understanding, filters=filters, analyzed=analyzed)


def _decision(
    route: SearchRoute,
    *,
    understanding: QueryUnderstanding,
    filters: SearchFilter | None,
    analyzed: bool,
) -> SearchRouteDecision:
    return SearchRouteDecision(
        route=route,
        intent=understanding.intent,
        rewritten_query=understanding.rewritten_query,
        filters=filters,
        needs_image_search=understanding.needs_image_search,
        needs_text_search=understanding.needs_text_search,
        clarifying_question=understanding.clarifying_question,
        analyzed=analyzed,
    )


def _is_image_reference_only(query: str) -> bool:
    text = _normalize_text(query)
    if not text:
        return False
    image_reference_phrases = (
        "giong anh",
        "giong hinh",
        "giong mau nay",
        "tuong tu anh",
        "tuong tu hinh",
        "tim giong",
        "tim mau giong",
        "find similar",
        "similar to this",
        "look like this",
    )
    if any(phrase in text for phrase in image_reference_phrases):
        product_terms = (
            "ao",
            "quan",
            "vay",
            "dam",
            "giay",
            "tui",
            "balo",
            "hoodie",
            "jacket",
            "dress",
            "shirt",
            "sneaker",
            "black",
            "white",
            "den",
            "trang",
            "nam",
            "nu",
        )
        return not any(term in text for term in product_terms)
    return False


def _normalize_text(value: str) -> str:
    text = value.strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(char for char in text if unicodedata.category(char) != "Mn")
