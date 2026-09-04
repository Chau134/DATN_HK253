from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import ConvProductRecord, ensure_parent_dir, load_conv_products, write_csv_rows

SNAPSHOT_FIELDNAMES = [
    "product_id",
    "product_name",
    "product_name_vi",
    "category",
    "brand",
    "color",
    "material",
    "gender",
    "is_active",
    "description",
    "version",
]


def main() -> int:
    args = parse_args()
    version = args.version or f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    products = load_conv_products(args.source_csv)
    stamped = [
        ConvProductRecord(
            product_id=product.product_id,
            product_name=product.product_name,
            product_name_vi=product.product_name_vi,
            category=product.category,
            brand=product.brand,
            color=product.color,
            material=product.material,
            gender=product.gender,
            is_active=product.is_active,
            description=product.description,
            version=version,
        )
        for product in products
        if product.product_id
    ]

    write_csv_rows(args.output_csv, [product.to_row() for product in stamped], SNAPSHOT_FIELDNAMES)

    active_count = sum(1 for product in stamped if product.is_active)
    summary = {
        "source_csv": str(args.source_csv),
        "input_rows": len(products),
        "snapshot_rows": len(stamped),
        "active_rows": active_count,
        "version": version,
    }
    ensure_parent_dir(args.summary_json)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the conversational eval product snapshot from a source product CSV.")
    parser.add_argument("--source-csv", type=Path, default=SCRIPT_DIR.parent.parent / "search_evaluation" / "image" / "data" / "product_snapshot.csv")
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--summary-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "snapshot_summary.json")
    parser.add_argument("--version", type=str, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
