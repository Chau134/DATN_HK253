from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path
from typing import Any


METRICS = ('hit@5', 'precision@5', 'recall@5', 'ndcg@5', 'mrr')


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_ci(
    pairs: list[tuple[float, float]], samples: int, seed: int
) -> list[float]:
    rng = random.Random(seed)
    count = len(pairs)
    deltas = [
        statistics.fmean(
            pairs[index][1] - pairs[index][0]
            for index in (rng.randrange(count) for _ in range(count))
        )
        for _ in range(samples)
    ]
    return [percentile(deltas, 0.025), percentile(deltas, 0.975)]


def positive_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row['query_id']): row
        for row in report.get('per_query', [])
        if row.get('query_type') != 'negative'
    }


def compare(
    no_rerank: dict[str, Any],
    rerank: dict[str, Any],
    *,
    bootstrap_samples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    before = positive_rows(no_rerank)
    after = positive_rows(rerank)
    query_ids = sorted(set(before) & set(after))
    result: dict[str, Any] = {
        'baseline': 'vector_no_rerank',
        'candidate': 'vector_rerank',
        'shared_positive_query_count': len(query_ids),
        'metrics': {},
        'breakdown': {},
    }
    for metric_index, metric in enumerate(METRICS):
        pairs = [
            (float(before[query_id][metric]), float(after[query_id][metric]))
            for query_id in query_ids
        ]
        deltas = [candidate - baseline for baseline, candidate in pairs]
        result['metrics'][metric] = {
            'vector_no_rerank': statistics.fmean(value[0] for value in pairs),
            'vector_rerank': statistics.fmean(value[1] for value in pairs),
            'delta_rerank_minus_no_rerank': statistics.fmean(deltas),
            'delta_ci95': paired_ci(
                pairs, bootstrap_samples, bootstrap_seed + metric_index
            ),
            'rerank_wins': sum(delta > 1e-12 for delta in deltas),
            'ties': sum(abs(delta) <= 1e-12 for delta in deltas),
            'rerank_losses': sum(delta < -1e-12 for delta in deltas),
        }

    for field in ('evaluation_slice', 'semantic_variant_type', 'difficulty'):
        groups = sorted(
            {str(before[query_id].get(field) or 'unknown') for query_id in query_ids}
        )
        result['breakdown'][field] = {}
        for group in groups:
            group_ids = [
                query_id
                for query_id in query_ids
                if str(before[query_id].get(field) or 'unknown') == group
            ]
            result['breakdown'][field][group] = {
                metric: {
                    'vector_no_rerank': statistics.fmean(
                        float(before[query_id][metric]) for query_id in group_ids
                    ),
                    'vector_rerank': statistics.fmean(
                        float(after[query_id][metric]) for query_id in group_ids
                    ),
                }
                for metric in ('hit@5', 'ndcg@5', 'mrr')
            }
            result['breakdown'][field][group]['query_count'] = len(group_ids)

    result['negative'] = {
        'vector_no_rerank_empty_result_accuracy': no_rerank['aggregate']['negative'][
            'empty_result_accuracy'
        ],
        'vector_rerank_empty_result_accuracy': rerank['aggregate']['negative'][
            'empty_result_accuracy'
        ],
    }
    return result


def markdown(result: dict[str, Any]) -> str:
    lines = [
        '# Vector Search: rerank off vs rerank on',
        '',
        f"Shared positive queries: {result['shared_positive_query_count']}",
        '',
        '| Metric | No rerank | Rerank | Delta | 95% CI | Wins/Ties/Losses |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for metric, values in result['metrics'].items():
        lower, upper = values['delta_ci95']
        lines.append(
            '| {metric} | {before:.4f} | {after:.4f} | {delta:+.4f} | '
            '[{lower:+.4f}, {upper:+.4f}] | {wins}/{ties}/{losses} |'.format(
                metric=metric,
                before=values['vector_no_rerank'],
                after=values['vector_rerank'],
                delta=values['delta_rerank_minus_no_rerank'],
                lower=lower,
                upper=upper,
                wins=values['rerank_wins'],
                ties=values['ties'],
                losses=values['rerank_losses'],
            )
        )
    negative = result['negative']
    lines.extend(
        [
            '',
            '## Negative queries',
            '',
            '- No-rerank empty-result accuracy: {}'.format(
                negative['vector_no_rerank_empty_result_accuracy']
            ),
            '- Rerank empty-result accuracy: {}'.format(
                negative['vector_rerank_empty_result_accuracy']
            ),
            '',
            'Positive delta means reranking is better; negative delta means it is worse.',
        ]
    )
    return '\n'.join(lines) + '\n'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Compare Vector Search before and after reranking.')
    parser.add_argument('--no-rerank-metrics', type=Path, required=True)
    parser.add_argument('--rerank-metrics', type=Path, required=True)
    parser.add_argument('--output-json', type=Path, required=True)
    parser.add_argument('--output-markdown', type=Path, required=True)
    parser.add_argument('--bootstrap-samples', type=int, default=10000)
    parser.add_argument('--bootstrap-seed', type=int, default=20260826)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = compare(
        load_report(args.no_rerank_metrics),
        load_report(args.rerank_metrics),
        bootstrap_samples=args.bootstrap_samples,
        bootstrap_seed=args.bootstrap_seed,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    report = markdown(result)
    args.output_markdown.write_text(report, encoding='utf-8')
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
