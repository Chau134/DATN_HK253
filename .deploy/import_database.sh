#!/usr/bin/env bash
set -euo pipefail

cd /opt/dATN
compose=(sudo docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.vm.yml)

for _ in $(seq 1 60); do
  mysql_health="$(sudo docker inspect datn-mysql-1 --format '{{.State.Health.Status}}' 2>/dev/null || true)"
  qdrant_health="$(sudo docker inspect datn-qdrant-1 --format '{{.State.Health.Status}}' 2>/dev/null || true)"
  if [[ "$mysql_health" == healthy && "$qdrant_health" == healthy ]]; then
    break
  fi
  sleep 5
done

test "$(sudo docker inspect datn-mysql-1 --format '{{.State.Health.Status}}')" = healthy
test "$(sudo docker inspect datn-qdrant-1 --format '{{.State.Health.Status}}')" = healthy

"${compose[@]}" exec -T mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" DATN' \
  < database/1000_final.sql

product_count="$("${compose[@]}" exec -T mysql sh -c \
  'exec mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" DATN -e "select count(*) from products"')"
printf 'MYSQL_PRODUCT_COUNT=%s\n' "$product_count"
test "$product_count" = 1000

backup="/opt/backups/datn/mysql-DATN-$(date +%Y%m%d-%H%M%S)-post-import.sql"
"${compose[@]}" exec -T mysql sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers DATN' \
  | sudo tee "$backup" >/dev/null
sudo chmod 600 "$backup"
printf 'MYSQL_BACKUP=%s\n' "$backup"
