from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "07b_build_image_post_filter.py"
spec = importlib.util.spec_from_file_location("image_post_filter", SCRIPT)
assert spec and spec.loader
POST_FILTER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(POST_FILTER)


def test_post_filter_preserves_image_order_and_requires_all_constraints() -> None:
    query = {
        "category": "Áo thun", "color": "Đỏ", "material": "cotton",
        "price_bucket": "under_200k", "usage": "Đi làm",
    }
    products = {
        "p1": {"category": "ao thun", "color": "do", "material": "Cotton", "price": "199999", "usage": "di lam"},
        "p2": {"category": "ao thun", "color": "xanh", "material": "Cotton", "price": "199999", "usage": "di lam"},
        "p3": {"category": "Áo thun", "color": "Đỏ", "material": "cotton", "price": "100000", "usage": "Đi làm"},
    }
    source = [
        {"rank": "1", "product_id": "p1"},
        {"rank": "2", "product_id": "p2"},
        {"rank": "3", "product_id": "p3"},
    ]
    output = POST_FILTER.filter_image_results(query, products, source, candidate_pool_size=20)
    assert [row["product_id"] for row in output] == ["p1", "p3"]


def test_ground_truth_extension_reuses_only_approved_image_label() -> None:
    queries = {"hq1": {"source_image_query_id": "iq1"}}
    image_gt = [{
        "query_id": "iq1", "relevant_product_id": "p1", "relevance_grade": "2",
        "review_status": "approved", "source": "human", "notes": "reviewed",
    }]
    extended, additions = POST_FILTER.extend_ground_truth(queries, [], image_gt, [("hq1", "p1")])
    assert extended == additions
    assert additions[0]["relevance_grade"] == "2"
    assert additions[0]["source"] == "approved_image_ground_truth_transfer"


def test_ground_truth_extension_rejects_unreviewed_candidate() -> None:
    queries = {"hq1": {"source_image_query_id": "iq1"}}
    with pytest.raises(ValueError, match="no approved"):
        POST_FILTER.extend_ground_truth(queries, [], [], [("hq1", "missing")])
