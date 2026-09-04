from functools import lru_cache

from ecommerce_search_assistant.services.llm.factory import get_llm_service
from ecommerce_search_assistant.services.query_understanding.service import (
    QueryUnderstandingService,
)


@lru_cache
def get_query_understanding_service() -> QueryUnderstandingService:
    return get_llm_service()
