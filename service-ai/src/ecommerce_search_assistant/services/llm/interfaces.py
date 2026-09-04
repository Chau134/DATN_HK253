from typing import Any, Protocol

from ecommerce_search_assistant.schemas.search import SearchFilter, SearchResultItem
from ecommerce_search_assistant.services.llm.service import QueryUnderstanding


class LlmService(Protocol):
    def warmup(self) -> None:
        ...

    def is_ready(self) -> bool:
        ...

    def consume_warnings(self) -> list[str]:
        ...

    def analyze_user_query(
        self,
        message: str,
        locale: str = "vi-VN",
        conversation_context: str | None = None,
    ) -> QueryUnderstanding:
        ...

    def understand(self, query: str) -> QueryUnderstanding:
        ...

    def rewrite_query(self, message: str, context: str | None = None) -> str:
        ...

    def extract_filters(self, message: str, context: str | None = None) -> SearchFilter:
        ...

    def generate_assistant_reply(
        self,
        message: str,
        search_results: list[SearchResultItem],
        product_context: list[dict[str, Any]],
        conversation_context: str | None = None,
        is_reference_followup: bool = False,
    ) -> str:
        ...

    def generate_conversational_reply(
        self,
        message: str,
        conversation_context: str | None = None,
    ) -> str:
        ...
