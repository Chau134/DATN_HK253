from typing import Any

from pydantic import Field

from ecommerce_search_assistant.schemas.base import SchemaModel
from ecommerce_search_assistant.schemas.search import SearchFilter, SearchResultItem
from ecommerce_search_assistant.schemas.types import NonEmptyString


class EvaluationTraceCandidate(SchemaModel):
    product_id: str
    score: float | None = None
    rank: int = Field(ge=1)
    source: str | None = None


class AssistantEvaluationTrace(SchemaModel):
    """Redacted diagnostic data exposed only when eval tracing is enabled."""

    schema_version: str = "1.0"
    request_id_hash: str | None = None
    session_id_hash: str
    turn_sequence: int | None = None
    route: str
    intent: str | None = None
    original_query: str | None = None
    rewritten_query: str | None = None
    rule_filters: dict[str, Any] = Field(default_factory=dict)
    llm_filters: dict[str, Any] = Field(default_factory=dict)
    effective_filters: dict[str, Any] = Field(default_factory=dict)
    retrieved_candidates: list[EvaluationTraceCandidate] = Field(default_factory=list)
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    referenced_product_ids: list[str] = Field(default_factory=list)
    reference_resolution_source: str = "none"
    memory_sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback_reasons: list[str] = Field(default_factory=list)
    stage_latencies_ms: dict[str, float] = Field(default_factory=dict)


class AssistantChatResponse(SchemaModel):
    session_id: NonEmptyString
    message: str
    product_ids: list[SearchResultItem] = Field(default_factory=list)
    filters: SearchFilter | None = None
    rewritten_query: str | None = None
    warnings: list[str] | None = None
    evaluation_trace: AssistantEvaluationTrace | None = None
