from __future__ import annotations

import argparse
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import UTC, datetime
import json
import mimetypes
from pathlib import Path
import re
import statistics
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
PRODUCT_PATTERN = re.compile(
    r"\(\d+,(\d+),'search_name_vi',NULL,'[^']*','[^']*','((?:''|[^'])*)'\)"
)
IMAGE_INSERT_PATTERN = re.compile(r"INSERT INTO `product_images` VALUES\s+(.*?);", re.DOTALL)
IMAGE_PATTERN = re.compile(
    r"\(\d+,(\d+),'((?:''|[^'])*)','((?:''|[^'])*)',(\d+),"
)


def extract_cases(sql_path: Path, expected_count: int = 100) -> list[dict[str, str]]:
    sql = sql_path.read_text(encoding="utf-8")
    names = {
        match.group(1): match.group(2).replace("''", "'")
        for match in PRODUCT_PATTERN.finditer(sql)
    }
    image_insert = IMAGE_INSERT_PATTERN.search(sql)
    if image_insert is None:
        raise RuntimeError(f"Could not find product_images data in {sql_path}")

    images_by_product: dict[str, list[dict[str, str]]] = {}
    for match in IMAGE_PATTERN.finditer(image_insert.group(1)):
        product_id, image_type, image_url, sort_order = match.groups()
        images_by_product.setdefault(product_id, []).append(
            {
                "image_url": image_url.replace("''", "'"),
                "image_type": image_type,
                "sort_order": sort_order,
            }
        )

    selected_images: dict[str, dict[str, str]] = {}
    type_priority = {"MAIN": 0, "FLAT_1": 1, "MODEL_1": 2}
    for product_id, images in images_by_product.items():
        selected_images[product_id] = min(
            images,
            key=lambda image: (
                type_priority.get(image["image_type"].upper(), 3),
                int(image["sort_order"]),
            ),
        )

    missing_names = sorted(set(selected_images) - set(names), key=int)
    if missing_names:
        raise RuntimeError(f"Images reference products without search_name_vi: {missing_names[:10]}")
    missing_images = sorted(set(names) - set(selected_images), key=int)
    if missing_images:
        raise RuntimeError(f"Products have no catalog image: {missing_images[:10]}")
    if len(names) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} products with images, "
            f"found names={len(names)} selected_images={len(selected_images)}"
        )

    return [
        {
            "case_id": f"main-{index:03d}",
            "expected_product_id": product_id,
            "expected_product_name_vi": names[product_id],
            "image_url": selected_images[product_id]["image_url"],
            "image_type": selected_images[product_id]["image_type"],
            "test_type": "catalog_preferred_image_identity",
        }
        for index, product_id in enumerate(sorted(names, key=int), 1)
    ]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def health_snapshot(url: str, timeout: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {
                "status_code": response.status,
                "body": _decode_json(response.read()),
            }
    except urllib.error.HTTPError as exc:
        return {"status_code": exc.code, "body": _decode_json(exc.read())}
    except Exception as exc:
        return {
            "status_code": 0,
            "body": {"error": f"{type(exc).__name__}: {exc}"},
        }


def _decode_json(raw: bytes) -> dict[str, Any]:
    try:
        body = json.loads(raw.decode("utf-8"))
        return body if isinstance(body, dict) else {"value": body}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw": raw.decode("utf-8", errors="replace")}


def _image_content_type(image_url: str, response_content_type: str | None = None) -> str:
    if response_content_type:
        content_type = response_content_type.split(";", 1)[0].strip().lower()
        if content_type.startswith("image/"):
            return content_type
    guessed = mimetypes.guess_type(urllib.parse.urlparse(image_url).path)[0]
    return guessed if guessed and guessed.startswith("image/") else "image/jpeg"


def load_image(
    case: dict[str, str],
    cache_dir: Path,
    timeout: int,
    force_download: bool = False,
) -> tuple[bytes, str, float, bool]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{case['expected_product_id']}.image"
    content_type_path = cache_dir / f"{case['expected_product_id']}.content-type"
    if cache_path.exists() and cache_path.stat().st_size > 0 and not force_download:
        content_type = (
            content_type_path.read_text(encoding="utf-8").strip()
            if content_type_path.exists()
            else _image_content_type(case["image_url"])
        )
        return cache_path.read_bytes(), content_type, 0.0, True

    request = urllib.request.Request(
        case["image_url"],
        headers={"User-Agent": "image-search-100-products-eval/1.0"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        content_type = _image_content_type(case["image_url"], response.headers.get("Content-Type"))
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not raw:
        raise RuntimeError("Downloaded image is empty")
    cache_path.write_bytes(raw)
    content_type_path.write_text(content_type, encoding="utf-8")
    return raw, content_type, elapsed_ms, False


def post_image_search(
    url: str,
    image_bytes: bytes,
    content_type: str,
    filename: str,
    top_k: int,
    timeout: int,
) -> tuple[int, dict[str, Any], float]:
    payload = json.dumps(
        {
            "image": {
                "content_type": content_type,
                "data_base64": base64.b64encode(image_bytes).decode("ascii"),
                "filename": filename,
            },
            "top_k": top_k,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, _decode_json(response.read()), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        return exc.code, _decode_json(exc.read()), (time.perf_counter() - started) * 1000


def score_response(
    case: dict[str, str],
    status_code: int,
    body: dict[str, Any],
    download_latency_ms: float,
    search_latency_ms: float,
    cache_hit: bool,
    error: str = "",
) -> dict[str, Any]:
    raw_results = body.get("results")
    results = raw_results if isinstance(raw_results, list) else []
    returned_ids = [str(item.get("product_id", "")) for item in results if item.get("product_id") is not None]
    expected_id = case["expected_product_id"]
    expected_rank = returned_ids.index(expected_id) + 1 if expected_id in returned_ids else None
    detections = body.get("detections") if isinstance(body.get("detections"), list) else []
    return {
        **case,
        "status_code": status_code,
        "download_latency_ms": round(download_latency_ms, 3),
        "search_latency_ms": round(search_latency_ms, 3),
        "total_latency_ms": round(download_latency_ms + search_latency_ms, 3),
        "cache_hit": cache_hit,
        "image_bytes": 0,
        "returned_product_ids": returned_ids,
        "expected_rank": expected_rank,
        "has_duplicate_product_ids": len(returned_ids) != len(set(returned_ids)),
        "detection_count": len(detections),
        "fallback_detection_count": sum(bool(item.get("is_fallback")) for item in detections if isinstance(item, dict)),
        "scores": [item.get("score") for item in results],
        "error": error,
        "response": body,
    }


def run_case(
    case: dict[str, str],
    url: str,
    cache_dir: Path,
    top_k: int,
    timeout: int,
    download_timeout: int,
    force_download: bool,
) -> dict[str, Any]:
    download_latency_ms = 0.0
    cache_hit = False
    try:
        raw, content_type, download_latency_ms, cache_hit = load_image(
            case,
            cache_dir,
            download_timeout,
            force_download,
        )
        filename = Path(urllib.parse.urlparse(case["image_url"]).path).name or f"{case['expected_product_id']}.jpg"
        status_code, body, search_latency_ms = post_image_search(
            url,
            raw,
            content_type,
            filename,
            top_k,
            timeout,
        )
        result = score_response(
            case,
            status_code,
            body,
            download_latency_ms,
            search_latency_ms,
            cache_hit,
        )
        result["image_bytes"] = len(raw)
        return result
    except Exception as exc:
        return score_response(
            case,
            0,
            {},
            download_latency_ms,
            0.0,
            cache_hit,
            f"{type(exc).__name__}: {exc}",
        )


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def build_summary(
    results: list[dict[str, Any]],
    top_k: int,
    run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    count = len(results)
    successful = [row for row in results if row["status_code"] == 200]
    ranks = [int(row["expected_rank"]) for row in results if row.get("expected_rank") is not None]
    search_latencies = [float(row["search_latency_ms"]) for row in successful]
    total_latencies = [float(row["total_latency_ms"]) for row in results]
    status_counts = Counter(str(row["status_code"]) for row in results)
    readiness = (run_context or {}).get("readiness", {})
    readiness_body = readiness.get("body", {}) if isinstance(readiness, dict) else {}
    capabilities = readiness_body.get("capabilities", {}) if isinstance(readiness_body, dict) else {}
    image_capability_ready = capabilities.get("image_search") is True
    score_lists = [
        [float(score) for score in row.get("scores", []) if isinstance(score, (int, float))]
        for row in results
    ]
    top1_margins = [scores[0] - scores[1] for scores in score_lists if len(scores) >= 2]
    top1_ties = [abs(scores[0] - scores[1]) <= 1e-6 for scores in score_lists if len(scores) >= 2]
    non_top1_tied_with_top1 = 0
    for row, scores in zip(results, score_lists, strict=True):
        rank = row.get("expected_rank")
        if isinstance(rank, int) and rank > 1 and len(scores) >= rank:
            non_top1_tied_with_top1 += abs(scores[0] - scores[rank - 1]) <= 1e-6

    summary: dict[str, Any] = {
        "run_context": run_context or {},
        "test_scope": "one preferred catalog image for each product in database/100.sql (MAIN, then FLAT_1/MODEL_1 fallback)",
        "query_count": count,
        "http_success_count": len(successful),
        "http_error_count": count - len(successful),
        "status_counts": dict(status_counts),
        "image_capability_ready": image_capability_ready,
        "hit_rate_at_1": sum(rank <= 1 for rank in ranks) / count if count else 0.0,
        "hit_rate_at_3": sum(rank <= 3 for rank in ranks) / count if count else 0.0,
        f"hit_rate_at_{top_k}": sum(rank <= top_k for rank in ranks) / count if count else 0.0,
        "mean_reciprocal_rank": sum(1 / rank for rank in ranks) / count if count else 0.0,
        "miss_count": sum(row.get("expected_rank") is None for row in results),
        "empty_result_query_count": sum(not row.get("returned_product_ids") for row in results),
        "duplicate_result_query_count": sum(bool(row.get("has_duplicate_product_ids")) for row in results),
        "download_or_transport_error_count": sum(row.get("status_code") == 0 for row in results),
        "cache_hit_count": sum(bool(row.get("cache_hit")) for row in results),
        "mean_search_latency_ms": statistics.fmean(search_latencies) if search_latencies else 0.0,
        "p50_search_latency_ms": percentile(search_latencies, 0.50),
        "p95_search_latency_ms": percentile(search_latencies, 0.95),
        "max_search_latency_ms": max(search_latencies, default=0.0),
        "p95_total_latency_ms": percentile(total_latencies, 0.95),
        "mean_image_bytes": statistics.fmean([row.get("image_bytes", 0) for row in results]) if results else 0.0,
        "mean_top1_score_margin": statistics.fmean(top1_margins) if top1_margins else 0.0,
        "top1_score_tie_query_count": sum(top1_ties),
        "non_top1_tied_with_top1_count": non_top1_tied_with_top1,
        "query_with_detection_count": sum(int(row.get("detection_count", 0)) > 0 for row in results),
        "query_with_fallback_detection_count": sum(int(row.get("fallback_detection_count", 0)) > 0 for row in results),
        "query_image_type_counts": dict(Counter(str(row.get("image_type", "unknown")) for row in results)),
        "non_main_query_count": sum(str(row.get("image_type", "")).upper() != "MAIN" for row in results),
    }
    summary["acceptance_gates"] = {
        "complete_100_cases": count == 100,
        "image_capability_ready": image_capability_ready,
        "http_success_100_percent": len(successful) == count and count > 0,
        "hit_at_1_at_least_95_percent": summary["hit_rate_at_1"] >= 0.95,
        f"hit_at_{top_k}_at_least_99_percent": summary[f"hit_rate_at_{top_k}"] >= 0.99,
        "no_empty_results": summary["empty_result_query_count"] == 0,
        "no_duplicate_product_ids": summary["duplicate_result_query_count"] == 0,
        "p95_search_latency_at_most_5_seconds": summary["p95_search_latency_ms"] <= 5_000,
    }
    summary["acceptance_passed"] = all(summary["acceptance_gates"].values())
    return summary


def assessment(summary: dict[str, Any], results: list[dict[str, Any]], top_k: int, endpoint: str) -> str:
    misses = [row for row in results if row.get("expected_rank") is None]
    non_top1 = [row for row in results if row.get("expected_rank") not in (None, 1)]
    errors = [row for row in results if row.get("status_code") != 200]
    lines = [
        "# Assessment: image search trên bộ 100 sản phẩm",
        "",
        "## Bối cảnh chạy",
        "",
        f"- Endpoint: `{endpoint}`",
        f"- Phạm vi: {summary['query_count']} ảnh catalog ưu tiên `MAIN`, mỗi sản phẩm một ảnh.",
        f"- Loại ảnh query: `{json.dumps(summary['query_image_type_counts'], ensure_ascii=False)}`.",
        f"- Image-search readiness: {'ready' if summary['image_capability_ready'] else 'not ready'}.",
        f"- HTTP thành công: {summary['http_success_count']}/{summary['query_count']}.",
        "",
        "## Kết quả",
        "",
        f"- Hit@1: {summary['hit_rate_at_1']:.1%}",
        f"- Hit@3: {summary['hit_rate_at_3']:.1%}",
        f"- Hit@{top_k}: {summary[f'hit_rate_at_{top_k}']:.1%}",
        f"- MRR: {summary['mean_reciprocal_rank']:.4f}",
        f"- Miss: {summary['miss_count']}",
        f"- Empty results: {summary['empty_result_query_count']}",
        f"- Query có duplicate ID: {summary['duplicate_result_query_count']}",
        f"- Query có Top-1/Top-2 đồng điểm: {summary['top1_score_tie_query_count']}",
        (
            f"- Search latency p50/p95/max: {summary['p50_search_latency_ms']:.0f}/"
            f"{summary['p95_search_latency_ms']:.0f}/{summary['max_search_latency_ms']:.0f} ms"
        ),
        f"- Query dùng fallback/full-image crop: {summary['query_with_fallback_detection_count']}/{summary['query_count']}",
        "",
        "## Nhận định",
        "",
    ]
    if errors:
        examples = ", ".join(f"{row['case_id']} ({row['status_code']}: {row.get('error') or 'HTTP error'})" for row in errors[:10])
        lines.append(f"1. Có {len(errors)} lỗi tải ảnh, kết nối hoặc HTTP. Ví dụ: {examples}.")
    else:
        lines.append("1. Toàn bộ ảnh được tải và endpoint xử lý thành công; baseline không bị nhiễu bởi lỗi vận hành.")
    if misses:
        examples = ", ".join(f"{row['case_id']}->{row['expected_product_id']}" for row in misses[:10])
        lines.append(f"2. Có {len(misses)} sản phẩm không xuất hiện trong Top {top_k}. Ví dụ: {examples}.")
    else:
        lines.append(f"2. Tất cả source product đều xuất hiện trong Top {top_k}.")
    if non_top1:
        examples = ", ".join(f"{row['case_id']} (rank {row['expected_rank']})" for row in non_top1[:10])
        lines.append(f"3. Có {len(non_top1)} source product không đứng hạng 1. Ví dụ: {examples}.")
        if summary["non_top1_tied_with_top1_count"]:
            lines.append(
                f"   Trong đó {summary['non_top1_tied_with_top1_count']} case có source product đồng điểm với Top 1; "
                "thứ tự hiện tại phụ thuộc tie-break không mang ngữ nghĩa."
            )
    else:
        lines.append("3. Tất cả source product đều đứng hạng 1.")
    lines.extend(
        [
            (
                "4. Đây là identity/ingestion acceptance test: ảnh query chính là ảnh catalog đã dùng để index. "
                "Kết quả cao chứng minh pipeline tải ảnh, embedding, Qdrant và dedupe hoạt động, nhưng chưa chứng minh "
                "khả năng tìm kiếm bằng ảnh chụp thực tế hoặc ảnh ngoài catalog."
            ),
            (
                f"5. Có {summary['non_main_query_count']} sản phẩm thiếu ảnh MAIN nên runner dùng ảnh ưu tiên kế tiếp "
                "(FLAT_1 rồi MODEL_1). Đây là data-quality gap cần được sửa ở catalog ingestion."
            ),
            (
                "6. Gate tiếp theo phải dùng ảnh cross-view và ảnh biến đổi (crop, nén, nền khác, occlusion), "
                "sau đó dùng ground truth relevance theo nhóm sản phẩm tương tự để đo Recall/NDCG thay vì chỉ self-hit."
            ),
            "",
            f"## Acceptance gate: {'PASS' if summary['acceptance_passed'] else 'FAIL'}",
            "",
        ]
    )
    for gate, passed in summary["acceptance_gates"].items():
        lines.append(f"- [{'x' if passed else ' '}] `{gate}`")
    return "\n".join(lines) + "\n"


def write_reports(
    results: list[dict[str, Any]],
    top_k: int,
    run_context: dict[str, Any],
    endpoint: str,
) -> dict[str, Any]:
    reports_dir = EVAL_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(results, top_k, run_context)
    (reports_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "assessment.md").write_text(
        assessment(summary, results, top_k, endpoint),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate image search on the 100-product SQL pilot")
    parser.add_argument("--sql", type=Path, default=ROOT / "database" / "100.sql")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--endpoint", default="/search/image")
    parser.add_argument("--health-url", default="http://localhost:8000/health/ready/image_search")
    parser.add_argument(
        "--collection-name",
        default="product_image_vectors_cohere_embed_v4_1536_100_products",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--download-timeout", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.top_k <= 0 or args.concurrency <= 0:
        parser.error("--top-k and --concurrency must be positive")

    cases = extract_cases(args.sql)
    write_csv(
        EVAL_DIR / "data" / "test_cases.csv",
        cases,
        [
            "case_id",
            "expected_product_id",
            "expected_product_name_vi",
            "image_url",
            "image_type",
            "test_type",
        ],
    )
    if args.prepare_only:
        print(f"Prepared {len(cases)} image-search cases")
        return 0

    endpoint = args.base_url.rstrip("/") + "/" + args.endpoint.lstrip("/")
    results_path = EVAL_DIR / "data" / "results.jsonl"
    context_path = EVAL_DIR / "reports" / "run_context.json"
    if args.report_only:
        results = [
            json.loads(line)
            for line in results_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        run_context = json.loads(context_path.read_text(encoding="utf-8")) if context_path.exists() else {}
        summary = write_reports(results, args.top_k, run_context, endpoint)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    run_context = {
        "run_id": args.run_id or f"image-search-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
        "started_at": datetime.now(UTC).isoformat(),
        "endpoint": endpoint,
        "health_url": args.health_url,
        "readiness": health_snapshot(args.health_url, min(args.timeout, 10)),
        "collection_name": args.collection_name,
        "search_config": {
            "top_k": args.top_k,
            "timeout_seconds": args.timeout,
            "download_timeout_seconds": args.download_timeout,
            "concurrency": args.concurrency,
            "query_image_selection": "MAIN, then FLAT_1/MODEL_1 fallback",
        },
    }
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(run_context, ensure_ascii=False, indent=2), encoding="utf-8")

    cache_dir = EVAL_DIR / "data" / "images"
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(
                run_case,
                case,
                endpoint,
                cache_dir,
                args.top_k,
                args.timeout,
                args.download_timeout,
                args.force_download,
            ): case
            for case in cases
        }
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            rank = result.get("expected_rank") or "miss"
            print(
                f"[{completed:03d}/{len(cases)}] {result['case_id']} "
                f"status={result['status_code']} rank={rank} "
                f"search_ms={result['search_latency_ms']:.0f}"
            )

    results.sort(key=lambda row: row["case_id"])
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in results),
        encoding="utf-8",
    )
    ranked_rows: list[dict[str, Any]] = []
    for row in results:
        for rank, product_id in enumerate(row["returned_product_ids"], 1):
            ranked_rows.append(
                {
                    "case_id": row["case_id"],
                    "expected_product_id": row["expected_product_id"],
                    "rank": rank,
                    "product_id": product_id,
                    "score": row["scores"][rank - 1] if rank <= len(row["scores"]) else "",
                }
            )
    write_csv(
        EVAL_DIR / "data" / "ranked_results.csv",
        ranked_rows,
        ["case_id", "expected_product_id", "rank", "product_id", "score"],
    )
    run_context["completed_at"] = datetime.now(UTC).isoformat()
    context_path.write_text(json.dumps(run_context, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = write_reports(results, args.top_k, run_context, endpoint)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
