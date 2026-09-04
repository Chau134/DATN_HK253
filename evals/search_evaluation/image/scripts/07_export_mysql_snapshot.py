from __future__ import annotations

import argparse
import csv
import os
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PRODUCT_FIELDS = [
    "product_id", "product_name", "category", "brand", "color", "material",
    "gender", "price", "usage", "is_active", "description",
]
IMAGE_FIELDS = ["product_id", "source_image_id", "image_type", "image_url", "sort_order"]

PRODUCT_QUERY = """
SELECT p.id,
       COALESCE(NULLIF(p.product_display_name_vi, ''), p.product_display_name),
       COALESCE(NULLIF(c.category_name_vi, ''), c.category_name),
       COALESCE(p.brand_name, ''),
       COALESCE(NULLIF(p.base_colour_vi, ''), p.base_colour, ''),
       COALESCE(NULLIF(p.material_vi, ''), p.material, ''),
       COALESCE(NULLIF(p.gender_vi, ''), p.gender, ''),
       pp.selling_price,
       COALESCE(NULLIF(p.product_usage_vi, ''), p.product_usage, ''),
       CASE WHEN COALESCE(pa.attr_value, 'true') = 'true' THEN 'true' ELSE 'false' END,
       COALESCE(NULLIF(p.description_vi, ''), p.description, '')
FROM products p
JOIN product_categories pc ON pc.product_id = p.id
JOIN categories c ON c.id = pc.category_id
LEFT JOIN product_prices pp ON pp.product_id = p.id
LEFT JOIN product_attributes pa
       ON pa.product_id = p.id AND pa.attr_key = 'flag:active'
ORDER BY p.id
"""

IMAGE_QUERY = """
SELECT product_id, id, image_type, image_url, sort_order
FROM product_images
ORDER BY product_id, sort_order, id
"""


def mysql_rows(args: argparse.Namespace, query: str) -> list[list[str]]:
    env = os.environ.copy()
    if args.password:
        env["MYSQL_PWD"] = args.password
    command = [
        args.mysql_bin, f"--host={args.host}", f"--port={args.port}",
        f"--user={args.user}", f"--database={args.database}",
        "--default-character-set=utf8mb4", "--batch", "--skip-column-names",
        f"--execute={query}",
    ]
    result = subprocess.run(
        command, check=True, capture_output=True, text=True,
        encoding="utf-8", env=env,
    )
    return list(csv.reader(result.stdout.splitlines(), delimiter="\t"))


def write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    products = mysql_rows(args, PRODUCT_QUERY)
    images = mysql_rows(args, IMAGE_QUERY)
    if len(products) != args.expected_products:
        raise RuntimeError(f"Expected {args.expected_products} products, got {len(products)}")
    if len({row[0] for row in images}) != args.expected_products:
        raise RuntimeError("Not every product has an image")
    write_csv(args.products_csv, PRODUCT_FIELDS, products)
    write_csv(args.images_csv, IMAGE_FIELDS, images)
    print(f"products={len(products)} images={len(images)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default=os.getenv("MYSQL_PWD", ""))
    parser.add_argument("--database", default="dacn")
    parser.add_argument("--mysql-bin", default="mysql")
    parser.add_argument("--expected-products", type=int, default=1000)
    parser.add_argument("--products-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--images-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_images.csv")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
