from __future__ import annotations

import argparse
import json
import statistics
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from time import perf_counter

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import call_text_search, json_response_from_text_search, load_json_config, read_csv_rows, write_csv_rows

RESULT_FIELDNAMES = ["run_id", "query_id", "mode", "rank", "product_id", "score", "raw_score_json"]


def main() -> int:
    args = parse_args()
    config = load_json_config(args.config) if args.config and args.config.exists() else {}
    paths = config.get("paths", {})

    query_set_csv = args.query_set_csv or _config_path(paths.get("query_set_csv"))
    output_csv = args.output_csv or _config_path(paths.get("search_results_csv")) or (SCRIPT_DIR.parent / "data" / "search_results_text.csv")
    latency_output_json = args.latency_output_json or _config_path(paths.get("latency_json"))
    run_id = args.run_id or f"text-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    all_query_rows = read_csv_rows(query_set_csv)
    query_rows = [
        row
        for row in all_query_rows
        if args.query_type == "all" or row.get("query_type") == args.query_type
    ]
    selected_query_ids = {row.get("query_id", "") for row in query_rows}
    health_url = args.health_url or args.base_url.rstrip("/") + "/health/ready/text_search"
    health_status, health = _get_json(health_url, min(args.timeout, 10))
    if health_status != 200 or health.get("ready") is not True:
        print(f"preflight failed status={health_status} body={health}")
        return 2
    expected_rerank = (config.get("rerank") or {}).get("enabled")
    actual_rerank = (health.get("effective_features") or {}).get("reranker_enabled")
    if expected_rerank is not None and actual_rerank is not expected_rerank:
        print(
            "preflight failed: rerank state does not match evaluation config "
            f"expected={expected_rerank} actual={actual_rerank}"
        )
        return 2
    instance_id = health.get("instance_id")
    request_latencies: list[dict] = []

    result_rows: list[dict] = []
    if args.merge_existing and output_csv.exists():
        result_rows = [
            row
            for row in read_csv_rows(output_csv)
            if row.get("query_id", "") not in selected_query_ids
        ]
    error_count = 0
    for index, query_row in enumerate(query_rows, 1):
        if args.health_check_every > 0 and index > 1 and (index - 1) % args.health_check_every == 0:
            current_status, current_health = _get_json(health_url, min(args.timeout, 10))
            instance_changed = (
                instance_id
                and current_health.get("instance_id")
                and current_health.get("instance_id") != instance_id
            )
            if current_status != 200 or current_health.get("ready") is not True or instance_changed:
                print(
                    "run invalidated by unhealthy/restarted service-ai "
                    f"status={current_status} instance_changed={bool(instance_changed)}"
                )
                return 2
        query_id = query_row.get("query_id", "")
        query_text = query_row.get("query_text", "")
        if not query_text:
            continue
        request_started = perf_counter()
        try:
            raw_response = call_text_search(args.base_url, args.endpoint, query_text, args.top_k, args.timeout)
        except RuntimeError as exc:
            latency_ms = (perf_counter() - request_started) * 1000
            error_count += 1
            request_latencies.append(
                {
                    "query_id": query_id,
                    "query_type": query_row.get("query_type", ""),
                    "latency_ms": round(latency_ms, 3),
                    "result_count": 0,
                    "success": False,
                    "error": str(exc),
                }
            )
            result_rows.append(
                {
                    "run_id": run_id,
                    "query_id": query_id,
                    "mode": "text",
                    "rank": 0,
                    "product_id": "",
                    "score": "",
                    "raw_score_json": json.dumps({"error": str(exc)}, ensure_ascii=False, separators=(",", ":")),
                }
            )
            write_csv_rows(output_csv, result_rows, RESULT_FIELDNAMES)
            _write_latency_report(
                latency_output_json,
                run_id=run_id,
                health=health,
                base_url=args.base_url,
                endpoint=args.endpoint,
                top_k=args.top_k,
                expected_rerank=expected_rerank,
                samples=request_latencies,
                completed=False,
            )
            print(f"[{index:03d}/{len(query_rows):03d}] {query_id} error={exc}")
            return 2
        latency_ms = (perf_counter() - request_started) * 1000
        request_latencies.append(
            {
                "query_id": query_id,
                "query_type": query_row.get("query_type", ""),
                "latency_ms": round(latency_ms, 3),
                "result_count": len(raw_response.get("results", [])),
                "success": True,
            }
        )
        sources = {
            str(item.get("source", ""))
            for item in raw_response.get("results", [])
        }
        if sources and sources != {"text"}:
            print(f"[{index:03d}/{len(query_rows):03d}] {query_id} degraded sources={sources}")
            return 2
        result_rows.extend(
            json_response_from_text_search(
                raw_response,
                query_id=query_id,
                run_id=run_id,
                top_k=args.top_k,
            )
        )
        write_csv_rows(output_csv, result_rows, RESULT_FIELDNAMES)
        _write_latency_report(
            latency_output_json,
            run_id=run_id,
            health=health,
            base_url=args.base_url,
            endpoint=args.endpoint,
            top_k=args.top_k,
            expected_rerank=expected_rerank,
            samples=request_latencies,
            completed=False,
        )
        print(
            f"[{index:03d}/{len(query_rows):03d}] {query_id} "
            f"results={len(raw_response.get('results', []))} latency_ms={latency_ms:.1f}",
            flush=True,
        )

    _write_latency_report(
        latency_output_json,
        run_id=run_id,
        health=health,
        base_url=args.base_url,
        endpoint=args.endpoint,
        top_k=args.top_k,
        expected_rerank=expected_rerank,
        samples=request_latencies,
        completed=True,
    )
    print(f"run_id={run_id} queries={len(query_rows)} result_rows={len(result_rows)} errors={error_count} -> {output_csv}")
    return 0


