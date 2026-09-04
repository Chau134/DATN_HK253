from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import tomllib
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASELINE_DIR = SCRIPT_DIR.parent
WORD_RE = re.compile(r'[^\W_]+', flags=re.UNICODE)

# Stop words are checked before accent removal so đen and đến remain distinct.
STOP_WORDS = {
    'tìm',
    'kiếm',
    'giúp',
    'tôi',
    'mình',
    'cần',
    'muốn',
    'sản',
    'phẩm',
    'mẫu',
    'phù',
    'hợp',
    'cho',
    'màu',
    'chất',
    'liệu',
    'làm',
    'từ',
    'đến',
    'giá',
    'khoảng',
    'hiệu',
    'loại',
    'có',
    'và',
    'hoặc',
}

RESULT_FIELDS = [
    'run_id',
    'query_id',
    'mode',
    'rank',
    'product_id',
    'score',
    'raw_score_json',
]


@dataclass(frozen=True)
class IndexedProduct:
    product_id: str
    tokens: tuple[str, ...]
    unique_tokens: frozenset[str]


@dataclass(frozen=True)
class RankedProduct:
    product_id: str
    score: float
    matched_terms: tuple[str, ...]
    query_terms: tuple[str, ...]
    required_match_count: int

    @property
    def token_coverage(self) -> float:
        if not self.query_terms:
            return 0.0
        return len(self.matched_terms) / len(self.query_terms)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize(
        'NFKD',
        value.replace('đ', 'd').replace('Đ', 'D'),
    )
    return ''.join(character for character in normalized if not unicodedata.combining(character))


def tokenize(value: str | None) -> list[str]:
    if not value:
        return []
    output: list[str] = []
    for original in WORD_RE.findall(str(value).casefold()):
        if original in STOP_WORDS:
            continue
        token = re.sub(r'[^0-9a-z]+', '', strip_accents(original).casefold())
        if token:
            output.append(token)
    return output


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def load_config(path: Path) -> dict[str, Any]:
    with path.open('rb') as handle:
        return tomllib.load(handle)


