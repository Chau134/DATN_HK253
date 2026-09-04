from __future__ import annotations

import json
import logging

from ecommerce_search_assistant.core.correlation import reset_correlation_id, set_correlation_id
from ecommerce_search_assistant.core.logging import JsonFormatter


def test_json_log_includes_request_correlation_id() -> None:
    token = set_correlation_id("backend-request-42")
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="search_started",
            args=(),
            exc_info=None,
        )
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_correlation_id(token)

    assert payload["correlation_id"] == "backend-request-42"
