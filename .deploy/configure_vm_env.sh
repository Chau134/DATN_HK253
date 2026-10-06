#!/usr/bin/env bash
set -euo pipefail

project_id='project-7a5551d7-985f-4ecc-985'
mysql_password="$(gcloud secrets versions access latest --secret=datn-mysql-root-password --project="$project_id")"
jwt_secret="$(gcloud secrets versions access latest --secret=datn-jwt-secret --project="$project_id")"
internal_api_key="$(gcloud secrets versions access latest --secret=service-ai-internal-api-key --project="$project_id")"

umask 077
env_tmp="$(mktemp /tmp/datn-env.XXXXXX)"
trap 'rm -f "$env_tmp"' EXIT

{
  printf 'MYSQL_ROOT_PASSWORD=%s\n' "$mysql_password"
  printf 'SPRING_DATASOURCE_USERNAME=root\n'
  printf 'SPRING_DATASOURCE_PASSWORD=%s\n' "$mysql_password"
  printf 'JWT_SECRET=%s\n' "$jwt_secret"
  printf 'VM_INTERNAL_IP=10.148.0.4\n'
  printf 'VITE_API_BASE_URL=http://34.124.206.37:8080\n'
  printf 'APP_CORS_ALLOWED_ORIGINS=http://34.124.206.37\n'
  printf 'AI_SERVICE_BASE_URL=https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app\n'
  printf 'AI_SERVICE_INTERNAL_API_KEY=%s\n' "$internal_api_key"
  printf 'AI_SERVICE_TIMEOUT_SECONDS=900\n'
} > "$env_tmp"

sudo install -o root -g root -m 600 "$env_tmp" /opt/dATN/.env.production
test "$(sudo stat -c '%a:%U:%G' /opt/dATN/.env.production)" = '600:root:root'
echo 'production env installed with mode 600'
