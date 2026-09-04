from functools import lru_cache

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.infrastructure.qdrant import build_qdrant_client
from ecommerce_search_assistant.services.cropping.factory import get_yolo_crop_service
from ecommerce_search_assistant.services.embeddings.factory import (
    get_image_embedding_service,
    get_text_embedding_service,
)
from ecommerce_search_assistant.services.llm.factory import get_llm_service
from ecommerce_search_assistant.services.reranking.factory import get_rerank_service
from ecommerce_search_assistant.services.search.service import SearchService


@lru_cache
def get_search_service() -> SearchService:
    settings = get_settings()
    return SearchService(
        settings=settings,
        qdrant_client=build_qdrant_client(settings),
        text_embedding_service=get_text_embedding_service(),
        image_embedding_service=get_image_embedding_service(),
        yolo_crop_service=get_yolo_crop_service(),
        llm_service=get_llm_service(),
        rerank_service=get_rerank_service(),
    )
