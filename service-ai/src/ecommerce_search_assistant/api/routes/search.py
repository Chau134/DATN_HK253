from typing import Annotated

from fastapi import APIRouter, Depends

from ecommerce_search_assistant.core.metrics import search_metrics
from ecommerce_search_assistant.schemas.search import (
    AutoSearchRequest,
    HybridSearchRequest,
    ImageDetectionRequest,
    ImageDetectionResponse,
    ImageSearchRequest,
    SearchResponse,
    TextSearchRequest,
)
from ecommerce_search_assistant.services.search.factory import get_search_service
from ecommerce_search_assistant.services.search.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/text", response_model=SearchResponse, response_model_exclude_none=True)
def search_text(
    request: TextSearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchResponse:
    try:
        return service.search_text(request)
    except Exception:
        search_metrics.record_error("text")
        raise


@router.post("/auto", response_model=SearchResponse, response_model_exclude_none=True)
def search_auto(
    request: AutoSearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchResponse:
    return service.search_auto(request)


@router.post("/image", response_model=SearchResponse, response_model_exclude_none=True)
def search_image(
    request: ImageSearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchResponse:
    return service.search_image(request)


@router.post("/image/detections", response_model=ImageDetectionResponse, response_model_exclude_none=True)
def detect_image(
    request: ImageDetectionRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> ImageDetectionResponse:
    return service.detect_image(request)


@router.post("/hybrid", response_model=SearchResponse, response_model_exclude_none=True)
def search_hybrid(
    request: HybridSearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchResponse:
    return service.search_hybrid(request)
