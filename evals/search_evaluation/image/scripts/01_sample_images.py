from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import annotation_rows_from_images, ensure_parent_dir, load_image_records, load_json_config, sample_images_for_queries, write_csv_rows


def main() -> int:
    args = parse_args()
    config = load_json_config(args.config)
    images = load_image_records(args.products_csv, args.product_images_csv)
    sampled_images = sample_images_for_queries(
        images,
        total_count=args.query_count,
        seed=args.seed,
        min_per_category=args.min_per_category,
        max_per_category=args.max_per_category,
    )

    image_fields = list(sampled_images[0].to_row().keys()) if sampled_images else [
        "source_image_id",
        "source_product_id",
        "product_name",
        "category",
        "brand",
        "color",
        "material",
        "gender",
        "image_url",
        "db_image_type",
        "sort_order",
        "image_count",
    ]
    write_csv_rows(args.output_csv, [image.to_row() for image in sampled_images], image_fields)
    write_csv_rows(
        args.annotation_csv,
        annotation_rows_from_images(sampled_images),
        ["source_image_id", "source_product_id", "image_url", "db_image_type", "sort_order", "semantic_image_type", "image_quality", "review_status", "notes"],
    )

    summary = {
        "input_images": len(images),
        "sampled_images": len(sampled_images),
        "query_count": args.query_count,
        "seed": args.seed,
        "config_mode": config.get("mode", "image"),
    }
    ensure_parent_dir(args.summary_json)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample product images for image search evaluation.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR.parent / "configs" / "image_search.yaml")
    parser.add_argument("--products-csv", type=Path, required=True)
    parser.add_argument("--product-images-csv", type=Path)
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "sampled_images.csv")
    parser.add_argument("--annotation-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_annotations.csv")
    parser.add_argument("--summary-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "sample_summary.json")
    parser.add_argument("--query-count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-per-category", type=int, default=5)
    parser.add_argument("--max-per-category", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
