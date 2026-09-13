"""Replay a frozen Fusion candidate list through the request-scoped contract.

This is a diagnostic only: it preserves the source ranking and latency, filters
with the production Hybrid intent predicate, and never calls a provider or
changes ground-truth labels.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hybrid_contract", ROOT / "scripts/13_compare_ablation.py")
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refuse_existing(paths: list[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite replay artifacts: {existing}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter frozen Fusion candidates by user-requested constraints.")
    parser.add_argument("--queries", type=Path, default=ROOT / "data/multimodal_queries.csv")
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--source-results", type=Path, required=True)
    parser.add_argument("--source-responses", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--candidate-limit", type=int, default=20)
    args = parser.parse_args()

    outputs = {
        "results": Path(f"{args.output_prefix}_results.csv"),
        "responses": Path(f"{args.output_prefix}_responses.jsonl"),
        "metadata": Path(f"{args.output_prefix}_metadata.json"),
    }
    refuse_existing(list(outputs.values()))
    queries = CONTRACT.read_csv(args.queries)
    products = {row["product_id"]: row for row in CONTRACT.read_csv(args.products)}
    source_results = CONTRACT.read_csv(args.source_results)
    source_responses = CONTRACT.read_jsonl(args.source_responses)
    if len(queries) != 100 or len(source_responses) != 100:
        raise ValueError("Expected the frozen 100-query evaluation set")

    results_by_query: dict[str, list[dict[str, str]]] = {}
    for query in queries:
        query_id = query["query_id"]
        ordered = sorted(
            (row for row in source_results if row["query_id"] == query_id and int(row["rank"]) <= args.candidate_limit),
            key=lambda row: int(row["rank"]),
        )
        missing = [row["product_id"] for row in ordered if row["product_id"] not in products]
        if missing:
            raise ValueError(f"{query_id}: products missing from canonical snapshot: {missing[:5]}")
        admitted = [row for row in ordered if CONTRACT.product_satisfies(products[row["product_id"]], query)]
        replayed = []
        for rank, row in enumerate(admitted, 1):
            replay = dict(row)
            replay["run_id"] = "request-scoped-fusion-replay-20260911"
            replay["rank"] = str(rank)
            replayed.append(replay)
        results_by_query[query_id] = replayed

    output_rows = [row for query in queries for row in results_by_query[query["query_id"]]]
    outputs["results"].parent.mkdir(parents=True, exist_ok=True)
    with outputs["results"].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(source_results[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    response_by_query = {row["query_id"]: row for row in source_responses}
    with outputs["responses"].open("w", encoding="utf-8", newline="\n") as handle:
        for query in queries:
            query_id = query["query_id"]
            response_row = dict(response_by_query[query_id])
            response_row["run_id"] = "request-scoped-fusion-replay-20260911"
            response_row["offline_replay"] = True
            response = dict(response_row.get("response") or {})
            admitted = results_by_query[query_id]
            response["product_ids"] = [row["product_id"] for row in admitted]
            response["results"] = [
                {"product_id": row["product_id"], "score": float(row["score"]), "source": "hybrid"}
                for row in admitted
            ]
            response_row["response"] = response
            handle.write(json.dumps(response_row, ensure_ascii=False) + "\n")

    metadata = {
        "method": "frozen Fusion Top-20 filtered by request-scoped production predicate; source order preserved",
        "diagnostic_only": True,
        "query_count": len(queries),
        "result_count": len(output_rows),
        "underfilled_top5_queries": sum(len(results_by_query[row["query_id"]]) < 5 for row in queries),
        "inputs_sha256": {
            "queries": sha256(args.queries),
            "products": sha256(args.products),
            "source_results": sha256(args.source_results),
            "source_responses": sha256(args.source_responses),
        },
        "constraint_contract": "only attributes parsed from query_text; all requested fields pass; plain usage list is ANY",
    }
    outputs["metadata"].write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
