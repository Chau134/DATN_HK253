from io import BytesIO
import json
from pathlib import Path
import urllib.error

from run_eval import build_summary, extract_cases, health_snapshot, score_response


def test_extract_cases_pairs_search_names_with_main_images(tmp_path: Path) -> None:
    sql_path = tmp_path / "pilot.sql"
    sql_path.write_text(
        """
        INSERT INTO `product_images` VALUES
        (1,10,'MAIN','https://cdn.test/10-main.jpg',0,'2026-01-01'),
        (2,10,'DETAIL_1','https://cdn.test/10-detail.jpg',1,'2026-01-01'),
        (3,20,'FLAT_1','https://cdn.test/20-flat.jpg',4,'2026-01-01');
        INSERT INTO `product_search_documents` VALUES
        (1,10,'search_name_vi',NULL,'a','b','Áo sơ mi'),
        (2,20,'search_name_vi',NULL,'a','b','Quần jean');
        """,
        encoding="utf-8",
    )

    cases = extract_cases(sql_path, expected_count=2)

    assert [case["expected_product_id"] for case in cases] == ["10", "20"]
    assert cases[0]["image_url"] == "https://cdn.test/10-main.jpg"
    assert cases[1]["expected_product_name_vi"] == "Quần jean"
    assert cases[1]["image_type"] == "FLAT_1"


def test_score_and_summary_penalize_misses_and_detect_duplicates() -> None:
    case = {
        "case_id": "main-001",
        "expected_product_id": "10",
        "expected_product_name_vi": "Áo sơ mi",
        "image_url": "https://cdn.test/10.jpg",
        "image_type": "MAIN",
        "test_type": "catalog_preferred_image_identity",
    }
    hit = score_response(
        case,
        200,
        {
            "results": [
                {"product_id": "20", "score": 0.9},
                {"product_id": "10", "score": 0.8},
                {"product_id": "10", "score": 0.7},
            ],
            "detections": [{"is_fallback": True}],
        },
        5.0,
        100.0,
        False,
    )
    miss = {**hit, "case_id": "main-002", "expected_rank": None, "returned_product_ids": []}
    summary = build_summary(
        [hit, miss],
        5,
        {"readiness": {"body": {"capabilities": {"image_search": True}}}},
    )

    assert hit["expected_rank"] == 2
    assert hit["has_duplicate_product_ids"] is True
    assert summary["hit_rate_at_1"] == 0.0
    assert summary["hit_rate_at_3"] == 0.5
    assert summary["empty_result_query_count"] == 1
    assert summary["top1_score_tie_query_count"] == 0
    assert summary["acceptance_passed"] is False


def test_health_snapshot_preserves_http_503(monkeypatch) -> None:
    raw = json.dumps({"ready": False, "capabilities": {"image_search": False}}).encode()

    def fail(*args, **kwargs):
        del args, kwargs
        raise urllib.error.HTTPError("http://test/health", 503, "unavailable", {}, BytesIO(raw))

    monkeypatch.setattr("urllib.request.urlopen", fail)

    snapshot = health_snapshot("http://test/health", 5)

    assert snapshot["status_code"] == 503
    assert snapshot["body"]["capabilities"]["image_search"] is False
