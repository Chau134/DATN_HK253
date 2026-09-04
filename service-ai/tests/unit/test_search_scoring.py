from types import SimpleNamespace

import pytest

from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.schemas.media import ImagePayload
from ecommerce_search_assistant.schemas.search import (
    HybridSearchRequest,
    ImageDetectionRequest,
    ImageSearchRequest,
    SearchFilter,
    TextSearchRequest,
)
from ecommerce_search_assistant.services.cropping.yolo import CropResult
from ecommerce_search_assistant.services.search.constraints import resolve_search_constraints
from ecommerce_search_assistant.services.search.service import (
    SearchService,
    _Candidate,
    _ScoredPoint,
    _business_signal,
    _image_payload_to_pil,
    _image_per_crop_limit,
    _image_score_boost,
    _hybrid_candidate_limit,
    _lexical_score_components,
    _rank_points_by_detected_category,
    _text_score_boost,
    _text_score_components,
)


class _ReversingRerankService:
    """Scores documents so their order is exactly reversed, for deterministic assertions."""

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        return [float(index) for index in range(1, len(documents) + 1)]

    def warmup(self) -> None:
        return None


class _FailingRerankService:
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        raise RuntimeError("reranker unavailable")

    def warmup(self) -> None:
        return None


class _RecordingRerankService:
    def __init__(self) -> None:
        self.documents: list[str] = []

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        del query
        self.documents = list(documents)
        return [float(index) for index in range(len(documents))]

    def warmup(self) -> None:
        return None


def _enable_rerank(service: SearchService, rerank_service: object) -> SearchService:
    service.settings = service.settings.model_copy(update={"rerank_enabled": True})
    service.rerank_service = rerank_service  # type: ignore[assignment]
    return service


def test_hybrid_score_merge_uses_configured_weights(settings: Settings) -> None:
    service = object.__new__(SearchService)
    service.settings = settings

    score = SearchService._hybrid_score(
        service,
        _Candidate(product_id="P-1", text_similarity=0.8, image_similarity=0.6),
        SearchFilter(category="hoodie"),
    )

    # Category is a hard Qdrant constraint, so it no longer adds a constant score.
    assert score == pytest.approx(0.55)


def test_hybrid_score_adds_business_signal(settings: Settings) -> None:
    service = object.__new__(SearchService)
    service.settings = settings

    score = SearchService._hybrid_score(
        service,
        _Candidate(
            product_id="P-1",
            text_similarity=0.8,
            image_similarity=0.6,
            payload={
                "available": True,
                "inventory_count": 5,
            },
        ),
        SearchFilter(category="hoodie"),
    )

    assert score == pytest.approx(0.60)


def test_hybrid_score_boosts_exact_use_case(settings: Settings) -> None:
    service = object.__new__(SearchService)
    service.settings = settings

    score = SearchService._hybrid_score(
        service,
        _Candidate(
            product_id="P-1",
            text_similarity=0.8,
            image_similarity=0.6,
            payload={"use_case_keys": ["office"]},
        ),
        SearchFilter(use_cases=["office"]),
    )

    assert score == pytest.approx(0.55 + settings.hybrid_use_case_boost_weight)


def test_hybrid_score_scales_use_case_boost_by_overlap(settings: Settings) -> None:
    service = object.__new__(SearchService)
    service.settings = settings

    score = SearchService._hybrid_score(
        service,
        _Candidate(
            product_id="P-1",
            text_similarity=0.8,
            image_similarity=0.6,
            payload={"use_case_keys": ["office"]},
        ),
        SearchFilter(use_cases=["office", "event"]),
    )

    assert score == pytest.approx(0.55 + settings.hybrid_use_case_boost_weight / 2)


def test_hybrid_can_restore_binary_use_case_boost_through_config(settings: Settings) -> None:
    service = object.__new__(SearchService)
    service.settings = settings.model_copy(
        update={"hybrid_use_case_overlap_boost_enabled": False}
    )

    score = SearchService._hybrid_score(
        service,
        _Candidate(
            product_id="P-1",
            text_similarity=0.8,
            image_similarity=0.6,
            payload={"use_case_keys": ["office"]},
        ),
        SearchFilter(use_cases=["office", "event"]),
    )

    assert score == pytest.approx(0.55 + settings.hybrid_use_case_boost_weight)


def test_hybrid_candidate_limit_overfetches_without_changing_public_top_k(
    settings: Settings,
) -> None:
    tuned = settings.model_copy(
        update={
            "hybrid_candidate_pool_size": 50,
            "hybrid_product_overfetch_factor": 4,
            "hybrid_candidate_pool_cap": 100,
            "rerank_enabled": False,
        }
    )

    assert _hybrid_candidate_limit(20, tuned) == 80
    assert _hybrid_candidate_limit(100, tuned) == 100

