from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(SCRIPT_DIR))
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build = load_module('build_semantic_challenge', 'build_semantic_challenge.py')
finalize = load_module('finalize_semantic_challenge', 'finalize_semantic_challenge.py')


def source_query(query_id: str = 'text-q0001') -> dict[str, str]:
    return {
        'query_id': query_id,
        'query_type': 'positive',
        'query_text': 'áo thun màu nâu chocolate',
        'category': 'Áo thun',
        'color': 'Nâu chocolate',
        'expected_relevant_count': '1',
    }


def test_manifest_has_30_distinct_positive_sources() -> None:
    assert len(build.VARIANTS) == 30
    assert len({item.source_query_id for item in build.VARIANTS}) == 30
    assert {item.variant_type for item in build.VARIANTS} == {
        'category_synonym',
        'material_synonym',
        'conversational_constraint',
        'description_paraphrase',
    }


def test_variant_ids_are_stable() -> None:
    assert build.variant_id(1) == 'text-sem-v1-q0001'
    assert build.variant_id(30) == 'text-sem-v1-q0030'


def test_finalize_rejects_pending_review() -> None:
    with pytest.raises(ValueError, match='Review is incomplete'):
        finalize.finalize_rows(
            [source_query()],
            [],
            [{'query_id': 'text-sem-v1-q0001', 'query_text': 'áo phông'}],
            [],
            [
                {
                    'variant_query_id': 'text-sem-v1-q0001',
                    'reviewer_decision': 'pending',
                    'proposed_query_text': 'áo phông',
                }
            ],
        )


def test_finalize_approve_clones_slice_and_ground_truth() -> None:
    candidate = {
        'query_id': 'text-sem-v1-q0001',
        'query_text': 'áo phông',
        'manual_status': 'pending',
        'notes': 'review_required',
    }
    candidate_gt = {
        'query_id': 'text-sem-v1-q0001',
        'relevant_product_id': '749',
        'review_status': 'pending',
        'notes': 'provisional',
    }
    review = {
        'variant_query_id': 'text-sem-v1-q0001',
        'reviewer_decision': 'approve',
        'proposed_query_text': 'áo phông',
        'approved_query_text': '',
    }
    semantic_queries, semantic_gt, combined_queries, combined_gt = finalize.finalize_rows(
        [source_query()], [], [candidate], [candidate_gt], [review]
    )
    assert semantic_queries[0]['manual_status'] == 'approved'
    assert semantic_gt[0]['review_status'] == 'approved'
    assert combined_queries[0]['evaluation_slice'] == 'canonical_v2'
    assert len(combined_queries) == 2
    assert len(combined_gt) == 1


def test_finalize_revision_requires_text() -> None:
    candidate = {'query_id': 'text-sem-v1-q0001', 'query_text': 'old'}
    review = {
        'variant_query_id': 'text-sem-v1-q0001',
        'reviewer_decision': 'revise',
        'proposed_query_text': 'proposal',
        'approved_query_text': '',
    }
    with pytest.raises(ValueError, match='requires approved_query_text'):
        finalize.finalize_rows([], [], [candidate], [], [review])
