from io import BytesIO
import json
from pathlib import Path
import urllib.error

from run_eval import (
    ADVANCED_TEST_TYPES,
    build_summary,
    build_query,
    extract_cases,
    health_snapshot,
    post_hybrid_search,
    score_response,
    service_config_snapshot,
)


def test_pilot_sql_produces_exactly_100_hybrid_cases() -> None:
    sql_path = Path(__file__).resolve().parents[2] / "database" / "100.sql"

    cases = extract_cases(sql_path)

    assert len(cases) == 100
    assert len({case["expected_product_id"] for case in cases}) == 100
    assert all(case["query_text"] and case["image_url"] for case in cases)
    assert {case["test_type"] for case in cases} == set(ADVANCED_TEST_TYPES)
    assert all(
        sum(case["test_type"] == test_type for case in cases) == 20
        for test_type in ADVANCED_TEST_TYPES
    )


def test_extract_cases_pairs_each_name_with_preferred_image(tmp_path: Path) -> None:
    sql_path = tmp_path / "pilot.sql"
    sql_path.write_text(
        """
        INSERT INTO `product_images` VALUES
        (1,10,'DETAIL_1','https://cdn.test/10-detail.jpg',1,'2026-01-01'),
        (2,10,'MAIN','https://cdn.test/10-main.jpg',2,'2026-01-01'),
        (3,20,'FLAT_1','https://cdn.test/20-flat.jpg',4,'2026-01-01');
        INSERT INTO `product_search_documents` VALUES
        (1,10,'search_name_vi',NULL,'a','b','Áo sơ mi'),
        (2,20,'search_name_vi',NULL,'a','b','Quần jean');
        """,
        encoding="utf-8",
    )

    cases = extract_cases(sql_path, expected_count=2)

    assert [case["expected_product_id"] for case in cases] == ["10", "20"]
    assert cases[0]["query_text"] == "Áo sơ mi"
    assert cases[0]["image_url"] == "https://cdn.test/10-main.jpg"
    assert cases[1]["image_type"] == "FLAT_1"
    assert cases[1]["query_text"] == "quan jean"


def test_advanced_query_builders_add_deterministic_text_noise() -> None:
    title = "Áo sơ mi satin hoa nữ"

    assert build_query("exact_title_aligned_image", title) == title
    assert build_query("accentless_title_aligned_image", title) == "ao so mi satin hoa nu"
    assert build_query("accentless_title_aligned_image", "Đầm đỏ") == "dam do"
    assert build_query("conversational_title_aligned_image", title).startswith(
        "mình muốn tìm Áo sơ mi satin hoa"
    )
    assert build_query("reordered_keywords_aligned_image", title) == "mi satin hoa Áo sơ"
    assert build_query("minor_typo_aligned_image", title) == "Áo sơ mi sain hoa"
    assert build_query("minor_typo_aligned_image", "áo hai dây cổ tim nút cài màu đen") != (
        "áo hai dây cổ tim nút cài màu đen"
    )


def test_post_hybrid_search_sends_text_image_and_weighted_strategy(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            return b'{"results":[]}'

    def open_request(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", open_request)

    status, _, _ = post_hybrid_search(
        "http://test/search/hybrid", "áo xanh", b"image", "image/jpeg", "x.jpg", 5, 10
    )

    payload = captured["payload"]
    assert status == 200
    assert payload["query"] == "áo xanh"
    assert payload["image"]["data_base64"] == "aW1hZ2U="
    assert payload["strategy"] == "weighted"
    assert payload["top_k"] == 5


def test_summary_requires_all_hybrid_capabilities_and_sources() -> None:
    case = {
        "case_id": "hybrid-001",
        "query_text": "Áo sơ mi",
        "expected_product_id": "10",
        "expected_product_name_vi": "Áo sơ mi",
        "image_url": "https://cdn.test/10.jpg",
        "image_type": "MAIN",
        "test_type": "exact_title_aligned_image",
    }
    hit = score_response(
        case,
        200,
        {"results": [{"product_id": "10", "score": 0.9, "source": "hybrid"}]},
        5.0,
        100.0,
        False,
        123,
    )
    miss = {
        **hit,
        "case_id": "hybrid-002",
        "expected_rank": None,
        "returned_product_ids": [],
        "sources": ["text"],
    }
    summary = build_summary(
        [hit, miss],
        5,
        {
            "readiness": {
                "body": {
                    "capabilities": {
                        "text_search": True,
                        "image_search": True,
                        "assistant_llm": True,
                    }
                }
            }
        },
    )

    assert hit["expected_rank"] == 1
    assert summary["hybrid_capability_ready"] is True
    assert summary["hit_rate_at_1"] == 0.5
    assert summary["empty_result_query_count"] == 1
    assert summary["non_hybrid_source_query_count"] == 1
    assert summary["result_count_distribution"] == {"1": 1, "0": 1}
    assert summary["expected_rank_distribution"] == {"1": 1, "miss": 1}
    assert summary["breakdowns"]["image_type"]["MAIN"]["query_count"] == 2
    assert summary["breakdowns"]["test_type"]["exact_title_aligned_image"]["hit_rate_at_1"] == 0.5
    assert summary["acceptance_passed"] is False


def test_summary_accepts_complete_balanced_advanced_suite() -> None:
    results = []
    for index in range(100):
        test_type = ADVANCED_TEST_TYPES[index % len(ADVANCED_TEST_TYPES)]
        case = {
            "case_id": f"hybrid-{index + 1:03d}",
            "query_text": "query",
            "source_product_name_vi": "Sản phẩm",
            "expected_product_id": str(index + 1),
            "expected_product_name_vi": "Sản phẩm",
            "image_url": f"https://cdn.test/{index + 1}.jpg",
            "image_type": "MAIN",
            "test_type": test_type,
        }
        results.append(
            score_response(
                case,
                200,
                {
                    "results": [
                        {
                            "product_id": str(index + 1),
                            "score": 0.9,
                            "source": "hybrid",
                        }
                    ]
                },
                0.0,
                100.0,
                True,
            )
        )

    summary = build_summary(
        results,
        5,
        {
            "readiness": {
                "body": {
                    "capabilities": {
                        "text_search": True,
                        "image_search": True,
                        "assistant_llm": True,
                    }
                }
            }
        },
    )

    assert summary["acceptance_gates"]["all_advanced_test_types_have_20_cases"] is True
    assert summary["acceptance_gates"]["each_test_type_hit_at_5_at_least_95_percent"] is True
    assert summary["acceptance_passed"] is True


def test_service_config_snapshot_excludes_secrets(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "QDRANT_TEXT_COLLECTION=text-v5\n"
        "HYBRID_CANDIDATE_POOL_SIZE=50\n"
        "QDRANT_API_KEY=do-not-record\n"
        "COHERE_API_KEY=do-not-record\n",
        encoding="utf-8",
    )

    snapshot = service_config_snapshot(env_path)

    assert snapshot == {
        "QDRANT_TEXT_COLLECTION": "text-v5",
        "HYBRID_CANDIDATE_POOL_SIZE": "50",
    }


def test_health_snapshot_preserves_http_503(monkeypatch) -> None:
    raw = json.dumps({"ready": False, "capabilities": {"image_search": False}}).encode()

    def fail(*args, **kwargs):
        del args, kwargs
        raise urllib.error.HTTPError("http://test/health", 503, "unavailable", {}, BytesIO(raw))

    monkeypatch.setattr("urllib.request.urlopen", fail)

    snapshot = health_snapshot("http://test/health", 5)

    assert snapshot["status_code"] == 503
    assert snapshot["body"]["capabilities"]["image_search"] is False
