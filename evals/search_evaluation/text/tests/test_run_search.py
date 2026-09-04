from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "04_run_search.py"
SPEC = importlib.util.spec_from_file_location("text_run_search", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_percentile_uses_r7_linear_interpolation() -> None:
    assert MODULE._percentile([100.0, 200.0], 0.95) == pytest.approx(195.0)
    assert MODULE._percentile([], 0.95) is None


def test_latency_report_preserves_samples_and_rerank_state(tmp_path: Path) -> None:
    output_path = tmp_path / "latency.json"
    MODULE._write_latency_report(
        output_path,
        run_id="text-test",
        health={
            "instance_id": "instance-1",
            "started_at": "2026-08-30T00:00:00+00:00",
            "effective_features": {"reranker_enabled": False},
        },
        base_url="http://localhost:8000",
        endpoint="/search/text",
        top_k=20,
        expected_rerank=False,
        samples=[
            {"query_id": "q1", "latency_ms": 100.0, "success": True, "result_count": 5},
            {"query_id": "q2", "latency_ms": 200.0, "success": True, "result_count": 5},
        ],
        completed=True,
    )

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["completed"] is True
    assert report["rerank_expected"] is False
    assert report["rerank_observed"] is False
    assert report["successful_request_count"] == 2
    assert report["total_latency_ms"]["p95"] == pytest.approx(195.0)
    assert [row["query_id"] for row in report["requests"]] == ["q1", "q2"]
