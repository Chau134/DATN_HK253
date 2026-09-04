from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import statistics
from typing import Any
from uuid import uuid4

from prepare_ground_truth_review import (
    CASES_PER_GROUP,
    TEST_GROUPS,
    extract_review_products,
)
from run_eval import (
    EVAL_DIR,
    ROOT,
    health_snapshot,
    load_image,
    percentile,
    post_hybrid_search,
    service_config_snapshot,
)


REVIEW_DIR = EVAL_DIR / "review"
CONSTRAINT_FIELDS = ("category", "colors", "material")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def approved_ids(case: dict[str, str]) -> list[str]:
    return list(
        dict.fromkeys(
            value.strip()
            for value in case.get("approved_product_ids", "").split("|")
            if value.strip()
        )
    )


def candidate_ids(case: dict[str, str]) -> list[str]:
    return list(
        dict.fromkeys(
            value.strip()
            for value in case.get("candidate_product_ids", "").split("|")
            if value.strip()
        )
    )


def load_approval_grades(path: Path) -> dict[str, dict[str, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", {})
    if not isinstance(cases, dict):
        return {}
    return {
        str(case_id): {
            str(product_id): int(grade)
            for product_id, grade in raw_case.get("approved_grades", {}).items()
        }
        for case_id, raw_case in cases.items()
        if isinstance(raw_case, dict)
        and isinstance(raw_case.get("approved_grades"), dict)
    }


def ndcg_at_k(
    returned_ids: list[str],
    grades: dict[str, int],
    top_k: int,
) -> float:
    gains = [grades.get(product_id, 0) for product_id in returned_ids[:top_k]]
    dcg = sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(gains, 1)
    )
    ideal = sorted(grades.values(), reverse=True)[:top_k]
    idcg = sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(ideal, 1)
    )
    return dcg / idcg if idcg else 0.0


def validate_runnable_cases(
    cases: list[dict[str, str]],
    valid_product_ids: set[str],
) -> None:
    errors: list[str] = []
    group_counts = Counter(case.get("test_group", "") for case in cases)
    expected_group_counts = Counter(
        {group: CASES_PER_GROUP for group in TEST_GROUPS}
    )
    if group_counts != expected_group_counts:
        errors.append(
            "manifest must contain exactly "
            f"{CASES_PER_GROUP} cases for each group: {dict(expected_group_counts)}; "
            f"found {dict(group_counts)}"
        )
    for case in cases:
        case_id = case.get("case_id", "<missing>")
        expected = approved_ids(case)
        if case.get("review_status") != "APPROVED":
            errors.append(f"{case_id}: review_status must be APPROVED")
        if not case.get("external_image_url", "").startswith(("http://", "https://")):
            errors.append(f"{case_id}: external_image_url is missing")
        if not expected:
            errors.append(f"{case_id}: approved_product_ids is empty")
        invalid = sorted(set(expected) - valid_product_ids, key=int)
        if invalid:
            errors.append(f"{case_id}: approved IDs outside database/100.sql: {invalid}")
    if errors:
        raise RuntimeError("Review manifest is not runnable:\n- " + "\n- ".join(errors))


