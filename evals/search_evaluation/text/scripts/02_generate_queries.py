from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import build_query_records, load_products, write_csv_rows


def main() -> int:
    args = parse_args()
    products = load_products(args.sampled_products_csv)
    query_records = build_query_records(products, total_query_count=args.total_query_count, positive_ratio=args.positive_ratio, seed=args.seed)
    fieldnames = list(query_records[0].to_row().keys()) if query_records else ["query_id", "mode", "query_type", "source_product_id", "query_text", "category", "brand", "color", "material", "gender", "price_bucket", "usage", "manual_status", "notes"]
    write_csv_rows(args.output_csv, [query_record.to_row() for query_record in query_records], fieldnames)
    print(f"generated {len(query_records)} queries")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate text search queries from sampled products.")
    parser.add_argument("--sampled-products-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "text_queries.csv")
    parser.add_argument("--total-query-count", type=int, default=100)
    parser.add_argument("--positive-ratio", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())