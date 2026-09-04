from functools import lru_cache

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.infrastructure.qdrant import build_qdrant_client
from ecommerce_search_assistant.services.cropping.factory import get_yolo_crop_service
from ecommerce_search_assistant.services.embeddings.factory import (
    get_image_embedding_service,
    get_text_embedding_service,
)
from ecommerce_search_assistant.services.indexing.image_loader import ImageLoadService
from ecommerce_search_assistant.services.indexing.product import ProductIndexingService


@lru_cache
def get_product_indexing_service() -> ProductIndexingService:
    settings = get_settings()
    return ProductIndexingService(
        settings=settings,
        qdrant_client=build_qdrant_client(settings),
        text_embedding_service=get_text_embedding_service(),
        image_embedding_service=get_image_embedding_service(),
        yolo_crop_service=get_yolo_crop_service(),
        image_loader=ImageLoadService(settings=settings),
    )
