from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
CHALLENGE_DIR = SCRIPT_DIR.parent
TEXT_DIR = CHALLENGE_DIR.parent


@dataclass(frozen=True)
class Variant:
    source_query_id: str
    variant_type: str
    review_risk: str
    query_text: str
    rationale: str


VARIANTS = (
    Variant('text-q0001', 'category_synonym', 'low', 'áo phông tông nâu sô-cô-la', 'áo phông và áo thun là cách gọi tương đương'),
    Variant('text-q0010', 'category_synonym', 'low', 'áo phông dành cho nữ', 'thay áo thun bằng cách gọi phổ biến áo phông'),
    Variant('text-q0018', 'category_synonym', 'medium', 'đồ liền thân Zara màu đen bằng vải elastane', 'diễn đạt bodysuit bằng mô tả tiếng Việt'),
    Variant('text-q0021', 'category_synonym', 'medium', 'áo blazer để mặc xuống phố', 'dùng blazer và diễn đạt lại mục đích dạo phố'),
    Variant('text-q0029', 'category_synonym', 'medium', 'đồ bay nữ trong tầm một đến hai triệu', 'đồ bay là cách gọi thông dụng của jumpsuit'),
    Variant('text-q0036', 'category_synonym', 'low', 'đầm của Zara', 'rút gọn váy và đầm thành đầm'),
    Variant('text-q0044', 'category_synonym', 'medium', 'đồ bay bằng polyester', 'thay jumpsuit bằng đồ bay'),
    Variant('text-q0051', 'category_synonym', 'medium', 'đồ knitwear để mặc xuống phố', 'dùng từ vay mượn knitwear và paraphrase dạo phố'),
    Variant('text-q0077', 'category_synonym', 'medium', 'áo blazer tầm nửa triệu đến một triệu', 'dùng blazer và cách nói giá tự nhiên'),
    Variant('text-q0084', 'category_synonym', 'low', 'áo phông của Zara', 'thay áo thun bằng áo phông'),
    Variant('text-q0006', 'material_synonym', 'medium', 'áo phông Zara tông be bằng vải bông', 'cotton được diễn đạt bằng vải bông'),
    Variant('text-q0026', 'material_synonym', 'medium', 'đồ liền thân nữ bằng ni-lông polyamide để đi hẹn hò', 'kết hợp tên phổ thông và tên kỹ thuật của polyamide'),
    Variant('text-q0042', 'material_synonym', 'high', 'quần dài Zara màu trắng bằng rayon', 'rayon thường được dùng gần nghĩa với viscose trong mô tả thời trang'),
    Variant('text-q0048', 'material_synonym', 'high', 'đồ bay Zara màu xanh dương vừa bằng vải bông', 'đồng thời paraphrase category, sắc độ và cotton'),
    Variant('text-q0049', 'material_synonym', 'medium', 'áo phông trắng bằng vải bông để mặc xuống phố', 'paraphrase category, cotton và dạo phố'),
    Variant('text-q0062', 'material_synonym', 'high', 'quần dài nữ bằng rayon để mặc xuống phố', 'rayon thay viscose và xuống phố thay dạo phố'),
    Variant('text-q0002', 'conversational_constraint', 'low', 'mình cần đầm nữ vải cotton để mặc xuống phố', 'chuyển truy vấn facet sang câu nói tự nhiên'),
    Variant('text-q0003', 'conversational_constraint', 'low', 'tìm sơ mi nữ mặc đi tiệc, ngân sách từ nửa triệu tới một triệu', 'paraphrase usage và khoảng giá'),
    Variant('text-q0033', 'conversational_constraint', 'low', 'sơ mi nữ mặc công sở trong tầm 500 nghìn tới một triệu', 'đi làm được diễn đạt bằng mặc công sở'),
    Variant('text-q0035', 'conversational_constraint', 'low', 'bodysuit giá khoảng hai trăm đến năm trăm nghìn', 'viết khoảng giá bằng từ tự nhiên'),
    Variant('text-q0063', 'conversational_constraint', 'low', 'quần dài nữ mặc hằng ngày, ngân sách nửa triệu tới một triệu', 'đổi trật tự và cách diễn đạt giá'),
    Variant('text-q0075', 'conversational_constraint', 'medium', 'cần áo hai dây, áo sát nách hay áo yếm nữ để đi hẹn hò, ngân sách 200 đến 500 nghìn', 'giữ nhóm category nhưng chuyển thành câu hội thoại'),
    Variant('text-q0081', 'conversational_constraint', 'medium', 'đồ knitwear nữ mặc công sở, giá khoảng nửa triệu tới một triệu', 'dùng knitwear và paraphrase đi làm'),
    Variant('text-q0087', 'conversational_constraint', 'low', 'quần dài nữ mặc đi chơi, tầm một đến hai triệu', 'đổi trật tự và cách nói khoảng giá'),
    Variant('text-q0008', 'description_paraphrase', 'high', 'quần bó đen lưng cao bản to, chất vải đàn hồi', 'mô tả lại tên sản phẩm singleton bằng từ đồng nghĩa'),
    Variant('text-q0022', 'description_paraphrase', 'medium', 'quần lửng xám nhạt có phần gấu nhún', 'capri được diễn đạt bằng quần lửng'),
    Variant('text-q0054', 'description_paraphrase', 'high', 'đồ liền thân xanh hải quân bằng polyamide, cổ cao, buộc dây và hở lưng', 'paraphrase tên sản phẩm singleton'),
    Variant('text-q0058', 'description_paraphrase', 'high', 'đồ bay kaki sẫm bằng lyocell, cổ ve và có túi nổi', 'paraphrase jumpsuit, màu và kiểu túi'),
    Variant('text-q0089', 'description_paraphrase', 'high', 'jeans xanh nhạt dáng thùng thình ống rộng, hiệu ứng vẩy sơn', 'paraphrase tên sản phẩm singleton'),
    Variant('text-q0030', 'description_paraphrase', 'high', 'đồ bay satin hồng cánh sen, ống rộng bất đối xứng và dây ánh vàng', 'paraphrase tên sản phẩm singleton'),
)


