from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
import importlib.util
from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter_ns
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
RESULT_FIELDS = [
    "run_id", "query_id", "mode", "rank", "product_id", "score",
    "raw_score_json",
]
GROUND_TRUTH_FIELDS = [
    "query_id", "mode", "query_type", "relevant_product_id",
    "relevance_grade", "match_reason", "source", "review_status", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def normalize(value: str | None) -> str:
    value = (value or "").replace("Đ", "D").replace("đ", "d")
    value = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", ascii_text.casefold()).split())


def price_bucket(value: str | None) -> str:
    try:
        price = float(value or "")
    except ValueError:
        return ""
    if price < 200_000:
        return "under_200k"
    if price < 500_000:
        return "200k_500k"
    if price < 1_000_000:
        return "500k_1m"
    if price < 2_000_000:
        return "1m_2m"
    return "over_2m"


_contract_spec = importlib.util.spec_from_file_location("hybrid_constraint_contract", SCRIPT_DIR / "13_compare_ablation.py")
_contract = importlib.util.module_from_spec(_contract_spec)
_contract_spec.loader.exec_module(_contract)
required_constraints = _contract.required_constraints
product_satisfies = _contract.product_satisfies


def filter_image_results(
    query: dict[str, str],
    products: dict[str, dict[str, str]],
    source_rows: list[dict[str, str]],
    *,
    candidate_pool_size: int,
) -> list[dict[str, str]]:
    required_constraints(query)  # validate the frozen query contract
    ordered = sorted(source_rows, key=lambda row: int(row.get("rank") or 0))
    candidates = [row for row in ordered if 0 < int(row.get("rank") or 0) <= candidate_pool_size]
    missing_products = sorted({row["product_id"] for row in candidates if row["product_id"] not in products})
    if missing_products:
        raise ValueError(f"products missing from snapshot: {missing_products[:10]}")
    return [row for row in candidates if product_satisfies(products[row["product_id"]], query)]


def extend_ground_truth(
    queries: dict[str, dict[str, str]],
    ground_truth: list[dict[str, str]],
    image_ground_truth: list[dict[str, str]],
    required_pairs: list[tuple[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    existing = {(row["query_id"], row["relevant_product_id"]) for row in ground_truth}
    approved_image = {
        (row["query_id"], row["relevant_product_id"]): row
        for row in image_ground_truth
        if row.get("review_status") == "approved"
    }
    additions: list[dict[str, str]] = []
    for query_id, product_id in dict.fromkeys(required_pairs):
        if (query_id, product_id) in existing:
            continue
        image_query_id = queries[query_id]["source_image_query_id"]
        prior = approved_image.get((image_query_id, product_id))
        if prior is None:
            raise ValueError(
                "post-filter Top-5 candidate has no approved Hybrid or Image ground-truth label: "
                f"{query_id}/{product_id}"
            )
        additions.append({
            "query_id": query_id,
            "mode": "multimodal",
            "query_type": "positive",
            "relevant_product_id": product_id,
            "relevance_grade": prior["relevance_grade"],
            "match_reason": "text_constraints_match+approved_visual_grade",
            "source": "approved_image_ground_truth_transfer",
            "review_status": "approved",
            "notes": (
                f"reused_image_ground_truth:{prior.get('source', '')}:"
                f"{prior.get('notes', '')};added_for_image_post_filter_baseline"
            ),
        })
        existing.add((query_id, product_id))
    return [*ground_truth, *additions], additions


def percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def main() -> int:
    args = parse_args()
    query_rows = read_csv(args.queries_csv)
    if len(query_rows) != 100:
        raise ValueError(f"expected frozen 100-query suite, got {len(query_rows)}")
    queries = {row["query_id"]: row for row in query_rows}
    products = {row["product_id"]: row for row in read_csv(args.products_csv)}
    source_results = read_csv(args.source_results_csv)
    source_responses = read_jsonl(args.source_responses_jsonl)
    responses_by_query = {row["query_id"]: row for row in source_responses}
    if len(responses_by_query) != 100 or set(responses_by_query) != set(queries):
        raise ValueError("image-only source must contain one response for every frozen query")
    if any(row.get("status_code") != 200 or row.get("variant") != "image-only" for row in source_responses):
        raise ValueError("image-only source contains a failed request or unexpected variant")
    if any(bool(row.get("reranker_enabled")) for row in source_responses):
        raise ValueError("image-only source unexpectedly reports reranker enabled")

    results_by_query: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_results:
        if row.get("query_id") not in queries:
            raise ValueError(f"source result contains unknown query: {row.get('query_id')}")
        results_by_query[row["query_id"]].append(row)

    run_id = args.run_id or f"hybrid-image-post-filter-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    output_results: list[dict[str, Any]] = []
    output_responses: list[dict[str, Any]] = []
    required_gt_pairs: list[tuple[str, str]] = []
    filter_latencies: list[float] = []
    empty_queries = 0

    for query in query_rows:
        query_id = query["query_id"]
        started_ns = perf_counter_ns()
        filtered = filter_image_results(
            query,
            products,
            results_by_query[query_id],
            candidate_pool_size=args.candidate_pool_size,
        )[: args.output_top_k]
        filter_ms = (perf_counter_ns() - started_ns) / 1_000_000
        filter_latencies.append(filter_ms)
        if not filtered:
            empty_queries += 1
        constraints = required_constraints(query)
        response_items: list[dict[str, Any]] = []
        for rank, source_row in enumerate(filtered, 1):
            raw = json.loads(source_row.get("raw_score_json") or "{}")
            raw.update(source="image_post_filter", post_filter_constraints=constraints)
            output_results.append({
                "run_id": run_id,
                "query_id": query_id,
                "mode": "image-post-filter",
                "rank": rank,
                "product_id": source_row["product_id"],
                "score": source_row.get("score", ""),
                "raw_score_json": json.dumps(raw, ensure_ascii=False, separators=(",", ":")),
            })
            response_items.append(raw)
            if rank <= 5:
                required_gt_pairs.append((query_id, source_row["product_id"]))

        source_response = responses_by_query[query_id]
        response_row = deepcopy(source_response)
        source_search_ms = float(source_response.get("search_latency_ms") or 0)
        source_total_ms = float(source_response.get("total_latency_ms") or 0)
        response_row.update({
            "run_id": run_id,
            "variant": "image-post-filter",
            "endpoint": "offline-replay:image-only+metadata-post-filter",
            "source_run_id": source_response.get("run_id", ""),
            "candidate_pool_size": args.candidate_pool_size,
            "post_filter_latency_ms": round(filter_ms, 6),
            "search_latency_ms": round(source_search_ms + filter_ms, 6),
            "total_latency_ms": round(source_total_ms + filter_ms, 6),
            "response": {
                "filters": constraints,
                "product_ids": [item["product_id"] for item in response_items],
                "results": response_items,
                "post_filter_source": "frozen_image_only_20260828",
            },
        })
        output_responses.append(response_row)

    extended_gt, additions = extend_ground_truth(
        queries,
        read_csv(args.ground_truth_csv),
        read_csv(args.image_ground_truth_csv),
        required_gt_pairs,
    )
    write_csv(args.output_results_csv, output_results, RESULT_FIELDS)
    write_jsonl(args.output_responses_jsonl, output_responses)
    write_csv(args.output_ground_truth_csv, extended_gt, GROUND_TRUTH_FIELDS)
    metadata = {
        "run_id": run_id,
        "method": "offline replay of frozen image-only Top-20 followed by request-scoped semantic metadata post-filter",
        "constraint_contract": "only attributes parsed from user query text; all requested fields required; plain usage lists use ANY",
        "source_results": str(args.source_results_csv),
        "source_responses": str(args.source_responses_jsonl),
        "query_count": len(query_rows),
        "candidate_pool_size": args.candidate_pool_size,
        "output_top_k": args.output_top_k,
        "returned_rows": len(output_results),
        "empty_queries": empty_queries,
        "post_filter_latency_p95_ms": percentile(filter_latencies, 0.95),
        "ground_truth_rows_before": len(extended_gt) - len(additions),
        "ground_truth_rows_after": len(extended_gt),
        "ground_truth_transfers_added": len(additions),
        "unresolved_ground_truth_pairs": 0,
    }
    args.output_metadata_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_metadata_json.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    root = SCRIPT_DIR.parent
    parser = argparse.ArgumentParser(
        description="Build an image-retrieval plus request-scoped metadata post-filter baseline from the frozen image-only run."
    )
    parser.add_argument("--queries-csv", type=Path, default=root / "data/multimodal_queries.csv")
    parser.add_argument("--products-csv", type=Path, default=root / "data/product_snapshot.csv")
    parser.add_argument("--source-results-csv", type=Path, default=root / "data/search_results_image_only_20260828.csv")
    parser.add_argument("--source-responses-jsonl", type=Path, default=root / "reports/hybrid_responses_image_only_20260828.jsonl")
    parser.add_argument("--ground-truth-csv", type=Path, default=root / "data/ground_truth_multimodal.csv")
    parser.add_argument("--image-ground-truth-csv", type=Path, default=root.parent / "image/data/ground_truth_image_paired.csv")
    parser.add_argument("--output-results-csv", type=Path, default=root / "data/search_results_image_post_filter_20260831.csv")
    parser.add_argument("--output-responses-jsonl", type=Path, default=root / "reports/hybrid_responses_image_post_filter_20260831.jsonl")
    parser.add_argument("--output-ground-truth-csv", type=Path, default=root / "data/ground_truth_multimodal_post_filter_20260831.csv")
    parser.add_argument("--output-metadata-json", type=Path, default=root / "reports/hybrid_image_post_filter_run_metadata_20260831.json")
    parser.add_argument("--candidate-pool-size", type=int, default=20)
    parser.add_argument("--output-top-k", type=int, default=20)
    parser.add_argument("--run-id", default="hybrid-image-post-filter-20260831")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
