"""Read-only catalog admission audit using the runtime predicate and reviewed GT."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import urllib.request

from ecommerce_search_assistant.services.search.hybrid_intent import parse_hybrid_intent
from ecommerce_search_assistant.services.search.service import _filter_satisfaction


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--ground-truth", type=Path, required=True)
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--catalog-url", required=True)
    p.add_argument("--collection", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    products, offset = {}, None
    fields = ["product_id", "category_keys", "category_names", "category_names_vi", "color_keys", "base_colour", "base_colour_vi",
              "material_keys", "material", "material_vi", "use_case_keys", "product_usage_vi", "selling_price", "active", "available",
              "gender_key", "size_keys", "brand_key"]
    while True:
        request = {"limit": 250, "with_payload": fields, "with_vector": False}
        if offset is not None:
            request["offset"] = offset
        url = args.catalog_url.rstrip("/") + "/collections/" + args.collection + "/points/scroll"
        with urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(request).encode(), headers={"Content-Type": "application/json"}), timeout=15) as response:
            result = json.load(response)["result"]
        for point in result["points"]:
            value = point["payload"]
            products[str(value["product_id"])] = value
        offset = result.get("next_page_offset")
        if offset is None:
            break
    queries = read_csv(args.queries)
    gt, results = read_csv(args.ground_truth), read_csv(args.results)
    rows, missing, rejected = [], [], Counter()
    for q in queries:
        qid = q["query_id"]
        intent = parse_hybrid_intent(q["query_text"])
        returned = {r["product_id"] for r in results if r["query_id"] == qid}
        eligible = {pid for pid, payload in products.items() if all(intent.checks(payload, _filter_satisfaction).values())}
        labeled = [g for g in gt if g["query_id"] == qid and int(g["relevance_grade"]) >= 2]
        for g in labeled:
            pid = g["relevant_product_id"]
            if pid in returned:
                continue
            checks = intent.checks(products.get(pid, {}), _filter_satisfaction)
            failed = [name for name, passed in checks.items() if not passed]
            rejected.update(failed)
            missing.append({"query_id": qid, "query_text": q["query_text"], "product_id": pid, "grade": g["relevance_grade"],
                            "eligible": pid in eligible, "failed_fields": ";".join(failed), "payload": json.dumps(products.get(pid), ensure_ascii=False)})
        rows.append({"query_id": qid, "catalog_eligible": len(eligible), "returned": len(returned),
                     "eligible_not_returned": len(eligible - returned), "judged_relevant_not_returned": sum(g["relevant_product_id"] not in returned for g in labeled)})
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data, fields in (
        ("per_query.csv", rows, list(rows[0])),
        ("judged_missing.csv", missing, ["query_id", "query_text", "product_id", "grade", "eligible", "failed_fields", "payload"]),
    ):
        with (args.output / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
    summary = {"catalog_products": len(products), "underfilled_with_at_least_5_eligible": [r["query_id"] for r in rows if r["returned"] < 5 and r["catalog_eligible"] >= 5],
               "judged_relevant_missing": len(missing), "judged_relevant_missing_but_eligible": sum(r["eligible"] for r in missing),
               "rejected_by_field": dict(rejected)}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