def _response_results(body: dict[str, Any]) -> list[dict[str, Any]]:
    raw = body.get("results")
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def run_case(
    case: dict[str, str],
    *,
    endpoint: str,
    cache_dir: Path,
    top_k: int,
    timeout: int,
    download_timeout: int,
    force_download: bool,
    valid_product_ids: set[str] | None = None,
    retrieval_mode: str = "constrained-hybrid",
) -> dict[str, Any]:
    image_case = {
        "expected_product_id": case["image_source_product_id"] or case["case_id"],
        "image_url": case["external_image_url"],
    }
    try:
        raw, content_type, download_ms, cache_hit = load_image(
            image_case,
            cache_dir,
            download_timeout,
            force_download,
        )
        status, body, search_ms = post_hybrid_search(
            endpoint,
            case["query_text"] if retrieval_mode != "image-only" else None,
            raw if retrieval_mode != "text-only" else None,
            content_type if retrieval_mode != "text-only" else None,
            (
                f"{case['case_id']}.jpg"
                if retrieval_mode != "text-only"
                else None
            ),
            top_k,
            timeout,
        )
        results = _response_results(body)
        raw_ids = [
            str(item["product_id"])
            for item in results
            if item.get("product_id") is not None
        ]
        returned_ids = list(dict.fromkeys(raw_ids))
        outside_snapshot_ids = (
            [product_id for product_id in returned_ids if product_id not in valid_product_ids]
            if valid_product_ids is not None
            else []
        )
        acceptable = approved_ids(case)
        acceptable_set = set(acceptable)
        rank = next(
            (
                index
                for index, product_id in enumerate(returned_ids, 1)
                if product_id in acceptable_set
            ),
            None,
        )
        metadata_candidates = set(candidate_ids(case))
        metadata_candidate_rank = next(
            (
                index
                for index, product_id in enumerate(returned_ids, 1)
                if product_id in metadata_candidates
            ),
            None,
        )
        explicit_filters = body.get("explicit_filters")
        explicit_filter_fields = [
            field_name
            for field_name in CONSTRAINT_FIELDS
            if isinstance(explicit_filters, dict)
            and explicit_filters.get(field_name) is not None
        ]
        constraint_satisfaction: dict[str, dict[str, bool]] = {}
        for field_name in explicit_filter_fields:
            values = [
                bool(
                    (item.get("explicit_constraint_satisfaction") or {}).get(
                        field_name
                    )
                )
                for item in results[:top_k]
                if isinstance(
                    item.get("explicit_constraint_satisfaction"),
                    dict,
                )
            ]
            constraint_satisfaction[field_name] = {
                "at_1": bool(values and values[0]),
                f"at_{top_k}": bool(
                    values
                    and len(values) == len(results[:top_k])
                    and all(values)
                ),
            }
        raw_grades = case.get("approved_grades", {})
        grades = (
            {
                str(product_id): int(grade)
                for product_id, grade in raw_grades.items()
            }
            if isinstance(raw_grades, dict)
            else {product_id: 1 for product_id in acceptable}
        )
        return {
            **case,
            "retrieval_mode": retrieval_mode,
            "approved_product_ids": acceptable,
            "status_code": status,
            "returned_product_ids_raw": raw_ids,
            "returned_product_ids": returned_ids,
            "outside_snapshot_product_ids": outside_snapshot_ids,
            "acceptable_rank": rank,
            "visually_approved_rank": rank,
            "metadata_candidate_rank": metadata_candidate_rank,
            "metadata_candidate_hit_at_5": (
                metadata_candidate_rank is not None
                and metadata_candidate_rank <= top_k
            ),
            "hit_at_1": rank == 1,
            "hit_at_5": rank is not None and rank <= top_k,
            "ndcg_at_5": ndcg_at_k(returned_ids, grades, top_k),
            "constraint_satisfaction": constraint_satisfaction,
            "relaxed_filters": body.get("relaxed_filters", []),
            "has_duplicate_product_ids": len(raw_ids) != len(set(raw_ids)),
            "sources": [str(item.get("source", "")) for item in results],
            "scores": [item.get("score") for item in results],
            "download_latency_ms": round(download_ms, 3),
            "search_latency_ms": round(search_ms, 3),
            "cache_hit": cache_hit,
            "error": "",
            "response": body,
        }
    except Exception as exc:
        return {
            **case,
            "retrieval_mode": retrieval_mode,
            "approved_product_ids": approved_ids(case),
            "status_code": 0,
            "returned_product_ids_raw": [],
            "returned_product_ids": [],
            "outside_snapshot_product_ids": [],
            "acceptable_rank": None,
            "visually_approved_rank": None,
            "metadata_candidate_rank": None,
            "metadata_candidate_hit_at_5": False,
            "hit_at_1": False,
            "hit_at_5": False,
            "ndcg_at_5": 0.0,
            "constraint_satisfaction": {},
            "relaxed_filters": [],
            "has_duplicate_product_ids": False,
            "sources": [],
            "scores": [],
            "download_latency_ms": 0.0,
            "search_latency_ms": 0.0,
            "cache_hit": False,
            "error": f"{type(exc).__name__}: {exc}",
            "response": {},
        }


