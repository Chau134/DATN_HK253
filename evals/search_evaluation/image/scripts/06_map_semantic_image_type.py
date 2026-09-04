from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import read_csv_rows, write_csv_rows

# Zara encodes the shot type in the image filename suffix (the token after the
# last dash before .jpg), e.g. ...03564119330-e1.jpg -> "e1". This maps those
# codes to the evaluation semantic_image_type. "p"/"f" packshots are reliable;
# the "a" (additional) group is ambiguous (detail/side/back) so it is defaulted
# to detail and flagged for manual review.
SUFFIX_MAP: dict[str, tuple[str, bool]] = {
    "p": ("front", False),
    "f1": ("front", False),
    "f2": ("front", False),
    "e1": ("lifestyle", False),
    "e2": ("lifestyle", False),
    "e3": ("lifestyle", False),
    "e4": ("lifestyle", False),
    "a1": ("detail", True),
    "a2": ("detail", True),
    "a3": ("detail", True),
    "a4": ("detail", True),
    "a5": ("detail", True),
    "a6": ("detail", True),
    "a7": ("detail", True),
    "a8": ("detail", True),
}

ANNOTATION_FIELDS = [
    "source_image_id",
    "source_product_id",
    "image_url",
    "db_image_type",
    "sort_order",
    "semantic_image_type",
    "image_quality",
    "review_status",
    "notes",
]


def suffix_from_url(image_url: str) -> str:
    filename = re.split(r"[?#]", image_url, maxsplit=1)[0].rsplit("/", 1)[-1]
    stem = re.sub(r"\.(jpg|jpeg|png|webp)$", "", filename, flags=re.IGNORECASE)
    parts = stem.split("-")
    return parts[-1].lower() if parts else ""


def main() -> int:
    args = parse_args()
    rows = read_csv_rows(args.annotation_csv)

    filled = 0
    skipped_reviewed = 0
    unmapped = 0
    needs_review = 0
    type_counts: Counter[str] = Counter()

    for row in rows:
        current = (row.get("semantic_image_type") or "").strip().lower()
        if current and current != "unknown":
            skipped_reviewed += 1
            continue

        suffix = suffix_from_url(row.get("image_url", ""))
        mapped = SUFFIX_MAP.get(suffix)
        if mapped is None:
            unmapped += 1
            row["notes"] = f"auto: unmatched suffix '{suffix}', needs manual review"
            continue

        semantic_type, verify = mapped
        row["semantic_image_type"] = semantic_type
        row["notes"] = (
            f"auto from Zara suffix '{suffix}' -> {semantic_type}; verify angle"
            if verify
            else f"auto from Zara suffix '{suffix}' -> {semantic_type}"
        )
        filled += 1
        type_counts[semantic_type] += 1
        if verify:
            needs_review += 1

    write_csv_rows(args.output_csv, rows, ANNOTATION_FIELDS)

    print(f"rows={len(rows)} filled={filled} skipped_already_reviewed={skipped_reviewed} unmapped={unmapped}")
    print(f"needs_manual_verify (a* group)={needs_review}")
    print("semantic_image_type distribution (auto-filled):")
    for name, count in sorted(type_counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {name}: {count}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-fill semantic_image_type in image annotations from Zara image URL suffixes.")
    parser.add_argument("--annotation-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "image_annotations.csv")
    parser.add_argument("--output-csv", type=Path, default=None, help="Defaults to the annotation CSV (in-place).")
    args = parser.parse_args()
    if args.output_csv is None:
        args.output_csv = args.annotation_csv
    return args


if __name__ == "__main__":
    raise SystemExit(main())
