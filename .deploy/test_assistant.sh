#!/usr/bin/env bash
set -euo pipefail

candidate_url="${1:?candidate URL required}"
request_id="gcp-bedrock-smoke-$(date +%s)"

curl -fsS --max-time 300 \
  -H 'Content-Type: application/json' \
  --data "{\"session_id\":\"$request_id\",\"user_id\":\"deployment-smoke\",\"request_id\":\"$request_id\",\"turn_sequence\":1,\"message\":\"Xin chào, hãy trả lời ngắn gọn rằng trợ lý đang hoạt động.\",\"locale\":\"vi-VN\"}" \
  "$candidate_url/assistant/chat"
printf '\n'
