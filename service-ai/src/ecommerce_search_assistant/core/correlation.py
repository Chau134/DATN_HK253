from __future__ import annotations

from contextvars import ContextVar, Token
import re
from uuid import uuid4

CORRELATION_ID_HEADER = "X-Correlation-ID"
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def resolve_correlation_id(candidate: str | None) -> str:
    normalized = candidate.strip() if candidate else ""
    if _CORRELATION_ID_PATTERN.fullmatch(normalized):
        return normalized
    return str(uuid4())


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str) -> Token[str | None]:
    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str | None]) -> None:
    _correlation_id.reset(token)
