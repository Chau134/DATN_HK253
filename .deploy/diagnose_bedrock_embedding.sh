#!/usr/bin/env bash
set -euo pipefail

project_id='project-7a5551d7-985f-4ecc-985'
registry='asia-southeast1-docker.pkg.dev'
image="$registry/$project_id/dacn/service-ai:20260922-d2e04d7-cpu-1000"

gcloud auth print-access-token | sudo docker login -u oauth2accesstoken --password-stdin "https://$registry" >/dev/null
sudo docker pull "$image" >/dev/null

env_file="$(mktemp /tmp/bedrock-diagnostic.XXXXXX)"
trap 'sudo rm -f "$env_file"' EXIT
sudo install -o root -g root -m 600 /dev/null "$env_file"
token="$(gcloud secrets versions access latest --secret=service-ai-bedrock-bearer-token --project="$project_id")"
sudo sh -c 'printf "AWS_BEARER_TOKEN_BEDROCK=%s\n" "$1" > "$2"' _ "$token" "$env_file"
unset token

sudo docker run --rm \
  --env-file "$env_file" \
  -e BEDROCK_REGION=ap-northeast-1 \
  -e BEDROCK_EMBEDDING_MODEL_ID=global.cohere.embed-v4:0 \
  -e EMBEDDING_PROVIDER=bedrock \
  -e EMBEDDING_OUTPUT_DIMENSIONALITY=1536 \
  --entrypoint python \
  "$image" \
  -c 'from ecommerce_search_assistant.services.embeddings.factory import get_text_embedding_service; import traceback; s=get_text_embedding_service();
try:
 s.warmup(); print("BEDROCK_EMBEDDING_OK")
except Exception as exc:
 print("BEDROCK_EMBEDDING_ERROR", type(exc).__name__, str(exc)); raise'
