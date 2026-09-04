from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import ProductImageRecord, build_image_query_records, read_csv_rows, write_csv_rows


def main() -> int:
    args = parse_args()
    sampled_images = [_image_from_row(row) for row in read_csv_rows(args.sampled_images_csv)]
    annotations = read_csv_rows(args.annotation_csv) if args.annotation_csv.exists() else []
    query_records = build_image_query_records(sampled_images, annotations)
    fieldnames = list(query_records[0].to_row().keys()) if query_records else [
        "query_id",
        "mode",
        "source_product_id",
        "source_image_id",
        "image_url",
        "db_image_type",
        "semantic_image_type",
        "category",
        "brand",
        "color",
        "material",
        "gender",
        "image_quality",
        "manual_status",
        "notes",
    ]
    write_csv_rows(args.output_csv, [query.to_row() for query in query_records], fieldnames)
    print(f"generated {len(query_records)} image queries")
    return 0


def _image_from_row(row: dict[str, str]) -> ProductImageRecord:
    return ProductImageRecord(
        source_image_id=row.get("source_image_id", ""),
        source_product_id=row.get("source_product_id", ""),
        product_name=row.get("product_name", ""),
        category=row.get("category", ""),
        brand=row.get("brand", ""),
        color=row.get("color", ""),
        material=row.get("material", ""),
        gender=row.get("gender", ""),
        image_url=row.get("image_url", ""),
        db_image_type=row.get("db_image_type", ""),
        sort_order=row.get("sort_order", ""),
        image_count=int(float(row.get("image_count") or 1)),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate image search query set from sampled images and annotation.")
    parser.add_argument("--sampled-images-csv", type=Path, required=True)
    parser.add_argument("--annotation-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_annotations.csv")
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_queries.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
