from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPECTED_TRANSFORMATIONS = {
    "color": 17, "material": 17, "usage": 17, "price": 16,
    "color_material": 11, "color_usage": 11, "material_usage": 11,
}
EXPECTED_DIFFICULTY = {"easy": 34, "medium": 33, "hard": 33}


def normalized(value: str) -> str:
    return " ".join(
        "".join(
            character for character in unicodedata.normalize("NFKD", value or "")
            if not unicodedata.combining(character)
        ).lower().split()
    )


def main() -> int:
    args = parse_args()
    with args.queries_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    errors: list[str] = []
    if len(rows) != 100:
        errors.append(f"expected 100 queries, got {len(rows)}")
    if len({row.get("query_id", "") for row in rows}) != len(rows):
        errors.append("query_id must be unique")
    source_urls = [row.get("source_image_url", "").strip() for row in rows]
    if len({url for url in source_urls if url}) != len(rows):
        errors.append("source_image_url must be non-empty and unique")
    urls = [row.get("image_url", "").strip() for row in rows]
    provided_urls = [url for url in urls if url]
    if len(set(provided_urls)) != len(provided_urls):
        errors.append("provided image_url values must be unique")
    pending_count = len(rows) - len(provided_urls)
    if not args.allow_pending_images and pending_count:
        errors.append(f"missing edited image_url values: {pending_count}")
    if args.allow_pending_images and pending_count > 67:
        errors.append(f"at most 67 edited image URLs may be pending, got {pending_count}")
    transformations = Counter(row.get("transformation_type", "") for row in rows)
    if transformations != Counter(EXPECTED_TRANSFORMATIONS):
        errors.append(f"unexpected transformation distribution: {dict(transformations)}")
    difficulties = Counter(row.get("difficulty", "") for row in rows)
    if difficulties != Counter(EXPECTED_DIFFICULTY):
        errors.append(f"unexpected difficulty distribution: {dict(difficulties)}")
    for row in rows:
        query_id = row["query_id"]
        if not args.allow_pending_images and not row.get("image_url", "").strip():
            errors.append(f"{query_id}: missing image_url")
        if row.get("source_product_id", "") != row.get("target_product_id", ""):
            errors.append(f"{query_id}: target_product_id must equal source_product_id")
        if normalized(row.get("reference_category", "")) != normalized(row.get("category", "")):
            errors.append(f"{query_id}: reference_category must match target category")
        transformation = row.get("transformation_type", "")
        if "color" in transformation:
            reference = normalized(row.get("reference_color", ""))
            target = normalized(row.get("color", ""))
            if not reference:
                errors.append(f"{query_id}: missing reference_color")
            elif reference == target:
                errors.append(f"{query_id}: reference_color must differ from requested color")
        if "material" in transformation:
            reference = normalized(row.get("reference_material", ""))
            target = normalized(row.get("material", ""))
            if not reference:
                errors.append(f"{query_id}: missing reference_material")
            elif reference == target:
                errors.append(f"{query_id}: reference_material must differ from requested material")
        if "usage" in transformation:
            reference = normalized(row.get("reference_usage", ""))
            target = normalized(row.get("usage", ""))
            if not reference:
                errors.append(f"{query_id}: missing reference_usage")
            elif reference != target:
                errors.append(f"{query_id}: requested usage must match target product metadata")
        if transformation == "price":
            reference = row.get("reference_price_bucket", "").strip()
            target = row.get("price_bucket", "").strip()
            if not reference:
                errors.append(f"{query_id}: missing reference_price_bucket")
            elif reference != target:
                errors.append(f"{query_id}: requested price_bucket must match target product metadata")
        needs_edit = "color" in transformation or "material" in transformation
        if needs_edit and not row.get("image_edit_request", "").strip():
            errors.append(f"{query_id}: missing image_edit_request")
        if not needs_edit and row.get("image_edit_request", "").strip():
            errors.append(f"{query_id}: medium usage/price query must not request an image edit")
        if transformation in {"gender", "brand"}:
            errors.append(f"{query_id}: forbidden transformation {transformation}")
        try:
            if int(row.get("candidate_count", "0")) < 1:
                errors.append(f"{query_id}: candidate_count must be at least 1")
        except ValueError:
            errors.append(f"{query_id}: invalid candidate_count")

    if errors:
        print("\n".join(errors))
        print(f"validation_failed={len(errors)}")
        return 1
    print(f"validation=ok queries={len(rows)} pending_edited_images={pending_count}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending-images", action="store_true")
    parser.add_argument(
        "--queries-csv", type=Path,
        default=SCRIPT_DIR.parent / "data" / "multimodal_queries.csv",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
