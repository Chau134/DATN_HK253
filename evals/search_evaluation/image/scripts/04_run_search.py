from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    call_image_search_with_payload,
    image_payload_from_url,
    json_response_from_image_search,
    load_json_config,
    read_csv_rows,
    write_csv_rows,
)

RESULT_FIELDNAMES = [
    "run_id",
    "query_id",
    "mode",
    "rank",
    "product_id",
    "score",
    "latency_ms",
    "end_to_end_latency_ms",
    "request_status",
    "error_phase",
    "raw_score_json",
]


def main() -> int:
    args = parse_args()
    config = load_json_config(args.config) if args.config and args.config.exists() else {}
    paths = config.get("paths", {})
    config_root = args.config.parent.parent if args.config else SCRIPT_DIR.parent
    query_set_csv = args.query_set_csv or _config_path(paths.get("query_set_csv"), config_root)
    output_csv = args.output_csv or _config_path(paths.get("search_results_csv"), config_root) or (SCRIPT_DIR.parent / "data" / "search_results_image.csv")
    run_id = args.run_id or f"image-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    query_rows = read_csv_rows(query_set_csv)
    result_rows: list[dict] = []
    error_count = 0
    for query_row in query_rows:
        query_id = query_row.get("query_id", "")
        image_url = query_row.get("image_url", "")
        if not image_url:
            continue
        total_started = time.perf_counter()
        request_started: float | None = None
        try:
            image_payload = image_payload_from_url(image_url, args.timeout)
            request_started = time.perf_counter()
            raw_response = call_image_search_with_payload(
                args.base_url, args.endpoint, image_payload, args.top_k, args.timeout
            )
        except RuntimeError as exc:
            finished = time.perf_counter()
            error_count += 1
            result_rows.append(
                {
                    "run_id": run_id,
                    "query_id": query_id,
                    "mode": "image",
                    "rank": 0,
                    "product_id": "",
                    "score": "",
                    "latency_ms": round((finished - request_started) * 1000, 3) if request_started is not None else "",
                    "end_to_end_latency_ms": round((finished - total_started) * 1000, 3),
                    "request_status": "error",
                    "error_phase": "service_request" if request_started is not None else "fixture_download",
                    "raw_score_json": json.dumps({"error": str(exc), "image_url": image_url}, ensure_ascii=False, separators=(",", ":")),
                }
            )
            continue
        finished = time.perf_counter()
        latency_ms = round((finished - request_started) * 1000, 3)
        end_to_end_latency_ms = round((finished - total_started) * 1000, 3)
        normalized = json_response_from_image_search(raw_response, query_id=query_id, run_id=run_id, top_k=args.top_k)
        if not normalized:
            normalized = [
                {
                    "run_id": run_id,
                    "query_id": query_id,
                    "mode": "image",
                    "rank": 0,
                    "product_id": "",
                    "score": "",
                    "raw_score_json": json.dumps(raw_response, ensure_ascii=False, separators=(",", ":")),
                }
            ]
        for row in normalized:
            row.update(
                {
                    "latency_ms": latency_ms,
                    "end_to_end_latency_ms": end_to_end_latency_ms,
                    "request_status": "success",
                    "error_phase": "",
                }
            )
        result_rows.extend(normalized)

    write_csv_rows(output_csv, result_rows, RESULT_FIELDNAMES)
    print(f"run_id={run_id} queries={len(query_rows)} result_rows={len(result_rows)} errors={error_count} -> {output_csv}")
    return 0


def _config_path(value: str | None, config_root: Path) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else config_root / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run image search queries against service-ai and save normalized results.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR.parent / "configs" / "image_search.yaml")
    parser.add_argument("--query-set-csv", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--base-url", type=str, default="http://localhost:8000")
    parser.add_argument("--endpoint", type=str, default="/search/image")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--run-id", type=str, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
