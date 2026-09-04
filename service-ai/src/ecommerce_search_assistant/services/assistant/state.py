from typing import Any, TypedDict


class AssistantState(TypedDict, total=False):
    session_id: str
    user_id: str
    request_id: str | None
    turn_sequence: int | None
    message: str
    image: dict[str, Any] | None
    crop_box: dict[str, Any] | None
    locale: str
    intent: str
    rule_intent: str | None
    answer_target: str | None
    original_search_query: str
    resolved_search_query: str
    exact_product_query: str | None
    exact_product_code: str | None
    exact_match_resolved: bool | None
    catalog_title_query: str | None
    catalog_title_queries: list[str]
    comparison_provenance: dict[str, list[str]]
    out_of_catalog_domain: str | None
    shop_knowledge_topic: str | None
    shop_knowledge_answer: str | None
    rewritten_query: str | None
    needs_image_search: bool
    needs_text_search: bool
    filters: dict[str, Any] | None
    rule_filters: dict[str, Any] | None
    llm_filters: dict[str, Any] | None
    filter_confidences: dict[str, float]
    filter_match_sources: dict[str, str]
    last_filters: dict[str, Any] | None
    final_product_ids: list[dict[str, Any]]
    last_product_ids: list[dict[str, Any]]
    assistant_reply: str
    warnings: list[str]
    clarifying_question: str | None
    product_context: list[dict[str, Any]]
    # Previous non-empty result context is retained separately because the
    # start node clears current-turn context before routing. Comparative
    # follow-ups (for example "rẻ hơn") still need the displayed prices.
    last_product_context: list[dict[str, Any]]
    referenced_product_ids: list[str]
    route: str
    llm_call_count: int
    springboot_call_count: int
    product_context_limit: int
    recent_messages: list[dict[str, str]]
    conversation_summary: str | None
    user_preferences: dict[str, Any]
    conversation_memory: dict[str, Any]
    reference_resolution_source: str
    processed_requests: dict[str, dict[str, Any]]
    last_turn_sequence: int
    user_preference_version: int
    stage_latencies_ms: dict[str, float]
