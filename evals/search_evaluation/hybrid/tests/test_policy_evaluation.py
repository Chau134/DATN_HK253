import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "policy_eval", Path(__file__).resolve().parents[1] / "scripts/15_policy_evaluation.py"
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


@pytest.mark.parametrize("second", [
    {"query_id": "q", "product_id": "a", "rank": "2"},
    {"query_id": "q", "product_id": "b", "rank": "1"},
])
def test_duplicates_cannot_disappear_in_metric_deduplication(second):
    with pytest.raises(ValueError, match="Duplicate"):
        policy.validate_policy_results([{"query_id": "q", "product_id": "a", "rank": "1"}, second])


def test_same_product_in_different_queries_is_valid():
    policy.validate_policy_results([
        {"query_id": "q1", "product_id": "a", "rank": "1"},
        {"query_id": "q2", "product_id": "a", "rank": "1"},
    ])