def _group_metrics(rows: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    count = len(rows)
    ranks = [
        int(row["acceptable_rank"])
        for row in rows
        if row.get("acceptable_rank") is not None
    ]
    return {
        "query_count": count,
        "http_success_rate": (
            sum(row["status_code"] == 200 for row in rows) / count if count else 0.0
        ),
        "hit_rate_at_1": sum(rank == 1 for rank in ranks) / count if count else 0.0,
        f"hit_rate_at_{top_k}": (
            sum(rank <= top_k for rank in ranks) / count if count else 0.0
        ),
        "mean_reciprocal_rank": (
            sum(1 / rank for rank in ranks) / count if count else 0.0
        ),
        "mean_ndcg_at_5": (
            statistics.fmean(float(row.get("ndcg_at_5", 0.0)) for row in rows)
            if rows
            else 0.0
        ),
        "metadata_candidate_hit_rate_at_5": (
            sum(bool(row.get("metadata_candidate_hit_at_5")) for row in rows)
            / count
            if count
            else 0.0
        ),
        "miss_count": sum(row.get("acceptable_rank") is None for row in rows),
        "empty_result_count": sum(not row.get("returned_product_ids") for row in rows),
    }


def build_summary(
    results: list[dict[str, Any]],
    *,
    top_k: int,
    run_context: dict[str, Any],
    valid_product_ids: set[str] | None = None,
) -> dict[str, Any]:
    successful = [row for row in results if row["status_code"] == 200]
    latencies = [float(row["search_latency_ms"]) for row in successful]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["test_group"])].append(row)
    overall = _group_metrics(results, top_k)
    constraint_metrics: dict[str, dict[str, Any]] = {}
    for field_name in CONSTRAINT_FIELDS:
        checks = [
            row["constraint_satisfaction"][field_name]
            for row in results
            if field_name in row.get("constraint_satisfaction", {})
        ]
        constraint_metrics[field_name] = {
            "query_count": len(checks),
            "satisfaction_at_1": (
                sum(bool(check.get("at_1")) for check in checks) / len(checks)
                if checks
                else None
            ),
            f"satisfaction_at_{top_k}": (
                sum(bool(check.get(f"at_{top_k}")) for check in checks)
                / len(checks)
                if checks
                else None
            ),
        }
    outside_by_case = {
        str(row["case_id"]): [
            product_id
            for product_id in row.get("returned_product_ids", [])
            if valid_product_ids is not None and product_id not in valid_product_ids
        ]
        for row in results
    }
    outside_by_case = {
        case_id: product_ids
        for case_id, product_ids in outside_by_case.items()
        if product_ids
    }
    metrics_by_group = {
        name: _group_metrics(rows, top_k)
        for name, rows in sorted(grouped.items())
    }
    required_hit5_groups = (
        "available-image",
        "external-image",
        "different-color",
        "different-material",
    )
    group_hit5_gate = all(
        metrics_by_group.get(name, {}).get(f"hit_rate_at_{top_k}") == 1.0
        for name in required_hit5_groups
    )
    specific_use = metrics_by_group.get("specific-use", {})
    return {
        "run_context": run_context,
        "ground_truth_contract": (
            "human-reviewed database candidates; relevance is satisfied by the first "
            "deduplicated returned product_id in approved_product_ids"
        ),
        **overall,
        "http_success_count": len(successful),
        "http_error_count": len(results) - len(successful),
        "status_counts": dict(Counter(str(row["status_code"]) for row in results)),
        "duplicate_result_query_count": sum(
            bool(row["has_duplicate_product_ids"]) for row in results
        ),
        "non_hybrid_source_query_count": sum(
            any(source != "hybrid" for source in row["sources"])
            for row in results
        ),
        "outside_snapshot_query_count": len(outside_by_case),
        "outside_snapshot_product_ids": sorted(
            {
                product_id
                for product_ids in outside_by_case.values()
                for product_id in product_ids
            },
            key=int,
        ),
        "outside_snapshot_cases": outside_by_case,
        "constraint_satisfaction": constraint_metrics,
        "relaxed_filter_query_count": sum(
            bool(row.get("relaxed_filters")) for row in results
        ),
        "mean_search_latency_ms": (
            statistics.fmean(latencies) if latencies else 0.0
        ),
        "p50_search_latency_ms": percentile(latencies, 0.50),
        "p95_search_latency_ms": percentile(latencies, 0.95),
        "max_search_latency_ms": max(latencies, default=0.0),
        "metrics_by_test_group": metrics_by_group,
        "miss_case_ids": [
            row["case_id"]
            for row in results
            if row.get("acceptable_rank") is None
        ],
        "acceptance_gates": {
            "http_success": len(successful) == len(results),
            "no_empty_results": all(
                row.get("returned_product_ids") for row in results
            ),
            "no_duplicate_results": not any(
                row.get("has_duplicate_product_ids") for row in results
            ),
            "snapshot_integrity": not outside_by_case,
            "hit_at_1": overall["hit_rate_at_1"] >= 0.80,
            f"hit_at_{top_k}": overall[f"hit_rate_at_{top_k}"] >= 0.96,
            "required_groups_hit_at_5": group_hit5_gate,
            "specific_use": (
                specific_use.get("hit_rate_at_1", 0.0) >= 0.80
                and specific_use.get(f"hit_rate_at_{top_k}", 0.0) == 1.0
            ),
            "latency_p95": percentile(latencies, 0.95) <= 5000,
            "explicit_constraints": all(
                metrics[f"satisfaction_at_{top_k}"] in {None, 1.0}
                for metrics in constraint_metrics.values()
            ),
        },
    }


