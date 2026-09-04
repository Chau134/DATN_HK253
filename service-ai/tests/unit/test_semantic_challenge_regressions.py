from __future__ import annotations

from types import SimpleNamespace

import pytest

from ecommerce_search_assistant.schemas.search import SearchFilter, TextSearchRequest
from ecommerce_search_assistant.services.search.filtering import analyze_query
from ecommerce_search_assistant.schemas.search import SearchResultItem
from ecommerce_search_assistant.services.search.service import (
    SearchService,
    _filter_requested_color_shade,
    _text_score_components,
)


@pytest.mark.parametrize(
    ('query', 'expected_filters'),
    (
        (
            'áo phông tông nâu sô-cô-la',
            {'category': 'tshirt', 'colors': ['brown']},
        ),
        (
            'đồ liền thân Zara màu đen bằng vải elastane',
            {
                'category': 'bodysuit',
                'brand': 'zara',
                'colors': ['black'],
                'material': 'elastane',
            },
        ),
        (
            'đồ bay nữ trong tầm một đến hai triệu',
            {
                'category': 'jumpsuit',
                'gender': 'women',
                'min_price': 1000000.0,
                'max_price': 2000000.0,
            },
        ),
        (
            'đồ liền thân nữ bằng ni-lông polyamide để đi hẹn hò',
            {
                'category': 'bodysuit',
                'gender': 'women',
                'material': 'polyamide',
            },
        ),
        (
            'bodysuit giá khoảng hai trăm đến năm trăm nghìn',
            {
                'category': 'bodysuit',
                'min_price': 200000.0,
                'max_price': 500000.0,
            },
        ),
        (
            'quần dài nữ mặc đi chơi, tầm một đến hai triệu',
            {
                'category': 'long_pants',
                'gender': 'women',
                'use_cases': ['casual'],
                'min_price': 1000000.0,
                'max_price': 2000000.0,
            },
        ),
        (
            'quần bó đen lưng cao bản to, chất vải đàn hồi',
            {'category': 'leggings', 'colors': ['black']},
        ),
    ),
)
def test_semantic_challenge_rule_extraction(
    query: str,
    expected_filters: dict[str, object],
) -> None:
    analysis = analyze_query(query)
    actual = analysis.filters.model_dump(exclude_none=True)

    for field, expected in expected_filters.items():
        assert actual[field] == expected
    if 'colors' not in expected_filters:
        assert 'colors' not in actual


def test_word_price_normalization_prevents_den_from_becoming_black() -> None:
    analysis = analyze_query('đồ bay nữ trong tầm một đến hai triệu')

    assert analysis.corrected_query == 'do bay nu trong tam 1 den 2 trieu'
    assert analysis.filters.colors is None


def test_text_search_drops_llm_color_absent_from_query(
    search_service: SearchService,
    fake_llm_service,
) -> None:
    search_service.settings = search_service.settings.model_copy(
        update={
            'text_llm_fast_path_enabled': False,
            'text_out_of_catalog_rejection_enabled': False,
        }
    )

    def analyze_user_query(message: str, locale: str = 'vi-VN'):
        fake_llm_service.analyze_calls.append((message, locale))
        return SimpleNamespace(
            rewritten_query='generic fashion products',
            filters=SearchFilter(colors=['black']),
        )

    fake_llm_service.analyze_user_query = analyze_user_query
    response = search_service.search_text(TextSearchRequest(query='tìm đồ phù hợp'))

    assert response.filters is None


def test_text_score_adds_dedicated_soft_use_case_boost(settings) -> None:
    components = _text_score_components(
        {
            'use_case_keys': ['casual'],
            'product_usage_vi': 'dạo phố, đi chơi',
        },
        SearchFilter(use_cases=['casual']),
        settings,
        query='quần dài mặc đi chơi',
    )

    assert components['use_case'] == pytest.approx(
        settings.text_use_case_boost_weight
    )


def test_compound_color_query_boosts_matching_raw_shade_only(settings) -> None:
    filters = SearchFilter(colors=['white'])
    ivory = _text_score_components(
        {'base_colour': 'Ecru', 'base_colour_vi': 'Trắng ngà'},
        filters,
        settings,
        query='áo thun màu trắng ngà',
    )
    plain_white = _text_score_components(
        {'base_colour': 'White', 'base_colour_vi': 'Trắng'},
        filters,
        settings,
        query='áo thun màu trắng ngà',
    )

    assert ivory['exact_shade'] == pytest.approx(
        settings.text_exact_shade_boost_weight
    )
    assert 'exact_shade' not in plain_white


def test_compound_color_query_does_not_pad_results_with_broad_family() -> None:
    results = [
        SearchResultItem(product_id="wine", score=1.0, source="text"),
        SearchResultItem(product_id="red", score=0.9, source="text"),
    ]
    payloads = {
        "wine": {"base_colour": "Wine", "base_colour_vi": "Đỏ rượu vang"},
        "red": {"base_colour": "Red", "base_colour_vi": "Đỏ"},
    }

    assert _filter_requested_color_shade(
        results,
        payloads,
        query="women's dresses in wine red color",
    ) == [results[0]]
    assert _filter_requested_color_shade(
        results,
        payloads,
        query="women's dresses in red",
    ) == results


def test_text_score_does_not_confuse_dao_pho_with_di_choi(settings) -> None:
    components = _text_score_components(
        {
            'use_case_keys': ['casual', 'streetwear'],
            'product_usage_vi': 'đi làm, dạo phố',
        },
        SearchFilter(use_cases=['casual']),
        settings,
        query='quần dài mặc đi chơi',
    )

    assert 'use_case' not in components
