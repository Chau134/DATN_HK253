#!/usr/bin/env bash
set -euo pipefail

sudo docker exec -i datn-mysql-1 sh -c 'exec mysql -N -uroot -p"$MYSQL_ROOT_PASSWORD" DATN' <<'SQL'
SELECT CONCAT('products=', COUNT(*)) FROM products;
SELECT CONCAT('product_images=', COUNT(*)) FROM product_images;
SELECT CONCAT('products_with_images=', COUNT(DISTINCT product_id)) FROM product_images;
SELECT CONCAT('avg_images_per_product=', ROUND(COUNT(*) / COUNT(DISTINCT product_id), 2)) FROM product_images;
SELECT CONCAT('max_images_per_product=', MAX(image_count))
FROM (SELECT product_id, COUNT(*) AS image_count FROM product_images GROUP BY product_id) counts;
SQL
