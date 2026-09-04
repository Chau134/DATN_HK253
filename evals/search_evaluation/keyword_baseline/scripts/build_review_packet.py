from __future__ import annotations

import argparse
import csv
import json
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
BASELINE_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = BASELINE_DIR / 'configs' / 'keyword_bm25.toml'
FIELDS = [
    'review_priority',
    'review_reason',
    'query_id',
    'query_type',
    'intent_type',
    'difficulty',
    'query_text',
    'relevant_count',
    'relevant_sample',
    'keyword_hit@5',
    'keyword_ndcg@5',
    'keyword_top5',
    'vector_hit@5',
    'vector_ndcg@5',
    'vector_top5',
    'delta_vector_minus_keyword_ndcg@5',
    'review_status',
    'reviewer_decision',
    'review_notes',
]


def load_config(path: Path) -> dict[str, Any]:
    with path.open('rb') as handle:
        return tomllib.load(handle)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def resolve_config_path(config_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (config_path.parent / path).resolve()


def per_query_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row['query_id']): row
        for row in report.get('per_query', [])
    }


def top_results(rows: list[dict[str, str]], top_k: int = 5) -> dict[str, list[str]]:
    grouped: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in rows:
        query_id = str(row.get('query_id', '')).strip()
        product_id = str(row.get('product_id', '')).strip()
        try:
            rank = int(float(str(row.get('rank', '0'))))
        except ValueError:
            continue
        if query_id and product_id and 0 < rank <= top_k:
            grouped[query_id].append((rank, product_id))
    return {
        query_id: [
            product_id
            for _, product_id in sorted(items)
        ]
        for query_id, items in grouped.items()
    }


def product_label(product_id: str, products: dict[str, dict[str, str]]) -> str:
    row = products.get(product_id, {})
    name = str(row.get('product_name', '')).strip()
    return '{}: {}'.format(product_id, name or 'unknown')


def format_product_list(
    product_ids: list[str],
    products: dict[str, dict[str, str]],
    *,
    limit: int = 10,
) -> str:
    return ' | '.join(
        product_label(product_id, products)
        for product_id in product_ids[:limit]
    )


def review_reason(
    baseline: dict[str, Any],
    vector: dict[str, Any],
) -> tuple[str, str] | None:
    if baseline.get('query_type') == 'negative':
        if float(baseline.get('false_positive_flag', 0.0)) > 0:
            return 'required', 'keyword_negative_false_positive'
        return None
    baseline_ndcg = float(baseline.get('ndcg@5', 0.0))
    vector_ndcg = float(vector.get('ndcg@5', 0.0))
    delta = vector_ndcg - baseline_ndcg
    if float(vector.get('hit@5', 0.0)) == 0.0:
        return 'required', 'vector_misses_relevant_top5'
    if delta <= -0.1:
        return 'recommended', 'keyword_materially_better'
    if delta >= 0.1:
        return 'recommended', 'vector_materially_better'
    return None


def build_review_rows(config_path: Path) -> list[dict[str, Any]]:
    config = load_config(config_path)
    paths = config['paths']
    threshold = int(config['evaluation']['relevance_threshold'])
    queries = {
        row['query_id']: row
        for row in read_csv_rows(
            resolve_config_path(config_path, paths['query_set_csv'])
        )
    }
    products = {
        row['product_id']: row
        for row in read_csv_rows(
            resolve_config_path(config_path, paths['products_csv'])
        )
    }
    relevant_by_query: dict[str, list[str]] = defaultdict(list)
    for row in read_csv_rows(
        resolve_config_path(config_path, paths['ground_truth_csv'])
    ):
        try:
            grade = int(float(row.get('relevance_grade', '0')))
        except ValueError:
            grade = 0
        product_id = str(row.get('relevant_product_id', '')).strip()
        if product_id and grade >= threshold:
            relevant_by_query[row['query_id']].append(product_id)

    baseline_report = load_json(
        resolve_config_path(config_path, paths['metrics_json'])
    )
    vector_report = load_json(
        resolve_config_path(config_path, paths['vector_metrics_json'])
    )
    baseline_metrics = per_query_map(baseline_report)
    vector_metrics = per_query_map(vector_report)
    baseline_top5 = top_results(
        read_csv_rows(resolve_config_path(config_path, paths['results_csv']))
    )
    vector_top5 = top_results(
        read_csv_rows(
            resolve_config_path(config_path, paths['vector_results_csv'])
        )
    )

    output: list[dict[str, Any]] = []
    for query_id in sorted(baseline_metrics):
        baseline = baseline_metrics[query_id]
        vector = vector_metrics.get(query_id, {})
        selected = review_reason(baseline, vector)
        if selected is None:
            continue
        priority, reason = selected
        query = queries.get(query_id, {})
        relevant_ids = relevant_by_query.get(query_id, [])
        baseline_ndcg = float(baseline.get('ndcg@5', 0.0))
        vector_ndcg = float(vector.get('ndcg@5', 0.0))
        output.append(
            {
                'review_priority': priority,
                'review_reason': reason,
                'query_id': query_id,
                'query_type': baseline.get('query_type', ''),
                'intent_type': baseline.get('intent_type', ''),
                'difficulty': baseline.get('difficulty', ''),
                'query_text': query.get('query_text', ''),
                'relevant_count': len(relevant_ids),
                'relevant_sample': format_product_list(
                    relevant_ids,
                    products,
                ),
                'keyword_hit@5': baseline.get('hit@5', ''),
                'keyword_ndcg@5': baseline.get('ndcg@5', ''),
                'keyword_top5': format_product_list(
                    baseline_top5.get(query_id, []),
                    products,
                    limit=5,
                ),
                'vector_hit@5': vector.get('hit@5', ''),
                'vector_ndcg@5': vector.get('ndcg@5', ''),
                'vector_top5': format_product_list(
                    vector_top5.get(query_id, []),
                    products,
                    limit=5,
                ),
                'delta_vector_minus_keyword_ndcg@5': (
                    vector_ndcg - baseline_ndcg
                ),
                'review_status': 'pending',
                'reviewer_decision': '',
                'review_notes': '',
            }
        )
    output.sort(
        key=lambda row: (
            0 if row['review_priority'] == 'required' else 1,
            float(row['delta_vector_minus_keyword_ndcg@5'] or 0.0),
            row['query_id'],
        )
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Build a focused review packet for the keyword baseline.'
    )
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--output-csv', type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve()
    config = load_config(config_path)
    output_csv = args.output_csv or resolve_config_path(
        config_path,
        config['paths']['review_csv'],
    )
    rows = build_review_rows(config_path)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    required = sum(row['review_priority'] == 'required' for row in rows)
    recommended = sum(
        row['review_priority'] == 'recommended' for row in rows
    )
    print(
        'review_rows={} required={} recommended={}'.format(
            len(rows),
            required,
            recommended,
        )
    )
    print('review -> {}'.format(output_csv))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