def _percentile(values: list[float], probability: float) -> float | None:
    """Return the R-7 linearly interpolated percentile used by the other evals."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _write_latency_report(
    output_path: Path | None,
    *,
    run_id: str,
    health: dict,
    base_url: str,
    endpoint: str,
    top_k: int,
    expected_rerank: bool | None,
    samples: list[dict],
    completed: bool,
) -> None:
    if output_path is None:
        return
    successful_values = [float(row["latency_ms"]) for row in samples if row.get("success")]
    summary = {
        "mean": statistics.fmean(successful_values) if successful_values else None,
        "p50": _percentile(successful_values, 0.50),
        "p95": _percentile(successful_values, 0.95),
        "p99": _percentile(successful_values, 0.99),
        "min": min(successful_values, default=None),
        "max": max(successful_values, default=None),
    }
    report = {
        "run_id": run_id,
        "captured_at": datetime.now().astimezone().isoformat(),
        "completed": completed,
        "service_instance_id": health.get("instance_id"),
        "service_started_at": health.get("started_at"),
        "base_url": base_url,
        "endpoint": endpoint,
        "top_k": top_k,
        "execution": "sequential",
        "latency_boundary": "client end-to-end POST /search/text, including response body read and JSON decode",
        "percentile_method": "R-7 linear interpolation over successful requests",
        "rerank_expected": expected_rerank,
        "rerank_observed": (health.get("effective_features") or {}).get("reranker_enabled"),
        "request_count": len(samples),
        "successful_request_count": len(successful_values),
        "failed_request_count": len(samples) - len(successful_values),
        "total_latency_ms": {key: round(value, 3) if value is not None else None for key, value in summary.items()},
        "requests": samples,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(output_path)


def _get_json(url: str, timeout: int) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": exc.read().decode("utf-8", errors="replace")}
    except Exception as exc:
        return 0, {"error": f"{type(exc).__name__}: {exc}"}


def _config_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else SCRIPT_DIR.parent / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run text search queries against the service and save normalized results.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR.parent / "configs" / "text_search.yaml")
    parser.add_argument("--query-set-csv", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--latency-output-json", type=Path, default=None)
    parser.add_argument("--base-url", type=str, default="http://localhost:8000")
    parser.add_argument("--endpoint", type=str, default="/search/text")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--health-url", type=str, default=None)
    parser.add_argument("--health-check-every", type=int, default=10)
    parser.add_argument(
        "--query-type",
        choices=("all", "positive", "negative"),
        default="all",
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="Replace only selected query IDs while preserving other rows in the output CSV",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