def resolve_config_path(config_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (config_path.parent / path).resolve()


def price_bucket_label(raw_price: str | None) -> str:
    try:
        price = float(str(raw_price or '').replace(',', '').strip())
    except ValueError:
        return ''
    if price < 200_000:
        return 'dưới 200k'
    if price < 500_000:
        return '200k đến 500k'
    if price < 1_000_000:
        return '500k đến 1 triệu'
    if price < 2_000_000:
        return '1 đến 2 triệu'
    return 'trên 2 triệu'


def weighted_tokens(row: dict[str, str], weights: dict[str, int]) -> tuple[str, ...]:
    fields = {
        'product_name': row.get('product_name', ''),
        'category': row.get('category', ''),
        'brand': row.get('brand', ''),
        'color': row.get('color', ''),
        'material': row.get('material', ''),
        'gender': row.get('gender', ''),
        'price_bucket': price_bucket_label(row.get('price')),
        'usage': row.get('usage', ''),
        'description': row.get('description', ''),
    }
    output: list[str] = []
    for field, value in fields.items():
        output.extend(tokenize(value) * max(0, int(weights.get(field, 1))))
    return tuple(output)


def build_documents(
    product_rows: list[dict[str, str]],
    weights: dict[str, int],
) -> list[IndexedProduct]:
    documents: list[IndexedProduct] = []
    for row in product_rows:
        active = str(row.get('is_active', '')).strip().casefold()
        if active not in {'1', 'true', 'yes', 'active'}:
            continue
        product_id = str(row.get('product_id', '')).strip()
        if not product_id:
            continue
        tokens = weighted_tokens(row, weights)
        documents.append(
            IndexedProduct(
                product_id=product_id,
                tokens=tokens,
                unique_tokens=frozenset(tokens),
            )
        )
    return documents


class BM25KeywordIndex:
    def __init__(
        self,
        documents: list[IndexedProduct],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if not documents:
            raise ValueError('Keyword index requires at least one active product.')
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.average_document_length = statistics.fmean(
            len(document.tokens) for document in documents
        )
        self.term_frequencies = [Counter(document.tokens) for document in documents]
        document_frequency: Counter[str] = Counter()
        for document in documents:
            document_frequency.update(document.unique_tokens)
        document_count = len(documents)
        self.idf = {
            term: math.log(
                1.0 + (document_count - frequency + 0.5) / (frequency + 0.5)
            )
            for term, frequency in document_frequency.items()
        }

    def search(
        self,
        query_text: str,
        *,
        top_k: int,
        minimum_token_coverage: float,
        minimum_should_match: int,
    ) -> list[RankedProduct]:
        query_terms = tuple(dict.fromkeys(tokenize(query_text)))
        if not query_terms:
            return []
        required_match_count = max(
            minimum_should_match,
            math.ceil(len(query_terms) * minimum_token_coverage),
        )
        ranked: list[RankedProduct] = []
        for document, frequencies in zip(
            self.documents,
            self.term_frequencies,
            strict=True,
        ):
            matched_terms = tuple(
                term for term in query_terms if term in document.unique_tokens
            )
            if len(matched_terms) < required_match_count:
                continue
            score = self.score(frequencies, len(document.tokens), query_terms)
            if score <= 0:
                continue
            ranked.append(
                RankedProduct(
                    product_id=document.product_id,
                    score=score,
                    matched_terms=matched_terms,
                    query_terms=query_terms,
                    required_match_count=required_match_count,
                )
            )
        ranked.sort(key=lambda item: (-item.score, product_id_sort_key(item.product_id)))
        return ranked[:top_k]

    def score(
        self,
        frequencies: Counter[str],
        document_length: int,
        query_terms: tuple[str, ...],
    ) -> float:
        score = 0.0
        length_ratio = document_length / self.average_document_length
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if frequency <= 0:
                continue
            denominator = frequency + self.k1 * (
                1.0 - self.b + self.b * length_ratio
            )
            score += (
                self.idf.get(term, 0.0)
                * frequency
                * (self.k1 + 1.0)
                / denominator
            )
        return score


def product_id_sort_key(product_id: str) -> tuple[int, int | str]:
    try:
        return 0, int(product_id)
    except ValueError:
        return 1, product_id


def result_rows_for_query(
    run_id: str,
    query_id: str,
    ranked: list[RankedProduct],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, item in enumerate(ranked, start=1):
        rows.append(
            {
                'run_id': run_id,
                'query_id': query_id,
                'mode': 'text',
                'rank': rank,
                'product_id': item.product_id,
                'score': f'{item.score:.12f}',
                'raw_score_json': json.dumps(
                    {
                        'algorithm': 'bm25_field_weighted',
                        'bm25_score': item.score,
                        'query_terms': item.query_terms,
                        'matched_terms': item.matched_terms,
                        'required_match_count': item.required_match_count,
                        'token_coverage': item.token_coverage,
                    },
                    ensure_ascii=False,
                    separators=(',', ':'),
                ),
            }
        )
    return rows


def run(config_path: Path, *, run_id: str | None = None) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = load_config(config_path)
    paths = config['paths']
    ranking = config['ranking']
    products_csv = resolve_config_path(config_path, paths['products_csv'])
    query_set_csv = resolve_config_path(config_path, paths['query_set_csv'])
    results_csv = resolve_config_path(config_path, paths['results_csv'])
    metadata_json = resolve_config_path(config_path, paths['run_metadata_json'])

    documents = build_documents(
        read_csv_rows(products_csv),
        ranking['field_weights'],
    )
    query_rows = read_csv_rows(query_set_csv)
    index = BM25KeywordIndex(
        documents,
        k1=float(ranking['k1']),
        b=float(ranking['b']),
    )
    actual_run_id = run_id or datetime.now(timezone.utc).strftime(
        'keyword-bm25-%Y%m%dT%H%M%SZ'
    )

    output_rows: list[dict[str, Any]] = []
    result_count_by_query: dict[str, int] = {}
    for query in query_rows:
        query_id = str(query.get('query_id', '')).strip()
        query_text = str(query.get('query_text', '')).strip()
        ranked = index.search(
            query_text,
            top_k=int(ranking['top_k']),
            minimum_token_coverage=float(ranking['minimum_token_coverage']),
            minimum_should_match=int(ranking['minimum_should_match']),
        )
        output_rows.extend(result_rows_for_query(actual_run_id, query_id, ranked))
        result_count_by_query[query_id] = len(ranked)

    write_csv_rows(results_csv, output_rows)
    metadata = {
        'run_id': actual_run_id,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'algorithm': config['algorithm'],
        'config': str(config_path),
        'products_csv': str(products_csv),
        'query_set_csv': str(query_set_csv),
        'results_csv': str(results_csv),
        'product_count': len(documents),
        'query_count': len(query_rows),
        'result_row_count': len(output_rows),
        'empty_query_count': sum(
            1 for count in result_count_by_query.values() if count == 0
        ),
        'ranking': ranking,
        'data_access_policy': (
            'ranking reads query_id/query_text only; testcase facets and '
            'ground truth are not read'
        ),
    }
    metadata_json.parent.mkdir(parents=True, exist_ok=True)
    metadata_json.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run the offline BM25 keyword baseline.'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=BASELINE_DIR / 'configs' / 'keyword_bm25.toml',
    )
    parser.add_argument('--run-id', type=str, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = run(args.config, run_id=args.run_id)
    print(
        (
            'run_id={run_id} products={product_count} queries={query_count} '
            'rows={result_row_count} empty_queries={empty_query_count}'
        ).format(**metadata)
    )
    print('results -> {}'.format(metadata['results_csv']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
