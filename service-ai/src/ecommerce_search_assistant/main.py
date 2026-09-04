import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextlib import suppress
from datetime import UTC, datetime
import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ecommerce_search_assistant.api.middleware import CorrelationIdMiddleware
from ecommerce_search_assistant.api.router import api_router
from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.core.logging import configure_logging
from ecommerce_search_assistant.services.search.service import SearchTopKExceededError


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        preload_task: asyncio.Task[None] | None = None
        logger.info(
            "application_started",
            extra={
                "app_name": resolved_settings.app_name,
                "environment": resolved_settings.app_env,
            },
        )
        if resolved_settings.preload_models:
            preload_task = asyncio.create_task(
                asyncio.to_thread(_preload_models, resolved_settings, logger),
                name="model-preload",
            )
        try:
            yield
        finally:
            if preload_task is not None and not preload_task.done():
                preload_task.cancel()
                with suppress(asyncio.CancelledError):
                    await preload_task
            logger.info("application_stopped")

    app = FastAPI(
        title=resolved_settings.app_name,
        lifespan=lifespan,
    )

    @app.exception_handler(SearchTopKExceededError)
    async def search_top_k_exceeded_handler(
        _: Request,
        exc: SearchTopKExceededError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    app.state.settings = resolved_settings
    app.state.instance_id = uuid4().hex
    app.state.started_at = datetime.now(UTC).isoformat()
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


def _preload_models(settings: Settings, logger: logging.Logger) -> None:
    from ecommerce_search_assistant.services.embeddings.factory import (
        get_image_embedding_service,
        get_text_embedding_service,
    )
    from ecommerce_search_assistant.services.cropping.factory import get_yolo_crop_service
    from ecommerce_search_assistant.services.llm.factory import get_llm_service
    from ecommerce_search_assistant.services.reranking.factory import get_rerank_service

    loaders = [
        ("text_embedding", get_text_embedding_service),
        ("image_embedding", get_image_embedding_service),
        ("llm", get_llm_service),
        ("yolo", get_yolo_crop_service),
    ]
    if settings.rerank_enabled:
        loaders.append(("reranker", get_rerank_service))

    for name, factory in loaders:
        try:
            factory().warmup()
            logger.info("model_preloaded", extra={"model": name})
        except Exception:
            logger.exception("model_preload_failed", extra={"model": name})


app = create_app()
