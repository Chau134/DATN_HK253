#!/usr/bin/env bash
set -euo pipefail

candidate_url="${1:?candidate URL required}"
image_url="https://pub-5a1bb641c66b47c794fbd182d1cfef7b.r2.dev/products/1286/10690-05584448321-p.jpg"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

printf 'READINESS='
curl -fsS --max-time 60 "$candidate_url/health/ready"
printf '\nTEXT_SEARCH='
curl -fsS --max-time 300 \
  -H 'Content-Type: application/json' \
  --data '{"query":"áo sơ mi nam màu xanh chất liệu cotton","top_k":5}' \
  "$candidate_url/search/text"

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
    },
}), encoding="utf-8")
PY

printf '\nYOLO_DETECTION='
curl -fsS --max-time 300 \
  -H 'Content-Type: application/json' \
  --data-binary "@$work_dir/request.json" \
  "$candidate_url/search/image/detections"
printf '\nIMAGE_SEARCH='
curl -fsS --max-time 300 \
  -H 'Content-Type: application/json' \
  --data-binary "@$work_dir/request.json" \
  "$candidate_url/search/image"

printf '\nBEDROCK_ASSISTANT='
curl -fsS --max-time 300 \
  -H 'Content-Type: application/json' \
  --data '{"session_id":"gcp-smoke-bedrock-v2","user_id":"deployment-smoke","request_id":"gcp-smoke-bedrock-v2-1","turn_sequence":1,"message":"Xin chào, hãy trả lời ngắn gọn rằng trợ lý đang hoạt động.","locale":"vi-VN"}' \
  "$candidate_url/assistant/chat"
printf '\n'
