from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ecommerce_search_assistant.api.dependencies import require_internal_api_key
from ecommerce_search_assistant.schemas.indexing import ProductDeleteResponse, ProductIndexResponse
from ecommerce_search_assistant.schemas.product import ProductIndexItem, ProductIndexRequest
from ecommerce_search_assistant.services.indexing.factory import get_product_indexing_service
from ecommerce_search_assistant.services.indexing.product import ProductIndexingService

router = APIRouter(
    prefix="/internal",
    tags=["internal-indexing"],
    dependencies=[Depends(require_internal_api_key)],
)


@router.post("/index/products/batch", response_model=ProductIndexResponse)
def index_products_batch(
    request: ProductIndexRequest,
    service: Annotated[ProductIndexingService, Depends(get_product_indexing_service)],
) -> ProductIndexResponse:
    return service.index_products(request.items)


@router.post("/index/products/{product_id}", response_model=ProductIndexResponse)
def update_product_index(
    product_id: str,
    product: ProductIndexItem,
    service: Annotated[ProductIndexingService, Depends(get_product_indexing_service)],
) -> ProductIndexResponse:
    if product.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path product_id must match body product_id",
        )
    return service.update_product(product)


@router.delete("/index/products/{product_id}", response_model=ProductDeleteResponse)
def delete_product_index(
    product_id: str,
    service: Annotated[ProductIndexingService, Depends(get_product_indexing_service)],
) -> ProductDeleteResponse:
    try:
        return service.delete_product(product_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/reindex", response_model=ProductIndexResponse)
def reindex_products(
    request: ProductIndexRequest,
    service: Annotated[ProductIndexingService, Depends(get_product_indexing_service)],
) -> ProductIndexResponse:
    return service.reindex_products(request.items)
