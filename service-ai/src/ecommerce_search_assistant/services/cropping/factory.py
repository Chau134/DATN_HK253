from functools import lru_cache

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.services.cropping.yolo import (
    CropService,
    OriginalImageCropService,
    YoloCropService,
)


@lru_cache
def get_yolo_crop_service() -> CropService:
    settings = get_settings()
    if not settings.yolo_enabled:
        return OriginalImageCropService()
    return YoloCropService(settings=settings)
