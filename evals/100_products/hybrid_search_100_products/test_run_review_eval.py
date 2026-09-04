from pathlib import Path

import pytest

import run_review_eval
from run_review_eval import (
    approved_ids,
    build_summary,
    ndcg_at_k,
    run_case,
    validate_runnable_cases,
)


def test_approved_ids_are_deduplicated_in_manifest_order() -> None:
    assert approved_ids({"approved_product_ids": "10|20|10||30"}) == [
        "10",
        "20",
        "30",
    ]


def test_ndcg_uses_reviewed_relevance_grades() -> None:
    assert ndcg_at_k(["high", "medium"], {"high": 3, "medium": 2}, 5) == 1.0
    assert ndcg_at_k(["medium", "high"], {"high": 3, "medium": 2}, 5) < 1.0


def test_validate_runnable_cases_rejects_unapproved_and_external_ground_truth() -> None:
    with pytest.raises(RuntimeError, match="review_status must be APPROVED"):
        validate_runnable_cases(
            [
                {
                    "case_id": "case-1",
                    "test_group": "available-image",
                    "review_status": "PENDING",
                    "external_image_url": "https://example.test/image.jpg",
                    "approved_product_ids": "999",
                }
            ],
            {"1"},
        )


def test_run_case_scores_first_approved_id_after_result_dedupe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        run_review_eval,
        "load_image",
        lambda *args, **kwargs: (b"image", "image/jpeg", 1.0, True),
    )
    monkeypatch.setattr(
        run_review_eval,
        "post_hybrid_search",
        lambda *args, **kwargs: (
            200,
            {
                "explicit_filters": {"category": "blouse", "material": "viscose"},
                "relaxed_filters": [],
                "results": [
                    {
                        "product_id": "9",
                        "score": 0.9,
                        "source": "hybrid",
                        "explicit_constraint_satisfaction": {
                            "category": True,
                            "material": True,
                        },
                    },
                    {
                        "product_id": "9",
                        "score": 0.8,
                        "source": "hybrid",
                        "explicit_constraint_satisfaction": {
                            "category": True,
                            "material": True,
                        },
                    },
                    {
                        "product_id": "20",
                        "score": 0.7,
                        "source": "hybrid",
                        "explicit_constraint_satisfaction": {
                            "category": True,
                            "material": True,
                        },
                    },
                ]
            },
            10.0,
        ),
    )
    case = {
        "case_id": "case-1",
        "test_group": "external-image",
        "test_type": "similar_style_external_image",
        "query_text": "tìm áo giống ảnh",
        "external_image_url": "https://example.test/image.jpg",
        "image_source_product_id": "1",
        "approved_product_ids": "10|20",
        "candidate_product_ids": "9|20",
        "approved_grades": {"20": 3},
    }

    result = run_case(
        case,
        endpoint="http://test/search/hybrid",
        cache_dir=tmp_path,
        top_k=5,
        timeout=10,
        download_timeout=10,
        force_download=False,
        valid_product_ids={"9", "20"},
    )

    assert result["returned_product_ids_raw"] == ["9", "9", "20"]
    assert result["returned_product_ids"] == ["9", "20"]
    assert result["acceptable_rank"] == 2
    assert result["has_duplicate_product_ids"] is True
    assert result["outside_snapshot_product_ids"] == []
    assert result["metadata_candidate_rank"] == 1
    assert result["ndcg_at_5"] > 0
    assert result["constraint_satisfaction"]["material"]["at_5"] is True


def test_summary_reports_breakdown_and_latency() -> None:
    rows = [
        {
            "test_type": "different_color",
            "test_group": "different-color",
            "status_code": 200,
            "acceptable_rank": 1,
            "returned_product_ids": ["1"],
            "has_duplicate_product_ids": False,
            "sources": ["hybrid"],
            "search_latency_ms": 100.0,
            "case_id": "a",
        },
        {
            "test_type": "different_color",
            "test_group": "different-color",
            "status_code": 500,
            "acceptable_rank": None,
            "returned_product_ids": [],
            "has_duplicate_product_ids": False,
            "sources": [],
            "search_latency_ms": 200.0,
            "case_id": "b",
        },
    ]

    summary = build_summary(
        rows,
        top_k=5,
        run_context={"run_id": "test"},
        valid_product_ids={"1"},
    )

    assert summary["http_success_count"] == 1
    assert summary["hit_rate_at_1"] == 0.5
    assert summary["metrics_by_test_group"]["different-color"]["miss_count"] == 1
    assert summary["p95_search_latency_ms"] == 100.0
    assert summary["outside_snapshot_query_count"] == 0


def test_summary_reports_products_outside_snapshot() -> None:
    rows = [
        {
            "test_type": "similar_style_external_image",
            "test_group": "external-image",
            "status_code": 200,
            "acceptable_rank": 1,
            "returned_product_ids": ["1", "999"],
            "has_duplicate_product_ids": False,
            "sources": ["hybrid"],
            "search_latency_ms": 100.0,
            "case_id": "case-outside",
        }
    ]

    summary = build_summary(
        rows,
        top_k=5,
        run_context={"run_id": "test"},
        valid_product_ids={"1"},
    )

    assert summary["outside_snapshot_query_count"] == 1
    assert summary["outside_snapshot_product_ids"] == ["999"]
    assert summary["outside_snapshot_cases"] == {"case-outside": ["999"]}
