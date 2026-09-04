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
import unicodedata
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
IMAGE_PATTERN = re.compile(r"\(\d+,(\d+),'((?:''|[^'])*)','((?:''|[^'])*)',(\d+),")
SERVICE_CONFIG_KEYS = (
    "EMBEDDING_PROVIDER",
    "COHERE_EMBEDDING_MODEL_NAME",
    "BEDROCK_EMBEDDING_MODEL_ID",
    "BEDROCK_MODEL_ID",
    "QDRANT_TEXT_COLLECTION",
    "QDRANT_IMAGE_COLLECTION",
    "EMBEDDING_OUTPUT_DIMENSIONALITY",
    "HYBRID_CANDIDATE_POOL_SIZE",
    "HYBRID_IMAGE_WEIGHT",
    "HYBRID_TEXT_WEIGHT",
    "HYBRID_FILTER_WEIGHT",
    "HYBRID_BUSINESS_WEIGHT",
    "HYBRID_INFERRED_FILTERS_SOFT_ENABLED",
    "HYBRID_FILTER_RECOVERY_ENABLED",
    "HYBRID_LEXICAL_FUSION_ENABLED",
    "HYBRID_PARALLEL_BRANCHES_ENABLED",
    "RERANK_ENABLED",
    "RERANKER_MODEL_NAME",
    "RERANKER_LOCATION",
    "RERANKER_CONFIG_ID",
    "RERANK_TOP_K",
)
ADVANCED_TEST_TYPES = (
    "exact_title_aligned_image",
    "accentless_title_aligned_image",
    "conversational_title_aligned_image",
    "reordered_keywords_aligned_image",
    "minor_typo_aligned_image",
)


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    accentless = "".join(char for char in decomposed if not unicodedata.combining(char)).replace(
        "đ", "d"
    )
    return " ".join(re.findall(r"[0-9a-z]+", accentless))


def _without_trailing_gender(value: str) -> str:
    return re.sub(r"\s+(?:nam|nữ)\s*$", "", value, flags=re.IGNORECASE).strip()


def _reordered_keywords(value: str) -> str:
    tokens = value.split()
    if len(tokens) < 2:
        return value
    if len(tokens) < 4:
        return " ".join(reversed(tokens))
    pivot = 2 if tokens[0].casefold() == "áo" else 1
    return " ".join(tokens[pivot:] + tokens[:pivot])


def _with_minor_typo(value: str) -> str:
    tokens = value.split()
    candidates = [
        (len(re.sub(r"\W", "", token, flags=re.UNICODE)), index)
        for index, token in enumerate(tokens)
        if len(re.sub(r"\W", "", token, flags=re.UNICODE)) >= 3
    ]
    if not candidates:
        return value
    _, index = max(candidates)
    token = tokens[index]
    middle = max(1, len(token) // 2)
    tokens[index] = token[:middle] + token[middle + 1 :]
    return " ".join(tokens)


def build_query(test_type: str, title: str) -> str:
    if test_type == "exact_title_aligned_image":
        return title
    if test_type == "accentless_title_aligned_image":
        return normalize_text(title)
    if test_type == "conversational_title_aligned_image":
        return f"mình muốn tìm {_without_trailing_gender(title)} giống ảnh này để mặc hằng ngày"
    if test_type == "reordered_keywords_aligned_image":
        return _reordered_keywords(_without_trailing_gender(title))
    if test_type == "minor_typo_aligned_image":
        return _with_minor_typo(_without_trailing_gender(title))
    raise ValueError(f"Unsupported hybrid test type: {test_type}")


def extract_cases(sql_path: Path, expected_count: int = 100) -> list[dict[str, str]]:
    """Build a deterministic hybrid robustness case for every pilot product."""
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

    type_priority = {"MAIN": 0, "FLAT_1": 1, "MODEL_1": 2}
    selected_images = {
        product_id: min(
            images,
            key=lambda image: (
                type_priority.get(image["image_type"].upper(), 3),
                int(image["sort_order"]),
            ),
        )
        for product_id, images in images_by_product.items()
    }

    missing_names = sorted(set(selected_images) - set(names), key=int)
    missing_images = sorted(set(names) - set(selected_images), key=int)
    if missing_names:
        raise RuntimeError(f"Images reference products without search_name_vi: {missing_names[:10]}")
    if missing_images:
        raise RuntimeError(f"Products have no catalog image: {missing_images[:10]}")
    if len(names) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} products with images, "
            f"found names={len(names)} selected_images={len(selected_images)}"
        )

    cases: list[dict[str, str]] = []
    for index, product_id in enumerate(sorted(names, key=int), 1):
        title = names[product_id]
        test_type = ADVANCED_TEST_TYPES[(index - 1) % len(ADVANCED_TEST_TYPES)]
        cases.append(
            {
                "case_id": f"hybrid-{index:03d}",
                "query_text": build_query(test_type, title),
                "source_product_name_vi": title,
                "expected_product_id": product_id,
                "expected_product_name_vi": title,
                "image_url": selected_images[product_id]["image_url"],
                "image_type": selected_images[product_id]["image_type"],
                "test_type": test_type,
            }
        )
    return cases


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def service_config_snapshot(env_path: Path) -> dict[str, str]:
    """Read only non-secret, evaluation-relevant settings from the service env file."""

    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in SERVICE_CONFIG_KEYS:
            values[key] = value.strip().strip('"').strip("'")
    return values


