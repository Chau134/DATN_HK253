from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import ensure_parent_dir, enrich_product_categories, load_categories, load_json_config, load_product_category_map, load_products, sample_products_for_queries, write_csv_rows


def main() -> int:
    args = parse_args()
    config = load_json_config(args.config)
    products = load_products(args.products_csv)

    if args.product_categories_csv and args.categories_csv:
        products = enrich_product_categories(
            products,
            load_product_category_map(args.product_categories_csv),
            load_categories(args.categories_csv),
        )

    sampled_products = sample_products_for_queries(
        products,
        total_positive_count=args.positive_count,
        seed=args.seed,
        min_per_category=args.min_per_category,
        max_per_category=args.max_per_category,
    )

    fieldnames = list(sampled_products[0].to_row().keys()) if sampled_products else ["product_id", "product_name", "category", "brand", "color", "material", "gender", "price", "usage", "is_active", "description", "price_bucket"]
    write_csv_rows(args.output_csv, [product.to_row() for product in sampled_products], fieldnames)

    summary = {
        "input_products": len(products),
        "sampled_products": len(sampled_products),
        "positive_count": args.positive_count,
        "seed": args.seed,
        "config_mode": config.get("mode", "text"),
    }
    ensure_parent_dir(args.summary_json)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample products for text search evaluation using stratified category sampling.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR.parent / "configs" / "text_search.yaml")
    parser.add_argument("--products-csv", type=Path, required=True)
    parser.add_argument("--product-categories-csv", type=Path)
    parser.add_argument("--categories-csv", type=Path)
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "sampled_products.csv")
    parser.add_argument("--summary-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "sample_summary.json")
    parser.add_argument("--positive-count", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-per-category", type=int, default=5)
    parser.add_argument("--max-per-category", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())