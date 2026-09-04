from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


K_VALUES = (1, 5, 10, 20)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def query_map(path: Path) -> dict[str, dict[str, str]]:
    rows = read_rows(path)
    result = {row["query_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate query_id in {path}")
    return result


def exact_ranks(
    results_path: Path, queries: dict[str, dict[str, str]]
) -> tuple[dict[str, int | None], dict[str, int]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_rows(results_path):
        grouped.setdefault(row["query_id"], []).append(row)

    ranks: dict[str, int | None] = {}
    unique_counts: dict[str, int] = {}
    for query_id, query in queries.items():
        rows = grouped.get(query_id, [])
        unique_counts[query_id] = len({row["product_id"] for row in rows})
        ranks[query_id] = next(
            (
                int(row["rank"])
                for row in rows
                if row["product_id"] == query["source_product_id"]
            ),
            None,
        )
    return ranks, unique_counts


def reciprocal_rank(rank: int | None) -> float:
    return 0.0 if rank is None else 1.0 / rank


def aggregate(ranks: dict[str, int | None], query_ids: list[str]) -> dict[str, float]:
    result = {
        f"exact_hit@{k}": sum(
            rank is not None and rank <= k for rank in (ranks[q] for q in query_ids)
        )
        / len(query_ids)
        for k in K_VALUES
    }
    result["exact_mrr"] = sum(reciprocal_rank(ranks[q]) for q in query_ids) / len(
        query_ids
    )
    return result


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_delta(
    simple: dict[str, int | None],
    challenging: dict[str, int | None],
    query_ids: list[str],
    metric: str,
    samples: int = 10_000,
    seed: int = 42,
) -> dict[str, float | list[float]]:
    if metric.startswith("exact_hit@"):
        k = int(metric.split("@", 1)[1])

        def value(rank: int | None) -> float:
            return float(rank is not None and rank <= k)

    elif metric == "exact_mrr":
        value = reciprocal_rank
    else:
        raise ValueError(f"Unsupported metric: {metric}")

    paired = [(value(simple[q]), value(challenging[q])) for q in query_ids]
    observed = sum(hard - clean for clean, hard in paired) / len(paired)
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        selected = [paired[rng.randrange(len(paired))] for _ in paired]
        deltas.append(sum(hard - clean for clean, hard in selected) / len(selected))
    return {
        "challenging_minus_simple": observed,
        "ci95": [percentile(deltas, 0.025), percentile(deltas, 0.975)],
        "bootstrap_samples": samples,
        "seed": seed,
    }


def subgroup(query: dict[str, str]) -> str:
    notes = query.get("notes", "")
    if "outdoor" in notes:
        return "new_outdoor_34"
    if query.get("difficulty") == "medium":
        return "legacy_model_1_33"
    return "legacy_model_2_5_33"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simple-queries", type=Path, required=True)
    parser.add_argument("--simple-results", type=Path, required=True)
    parser.add_argument("--challenging-queries", type=Path, required=True)
    parser.add_argument("--challenging-results", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    simple_queries = query_map(args.simple_queries)
    challenging_queries = query_map(args.challenging_queries)
    if set(simple_queries) != set(challenging_queries):
        raise ValueError("The paired query_id sets do not match")
    for query_id in simple_queries:
        if (
            simple_queries[query_id]["source_product_id"]
            != challenging_queries[query_id]["source_product_id"]
        ):
            raise ValueError(f"Mismatched source product for {query_id}")

    simple_ranks, simple_unique = exact_ranks(args.simple_results, simple_queries)
    challenging_ranks, challenging_unique = exact_ranks(
        args.challenging_results, challenging_queries
    )
    query_ids = sorted(simple_queries)

    per_query = []
    for query_id in query_ids:
        clean_rank = simple_ranks[query_id]
        hard_rank = challenging_ranks[query_id]
        per_query.append(
            {
                "query_id": query_id,
                "source_product_id": simple_queries[query_id]["source_product_id"],
                "subgroup": subgroup(challenging_queries[query_id]),
                "simple_exact_rank": clean_rank or "",
                "challenging_exact_rank": hard_rank or "",
                "simple_hit_at_5": int(clean_rank is not None and clean_rank <= 5),
                "challenging_hit_at_5": int(hard_rank is not None and hard_rank <= 5),
                "simple_unique_products": simple_unique[query_id],
                "challenging_unique_products": challenging_unique[query_id],
            }
        )

    groups = {
        name: [row["query_id"] for row in per_query if row["subgroup"] == name]
        for name in ("new_outdoor_34", "legacy_model_1_33", "legacy_model_2_5_33")
    }
    report = {
        "evaluation": "paired_exact_product_retrieval",
        "query_count": len(query_ids),
        "simple": aggregate(simple_ranks, query_ids),
        "challenging": aggregate(challenging_ranks, query_ids),
        "paired_delta": {
            metric: bootstrap_delta(
                simple_ranks, challenging_ranks, query_ids, metric
            )
            for metric in ("exact_hit@1", "exact_hit@5", "exact_mrr")
        },
        "breakdown": {
            name: {
                "query_count": len(ids),
                "simple": aggregate(simple_ranks, ids),
                "challenging": aggregate(challenging_ranks, ids),
            }
            for name, ids in groups.items()
        },
        "validation": {
            "simple_queries_with_20_unique_products": sum(
                count == 20 for count in simple_unique.values()
            ),
            "challenging_queries_with_20_unique_products": sum(
                count == 20 for count in challenging_unique.values()
            ),
        },
        "challenging_exact_misses_at_5": [
            row for row in per_query if row["challenging_hit_at_5"] == 0
        ],
        "limitations": [
            "Similarity Recall, NDCG, and mAP require a newly pooled and reviewed ground truth.",
            "The runner output does not contain per-request latency.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_query[0]))
        writer.writeheader()
        writer.writerows(per_query)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
