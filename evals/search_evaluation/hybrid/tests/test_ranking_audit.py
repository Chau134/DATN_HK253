import importlib.util
import json
from pathlib import Path
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    "ranking_audit", Path(__file__).resolve().parents[1] / "scripts/24_audit_ranking_loss.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.mark.parametrize("returned, expected_missing", [(["a", "b"], 0), (["b", "unknown"], 1)])
@pytest.mark.parametrize("with_admission", [False, True])
def test_decomposes_loss_without_modifying_judgments(tmp_path, monkeypatch, returned, expected_missing, with_admission):
    ground_truth = tmp_path / "gt.csv"
    ground_truth.write_text("frozen source", encoding="utf-8")
    output = tmp_path / "audit"
    gt = [{"query_id": "q", "relevant_product_id": p, "relevance_grade": str(g)} for p, g in [("a", 3), ("b", 1)]]
    results = [{"query_id": "q", "product_id": p, "rank": str(i)} for i, p in enumerate(returned, 1)]
    queries = [{"query_id": "q", "query_text": "cotton", "transformation_type": "material"}]
    admission = tmp_path / "admission.csv"
    admission.write_text("frozen audit", encoding="utf-8")
    def read(path):
        if path == admission:
            return [{"query_id": "q", "product_id": "a", "eligible": "False"}]
        return gt if path == ground_truth else results if path.name == "results.csv" else queries
    monkeypatch.setattr(audit.comparison, "read_csv", read)
    argv = ["audit", "--ground-truth", str(ground_truth), "--results", str(tmp_path / "results.csv"), "--output", str(output)]
    if with_admission:
        argv += ["--admission-audit", str(admission)]
    monkeypatch.setattr(sys, "argv", argv)
    audit.main()
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["actual_ndcg@5"] + summary["mean_ranking_gap"] + summary["mean_coverage_gap"] == pytest.approx(1)
    assert len((output / "judged_positive_not_returned.csv").read_text().splitlines()) == expected_missing + 1
    assert ground_truth.read_text() == "frozen source"
    assert summary["unjudged_top20"] == int("unknown" in returned)
    if with_admission:
        assert summary["known_rejected_judgments"] == 1
        assert summary["optimistic_fixed_gt_admission_ceiling@5"] == pytest.approx(audit.comparison.ndcg(["b"], {"a": 3, "b": 1}, 5))
    with pytest.raises(FileExistsError):
        audit.main()
