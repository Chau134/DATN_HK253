import json
import logging
import sys

from ecommerce_search_assistant.core.logging import JsonFormatter


def test_json_formatter_redacts_secrets_from_messages_exceptions_and_extras() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("Invalid header b'Bearer ABSK-secret-value\\r\\n'")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=10,
            msg="request failed with Bearer ABSK-another-secret",
            args=(),
            exc_info=sys.exc_info(),
        )
        record.internal_api_key = "private-value"
        payload = json.loads(formatter.format(record))

    serialized = json.dumps(payload)
    assert "ABSK-secret-value" not in serialized
    assert "ABSK-another-secret" not in serialized
    assert "private-value" not in serialized
    assert "[REDACTED]" in serialized
