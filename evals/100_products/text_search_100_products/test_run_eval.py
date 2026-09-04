import pytest

import run_eval
from run_eval import (
    acceptance_gates,
    build_advanced_cases,
    build_summary,
    first_acceptable_rank,
    ndcg_at_k,
    relevance_grades_for_case,
    smoke_check,
)


def test_advanced_cases_cover_four_transformations_and_group_duplicate_titles() -> None:
    products = [
        {"product_id": "1", "product_name_vi": "áo sơ mi satin hoa nữ"},
        {"product_id": "2", "product_name_vi": "đầm maxi cổ cao nữ"},
        {"product_id": "3", "product_name_vi": "áo thun in chữ tay dài nữ"},
        {"product_id": "4", "product_name_vi": "áo croptop chấm bi nữ"},
        {"product_id": "5", "product_name_vi": "áo sơ mi satin hoa nữ"},
    ]

    cases = build_advanced_cases(products)

    assert [case["test_type"] for case in cases[:4]] == [
        "accentless_title",
        "conversational_title",
        "reordered_keywords",
        "minor_typo",
    ]
    assert cases[0]["query_text"] == "ao so mi satin hoa nu"
    assert cases[1]["query_text"].startswith("mình muốn tìm đầm maxi cổ cao")
    assert cases[2]["query_text"] == "in chữ tay dài nữ áo thun"
    assert cases[3]["query_text"] == "áo crotop chấm bi"
    assert cases[0]["acceptable_product_ids"] == "1|5"
    assert cases[4]["acceptable_product_ids"] == "1|5"
    assert [case["query_id"] for case in cases[:4]] == [
        "accentless-title-product-1",
        "conversational-title-product-2",
        "reordered-keywords-product-3",
        "minor-typo-product-4",
    ]
    assert all(case["query_text"] != case["source_product_name_vi"] for case in cases)


def test_query_ids_follow_products_instead_of_snapshot_positions() -> None:
    products = [
        {"product_id": "900", "product_name_vi": "áo sơ mi linen nữ"},
        {"product_id": "42", "product_name_vi": "đầm midi cổ vuông nữ"},
    ]

    cases = build_advanced_cases(products)

    assert cases[0]["query_id"] == "accentless-title-product-900"
    assert cases[1]["query_id"] == "conversational-title-product-42"


def test_acceptable_rank_uses_equivalent_product_ids() -> None:
    case = {
        "expected_product_id": "1",
        "acceptable_product_ids": "1|5",
    }

    assert first_acceptable_rank(["9", "5", "1"], case) == 2
    assert first_acceptable_rank(["9", "8"], case) is None


def test_summary_reports_primary_and_per_type_robustness_metrics() -> None:
    def row(test_type: str, expected_rank: int | None, source_rank: int | None) -> dict:
        returned = [] if expected_rank is None else ["1", "2", "3", "4", "5"]
        return {
            "test_type": test_type,
            "status_code": 200,
            "expected_rank": expected_rank,
            "source_product_rank": source_rank,
            "latency_ms": 100.0,
            "warnings": [],
            "sources": ["text"] * len(returned),
            "returned_product_ids": returned,
            "has_duplicate_product_ids": False,
            "response": {},
        }

    results = [
        row("accentless_title", 1, 1),
        row("conversational_title", 2, 2),
        row("reordered_keywords", None, None),
        row("minor_typo", 5, None),
    ]

    summary = build_summary(results, top_k=5)

    assert summary["hit_rate_at_1"] == 0.25
    assert summary["hit_rate_at_5"] == 0.75
    assert summary["source_product_hit_rate_at_5"] == 0.5
    assert summary["miss_count"] == 1
    assert summary["metrics_by_test_type"]["minor_typo"]["hit_rate_at_5"] == 1.0
    assert summary["metrics_by_test_type"]["reordered_keywords"]["hit_rate_at_5"] == 0.0


def test_semantic_grades_support_relevant_alternatives_and_ndcg() -> None:
    case = {
        "query_id": "case-1",
        "expected_product_id": "1",
        "acceptable_product_ids": "1|2",
    }
    judgments = {
        "case-1": {
            "3": {"grade": 2, "review_status": "reviewed"},
            "4": {"grade": 0, "review_status": "reviewed"},
        }
    }

    grades = relevance_grades_for_case(case, judgments)

    assert grades == {"1": 3, "2": 3, "3": 2, "4": 0}
    assert ndcg_at_k(["3", "1", "4"], grades, 3) == pytest.approx(0.5741883268)


def test_smoke_check_requires_real_text_sources_without_fallback(monkeypatch) -> None:
    def fake_post(url: str, query: str, top_k: int, timeout: int):
        del query, top_k, timeout
        if "service-ai" in url:
            return 200, {"results": [{"product_id": "1", "source": "text"}]}, 10.0
        return 200, {
            "products": [{"product_id": "1", "ai_source": "text"}],
            "warnings": [],
        }, 20.0

    monkeypatch.setattr(run_eval, "post_search", fake_post)

    healthy = smoke_check(
        direct_url="http://service-ai/search/text",
        public_url="http://spring/api/search/ai/text",
        query="ao so mi",
        timeout=10,
    )
    assert healthy["valid"] is True

    def fallback_post(url: str, query: str, top_k: int, timeout: int):
        del url, query, top_k, timeout
        return 200, {
            "products": [{"product_id": "1", "ai_source": "keyword_fallback"}],
            "warnings": ["ai_service_unavailable", "ai_keyword_fallback"],
        }, 20.0

    monkeypatch.setattr(run_eval, "post_search", fallback_post)
    degraded = smoke_check(
        direct_url="http://service-ai/search/text",
        public_url="http://spring/api/search/ai/text",
        query="ao so mi",
        timeout=10,
    )
    assert degraded["valid"] is False


def test_acceptance_gate_requires_complete_semantic_ground_truth() -> None:
    summary = {
        "run_validity": "VALID",
        "query_count": 100,
        "http_success_count": 100,
        "ai_service_degraded_query_count": 0,
        "hit_rate_at_1": 0.98,
        "hit_rate_at_5": 1.0,
        "metrics_by_test_type": {
            "accentless_title": {"hit_rate_at_5": 1.0},
            "conversational_title": {"hit_rate_at_5": 1.0},
        },
        "empty_result_query_count": 0,
        "duplicate_result_query_count": 0,
        "p95_latency_ms": 1200,
        "semantic_ndcg_at_5": 0.95,
        "semantic_judgment_coverage_at_5": 0.99,
    }

    assert acceptance_gates(summary, 5) is False

    summary["semantic_judgment_coverage_at_5"] = 1.0
    assert acceptance_gates(summary, 5) is True

    summary["semantic_ndcg_at_5"] = 0.89
    assert acceptance_gates(summary, 5) is False
