from functools import lru_cache

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.services.reranking.interfaces import RerankService
from ecommerce_search_assistant.services.reranking.vertex import VertexRankingRerankService


@lru_cache
def get_rerank_service() -> RerankService:
    return VertexRankingRerankService(settings=get_settings())
