from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import ensure_parent_dir, load_json_config, load_multimodal_items, load_products, sample_items_for_queries, write_csv_rows


def main() -> int:
    args = parse_args()
    config = load_json_config(args.config)
    products = load_products(args.products_csv)
    items = load_multimodal_items(args.products_csv, args.product_images_csv)
    sampled_items = sample_items_for_queries(
        items,
        products,
        total_count=args.query_count,
        seed=args.seed,
        min_per_category=args.min_per_category,
        max_per_category=args.max_per_category,
        max_products=args.max_products,
    )

    fieldnames = list(sampled_items[0].to_row().keys()) if sampled_items else [
        "product_id",
        "product_name",
        "category",
        "brand",
        "color",
        "material",
        "gender",
        "price",
        "usage",
        "image_id",
        "image_url",
        "price_bucket",
    ]
    write_csv_rows(args.output_csv, [item.to_row() for item in sampled_items], fieldnames)

    summary = {
        "input_products": len(products),
        "input_items": len(items),
        "sampled_items": len(sampled_items),
        "query_count": args.query_count,
        "seed": args.seed,
        "max_products": args.max_products,
        "config_mode": config.get("mode", "multimodal"),
    }
    ensure_parent_dir(args.summary_json)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample products with one valid image each for multimodal search evaluation.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR.parent / "configs" / "multimodal_search.yaml")
    parser.add_argument("--products-csv", type=Path, required=True)
    parser.add_argument("--product-images-csv", type=Path)
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "sampled_multimodal_items.csv")
    parser.add_argument("--summary-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "sample_summary.json")
    parser.add_argument("--query-count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-products", type=int, default=5000)
    parser.add_argument("--min-per-category", type=int, default=5)
    parser.add_argument("--max-per-category", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
