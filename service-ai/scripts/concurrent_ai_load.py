#!/usr/bin/env python3
"""Closed-model concurrent load test for Text, Hybrid, and Assistant AI endpoints."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import csv
import json
import math
import mimetypes
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_HYBRID_QUERIES = WORKSPACE_ROOT / "evals/search_evaluation/hybrid/data/multimodal_queries.csv"
DEFAULT_TEXT_QUERIES = WORKSPACE_ROOT / "evals/search_evaluation/text/data/text_queries_v4_reduced.csv"
OPERATIONS = ("text_search", "hybrid_search", "assistant_chat")


@dataclass(frozen=True)
class Sample:
    operation: str
    latency_ms: float
    status: int
    valid_response: bool
    correlation_id_present: bool
    error: str = ""
    result_count: int = 0
    warnings: tuple[str, ...] = ()


def percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(samples: list[Sample]) -> dict[str, Any]:
    successful = [
        sample for sample in samples
        if 200 <= sample.status < 300 and sample.valid_response and not sample.error
    ]
    latencies = [sample.latency_ms for sample in successful]
    failures = len(samples) - len(successful)
    return {
        "requests": len(samples),
        "successful": len(successful),
        "failed": failures,
        "error_rate": round(failures / len(samples), 6) if samples else 0.0,
        "correlation_id_rate": round(
            sum(sample.correlation_id_present for sample in samples) / len(samples), 6
        ) if samples else 0.0,
        "p50_ms": round(percentile(latencies, 0.50), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "max_ms": round(max(latencies, default=0.0), 3),
    }


def request_json(
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float,
) -> tuple[int, Any, float, dict[str, str], str]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base_url.rstrip("/") + path, data=body, headers=headers,
                                     method="GET" if body is None else "POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            parsed = json.loads(raw) if raw else None
            return (
                response.status,
                parsed,
                (time.perf_counter() - started) * 1000,
                {key.casefold(): value for key, value in response.headers.items()},
                "",
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        return (
            exc.code,
            parsed,
            (time.perf_counter() - started) * 1000,
            {key.casefold(): value for key, value in exc.headers.items()},
            f"HTTP {exc.code}: {str(parsed)[:300]}",
        )
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        return 0, None, (time.perf_counter() - started) * 1000, {}, f"{type(exc).__name__}: {exc}"


def read_query_fixtures(path: Path, count: int) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fixtures = [row for row in rows if row.get("query_text") and row.get("image_url")]
    if len(fixtures) < count:
        raise ValueError(f"need {count} complete query fixtures, found {len(fixtures)}")
    return fixtures[:count]


def read_text_fixtures(path: Path, count: int) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fixtures = [row for row in rows if row.get("query_text")]
    if len(fixtures) < count:
        raise ValueError(f"need {count} text query fixtures, found {len(fixtures)}")
    return fixtures[:count]


def download_image_payload(url: str, timeout: float) -> dict[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "concurrent-ai-load/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
        content_type = response.headers.get_content_type()
    if not content:
        raise ValueError(f"empty fixture image: {url}")
    return {
        "filename": Path(url.split("?", 1)[0]).name or "load-fixture.jpg",
        "content_type": content_type or mimetypes.guess_type(url)[0] or "image/jpeg",
        "data_base64": base64.b64encode(content).decode("ascii"),
    }


def valid_response(operation: str, payload: Any, expected_session: str | None = None) -> bool:
    if not isinstance(payload, dict):
        return False
    if operation in ("text_search", "hybrid_search"):
        return isinstance(payload.get("results"), list) and isinstance(payload.get("product_ids"), list)
    return (
        payload.get("session_id") == expected_session
        and isinstance(payload.get("message"), str)
        and bool(payload.get("message"))
        and isinstance(payload.get("product_ids"), list)
    )


def valid_assistant_integration(sample: Sample) -> bool:
    """Reject a superficially valid reply that was produced through a degraded path."""
    degraded_markers = ("fallback", "failed", "unavailable")
    return (
        sample.operation == "assistant_chat"
        and sample.valid_response
        and not sample.error
        and sample.result_count > 0
        and not any(
            marker in warning
            for warning in sample.warnings
            for marker in degraded_markers
        )
    )


def execute_operation(
    operation: str,
    base_url: str,
    fixture: dict[str, str],
    image: dict[str, str],
    session_id: str,
    sequence: int,
    timeout: float,
) -> Sample:
    if operation == "text_search":
        path = "/search/text"
        payload = {"query": fixture["query_text"], "top_k": 5}
        expected_session = None
    elif operation == "hybrid_search":
        path = "/search/hybrid"
        payload = {"query": fixture["query_text"], "image": image, "top_k": 5}
        expected_session = None
    else:
        path = "/assistant/chat"
        payload = {
            "session_id": session_id,
            "user_id": f"load-user-{session_id}",
            "request_id": f"{session_id}-{sequence}",
            "turn_sequence": sequence,
            "message": fixture["query_text"],
            "locale": "vi-VN",
        }
        expected_session = session_id
    status, response, latency_ms, headers, error = request_json(
        base_url, path, payload, timeout=timeout
    )
    valid = 200 <= status < 300 and valid_response(operation, response, expected_session)
    if not error and not valid:
        error = "response_contract_invalid"
    result_count = 0
    warnings: tuple[str, ...] = ()
    if isinstance(response, dict):
        product_ids = response.get("product_ids")
        if isinstance(product_ids, list):
            result_count = len(product_ids)
        raw_warnings = response.get("warnings")
        if isinstance(raw_warnings, list):
            warnings = tuple(str(value) for value in raw_warnings if value)
    return Sample(
        operation=operation,
        latency_ms=latency_ms,
        status=status,
        valid_response=valid,
        correlation_id_present=bool(headers.get("x-correlation-id")),
        error=error,
        result_count=result_count,
        warnings=warnings,
    )


def worker(
    worker_id: int,
    operation: str,
    base_url: str,
    text_fixtures: list[dict[str, str]],
    hybrid_fixtures: list[dict[str, str]],
    images: list[dict[str, str]],
    barrier: threading.Barrier,
    duration_seconds: float,
    cycle_period_seconds: float,
    timeout: float,
    run_suffix: str,
) -> list[Sample]:
    samples: list[Sample] = []
    session_id = f"ai-load-{run_suffix}-w{worker_id}"
    sequence = 1
    barrier.wait()
    deadline = time.perf_counter() + duration_seconds
    next_cycle = time.perf_counter()
    while time.perf_counter() < deadline:
        fixtures = hybrid_fixtures if operation == "hybrid_search" else text_fixtures
        fixture = fixtures[(worker_id + sequence - 1) % len(fixtures)]
        image = images[(worker_id + sequence - 1) % len(images)]
        samples.append(execute_operation(
            operation, base_url, fixture, image, session_id, sequence, timeout
        ))
        sequence += 1
        next_cycle += cycle_period_seconds
        remaining = next_cycle - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)
        else:
            next_cycle = time.perf_counter()
    return samples


def parse_memory_bytes(value: str) -> float:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)", value.strip())
    if match is None:
        raise ValueError(f"unsupported Docker memory value: {value!r}")
    number_text, unit = match.groups()
    multipliers = {
        "B": 1, "kB": 1000, "KB": 1000, "KiB": 1024,
        "MB": 1000**2, "MiB": 1024**2,
        "GB": 1000**3, "GiB": 1024**3,
    }
    return float(number_text) * multipliers[unit]


def docker_stat(container: str) -> dict[str, Any] | None:
    if not container:
        return None
    completed = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}", container],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    raw = json.loads(completed.stdout.strip().splitlines()[-1])
    used_memory = raw.get("MemUsage", "0B / 0B").split("/", 1)[0].strip()
    return {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "cpu_percent": float(raw.get("CPUPerc", "0").rstrip("%") or 0),
        "memory_bytes": round(parse_memory_bytes(used_memory)),
        "memory_display": used_memory,
        "memory_percent": float(raw.get("MemPerc", "0").rstrip("%") or 0),
        "pids": int(raw.get("PIDs", 0) or 0),
        "net_io": raw.get("NetIO", ""),
        "block_io": raw.get("BlockIO", ""),
    }


def resource_sampler(container: str, interval: float, stop: threading.Event,
                     samples: list[dict[str, Any]]) -> None:
    while not stop.is_set():
        sample = docker_stat(container)
        if sample is not None:
            samples.append(sample)
        stop.wait(interval)


def summarize_resources(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {"sample_count": 0, "warning": "docker_stats_unavailable"}
    cpu = [float(row["cpu_percent"]) for row in samples]
    memory = [float(row["memory_bytes"]) for row in samples]
    return {
        "sample_count": len(samples),
        "cpu_p50_percent": round(percentile(cpu, 0.50), 3),
        "cpu_p95_percent": round(percentile(cpu, 0.95), 3),
        "cpu_max_percent": round(max(cpu), 3),
        "memory_start_mib": round(memory[0] / 1024**2, 3),
        "memory_end_mib": round(memory[-1] / 1024**2, 3),
        "memory_peak_mib": round(max(memory) / 1024**2, 3),
        "pids_max": max(int(row["pids"]) for row in samples),
        "first": samples[0],
        "last": samples[-1],
    }


def prometheus_snapshot(base_url: str, timeout: float) -> dict[str, float]:
    request = urllib.request.Request(base_url.rstrip("/") + "/metrics", headers={"Accept": "text/plain"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8")
    output: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#") or not line.startswith("ecommerce_"):
            continue
        try:
            name, value = line.rsplit(" ", 1)
            output[name] = float(value)
        except ValueError:
            continue
    return output


def metric_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {
        key: round(value - before.get(key, 0.0), 9)
        for key, value in after.items()
        if value != before.get(key, 0.0)
    }


def evaluate_thresholds(overall: dict[str, Any], operations: dict[str, dict[str, Any]],
                        max_error_rate: float, search_p95_ms: float,
                        assistant_p95_ms: float,
                        prometheus_delta: dict[str, float] | None = None) -> dict[str, Any]:
    metrics = prometheus_delta or {}
    assistant_fallback_free = not any(
        key.startswith("ecommerce_assistant_fallback_total{") and value > 0
        for key, value in metrics.items()
    )
    checks = {
        "overall_error_rate": overall["error_rate"] <= max_error_rate,
        "correlation_id_coverage": overall["correlation_id_rate"] == 1.0,
        "text_search_p95": operations["text_search"]["p95_ms"] <= search_p95_ms,
        "hybrid_search_p95": operations["hybrid_search"]["p95_ms"] <= search_p95_ms,
        "assistant_chat_p95": operations["assistant_chat"]["p95_ms"] <= assistant_p95_ms,
        "assistant_fallback_free": assistant_fallback_free,
        "each_operation_has_samples": all(value["requests"] > 0 for value in operations.values()),
    }
    return {"passed": all(checks.values()), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--cycle-period", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--fixture-count", type=int, default=6)
    parser.add_argument("--hybrid-queries-csv", type=Path, default=DEFAULT_HYBRID_QUERIES)
    parser.add_argument("--text-queries-csv", type=Path, default=DEFAULT_TEXT_QUERIES)
    parser.add_argument("--docker-container", default="service-ai-service-ai-1")
    parser.add_argument("--resource-interval", type=float, default=5.0)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--search-p95-ms", type=float, default=5000.0)
    parser.add_argument("--assistant-p95-ms", type=float, default=5000.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workers < len(OPERATIONS):
        raise ValueError(f"workers must be >= {len(OPERATIONS)} to cover every operation")
    if args.duration <= 0 or args.cycle_period <= 0:
        raise ValueError("duration and cycle period must be positive")

    base_url = args.base_url.rstrip("/")
    health_status, health_before, _, _, health_error = request_json(
        base_url, "/health/ready", timeout=args.timeout
    )
    if health_status != 200 or health_error or not health_before.get("ready"):
        raise RuntimeError(f"AI readiness preflight failed: {health_status} {health_error} {health_before}")
    if bool((health_before.get("effective_features") or {}).get("reranker_enabled")):
        raise RuntimeError("load baseline requires reranker_enabled=false")

    hybrid_fixtures = read_query_fixtures(args.hybrid_queries_csv, args.fixture_count)
    text_fixtures = read_text_fixtures(args.text_queries_csv, args.fixture_count)
    images = [download_image_payload(row["image_url"], args.timeout) for row in hybrid_fixtures]
    warmup_suffix = uuid.uuid4().hex[:8]
    warmup = [
        execute_operation(
            operation,
            base_url,
            hybrid_fixtures[index] if operation == "hybrid_search" else text_fixtures[index],
            images[index],
                          f"ai-load-warmup-{warmup_suffix}-{index}", 1, args.timeout)
        for index, operation in enumerate(OPERATIONS)
    ]
    if any(sample.error for sample in warmup):
        raise RuntimeError(f"warm-up failed: {[asdict(sample) for sample in warmup]}")
    assistant_warmup = next(sample for sample in warmup if sample.operation == "assistant_chat")
    if not valid_assistant_integration(assistant_warmup):
        raise RuntimeError(
            "assistant integration preflight failed: expected product results without "
            f"fallback/unavailable warnings; got {asdict(assistant_warmup)}"
        )

    metrics_before = prometheus_snapshot(base_url, args.timeout)
    resources: list[dict[str, Any]] = []
    stop_resources = threading.Event()
    resource_thread = threading.Thread(
        target=resource_sampler,
        args=(args.docker_container, args.resource_interval, stop_resources, resources),
        daemon=True,
    )
    resource_thread.start()

    run_suffix = uuid.uuid4().hex[:10]
    operations_by_worker = [OPERATIONS[index % len(OPERATIONS)] for index in range(args.workers)]
    barrier = threading.Barrier(args.workers + 1)
    started_at = datetime.now(UTC)
    wall_started = time.perf_counter()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    worker, worker_id, operations_by_worker[worker_id], base_url,
                    text_fixtures, hybrid_fixtures, images, barrier,
                    args.duration, args.cycle_period,
                    args.timeout, run_suffix,
                )
                for worker_id in range(args.workers)
            ]
            barrier.wait()
            all_samples = [sample for future in futures for sample in future.result()]
    finally:
        stop_resources.set()
        resource_thread.join(timeout=args.resource_interval + 16)
    elapsed = time.perf_counter() - wall_started
    metrics_after = prometheus_snapshot(base_url, args.timeout)
    _, health_after, _, _, _ = request_json(base_url, "/health/ready", timeout=args.timeout)

    grouped: dict[str, list[Sample]] = defaultdict(list)
    for sample in all_samples:
        grouped[sample.operation].append(sample)
    overall = summarize(all_samples)
    operation_summary = {operation: summarize(grouped[operation]) for operation in OPERATIONS}
    prometheus_delta_result = metric_delta(metrics_before, metrics_after)
    acceptance = evaluate_thresholds(
        overall, operation_summary, args.max_error_rate,
        args.search_p95_ms, args.assistant_p95_ms,
        prometheus_delta_result,
    )
    result = {
        "run_id": f"AI-CONCURRENT-{started_at.strftime('%Y%m%d-%H%M%S')}",
        "started_at_utc": started_at.isoformat(),
        "base_url": base_url,
        "workload_model": "closed",
        "workers": args.workers,
        "workers_by_operation": {
            operation: operations_by_worker.count(operation) for operation in OPERATIONS
        },
        "configured_duration_seconds": args.duration,
        "cycle_period_seconds": args.cycle_period,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_requests_per_second": round(len(all_samples) / elapsed, 3),
        "fixture_count": {
            "text_and_assistant": len(text_fixtures),
            "hybrid": len(hybrid_fixtures),
        },
        "warmup_excluded": [asdict(sample) for sample in warmup],
        "health_before": health_before,
        "health_after": health_after,
        "overall": overall,
        "operations": operation_summary,
        "resources": summarize_resources(resources),
        "prometheus_delta": prometheus_delta_result,
        "thresholds": {
            "max_error_rate": args.max_error_rate,
            "search_p95_ms": args.search_p95_ms,
            "assistant_p95_ms": args.assistant_p95_ms,
        },
        "acceptance": acceptance,
        "errors": [asdict(sample) for sample in all_samples if sample.error][:100],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if acceptance["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
