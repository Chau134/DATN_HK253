from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPT_DIR.parent


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def variant_review_config(variant: dict[str, Any]) -> dict[str, Any]:
    blind_code = variant["blind_code"]
    return {
        "suite": f"conversational_ai_master_80_{blind_code}",
        "version": "2.0",
        "sample_size": 80,
        "sampling_seed": 252,
        "acceptable_rating": 4,
        "current_token_f1_threshold": 0.70,
        "source": {
            "questions_csv": "../../data/master_80/question_set.csv",
            "references_csv": "../../data/master_80/reference_answers.csv",
            "evidence_csv": "../../data/master_80/required_evidence.csv",
            "responses_csv": "reports/responses.csv",
            "metrics_csv": "reports/rag_metrics_by_question.csv",
            "metrics_summary_json": "reports/rag_metrics_summary.json",
            "critical_cases_csv": "../../data/critical_cases.csv",
            "critical_responses_csv": "reports/responses.csv",
        },
        "review": {
            "reviewer_a_csv": f"review/reviewer_a_{blind_code}.csv",
            "reviewer_b_csv": f"review/reviewer_b_{blind_code}.csv",
        },
        "reports": {
            "sample_manifest_csv": "reports/review_manifest.csv",
            "automatic_breakdown_csv": "reports/automatic_breakdown.csv",
            "human_validation_summary_json": "reports/human_validation_summary.json",
            "human_validation_by_case_csv": "reports/human_validation_by_case.csv",
            "adjudication_csv": "review/adjudication.csv",
            "calibration_csv": "reports/token_f1_calibration.csv",
        },
    }


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.manifest)
    created_configs = []
    prepared_variants = []
    waiting_variants = []
    for variant in manifest["variants"]:
        variant_dir = args.manifest.parent / variant["id"]
        config_path = variant_dir / "review_config.json"
        write_json(config_path, variant_review_config(variant))
        created_configs.append(str(config_path))

        required = [
            variant_dir / "reports" / "responses.csv",
            variant_dir / "reports" / "rag_metrics_by_question.csv",
            variant_dir / "reports" / "rag_metrics_summary.json",
        ]
        if not all(path.exists() for path in required):
            waiting_variants.append(variant["id"])
            continue
        if args.scaffold_only:
            continue
        command = [
            sys.executable,
            str(SCRIPT_DIR / "01_prepare_review.py"),
            "--config",
            str(config_path),
        ]
        if args.force:
            command.append("--force")
        subprocess.run(command, check=True)
        prepared_variants.append(variant["id"])

    return {
        "suite_version": manifest.get("suite_version"),
        "variant_count": len(manifest["variants"]),
        "review_cases_per_reviewer": 80 * len(manifest["variants"]),
        "total_review_rows": 80 * len(manifest["variants"]) * 2,
        "created_configs": created_configs,
        "prepared_variants": prepared_variants,
        "waiting_for_baseline_results": waiting_variants,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold and prepare blinded Reviewer A/B packets for all four 80-case variants."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=SUITE_DIR / "baselines" / "manifest_master_80.json",
    )
    parser.add_argument("--scaffold-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    result = prepare(parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
