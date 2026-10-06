#!/usr/bin/env bash
set -euo pipefail

candidate_url="${1:?candidate URL required}"
image_url="https://pub-5a1bb641c66b47c794fbd182d1cfef7b.r2.dev/products/1286/10690-05584448321-p.jpg"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

curl -fsSL --max-time 60 "$image_url" -o "$work_dir/product.jpg"
python3 - "$work_dir/product.jpg" "$work_dir/request.json" <<'PY'
import base64
import json
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
target.write_text(json.dumps({
    "image": {
        "content_type": "image/jpeg",
        "data_base64": base64.b64encode(source.read_bytes()).decode("ascii"),
        "filename": source.name,
    }
}), encoding="utf-8")
PY

curl -fsS --max-time 120 \
  -H 'Content-Type: application/json' \
  --data-binary "@$work_dir/request.json" \
  "$candidate_url/search/image/detections"
