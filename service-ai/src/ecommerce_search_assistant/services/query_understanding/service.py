from typing import Protocol

from ecommerce_search_assistant.services.llm.service import QueryUnderstanding


class QueryUnderstandingService(Protocol):
    def understand(self, query: str) -> QueryUnderstanding:
        ...


QueryUnderstandingResult = QueryUnderstanding