REVIEW_FIELDS = (
    'review_priority',
    'review_risk',
    'variant_query_id',
    'source_query_id',
    'variant_type',
    'original_query_text',
    'proposed_query_text',
    'canonical_constraints',
    'expected_relevant_count',
    'ground_truth_rows',
    'rationale',
    'equivalence_question',
    'reviewer_decision',
    'approved_query_text',
    'reviewer_notes',
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, str]], fields: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def union_fields(rows: Iterable[dict[str, str]], preferred: Iterable[str] = ()) -> list[str]:
    fields = list(preferred)
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    return fields


def variant_id(index: int) -> str:
    return f'text-sem-v1-q{index:04d}'


def constraint_summary(query: dict[str, str]) -> str:
    fields = ('category', 'brand', 'color', 'material', 'gender', 'price_bucket', 'usage')
    values = [f'{field}={query[field]}' for field in fields if query.get(field, '').strip()]
    return '; '.join(values) or 'product_name=' + query.get('query_text', '')


def build_rows(
    source_queries: list[dict[str, str]],
    source_ground_truth: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    query_by_id = {row['query_id']: row for row in source_queries}
    gt_by_id: dict[str, list[dict[str, str]]] = {}
    for row in source_ground_truth:
        gt_by_id.setdefault(row['query_id'], []).append(row)

    if len(VARIANTS) != 30:
        raise ValueError(f'Expected 30 semantic variants, got {len(VARIANTS)}')
    if len({item.source_query_id for item in VARIANTS}) != len(VARIANTS):
        raise ValueError('Each semantic variant must use a distinct source query')

    candidate_queries: list[dict[str, str]] = []
    candidate_ground_truth: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    for index, variant in enumerate(VARIANTS, start=1):
        if variant.source_query_id not in query_by_id:
            raise ValueError(f'Missing source query: {variant.source_query_id}')
        source = query_by_id[variant.source_query_id]
        if source.get('query_type') != 'positive':
            raise ValueError(f'Semantic variant source must be positive: {variant.source_query_id}')
        target_id = variant_id(index)
        target = dict(source)
        target.update(
            {
                'query_id': target_id,
                'query_text': variant.query_text,
                'difficulty': 'semantic',
                'manual_status': 'pending',
                'source_query_id': variant.source_query_id,
                'evaluation_slice': 'semantic_challenge_v1',
                'semantic_variant_type': variant.variant_type,
                'notes': f'semantic_variant_of={variant.source_query_id};review_required',
            }
        )
        candidate_queries.append(target)

        source_gt = gt_by_id.get(variant.source_query_id, [])
        if not source_gt:
            raise ValueError(f'Source query has no ground truth: {variant.source_query_id}')
        for row in source_gt:
            cloned = dict(row)
            cloned.update(
                {
                    'query_id': target_id,
                    'source': 'inherited_from_approved_v2_after_equivalence_review',
                    'review_status': 'pending',
                    'notes': f'provisional_clone_of={variant.source_query_id}',
                }
            )
            candidate_ground_truth.append(cloned)

        review_rows.append(
            {
                'review_priority': 'required',
                'review_risk': variant.review_risk,
                'variant_query_id': target_id,
                'source_query_id': variant.source_query_id,
                'variant_type': variant.variant_type,
                'original_query_text': source.get('query_text', ''),
                'proposed_query_text': variant.query_text,
                'canonical_constraints': constraint_summary(source),
                'expected_relevant_count': source.get('expected_relevant_count', ''),
                'ground_truth_rows': str(len(source_gt)),
                'rationale': variant.rationale,
                'equivalence_question': 'Câu mới có giữ nguyên đầy đủ ý định và mọi ràng buộc của câu gốc không?',
                'reviewer_decision': 'pending',
                'approved_query_text': '',
                'reviewer_notes': '',
            }
        )
    return candidate_queries, candidate_ground_truth, review_rows


def write_runner_configs(*, combined_count: int = 130, semantic_count: int = 30) -> None:
    config_dir = TEXT_DIR / 'configs'
    config_dir.mkdir(parents=True, exist_ok=True)
    configs = {
        'text_search_v3_semantic.yaml': {
            'schema_version': 'v3-semantic',
            'mode': 'text',
            'query_count': combined_count,
            'relevance_policy': 'v2_canonical_plus_reviewed_semantic_equivalence',
            'paths': {
                'products_csv': 'data/product_snapshot.csv',
                'query_set_csv': 'data/text_queries_v3_semantic.csv',
                'ground_truth_csv': 'data/ground_truth_text_v3_semantic.csv',
                'search_results_csv': 'data/search_results_text_v3_semantic.csv',
                'metrics_json': 'reports/metrics_text_v3_semantic.json',
                'metrics_csv': 'reports/metrics_text_v3_semantic.csv',
            },
        },
        'text_search_semantic_only_v1.yaml': {
            'schema_version': 'semantic-only-v1',
            'mode': 'text',
            'query_count': semantic_count,
            'relevance_policy': 'ground_truth_inherited_after_query_equivalence_review',
            'paths': {
                'products_csv': 'data/product_snapshot.csv',
                'query_set_csv': 'semantic_challenge/data/text_queries_semantic_only_v1.csv',
                'ground_truth_csv': 'semantic_challenge/data/ground_truth_text_semantic_only_v1.csv',
                'search_results_csv': 'semantic_challenge/reports/search_results_vector_no_rerank.csv',
                'metrics_json': 'semantic_challenge/reports/metrics_vector_no_rerank.json',
                'metrics_csv': 'semantic_challenge/reports/metrics_vector_no_rerank.csv',
            },
        },
    }
    for filename, config in configs.items():
        (config_dir / filename).write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )


def main() -> int:
    parser = argparse.ArgumentParser(description='Build semantic challenge candidates and review sheet.')
    parser.add_argument('--queries', type=Path, default=TEXT_DIR / 'data' / 'text_queries_v2.csv')
    parser.add_argument('--ground-truth', type=Path, default=TEXT_DIR / 'data' / 'ground_truth_text_v2.csv')
    args = parser.parse_args()

    candidates, ground_truth, review = build_rows(read_csv(args.queries), read_csv(args.ground_truth))
    data_dir = CHALLENGE_DIR / 'data'
    write_csv(data_dir / 'text_queries_semantic_candidates_v1.csv', candidates, union_fields(candidates))
    write_csv(data_dir / 'ground_truth_text_semantic_candidates_v1.csv', ground_truth, union_fields(ground_truth))
    write_csv(CHALLENGE_DIR / 'review' / 'semantic_query_review.csv', review, REVIEW_FIELDS)
    write_runner_configs()
    print(f'candidates={len(candidates)} ground_truth_rows={len(ground_truth)} review_rows={len(review)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
