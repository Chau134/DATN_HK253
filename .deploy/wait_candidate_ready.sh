#!/usr/bin/env bash
set -euo pipefail

candidate_url="${1:?candidate URL required}"
response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

for _ in {1..20}; do
  status="$(curl -sS -o "$response_file" -w '%{http_code}' "$candidate_url/health/ready")"
  cat "$response_file"
  printf '\n'
  if [[ "$status" == "200" ]]; then
    exit 0
  fi
  sleep 15
done

exit 1
