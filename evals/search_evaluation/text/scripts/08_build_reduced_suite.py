from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TEXT_DIR = SCRIPT_DIR.parent
DIFFICULTY_TARGETS = {'easy': 20, 'medium': 20, 'hard': 20}


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_rows(
    path: Path, rows: list[dict[str, str]], fieldnames: list[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def select_canonical_positive(
    canonical: list[dict[str, str]], semantic: list[dict[str, str]]
) -> tuple[set[str], dict[str, str]]:
    source_ids = {row['source_query_id'].strip() for row in semantic}
    canonical_by_id = {row['query_id']: row for row in canonical}
    missing_sources = sorted(source_ids - set(canonical_by_id))
    if missing_sources:
        raise RuntimeError(f'Semantic source queries are missing: {missing_sources}')

    selected = set(source_ids)
    reasons = {query_id: 'semantic_source_pair' for query_id in source_ids}
    total_category_counts = Counter(
        canonical_by_id[query_id].get('category', '') for query_id in selected
    )

    for difficulty, target in DIFFICULTY_TARGETS.items():
        selected_for_difficulty = {
            query_id
            for query_id in selected
            if canonical_by_id[query_id].get('difficulty') == difficulty
        }
        if len(selected_for_difficulty) > target:
            raise RuntimeError(
                f'{difficulty} semantic sources exceed target: '
                f'{len(selected_for_difficulty)} > {target}'
            )
        difficulty_category_counts = Counter(
            canonical_by_id[query_id].get('category', '')
            for query_id in selected_for_difficulty
        )
        candidates = [
            row
            for row in canonical
            if row.get('difficulty') == difficulty
            and row['query_id'] not in selected
        ]
        while len(selected_for_difficulty) < target:
            if not candidates:
                raise RuntimeError(f'Not enough candidates for {difficulty}')
            chosen = min(
                candidates,
                key=lambda row: (
                    difficulty_category_counts[row.get('category', '')],
                    total_category_counts[row.get('category', '')],
                    row['query_id'],
                ),
            )
            candidates.remove(chosen)
            query_id = chosen['query_id']
            category = chosen.get('category', '')
            selected.add(query_id)
            selected_for_difficulty.add(query_id)
            reasons[query_id] = 'difficulty_category_balance'
            difficulty_category_counts[category] += 1
            total_category_counts[category] += 1

    return selected, reasons


def main() -> int:
    args = parse_args()
    queries, query_fields = read_rows(args.input_queries)
    ground_truth, gt_fields = read_rows(args.input_ground_truth)

    canonical_positive = [
        row
        for row in queries
        if row.get('evaluation_slice') == 'canonical_v2'
        and row.get('query_type') == 'positive'
    ]
    semantic_positive = [
        row
        for row in queries
        if row.get('evaluation_slice') == 'semantic_challenge_v1'
        and row.get('query_type') == 'positive'
    ]
    negative = [row for row in queries if row.get('query_type') == 'negative']
    if (len(canonical_positive), len(semantic_positive), len(negative)) != (90, 30, 10):
        raise RuntimeError(
            'Expected 90 canonical positive, 30 semantic positive and '
            f'10 negative queries, got {len(canonical_positive)}, '
            f'{len(semantic_positive)}, {len(negative)}'
        )

    selected_ids, reasons = select_canonical_positive(
        canonical_positive, semantic_positive
    )
    selected_canonical = [
        row for row in canonical_positive if row['query_id'] in selected_ids
    ]
    reduced_queries = [*selected_canonical, *negative, *semantic_positive]
    kept_ids = {row['query_id'] for row in reduced_queries}
    reduced_ground_truth = [
        row for row in ground_truth if row.get('query_id') in kept_ids
    ]

    difficulty_counts = Counter(row['difficulty'] for row in selected_canonical)
    if len(selected_canonical) != 60 or difficulty_counts != Counter(DIFFICULTY_TARGETS):
        raise RuntimeError(
            f'Invalid canonical selection: count={len(selected_canonical)}, '
            f'difficulties={dict(difficulty_counts)}'
        )
    if len(reduced_queries) != 100 or len(kept_ids) != 100:
        raise RuntimeError('Reduced suite must contain 100 unique queries')
    positive_ids = {
        row['query_id']
        for row in reduced_queries
        if row.get('query_type') == 'positive'
    }
    gt_positive_ids = {
        row['query_id']
        for row in reduced_ground_truth
        if row.get('query_type') == 'positive'
        and int(row.get('relevance_grade') or 0) >= 1
    }
    if positive_ids - gt_positive_ids:
        raise RuntimeError(
            f'Positive queries without ground truth: {sorted(positive_ids - gt_positive_ids)}'
        )

    review_rows = []
    semantic_sources = {row['source_query_id'] for row in semantic_positive}
    for row in canonical_positive:
        query_id = row['query_id']
        review_rows.append(
            {
                'query_id': query_id,
                'query_text': row.get('query_text', ''),
                'difficulty': row.get('difficulty', ''),
                'category': row.get('category', ''),
                'selected': 'yes' if query_id in selected_ids else 'no',
                'selection_reason': reasons.get(query_id, 'excluded'),
                'has_semantic_pair': 'yes' if query_id in semantic_sources else 'no',
            }
        )

    write_rows(args.output_queries, reduced_queries, query_fields)
    write_rows(args.output_ground_truth, reduced_ground_truth, gt_fields)
    write_rows(
        args.selection_review,
        review_rows,
        [
            'query_id',
            'query_text',
            'difficulty',
            'category',
            'selected',
            'selection_reason',
            'has_semantic_pair',
        ],
    )
    print(
        'queries=100 canonical_positive=60 semantic_positive=30 negative=10 '
        f'ground_truth_rows={len(reduced_ground_truth)} '
        f'difficulties={dict(sorted(difficulty_counts.items()))}'
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Build the reduced 60 canonical + 30 semantic + 10 negative suite.'
    )
    parser.add_argument(
        '--input-queries',
        type=Path,
        default=TEXT_DIR / 'data' / 'text_queries_v3_semantic.csv',
    )
    parser.add_argument(
        '--input-ground-truth',
        type=Path,
        default=TEXT_DIR / 'data' / 'ground_truth_text_v3_semantic.csv',
    )
    parser.add_argument(
        '--output-queries',
        type=Path,
        default=TEXT_DIR / 'data' / 'text_queries_v4_reduced.csv',
    )
    parser.add_argument(
        '--output-ground-truth',
        type=Path,
        default=TEXT_DIR / 'data' / 'ground_truth_text_v4_reduced.csv',
    )
    parser.add_argument(
        '--selection-review',
        type=Path,
        default=(
            TEXT_DIR
            / 'semantic_challenge'
            / 'review'
            / 'reduced_canonical_selection_review.csv'
        ),
    )
    return parser.parse_args()


if __name__ == '__main__':
    raise SystemExit(main())
