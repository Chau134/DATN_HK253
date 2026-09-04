from fastapi import APIRouter

from ecommerce_search_assistant.api.routes.assistant import router as assistant_router
from ecommerce_search_assistant.api.routes.health import router as health_router
from ecommerce_search_assistant.api.routes.internal_indexing import router as internal_indexing_router
from ecommerce_search_assistant.api.routes.metrics import router as metrics_router
from ecommerce_search_assistant.api.routes.search import router as search_router

api_router = APIRouter()
api_router.include_router(assistant_router)
api_router.include_router(health_router)
api_router.include_router(internal_indexing_router)
api_router.include_router(metrics_router)
api_router.include_router(search_router)
