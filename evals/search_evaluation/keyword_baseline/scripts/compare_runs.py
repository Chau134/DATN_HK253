from __future__ import annotations

import argparse
import json
import random
import statistics
import tomllib
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
BASELINE_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = BASELINE_DIR / 'configs' / 'keyword_bm25.toml'
METRICS = ('hit@5', 'precision@5', 'recall@5', 'ndcg@5', 'mrr')


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def load_config(path: Path) -> dict[str, Any]:
    with path.open('rb') as handle:
        return tomllib.load(handle)


def resolve_config_path(config_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (config_path.parent / path).resolve()


def percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return 0.0
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return (
        sorted_values[lower] * (1.0 - fraction)
        + sorted_values[upper] * fraction
    )


def paired_bootstrap(
    pairs: list[tuple[float, float]],
    *,
    samples: int,
    seed: int,
) -> tuple[float, float]:
    if not pairs:
        return 0.0, 0.0
    rng = random.Random(seed)
    count = len(pairs)
    deltas: list[float] = []
    for _ in range(samples):
        sampled: list[float] = []
        for _ in range(count):
            baseline_value, candidate_value = pairs[rng.randrange(count)]
            sampled.append(candidate_value - baseline_value)
        deltas.append(statistics.fmean(sampled))
    deltas.sort()
    return percentile(deltas, 0.025), percentile(deltas, 0.975)


def positive_per_query(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row['query_id']): row
        for row in report.get('per_query', [])
        if row.get('query_type') != 'negative'
    }


def compare_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    bootstrap_samples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    baseline_queries = positive_per_query(baseline)
    candidate_queries = positive_per_query(candidate)
    shared_ids = sorted(set(baseline_queries) & set(candidate_queries))
    comparison: dict[str, Any] = {
        'baseline': 'keyword_bm25',
        'candidate': 'vector_no_rerank',
        'shared_positive_query_count': len(shared_ids),
        'metrics': {},
        'breakdown': {},
    }
    for metric_index, metric in enumerate(METRICS):
        pairs = [
            (
                float(baseline_queries[query_id].get(metric, 0.0)),
                float(candidate_queries[query_id].get(metric, 0.0)),
            )
            for query_id in shared_ids
        ]
        baseline_values = [pair[0] for pair in pairs]
        candidate_values = [pair[1] for pair in pairs]
        deltas = [
            candidate_value - baseline_value
            for baseline_value, candidate_value in pairs
        ]
        lower, upper = paired_bootstrap(
            pairs,
            samples=bootstrap_samples,
            seed=bootstrap_seed + metric_index,
        )
        comparison['metrics'][metric] = {
            'keyword_bm25': (
                statistics.fmean(baseline_values) if baseline_values else 0.0
            ),
            'vector_no_rerank': (
                statistics.fmean(candidate_values) if candidate_values else 0.0
            ),
            'delta_vector_minus_keyword': (
                statistics.fmean(deltas) if deltas else 0.0
            ),
            'delta_ci95': [lower, upper],
            'vector_wins': sum(delta > 1e-12 for delta in deltas),
            'ties': sum(abs(delta) <= 1e-12 for delta in deltas),
            'vector_losses': sum(delta < -1e-12 for delta in deltas),
        }

    for field in ('intent_type', 'difficulty'):
        groups = sorted(
            {
                str(baseline_queries[query_id].get(field) or 'unknown')
                for query_id in shared_ids
            }
        )
        comparison['breakdown'][field] = {}
        for group in groups:
            group_ids = [
                query_id
                for query_id in shared_ids
                if str(baseline_queries[query_id].get(field) or 'unknown')
                == group
            ]
            comparison['breakdown'][field][group] = {
                metric: {
                    'keyword_bm25': statistics.fmean(
                        float(baseline_queries[query_id].get(metric, 0.0))
                        for query_id in group_ids
                    ),
                    'vector_no_rerank': statistics.fmean(
                        float(candidate_queries[query_id].get(metric, 0.0))
                        for query_id in group_ids
                    ),
                }
                for metric in ('hit@5', 'ndcg@5', 'mrr')
            }

    comparison['negative'] = {
        'keyword_empty_result_accuracy': (
            baseline.get('aggregate', {})
            .get('negative', {})
            .get('empty_result_accuracy')
        ),
        'vector_empty_result_accuracy': (
            candidate.get('aggregate', {})
            .get('negative', {})
            .get('empty_result_accuracy')
        ),
    }
    return comparison


def markdown_report(comparison: dict[str, Any]) -> str:
    lines = [
        '# Keyword BM25 vs Vector Search (rerank off)',
        '',
        'Shared positive queries: {}'.format(
            comparison['shared_positive_query_count']
        ),
        '',
        (
            '| Metric | Keyword BM25 | Vector no rerank | Delta | 95% CI | '
            'Wins/Ties/Losses |'
        ),
        '|---|---:|---:|---:|---:|---:|',
    ]
    for metric, values in comparison['metrics'].items():
        lower, upper = values['delta_ci95']
        lines.append(
            (
                '| {metric} | {keyword:.4f} | {vector:.4f} | {delta:+.4f} | '
                '[{lower:+.4f}, {upper:+.4f}] | {wins}/{ties}/{losses} |'
            ).format(
                metric=metric,
                keyword=values['keyword_bm25'],
                vector=values['vector_no_rerank'],
                delta=values['delta_vector_minus_keyword'],
                lower=lower,
                upper=upper,
                wins=values['vector_wins'],
                ties=values['ties'],
                losses=values['vector_losses'],
            )
        )
    negative = comparison['negative']
    lines.extend(
        [
            '',
            '## Negative queries',
            '',
            '- Keyword empty-result accuracy: {}'.format(
                negative['keyword_empty_result_accuracy']
            ),
            '- Vector empty-result accuracy: {}'.format(
                negative['vector_empty_result_accuracy']
            ),
            '',
            'Positive delta means Vector Search is better than Keyword BM25.',
        ]
    )
    return '\n'.join(lines) + '\n'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Compare keyword baseline with vector no-rerank metrics.'
    )
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--baseline-metrics', type=Path, default=None)
    parser.add_argument('--candidate-metrics', type=Path, default=None)
    parser.add_argument('--output-json', type=Path, default=None)
    parser.add_argument('--output-markdown', type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve()
    config = load_config(config_path)
    paths = config['paths']
    evaluation = config['evaluation']
    baseline_path = args.baseline_metrics or resolve_config_path(
        config_path,
        paths['metrics_json'],
    )
    candidate_path = args.candidate_metrics or resolve_config_path(
        config_path,
        paths['vector_metrics_json'],
    )
    output_json = args.output_json or resolve_config_path(
        config_path,
        paths['comparison_json'],
    )
    output_markdown = args.output_markdown or resolve_config_path(
        config_path,
        paths['comparison_markdown'],
    )
    comparison = compare_reports(
        load_json(baseline_path),
        load_json(candidate_path),
        bootstrap_samples=int(evaluation['bootstrap_samples']),
        bootstrap_seed=int(evaluation['bootstrap_seed']),
    )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    report = markdown_report(comparison)
    output_markdown.write_text(report, encoding='utf-8')
    print(report)
    print('comparison -> {} , {}'.format(output_json, output_markdown))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
