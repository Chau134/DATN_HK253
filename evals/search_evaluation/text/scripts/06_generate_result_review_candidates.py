from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[3]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import read_csv_rows, write_csv_rows


PRODUCT_PATTERN = re.compile(
    r"\(\d+,(\d+),'search_name_vi',NULL,'[^']*','[^']*','((?:''|[^'])*)'\)"
)
FIELDS = [
    "query_id",
    "query_text",
    "query_type",
    "rank",
    "product_id",
    "title_vi",
    "candidate_category",
    "candidate_brand",
    "candidate_color",
    "candidate_material",
    "candidate_gender",
    "candidate_price",
    "candidate_usage",
    "score",
    "relevance_grade",
    "review_status",
    "notes",
]


def _product_titles(sql_path: Path) -> dict[str, str]:
    sql = sql_path.read_text(encoding="utf-8")
    return {
        match.group(1): match.group(2).replace("''", "'")
        for match in PRODUCT_PATTERN.finditer(sql)
    }


def _catalog_payloads(qdrant_url: str, collection_name: str) -> dict[str, dict]:
    url = (
        qdrant_url.rstrip("/")
        + f"/collections/{collection_name}/points/scroll"
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {"limit": 256, "with_payload": True, "with_vector": False}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    return {
        str(point.get("payload", {}).get("product_id", "")): point.get("payload", {})
        for point in body.get("result", {}).get("points", [])
        if point.get("payload", {}).get("product_id")
    }


def _joined(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return " | ".join(str(item) for item in value)
        if value not in (None, ""):
            return str(value)
    return ""


def main() -> int:
    args = parse_args()
    queries = {
        row["query_id"]: row
        for row in read_csv_rows(args.query_set_csv)
    }
    existing = {
        (row["query_id"], row.get("relevant_product_id", "")): row
        for row in read_csv_rows(args.ground_truth_csv)
        if row.get("relevant_product_id")
    }
    titles = _product_titles(args.sql)
    payloads = _catalog_payloads(args.qdrant_url, args.collection_name)

    candidates: list[dict[str, object]] = []
    for result in read_csv_rows(args.results_csv):
        product_id = result.get("product_id", "")
        query = queries.get(result.get("query_id", ""), {})
        if not product_id or not query:
            continue
        judgment = existing.get((query["query_id"], product_id), {})
        is_negative = query.get("query_type") == "negative"
        payload = payloads.get(product_id, {})
        candidates.append(
            {
                "query_id": query["query_id"],
                "query_text": query.get("query_text", ""),
                "query_type": query.get("query_type", ""),
                "rank": result.get("rank", ""),
                "product_id": product_id,
                "title_vi": titles.get(product_id, ""),
                "candidate_category": _joined(
                    payload,
                    "category_names_vi",
                    "category_names",
                ),
                "candidate_brand": _joined(payload, "brand_name"),
                "candidate_color": _joined(
                    payload,
                    "base_colour_vi",
                    "base_colour",
                ),
                "candidate_material": _joined(
                    payload,
                    "material_vi",
                    "material",
                ),
                "candidate_gender": _joined(
                    payload,
                    "gender_vi",
                    "gender",
                ),
                "candidate_price": _joined(payload, "selling_price"),
                "candidate_usage": _joined(
                    payload,
                    "product_usage_vi",
                    "product_usage",
                ),
                "score": result.get("score", ""),
                "relevance_grade": (
                    "0" if is_negative else judgment.get("relevance_grade", "")
                ),
                "review_status": (
                    "approved_negative"
                    if is_negative
                    else judgment.get("review_status", "pending")
                ),
                "notes": (
                    "negative query expected no relevant catalog result"
                    if is_negative
                    else judgment.get("notes", "review current Top-5 result")
                ),
            }
        )

    write_csv_rows(args.output_csv, candidates, FIELDS)
    pending = sum(row["review_status"] == "pending" for row in candidates)
    print(
        f"candidates={len(candidates)} pending={pending} -> {args.output_csv}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a review sheet from the current semantic search results."
    )
    data_dir = SCRIPT_DIR.parent / "data"
    parser.add_argument(
        "--query-set-csv",
        type=Path,
        default=data_dir / "text_queries.csv",
    )
    parser.add_argument(
        "--results-csv",
        type=Path,
        default=data_dir / "search_results_text.csv",
    )
    parser.add_argument(
        "--ground-truth-csv",
        type=Path,
        default=data_dir / "ground_truth_text.csv",
    )
    parser.add_argument(
        "--sql",
        type=Path,
        default=ROOT / "database" / "100.sql",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=data_dir / "result_review_candidates.csv",
    )
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument(
        "--collection-name",
        default="product_text_vectors_cohere_embed_v4_1536_metadata_v4_100_products",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