def test_hybrid_filter_weight_uses_per_candidate_soft_match_ratio(settings: Settings) -> None:
    service = object.__new__(SearchService)
    service.settings = settings.model_copy(update={"hybrid_soft_attribute_boost_enabled": True})

    fully_matched = SearchService._hybrid_score(
        service,
        _Candidate(
            product_id="P-1",
            text_similarity=0.8,
            image_similarity=0.6,
            payload={
                "category_keys": ["hoodie"],
                "color_keys": ["black"],
                "audience_keys": ["women"],
            },
        ),
        SearchFilter(category="hoodie", colors=["black"], gender="women"),
    )
    color_only = SearchService._hybrid_score(
        service,
        _Candidate(
            product_id="P-2",
            text_similarity=0.8,
            image_similarity=0.6,
            payload={
                "category_keys": ["hoodie"],
                "color_keys": ["black"],
                "audience_keys": ["men"],
            },
        ),
        SearchFilter(category="hoodie", colors=["black"], gender="women"),
    )

    assert fully_matched == pytest.approx(0.55 + settings.hybrid_filter_weight)
    assert color_only == pytest.approx(
        0.55 + settings.hybrid_filter_weight * 2 / 3
    )
    assert fully_matched > color_only


def test_hybrid_literal_category_and_color_are_hard_for_both_modalities(
    search_service: SearchService,
    fake_qdrant_client,
    fake_llm_service,
    image_payload: dict[str, str],
) -> None:
    response = search_service.search_hybrid(
        HybridSearchRequest(
            query="tìm hoodie giống ảnh nhưng màu đen",
            image=ImagePayload(**image_payload),
        )
    )

    assert response.results
    assert response.filters and response.filters.category == "hoodie"
    assert response.explicit_filters == SearchFilter(
        category="hoodie",
        colors=["black"],
    )
    assert all(
        result.explicit_constraint_satisfied is True
        for result in response.results
    )
    assert fake_llm_service.analyze_calls == []
    for query in fake_qdrant_client.queries:
        if "query_filter" in query:
            assert [condition.key for condition in query["query_filter"].must] == [
                "active",
                "category_keys",
                "color_keys",
            ]


def test_hybrid_context_reference_does_not_filter_image_candidates_as_dresses(
    search_service: SearchService,
    fake_qdrant_client,
    image_payload: dict[str, str],
) -> None:
    response = search_service.search_hybrid(
        HybridSearchRequest(
            query="tìm kiểu giống vậy",
            image=ImagePayload(**image_payload),
        )
    )

    assert response.results
    assert response.explicit_filters is None
    assert "P-IMAGE" in response.product_ids
    for query in fake_qdrant_client.queries:
        if "query_filter" in query:
            assert [condition.key for condition in query["query_filter"].must] == [
                "active",
            ]


def test_hybrid_explicit_material_stays_hard_for_both_modalities(
    search_service: SearchService,
    fake_qdrant_client,
    image_payload: dict[str, str],
) -> None:
    search_service.search_hybrid(
        HybridSearchRequest(
            query="black hoodie",
            image=ImagePayload(**image_payload),
            filters=SearchFilter(material="leather"),
        )
    )

    for query in fake_qdrant_client.queries:
        if "query_filter" in query:
            assert [condition.key for condition in query["query_filter"].must] == [
                "active",
                "category_keys",
                "color_keys",
                "material_keys",
            ]


def test_hybrid_exact_original_title_is_unioned_before_ranking(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        is_exact_lookup = bool(kwargs["query_filter"].should)
        product_id = "P-EXACT" if is_exact_lookup else "P-VECTOR"
        score = 0.10 if is_exact_lookup else 0.95
        title = "ao khoac da nam" if is_exact_lookup else "san pham khac"
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    payload={
                        "product_id": product_id,
                        "normalized_title_vi": title,
                        "embedding_text": title,
                    },
                    score=score,
                )
            ]
        )

    fake_qdrant_client.query_points = query_points

    response = search_service.search_hybrid_prepared(
        rewritten_query="mens leather jacket",
        original_query="Áo khoác da nam",
        image=None,
        crop_box=None,
        filters=None,
    )

    assert response.product_ids[0] == "P-EXACT"
    assert fake_qdrant_client.queries[-1]["limit"] == search_service.settings.hybrid_candidate_pool_size


def test_detect_image_returns_crop_boxes(search_service: SearchService, image_payload: dict[str, str]) -> None:
    response = search_service.detect_image(ImageDetectionRequest(image=ImagePayload(**image_payload)))

    assert response.image_width == 8
    assert response.image_height == 8
    assert response.detections[0].bbox.left == 0
    assert response.detections[0].bbox.right == 8


def test_image_search_uses_user_crop_box(search_service: SearchService, image_payload: dict[str, str]) -> None:
    request = ImageSearchRequest(
        image=ImagePayload(**image_payload),
        crop_box={"left": 1, "top": 2, "right": 7, "bottom": 6},
    )

    response = search_service.search_image(request)

    assert response.product_ids == ["P-IMAGE", "P-SHARED"]
    assert response.detections[0].bbox.left == 1
    assert response.detections[0].bbox.top == 2
    assert response.detections[0].bbox.right == 7
    assert response.detections[0].bbox.bottom == 6


def test_image_decode_rejects_images_below_min_dimensions(
    settings: Settings,
    image_payload: dict[str, str],
) -> None:
    settings = settings.model_copy(update={"image_min_width": 16, "image_min_height": 16})

    with pytest.raises(ValueError, match="image dimensions"):
        _image_payload_to_pil(ImagePayload(**image_payload), settings)


def test_image_per_crop_limit_scales_down_multi_crop_queries(settings: Settings) -> None:
    settings = settings.model_copy(
        update={
            "image_candidate_pool_size": 20,
            "image_product_overfetch_factor": 1,
            "image_query_per_crop_limit_cap": 50,
        }
    )

    assert _image_per_crop_limit(limit=50, crop_count=3, settings=settings) == 34


def test_image_candidate_pool_is_independent_from_rerank_top_k(settings: Settings) -> None:
    settings = settings.model_copy(
        update={
            "image_candidate_pool_size": 20,
            "image_product_overfetch_factor": 1,
            "image_query_per_crop_limit_cap": 50,
            "rerank_top_k": 999,
        }
    )

    assert _image_per_crop_limit(limit=5, crop_count=1, settings=settings) == 20
    assert _image_per_crop_limit(limit=5, crop_count=3, settings=settings) == 14


def test_image_candidate_pool_overfetches_before_product_dedupe(settings: Settings) -> None:
    settings = settings.model_copy(
        update={
            "image_candidate_pool_size": 20,
            "image_product_overfetch_factor": 4,
            "image_query_per_crop_limit_cap": 100,
        }
    )

    assert _image_per_crop_limit(limit=20, crop_count=1, settings=settings) == 80
    assert _image_per_crop_limit(limit=20, crop_count=2, settings=settings) == 80


def test_image_search_refills_when_points_collapse_to_too_few_products(
    search_service: SearchService,
    fake_qdrant_client,
    image_payload: dict[str, str],
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={
            "image_candidate_pool_size": 5,
            "image_product_overfetch_factor": 1,
            "image_query_per_crop_limit_cap": 8,
        }
    )

    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        product_ids = (
            ["P1", "P1", "P2", "P2", "P2"]
            if kwargs["limit"] == 5
            else ["P1", "P1", "P2", "P2", "P3", "P4", "P5", "P6"]
        )
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    payload={"product_id": product_id},
                    score=1.0 - index / 100,
                )
                for index, product_id in enumerate(product_ids)
            ]
        )

    fake_qdrant_client.query_points = query_points
    response = search_service.search_image(
        ImageSearchRequest(image=ImagePayload(**image_payload), top_k=5)
    )

    assert response.product_ids == ["P1", "P2", "P3", "P4", "P5"]
    assert [query["limit"] for query in fake_qdrant_client.queries] == [5, 8]


def test_image_search_stops_refill_when_collection_is_exhausted(
    search_service: SearchService,
    fake_qdrant_client,
    image_payload: dict[str, str],
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={
            "image_candidate_pool_size": 5,
            "image_product_overfetch_factor": 1,
            "image_query_per_crop_limit_cap": 20,
        }
    )

    response = search_service.search_image(
        ImageSearchRequest(image=ImagePayload(**image_payload), top_k=5)
    )

    assert response.product_ids == ["P-IMAGE", "P-SHARED"]
    assert [query["limit"] for query in fake_qdrant_client.queries] == [5]


def test_image_search_stops_refill_at_per_crop_cap(
    search_service: SearchService,
    fake_qdrant_client,
    image_payload: dict[str, str],
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={
            "image_candidate_pool_size": 5,
            "image_product_overfetch_factor": 1,
            "image_query_per_crop_limit_cap": 8,
        }
    )

    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        return SimpleNamespace(
            points=[
                SimpleNamespace(payload={"product_id": f"P{index % 2}"}, score=1.0)
                for index in range(kwargs["limit"])
            ]
        )

    fake_qdrant_client.query_points = query_points
    response = search_service.search_image(
        ImageSearchRequest(image=ImagePayload(**image_payload), top_k=5)
    )

    assert response.product_ids == ["P0", "P1"]
    assert [query["limit"] for query in fake_qdrant_client.queries] == [5, 8]


def test_image_score_boost_adds_filter_and_business_signals(settings: Settings) -> None:
    settings = settings.model_copy(update={"image_business_boost_enabled": True})
    payload = {
        "category_names": ["Running Shoes"],
        "base_colour": "black",
        "available": True,
        "inventory_count": 3,
    }

    boost = _image_score_boost(payload, SearchFilter(category="shoes", colors=["black"]), settings)

    assert boost == pytest.approx(0.01 + 0.01 + settings.image_business_boost_weight)


def test_text_search_uses_rewritten_query_and_qdrant_filter(search_service: SearchService, fake_qdrant_client) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={
            "text_llm_fast_path_enabled": False,
            "text_out_of_catalog_rejection_enabled": False,
            "text_trusted_color_hard_filter_enabled": True,
        }
    )
    response = search_service.search_text(
        TextSearchRequest(query="áo thun đen dưới 300k")
    )

    assert response.rewritten_query == "rewritten áo thun đen dưới 300k"
    # The catalog snapshot has no product below this budget, so validation drops
    # the impossible hard price filter before querying Qdrant.
    assert response.filters == SearchFilter(category="tshirt", colors=["black"])
    product_queries = [query for query in fake_qdrant_client.queries if "query_filter" in query]
    assert product_queries
    assert all(
        query["query"] != search_service.text_embedding_service.embed_text("áo thun đen dưới 300k")
        for query in product_queries
    )
    # Exact-title lookup bypasses inferred category/color constraints.
    exact_query = product_queries[0]
    assert exact_query["query_filter"].should
    assert [condition.key for condition in exact_query["query_filter"].must] == ["active"]
    vector_queries = [query for query in product_queries if not query["query_filter"].should]
    assert vector_queries
    # Trusted category and color phrases remain hard even when the fake result
    # set is thin. Recovery must not admit unrelated products merely to fill
    # top_k.
    assert all(
        [condition.key for condition in query["query_filter"].must]
        == ["active", "category_keys", "color_keys"]
        for query in vector_queries
    )


def test_text_search_rejects_invalid_catalog_constraint_before_llm_and_qdrant(
    search_service: SearchService,
    fake_qdrant_client,
    fake_llm_service,
) -> None:
    response = search_service.search_text(
        TextSearchRequest(query="áo thun đen dưới 300k")
    )

    assert response.results == []
    assert fake_llm_service.analyze_calls == []
    assert all(query.get("scroll") is True for query in fake_qdrant_client.queries)


@pytest.mark.parametrize(
    "query",
    [
        "vay cuoi dinh kim cuong chong nuoc",
        "giay truot tuyet mau bac cho mua he",
        "ao so mi kim loai chong dan",
    ],
)
def test_text_search_rejects_infeasible_catalog_request_before_llm_and_qdrant(
    query: str,
    search_service: SearchService,
    fake_qdrant_client,
    fake_llm_service,
) -> None:
    response = search_service.search_text(TextSearchRequest(query=query))

    assert response.results == []
    assert fake_llm_service.analyze_calls == []
    assert all(call.get("scroll") is True for call in fake_qdrant_client.queries)


@pytest.mark.parametrize(
    "query",
    ["ao khoac chong nuoc", "ao chong nang"],
)
def test_text_search_feasibility_check_preserves_supported_product_language(
    query: str,
    search_service: SearchService,
) -> None:
    response = search_service.search_text(TextSearchRequest(query=query))

    assert response.results


def test_text_search_keeps_catalog_title_when_only_inferred_attribute_is_invalid(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    fake_qdrant_client.scroll = lambda *args, **kwargs: (
        [
            SimpleNamespace(
                payload={
                    "active": True,
                    "category_keys": ["blouse"],
                    "color_keys": ["light beige"],
                    "normalized_title_vi": "ao blouse soc co vest be nhat",
                    "selling_price": 500000,
                }
            )
        ],
        None,
    )

    response = search_service.search_text(
        TextSearchRequest(query="áo blouse sọc cổ vest be nhạt")
    )

    assert response.product_ids == ["P-TEXT", "P-SHARED"]


def test_text_search_fast_path_skips_llm_for_catalog_query(
    search_service: SearchService,
    fake_llm_service,
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={"text_out_of_catalog_rejection_enabled": False}
    )
    response = search_service.search_text(
        TextSearchRequest(query="ao so mi satin hoa nu")
    )

    assert response.product_ids == ["P-TEXT", "P-SHARED"]
    assert fake_llm_service.analyze_calls == []
    assert response.rewritten_query


def test_text_search_keeps_llm_for_vague_query(
    search_service: SearchService,
    fake_llm_service,
) -> None:
    search_service.search_text(TextSearchRequest(query="tìm đồ phù hợp"))

    assert fake_llm_service.analyze_calls == [("tìm đồ phù hợp", "vi-VN")]


def test_text_search_keeps_explicit_request_filter_hard(search_service: SearchService, fake_qdrant_client) -> None:
    search_service.search_text(
        TextSearchRequest(query="áo khoác da nam", filters=SearchFilter(material="leather"))
    )

    keys = [condition.key for condition in fake_qdrant_client.queries[-1]["query_filter"].must]
    assert keys == ["active", "category_keys", "material_keys"]


def test_text_search_keeps_broad_long_pants_category_for_black_budget_query(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={"text_lexical_fusion_enabled": False}
    )

    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        keys = [condition.key for condition in kwargs["query_filter"].must]
        candidates = (
            [
                ("P-LEGGINGS", 0.88, "quan legging cap cao mau den", ["leggings"]),
                ("P-PANTS", 0.82, "quan dai ong rong mau den", ["pants"]),
            ]
            if "category_keys" in keys
            else [
                ("P-BODYSUIT", 0.98, "bodysuit bandeau co gian mau den", ["bodysuit"]),
                ("P-BLOUSE", 0.96, "ao kieu co cheo xep ly tay dai mau den", ["blouse"]),
            ]
        )
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    payload={
                        "product_id": product_id,
                        "normalized_title_vi": title,
                        "normalized_title_tokens": title.split(),
                        "category_keys": category_keys,
                        "color_keys": ["black"],
                        "selling_price": 900000,
                    },
                    score=score,
                )
                for product_id, score, title, category_keys in candidates
            ]
        )

    fake_qdrant_client.query_points = query_points
    constraints = resolve_search_constraints(
        rule_filters=SearchFilter(
            category="long_pants",
            colors=["black"],
            max_price=1000000,
        ),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.97, "color": 0.95, "price": 0.92},
        match_sources={"category": "alias", "color": "dictionary", "price": "regex"},
        allow_category_hard=True,
    )

    response, timings = search_service.search_text_prepared(
        rewritten_query="quần dài màu đen giá dưới 1 triệu",
        filters=constraints.response_filters,
        constraints=constraints,
    )

    assert response.product_ids == ["P-LEGGINGS", "P-PANTS"]
    assert timings["recovery_triggered"] == 0.0
    product_queries = [query for query in fake_qdrant_client.queries if "query_filter" in query]
    assert product_queries
    assert all(
        "category_keys" in [condition.key for condition in query["query_filter"].must]
        for query in product_queries
    )
    category_conditions = [
        condition
        for condition in product_queries[0]["query_filter"].must
        if condition.key == "category_keys"
    ]
    assert set(category_conditions[0].match.any) >= {"pants", "jeans", "leggings", "sweatpants"}


def test_text_search_filters_generic_winter_top_query_to_warm_categories(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={"text_lexical_fusion_enabled": False}
    )

    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        keys = [condition.key for condition in kwargs["query_filter"].must]
        candidates = (
            [
                ("P-JACKET", 0.89, "ao khoac da lon co cao", ["jacket"]),
                ("P-HOODIE", 0.86, "ao hoodie ni co mu", ["hoodie"]),
                ("P-SWEATER", 0.83, "ao len co tron tay dai", ["sweater"]),
            ]
            if "category_keys" in keys
            else [
                ("P-BODYSUIT", 0.98, "bodysuit bandeau co gian", ["bodysuit"]),
                ("P-BLOUSE", 0.96, "ao blouse mong tay dai", ["blouse"]),
            ]
        )
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    payload={
                        "product_id": product_id,
                        "normalized_title_vi": title,
                        "normalized_title_tokens": title.split(),
                        "category_keys": category_keys,
                    },
                    score=score,
                )
                for product_id, score, title, category_keys in candidates
            ]
        )

    fake_qdrant_client.query_points = query_points
    constraints = resolve_search_constraints(
        rule_filters=SearchFilter(category="winter_outerwear"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.97},
        match_sources={"category": "alias"},
        allow_category_hard=True,
    )

    response, timings = search_service.search_text_prepared(
        rewritten_query="áo mặc mùa đông",
        filters=constraints.response_filters,
        constraints=constraints,
    )

    assert response.product_ids == ["P-JACKET", "P-HOODIE", "P-SWEATER"]
    assert timings["recovery_triggered"] == 0.0
    product_queries = [query for query in fake_qdrant_client.queries if "query_filter" in query]
    category_condition = next(
        condition
        for condition in product_queries[0]["query_filter"].must
        if condition.key == "category_keys"
    )
    assert set(category_condition.match.any) >= {
        "jacket",
        "coat",
        "hoodie",
        "sweatshirt",
        "sweater",
        "cardigan",
    }


def test_text_search_filters_generic_work_top_query_to_office_categories(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={"text_lexical_fusion_enabled": False}
    )

    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        keys = [condition.key for condition in kwargs["query_filter"].must]
        candidates = (
            [
                ("P-SHIRT", 0.90, "ao so mi satin cong so", ["shirt"]),
                ("P-BLOUSE", 0.87, "ao blouse co vest di lam", ["blouse"]),
                ("P-BLAZER", 0.84, "ao blazer nu cong so", ["blazer"]),
            ]
            if "category_keys" in keys
            else [
                ("P-TSHIRT-1", 0.98, "ao thun cotton tay ngan", ["tshirt"]),
                ("P-TSHIRT-2", 0.96, "ao thun basic co tron", ["tshirt"]),
            ]
        )
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    payload={
                        "product_id": product_id,
                        "normalized_title_vi": title,
                        "normalized_title_tokens": title.split(),
                        "category_keys": category_keys,
                    },
                    score=score,
                )
                for product_id, score, title, category_keys in candidates
            ]
        )

    fake_qdrant_client.query_points = query_points
    constraints = resolve_search_constraints(
        rule_filters=SearchFilter(category="office_tops"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.97},
        match_sources={"category": "alias"},
        allow_category_hard=True,
    )

    response, timings = search_service.search_text_prepared(
        rewritten_query="tôi muốn áo mặc đi làm",
        filters=constraints.response_filters,
        constraints=constraints,
    )

    assert set(response.product_ids) == {"P-SHIRT", "P-BLOUSE", "P-BLAZER"}
    assert timings["recovery_triggered"] == 0.0
    product_query = next(
        query for query in fake_qdrant_client.queries if "query_filter" in query
    )
    category_condition = next(
        condition
        for condition in product_query["query_filter"].must
        if condition.key == "category_keys"
    )
    assert set(category_condition.match.any) >= {
        "shirt",
        "blouse",
        "blazer",
        "vest",
        "polo",
        "sweater",
        "cardigan",
    }
    assert "tshirt" not in set(category_condition.match.any)


def test_prepared_text_search_skips_query_understanding(search_service: SearchService, fake_llm_service) -> None:
    response, _timings = search_service.search_text_prepared(
        rewritten_query="prepared hoodie search",
        filters=SearchFilter(category="hoodie"),
    )

    assert response.rewritten_query == "prepared hoodie search"
    assert response.product_ids == ["P-TEXT", "P-SHARED"]
    assert fake_llm_service.analyze_calls == []


def test_weak_result_recovery_relaxes_only_inferred_hard_filter(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    original_query_points = fake_qdrant_client.query_points

    def query_points(collection_name: str, **kwargs):
        keys = [condition.key for condition in kwargs["query_filter"].must]
        if "size_keys" in keys:
            fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
            return SimpleNamespace(points=[])
        return original_query_points(collection_name, **kwargs)

    fake_qdrant_client.query_points = query_points
    constraints = resolve_search_constraints(
        rule_filters=SearchFilter(sizes=["M"]),
        llm_filters=None,
        explicit_filters=None,
        confidences={"size": 0.99},
        match_sources={"size": "regex"},
    )

    response, timings = search_service.search_text_prepared(
        rewritten_query="áo polo size M",
        filters=constraints.response_filters,
        constraints=constraints,
    )

    assert timings["recovery_triggered"] == 1.0
    assert response.product_ids == ["P-TEXT", "P-SHARED"]
    assert all(
        "size_keys" not in [condition.key for condition in query["query_filter"].must]
        for query in fake_qdrant_client.queries[-2:]
    )


def test_explicit_hard_filter_is_not_recovered(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        return SimpleNamespace(points=[])

    fake_qdrant_client.query_points = query_points
    constraints = resolve_search_constraints(
        rule_filters=None,
        llm_filters=None,
        explicit_filters=SearchFilter(sizes=["M"]),
    )

    response, timings = search_service.search_text_prepared(
        rewritten_query="áo polo",
        filters=constraints.response_filters,
        constraints=constraints,
    )

    assert timings["recovery_triggered"] == 0.0
    assert response.results == []
    assert all(
        "size_keys" in [condition.key for condition in query["query_filter"].must]
        for query in fake_qdrant_client.queries
    )


def test_category_recovery_unions_primary_and_relaxed_candidates(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={"text_lexical_fusion_enabled": False}
    )

    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        keys = [condition.key for condition in kwargs["query_filter"].must]
        candidates = (
            [("P-PRIMARY", 0.91)]
            if "category_keys" in keys
            else [("P-RECOVERED", 0.95), ("P-PRIMARY", 0.90)]
        )
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    payload={
                        "product_id": product_id,
                        "normalized_title_vi": "ao blouse soc co vest hong",
                        "normalized_title_tokens": [
                            "ao",
                            "blouse",
                            "soc",
                            "co",
                            "vest",
                            "hong",
                        ],
                    },
                    score=score,
                )
                for product_id, score in candidates
            ]
        )

    fake_qdrant_client.query_points = query_points
    constraints = resolve_search_constraints(
        rule_filters=SearchFilter(category="blouse"),
        llm_filters=None,
        explicit_filters=None,
        confidences={"category": 0.94},
        match_sources={"category": "typo"},
        allow_category_hard=True,
    )

    response, timings = search_service.search_text_prepared(
        rewritten_query="ao blouse soc co vest hong",
        filters=constraints.response_filters,
        constraints=constraints,
    )

    assert response.product_ids == ["P-RECOVERED", "P-PRIMARY"]
    assert timings["recovery_triggered"] == 1.0
    assert timings["category_filter_relaxed"] == 1.0
    assert timings["recovery_rescued_top5"] == 1.0
    assert timings["primary_qdrant_ms"] >= 0
    assert timings["recovery_qdrant_ms"] >= 0


def test_detected_category_soft_boost_does_not_remove_other_candidates(settings: Settings, pil_image) -> None:
    points = [
        _ScoredPoint(
            product_id="P-SHOE",
            score=0.91,
            payload={"category_names": ["Shoes"]},
        ),
        _ScoredPoint(
            product_id="P-PANTS",
            score=0.90,
            payload={"category_names": ["Track Pants"]},
        ),
    ]
    crops = [
        CropResult(
            image=pil_image,
            bbox=(0, 0, 8, 8),
            confidence=0.9,
            class_id=3,
        )
    ]

    ranked = _rank_points_by_detected_category(points, crops, settings)

    assert [point.product_id for point in ranked] == ["P-SHOE", "P-PANTS"]
    assert ranked[0].score == pytest.approx(0.91 + settings.image_yolo_category_soft_boost_weight * 0.9)
    assert ranked[1].score == pytest.approx(0.90)


def test_wrong_yolo_category_cannot_remove_vector_candidate_by_default(settings: Settings, pil_image) -> None:
    points = [
        _ScoredPoint(product_id="P-CORRECT", score=0.95, payload={"category_names": ["Track Pants"]}),
        _ScoredPoint(product_id="P-YOLO", score=0.70, payload={"category_names": ["Shirt"]}),
    ]
    crops = [CropResult(image=pil_image, bbox=(0, 0, 8, 8), confidence=0.99, class_id=0)]

    ranked = _rank_points_by_detected_category(points, crops, settings)

    assert {point.product_id for point in ranked} == {"P-CORRECT", "P-YOLO"}
    assert next(point for point in ranked if point.product_id == "P-CORRECT").score == pytest.approx(0.95)


def test_high_precision_class_can_hard_filter_above_threshold(settings: Settings, pil_image) -> None:
    settings = settings.model_copy(
        update={
            "image_yolo_category_hard_filter_class_ids": [3],
            "image_yolo_category_hard_filter_confidence": 0.90,
        }
    )
    points = [
        _ScoredPoint(product_id="P-SHOE", score=0.91, payload={"category_names": ["Shoes"]}),
        _ScoredPoint(product_id="P-PANTS", score=0.95, payload={"category_names": ["Track Pants"]}),
    ]
    crops = [CropResult(image=pil_image, bbox=(0, 0, 8, 8), confidence=0.95, class_id=3)]

    ranked = _rank_points_by_detected_category(points, crops, settings)

    assert [point.product_id for point in ranked] == ["P-SHOE"]


def test_low_confidence_or_unmapped_yolo_category_is_ignored(settings: Settings, pil_image) -> None:
    points = [_ScoredPoint(product_id="P-1", score=0.91, payload={"category_names": ["Shoes"]})]
    low_confidence = [CropResult(image=pil_image, bbox=(0, 0, 8, 8), confidence=0.2, class_id=3)]
    unmapped = [CropResult(image=pil_image, bbox=(0, 0, 8, 8), confidence=0.99, class_id=999)]

    assert _rank_points_by_detected_category(points, low_confidence, settings) == points
    assert _rank_points_by_detected_category(points, unmapped, settings) == points


def test_text_search_retrieval_order_without_rerank(search_service: SearchService) -> None:
    # rerank_enabled defaults to False, so results keep pure retrieval order.
    response = search_service.search_text(TextSearchRequest(query="áo thun"))
    assert [item.product_id for item in response.results] == ["P-TEXT", "P-SHARED"]


def test_lexical_fusion_prioritizes_exact_normalized_title(settings: Settings) -> None:
    components = _lexical_score_components(
        {
            "normalized_title_vi": "ao khoac da nam",
            "normalized_title": "mens leather jacket",
        },
        "Áo khoác da nam",
        settings,
    )

    assert components["exact_title"] == settings.text_exact_title_boost_weight
    assert components["token_coverage"] == settings.text_token_coverage_boost_weight


def test_lexical_fusion_boosts_specific_and_guarded_fuzzy_tokens(settings: Settings) -> None:
    exact = _lexical_score_components(
        {"normalized_title_vi": "ao thun tay dai co tron vai tho"},
        "ao thun tay dai co tron vai tho",
        settings,
    )
    typo = _lexical_score_components(
        {"normalized_title_vi": "ao thun tay dai co tron vai tho"},
        "ao thun tay dai co trn vai tho",
        settings,
    )
    unrelated = _lexical_score_components(
        {"normalized_title_vi": "ao thun in chu tay dai"},
        "ao thun tay dai co trn vai tho",
        settings,
    )

    assert exact["specific_tokens"] == settings.text_specific_token_boost_weight
    assert typo["fuzzy_tokens"] > 0
    assert typo["specific_tokens"] > unrelated["specific_tokens"]


def test_text_search_reorders_results_when_rerank_enabled(search_service: SearchService) -> None:
    _enable_rerank(search_service, _ReversingRerankService())

    reranked = search_service.search_text(TextSearchRequest(query="áo thun"))
    # _ReversingRerankService gives the last document the highest score, so order flips.
    assert [item.product_id for item in reranked.results] == ["P-SHARED", "P-TEXT"]
    assert reranked.results[0].rerank_score is not None


