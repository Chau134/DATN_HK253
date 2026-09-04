from functools import lru_cache

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.services.bedrock.service import BedrockService
from ecommerce_search_assistant.services.llm.interfaces import LlmService
from ecommerce_search_assistant.services.llm.service import BaseLlmService


@lru_cache
def get_llm_service() -> LlmService:
    settings = get_settings()
    if settings.llm_provider == "bedrock":
        return BedrockService(settings=settings)
    return BaseLlmService(settings=settings)
