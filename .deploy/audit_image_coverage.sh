#!/usr/bin/env bash
set -euo pipefail

expected_file="$(mktemp)"
trap 'rm -f "$expected_file"' EXIT

sudo docker exec datn-mysql-1 sh -c \
  'exec mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" DATN -e "SELECT product_id, image_url FROM product_images ORDER BY product_id, id"' \
  > "$expected_file"

python3 - "$expected_file" <<'PY'
import json
import pathlib
import sys
import urllib.request

collection = "product_image_vectors_qwen3_vl_embedding_2b_2048_1000_products"
scroll_url = f"http://10.148.0.4:6333/collections/{collection}/points/scroll"
expected = set()
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    product_id, image_url = line.split("\t", 1)
    expected.add((product_id, image_url))

observed = set()
offset = None
while True:
    body = {"limit": 1000, "with_payload": True, "with_vector": False}
    if offset is not None:
        body["offset"] = offset
    request = urllib.request.Request(
        scroll_url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)["result"]
    for point in result["points"]:
        payload = point.get("payload") or {}
        product_id = str(payload.get("product_id", ""))
        image_url = payload.get("image_url")
        if product_id and image_url:
            observed.add((product_id, image_url))
    offset = result.get("next_page_offset")
    if offset is None:
        break

missing = sorted(expected - observed, key=lambda item: (int(item[0]), item[1]))
unexpected = observed - expected
print(f"EXPECTED_UNIQUE_IMAGES={len(expected)}")
print(f"OBSERVED_UNIQUE_IMAGES={len(observed)}")
print(f"MISSING_IMAGE_COUNT={len(missing)}")
print(f"UNEXPECTED_IMAGE_COUNT={len(unexpected)}")
print("MISSING_JSON=" + json.dumps(missing, ensure_ascii=False, separators=(",", ":")))
PY
