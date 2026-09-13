"""Build an enriched, human-reviewable pool from frozen hybrid runs.

This tool never changes the ground truth and never infers a visual grade from
metadata. Existing approved labels are copied for reference; new label fields
remain blank for an independent reviewer.
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def product_images_from_sql(path):
    """Read catalog image URLs without querying or changing the database."""
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"INSERT INTO `product_images` VALUES (.*?);", text, re.S)
    if not matches:
        return {}
    grouped = defaultdict(list)
    pattern = re.compile(r"\((\d+),(\d+),'([^']*)','([^']*)',(\d+),'[^']*'\)")
    for values in matches:
        for _, product_id, image_type, url, sort_order in pattern.findall(values):
            if url.startswith("http"):
                grouped[product_id].append((image_type.upper(), int(sort_order), url))
    preference = {"DETAIL_1": 0, "MAIN": 1, "FLAT_1": 2, "MODEL_1": 3}
    return {
        product_id: " | ".join(url for image_type, order, url in sorted(values, key=lambda item: (preference.get(item[0], 10), item[1]))[:3])
        for product_id, values in grouped.items()
    }


def index_run(path, limit):
    indexed = {}
    for row in read_csv(path):
        rank = int(row["rank"])
        if 0 < rank <= limit:
            indexed[(row["query_id"], row["product_id"])] = {
                "rank": rank,
                "score": row.get("score", ""),
            }
    return indexed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, default=ROOT / "data/ground_truth_multimodal.csv")
    parser.add_argument("--product-images-sql", type=Path, default=ROOT.parents[2] / "database" / "1000_final.sql")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    queries = {row["query_id"]: row for row in read_csv(ROOT / "data/multimodal_queries.csv")}
    products = {row["product_id"]: row for row in read_csv(ROOT / "data/product_snapshot.csv")}
    ground_truth = {}
    for row in read_csv(args.ground_truth):
        ground_truth[(row["query_id"], row["relevant_product_id"])] = row
    product_images = product_images_from_sql(args.product_images_sql)

    candidate = index_run(args.candidate, args.top_k)
    baseline = index_run(args.baseline, args.top_k)
    keys = sorted(set(candidate) | set(baseline), key=lambda item: (item[0], int(candidate.get(item, baseline.get(item))["rank"])))
    rows = []
    for query_id, product_id in keys:
        query = queries[query_id]
        product = products.get(product_id, {})
        old = ground_truth.get((query_id, product_id), {})
        cand = candidate.get((query_id, product_id), {})
        base = baseline.get((query_id, product_id), {})
        existing = old.get("relevance_grade", "")
        candidate_rank = cand.get("rank", "")
        known = bool(existing)
        is_target = product_id == query.get("target_product_id")
        baseline_rank = base.get("rank", "")
        candidate_top5 = bool(candidate_rank) and int(candidate_rank) <= 5
        baseline_top5 = bool(baseline_rank) and int(baseline_rank) <= 5
        if is_target and candidate_rank and int(candidate_rank) > 5:
            priority = "P1_target_outside_top5"
        elif not known and candidate_top5:
            priority = "P0_candidate_top5_unjudged"
        elif not known and baseline_top5:
            priority = "P0_baseline_top5_unjudged"
        elif not known and candidate_rank:
            priority = "P2_candidate_top20_unjudged"
        elif not known and baseline_rank:
            priority = "P3_baseline_top20_unjudged"
        else:
            priority = "P3_existing_or_baseline_only"
        rows.append({
            "query_id": query_id,
            "query_text": query.get("query_text", ""),
            "image_url": query.get("image_url", ""),
            "transformation_type": query.get("transformation_type", ""),
            "difficulty": query.get("difficulty", ""),
            "target_product_id": query.get("target_product_id", ""),
            "product_id": product_id,
            "candidate_rank": candidate_rank,
            "candidate_score": cand.get("score", ""),
            "baseline_rank": base.get("rank", ""),
            "baseline_score": base.get("score", ""),
            "priority": priority,
            "existing_grade": existing,
            "existing_grade_source": old.get("source", ""),
            "existing_grade_reason": old.get("match_reason", ""),
            "product_name": product.get("product_name", ""),
            "product_category": product.get("category", ""),
            "product_color": product.get("color", ""),
            "product_material": product.get("material", ""),
            "product_usage": product.get("usage", ""),
            "product_price": product.get("price", ""),
            "candidate_image_urls": product_images.get(product_id, ""),
            "fixture_category": query.get("category", ""),
            "fixture_color": query.get("color", ""),
            "fixture_material": query.get("material", ""),
            "fixture_usage": query.get("usage", ""),
            "fixture_price_bucket": query.get("price_bucket", ""),
            "manual_relevance_grade": existing if known else "",
            "manual_constraint_status": "" if not known else "existing_label_not_constraint_adjudication",
            "manual_violation_fields": "",
            "reviewer": "",
            "reviewed_at": "",
            "review_notes": "",
        })

    fields = list(rows[0]) if rows else []
    write_csv(args.output / "review_pool_top20.csv", rows, fields)
    write_csv(args.output / "review_pool_top5_new.csv", [row for row in rows if row["priority"] == "P0_candidate_top5_unjudged"], fields)
    write_csv(args.output / "review_pool_top5_unjudged_union.csv", [row for row in rows if row["priority"] in {"P0_candidate_top5_unjudged", "P0_baseline_top5_unjudged"}], fields)
    write_csv(args.output / "constraint_review_top5.csv", [row for row in rows if row["candidate_rank"] and int(row["candidate_rank"]) <= 5], fields)

    stats = {
        "ground_truth_sha256": __import__("hashlib").sha256(args.ground_truth.read_bytes()).hexdigest(),
        "candidate_top_k": args.top_k,
        "rows_union_top_k": len(rows),
        "candidate_top5_rows": sum(bool(row["candidate_rank"]) and int(row["candidate_rank"]) <= 5 for row in rows),
        "new_candidate_top5_rows": sum(row["priority"] == "P0_candidate_top5_unjudged" for row in rows),
        "new_baseline_top5_rows": sum(row["priority"] == "P0_baseline_top5_unjudged" for row in rows),
        "target_outside_top5_rows": sum(row["priority"] == "P1_target_outside_top5" for row in rows),
        "new_candidate_top20_rows": sum(row["priority"] in {"P0_candidate_top5_unjudged", "P1_target_outside_top5", "P2_candidate_top20_unjudged"} for row in rows),
        "by_priority": {key: sum(row["priority"] == key for row in rows) for key in sorted({row["priority"] for row in rows})},
        "outputs": ["review_pool_top20.csv", "review_pool_top5_new.csv", "review_pool_top5_unjudged_union.csv", "constraint_review_top5.csv"],
    }
    (args.output / "pool_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
