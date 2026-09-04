from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from logging.config import dictConfig
import re
from typing import Any

from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.core.correlation import get_correlation_id

_STANDARD_LOG_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}

_SENSITIVE_KEY_PARTS = ("authorization", "api_key", "apikey", "password", "secret", "token")
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[^\s'\"\\]+"),
    re.compile(r"\bABSK[A-Za-z0-9+/=_-]+"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
_SENSITIVE_QUERY_PATTERN = re.compile(r"(?i)([?&](?:access_token|api_key|key|token)=)[^&\s]+")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage()),
        }
        correlation_id = get_correlation_id()
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_KEYS
        }
        if extra_fields:
            payload.update(_redact(extra_fields))

        if record.exc_info:
            payload["exception"] = _redact(self.formatException(record.exc_info))

        return json.dumps(payload, default=str)


def _redact(value: Any, key: str | None = None) -> Any:
    if key is not None and any(part in key.lower() for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {item_key: _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if not isinstance(value, str):
        return value

    redacted = value
    for pattern in _SENSITIVE_VALUE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return _SENSITIVE_QUERY_PATTERN.sub(r"\1[REDACTED]", redacted)


def configure_logging(settings: Settings) -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "ecommerce_search_assistant.core.logging.JsonFormatter",
                },
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "handlers": ["stdout"],
                "level": settings.log_level.upper(),
            },
            "loggers": {
                "uvicorn": {"handlers": ["stdout"], "level": settings.log_level.upper(), "propagate": False},
                "uvicorn.error": {
                    "handlers": ["stdout"],
                    "level": settings.log_level.upper(),
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["stdout"],
                    "level": settings.log_level.upper(),
                    "propagate": False,
                },
            },
        }
    )
