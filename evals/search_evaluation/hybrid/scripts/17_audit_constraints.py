"""Read-only evaluator audit; writes evidence without changing labels or queries."""
import argparse
from collections import Counter
import csv
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("comparison", ROOT / "scripts/13_compare_ablation.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, help="fresh output prefix; defaults to the run prefix for legacy compatibility")
    args = parser.parse_args()
    output_prefix = args.output_prefix or args.prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    output_files = [Path(str(output_prefix) + suffix) for suffix in ("_constraint_violations.csv", "_audit.json")]
    if args.output_prefix and any(path.exists() for path in output_files):
        raise FileExistsError("Refusing to overwrite a scoped audit artifact")
    queries = {r["query_id"]: r for r in c.read_csv(ROOT / "data/multimodal_queries.csv")}
    products = {r["product_id"]: r for r in c.read_csv(ROOT / "data/product_snapshot.csv")}
    responses = {r["query_id"]: r for r in c.read_jsonl(Path(str(args.prefix) + "_responses.jsonl"))}
    violations, counts, errors = [], Counter(), []
    for r in c.read_csv(Path(str(args.prefix) + "_results.csv")):
        if not 0 < int(r["rank"]) <= 5:
            continue
        q, p = queries[r["query_id"]], products[r["product_id"]]
        requested = c.required_constraints(q)
        for name, passed in c.requested_constraint_results(q, p).items():
            if not passed:
                counts[name] += 1
                violations.append({"query_id": q["query_id"], "query_text": q["query_text"], "product_id": p["product_id"],
                                   "rank": r["rank"], "field": name, "expected_fixture": json.dumps(requested[name], ensure_ascii=False),
                                   "actual": p.get("price" if name == "price" else name, ""),
                                   "api_filters": json.dumps(responses[q["query_id"]]["response"].get("filters"), ensure_ascii=False)})
    for qid, response in responses.items():
        q = queries[qid]
        ids = response["response"].get("product_ids", [])
        if q["target_product_id"] not in ids[:5]:
            errors.append({"query_id": qid, "query_text": q["query_text"], "target": q["target_product_id"],
                           "target_snapshot": products[q["target_product_id"]], "response": response["response"]})
    with output_files[0].open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["query_id", "query_text", "product_id", "rank", "field", "expected_fixture", "actual", "api_filters"])
        writer.writeheader()
        writer.writerows(violations)
    summary = {"exact_mismatch_rows_by_field": dict(counts), "strict_top5_misses": errors,
               "fixture_material_percentages_absent_in_query": [q["query_id"] for q in queries.values() if re.search(r"\d+%", q["material"]) and not re.search(r"\d+%", q["query_text"])]}
    output_files[1].write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"exact_mismatch_rows_by_field": dict(counts), "strict_top5_misses": [r["query_id"] for r in errors],
                      "fixture_material_percentages_absent_in_query": len(summary["fixture_material_percentages_absent_in_query"])}, indent=2))


if __name__ == "__main__":
    main()
