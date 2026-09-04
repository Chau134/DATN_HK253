from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "09_build_ground_truth_review.py"
SPEC = importlib.util.spec_from_file_location("image_ground_truth_review", SCRIPT_PATH)
assert SPEC and SPEC.loader
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)


def test_review_queue_keeps_labels_pending_and_adds_missing_source_product() -> None:
    rows = REVIEW.build_review_rows(
        [
            {
                "query_id": "q1",
                "source_product_id": "p-source",
                "category": "Dress",
                "color": "Black",
                "material": "Cotton",
                "gender": "Women",
                "image_url": "https://example.test/query.jpg",
                "difficulty": "hard",
            }
        ],
        [
            {"product_id": "p-source", "product_name": "Source", "category": "Dress"},
            {"product_id": "p-other", "product_name": "Other", "category": "Shirt"},
        ],
        [
            {
                "product_id": "p-source",
                "image_type": "MAIN",
                "sort_order": "0",
                "image_url": "https://example.test/source.jpg",
            },
            {
                "product_id": "p-other",
                "image_type": "MAIN",
                "sort_order": "0",
                "image_url": "https://example.test/other.jpg",
            },
        ],
        [{"query_id": "q1", "rank": "1", "product_id": "p-other", "score": "0.9"}],
        top_k=20,
    )

    assert len(rows) == 2
    assert all(row["review_status"] == "pending" for row in rows)
    assert all(row["relevance_grade"] == "" for row in rows)
    source = next(row for row in rows if row["candidate_product_id"] == "p-source")
    assert source["candidate_source"] == "source_product_not_retrieved"
    assert source["review_priority"] == "source_mapping_check"
    assert source["suggested_grade"] == 3


def test_product_image_preference_puts_main_before_other_views() -> None:
    images = REVIEW.product_images_by_id(
        [
            {"product_id": "p1", "image_type": "MODEL_2", "sort_order": "1", "image_url": "model.jpg"},
            {"product_id": "p1", "image_type": "DETAIL_1", "sort_order": "2", "image_url": "detail.jpg"},
            {"product_id": "p1", "image_type": "MAIN", "sort_order": "9", "image_url": "main.jpg"},
        ]
    )

    assert images["p1"] == ["main.jpg", "detail.jpg", "model.jpg"]
