from secrets import compare_digest
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from ecommerce_search_assistant.core.config import Settings

internal_api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def require_internal_api_key(
    api_key: Annotated[str | None, Depends(internal_api_key_header)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> None:
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing internal API key",
        )
    if not compare_digest(api_key, settings.internal_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )
