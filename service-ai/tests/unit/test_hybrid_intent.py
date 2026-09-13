import pytest

from ecommerce_search_assistant.schemas.search import SearchFilter, HybridSearchRequest
from ecommerce_search_assistant.schemas.media import ImagePayload
from ecommerce_search_assistant.services.search.hybrid_intent import parse_hybrid_intent
from ecommerce_search_assistant.services.search.service import _filter_satisfaction, _ScoredPoint


def test_destination_replaces_source_color():
    intent = parse_hybrid_intent("áo giống ảnh, đổi từ màu đen sang màu trắng")
    assert intent.required.colors == ["white"]


@pytest.mark.parametrize("product,category", [("bodysuit", "bodysuit"), ("áo khoác", "jacket")])
def test_dark_color_does_not_erase_product_category(product, category):
    intent = parse_hybrid_intent(f"tìm {product} giống ảnh nhưng đổi sang màu nâu đậm")
    assert intent.required.category == category


def test_catalog_category_names_override_incidental_index_keys():
    intent = parse_hybrid_intent("tìm váy đầm giống ảnh")
    checks = intent.checks({"category_keys": ["dress"], "category_names_vi": ["Áo dệt kim"]}, _filter_satisfaction)
    assert not checks["category"]


def test_material_components_are_all_required_without_inventing_percentages():
    intent = parse_hybrid_intent("áo giống ảnh chất liệu cotton và elastane")
    assert set(intent.required.material.split(", ")) == {"cotton", "elastane"}
    assert not intent.checks({"category_keys": ["shirt"], "material_keys": ["cotton"]}, _filter_satisfaction)["material"]
    assert intent.checks({"material_keys": ["cotton", "elastane"]}, _filter_satisfaction)["material"]
    assert not intent.required_composition


def test_explicit_composition_requires_evidence():
    intent = parse_hybrid_intent("giống ảnh chất liệu 100% cotton")
    assert intent.required_composition == {"cotton": 100}
    assert not all(intent.checks({"material_keys": ["cotton"], "material": "95% Cotton, 5% Elastane"}, _filter_satisfaction).values())
    assert all(intent.checks({"material_keys": ["cotton"], "material": "100% Cotton"}, _filter_satisfaction).values())


def test_linen_is_not_cold_weather_requirement():
    intent = parse_hybrid_intent("giống ảnh chất liệu viscose, polyester và vải lanh")
    assert set(intent.required.material.split(", ")) == {"viscose", "polyester", "linen"}
    assert intent.required.use_cases is None


def test_material_can_be_proven_from_raw_composition_when_index_keys_omit_it():
    intent = parse_hybrid_intent("giống ảnh chất liệu lyocell")
    assert all(intent.checks({"material_keys": [], "material": "100% Lyocell"}, _filter_satisfaction).values())


def test_preference_does_not_weaken_later_price():
    intent = parse_hybrid_intent("giống ảnh ưu tiên linen giá dưới 1 triệu")
    assert intent.required.material is None
    assert intent.preferred.material == "linen"
    assert intent.required.max_price < 1000000


def test_negated_color_excluded_not_required():
    intent = parse_hybrid_intent("giống ảnh không màu đen")
    assert intent.required.colors is None
    assert not all(intent.checks({"color_keys": ["black"]}, _filter_satisfaction).values())
    assert all(intent.checks({"color_keys": ["white"]}, _filter_satisfaction).values())
    assert not all(intent.checks({}, _filter_satisfaction).values())


@pytest.mark.parametrize("joiner,expected", [("và", False), ("hoặc", True)])
def test_multiple_colors(joiner, expected):
    intent = parse_hybrid_intent(f"giống ảnh màu trắng {joiner} màu đen")
    assert intent.checks({"color_keys": ["white"]}, _filter_satisfaction)["colors"] is expected


def test_usage_literals_do_not_collapse_into_casual():
    intent = parse_hybrid_intent("giống ảnh phù hợp du lịch")
    assert not intent.checks({"use_case_keys": ["casual"], "product_usage_vi": "đi chơi"}, _filter_satisfaction)["use_cases"]
    assert intent.checks({"product_usage_vi": "đi chơi, dạo phố, du lịch"}, _filter_satisfaction)["use_cases"]


@pytest.mark.parametrize("usage", ["đi chơi", "dạo phố, đi làm", "du lịch"])
def test_usage_list_accepts_any_named_occasion(usage):
    intent = parse_hybrid_intent("giống ảnh phù hợp đi chơi, dạo phố, du lịch")
    assert intent.usage_mode == "any"
    assert intent.checks({"product_usage_vi": usage}, _filter_satisfaction)["use_cases"]


@pytest.mark.parametrize("payload", [{}, {"use_case_keys": ["casual"]}, {"product_usage_vi": "đi làm, hẹn hò"}])
def test_usage_list_still_requires_evidence_for_one_named_occasion(payload):
    intent = parse_hybrid_intent("giống ảnh phù hợp đi chơi, dạo phố, du lịch")
    assert not intent.checks(payload, _filter_satisfaction)["use_cases"]


@pytest.mark.parametrize("clause", [
    "phù hợp cả ba: đi chơi, dạo phố, du lịch",
    "phù hợp tất cả: đi chơi, dạo phố, du lịch",
    "đồng thời phù hợp đi chơi, dạo phố, du lịch",
    "phù hợp đi chơi và du lịch",
])
def test_explicit_usage_conjunction_remains_required(clause):
    intent = parse_hybrid_intent("giống ảnh " + clause)
    assert intent.usage_mode == "all"
    assert not intent.checks({"product_usage_vi": "đi chơi"}, _filter_satisfaction)["use_cases"]
    assert intent.checks({"product_usage_vi": "đi chơi, dạo phố, du lịch"}, _filter_satisfaction)["use_cases"]


def test_usage_alternatives_do_not_weaken_material_color_or_price():
    intent = parse_hybrid_intent("giống ảnh màu trắng và đen chất liệu cotton và elastane phù hợp đi chơi, du lịch giá dưới 500k")
    assert intent.usage_mode == "any"
    assert intent.material_mode == "all"
    assert intent.required.color_match_mode == "all"
    assert intent.required.max_price < 500000


def test_explicit_usage_filter_retains_api_override():
    intent = parse_hybrid_intent("giống ảnh phù hợp cả ba đi chơi, dạo phố, du lịch", SearchFilter(use_cases=["office"]))
    assert intent.usage_mode == "any" and not intent.usage_phrases
    assert intent.checks({"use_case_keys": ["office"]}, _filter_satisfaction)["use_cases"]


@pytest.mark.parametrize("all_required", [False, True])
def test_usage_contract_controls_candidate_admission(search_service, image_payload, monkeypatch, all_required):
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned", "hybrid_conditioned_recovery_enabled": False})
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [
        _ScoredPoint("unrelated", .99, {"product_usage_vi": "đi làm"}),
        _ScoredPoint("one", .9, {"product_usage_vi": "dạo phố"}),
        _ScoredPoint("all", .8, {"product_usage_vi": "đi chơi, dạo phố, du lịch"}),
    ])
    qualifier = "cả ba " if all_required else ""
    response = search_service.search_hybrid(HybridSearchRequest(
        query=f"giống ảnh phù hợp {qualifier}đi chơi, dạo phố, du lịch", image=ImagePayload(**image_payload)))
    assert response.product_ids == (["all"] if all_required else ["one", "all"])


def test_color_only_request_does_not_require_hidden_material_usage_or_price(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned", "hybrid_conditioned_recovery_enabled": False})
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [
        _ScoredPoint("right", .8, {"color_keys": ["red"]}),
        _ScoredPoint("wrong", .9, {"color_keys": ["blue"], "material_keys": ["cotton"],
                                    "product_usage_vi": "đi chơi", "selling_price": 100}),
    ])
    response = search_service.search_hybrid(HybridSearchRequest(
        query="giống ảnh nhưng đổi sang màu đỏ", image=ImagePayload(**image_payload)))
    assert response.product_ids == ["right"]
    assert response.filters.colors == ["red"]
    assert response.filters.material is None and response.filters.use_cases is None
    assert response.filters.min_price is None and response.filters.max_price is None


def test_every_user_requested_field_is_required_during_admission(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned", "hybrid_conditioned_recovery_enabled": False})
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [
        _ScoredPoint("good", .7, {"color_keys": ["red"], "material_keys": ["cotton"], "selling_price": 499000}),
        _ScoredPoint("wrong-color", .99, {"color_keys": ["blue"], "material_keys": ["cotton"], "selling_price": 499000}),
        _ScoredPoint("wrong-material", .98, {"color_keys": ["red"], "material_keys": ["silk"], "selling_price": 499000}),
        _ScoredPoint("wrong-price", .97, {"color_keys": ["red"], "material_keys": ["cotton"], "selling_price": 500000}),
    ])
    response = search_service.search_hybrid(HybridSearchRequest(
        query="giống ảnh màu đỏ chất liệu cotton giá dưới 500k", image=ImagePayload(**image_payload)))
    assert response.product_ids == ["good"]


def test_request_filters_override_text():
    intent = parse_hybrid_intent("màu trắng giá dưới 1 triệu", SearchFilter(colors=["black"], max_price=1500000))
    assert intent.required.colors == ["black"]
    assert intent.required.max_price == 1500000


def test_unknown_material_is_not_silently_ignored():
    assert parse_hybrid_intent("giống ảnh chất liệu unobtainium").uncertain


def test_unknown_color_is_not_silently_ignored():
    intent = parse_hybrid_intent("giống ảnh màu octarine")
    assert not all(intent.checks({"color_keys": ["white"], "base_colour_vi": "Trắng"}, _filter_satisfaction).values())
    assert all(intent.checks({"base_colour": "Octarine"}, _filter_satisfaction).values())


def test_sample_word_is_not_color_word():
    assert not parse_hybrid_intent("tìm mẫu giống ảnh").uncertain


def test_sample_word_before_negated_color_is_not_a_positive_color():
    intent = parse_hybrid_intent("tìm mẫu giống ảnh nhưng không màu đen")
    assert not intent.required.colors
    assert all(intent.checks({"color_keys": ["white"]}, _filter_satisfaction).values())


def test_literal_shade_cannot_match_other_shade_in_same_family():
    intent = parse_hybrid_intent("giống ảnh màu hồng pastel")
    assert not all(intent.checks({"color_keys": ["pink"], "base_colour_vi": "Hồng đậm"}, _filter_satisfaction).values())
    assert all(intent.checks({"color_keys": ["pink"], "base_colour_vi": "Hồng pastel"}, _filter_satisfaction).values())


def test_two_colors_allow_bare_second_color_name():
    intent = parse_hybrid_intent("giống ảnh màu trắng ngà và đỏ")
    assert set(intent.required.colors) == {"cream", "red"}


def test_plain_color_or_specific_shade():
    intent = parse_hybrid_intent("giống ảnh màu trắng hoặc hồng pastel nhé")
    assert all(intent.checks({"color_keys": ["white"], "base_colour_vi": "Trắng"}, _filter_satisfaction).values())
    assert not all(intent.checks({"color_keys": ["pink"], "base_colour_vi": "Hồng đậm"}, _filter_satisfaction).values())


def test_material_or_does_not_weaken_color_and():
    intent = parse_hybrid_intent("giống ảnh màu trắng và đen chất liệu cotton hoặc linen")
    assert intent.required.color_match_mode == "all"
    assert intent.material_mode == "any"


def test_unsupported_price_negation_fails_closed():
    assert parse_hybrid_intent("giống ảnh giá không dưới 500k").uncertain == ["unsupported_negated_price"]


def test_inclusive_price_is_not_a_negation():
    intent = parse_hybrid_intent("giống ảnh giá không quá 1 triệu")
    assert not intent.uncertain
    assert not intent.excluded
    assert intent.required.max_price == 1000000


def test_explicit_filter_overrides_conflicting_negation():
    intent = parse_hybrid_intent("không màu đen", SearchFilter(colors=["black"]))
    assert not intent.excluded
    assert intent.checks({"color_keys": ["black"]}, _filter_satisfaction)["colors"]


def test_high_similarity_wrong_material_cannot_enter_results(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={"hybrid_search_policy": "image_conditioned", "hybrid_conditioned_recovery_enabled": False})
    points = [
        _ScoredPoint("wrong", 0.99, {"material_keys": ["polyester"]}),
        _ScoredPoint("right", 0.7, {"material_keys": ["cotton"]}),
        _ScoredPoint("right", 0.6, {"material_keys": ["cotton"]}),
    ]
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: points)
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload), top_k=5))
    assert response.product_ids == ["right"]
    assert response.results[0].score == 0.7


def test_empty_instead_of_relaxing_required(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={"hybrid_search_policy": "image_conditioned", "hybrid_conditioned_recovery_enabled": False})
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [_ScoredPoint("wrong", 0.99, {"material_keys": ["polyester"]})])
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload)))
    assert not response.product_ids
    assert response.constraint_failure_reason == "no_candidates_satisfy_required_constraints"


def test_recovery_requires_actual_image_vector(search_service, image_payload, monkeypatch):
    from types import SimpleNamespace
    search_service.settings = search_service.settings.model_copy(update={"hybrid_search_policy": "image_conditioned"})
    def query(**kwargs):
        return [_ScoredPoint("text-only", 0.99, {"material_keys": ["cotton"]})] if "text" in kwargs["collection_name"] else []
    monkeypatch.setattr(search_service, "_query_collection", query)
    monkeypatch.setattr(search_service.qdrant_client, "query_points", lambda **kwargs: SimpleNamespace(points=[]))
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload)))
    assert response.product_ids == []


def test_recovery_scores_visual_candidate_and_revalidates_metadata(search_service, image_payload, monkeypatch):
    from types import SimpleNamespace
    search_service.settings = search_service.settings.model_copy(update={"hybrid_search_policy": "image_conditioned"})
    def query(**kwargs):
        return [_ScoredPoint("rescued", 0.99, {"material_keys": ["cotton"]})] if "text" in kwargs["collection_name"] else []
    monkeypatch.setattr(search_service, "_query_collection", query)
    monkeypatch.setattr(search_service.qdrant_client, "query_points", lambda **kwargs: SimpleNamespace(points=[
        SimpleNamespace(score=0.6, payload={"product_id": "rescued", "material_keys": ["cotton"]}),
        SimpleNamespace(score=0.99, payload={"product_id": "bad", "material_keys": ["polyester"]}),
    ]))
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload)))
    assert response.product_ids == ["rescued"]
    assert response.results[0].score == 0.6


def test_recovery_exception_keeps_valid_image_results(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={"hybrid_search_policy": "image_conditioned"})
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [_ScoredPoint("valid", 0.6, {"material_keys": ["cotton"]})])
    def fail(_):
        raise TimeoutError("provider unavailable")
    from types import SimpleNamespace
    monkeypatch.setattr(search_service, "text_embedding_service", SimpleNamespace(embed_query=fail))
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload)))
    assert response.product_ids == ["valid"]


def test_soft_preference_changes_close_ranking_without_filtering(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={"hybrid_search_policy": "image_conditioned", "hybrid_conditioned_recovery_enabled": False})
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [
        _ScoredPoint("other", 0.81, {"material_keys": ["polyester"]}),
        _ScoredPoint("preferred", 0.8, {"material_keys": ["linen"]}),
    ])
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh ưu tiên linen", image=ImagePayload(**image_payload)))
    assert response.product_ids == ["preferred", "other"]


def test_requested_secondary_color_ranks_after_dominant_color_matches(
    search_service, image_payload, monkeypatch
):
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned",
        "hybrid_conditioned_recovery_enabled": False,
        "hybrid_conditioned_dominant_color_ranking_enabled": True,
    })
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [
        _ScoredPoint("secondary-beige", .99, {
            "category_keys": ["tshirt"],
            "color_keys": ["brown", "beige", "multicolor"],
            "normalized_title_vi": "ao thun mau nau va be",
        }),
        _ScoredPoint("single-beige", .70, {
            "category_keys": ["tshirt"],
            "color_keys": ["beige"],
            "normalized_title_vi": "ao thun mau be",
        }),
        _ScoredPoint("dominant-beige", .80, {
            "category_keys": ["tshirt"],
            "color_keys": ["beige", "brown", "multicolor"],
            "normalized_title_vi": "ao thun mau be va nau",
        }),
    ])

    response = search_service.search_hybrid(HybridSearchRequest(
        query="tìm áo thun giống ảnh nhưng đổi sang màu be",
        image=ImagePayload(**image_payload),
        top_k=3,
    ))

    assert response.product_ids == ["dominant-beige", "single-beige", "secondary-beige"]
    assert response.results[2].score < response.results[1].score


def test_dominant_color_ranking_can_be_disabled(
    search_service, image_payload, monkeypatch
):
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned",
        "hybrid_conditioned_recovery_enabled": False,
        "hybrid_conditioned_dominant_color_ranking_enabled": False,
    })
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [
        _ScoredPoint("secondary-beige", .99, {
            "category_keys": ["tshirt"],
            "color_keys": ["brown", "beige", "multicolor"],
            "base_colour_vi": "Nâu / Be",
        }),
        _ScoredPoint("single-beige", .70, {
            "category_keys": ["tshirt"],
            "color_keys": ["beige"],
            "base_colour_vi": "Be",
        }),
    ])

    response = search_service.search_hybrid(HybridSearchRequest(
        query="tìm áo thun giống ảnh nhưng đổi sang màu be",
        image=ImagePayload(**image_payload),
        top_k=2,
    ))

    assert response.product_ids == ["secondary-beige", "single-beige"]


