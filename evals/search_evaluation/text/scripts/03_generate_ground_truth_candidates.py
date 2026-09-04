from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import build_candidate_rows, load_products, read_csv_rows, write_csv_rows


def main() -> int:
    args = parse_args()
    products = load_products(args.products_csv)
    query_rows = read_csv_rows(args.query_set_csv)
    candidate_rows = []
    for query_row in query_rows:
        candidate_rows.extend(build_candidate_rows(query_row, products, max_candidates=args.max_candidates))
    fieldnames = list(candidate_rows[0].to_row().keys()) if candidate_rows else ["query_id", "mode", "query_type", "relevant_product_id", "relevance_grade", "match_reason", "source", "review_status", "notes"]
    write_csv_rows(args.output_csv, [candidate.to_row() for candidate in candidate_rows], fieldnames)
    print(f"generated {len(candidate_rows)} candidate rows")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate candidate ground truth rows for text search evaluation.")
    parser.add_argument("--products-csv", type=Path, required=True)
    parser.add_argument("--query-set-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "ground_truth_text_candidates.csv")
    parser.add_argument("--max-candidates", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())