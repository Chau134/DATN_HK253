import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from long_session_eval import (  # noqa: E402
    build_primary_turns,
    deterministic_run_id,
    correction_supersedes_old_value,
    has_unsupported_availability_claim,
    is_unsupported_availability_claim,
    summarize,
    write_reports,
)


def test_long_session_config_has_ten_twenty_turn_sessions() -> None:
    config_path = Path(__file__).resolve().parent / "configs" / "long_session_cases.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert len(config["sessions"]) == 10
    assert all(len(build_primary_turns(case)) == 20 for case in config["sessions"])
    assert deterministic_run_id(config) == deterministic_run_id(
        json.loads(config_path.read_text(encoding="utf-8"))
    )


def test_availability_guard_distinguishes_claim_from_grounded_refusal() -> None:
    assert has_unsupported_availability_claim("Mẫu này vẫn còn hàng.")
    assert not has_unsupported_availability_claim(
        "Mình chưa thể xác nhận còn hàng vì không có dữ liệu tồn kho."
    )
    assert not is_unsupported_availability_claim(
        "Mẫu này còn hàng.", product_ids=["42"], warnings=[]
    )
    assert is_unsupported_availability_claim(
        "Mẫu này còn hàng.", product_ids=[], warnings=["spring_boot_unavailable"]
    )


def test_correction_probe_distinguishes_current_color_from_abandoned_color() -> None:
    assert correction_supersedes_old_value(
        "Màu hiện tại là xanh, đã bỏ màu đen.",
        current_value="xanh",
        old_value="đen",
    )
    assert not correction_supersedes_old_value(
        "Màu mới là xám, đã bỏ màu đen và xanh.",
        current_value="xanh",
        old_value="đen",
    )


def test_summary_scores_each_memory_probe_and_latency_gate() -> None:
    probe_names = [
        "early_recall",
        "middle_recall",
        "recent_recall",
        "correction_supersedes_old_value",
        "reference_resolution",
        "cross_session_preference_recall",
        "session_isolation",
        "false_memory",
    ]
    rows = [
        {
            "turn_index": index + 1,
            "http_ok": True,
            "nonempty": True,
            "latency_seconds": 1.0,
            "unsupported_availability_claim": False,
            "probe_results": [{"name": name, "passed": True}],
        }
        for index, name in enumerate(probe_names)
    ]
    thresholds = {
        "min_completed_session_rate": 1.0,
        "min_early_recall": 0.95,
        "min_middle_recall": 0.95,
        "min_recent_recall": 0.95,
        "min_correction_supersedes_old_value": 1.0,
        "min_reference_resolution": 0.95,
        "min_cross_session_preference_recall": 0.95,
        "min_session_isolation": 1.0,
        "max_false_memory_rate": 0.0,
        "max_unsupported_availability_claim_rate": 0.0,
        "max_p95_latency_seconds": 30.0,
    }

    summary = summarize(
        rows,
        session_count=1,
        completed_sessions=1,
        thresholds=thresholds,
    )

    assert summary["acceptance_passed"]
    assert summary["metrics"]["false_memory_rate"] == 0.0


def test_reports_are_machine_readable_and_use_redacted_transcript_name(tmp_path) -> None:
    summary = {
        "run_id": "longmem-test",
        "session_statistics": [],
        "acceptance_passed": True,
    }
    rows = [
        {
            "case_id": "case",
            "session_id": "hashed",
            "turn_index": 1,
            "probe_results": [{"name": "early_recall", "passed": True, "checks": {}}],
        }
    ]

    output = write_reports(tmp_path, summary, rows)

    assert json.loads((output / "summary.json").read_text(encoding="utf-8"))["acceptance_passed"]
    assert (output / "transcript.redacted.jsonl").is_file()
    assert (output / "probe_results.jsonl").is_file()
    assert (output / "checkpoint_statistics.json").is_file()
