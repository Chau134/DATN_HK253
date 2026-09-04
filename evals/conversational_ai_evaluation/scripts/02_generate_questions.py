from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    DEFAULT_GROUP_COUNTS,
    build_question_records,
    load_conv_products,
    load_json_config,
    preserve_review_metadata_if_unchanged,
    read_csv_rows,
    write_csv_rows,
)

QUESTION_FIELDNAMES = [
    "question_id",
    "session_id",
    "turn_index",
    "category",
    "question",
    "expected_answer_type",
    "entity_ids",
    "depends_on_history",
    "difficulty",
    "manual_status",
    "notes",
    "reviewer",
    "reviewed_at",
    "review_notes",
]


def main() -> int:
    args = parse_args()
    group_counts = dict(DEFAULT_GROUP_COUNTS)
    seed = args.seed
    if args.config and args.config.exists():
        config = load_json_config(args.config)
        group_counts.update(config.get("group_counts", {}))
        seed = config.get("sampling_seed", seed)

    products = load_conv_products(args.snapshot_csv)
    records = build_question_records(products, seed=seed, group_counts=group_counts)
    existing = (
        {row["question_id"]: row for row in read_csv_rows(args.output_csv)}
        if args.output_csv.exists()
        else {}
    )
    rows = []
    for record in records:
        row = record.to_row()
        rows.append(
            preserve_review_metadata_if_unchanged(
                row,
                existing.get(record.question_id),
                content_fields=(
                    "question_id",
                    "session_id",
                    "turn_index",
                    "category",
                    "question",
                    "expected_answer_type",
                    "entity_ids",
                    "depends_on_history",
                    "difficulty",
                    "notes",
                ),
            )
        )
    write_csv_rows(args.output_csv, rows, QUESTION_FIELDNAMES)
    print(f"generated {len(records)} questions -> {args.output_csv}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the conversational eval question set from the product snapshot.")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR.parent / "configs" / "conversational_ai.yaml")
    parser.add_argument("--snapshot-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "question_set.csv")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