def _decode_json(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) else {"value": value}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw": raw.decode("utf-8", errors="replace")}


def health_snapshot(url: str, timeout: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {"status_code": response.status, "body": _decode_json(response.read())}
    except urllib.error.HTTPError as exc:
        return {"status_code": exc.code, "body": _decode_json(exc.read())}
    except Exception as exc:
        return {"status_code": 0, "body": {"error": f"{type(exc).__name__}: {exc}"}}


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
        headers={"User-Agent": "hybrid-search-100-products-eval/1.0"},
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


def post_hybrid_search(
    url: str,
    query_text: str | None,
    image_bytes: bytes | None,
    content_type: str | None,
    filename: str | None,
    top_k: int,
    timeout: int,
) -> tuple[int, dict[str, Any], float]:
    request_body: dict[str, Any] = {
        "query": query_text,
        "top_k": top_k,
        "strategy": "weighted",
    }
    if image_bytes is not None and content_type is not None:
        request_body["image"] = {
                "content_type": content_type,
                "data_base64": base64.b64encode(image_bytes).decode("ascii"),
                "filename": filename,
        }
    payload = json.dumps(
        request_body,
        ensure_ascii=False,
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
    image_bytes: int = 0,
    error: str = "",
) -> dict[str, Any]:
    raw_results = body.get("results")
    results = raw_results if isinstance(raw_results, list) else []
    returned_ids = [
        str(item.get("product_id", ""))
        for item in results
        if isinstance(item, dict) and item.get("product_id") is not None
    ]
    expected_id = case["expected_product_id"]
    expected_rank = returned_ids.index(expected_id) + 1 if expected_id in returned_ids else None
    sources = [str(item.get("source", "")) for item in results if isinstance(item, dict)]
    detections = body.get("detections") if isinstance(body.get("detections"), list) else []
    response_filters = body.get("filters") if isinstance(body.get("filters"), dict) else {}
    return {
        **case,
        "status_code": status_code,
        "download_latency_ms": round(download_latency_ms, 3),
        "search_latency_ms": round(search_latency_ms, 3),
        "total_latency_ms": round(download_latency_ms + search_latency_ms, 3),
        "cache_hit": cache_hit,
        "image_bytes": image_bytes,
        "returned_product_ids": returned_ids,
        "expected_rank": expected_rank,
        "has_duplicate_product_ids": len(returned_ids) != len(set(returned_ids)),
        "sources": sources,
        "scores": [item.get("score") for item in results if isinstance(item, dict)],
        "detection_count": len(detections),
        "response_filters": response_filters,
        "fallback_detection_count": sum(
            bool(item.get("is_fallback")) for item in detections if isinstance(item, dict)
        ),
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
            case, cache_dir, download_timeout, force_download
        )
        filename = Path(urllib.parse.urlparse(case["image_url"]).path).name
        filename = filename or f"{case['expected_product_id']}.jpg"
        status_code, body, search_latency_ms = post_hybrid_search(
            url,
            case["query_text"],
            raw,
            content_type,
            filename,
            top_k,
            timeout,
        )
        return score_response(
            case,
            status_code,
            body,
            download_latency_ms,
            search_latency_ms,
            cache_hit,
            len(raw),
        )
    except Exception as exc:
        return score_response(
            case,
            0,
            {},
            download_latency_ms,
            0.0,
            cache_hit,
            error=f"{type(exc).__name__}: {exc}",
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
    readiness = (run_context or {}).get("readiness", {})
    readiness_body = readiness.get("body", {}) if isinstance(readiness, dict) else {}
    capabilities = readiness_body.get("capabilities", {}) if isinstance(readiness_body, dict) else {}
    required_capabilities = ("text_search", "image_search", "assistant_llm")
    hybrid_capability_ready = all(capabilities.get(name) is True for name in required_capabilities)
    source_counts = Counter(source for row in results for source in row.get("sources", []))
    result_count_distribution = Counter(str(len(row.get("returned_product_ids", []))) for row in results)
    rank_distribution = Counter(
        str(row["expected_rank"]) if row.get("expected_rank") is not None else "miss"
        for row in results
    )
    summary: dict[str, Any] = {
        "run_context": run_context or {},
        "test_scope": (
            "100-product deterministic aligned-modality robustness suite: exact, accentless, "
            "conversational, reordered-keyword, and minor-typo text with the preferred catalog image"
        ),
        "query_count": count,
        "test_type_counts": dict(
            Counter(str(row.get("test_type", "unknown")) for row in results)
        ),
        "http_success_count": len(successful),
        "http_error_count": count - len(successful),
        "status_counts": dict(Counter(str(row["status_code"]) for row in results)),
        "hybrid_capability_ready": hybrid_capability_ready,
        "hit_rate_at_1": sum(rank <= 1 for rank in ranks) / count if count else 0.0,
        "hit_rate_at_3": sum(rank <= 3 for rank in ranks) / count if count else 0.0,
        f"hit_rate_at_{top_k}": sum(rank <= top_k for rank in ranks) / count if count else 0.0,
        "mean_reciprocal_rank": sum(1 / rank for rank in ranks) / count if count else 0.0,
        "miss_count": sum(row.get("expected_rank") is None for row in results),
        "empty_result_query_count": sum(not row.get("returned_product_ids") for row in results),
        "duplicate_result_query_count": sum(bool(row.get("has_duplicate_product_ids")) for row in results),
        "non_hybrid_source_query_count": sum(
            any(source != "hybrid" for source in row.get("sources", [])) for row in results
        ),
        "source_counts": dict(source_counts),
        "mean_search_latency_ms": statistics.fmean(search_latencies) if search_latencies else 0.0,
        "p50_search_latency_ms": percentile(search_latencies, 0.50),
        "p95_search_latency_ms": percentile(search_latencies, 0.95),
        "max_search_latency_ms": max(search_latencies, default=0.0),
        "cache_hit_count": sum(bool(row.get("cache_hit")) for row in results),
        "query_image_type_counts": dict(Counter(str(row.get("image_type", "unknown")) for row in results)),
        "result_count_distribution": dict(result_count_distribution),
        "expected_rank_distribution": dict(rank_distribution),
        "breakdowns": {
            "test_type": _breakdown(
                results, lambda row: str(row.get("test_type", "unknown")), top_k
            ),
            "image_type": _breakdown(results, lambda row: str(row.get("image_type", "unknown")), top_k),
            "category": _filter_breakdown(results, "category", top_k),
            "material": _filter_breakdown(results, "material", top_k),
            "brand": _filter_breakdown(results, "brand", top_k),
        },
    }
    test_type_breakdown = summary["breakdowns"]["test_type"]
    summary["acceptance_gates"] = {
        "complete_100_cases": count == 100,
        "all_advanced_test_types_have_20_cases": (
            set(test_type_breakdown) == set(ADVANCED_TEST_TYPES)
            and all(group["query_count"] == 20 for group in test_type_breakdown.values())
        ),
        "hybrid_capability_ready": hybrid_capability_ready,
        "http_success_100_percent": len(successful) == count and count > 0,
        "hit_at_1_at_least_95_percent": summary["hit_rate_at_1"] >= 0.95,
        f"hit_at_{top_k}_at_least_99_percent": summary[f"hit_rate_at_{top_k}"] >= 0.99,
        f"each_test_type_hit_at_{top_k}_at_least_95_percent": (
            set(test_type_breakdown) == set(ADVANCED_TEST_TYPES)
            and all(
                group[f"hit_rate_at_{top_k}"] >= 0.95
                for group in test_type_breakdown.values()
            )
        ),
        "all_results_are_hybrid": summary["non_hybrid_source_query_count"] == 0,
        "no_empty_results": summary["empty_result_query_count"] == 0,
        "no_duplicate_product_ids": summary["duplicate_result_query_count"] == 0,
        "p95_search_latency_at_most_5_seconds": summary["p95_search_latency_ms"] <= 5_000,
    }
    summary["acceptance_passed"] = all(summary["acceptance_gates"].values())
    return summary


def _breakdown(
    results: list[dict[str, Any]],
    key: Any,
    top_k: int,
) -> dict[str, dict[str, float | int]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        groups.setdefault(key(row), []).append(row)
    return {
        name: {
            "query_count": len(rows),
            "hit_rate_at_1": sum((row.get("expected_rank") or top_k + 1) <= 1 for row in rows) / len(rows),
            f"hit_rate_at_{top_k}": sum(
                (row.get("expected_rank") or top_k + 1) <= top_k for row in rows
            )
            / len(rows),
            "empty_result_query_count": sum(not row.get("returned_product_ids") for row in rows),
        }
        for name, rows in sorted(groups.items())
    }


def _filter_breakdown(
    results: list[dict[str, Any]],
    field: str,
    top_k: int,
) -> dict[str, dict[str, float | int]]:
    return _breakdown(
        results,
        lambda row: str((row.get("response_filters") or {}).get(field) or "<none>"),
        top_k,
    )


def assessment(summary: dict[str, Any], top_k: int, endpoint: str) -> str:
    lines = [
        "# Đánh giá hybrid search trên bộ 100 sản phẩm",
        "",
        f"- Endpoint: `{endpoint}`",
        f"- Phạm vi: {summary['query_count']} query robustness có text và ảnh catalog cùng sản phẩm.",
        f"- Hybrid readiness: {'ready' if summary['hybrid_capability_ready'] else 'not ready'}.",
        f"- HTTP thành công: {summary['http_success_count']}/{summary['query_count']}.",
        "",
        "## Kết quả",
        "",
        f"- Hit@1: {summary['hit_rate_at_1']:.1%}",
        f"- Hit@3: {summary['hit_rate_at_3']:.1%}",
        f"- Hit@{top_k}: {summary[f'hit_rate_at_{top_k}']:.1%}",
        f"- MRR: {summary['mean_reciprocal_rank']:.4f}",
        f"- Miss/empty/duplicate: {summary['miss_count']}/{summary['empty_result_query_count']}/{summary['duplicate_result_query_count']}",
        f"- Query có source khác hybrid: {summary['non_hybrid_source_query_count']}",
        (
            f"- Search latency p50/p95/max: {summary['p50_search_latency_ms']:.0f}/"
            f"{summary['p95_search_latency_ms']:.0f}/{summary['max_search_latency_ms']:.0f} ms"
        ),
        "",
        "## Kết quả theo loại query",
        "",
    ]
    for test_type, metrics in summary["breakdowns"]["test_type"].items():
        lines.append(
            f"- `{test_type}` ({metrics['query_count']}): "
            f"Hit@1 {metrics['hit_rate_at_1']:.1%}, "
            f"Hit@{top_k} {metrics[f'hit_rate_at_{top_k}']:.1%}, "
            f"empty {metrics['empty_result_query_count']}"
        )
    lines.extend(
        [
            "",
            f"## Acceptance gate: {'PASS' if summary['acceptance_passed'] else 'FAIL'}",
            "",
        ]
    )
    for gate, passed in summary["acceptance_gates"].items():
        lines.append(f"- [{'x' if passed else ' '}] `{gate}`")
    lines.extend(
        [
            "",
            "## Giới hạn",
            "",
            "Ảnh vẫn là ảnh catalog của đúng sản phẩm nên đây là robustness test có kiểm soát, "
            "chưa phải benchmark multimodal ngoài catalog. Bộ test đã đo accentless, hội thoại, "
            "đảo từ khóa và typo, nhưng chưa gán ground truth cho text–ảnh mâu thuẫn hoặc ảnh chụp thực tế.",
            "",
        ]
    )
    return "\n".join(lines)


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
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (reports_dir / "assessment.md").write_text(
        assessment(summary, top_k, endpoint), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate hybrid text + image search on 100 products")
    parser.add_argument("--sql", type=Path, default=ROOT / "database" / "100.sql")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--endpoint", default="/search/hybrid")
    parser.add_argument("--health-url", default="http://localhost:8000/health/ready")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--download-timeout", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--case-limit",
        type=int,
        default=None,
        help="Run only the first N manifest cases for diagnostics; acceptance still requires all 100.",
    )
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--service-env", type=Path, default=ROOT / "service-ai" / ".env")
    args = parser.parse_args()
    if args.top_k <= 0 or args.concurrency <= 0 or (args.case_limit is not None and args.case_limit <= 0):
        parser.error("--top-k, --concurrency and --case-limit must be positive")

    cases = extract_cases(args.sql)
    write_csv(
        EVAL_DIR / "data" / "test_cases.csv",
        cases,
        [
            "case_id",
            "query_text",
            "expected_product_id",
            "expected_product_name_vi",
            "source_product_name_vi",
            "image_url",
            "image_type",
            "test_type",
        ],
    )
    if args.prepare_only:
        print(f"Prepared {len(cases)} hybrid-search cases")
        return 0
    if args.case_limit is not None:
        cases = cases[: args.case_limit]

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
        return 0 if summary["acceptance_passed"] else 1

    run_context = {
        "run_id": args.run_id or f"hybrid-search-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
        "started_at": datetime.now(UTC).isoformat(),
        "endpoint": endpoint,
        "health_url": args.health_url,
        "readiness": health_snapshot(args.health_url, min(args.timeout, 10)),
        "search_config": {
            "top_k": args.top_k,
            "timeout_seconds": args.timeout,
            "download_timeout_seconds": args.download_timeout,
            "concurrency": args.concurrency,
            "case_limit": args.case_limit,
            "strategy": "weighted",
            "query_text": (
                "deterministic rotation: exact, accentless, conversational, "
                "reordered-keyword, minor-typo"
            ),
            "query_image_selection": "MAIN, then FLAT_1/MODEL_1 fallback",
        },
        "service_config": service_config_snapshot(args.service_env),
        "metadata_contract": {
            "metadata_schema_version": 4,
            "required_parity_fields": [
                "category_keys",
                "source_category_keys",
                "brand_key",
                "color_keys",
                "material_keys",
                "size_keys",
                "audience_keys",
                "active",
                "available",
                "selling_price",
                "metadata_schema_version",
                "canonicalizer_version",
            ],
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
        for completed, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            print(
                f"[{completed:03d}/{len(cases)}] {result['case_id']} "
                f"status={result['status_code']} rank={result.get('expected_rank') or 'miss'} "
                f"search_ms={result['search_latency_ms']:.0f}",
                flush=True,
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
                    "query_text": row["query_text"],
                    "expected_product_id": row["expected_product_id"],
                    "rank": rank,
                    "product_id": product_id,
                    "score": row["scores"][rank - 1] if rank <= len(row["scores"]) else "",
                    "source": row["sources"][rank - 1] if rank <= len(row["sources"]) else "",
                }
            )
    write_csv(
        EVAL_DIR / "data" / "ranked_results.csv",
        ranked_rows,
        ["case_id", "query_text", "expected_product_id", "rank", "product_id", "score", "source"],
    )
    run_context["completed_at"] = datetime.now(UTC).isoformat()
    context_path.write_text(json.dumps(run_context, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = write_reports(results, args.top_k, run_context, endpoint)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
