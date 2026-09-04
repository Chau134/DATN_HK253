#!/usr/bin/env python3
"""Reproducible mixed Catalog--Cart load test using only the Python stdlib."""

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
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CATALOG_PATH = "/api/products?page=0&size=20&sort=newest"


@dataclass(frozen=True)
class Sample:
    operation: str
    latency_ms: float
    status: int
    error: str = ""


def request_json(base_url: str, method: str, path: str,
                 payload: dict[str, Any] | None = None,
                 token: str | None = None, timeout: float = 10.0) -> tuple[int, Any, float]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base_url + path, data=body, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None, (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        return exc.code, parsed, (time.perf_counter() - started) * 1000


def discover_variants(base_url: str, count: int) -> list[int]:
    status, page, _ = request_json(base_url, "GET", CATALOG_PATH)
    if status != 200:
        raise RuntimeError(f"Catalog fixture discovery failed with HTTP {status}: {page}")
    variants: list[int] = []
    for product in page.get("items", []):
        status, detail, _ = request_json(base_url, "GET", f"/api/products/{product['id']}")
        if status != 200:
            continue
        for variant in detail.get("variants", []):
            if variant.get("active") and variant.get("available") and (variant.get("inventory_count") or 0) >= 2:
                variants.append(int(variant["id"]))
                break
        if len(variants) >= count:
            return variants
    raise RuntimeError(f"Only found {len(variants)} usable variants; need {count}")


def create_accounts(base_url: str, workers: int) -> list[str]:
    suffix = uuid.uuid4().hex[:12]
    tokens: list[str] = []
    for worker_id in range(workers):
        status, response, _ = request_json(base_url, "POST", "/api/auth/register", {
            "email": f"mixed-load-{suffix}-{worker_id}@example.test",
            "password": "LoadTest!12345",
            "full_name": f"Mixed Load {worker_id}",
            "display_name": f"load-{worker_id}",
        })
        if status != 201:
            raise RuntimeError(f"Account setup failed with HTTP {status}: {response}")
        tokens.append(response["access_token"])
    return tokens


def matching_cart_item(response: dict[str, Any], variant_id: int) -> int:
    for item in response.get("items", []):
        if int(item.get("product_variant_id", -1)) == variant_id:
            return int(item["id"])
    raise RuntimeError(f"Cart response omitted variant {variant_id}")


def measured_request(samples: list[Sample], operation: str, base_url: str, method: str,
                     path: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    try:
        status, response, latency = request_json(base_url, method, path, payload, token)
        error = "" if 200 <= status < 300 else json.dumps(response, ensure_ascii=False)[:300]
        samples.append(Sample(operation, latency, status, error))
        if error:
            raise RuntimeError(error)
        return response
    except Exception as exc:
        if not samples or samples[-1].operation != operation:
            samples.append(Sample(operation, 0.0, 0, f"{type(exc).__name__}: {exc}"))
        raise


def worker(base_url: str, token: str, variant_id: int, barrier: threading.Barrier,
           duration_seconds: float, cycle_period_seconds: float) -> list[Sample]:
    samples: list[Sample] = []
    barrier.wait()
    deadline = time.perf_counter() + duration_seconds
    next_cycle = time.perf_counter()
    while time.perf_counter() < deadline:
        try:
            measured_request(samples, "catalog", base_url, "GET", CATALOG_PATH, token)
            measured_request(samples, "cart_read", base_url, "GET", "/api/cart", token)
            cart = measured_request(samples, "cart_add", base_url, "POST", "/api/cart/items", token,
                                    {"product_variant_id": variant_id, "quantity": 1})
            item_id = matching_cart_item(cart, variant_id)
            measured_request(samples, "cart_update", base_url, "PATCH", f"/api/cart/items/{item_id}", token,
                             {"quantity": 2, "selected": True})
            measured_request(samples, "cart_delete", base_url, "DELETE", f"/api/cart/items/{item_id}", token)
        except Exception:
            pass
        next_cycle += cycle_period_seconds
        remaining = next_cycle - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)
        else:
            next_cycle = time.perf_counter()
    return samples


def percentile(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * value / 100.0
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(samples: list[Sample]) -> dict[str, Any]:
    successful = [sample for sample in samples if 200 <= sample.status < 300 and not sample.error]
    latencies = [sample.latency_ms for sample in successful]
    return {
        "requests": len(samples), "successful": len(successful), "failed": len(samples) - len(successful),
        "p50_ms": round(percentile(latencies, 50), 2), "p95_ms": round(percentile(latencies, 95), 2),
        "p99_ms": round(percentile(latencies, 99), 2), "max_ms": round(max(latencies, default=0.0), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--duration", type=float, default=301.0)
    parser.add_argument("--cycle-period", type=float, default=2.5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    variants = discover_variants(base_url, args.workers)
    tokens = create_accounts(base_url, args.workers)
    barrier = threading.Barrier(args.workers + 1)
    started_at = datetime.now(timezone.utc)
    wall_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(worker, base_url, tokens[i], variants[i], barrier, args.duration,
                                   args.cycle_period) for i in range(args.workers)]
        barrier.wait()
        all_samples = [sample for future in futures for sample in future.result()]
    elapsed = time.perf_counter() - wall_started
    by_operation: dict[str, list[Sample]] = defaultdict(list)
    for sample in all_samples:
        by_operation[sample.operation].append(sample)
    result = {
        "run_id": f"MIXED-LOAD-{started_at.strftime('%Y%m%d-%H%M%S')}",
        "started_at_utc": started_at.isoformat(), "base_url": base_url, "workers": args.workers,
        "configured_duration_seconds": args.duration, "cycle_period_seconds": args.cycle_period,
        "elapsed_seconds": round(elapsed, 3), "throughput_requests_per_second": round(len(all_samples) / elapsed, 3),
        "overall": summarize(all_samples),
        "operations": {name: summarize(values) for name, values in sorted(by_operation.items())},
        "errors": [asdict(sample) for sample in all_samples if sample.error][:100],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
