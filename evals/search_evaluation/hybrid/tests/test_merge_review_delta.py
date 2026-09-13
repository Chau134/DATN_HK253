import csv
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location("merge_delta", Path(__file__).resolve().parents[1] / "scripts/26_merge_review_delta.py")
merger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merger)


@pytest.fixture
def inputs(tmp_path):
    fields = ["query_id", "product_id", "query_text", *sorted(merger.MANUAL_FIELDS)]
    pool = [{**dict.fromkeys(fields, ""), "query_id": "q", "product_id": str(i), "query_text": "frozen"} for i in range(4)]
    review = [{**r, "manual_relevance_grade": str(i), "manual_constraint_status": "pass"} for i, r in enumerate(pool)]
    base = [{"query_id": "q", "mode": "multimodal", "query_type": "positive", "relevant_product_id": "old",
             "relevance_grade": "1", "match_reason": "keep", "source": "keep", "review_status": "approved", "notes": "keep"}]
    paths = {"reviewed_csv": tmp_path / "review.csv", "expected_pool": tmp_path / "pool.csv", "base_ground_truth": tmp_path / "base.csv", "output_dir": tmp_path / "out", "version": "v2"}
    for key, rows in [("reviewed_csv", review), ("expected_pool", pool), ("base_ground_truth", base)]:
        merger.write_csv(paths[key], rows, list(rows[0]))
    return paths


def test_preserves_all_grades_old_rows_and_raw_source(inputs):
    raw = inputs["reviewed_csv"].read_bytes()
    base_raw = inputs["base_ground_truth"].read_bytes()
    summary = merger.merge_delta(**inputs)
    _, _, gt = merger.read_table(inputs["output_dir"] / "ground_truth_multimodal_reviewed_v2.csv")
    assert [r["relevance_grade"] for r in gt] == ["1", "0", "1", "2", "3"]
    assert gt[0] == merger.read_table(inputs["base_ground_truth"])[2][0]
    assert (inputs["output_dir"] / "source_review.csv").read_bytes() == raw == inputs["reviewed_csv"].read_bytes()
    assert inputs["base_ground_truth"].read_bytes() == base_raw
    assert summary["grade_defaults_applied"] == 0 and not summary["reviewer_or_time_invented"]
    with pytest.raises(FileExistsError):
        merger.merge_delta(**inputs)


@pytest.mark.parametrize("change", ["blank_grade", "bad_grade", "blank_constraint", "duplicate", "missing", "unexpected", "changed_context", "old_pair", "fail_no_notes"])
def test_rejects_invalid_review_without_output(inputs, change):
    _, fields, rows = merger.read_table(inputs["reviewed_csv"])
    if change == "blank_grade": rows[0]["manual_relevance_grade"] = ""
    elif change == "bad_grade": rows[0]["manual_relevance_grade"] = "4"
    elif change == "blank_constraint": rows[0]["manual_constraint_status"] = ""
    elif change == "duplicate": rows.append(dict(rows[0]))
    elif change == "missing": rows.pop()
    elif change == "unexpected": rows[0]["product_id"] = "other"
    elif change == "changed_context": rows[0]["query_text"] = "changed"
    elif change == "fail_no_notes": rows[0]["manual_constraint_status"] = "fail"
    elif change == "old_pair":
        rows[0]["product_id"] = "old"
        _, pool_fields, pool = merger.read_table(inputs["expected_pool"])
        pool[0]["product_id"] = "old"
        merger.write_csv(inputs["expected_pool"], pool, pool_fields)
    merger.write_csv(inputs["reviewed_csv"], rows, fields)
    with pytest.raises(ValueError): merger.merge_delta(**inputs)
    assert not inputs["output_dir"].exists()


def test_constraint_fail_is_preserved_independently_of_grade(inputs):
    _, fields, rows = merger.read_table(inputs["reviewed_csv"])
    rows[0].update(manual_constraint_status="fail", manual_violation_fields="colors")
    merger.write_csv(inputs["reviewed_csv"], rows, fields)
    summary = merger.merge_delta(**inputs)
    assert summary["constraint_distribution"] == {"fail": 1, "pass": 3}


def test_explicit_override_precedes_blank_grade_default(inputs):
    _, fields, rows = merger.read_table(inputs["reviewed_csv"])
    rows[1]["manual_relevance_grade"] = ""
    rows[2]["manual_relevance_grade"] = ""
    merger.write_csv(inputs["reviewed_csv"], rows, fields)
    summary = merger.merge_delta(
        **inputs,
        fill_blank_grade="2",
        grade_override=[("q", "1", "1")],
    )
    _, _, gt = merger.read_table(inputs["output_dir"] / "ground_truth_multimodal_reviewed_v2.csv")
    assert [row["relevance_grade"] for row in gt] == ["1", "0", "1", "2", "3"]
    assert summary["grade_overrides_applied"] == 1
    assert summary["grade_defaults_applied"] == 1
