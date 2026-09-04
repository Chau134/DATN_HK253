from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import build_query_records, item_from_row, load_products, read_csv_rows, write_csv_rows


def main() -> int:
    args = parse_args()
    products = load_products(args.products_csv)
    sampled_items = [item_from_row(row) for row in read_csv_rows(args.sampled_items_csv)]
    query_records = build_query_records(
        sampled_items,
        products,
        total_query_count=args.total_query_count,
        seed=args.seed,
        min_candidates=args.min_candidates,
        min_non_self_candidates=args.min_non_self_candidates,
        manual_review_ratio=args.manual_review_ratio,
    )
    fieldnames = list(query_records[0].to_row().keys()) if query_records else [
        "query_id",
        "mode",
        "source_product_id",
        "image_id",
        "image_url",
        "query_text",
        "category",
        "brand",
        "color",
        "material",
        "gender",
        "price_bucket",
        "usage",
        "manual_status",
        "notes",
    ]
    write_csv_rows(args.output_csv, [query.to_row() for query in query_records], fieldnames)
    print(f"generated {len(query_records)} multimodal queries")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate multimodal image + text query set from sampled items.")
    parser.add_argument("--products-csv", type=Path, required=True)
    parser.add_argument("--sampled-items-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "multimodal_queries.csv")
    parser.add_argument("--total-query-count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-candidates", type=int, default=1)
    parser.add_argument("--min-non-self-candidates", type=int, default=1)
    parser.add_argument("--manual-review-ratio", type=float, default=0.2)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
