from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from ecommerce_search_assistant.api.dependencies import get_app_settings
from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.services.cropping.factory import get_yolo_crop_service
from ecommerce_search_assistant.services.embeddings.factory import (
    get_image_embedding_service,
    get_text_embedding_service,
)
from ecommerce_search_assistant.services.llm.factory import get_llm_service
from ecommerce_search_assistant.services.reranking.factory import get_rerank_service

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str


class ReadinessResponse(BaseModel):
    ready: bool
    models: dict[str, bool]
    capabilities: dict[str, bool]
    effective_features: dict[str, bool]
    evaluation_variant: Literal["rag", "llm_no_rag"]
    capability: str | None = None
    instance_id: str | None = None
    started_at: str | None = None


CapabilityName = Literal["text_search", "image_search", "assistant_llm"]


@router.get("/health", response_model=HealthResponse)
def health_check(settings: Annotated[Settings, Depends(get_app_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness_check(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
    response: Response,
) -> ReadinessResponse:
    models, capabilities = _readiness_state(settings)
    ready = all(capabilities.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        ready=ready,
        models=models,
        capabilities=capabilities,
        effective_features=_effective_features(settings),
        evaluation_variant=settings.assistant_evaluation_variant,
        instance_id=getattr(request.app.state, "instance_id", None),
        started_at=getattr(request.app.state, "started_at", None),
    )


@router.get("/health/ready/{capability}", response_model=ReadinessResponse)
def capability_readiness_check(
    capability: CapabilityName,
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
    response: Response,
) -> ReadinessResponse:
    models, capabilities = _readiness_state(settings)
    ready = capabilities[capability]
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        ready=ready,
        models=models,
        capabilities=capabilities,
        effective_features=_effective_features(settings),
        evaluation_variant=settings.assistant_evaluation_variant,
        capability=capability,
        instance_id=getattr(request.app.state, "instance_id", None),
        started_at=getattr(request.app.state, "started_at", None),
    )


def _readiness_state(settings: Settings) -> tuple[dict[str, bool], dict[str, bool]]:
    models: dict[str, bool] = {
        "text_embedding": _is_loaded(get_text_embedding_service()),
        "image_embedding": _is_loaded(get_image_embedding_service()),
        "llm": _is_loaded(get_llm_service()),
        # Keep the key for compatibility, but an intentionally disabled YOLO is
        # optional and therefore does not make the service unready.
        "yolo": settings.yolo_enabled and _is_loaded(get_yolo_crop_service()),
    }
    text_dependencies = ["text_embedding"]
    image_dependencies = ["image_embedding"]
    if settings.rerank_enabled:
        models["reranker"] = _is_loaded(get_rerank_service())
        text_dependencies.append("reranker")
    if settings.yolo_enabled:
        image_dependencies.append("yolo")

    capabilities = {
        "text_search": all(models[name] for name in text_dependencies),
        "image_search": all(models[name] for name in image_dependencies),
        "assistant_llm": models["llm"],
    }
    return models, capabilities


def _effective_features(settings: Settings) -> dict[str, bool]:
    return {
        "reranker_enabled": settings.rerank_enabled,
        "yolo_enabled": settings.yolo_enabled,
        "hybrid_parallel_branches_enabled": settings.hybrid_parallel_branches_enabled,
        "hybrid_filter_recovery_enabled": settings.hybrid_filter_recovery_enabled,
    }


def _is_loaded(service: object) -> bool:
    readiness = getattr(service, "is_ready", None)
    if callable(readiness):
        return bool(readiness())
    return getattr(service, "_model", None) is not None
