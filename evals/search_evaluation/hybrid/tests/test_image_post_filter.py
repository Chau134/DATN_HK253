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
        "query_id": "q", "transformation_type": "color_material_price_usage",
        "query_text": "giống ảnh màu đỏ chất liệu cotton giá dưới 200k phù hợp đi làm",
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


def test_post_filter_does_not_apply_unrequested_fixture_columns() -> None:
    query = {
        "query_id": "q", "transformation_type": "color",
        "query_text": "tìm áo giống ảnh nhưng đổi sang màu đỏ",
        "category": "Áo thun", "color": "Đỏ", "material": "cotton",
        "price_bucket": "under_200k", "usage": "Đi làm",
    }
    products = {
        "right": {"category": "khác", "color": "Đỏ / Trắng", "material": "silk", "price": "900000", "usage": "du lịch"},
        "wrong": {"category": "Áo thun", "color": "xanh", "material": "cotton", "price": "100", "usage": "Đi làm"},
    }
    source = [{"rank": "1", "product_id": "right"}, {"rank": "2", "product_id": "wrong"}]
    assert [row["product_id"] for row in POST_FILTER.filter_image_results(query, products, source, candidate_pool_size=20)] == ["right"]


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