def assessment(summary: dict[str, Any], top_k: int) -> str:
    lines = [
        "# Kết quả live hybrid review",
        "",
        f"- Run: `{summary['run_context']['run_id']}`",
        f"- Case: {summary['query_count']}",
        f"- HTTP success: {summary['http_success_count']}/{summary['query_count']}",
        f"- Hit@1: {summary['hit_rate_at_1']:.1%}",
        f"- Hit@{top_k}: {summary[f'hit_rate_at_{top_k}']:.1%}",
        f"- MRR: {summary['mean_reciprocal_rank']:.4f}",
        f"- NDCG@5: {summary['mean_ndcg_at_5']:.4f}",
        f"- Metadata candidate Hit@5: {summary['metadata_candidate_hit_rate_at_5']:.1%}",
        f"- Miss/empty/duplicate: {summary['miss_count']}/{summary['empty_result_count']}/{summary['duplicate_result_query_count']}",
        (
            f"- Query trả ID ngoài snapshot: "
            f"{summary['outside_snapshot_query_count']} "
            f"({', '.join(summary['outside_snapshot_product_ids']) or 'không có'})"
        ),
        (
            f"- Latency p50/p95/max: {summary['p50_search_latency_ms']:.0f}/"
            f"{summary['p95_search_latency_ms']:.0f}/{summary['max_search_latency_ms']:.0f} ms"
        ),
        "",
        "## Theo nhóm",
        "",
    ]
    for name, metrics in summary["metrics_by_test_group"].items():
        lines.append(
            f"- `{name}` ({metrics['query_count']}): Hit@1 "
            f"{metrics['hit_rate_at_1']:.1%}, Hit@{top_k} "
            f"{metrics[f'hit_rate_at_{top_k}']:.1%}, miss {metrics['miss_count']}"
        )
    lines.extend(["", "## Explicit constraint satisfaction", ""])
    for field_name, metrics in summary["constraint_satisfaction"].items():
        if not metrics["query_count"]:
            continue
        lines.append(
            f"- `{field_name}` ({metrics['query_count']}): @1 "
            f"{metrics['satisfaction_at_1']:.1%}, @{top_k} "
            f"{metrics[f'satisfaction_at_{top_k}']:.1%}"
        )
    lines.extend(
        [
            "",
            "## Miss",
            "",
            *(
                [f"- `{case_id}`" for case_id in summary["miss_case_ids"]]
                or ["- Không có."]
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run approved hybrid ground-truth review cases"
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=REVIEW_DIR / "test_cases_pending_review.csv",
    )
    parser.add_argument("--sql", type=Path, default=ROOT / "database" / "100.sql")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/search/hybrid")
    parser.add_argument("--health-url", default="http://127.0.0.1:8000/health/ready")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--download-timeout", type=int, default=30)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="Also run text-only and image-only baselines on the same 25 cases.",
    )
    parser.add_argument(
        "--approvals",
        type=Path,
        default=REVIEW_DIR / "ground_truth_approvals.json",
    )
    parser.add_argument("--service-env", type=Path, default=EVAL_DIR.parents[1] / "service-ai" / ".env")
    args = parser.parse_args()

    cases = read_csv(args.cases)
    approval_grades = load_approval_grades(args.approvals)
    cases = [
        {
            **case,
            "approved_grades": approval_grades.get(case["case_id"], {}),
        }
        for case in cases
    ]
    valid_product_ids = {
        product.product_id
        for product in extract_review_products(args.sql)
    }
    validate_runnable_cases(cases, valid_product_ids)
    endpoint = args.base_url.rstrip("/") + "/" + args.endpoint.lstrip("/")
    run_context = {
        "run_id": (
            f"hybrid-review-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-"
            f"{uuid4().hex[:8]}"
        ),
        "started_at": datetime.now(UTC).isoformat(),
        "endpoint": endpoint,
        "top_k": args.top_k,
        "timeout_seconds": args.timeout,
        "concurrency": 1,
        "readiness": health_snapshot(args.health_url, 10),
        "service_config": service_config_snapshot(args.service_env),
    }
    results: list[dict[str, Any]] = []
    cache_dir = EVAL_DIR / "data" / "review_images"
    for index, case in enumerate(cases, 1):
        result = run_case(
            case,
            endpoint=endpoint,
            cache_dir=cache_dir,
            top_k=args.top_k,
            timeout=args.timeout,
            download_timeout=args.download_timeout,
            force_download=args.force_download,
            valid_product_ids=valid_product_ids,
        )
        results.append(result)
        print(
            f"[{index:02d}/{len(cases):02d}] {result['case_id']} "
            f"status={result['status_code']} rank={result.get('acceptable_rank') or 'miss'} "
            f"search_ms={result['search_latency_ms']:.0f}",
            flush=True,
        )

    run_context["completed_at"] = datetime.now(UTC).isoformat()
    summary = build_summary(
        results,
        top_k=args.top_k,
        run_context=run_context,
        valid_product_ids=valid_product_ids,
    )
    if args.ablation:
        ablation_summaries: dict[str, dict[str, Any]] = {
            "constrained-hybrid": summary
        }
        for retrieval_mode in ("text-only", "image-only"):
            mode_results = [
                run_case(
                    case,
                    endpoint=endpoint,
                    cache_dir=cache_dir,
                    top_k=args.top_k,
                    timeout=args.timeout,
                    download_timeout=args.download_timeout,
                    force_download=args.force_download,
                    valid_product_ids=valid_product_ids,
                    retrieval_mode=retrieval_mode,
                )
                for case in cases
            ]
            ablation_summaries[retrieval_mode] = build_summary(
                mode_results,
                top_k=args.top_k,
                run_context={**run_context, "retrieval_mode": retrieval_mode},
                valid_product_ids=valid_product_ids,
            )
        (REVIEW_DIR / "ablation_summary.json").write_text(
            json.dumps(ablation_summaries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (REVIEW_DIR / "results.jsonl").write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in results
        ),
        encoding="utf-8",
    )
    (REVIEW_DIR / "result_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REVIEW_DIR / "assessment.md").write_text(
        assessment(summary, args.top_k),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all(summary["acceptance_gates"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