def test_text_reranker_uses_candidate_pool_then_returns_output_top_k(
    search_service: SearchService,
    fake_qdrant_client,
) -> None:
    def query_points(collection_name: str, **kwargs):
        fake_qdrant_client.queries.append({"collection_name": collection_name, **kwargs})
        points = [
            SimpleNamespace(
                payload={
                    "product_id": f"P-{index:02d}",
                    "embedding_text": f"document {index:02d}",
                },
                score=1.0 - index / 100,
            )
            for index in range(25)
        ]
        return SimpleNamespace(points=points[: kwargs["limit"]])

    fake_qdrant_client.query_points = query_points
    recorder = _RecordingRerankService()
    search_service.settings = search_service.settings.model_copy(
        update={
            "text_top_k": 5,
            "text_candidate_pool_size": 20,
            "rerank_top_k": 20,
            "rerank_enabled": True,
        }
    )
    search_service.rerank_service = recorder

    response, _ = search_service.search_text_prepared(
        rewritten_query="prepared query",
        filters=None,
    )

    assert fake_qdrant_client.queries[-1]["limit"] == 20
    assert len(recorder.documents) == 20
    assert len(response.results) == 5
    assert response.product_ids == ["P-19", "P-18", "P-17", "P-16", "P-15"]


def test_text_search_falls_back_to_retrieval_order_when_rerank_fails(
    search_service: SearchService,
) -> None:
    _enable_rerank(search_service, _FailingRerankService())

    response = search_service.search_text(TextSearchRequest(query="áo thun"))

    # Reranker raised, so the original retrieval order is preserved.
    assert [item.product_id for item in response.results] == ["P-TEXT", "P-SHARED"]


def test_text_score_boost_is_zero_when_flags_disabled(settings: Settings) -> None:
    # Both boost flags default to False, so scoring must stay bit-for-bit identical
    # to the raw vector score.
    payload = {
        "base_colour": "black",
        "gender": "women",
        "available": True,
        "inventory_count": 5,
    }
    boost = _text_score_boost(payload, SearchFilter(colors=["black"], gender="women"), settings)

    assert boost == 0.0


def test_text_score_boost_adds_color_and_gender_weights(settings: Settings) -> None:
    settings = settings.model_copy(update={"text_soft_attribute_boost_enabled": True})
    payload = {"base_colour": "black", "gender": "women"}

    boost = _text_score_boost(payload, SearchFilter(colors=["black"], gender="women"), settings)

    assert boost == pytest.approx(settings.text_color_boost_weight + settings.text_gender_boost_weight)


def test_text_score_boost_skips_unmatched_attributes(settings: Settings) -> None:
    settings = settings.model_copy(update={"text_soft_attribute_boost_enabled": True})
    payload = {"base_colour": "red", "gender": "men"}

    boost = _text_score_boost(payload, SearchFilter(colors=["black"], gender="women"), settings)

    assert boost == 0.0


def test_text_score_boost_scales_business_signals(settings: Settings) -> None:
    settings = settings.model_copy(update={"text_business_boost_enabled": True})
    # Both business signals present (available and stock) -> full weight.
    payload = {"available": True, "inventory_count": 5}

    boost = _text_score_boost(payload, None, settings)

    assert boost == pytest.approx(settings.text_business_boost_weight)


def test_exact_shade_boost_ranks_plain_family_above_variant(settings: Settings) -> None:
    # After reindexing both products carry color_keys=["pink"], so the exact-shade
    # boost is the only signal separating "Pink" from "Hồng pastel".
    plain = _text_score_components(
        {"base_colour": "Pink", "color_keys": ["pink"]},
        SearchFilter(colors=["hong"]),
        settings,
        query="ao so mi hong",
    )
    variant = _text_score_components(
        {"base_colour": "Hồng pastel", "color_keys": ["pink"]},
        SearchFilter(colors=["hong"]),
        settings,
        query="ao so mi hong",
    )

    assert plain.get("exact_shade") == pytest.approx(settings.text_exact_shade_boost_weight)
    assert "exact_shade" not in variant


def test_exact_shade_boost_absent_without_requested_color(settings: Settings) -> None:
    components = _text_score_components(
        {"base_colour": "Pink", "color_keys": ["pink"]},
        SearchFilter(category="shirt_blouse"),
        settings,
        query="ao so mi",
    )

    assert "exact_shade" not in components


@pytest.mark.parametrize(
    "payload",
    [
        {"available": True, "inventory_count": 0},
        {"available": True, "inventory_count": None},
        {"available": True, "inventory_count": True},
        {"available": False, "inventory_count": 5},
        {"available": None, "inventory_count": 5},
    ],
)
def test_business_signal_rejects_inconsistent_or_unsellable_payloads(
    payload: dict[str, object],
) -> None:
    assert _business_signal(payload) == 0.0


def test_business_signal_is_binary_and_does_not_favor_excess_stock() -> None:
    assert _business_signal({"available": True, "inventory_count": 1}) == 1.0
    assert _business_signal({"available": True, "inventory_count": 100}) == 1.0
