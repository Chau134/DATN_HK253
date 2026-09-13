"""Manifest and paired policy evaluation, preserving the report's metrics.

Never supplies fixture filters to the service. Unknown relevance is reported as
pending review, not silently converted into an authoritative grade zero.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
spec = importlib.util.spec_from_file_location("comparison", ROOT / "scripts/13_compare_ablation.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprints(paths):
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def validate_policy_results(results):
    seen = defaultdict(set)
    ranks = defaultdict(set)
    for row in results:
        rank = int(row["rank"])
        if rank <= 0:
            continue
        qid, pid = row["query_id"], row["product_id"]
        if pid in seen[qid] or rank in ranks[qid]:
            raise ValueError(f"Duplicate product or rank in query {qid}")
        seen[qid].add(pid)
        ranks[qid].add(rank)


def snapshot(args):
    # Container env is only held in memory; the allowlist excludes credentials.
    info = json.loads(subprocess.check_output(["docker", "inspect", args.container], text=True))[0]
    env = dict(value.split("=", 1) for value in info["Config"]["Env"] if "=" in value)
    allowed = {"EMBEDDING_PROVIDER", "BEDROCK_REGION", "BEDROCK_MODEL_ID", "BEDROCK_EMBEDDING_MODEL_ID",
               "QDRANT_TEXT_COLLECTION", "QDRANT_IMAGE_COLLECTION", "RERANK_ENABLED", "YOLO_ENABLED",
               "BEDROCK_EMBEDDING_MIN_REQUEST_INTERVAL_SECONDS", "PRELOAD_MODELS", "TEXT_TOP_K", "IMAGE_TOP_K", "HYBRID_TOP_K"}
    allowed.update(k for k in env if k.startswith("HYBRID_") and not any(word in k for word in ("TOKEN", "KEY", "SECRET", "PASSWORD")))
    files = list((REPO / "service-ai/src").rglob("*.py")) + [ROOT / "data" / name for name in ("multimodal_queries.csv", "product_snapshot.csv", "ground_truth_multimodal.csv")]
    value = {"created_at": datetime.now(timezone.utc).isoformat(), "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
             "worktree": subprocess.check_output(["git", "status", "--short"], text=True).splitlines(),
             "container_id": info["Id"], "image_id": info["Image"], "container_started_at": info["State"]["StartedAt"],
             "runtime_environment_allowlist": {k: env[k] for k in sorted(allowed) if k in env},
             "source_note": "workspace hashes; separately record PYTHONPATH and effective readiness for temporary policy processes",
             "files_sha256": fingerprints(files), "seed": 42, "top_k": 20}
    if args.runtime_url:
        script = "import json,sys,urllib.request; print(json.dumps(json.load(urllib.request.urlopen(sys.argv[1] + '/health/ready'))))"
        value["readiness"] = json.loads(subprocess.check_output(["docker", "exec", args.container, "python", "-c", script, args.runtime_url], text=True))
        value["runtime_url_inside_container"] = args.runtime_url
    if args.runtime_source:
        if args.runtime_source not in ("/tmp/hybrid-src", "/app/src"):
            raise ValueError("Expected the original or temporary source directory")
        script = "import pathlib,hashlib,json,sys; root=pathlib.Path(sys.argv[1]); print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.py')}))"
        value["runtime_source_sha256"] = json.loads(subprocess.check_output(["docker", "exec", args.container, "python", "-c", script, args.runtime_source], text=True))
        value["runtime_source"] = args.runtime_source
    write_json(args.output / "manifest.json", value)
    print(f"manifest={args.output / 'manifest.json'}")


def evaluate(args):
    queries = comparison.read_csv(ROOT / "data/multimodal_queries.csv")
    products = comparison.read_csv(args.products or ROOT / "data/product_snapshot.csv")
    gt = comparison.read_csv(args.ground_truth or ROOT / "data/ground_truth_multimodal.csv")
    approved = {(r["query_id"], r["relevant_product_id"]) for r in gt if r.get("review_status") == "approved"}
    if len(queries) != 100 or len(approved) != len(gt):
        raise ValueError("Expected 100 queries and unique, approved ground truth")
    report, per_config, missing = {}, {}, []
    for item in args.run:
        name, prefix = item.split("=", 1)
        results = comparison.read_csv(Path(prefix + "_results.csv"))
        responses = comparison.read_jsonl(Path(prefix + "_responses.jsonl"))
        comparison.validate_run("fusion_no_rerank", [q["query_id"] for q in queries], results, responses)
        validate_policy_results(results)
        per_query = comparison.build_per_query(queries, products, gt, results, responses)
        per_config[name] = per_query
        unknown = {(r["query_id"], r["product_id"]) for r in results if 0 < int(r["rank"]) <= 5} - approved
        missing.extend({"configuration": name, "query_id": q, "product_id": p, "review_status": "pending"} for q, p in sorted(unknown))
        metrics = comparison.aggregate(per_query)
        metrics["graded_metrics_status"] = "pending_pool_review" if unknown else "complete"
        metrics["unjudged_top5_pairs"] = len(unknown)
        metrics["empty_queries"] = sum(r["returned@5"] == 0 for r in per_query)
        metrics["mean_returned@5"] = statistics.fmean(r["returned@5"] for r in per_query)
        metrics["by_transformation"] = {t: comparison.aggregate([r for r in per_query if r["transformation_type"] == t]) for t in sorted({r["transformation_type"] for r in per_query})}
        if unknown:
            metrics["provisional_graded_ndcg@5"] = metrics.pop("graded_ndcg@5")
            metrics["provisional_request_conditioned_ndcg@5"] = metrics.pop("request_conditioned_ndcg@5")
            metrics["provisional_graded_recall@5"] = metrics.pop("graded_recall@5")
        report[name] = metrics
    names = list(per_config)
    bootstrap = {}
    if len(names) >= 2:
        for name in names[1:]:
            ci = comparison.paired_bootstrap(per_config[names[0]], per_config[name], 10000, 42)
            if any(report[n]["unjudged_top5_pairs"] for n in (names[0], name)):
                ci = {k: v for k, v in ci.items() if not k.startswith("graded_") and k != "request_conditioned_ndcg@5"}
            bootstrap[f"{name}_minus_{names[0]}"] = ci
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "pending_pool_review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["configuration", "query_id", "product_id", "review_status"])
        writer.writeheader()
        writer.writerows(missing)
    write_json(args.output / "comparison.json", {
        "constraint_contract": "request-scoped v2; parsed only from user query text; all requested fields required; plain usage list uses ANY",
        "legacy_exact_constraint_contract": "diagnostic only; every non-empty fixture field compared exactly",
        "request_conditioned_ndcg_contract": "human grades unchanged; constraint-violating judged products contribute zero gain for that query",
        "configurations": report, "paired_bootstrap": bootstrap, "per_query": per_config,
        "ground_truth_sha256": hashlib.sha256((args.ground_truth or ROOT / "data/ground_truth_multimodal.csv").read_bytes()).hexdigest(),
        "product_snapshot_sha256": hashlib.sha256((args.products or ROOT / "data/product_snapshot.csv").read_bytes()).hexdigest(),
    })
    any_pending = any(metrics["unjudged_top5_pairs"] for metrics in report.values())
    status_note = ("Graded values with missing labels are provisional and cannot establish acceptance."
                   if any_pending else "All returned Top-5 pairs are judged; graded metrics are complete for this GT version.")
    lines = ["# Hybrid policy comparison", "", status_note, "",
             "Constraint satisfaction uses only attributes parsed from user query text; all requested fields must pass for a returned product. Plain usage lists use ANY. The legacy exact-fixture value is retained only as a diagnostic.", "",
             "| Policy | Strict Hit@5 | Graded NDCG@5 | Request-conditioned NDCG@5 | Request-scoped satisfaction@5 | Legacy exact diagnostic | Constraint success@5 | P95 search ms | Unjudged Top-5 pairs |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, metrics in report.items():
        ndcg = metrics.get("graded_ndcg@5", metrics.get("provisional_graded_ndcg@5"))
        conditioned_ndcg = metrics.get("request_conditioned_ndcg@5", metrics.get("provisional_request_conditioned_ndcg@5"))
        lines.append(f"| {name} | {metrics['strict_hit@5']:.3f} | {ndcg:.3f} | {conditioned_ndcg:.3f} | {metrics['constraint_satisfaction@5']:.3f} | {metrics['legacy_exact_constraint_satisfaction@5']:.3f} | {metrics['constraint_success@5']:.3f} | {metrics['p95_latency_ms']:.1f} | {metrics['unjudged_top5_pairs']} |")
    review_note = ("Pending pairs: `pending_pool_review.csv`. Review labels independently, version the expanded ground truth, and rescore every policy on that same version."
                   if any_pending else "No Top-5 pair remains unjudged for this comparison. Preserve the reviewed GT version and provenance when reproducing results.")
    lines.extend(["", review_note, "",
                  "Latency differences across host/container runners or different cache histories are descriptive only. Use the matched load experiments for performance comparison."])
    (args.output / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: {m: v for m, v in d.items() if m != "by_transformation"} for k, d in report.items()}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["snapshot", "compare"])
    parser.add_argument("--container", default="service-ai-service-ai-1")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path)
    parser.add_argument("--products", type=Path, help="versioned product snapshot used for independent constraint checks")
    parser.add_argument("--runtime-url", help="URL as seen inside the selected Docker container")
    parser.add_argument("--runtime-source", choices=["/tmp/hybrid-src", "/app/src"])
    parser.add_argument("--run", action="append", default=[], help="name=path_prefix; loads prefix_results.csv and prefix_responses.jsonl")
    args = parser.parse_args()
    snapshot(args) if args.action == "snapshot" else evaluate(args)


if __name__ == "__main__":
    main()
