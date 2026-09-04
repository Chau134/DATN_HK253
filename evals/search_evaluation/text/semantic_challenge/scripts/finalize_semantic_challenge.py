from __future__ import annotations

import argparse
from pathlib import Path

from build_semantic_challenge import CHALLENGE_DIR, TEXT_DIR, read_csv, union_fields, write_csv, write_runner_configs


ALLOWED_DECISIONS = {'approve', 'revise', 'reject'}


def finalize_rows(
    base_queries: list[dict[str, str]],
    base_ground_truth: list[dict[str, str]],
    candidate_queries: list[dict[str, str]],
    candidate_ground_truth: list[dict[str, str]],
    review_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    review_by_id = {row['variant_query_id']: row for row in review_rows}
    pending = [
        row['variant_query_id']
        for row in review_rows
        if row.get('reviewer_decision', '').strip().lower() not in ALLOWED_DECISIONS
    ]
    if pending:
        raise ValueError('Review is incomplete for: ' + ', '.join(pending))

    approved_queries: list[dict[str, str]] = []
    approved_ids: set[str] = set()
    for candidate in candidate_queries:
        query_id = candidate['query_id']
        review = review_by_id.get(query_id)
        if not review:
            raise ValueError(f'Missing review row for {query_id}')
        decision = review['reviewer_decision'].strip().lower()
        if decision == 'reject':
            continue
        approved_text = review.get('approved_query_text', '').strip()
        if decision == 'revise' and not approved_text:
            raise ValueError(f'Revised query requires approved_query_text: {query_id}')
        finalized = dict(candidate)
        finalized['query_text'] = approved_text or review['proposed_query_text']
        finalized['manual_status'] = 'approved'
        finalized['notes'] = finalized.get('notes', '').replace('review_required', f'review_decision={decision}')
        approved_queries.append(finalized)
        approved_ids.add(query_id)

    approved_ground_truth: list[dict[str, str]] = []
    for row in candidate_ground_truth:
        if row['query_id'] not in approved_ids:
            continue
        finalized = dict(row)
        finalized['review_status'] = 'approved'
        finalized['notes'] = finalized.get('notes', '') + ';query_equivalence_approved'
        approved_ground_truth.append(finalized)

    prepared_base_queries: list[dict[str, str]] = []
    for row in base_queries:
        prepared = dict(row)
        prepared.setdefault('source_query_id', '')
        prepared.setdefault('evaluation_slice', 'canonical_v2')
        prepared.setdefault('semantic_variant_type', 'none')
        prepared_base_queries.append(prepared)

    combined_queries = prepared_base_queries + approved_queries
    combined_ground_truth = list(base_ground_truth) + approved_ground_truth
    return approved_queries, approved_ground_truth, combined_queries, combined_ground_truth


def main() -> int:
    parser = argparse.ArgumentParser(description='Finalize reviewed semantic queries and build Text Search v3.')
    parser.add_argument('--review-csv', type=Path, default=CHALLENGE_DIR / 'review' / 'semantic_query_review.csv')
    args = parser.parse_args()

    base_queries = read_csv(TEXT_DIR / 'data' / 'text_queries_v2.csv')
    base_gt = read_csv(TEXT_DIR / 'data' / 'ground_truth_text_v2.csv')
    candidate_queries = read_csv(CHALLENGE_DIR / 'data' / 'text_queries_semantic_candidates_v1.csv')
    candidate_gt = read_csv(CHALLENGE_DIR / 'data' / 'ground_truth_text_semantic_candidates_v1.csv')
    outputs = finalize_rows(base_queries, base_gt, candidate_queries, candidate_gt, read_csv(args.review_csv))
    semantic_queries, semantic_gt, combined_queries, combined_gt = outputs

    write_csv(CHALLENGE_DIR / 'data' / 'text_queries_semantic_only_v1.csv', semantic_queries, union_fields(semantic_queries))
    write_csv(CHALLENGE_DIR / 'data' / 'ground_truth_text_semantic_only_v1.csv', semantic_gt, union_fields(semantic_gt))
    write_csv(TEXT_DIR / 'data' / 'text_queries_v3_semantic.csv', combined_queries, union_fields(combined_queries))
    write_csv(TEXT_DIR / 'data' / 'ground_truth_text_v3_semantic.csv', combined_gt, union_fields(combined_gt))
    write_runner_configs(combined_count=len(combined_queries), semantic_count=len(semantic_queries))
    print(
        f'semantic_queries={len(semantic_queries)} semantic_ground_truth={len(semantic_gt)} '
        f'combined_queries={len(combined_queries)} combined_ground_truth={len(combined_gt)}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
