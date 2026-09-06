from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "concurrent_ai_load.py"
spec = importlib.util.spec_from_file_location("concurrent_ai_load", SCRIPT)
assert spec and spec.loader
LOAD = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = LOAD
spec.loader.exec_module(LOAD)


def sample(operation: str, latency: float, *, status: int = 200,
           valid: bool = True, correlation: bool = True, error: str = ""):
    return LOAD.Sample(operation, latency, status, valid, correlation, error)


def test_percentile_uses_linear_interpolation() -> None:
    assert LOAD.percentile([100, 200, 300], 0.95) == pytest.approx(290)


def test_summary_excludes_failed_response_from_latency() -> None:
    summary = LOAD.summarize([
        sample("text_search", 100),
        sample("text_search", 999, status=500, valid=False, error="failed"),
    ])
    assert summary["successful"] == 1
    assert summary["failed"] == 1
    assert summary["error_rate"] == 0.5
    assert summary["p95_ms"] == 100


def test_memory_parser_supports_docker_binary_units() -> None:
    assert LOAD.parse_memory_bytes("140.5MiB") == pytest.approx(140.5 * 1024**2)
    assert LOAD.parse_memory_bytes("1.25 GiB") == pytest.approx(1.25 * 1024**3)


def test_thresholds_are_checked_per_endpoint() -> None:
    overall = {"error_rate": 0.0, "correlation_id_rate": 1.0}
    operations = {
        "text_search": {"requests": 10, "p95_ms": 1000},
        "hybrid_search": {"requests": 10, "p95_ms": 2000},
        "assistant_chat": {"requests": 10, "p95_ms": 5000},
    }
    result = LOAD.evaluate_thresholds(overall, operations, 0.01, 5000, 5000)
    assert result["passed"]


def test_assistant_above_nfr_p95_is_rejected() -> None:
    overall = {"error_rate": 0.0, "correlation_id_rate": 1.0}
    operations = {
        "text_search": {"requests": 10, "p95_ms": 1000},
        "hybrid_search": {"requests": 10, "p95_ms": 2000},
        "assistant_chat": {"requests": 10, "p95_ms": 5318},
    }

    result = LOAD.evaluate_thresholds(overall, operations, 0.01, 5000, 5000)

    assert not result["passed"]
    assert not result["checks"]["assistant_chat_p95"]


def test_assistant_fallback_metric_is_rejected() -> None:
    overall = {"error_rate": 0.0, "correlation_id_rate": 1.0}
    operations = {
        "text_search": {"requests": 10, "p95_ms": 1000},
        "hybrid_search": {"requests": 10, "p95_ms": 2000},
        "assistant_chat": {"requests": 10, "p95_ms": 4000},
    }
    metrics = {
        'ecommerce_assistant_fallback_total{reason="spring_boot_unavailable"}': 1.0,
    }

    result = LOAD.evaluate_thresholds(overall, operations, 0.01, 5000, 5000, metrics)

    assert not result["passed"]
    assert not result["checks"]["assistant_fallback_free"]


def test_assistant_integration_preflight_rejects_degraded_reply() -> None:
    healthy = LOAD.Sample("assistant_chat", 1000, 200, True, True, result_count=3)
    degraded = LOAD.Sample(
        "assistant_chat",
        1000,
        200,
        True,
        True,
        result_count=3,
        warnings=("spring_boot_unavailable",),
    )

    assert LOAD.valid_assistant_integration(healthy)
    assert not LOAD.valid_assistant_integration(degraded)


def test_invalid_response_contract_is_rejected() -> None:
    assert not LOAD.valid_response("text_search", {"product_ids": []})
    assert not LOAD.valid_response("assistant_chat", {"session_id": "wrong", "message": "ok", "product_ids": []}, "expected")


def test_text_and_hybrid_fixtures_are_loaded_separately(tmp_path: Path) -> None:
    text_path = tmp_path / "text.csv"
    text_path.write_text("query_text\náo thun nâu\n", encoding="utf-8")
    hybrid_path = tmp_path / "hybrid.csv"
    hybrid_path.write_text(
        "query_text,image_url\ntìm giống ảnh,https://example.test/image.jpg\n",
        encoding="utf-8",
    )

    assert LOAD.read_text_fixtures(text_path, 1)[0]["query_text"] == "áo thun nâu"
    assert LOAD.read_query_fixtures(hybrid_path, 1)[0]["query_text"] == "tìm giống ảnh"
