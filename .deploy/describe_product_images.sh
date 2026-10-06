#!/usr/bin/env bash
set -euo pipefail

sudo docker exec datn-mysql-1 sh -c \
  'exec mysql -N -uroot -p"$MYSQL_ROOT_PASSWORD" DATN -e "DESCRIBE product_images"'
