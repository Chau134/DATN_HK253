from __future__ import annotations

import re

from fastapi.testclient import TestClient

from ecommerce_search_assistant.core.correlation import CORRELATION_ID_HEADER


def test_preserves_valid_incoming_correlation_id(client: TestClient) -> None:
    response = client.get("/health", headers={CORRELATION_ID_HEADER: "backend-request-42"})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == "backend-request-42"


def test_generates_correlation_id_for_missing_or_invalid_header(client: TestClient) -> None:
    missing_response = client.get("/health")
    invalid_response = client.get(
        "/health",
        headers={CORRELATION_ID_HEADER: "unsafe correlation value"},
    )

    pattern = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
    assert pattern.fullmatch(missing_response.headers[CORRELATION_ID_HEADER])
    assert pattern.fullmatch(invalid_response.headers[CORRELATION_ID_HEADER])
    assert invalid_response.headers[CORRELATION_ID_HEADER] != "unsafe correlation value"
