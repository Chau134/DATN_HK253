from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from statistics import mean
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
IMAGE_ROOT = SCRIPT_DIR.parents[1]
METRICS = ("recall@5", "ndcg@5", "recall@10", "ndcg@10", "recall@20", "ndcg@20", "ap")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * probability)]


def paired_bootstrap(
    simple: dict[str, dict[str, Any]],
    challenging: dict[str, dict[str, Any]],
    *,
    samples: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    query_ids = sorted(simple)
    if query_ids != sorted(challenging):
        raise ValueError("simple and challenging per-query IDs differ")
    deltas = {
        metric: [float(challenging[q][metric]) - float(simple[q][metric]) for q in query_ids]
        for metric in METRICS
    }
    rng = random.Random(seed)
    boot = {metric: [] for metric in METRICS}
    for _ in range(samples):
        indices = [rng.randrange(len(query_ids)) for _ in query_ids]
        for metric in METRICS:
            boot[metric].append(mean(deltas[metric][index] for index in indices))
    return {
        metric: {
            "delta": mean(deltas[metric]),
            "ci95_low": percentile(boot[metric], 0.025),
            "ci95_high": percentile(boot[metric], 0.975),
        }
        for metric in METRICS
    }


def aggregate_subset(rows: dict[str, dict[str, Any]], query_ids: set[str]) -> dict[str, float]:
    selected = [rows[query_id] for query_id in sorted(query_ids)]
    return {metric: mean(float(row[metric]) for row in selected) for metric in METRICS}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare paired simple/challenging similarity metrics.")
    parser.add_argument("--simple-json", type=Path, default=IMAGE_ROOT / "simple/reports/metrics_paired_simple.json")
    parser.add_argument("--challenging-json", type=Path, default=IMAGE_ROOT / "challenging/reports/metrics_paired_challenging.json")
    parser.add_argument("--canonical-queries", type=Path, default=IMAGE_ROOT / "data/image_queries.csv")
    parser.add_argument("--challenging-queries", type=Path, default=IMAGE_ROOT / "challenging/data/image_queries.csv")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-json", type=Path, default=SCRIPT_DIR.parent / "reports/paired_similarity_comparison.json")
    parser.add_argument("--output-md", type=Path, default=SCRIPT_DIR.parent / "reports/paired_similarity_comparison.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    simple_report = read_json(args.simple_json)
    challenging_report = read_json(args.challenging_json)
    simple = {row["query_id"]: row for row in simple_report["per_query"]}
    challenging = {row["query_id"]: row for row in challenging_report["per_query"]}
    canonical = {row["query_id"]: row for row in read_csv(args.canonical_queries)}
    current = {row["query_id"]: row for row in read_csv(args.challenging_queries)}
    outdoor = {
        query_id
        for query_id, row in current.items()
        if canonical.get(query_id, {}).get("image_url") != row.get("image_url")
    }
    reused = set(current) - outdoor
    paired = paired_bootstrap(simple, challenging, samples=args.bootstrap_samples, seed=args.seed)
    result = {
        "query_count": len(simple),
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "simple": {metric: float(simple_report["aggregate"]["map" if metric == "ap" else metric]) for metric in METRICS},
        "challenging": {
            metric: float(challenging_report["aggregate"]["map" if metric == "ap" else metric]) for metric in METRICS
        },
        "paired_delta_challenging_minus_simple": paired,
        "subgroups": {
            "reused_model_66": {
                "query_count": len(reused),
                "simple": aggregate_subset(simple, reused),
                "challenging": aggregate_subset(challenging, reused),
            },
            "new_outdoor_34": {
                "query_count": len(outdoor),
                "simple": aggregate_subset(simple, outdoor),
                "challenging": aggregate_subset(challenging, outdoor),
            },
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    labels = {"recall@5": "Recall@5", "ndcg@5": "NDCG@5", "ap": "mAP"}
    lines = [
        "# Paired Image Similarity Comparison",
        "",
        f"Queries: {len(simple)}; paired bootstrap: {args.bootstrap_samples:,} samples; seed: {args.seed}.",
        "",
        "| Metric | Simple | Challenging | Delta C-S | CI 95% |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric in ("recall@5", "ndcg@5", "ap"):
        stats = paired[metric]
        lines.append(
            f"| {labels[metric]} | {result['simple'][metric]:.4f} | {result['challenging'][metric]:.4f} | "
            f"{stats['delta']:+.4f} | [{stats['ci95_low']:+.4f}, {stats['ci95_high']:+.4f}] |"
        )
    lines.extend(["", "The shared ground truth uses binary relevance grade >= 2; grade 1 contributes to graded NDCG."])
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"comparison -> {args.output_json} , {args.output_md}")
    for metric in ("recall@5", "ndcg@5", "ap"):
        stats = paired[metric]
        print(
            f"{labels[metric]} simple={result['simple'][metric]:.4f} challenging={result['challenging'][metric]:.4f} "
            f"delta={stats['delta']:+.4f} ci95=[{stats['ci95_low']:+.4f},{stats['ci95_high']:+.4f}]"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
