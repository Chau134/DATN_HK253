from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compare_runs import paired_bootstrap
from keyword_baseline import (
    BM25KeywordIndex,
    IndexedProduct,
    build_documents,
    tokenize,
)


class TokenizeTests(unittest.TestCase):
    def test_removes_query_scaffolding_but_keeps_product_terms(self) -> None:
        self.assertEqual(
            tokenize('Tìm áo sơ mi màu đen phù hợp cho nữ'),
            ['ao', 'so', 'mi', 'den', 'nu'],
        )

    def test_checks_stop_words_before_removing_accents(self) -> None:
        self.assertEqual(
            tokenize('đen đến 1 triệu'),
            ['den', '1', 'trieu'],
        )


class BM25KeywordIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = BM25KeywordIndex(
            [
                IndexedProduct(
                    '1',
                    ('ao', 'so', 'mi', 'den', 'nu'),
                    frozenset({'ao', 'so', 'mi', 'den', 'nu'}),
                ),
                IndexedProduct(
                    '2',
                    ('ao', 'thun', 'trang', 'nam'),
                    frozenset({'ao', 'thun', 'trang', 'nam'}),
                ),
            ]
        )

    def test_exact_keyword_match_ranks_first(self) -> None:
        results = self.index.search(
            'áo sơ mi đen nữ',
            top_k=5,
            minimum_token_coverage=0.6,
            minimum_should_match=1,
        )
        self.assertEqual(results[0].product_id, '1')
        self.assertEqual(
            results[0].matched_terms,
            ('ao', 'so', 'mi', 'den', 'nu'),
        )

    def test_impossible_query_can_return_empty(self) -> None:
        results = self.index.search(
            'áo nike tím neon',
            top_k=5,
            minimum_token_coverage=0.75,
            minimum_should_match=1,
        )
        self.assertEqual(results, [])


class ProductDocumentTests(unittest.TestCase):
    def test_build_documents_adds_price_bucket_terms(self) -> None:
        products = [
            {
                'product_id': '10',
                'product_name': 'Áo sơ mi',
                'category': 'Áo sơ mi',
                'brand': 'Zara',
                'color': 'Đen',
                'material': 'Cotton',
                'gender': 'Nữ',
                'price': '699000',
                'usage': 'đi làm',
                'is_active': 'true',
                'description': '',
            }
        ]
        weights = {
            'product_name': 1,
            'category': 1,
            'brand': 1,
            'color': 1,
            'material': 1,
            'gender': 1,
            'price_bucket': 1,
            'usage': 1,
            'description': 1,
        }
        document = build_documents(products, weights)[0]
        self.assertTrue(
            {'500k', '1', 'trieu'}.issubset(document.unique_tokens)
        )


class BootstrapTests(unittest.TestCase):
    def test_paired_bootstrap_uses_same_query_pair(self) -> None:
        lower, upper = paired_bootstrap(
            [(0.0, 1.0), (0.0, 1.0)],
            samples=100,
            seed=42,
        )
        self.assertEqual((lower, upper), (1.0, 1.0))


if __name__ == '__main__':
    unittest.main()
