#!/usr/bin/env bash
set -uo pipefail

status=0
for product_id in 262 285 438 648 1137 1708; do
  printf 'RETRY_PRODUCT_ID=%s\n' "$product_id"
  if ! python3 /tmp/retry_product_sync.py "$product_id"; then
    status=1
  fi
done
exit "$status"
