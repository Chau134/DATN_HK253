"""Freeze canonical catalog fields used by the service for constraint evaluation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import urllib.request


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-snapshot", type=Path, required=True)
    parser.add_argument("--qdrant-url", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.metadata.exists():
        raise FileExistsError("Refusing to overwrite a frozen constraint snapshot")
    base = read_csv(args.base_snapshot)
    if not base or len({r["product_id"] for r in base}) != len(base):
        raise ValueError("Base product snapshot is empty or has duplicate IDs")
    payloads, offset = {}, None
    payload_fields = ["product_id", "base_colour", "base_colour_vi", "color_keys", "material", "material_vi",
                      "material_keys", "product_usage_vi", "use_case_keys", "selling_price", "active", "available"]
    while True:
        body = {"limit": 250, "with_payload": payload_fields, "with_vector": False}
        if offset is not None:
            body["offset"] = offset
        url = args.qdrant_url.rstrip("/") + "/collections/" + args.collection + "/points/scroll"
        request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            page = json.load(response)["result"]
        for point in page["points"]:
            payload = point["payload"]
            pid = str(payload.get("product_id") or "")
            if not pid or pid in payloads:
                raise ValueError(f"Missing or duplicate Qdrant product_id: {pid!r}")
            payloads[pid] = payload
        offset = page.get("next_page_offset")
        if offset is None:
            break
    base_ids = {r["product_id"] for r in base}
    if set(payloads) != base_ids:
        raise ValueError(f"Snapshot/catalog ID mismatch: base_only={len(base_ids-set(payloads))}, catalog_only={len(set(payloads)-base_ids)}")
    extra = ["base_colour", "base_colour_vi", "color_keys_json", "material_raw", "material_vi",
             "material_keys_json", "product_usage_vi", "use_case_keys_json", "selling_price"]
    fields = list(base[0]) + [f for f in extra if f not in base[0]]
    rows = []
    for row in base:
        payload = payloads[row["product_id"]]
        if payload.get("active") is False or payload.get("available") is False:
            raise ValueError(f"Inactive/unavailable product in frozen 1,000-product snapshot: {row['product_id']}")
        item = dict(row)
        item.update({
            "base_colour": payload.get("base_colour", ""), "base_colour_vi": payload.get("base_colour_vi", ""),
            "color_keys_json": json.dumps(payload.get("color_keys") or [], ensure_ascii=False, separators=(",", ":")),
            "material_raw": payload.get("material", ""), "material_vi": payload.get("material_vi", ""),
            "material_keys_json": json.dumps(payload.get("material_keys") or [], ensure_ascii=False, separators=(",", ":")),
            "product_usage_vi": payload.get("product_usage_vi", ""),
            "use_case_keys_json": json.dumps(payload.get("use_case_keys") or [], ensure_ascii=False, separators=(",", ":")),
            "selling_price": payload.get("selling_price", ""),
        })
        rows.append(item)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    metadata = {
        "contract": "read-only canonical constraint snapshot; no vectors or credentials",
        "collection": args.collection, "products": len(rows), "fields": extra,
        "base_snapshot_sha256": hashlib.sha256(args.base_snapshot.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
