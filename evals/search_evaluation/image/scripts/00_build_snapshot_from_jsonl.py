from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import ensure_parent_dir, write_csv_rows

# Source dataset: data_clean_zara_search_vi.jsonl at repo root. Line N (1-indexed)
# maps to the DB / Qdrant integer product_id N (verified against database/data.sql
# product_images: JSONL line 1 hero == product_id 1 hero, line 2 == product_id 2).
# The top-level `category` field is only WOMAN/MAN, so it is used as `gender`; the
# real garment category comes from `category_family` (shirt_blouse, dress, pants...).

DEFAULT_JSONL = SCRIPT_DIR.parents[3] / "data_clean_zara_search_vi.jsonl"

PRODUCT_FIELDS = [
    "product_id",
    "product_name",
    "product_display_name_vi",
    "category",
    "brand",
    "color",
    "material",
    "gender",
    "is_active",
    "description",
]

IMAGE_FIELDS = [
    "product_id",
    "source_image_id",
    "image_type",
    "image_url",
    "sort_order",
]


def _first_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        for item in value:
            text = str(item).strip()
            if text:
                return text
        return ""
    return str(value).strip()


def main() -> int:
    args = parse_args()
    if not args.jsonl.exists():
        raise SystemExit(f"source dataset not found: {args.jsonl}")

    product_rows: list[dict[str, object]] = []
    image_rows: list[dict[str, object]] = []
    skipped_no_image = 0

    with args.jsonl.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            product_id = line_number

            image_urls = record.get("image_urls") or []
            if not isinstance(image_urls, list):
                image_urls = [image_urls]
            image_urls = [str(url).strip() for url in image_urls if str(url).strip()]
            hero = _first_str(record.get("hero_image_url"))
            if hero and hero not in image_urls:
                image_urls.insert(0, hero)
            if not image_urls:
                skipped_no_image += 1
                continue

            product_rows.append(
                {
                    "product_id": product_id,
                    "product_name": _first_str(record.get("product_name")),
                    "product_display_name_vi": _first_str(record.get("search_name_vi")),
                    "category": _first_str(record.get("category_family")),
                    "brand": _first_str(record.get("brand")),
                    "color": _first_str(record.get("color_name")),
                    "material": _first_str(record.get("material_composition")),
                    "gender": _first_str(record.get("category")),
                    "is_active": "true",
                    "description": _first_str(record.get("short_description")),
                }
            )

            for index, image_url in enumerate(image_urls):
                image_rows.append(
                    {
                        "product_id": product_id,
                        "source_image_id": f"{product_id}:img:{index}",
                        "image_type": "hero" if index == 0 else "gallery",
                        "image_url": image_url,
                        "sort_order": index,
                    }
                )

    write_csv_rows(args.products_csv, product_rows, PRODUCT_FIELDS)
    write_csv_rows(args.product_images_csv, image_rows, IMAGE_FIELDS)

    summary = {
        "source": str(args.jsonl),
        "products": len(product_rows),
        "images": len(image_rows),
        "skipped_no_image": skipped_no_image,
        "products_csv": str(args.products_csv),
        "product_images_csv": str(args.product_images_csv),
    }
    ensure_parent_dir(args.summary_json)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build product_snapshot.csv and product_images.csv from the Zara JSONL dataset for image search evaluation.")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--products-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--product-images-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_images.csv")
    parser.add_argument("--summary-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "snapshot_summary.json")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
