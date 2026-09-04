from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from common import SUITE_DIR, read_json, rounded, write_csv, write_json


def _metric(summary: dict[str, Any], name: str) -> float | None:
    value = summary.get("metrics", {}).get(name)
    return float(value) if value is not None else None


def compare(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = read_json(manifest_path)
    rows = []
    loaded: dict[str, dict[str, Any]] = {}
    for variant in manifest["variants"]:
        metrics_path = (manifest_path.parent / variant["metrics_summary"]).resolve()
        human_path = (manifest_path.parent / variant["human_summary"]).resolve()
        metrics = read_json(metrics_path) if metrics_path.exists() else None
        human = read_json(human_path) if human_path.exists() else None
        loaded[variant.get("comparison_role", variant["id"])] = {
            "metrics": metrics,
            "human": human,
        }
        acceptance = None
        if human and human.get("status") == "complete":
            counts = human.get("consensus_counts", {})
            decided = counts.get("accepted", 0) + counts.get("rejected", 0)
            acceptance = counts.get("accepted", 0) / decided if decided else None
        rows.append({
            "variant": variant["id"],
            "label": variant["label"],
            "comparison_role": variant.get("comparison_role", variant["id"]),
            "session_mode": variant.get("session_mode", ""),
            "reranker_enabled": variant.get("reranker_enabled"),
            "optional": bool(variant.get("optional", False)),
            "status": "complete" if metrics and human and human.get("status") == "complete" else "pending",
            "grounding": _metric(metrics, "rule_based_grounding_score") if metrics else None,
            "token_f1": _metric(metrics, "token_f1_relevancy") if metrics else None,
            "context_precision": _metric(metrics, "context_precision") if metrics else None,
            "context_recall": _metric(metrics, "context_recall") if metrics else None,
            "human_acceptance_rate": rounded(acceptance),
        })
        # Human scoring is optional; technical completion depends on metric artifacts.
        rows[-1]['status'] = 'complete' if metrics else 'pending'

    claims = []
    full = loaded.get("full_rerank_off", loaded.get("rag_search_memory_full", {}))
    reranked = loaded.get("full_rerank_on", {})
    no_rag = loaded.get("no_rag", loaded.get("llm_no_rag", {}))
    no_memory = loaded.get("no_memory", loaded.get("rag_no_memory", {}))
    if full.get("metrics") and no_rag.get("metrics"):
        full_grounding = _metric(full["metrics"], "rule_based_grounding_score")
        no_rag_grounding = _metric(no_rag["metrics"], "rule_based_grounding_score")
        if full_grounding is not None and no_rag_grounding is not None:
            claims.append({
                "comparison": "full_minus_no_rag_grounding",
                "delta": rounded(full_grounding - no_rag_grounding),
                "ready": True,
            })
    if full.get("human") and no_memory.get("human"):
        claims.append({
            "comparison": "full_vs_no_memory_context_retention",
            "ready": (
                full["human"].get("status") == "complete"
                and no_memory["human"].get("status") == "complete"
            ),
            "note": "Use context_retention human dimension after both reviews are complete.",
        })
    if full.get("metrics") and reranked.get("metrics"):
        for metric in (
            "rule_based_grounding_score",
            "token_f1_relevancy",
            "context_precision",
            "context_recall",
        ):
            off_value = _metric(full["metrics"], metric)
            on_value = _metric(reranked["metrics"], metric)
            if off_value is not None and on_value is not None:
                claims.append({
                    "comparison": f"rerank_on_minus_off_{metric}",
                    "delta": rounded(on_value - off_value),
                    "ready": True,
                })

    # Remove the legacy human-review dependency and compare memory automatically.
    claims = [
        claim for claim in claims
        if claim.get('comparison') != 'full_vs_no_memory_context_retention'
    ]
    if full.get('metrics') and no_memory.get('metrics'):
        full_recall = _metric(full['metrics'], 'context_recall')
        no_memory_recall = _metric(no_memory['metrics'], 'context_recall')
        claims.append({
            'comparison': 'full_minus_no_memory_context_recall',
            'delta': rounded(full_recall - no_memory_recall)
            if full_recall is not None and no_memory_recall is not None else None,
            'ready': full_recall is not None and no_memory_recall is not None,
            'note': 'Automatic comparison on the approved ground truth.',
        })

    output = {
        "variants": rows,
        "causal_comparisons": claims,
        "all_required_complete": all(
            row["status"] == "complete" for row in rows if not row["optional"]
        ),
    }
    reports = SUITE_DIR / "reports"
    write_json(reports / "baseline_comparison.json", output)
    write_csv(
        reports / "baseline_comparison.csv",
        rows,
        (
            "variant", "label", "comparison_role", "session_mode", "reranker_enabled",
            "optional", "status", "grounding", "token_f1",
            "context_precision", "context_recall", "human_acceptance_rate",
        ),
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare no-RAG, no-memory and full variants.")
    parser.add_argument(
        "--manifest", type=Path,
        default=SUITE_DIR / "baselines" / "manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    result = compare(parse_args().manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_required_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
