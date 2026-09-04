#!/usr/bin/env python3
"""Checkout/payment load and soak test using only the Python standard library.

The workload creates one isolated COD fixture per worker, repeatedly exercises
idempotent checkout/payment operations, and cancels the payment at the end so
reserved inventory is released. No external payment gateway is contacted.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATALOG_PATH = "/api/products?page=0&size=50&sort=newest"


@dataclass(frozen=True)
class Sample:
    operation: str
    latency_ms: float
    status: int
    valid_response: bool
    correlation_id_present: bool
    error: str = ""


@dataclass
class WorkerFixture:
    worker_id: int
    variant_id: int
    access_token: str
    refresh_token: str
    token_expires_at: float
    address_id: int
    checkout_cart_id: int
    preview_cart_id: int
    order_id: int
    payment_id: int
    payment_idempotency_key: str
    token_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


def request_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 15.0,
) -> tuple[int, Any, float, dict[str, str], str]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "checkout-payment-soak/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base_url + path, data=body, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            parsed = json.loads(raw) if raw else None
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, parsed, (time.perf_counter() - started) * 1000, response_headers, ""
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        response_headers = {key.lower(): value for key, value in exc.headers.items()}
        return exc.code, parsed, (time.perf_counter() - started) * 1000, response_headers, _error_text(parsed)
    except Exception as exc:
        return 0, None, (time.perf_counter() - started) * 1000, {}, f"{type(exc).__name__}: {exc}"


def _error_text(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False)[:500]
    except TypeError:
        return str(payload)[:500]


def require_success(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    expected_statuses: tuple[int, ...] = (200,),
    timeout: float = 15.0,
) -> Any:
    status, response, _, _, error = request_json(base_url, method, path, payload, token, timeout)
    if status not in expected_statuses:
        raise RuntimeError(f"{method} {path} failed with HTTP {status}: {error or response}")
    return response


def discover_variants(base_url: str, count: int, timeout: float) -> list[int]:
    page = require_success(base_url, "GET", CATALOG_PATH, timeout=timeout)
    variants: list[int] = []
    for product in page.get("items", []):
        detail = require_success(base_url, "GET", f"/api/products/{product['id']}", timeout=timeout)
        for variant in detail.get("variants", []):
            if variant.get("active") and variant.get("available") and int(variant.get("inventory_count") or 0) >= 2:
                variants.append(int(variant["id"]))
                break
        if len(variants) >= count:
            return variants
    raise RuntimeError(f"Only found {len(variants)} usable variants; need {count}")


def create_fixture(base_url: str, worker_id: int, variant_id: int, timeout: float) -> WorkerFixture:
    suffix = uuid.uuid4().hex[:12]
    auth = require_success(
        base_url,
        "POST",
        "/api/auth/register",
        {
            "email": f"checkout-soak-{suffix}-{worker_id}@example.test",
            "password": "LoadTest!12345",
            "full_name": f"Checkout Soak {worker_id}",
            "display_name": f"checkout-soak-{worker_id}",
        },
        expected_statuses=(201,),
        timeout=timeout,
    )
    token = auth["access_token"]
    expires_in = float(auth.get("expires_in") or 900)
    address = require_success(
        base_url,
        "POST",
        "/api/me/addresses",
        {
            "address_type": "SHIPPING",
            "recipient_name": f"Checkout Soak {worker_id}",
            "phone_number": "0900000000",
            "address_line1": f"{worker_id + 1} Performance Street",
            "ward": "Ben Nghe",
            "district": "District 1",
            "city": "Ho Chi Minh City",
            "province": "Ho Chi Minh",
            "country_code": "VN",
            "postal_code": "70000",
            "is_default": True,
        },
        token,
        expected_statuses=(201,),
        timeout=timeout,
    )
    first_cart = require_success(
        base_url,
        "POST",
        "/api/cart/items",
        {"product_variant_id": variant_id, "quantity": 1},
        token,
        timeout=timeout,
    )
    checkout_cart_id = int(first_cart["id"])
    checkout_payload = {
        "cart_id": checkout_cart_id,
        "shipping_address_id": int(address["id"]),
        "customer_note": "Automated checkout/payment performance fixture",
    }
    order = require_success(base_url, "POST", "/api/checkout", checkout_payload, token, timeout=timeout)
    payment_key = f"soak-cod-{suffix}-{worker_id}"
    payment = require_success(
        base_url,
        "POST",
        "/api/payments/cod",
        {"order_id": int(order["id"]), "idempotency_key": payment_key, "note": "performance fixture"},
        token,
        timeout=timeout,
    )
    preview_cart = require_success(
        base_url,
        "POST",
        "/api/cart/items",
        {"product_variant_id": variant_id, "quantity": 1},
        token,
        timeout=timeout,
    )
    require_success(
        base_url,
        "POST",
        "/api/checkout/preview",
        {"cart_id": int(preview_cart["id"])},
        token,
        timeout=timeout,
    )
    return WorkerFixture(
        worker_id=worker_id,
        variant_id=variant_id,
        access_token=token,
        refresh_token=auth["refresh_token"],
        token_expires_at=time.monotonic() + expires_in,
        address_id=int(address["id"]),
        checkout_cart_id=checkout_cart_id,
        preview_cart_id=int(preview_cart["id"]),
        order_id=int(order["id"]),
        payment_id=int(payment["id"]),
        payment_idempotency_key=payment_key,
    )


def current_token(base_url: str, fixture: WorkerFixture, timeout: float) -> str:
    with fixture.token_lock:
        if time.monotonic() < fixture.token_expires_at - 90:
            return fixture.access_token
        auth = require_success(
            base_url,
            "POST",
            "/api/auth/refresh",
            {"refresh_token": fixture.refresh_token},
            expected_statuses=(200,),
            timeout=timeout,
        )
        fixture.access_token = auth["access_token"]
        fixture.refresh_token = auth["refresh_token"]
        fixture.token_expires_at = time.monotonic() + float(auth.get("expires_in") or 900)
        return fixture.access_token


def execute_operation(
    base_url: str,
    fixture: WorkerFixture,
    operation: str,
    timeout: float,
) -> Sample:
    try:
        token = current_token(base_url, fixture, timeout)
    except Exception as exc:
        return Sample(operation, 0.0, 0, False, False, f"token_refresh_failed: {type(exc).__name__}: {exc}")

    if operation == "checkout_preview":
        method, path = "POST", "/api/checkout/preview"
        payload = {"cart_id": fixture.preview_cart_id}
        validator = lambda value: (
            isinstance(value, dict)
            and all(
                key in value
                for key in (
                    "subtotal_amount",
                    "total_discount_amount",
                    "shipping_fee",
                    "tax_amount",
                    "total_amount",
                )
            )
        )
    elif operation == "checkout_idempotent":
        method, path = "POST", "/api/checkout"
        payload = {"cart_id": fixture.checkout_cart_id, "shipping_address_id": fixture.address_id}
        validator = lambda value: isinstance(value, dict) and value.get("id") == fixture.order_id
    elif operation == "payment_cod_idempotent":
        method, path = "POST", "/api/payments/cod"
        payload = {"order_id": fixture.order_id, "idempotency_key": fixture.payment_idempotency_key}
        validator = lambda value: isinstance(value, dict) and value.get("id") == fixture.payment_id
    elif operation == "payment_read":
        method, path, payload = "GET", f"/api/payments/{fixture.payment_id}", None
        validator = lambda value: isinstance(value, dict) and value.get("id") == fixture.payment_id
    else:
        method, path, payload = "GET", f"/api/orders/{fixture.order_id}", None
        validator = lambda value: isinstance(value, dict) and value.get("id") == fixture.order_id

    status, response, latency_ms, headers, request_error = request_json(
        base_url, method, path, payload, token, timeout
    )
    valid = 200 <= status < 300 and validator(response)
    error = request_error
    if not error and not valid:
        error = "response_contract_or_idempotency_violation"
    return Sample(
        operation=operation,
        latency_ms=latency_ms,
        status=status,
        valid_response=valid,
        correlation_id_present=bool(headers.get("x-correlation-id")),
        error=error,
    )


def worker(
    base_url: str,
    fixture: WorkerFixture,
    barrier: threading.Barrier,
    run_stop_event: threading.Event,
    duration_seconds: float,
    cycle_period_seconds: float,
    timeout: float,
) -> list[Sample]:
    samples: list[Sample] = []
    operations = (
        "checkout_preview",
        "checkout_idempotent",
        "payment_cod_idempotent",
        "payment_read",
        "order_read",
    )
    barrier.wait()
    deadline = time.perf_counter() + duration_seconds
    next_cycle = time.perf_counter()
    while time.perf_counter() < deadline and not run_stop_event.is_set():
        for operation in operations:
            if run_stop_event.is_set():
                break
            samples.append(execute_operation(base_url, fixture, operation, timeout))
        next_cycle += cycle_period_seconds
        remaining = next_cycle - time.perf_counter()
        if remaining > 0 and not run_stop_event.is_set():
            run_stop_event.wait(remaining)
        else:
            next_cycle = time.perf_counter()
    return samples


def percentile(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * value / 100.0
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(samples: list[Sample]) -> dict[str, Any]:
    successful = [sample for sample in samples if 200 <= sample.status < 300 and sample.valid_response and not sample.error]
    latencies = [sample.latency_ms for sample in successful]
    correlated = [sample for sample in successful if sample.correlation_id_present]
    return {
        "requests": len(samples),
        "successful": len(successful),
        "failed": len(samples) - len(successful),
        "error_rate": round((len(samples) - len(successful)) / len(samples), 6) if samples else 1.0,
        "correlation_id_rate": round(len(correlated) / len(successful), 6) if successful else 0.0,
        "p50_ms": round(percentile(latencies, 50), 3),
        "p95_ms": round(percentile(latencies, 95), 3),
        "p99_ms": round(percentile(latencies, 99), 3),
        "max_ms": round(max(latencies, default=0.0), 3),
    }


def parse_prometheus(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    heap_used = 0.0
    nonheap_used = 0.0
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        try:
            key, raw_value = line.rsplit(" ", 1)
            value = float(raw_value)
        except (ValueError, TypeError):
            continue
        if key.startswith('jvm_memory_used_bytes{area="heap"'):
            heap_used += value
        elif key.startswith('jvm_memory_used_bytes{area="nonheap"'):
            nonheap_used += value
        elif key in {"process_cpu_usage", "system_cpu_usage", "process_uptime_seconds"}:
            values[key] = value
        elif key.startswith("hikaricp_connections_active{"):
            values["hikari_active"] = value
        elif key.startswith("hikaricp_connections_idle{"):
            values["hikari_idle"] = value
        elif key.startswith("hikaricp_connections_pending{"):
            values["hikari_pending"] = value
        elif key.startswith("hikaricp_connections_max{"):
            values["hikari_max"] = value
    values["jvm_heap_used_bytes"] = heap_used
    values["jvm_nonheap_used_bytes"] = nonheap_used
    return values


def resource_sampler(
    base_url: str,
    interval_seconds: float,
    stop_event: threading.Event,
    samples: list[dict[str, Any]],
    timeout: float,
) -> None:
    while not stop_event.is_set():
        captured_at = datetime.now(timezone.utc).isoformat()
        health_status, health, _, _, health_error = request_json(
            base_url, "GET", "/actuator/health", timeout=timeout
        )
        try:
            with urllib.request.urlopen(base_url + "/actuator/prometheus", timeout=timeout) as response:
                metrics = parse_prometheus(response.read().decode("utf-8", errors="replace"))
        except Exception as exc:
            metrics = {"metrics_error": f"{type(exc).__name__}: {exc}"}
        samples.append({
            "captured_at_utc": captured_at,
            "health_status": health_status,
            "health": health,
            "health_error": health_error,
            **metrics,
        })
        stop_event.wait(interval_seconds)


def summarize_resources(samples: list[dict[str, Any]]) -> dict[str, Any]:
    def numeric(name: str) -> list[float]:
        return [float(sample[name]) for sample in samples if isinstance(sample.get(name), (int, float))]

    heap = numeric("jvm_heap_used_bytes")
    nonheap = numeric("jvm_nonheap_used_bytes")
    cpu = numeric("process_cpu_usage")
    pending = numeric("hikari_pending")
    active = numeric("hikari_active")
    window_size = max(1, len(heap) // 5)
    heap_first_window = heap[:window_size]
    heap_last_window = heap[-window_size:]
    heap_first_median = percentile(heap_first_window, 50) if heap_first_window else None
    heap_last_median = percentile(heap_last_window, 50) if heap_last_window else None
    return {
        "sample_count": len(samples),
        "health_failures": sum(1 for sample in samples if sample.get("health_status") != 200 or sample.get("health", {}).get("status") != "UP"),
        "heap_start_mib": round(heap[0] / 1048576, 3) if heap else None,
        "heap_end_mib": round(heap[-1] / 1048576, 3) if heap else None,
        "heap_peak_mib": round(max(heap) / 1048576, 3) if heap else None,
        "heap_growth_mib": round((heap[-1] - heap[0]) / 1048576, 3) if heap else None,
        "heap_steady_growth_mib": round((heap_last_median - heap_first_median) / 1048576, 3)
        if heap_first_median is not None and heap_last_median is not None else None,
        "nonheap_peak_mib": round(max(nonheap) / 1048576, 3) if nonheap else None,
        "process_cpu_p95_percent": round(percentile(cpu, 95) * 100, 3) if cpu else None,
        "process_cpu_max_percent": round(max(cpu) * 100, 3) if cpu else None,
        "hikari_active_max": max(active, default=None),
        "hikari_pending_max": max(pending, default=None),
        "first": samples[0] if samples else None,
        "last": samples[-1] if samples else None,
    }


def cleanup_fixture(base_url: str, fixture: WorkerFixture, timeout: float) -> dict[str, Any]:
    try:
        token = current_token(base_url, fixture, timeout)
        status, response, latency, _, error = request_json(
            base_url,
            "POST",
            f"/api/payments/{fixture.payment_id}/cancel",
            {
                "idempotency_key": f"cleanup-{fixture.payment_id}",
                "reason": "performance_test_cleanup",
                "note": "Release soak-test reservation",
            },
            token,
            timeout,
        )
        return {"worker_id": fixture.worker_id, "status": status, "latency_ms": round(latency, 3), "error": error, "payment_status": response.get("status") if isinstance(response, dict) else None}
    except Exception as exc:
        return {"worker_id": fixture.worker_id, "status": 0, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--mode", choices=("load", "soak"), default="load")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--duration", type=float, default=300.0)
    parser.add_argument("--cycle-period", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--resource-interval", type=float, default=30.0)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--p95-threshold-ms", type=float, default=1000.0)
    parser.add_argument("--max-heap-growth-mib", type=float, default=128.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workers < 1 or args.duration <= 0 or args.cycle_period <= 0:
        parser.error("workers, duration and cycle-period must be positive")

    base_url = args.base_url.rstrip("/")
    health = require_success(base_url, "GET", "/actuator/health", timeout=args.timeout)
    if health.get("status") != "UP":
        raise RuntimeError(f"Backend health is not UP: {health}")

    variants = discover_variants(base_url, args.workers, args.timeout)
    fixtures: list[WorkerFixture] = []
    for worker_id, variant_id in enumerate(variants):
        fixtures.append(create_fixture(base_url, worker_id, variant_id, args.timeout))

    barrier = threading.Barrier(args.workers + 1)
    resource_samples: list[dict[str, Any]] = []
    stop_event = threading.Event()
    run_stop_event = threading.Event()
    resource_thread = threading.Thread(
        target=resource_sampler,
        args=(base_url, args.resource_interval, stop_event, resource_samples, args.timeout),
        daemon=True,
    )
    started_at = datetime.now(timezone.utc)
    wall_started = time.perf_counter()
    resource_thread.start()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
    cleanup: list[dict[str, Any]] = []
    try:
        futures = [
            executor.submit(
                worker,
                base_url,
                fixture,
                barrier,
                run_stop_event,
                args.duration,
                args.cycle_period,
                args.timeout,
            )
            for fixture in fixtures
        ]
        barrier.wait()
        all_samples = [sample for future in futures for sample in future.result()]
    finally:
        run_stop_event.set()
        barrier.abort()
        executor.shutdown(wait=True, cancel_futures=True)
        stop_event.set()
        resource_thread.join(timeout=args.resource_interval + args.timeout + 5)
        cleanup = [cleanup_fixture(base_url, fixture, args.timeout) for fixture in fixtures]
    elapsed = time.perf_counter() - wall_started

    by_operation: dict[str, list[Sample]] = defaultdict(list)
    for sample in all_samples:
        by_operation[sample.operation].append(sample)
    overall = summarize(all_samples)
    operations = {name: summarize(values) for name, values in sorted(by_operation.items())}
    resources = summarize_resources(resource_samples)
    health_after = require_success(base_url, "GET", "/actuator/health", timeout=args.timeout)

    checks = {
        "duration_completed": elapsed >= args.duration * 0.98,
        "overall_error_rate": overall["error_rate"] <= args.max_error_rate,
        "correlation_id_coverage": overall["correlation_id_rate"] == 1.0,
        "each_operation_has_samples": all(summary["requests"] > 0 for summary in operations.values()) and len(operations) == 5,
        "operation_p95": all(summary["p95_ms"] <= args.p95_threshold_ms for summary in operations.values()),
        "health_stayed_up": resources["health_failures"] == 0 and health_after.get("status") == "UP",
        "hikari_no_pending": (resources["hikari_pending_max"] or 0) == 0,
        "cleanup_succeeded": all(item.get("status") == 200 and item.get("payment_status") == "CANCELLED" for item in cleanup),
    }
    if args.mode == "soak":
        checks["heap_growth"] = (
            resources["heap_steady_growth_mib"] is not None
            and resources["heap_steady_growth_mib"] <= args.max_heap_growth_mib
        )

    result = {
        "run_id": f"CHECKOUT-PAYMENT-{args.mode.upper()}-{started_at.strftime('%Y%m%d-%H%M%S')}",
        "started_at_utc": started_at.isoformat(),
        "base_url": base_url,
        "mode": args.mode,
        "workload": "idempotent_checkout_cod_payment_reads",
        "external_payment_gateway_called": False,
        "workers": args.workers,
        "configured_duration_seconds": args.duration,
        "cycle_period_seconds": args.cycle_period,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_requests_per_second": round(len(all_samples) / elapsed, 3),
        "fixture_count": len(fixtures),
        "overall": overall,
        "operations": operations,
        "resources": resources,
        "health_before": health,
        "health_after": health_after,
        "cleanup": cleanup,
        "thresholds": {
            "max_error_rate": args.max_error_rate,
            "p95_threshold_ms": args.p95_threshold_ms,
            "max_heap_growth_mib": args.max_heap_growth_mib if args.mode == "soak" else None,
        },
        "acceptance": {"passed": all(checks.values()), "checks": checks},
        "errors": [asdict(sample) for sample in all_samples if sample.error][:200],
        "resource_samples": resource_samples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
