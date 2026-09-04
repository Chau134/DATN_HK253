from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPT_DIR.parent
LEGACY_SCRIPTS = SUITE_DIR.parent / "conversational_ai_evaluation" / "scripts"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require_approved_ground_truth(path: Path) -> None:
    if not path.exists():
        raise SystemExit(
            "Ground truth is not locked. Review review/master_80/ground_truth_review_pending.csv "
            "and run 11_apply_master_ground_truth_review.py first."
        )
    summary = read_json(path)
    if summary.get("status") != "approved" or int(summary.get("question_count", 0)) != 80:
        raise SystemExit("Ground-truth approval must contain status=approved and question_count=80.")


def fetch_ready(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SystemExit(f"Cannot verify service readiness at {url}: {error}") from error


def require_matching_service(variant: dict[str, Any], ready: dict[str, Any]) -> None:
    expected_eval = variant["evaluation_variant"]
    actual_eval = ready.get("evaluation_variant")
    expected_rerank = bool(variant["reranker_enabled"])
    actual_rerank = bool(ready.get("effective_features", {}).get("reranker_enabled"))
    if not ready.get("ready"):
        raise SystemExit("Service reports ready=false; baseline run aborted.")
    if actual_eval != expected_eval or actual_rerank != expected_rerank:
        raise SystemExit(
            "Service configuration mismatch: "
            f"expected evaluation_variant={expected_eval}, reranker={expected_rerank}; "
            f"got evaluation_variant={actual_eval!r}, reranker={actual_rerank}."
        )


def run(command: list[str], allow_metric_failure: bool = False) -> int:
    completed = subprocess.run(command, check=False)
    if completed.returncode and not allow_metric_failure:
        raise SystemExit(completed.returncode)
    return completed.returncode


def main() -> int:
    args = parse_args()
    require_approved_ground_truth(args.approval_summary)
    manifest = read_json(args.manifest)
    variants = {item["id"]: item for item in manifest["variants"]}
    variant = variants[args.variant]
    ready = fetch_ready(args.readiness_url)
    require_matching_service(variant, ready)

    variant_dir = args.manifest.parent / variant["id"]
    reports = variant_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    execution_id = f"master80-{variant['id']}-{timestamp}"
    questions = (args.manifest.parent / manifest["questions"]).resolve()
    references = (args.manifest.parent / manifest["references"]).resolve()
    evidence = (args.manifest.parent / manifest["evidence"]).resolve()
    snapshot = SUITE_DIR / "data" / "master_80" / "product_snapshot.csv"
    responses = reports / "responses.csv"
    metadata = reports / "rag_eval_run_metadata.json"

    run([
        sys.executable, str(LEGACY_SCRIPTS / "07_run_rag_eval.py"),
        "--endpoint", args.endpoint,
        "--questions-csv", str(questions),
        "--snapshot-csv", str(snapshot),
        "--output-csv", str(responses),
        "--metadata-json", str(metadata),
        "--execution-id", execution_id,
        "--session-mode", variant["session_mode"],
        "--require-evaluation-trace",
    ])
    metric_status = run([
        sys.executable, str(LEGACY_SCRIPTS / "08_compute_rag_metrics.py"),
        "--responses-csv", str(responses),
        "--questions-csv", str(questions),
        "--references-csv", str(references),
        "--evidence-csv", str(evidence),
        "--output-csv", str(reports / "rag_metrics_by_question.csv"),
        "--output-json", str(reports / "rag_metrics_summary.json"),
        "--run-metadata-json", str(metadata),
    ], allow_metric_failure=True)
    print(json.dumps({
        "variant": variant["id"],
        "blind_code": variant["blind_code"],
        "execution_id": execution_id,
        "response_count": 80,
        "automatic_thresholds_passed": metric_status == 0,
        "next": "Run 10_prepare_variant_reviews.py after all four variants finish.",
    }, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one locked master-80 A-D ablation variant.")
    parser.add_argument("variant", choices=(
        "llm_no_rag", "rag_no_memory", "rag_memory_rerank_off", "rag_memory_rerank_on"
    ))
    parser.add_argument(
        "--manifest", type=Path,
        default=SUITE_DIR / "baselines" / "manifest_master_80.json",
    )
    parser.add_argument(
        "--approval-summary", type=Path,
        default=SUITE_DIR / "review" / "master_80" / "ground_truth_approval_summary.json",
    )
    parser.add_argument("--endpoint", default="http://localhost:8000/assistant/chat")
    parser.add_argument("--readiness-url", default="http://localhost:8000/health/ready")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