def test_image_conditioned_rerank_uses_metadata_when_embedding_text_is_absent(
    search_service, image_payload, monkeypatch
):
    class MetadataReranker:
        def __init__(self):
            self.documents = []

        def rerank(self, query, documents):
            self.documents = documents
            return [0.1, 0.9]

    reranker = MetadataReranker()
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned",
        "hybrid_conditioned_recovery_enabled": False,
        "hybrid_conditioned_dominant_color_ranking_enabled": False,
        "rerank_enabled": True,
    })
    search_service.rerank_service = reranker
    monkeypatch.setattr(search_service, "_query_collection", lambda **kwargs: [
        _ScoredPoint("visual-first", .90, {
            "normalized_title_vi": "ao thun mau be",
            "category_names_vi": ["ao thun"],
            "base_colour_vi": "be",
        }),
        _ScoredPoint("rerank-first", .80, {
            "normalized_title_vi": "ao thun be di du lich",
            "category_names_vi": ["ao thun"],
            "base_colour_vi": "be",
            "product_usage_vi": "du lich",
        }),
    ])

    response = search_service.search_hybrid(HybridSearchRequest(
        query="giong anh",
        image=ImagePayload(**image_payload),
        top_k=2,
    ))

    assert response.product_ids == ["rerank-first", "visual-first"]
    assert len(reranker.documents) == 2
    assert "normalized_title_vi: ao thun mau be" in reranker.documents[0]
    assert "product_usage_vi: du lich" in reranker.documents[1]
    assert all(item.rerank_score is not None for item in response.results)


def test_rrf_fetches_text_even_when_image_results_are_full(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned", "hybrid_conditioned_ranking": "rrf",
        "hybrid_conditioned_recovery_enabled": False})
    collections = []
    def query(**kwargs):
        collections.append(kwargs["collection_name"])
        return [_ScoredPoint("valid", 0.7, {"material_keys": ["cotton"]})]
    monkeypatch.setattr(search_service, "_query_collection", query)
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload), top_k=1))
    assert response.product_ids == ["valid"]
    assert search_service.settings.qdrant_text_collection in collections
    assert response.results[0].score == pytest.approx(1 / 61)


def test_grouped_retrieval_preserves_required_and_real_visual_score(search_service, image_payload, monkeypatch):
    from types import SimpleNamespace
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned", "hybrid_conditioned_grouped_retrieval_enabled": True,
        "hybrid_conditioned_recovery_enabled": False})
    calls = []
    def grouped(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(groups=[SimpleNamespace(hits=[SimpleNamespace(score=score, payload={"product_id": pid, "material_keys": [material]})])
                                       for pid, material, score in [("wrong", "polyester", .99), ("right", "cotton", .6)]])
    monkeypatch.setattr(search_service.qdrant_client, "query_points_groups", grouped, raising=False)
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload), top_k=5))
    assert response.product_ids == ["right"]
    assert response.results[0].score == .6
    assert all(c["group_by"] == "product_id" and c["group_size"] == 1 and c["limit"] <= 100 for c in calls)


def test_refill_continues_past_page_without_new_eligible_product(search_service, image_payload, monkeypatch):
    search_service.settings = search_service.settings.model_copy(update={
        "hybrid_search_policy": "image_conditioned", "hybrid_conditioned_grouped_retrieval_enabled": True,
        "hybrid_conditioned_recovery_enabled": False, "hybrid_candidate_pool_size": 2,
        "hybrid_product_overfetch_factor": 1, "hybrid_candidate_pool_cap": 8})
    from types import SimpleNamespace
    calls = []
    def grouped(**kwargs):
        count = kwargs["limit"]
        calls.append(count)
        return SimpleNamespace(groups=[SimpleNamespace(hits=[SimpleNamespace(score=.5, payload={
            "product_id": str(i), "material_keys": ["cotton" if i == 7 else "polyester"]})]) for i in range(count)])
    monkeypatch.setattr(search_service.qdrant_client, "query_points_groups", grouped, raising=False)
    response = search_service.search_hybrid(HybridSearchRequest(query="giống ảnh chất liệu cotton", image=ImagePayload(**image_payload), top_k=2))
    assert response.product_ids == ["7"]
    assert 2 in calls and 4 in calls and 8 in calls
