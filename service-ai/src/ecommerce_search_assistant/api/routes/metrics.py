from fastapi import APIRouter, Response

from ecommerce_search_assistant.core.metrics import assistant_metrics, search_metrics


router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(
        content=search_metrics.render_prometheus() + assistant_metrics.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
