from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic


SCRIPT_DIR = Path(__file__).resolve().parent
RESULT_FIELDS = [
    "run_id", "query_id", "mode", "rank", "product_id", "score",
    "raw_score_json",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def image_payload(image_url: str, timeout: int) -> tuple[dict[str, str], float]:
    started = monotonic()
    request = urllib.request.Request(
        image_url, headers={"User-Agent": "hybrid-search-eval/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        content_type = (
            response.headers.get_content_type()
            or mimetypes.guess_type(image_url)[0]
            or "image/jpeg"
        )
    if not data:
        raise RuntimeError("image download returned no bytes")
    return {
        "content_type": content_type,
        "data_base64": base64.b64encode(data).decode("ascii"),
        "filename": Path(image_url.split("?", 1)[0]).name or "query-image.jpg",
    }, (monotonic() - started) * 1000


def call_search(
    endpoint: str,
    *,
    query: str | None,
    image: dict[str, str] | None,
    top_k: int,
    timeout: int,
) -> tuple[int, dict, float]:
    body = {"top_k": top_k}
    if query is not None:
        body["query"] = query
    if image is not None:
        body["image"] = image
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    started = monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return (
                response.status,
                json.loads(response.read().decode("utf-8")),
                (monotonic() - started) * 1000,
            )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def main() -> int:
    args = parse_args()
    queries = read_csv(args.queries_csv)
    if len(queries) != 100:
        raise RuntimeError(f"Expected 100 queries, got {len(queries)}")
    run_id = args.run_id or f"hybrid-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    endpoints = {
        "image-only": "/search/image",
        "text-only": "/search/text",
        "fusion": "/search/hybrid",
    }
    endpoint = args.base_url.rstrip("/") + "/" + (args.endpoint or endpoints[args.variant]).lstrip("/")
    ready_url = args.base_url.rstrip("/") + "/health/ready"
    with urllib.request.urlopen(ready_url, timeout=args.timeout) as ready_response:
        readiness = json.loads(ready_response.read().decode("utf-8"))
    effective_rerank = bool((readiness.get("effective_features") or {}).get("reranker_enabled"))
    if args.expect_rerank != "any" and effective_rerank != (args.expect_rerank == "enabled"):
        raise RuntimeError(
            f"Expected reranker {args.expect_rerank}, but /health/ready reports "
            f"reranker_enabled={effective_rerank}"
        )
    result_rows: list[dict] = []
    response_rows: list[dict] = []
    errors = 0
    for index, row in enumerate(queries, 1):
        query_id = row["query_id"]
        started = monotonic()
        try:
            image, download_ms = (None, 0.0)
            if args.variant != "text-only":
                image, download_ms = image_payload(row["image_url"], args.download_timeout)
            status, response, search_ms = call_search(
                endpoint,
                query=row["query_text"] if args.variant != "image-only" else None,
                image=image,
                top_k=args.top_k,
                timeout=args.timeout,
            )
            results = response.get("results") or []
            for rank, item in enumerate(results[: args.top_k], 1):
                result_rows.append({
                    "run_id": run_id, "query_id": query_id, "mode": args.variant,
                    "rank": rank, "product_id": str(item.get("product_id", "")),
                    "score": item.get("score", ""),
                    "raw_score_json": json.dumps(item, ensure_ascii=False, separators=(",", ":")),
                })
            error = ""
        except Exception as exc:
            errors += 1
            status, response, search_ms, download_ms = 0, {}, 0.0, 0.0
            error = f"{type(exc).__name__}: {exc}"
            result_rows.append({
                "run_id": run_id, "query_id": query_id, "mode": args.variant,
                "rank": 0, "product_id": "", "score": "",
                "raw_score_json": json.dumps({"error": error}, ensure_ascii=False),
            })
        response_rows.append({
            "run_id": run_id, "query_id": query_id,
            "variant": args.variant, "endpoint": endpoint,
            "reranker_enabled": effective_rerank,
            "transformation_type": row["transformation_type"],
            "difficulty": row["difficulty"], "query_text": row["query_text"],
            "image_url": row["image_url"], "target_product_id": row["target_product_id"],
            "status_code": status, "download_latency_ms": round(download_ms, 3),
            "search_latency_ms": round(search_ms, 3),
            "total_latency_ms": round((monotonic() - started) * 1000, 3),
            "error": error, "response": response,
        })
        print(
            f"[{index:03d}/{len(queries)}] {query_id} status={status} "
            f"results={len(response.get('results') or [])} search_ms={search_ms:.0f}",
            flush=True,
        )

    write_csv(args.results_csv, result_rows, RESULT_FIELDS)
    args.responses_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.responses_jsonl.open("w", encoding="utf-8") as handle:
        for row in response_rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(
        f"run_id={run_id} queries={len(queries)} result_rows={len(result_rows)} "
        f"errors={errors} results={args.results_csv} responses={args.responses_jsonl}"
    )
    return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "multimodal_queries.csv")
    parser.add_argument("--results-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "search_results_multimodal.csv")
    parser.add_argument("--responses-jsonl", type=Path, default=SCRIPT_DIR.parent / "reports" / "hybrid_eval_responses.jsonl")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--variant", choices=("image-only", "text-only", "fusion"), default="fusion")
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--expect-rerank", choices=("enabled", "disabled", "any"), default="any")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--download-timeout", type=int, default=30)
    parser.add_argument("--run-id")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
