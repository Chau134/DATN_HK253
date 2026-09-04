# Runbook deploy toàn bộ DATN lên GCP

> Cập nhật và kiểm chứng lần cuối: 2026-07-16 (Asia/Ho_Chi_Minh).
>
> Đây là tài liệu deployment chính cho frontend, Spring Boot API, MySQL, Qdrant và service-ai.
> Không copy secret thật vào tài liệu, Git, Docker image hoặc command log.

## 1. Phạm vi và kiến trúc

Kiến trúc production tách thành hai phần:

```text
Internet
  |
  +--> http://34.21.254.51:80    frontend Vite/nginx trên GCE VM
  |
  +--> http://34.21.254.51:8080  Spring Boot API trên GCE VM
                                      |
                                      +--> MySQL 8.4 (compose network only)
                                      |
                                      +--> Cloud Run service-ai (internal ingress)
                                                  |
                                                  +--> Qdrant 10.148.0.4:6333
                                                  +--> Spring API 10.148.0.4:8080
                                                  +--> Amazon Bedrock Tokyo qua HTTPS
```

- GCP project: `project-7a5551d7-985f-4ecc-985`.
- GCP region: `asia-southeast1`.
- GCE zone: `asia-southeast1-b`.
- VM: `datn-stack-vm`, `e2-standard-4`, Ubuntu 22.04, boot disk 150 GB.
- VM private/public IP: `10.148.0.4` / `34.21.254.51`.
- VM tag: `dacn-web`.
- Source trên VM: `/opt/dATN`.
- Cloud Run: `service-ai-gptoss-pilot`.
- Cloud Run live hiện tại (legacy): 1 x NVIDIA RTX PRO 6000 Blackwell, 20 CPU, 80 GiB.
- Target revision mới: CPU managed-only, 2 CPU, 4 GiB; YOLO/local models tắt.
- VPC connector: `datn-cloudrun-connector`, CIDR `10.8.0.0/28`.
- Bedrock: `openai.gpt-oss-120b-1:0`, region `ap-northeast-1` (Tokyo).
- Chỉ sync pilot 500 sản phẩm.
- Text/image/hybrid top-k tối đa đều là 5.

## 2. Trạng thái live đã kiểm tra

### 2.1 VM

| Container | Trạng thái | Network |
|---|---|---|
| `datn-frontend-1` | Up | public `80` |
| `datn-spring-api-1` | Up | public `8080` |
| `datn-mysql-1` | Up, healthy | compose network, không publish `3306` |
| `datn-qdrant-1` | Up, healthy | private `10.148.0.4:6333` |

Named volumes:

- `datn_mysql_data`;
- `datn_qdrant_storage`.

Disk VM lúc kiểm tra: 146 GiB usable, dùng khoảng 23 GiB, còn khoảng 123 GiB.

### 2.2 Cloud Run

- Ready revision: `service-ai-gptoss-pilot-00002-4h6`.
- Traffic: 100% vào latest revision.
- URL:
  `https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app`.
- Image:
  `asia-southeast1-docker.pkg.dev/project-7a5551d7-985f-4ecc-985/dacn/service-ai:20260714-gptoss-top5-cu130-v2`.
- Digest:
  `sha256:effe7b99c651db4e9345b27a8f1433037e1a469224ce0c26d5460a6dfb86e1a6`.
- Build ID: `40361da4-ddf3-4d70-9e2f-a77c0bb11b5b`.
- Ingress: internal.
- IAM invoker hiện là `allUsers`; internal ingress vẫn chặn nguồn ngoài phạm vi internal.
- Runtime service account:
  `datn-service-ai-runtime@project-7a5551d7-985f-4ecc-985.iam.gserviceaccount.com`.
- Container concurrency: 1, request timeout: 900 giây.
- Template hiện có `maxScale=3`; service metadata còn annotation `maxScale=1`. Khi deploy lại phải
  đặt rõ `--max-instances=1` hoặc `3`, không để hai giá trị mơ hồ. Pilot 500 nên dùng 1 để kiểm soát
  chi phí và model cold-load.
- `/health` trả HTTP 200 từ VM.
- Runtime log đã xác nhận CUDA 13.0.
- Revision lịch sử này từng load local Qwen3-Reranker-4B đủ 398/398 weights. Target revision mới
  dùng managed Google Cloud Ranking API nên không còn tải reranker weights; số liệu cold request
  272,5 giây bên trên không dùng làm baseline cho reranker mới.

### 2.3 Qdrant và sync

- Collection: `product_text_vectors_gptoss_pilot`.
- Vector size: 4096, distance: Cosine.
- Status: green.
- `points_count=500`.
- Sync response cuối đã ghi nhận:
  - `sync_type=limited_full`;
  - `total_count=500`;
  - `success_count=500`;
  - `failure_count=0`;
  - `batch_count=10`;
  - `failed_product_ids=[]`.
- Một số ảnh Zara trả 403; đây là image download warning, không làm thất bại text vector 500/500.

### 2.4 Hai lỗi chưa nghiệm thu

Không được coi toàn bộ service-ai là production-ready cho đến khi xử lý hai mục này:

1. **Bedrock mount sai loại credential.** Revision hiện tại mount Bedrock API key dạng `ABSK...`
   vào `AWS_SECRET_ACCESS_KEY` và một giá trị không phải IAM access key vào `AWS_ACCESS_KEY_ID`.
   Log trả `UnrecognizedClientException: The security token included in the request is invalid`.
   API key đã được test trực tiếp bằng Bearer tới Bedrock Tokyo và trả HTTP 200. Cần mount nó thành
   `AWS_BEARER_TOKEN_BEDROCK` rồi bỏ hai biến IAM sai.
2. **Metadata Qdrant và hard filter không canonical.** Qdrant lưu `Black`, `White` trong khi query
   tạo `black`, `white`; keyword filter phân biệt hoa/thường. Category `jacket` cũng không khớp trực
   tiếp `Jackets & Coats`. Query `ao khoac nam mau den` vì vậy trả HTTP 200 nhưng 0 sản phẩm. Cần sửa
   normalize/index hoặc đổi hard filter thành semantic retrieval + soft boost/rerank, rồi re-sync
   đúng 500.

## 3. File deployment trong repo

- `docker-compose.yml`: base stack MySQL, Qdrant, service-ai, Spring API, frontend.
- `docker-compose.vm.yml`: override production VM, vô hiệu hóa service-ai local và nối BE với Cloud
  Run.
- `frontend/Dockerfile`: Node 20 build Vite, nginx serve static bundle.
- `service-api-ecommerce/Dockerfile`: Maven/Java 21 multi-stage, runtime JRE 21 non-root.
- `service-ai/Dockerfile`: image CPU managed-only, không cài CUDA/PyTorch/Transformers/Ultralytics,
  runtime UID 1000. `Dockerfile.gpu` chỉ dùng khi bật lại local models.
- `service-ai/cloudbuild.kaniko.yaml`: Kaniko, `E2_HIGHCPU_8`, disk 200 GB, cache không nén và tag
  image truyền qua substitution `_IMAGE_TAG`.

Không dùng lại `Dockerfile.gpu.finalize` hoặc `cloudbuild.gpu.yaml`; đây là flow cũ đã bị hủy.

## 4. Chuẩn bị máy operator

```bash
cd /home/dungne/DATN

gcloud --version
gcloud auth list
gcloud config set project project-7a5551d7-985f-4ecc-985
gcloud config set run/region asia-southeast1
gcloud auth application-default login

gcloud services enable \
  run.googleapis.com \
  compute.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  apikeys.googleapis.com \
  generativelanguage.googleapis.com \
  discoveryengine.googleapis.com \
  iamcredentials.googleapis.com \
  vpcaccess.googleapis.com
```

Gate:

```bash
gcloud auth list --filter=status:ACTIVE
gcloud config get-value project
git status --short
```

Không deploy khi chưa biết commit/source nào sẽ phát hành. Không xóa thay đổi local của người dùng.

## 5. Tạo hạ tầng GCP từ đầu

Phần này chỉ chạy khi môi trường chưa tồn tại. Với stack hiện tại, dùng lệnh `describe` để kiểm tra,
không tạo trùng.

### 5.1 Artifact Registry

```bash
gcloud artifacts repositories describe dacn \
  --location=asia-southeast1 \
  --project=project-7a5551d7-985f-4ecc-985 \
|| gcloud artifacts repositories create dacn \
  --repository-format=docker \
  --location=asia-southeast1 \
  --description='DATN container images'

gcloud auth configure-docker asia-southeast1-docker.pkg.dev
```

### 5.2 VM

```bash
gcloud compute instances create datn-stack-vm \
  --project=project-7a5551d7-985f-4ecc-985 \
  --zone=asia-southeast1-b \
  --machine-type=e2-standard-4 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=150GB \
  --boot-disk-type=pd-balanced \
  --network=default \
  --subnet=default \
  --tags=dacn-web \
  --scopes=cloud-platform
```

Giữ static external IP nếu frontend/backend vẫn dùng IP trực tiếp; nếu IP ephemeral thay đổi thì
phải rebuild frontend vì `VITE_API_BASE_URL` được đóng vào bundle.

### 5.3 VPC connector

```bash
gcloud compute networks vpc-access connectors describe datn-cloudrun-connector \
  --region=asia-southeast1 \
|| gcloud compute networks vpc-access connectors create datn-cloudrun-connector \
  --region=asia-southeast1 \
  --network=default \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=3 \
  --machine-type=e2-micro
```

### 5.4 Firewall

```bash
gcloud compute firewall-rules describe dacn-allow-web \
|| gcloud compute firewall-rules create dacn-allow-web \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:80,tcp:8080 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=dacn-web

gcloud compute firewall-rules describe datn-allow-cloudrun-to-vm \
|| gcloud compute firewall-rules create datn-allow-cloudrun-to-vm \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:6333,tcp:8080 \
  --source-ranges=10.8.0.0/28 \
  --target-tags=dacn-web
```

Không mở port `3306` hoặc `6333` cho `0.0.0.0/0`.

### 5.5 Runtime service account

```bash
gcloud iam service-accounts describe \
  datn-service-ai-runtime@project-7a5551d7-985f-4ecc-985.iam.gserviceaccount.com \
|| gcloud iam service-accounts create datn-service-ai-runtime \
  --display-name='DATN service-ai Cloud Run runtime'

gcloud projects add-iam-policy-binding project-7a5551d7-985f-4ecc-985 \
  --member='serviceAccount:datn-service-ai-runtime@project-7a5551d7-985f-4ecc-985.iam.gserviceaccount.com' \
  --role='roles/secretmanager.secretAccessor'

gcloud projects add-iam-policy-binding project-7a5551d7-985f-4ecc-985 \
  --member='serviceAccount:datn-service-ai-runtime@project-7a5551d7-985f-4ecc-985.iam.gserviceaccount.com' \
  --role='roles/discoveryengine.user'
```

## 6. Secret Manager

### 6.1 Secret mục tiêu

- `service-ai-bedrock-bearer-token` -> Bedrock API key đầy đủ dạng `ABSK...`.
- `service-ai-gemini-api-key` -> API key chỉ cho phép `generativelanguage.googleapis.com`.
- `service-ai-internal-api-key` -> shared key giữa Spring API và service-ai.
- `datn-mysql-root-password` -> MySQL root/application password hiện tại.

JWT secret và các secret ứng dụng khác cũng nên đưa vào Secret Manager; không để trong Git.

### 6.2 Tạo hoặc thêm version không lộ giá trị

Đọc secret vào biến shell bằng prompt ẩn:

```bash
read -rsp 'Bedrock API key: ' AWS_BEARER_TOKEN_BEDROCK; echo
printf '%s' "$AWS_BEARER_TOKEN_BEDROCK" \
  | gcloud secrets create service-ai-bedrock-bearer-token \
      --replication-policy=automatic --data-file=- \
|| printf '%s' "$AWS_BEARER_TOKEN_BEDROCK" \
  | gcloud secrets versions add service-ai-bedrock-bearer-token --data-file=-
unset AWS_BEARER_TOKEN_BEDROCK
```

Áp dụng cùng pattern cho internal API key và MySQL password. Không chạy `echo $SECRET`, không bật
`set -x`, không đưa secret vào tham số `--set-env-vars`.

Trên PowerShell không dùng lệnh Bash `read`, không gõ ký tự `$` ở đầu command. Pipeline PowerShell
có thể thêm ký tự xuống dòng vào stdin; service-ai hiện strip khoảng trắng bao quanh token khi khởi
tạo Bedrock client, nhưng nên ghi secret không có CR/LF ngay từ đầu:

```powershell
$secure = Read-Host "Bedrock API key" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
)

$action = if (gcloud secrets describe service-ai-bedrock-bearer-token 2>$null) {
  @("secrets", "versions", "add", "service-ai-bedrock-bearer-token", "--data-file=-")
} else {
  @("secrets", "create", "service-ai-bedrock-bearer-token",
    "--replication-policy=automatic", "--data-file=-")
}
$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = "gcloud"
$startInfo.RedirectStandardInput = $true
$startInfo.UseShellExecute = $false
foreach ($argument in $action) { [void] $startInfo.ArgumentList.Add($argument) }
$process = [Diagnostics.Process]::Start($startInfo)
$process.StandardInput.Write($plain)
$process.StandardInput.Close()
$process.WaitForExit()
$plain = $null
$secure.Dispose()
if ($process.ExitCode -ne 0) { throw "gcloud secret update failed" }
```

Nếu token từng xuất hiện nguyên văn trong Cloud Logging thì phải thu hồi/rotate token phía AWS,
tạo secret version mới và redeploy. Redaction trong ứng dụng chỉ ngăn lần lộ tiếp theo, không làm
token cũ an toàn trở lại.

### 6.3 Migration credential Bedrock hiện tại

Revision live vẫn dùng hai secret sai:

- `service-ai-bedrock-aws-access-key-id`;
- `service-ai-bedrock-aws-secret-access-key`.

Khi migration:

1. Lấy giá trị Bedrock API key `ABSK...` hiện có và tạo version của
   `service-ai-bedrock-bearer-token`.
2. Deploy revision mới mount nó vào `AWS_BEARER_TOKEN_BEDROCK`.
3. Gỡ `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY` khỏi Cloud Run.
4. Smoke test Converse/chat thành công.
5. Chỉ sau đó mới disable/xóa hai secret cũ.

## 7. Chuẩn bị VM

```bash
gcloud compute ssh datn-stack-vm --zone=asia-southeast1-b

sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git curl jq rsync
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
sudo mkdir -p /opt/dATN /opt/backups/datn
sudo chown -R "$USER":"$USER" /opt/dATN
```

Nếu `docker-compose-v2` không có trong apt mirror, cài Docker Compose plugin từ Docker official apt
repository rồi kiểm tra lại `docker compose version`.

## 8. Đưa source lên VM

Ưu tiên release từ commit đã review để không vô tình copy `.env`, cache hoặc model weights:

```bash
cd /home/dungne/DATN
git status --short
git rev-parse HEAD
git archive --format=tar.gz --output=/tmp/datn-release.tar.gz HEAD

gcloud compute scp /tmp/datn-release.tar.gz datn-stack-vm:/tmp/ \
  --zone=asia-southeast1-b

gcloud compute ssh datn-stack-vm --zone=asia-southeast1-b --command='\
  release_dir=$(mktemp -d /tmp/datn-release.XXXXXX) && \
  tar -xzf /tmp/datn-release.tar.gz -C "$release_dir" && \
  sudo mkdir -p /opt/dATN && \
  sudo rsync -a --delete --exclude=.env.production "$release_dir"/ /opt/dATN/ && \
  rm -rf "$release_dir" /tmp/datn-release.tar.gz'

rm -f /tmp/datn-release.tar.gz
```

Không dùng `git archive` nếu thay đổi cần deploy chưa được commit. Khi đó phải tạo release artifact
có danh sách file rõ ràng và rà lại để không chứa `service-ai/.env` hoặc secret. `rsync --delete`
giúp xóa file release cũ không còn trong commit, nhưng giữ `.env.production`; dữ liệu DB/Qdrant nằm
trong Docker named volumes, không nằm trong thư mục source này.

## 9. Env production cho compose VM

Compose production dùng:

```text
/opt/dATN/docker-compose.yml
/opt/dATN/docker-compose.vm.yml
```

Tạo `/opt/dATN/.env.production`, owner root và mode 600:

```dotenv
MYSQL_ROOT_PASSWORD=<secret>
SPRING_DATASOURCE_USERNAME=root
SPRING_DATASOURCE_PASSWORD=<same-mysql-password>
JWT_SECRET=<strong-production-secret>

VM_INTERNAL_IP=10.148.0.4
VITE_API_BASE_URL=http://34.21.254.51:8080
APP_CORS_ALLOWED_ORIGINS=http://34.21.254.51

AI_SERVICE_BASE_URL=https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app
AI_SERVICE_INTERNAL_API_KEY=<same-as-service-ai-internal-api-key>
AI_SERVICE_TIMEOUT_SECONDS=900
```

Các URL `http://<PUBLIC_IP>` trong runbook chỉ dùng cho pilot tạm thời. Trước production phải đặt
frontend/backend sau HTTPS load balancer hoặc reverse proxy có certificate hợp lệ, đổi CORS/API URL
sang `https://...` và không truyền admin JWT qua HTTP công khai.

```bash
sudo chown root:root /opt/dATN/.env.production
sudo chmod 600 /opt/dATN/.env.production
```

`VITE_API_BASE_URL` là build-time variable; đổi URL phải rebuild frontend. Không chỉ restart.

## 10. Backup trước deploy VM

Không deploy/recreate DB hoặc Qdrant trước khi có backup.

Chạy các lệnh sau bên trong VM:

```bash
cd /opt/dATN

sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml \
  exec -T mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" \
  --single-transaction --routines --triggers DACN' \
  | sudo tee /opt/backups/datn/mysql-DACN-$(date +%Y%m%d-%H%M%S).sql >/dev/null

curl -fsS -X POST \
  http://10.148.0.4:6333/collections/product_text_vectors_gptoss_pilot/snapshots
```

Ghi lại tên snapshot. Tuyệt đối không dùng `docker compose down -v`.

## 11. Deploy MySQL, Qdrant, backend và frontend

### 11.1 Validate và build

```bash
cd /opt/dATN

sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml config --quiet

sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml \
  build spring-api frontend
```

### 11.2 Start theo thứ tự

```bash
# Data services trước, giữ nguyên named volumes.
sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml \
  up -d mysql qdrant

sudo docker inspect datn-mysql-1 --format '{{.State.Health.Status}}'
sudo docker inspect datn-qdrant-1 --format '{{.State.Health.Status}}'

# Backend sau khi MySQL healthy.
sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml \
  up -d --no-deps --force-recreate spring-api

curl -fsS http://127.0.0.1:8080/api/blogs >/dev/null

# Frontend cuối cùng.
sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml \
  up -d --no-deps --force-recreate frontend
```

Không chạy service-ai bằng compose trên VM. `docker-compose.vm.yml` phải giữ profile
`cloud-run-only` cho service này.

### 11.3 Khởi tạo database lần đầu

Chỉ áp dụng với `datn_mysql_data` mới hoàn toàn:

1. Start MySQL.
2. Start Spring API để `schema.sql` tạo schema.
3. Import data một lần:

```bash
sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml \
  exec -T mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" DACN' \
  < database/data.sql
```

Production DB đã có dữ liệu thì không import `database/data.sql` trong mỗi lần deploy. Schema change
phải có migration/review riêng và backup trước.

## 12. Build image service-ai managed-only (CPU)

`service-ai/Dockerfile` hiện dùng:

- `python:3.11-slim`;
- Cohere Embed v4 trên Amazon Bedrock và Ranking API chạy managed;
- YOLO tắt và dùng full-image fallback;
- không cài CUDA, PyTorch, Transformers hoặc Ultralytics;
- runtime user UID 1000.

Build bằng Kaniko từ đúng thư mục `service-ai`:

```bash
cd /home/dungne/DATN/service-ai

gcloud builds submit . \
  --project=project-7a5551d7-985f-4ecc-985 \
  --region=asia-southeast1 \
  --config=cloudbuild.kaniko.yaml \
  --substitutions=_IMAGE_TAG=<IMMUTABLE_TAG>
```

Xem log:

```bash
gcloud builds list --limit=5 --region=asia-southeast1
gcloud builds log <BUILD_ID> --stream --region=asia-southeast1
```

Build gate sau khi chạy container phải xác nhận:

```text
/health/ready trả ready=true
models.yolo=false
importlib.util.find_spec("torch") trả None
```

Không dùng `Dockerfile.gpu` trong flow này. Khi cần bật lại local embedding/YOLO thì build extra
`local-models`, kiểm tra CUDA riêng và cập nhật sizing trước khi deploy.

## 13. Env Cloud Run service-ai

Non-secret env mục tiêu:

```dotenv
APP_ENV=production
APP_PORT=8000
LLM_PROVIDER=bedrock
BEDROCK_REGION=ap-northeast-1
BEDROCK_MODEL_ID=openai.gpt-oss-120b-1:0
BEDROCK_TEMPERATURE=0.2
BEDROCK_MAX_TOKENS=2048
BEDROCK_TIMEOUT_SECONDS=30
BEDROCK_RETRY_ATTEMPTS=2

PRELOAD_MODELS=true
EMBEDDING_PROVIDER=bedrock
BEDROCK_EMBEDDING_MODEL_ID=cohere.embed-v4:0
BEDROCK_EMBEDDING_IMAGE_MAX_SIDE=512
BEDROCK_EMBEDDING_MIN_REQUEST_INTERVAL_SECONDS=1
BEDROCK_EMBEDDING_THROTTLE_RETRY_ATTEMPTS=6
BEDROCK_EMBEDDING_THROTTLE_BACKOFF_SECONDS=2
BEDROCK_EMBEDDING_THROTTLE_MAX_BACKOFF_SECONDS=30
EMBEDDING_OUTPUT_DIMENSIONALITY=1536
GOOGLE_CLOUD_PROJECT=project-7a5551d7-985f-4ecc-985
QDRANT_TEXT_VECTOR_SIZE=1536
QDRANT_TEXT_COLLECTION=product_text_vectors_cohere_embed_v4_1536
QDRANT_IMAGE_VECTOR_SIZE=1536
QDRANT_IMAGE_COLLECTION=product_image_vectors_cohere_embed_v4_1536

CHECKPOINT_BACKEND=redis
ASSISTANT_RECENT_MESSAGE_LIMIT=12
ASSISTANT_CONVERSATION_SUMMARY_MAX_CHARS=3000
ASSISTANT_CONVERSATION_CONTEXT_MAX_CHARS=8000
ASSISTANT_USER_MEMORY_ENABLED=true
ASSISTANT_USER_MEMORY_BACKEND=redis
ASSISTANT_USER_MEMORY_TTL_SECONDS=15552000
ASSISTANT_USER_MEMORY_MAX_NOTES=5

RERANK_ENABLED=true
RERANK_TOP_K=20
RERANKER_MODEL_NAME=semantic-ranker-default@latest
RERANKER_LOCATION=global
RERANKER_CONFIG_ID=default_ranking_config
RERANKER_TIMEOUT_SECONDS=10
YOLO_ENABLED=false

QDRANT_URL=http://10.148.0.4:6333
SPRINGBOOT_BASE_URL=http://10.148.0.4:8080
TEXT_TOP_K=5
IMAGE_TOP_K=5
HYBRID_TOP_K=5
MAX_SEARCH_TOP_K=50
IMAGE_CANDIDATE_POOL_SIZE=20
IMAGE_QUERY_PER_CROP_LIMIT_CAP=50
```

`RERANK_TOP_K=20` nằm trong một billing count của Ranking API vì nhỏ hơn 100 records/request.
Ranking API chưa liệt kê `vi-VN` là ngôn ngữ hỗ trợ chính thức, nên phải chạy behavioral/search eval
tiếng Việt trên candidate revision trước khi chuyển traffic.

Không cần khai báo `BEDROCK_TOP_P` hoặc `BEDROCK_ENDPOINT_URL` khi để trống; config tự dùng endpoint
Bedrock Runtime chuẩn theo region.

Secret env:

```text
AWS_BEARER_TOKEN_BEDROCK <- service-ai-bedrock-bearer-token:latest
INTERNAL_API_KEY         <- service-ai-internal-api-key:latest
SPRINGBOOT_API_KEY       <- service-ai-internal-api-key:latest
REDIS_URL                <- assistant-redis-url:latest
```

Không còn dùng `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY` cho Bedrock API key dạng `ABSK...`.
Nếu Hugging Face rate-limit hoặc timeout làm model không tải được ổn định, thêm `HF_TOKEN` từ Secret
Manager; không ghi token này vào image hoặc env command. Flow managed-only hiện tại không dùng
Hugging Face.

Không dùng `CHECKPOINT_BACKEND=sqlite` trên Cloud Run vì filesystem của instance là tạm thời. Cấu
hình `CHECKPOINT_BACKEND=redis` và secret `REDIS_URL` (ví dụ
`redis://10.x.x.x:6379`) trước khi nghiệm thu assistant session. Service account của Cloud Run phải
có role `roles/discoveryengine.user` cho Ranking API. Reranker dùng Application Default
Credentials. Cohere Embed v4 dùng cùng credential chain với Bedrock LLM và không tải model vào
image. Cohere Embed v4 không tương thích vector space với Gemini hoặc Qwen cũ, vì vậy phải tạo hai
collection mới đúng 1536 chiều và re-index toàn bộ sản phẩm; không đổi dimension trên collection cũ.

## 14. Deploy Cloud Run CPU

Ví dụ dưới đây dùng max instance 1 cho pilot. Dùng tag immutable mới, không ghi đè tag cũ.

```bash
PROJECT_ID=project-7a5551d7-985f-4ecc-985
REGION=asia-southeast1
SERVICE=service-ai-gptoss-pilot
IMAGE=asia-southeast1-docker.pkg.dev/$PROJECT_ID/dacn/service-ai:<IMMUTABLE_TAG>

gcloud run deploy "$SERVICE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --image="$IMAGE" \
  --execution-environment=gen2 \
  --service-account=datn-service-ai-runtime@$PROJECT_ID.iam.gserviceaccount.com \
  --cpu=2 \
  --memory=4Gi \
  --concurrency=20 \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=1 \
  --no-traffic \
  --tag=candidate \
  --no-cpu-throttling \
  --port=8080 \
  --ingress=internal \
  --allow-unauthenticated \
  --vpc-connector=datn-cloudrun-connector \
  --vpc-egress=private-ranges-only \
  --startup-probe='httpGet.path=/health,httpGet.port=8080,timeoutSeconds=10,periodSeconds=10,failureThreshold=24' \
  --set-env-vars='APP_ENV=production,APP_PORT=8000,LLM_PROVIDER=bedrock,BEDROCK_REGION=ap-northeast-1,BEDROCK_MODEL_ID=openai.gpt-oss-120b-1:0,BEDROCK_EMBEDDING_MODEL_ID=cohere.embed-v4:0,BEDROCK_EMBEDDING_IMAGE_MAX_SIDE=512,BEDROCK_EMBEDDING_MIN_REQUEST_INTERVAL_SECONDS=1,BEDROCK_EMBEDDING_THROTTLE_RETRY_ATTEMPTS=6,BEDROCK_EMBEDDING_THROTTLE_BACKOFF_SECONDS=2,BEDROCK_EMBEDDING_THROTTLE_MAX_BACKOFF_SECONDS=30,BEDROCK_TEMPERATURE=0.2,BEDROCK_MAX_TOKENS=2048,BEDROCK_TIMEOUT_SECONDS=30,BEDROCK_RETRY_ATTEMPTS=2,PRELOAD_MODELS=true,EMBEDDING_PROVIDER=bedrock,EMBEDDING_OUTPUT_DIMENSIONALITY=1536,GOOGLE_CLOUD_PROJECT=project-7a5551d7-985f-4ecc-985,QDRANT_TEXT_VECTOR_SIZE=1536,QDRANT_TEXT_COLLECTION=product_text_vectors_cohere_embed_v4_1536,QDRANT_IMAGE_VECTOR_SIZE=1536,QDRANT_IMAGE_COLLECTION=product_image_vectors_cohere_embed_v4_1536,CHECKPOINT_BACKEND=redis,ASSISTANT_RECENT_MESSAGE_LIMIT=12,ASSISTANT_CONVERSATION_SUMMARY_MAX_CHARS=3000,ASSISTANT_CONVERSATION_CONTEXT_MAX_CHARS=8000,ASSISTANT_USER_MEMORY_ENABLED=true,ASSISTANT_USER_MEMORY_BACKEND=redis,ASSISTANT_USER_MEMORY_TTL_SECONDS=15552000,ASSISTANT_USER_MEMORY_MAX_NOTES=5,RERANK_ENABLED=true,RERANKER_MODEL_NAME=semantic-ranker-default@latest,RERANKER_LOCATION=global,RERANKER_CONFIG_ID=default_ranking_config,RERANKER_TIMEOUT_SECONDS=10,YOLO_ENABLED=false,QDRANT_URL=http://10.148.0.4:6333,SPRINGBOOT_BASE_URL=http://10.148.0.4:8080,TEXT_TOP_K=5,IMAGE_TOP_K=5,HYBRID_TOP_K=5' \
  --set-secrets='AWS_BEARER_TOKEN_BEDROCK=service-ai-bedrock-bearer-token:latest,INTERNAL_API_KEY=service-ai-internal-api-key:latest,SPRINGBOOT_API_KEY=service-ai-internal-api-key:latest,REDIS_URL=assistant-redis-url:latest'
```

Lấy URL của traffic tag và poll readiness từ VM; mỗi lần poll giữ candidate instance hoạt động
trong lúc background preload:

```bash
CANDIDATE_URL=$(
  gcloud run services describe "$SERVICE" \
    --region="$REGION" \
    --format=json \
  | jq -r '.status.traffic[] | select(.tag=="candidate") | .url'
)

until curl -fsS "$CANDIDATE_URL/health/ready" | jq -e '.ready == true'; do
  sleep 15
done

gcloud run services update-traffic "$SERVICE" \
  --region="$REGION" \
  --to-tags=candidate=100
```

`SPRINGBOOT_API_KEY` phải dùng cùng secret với `AI_SERVICE_INTERNAL_API_KEY` của Spring Boot để gọi
endpoint batch `/api/internal/ai/products/context`. `--set-secrets` thay toàn bộ secret mapping của
revision bằng các mapping mục tiêu ở trên. Sau khi
deploy, kiểm tra YAML; nếu hai mapping cũ vẫn còn do deployment được thực hiện bằng flow khác, gỡ
chúng bằng nhóm flag secret, không dùng `--remove-env-vars`:

```bash
gcloud run services update service-ai-gptoss-pilot \
  --region=asia-southeast1 \
  --remove-secrets=AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY
```

Không ghép `--set-env-vars` với `--remove-env-vars` trong cùng lệnh; gcloud CLI chỉ cho ghép
`--update-env-vars` với `--remove-env-vars`.

Cloud Run inject `PORT=8080`; command uvicorn trong image dùng `${PORT:-$APP_PORT}`. Startup probe
phải gọi port 8080, không gọi 8000. Cloud Run giới hạn tổng thời gian startup probe ở 240 giây;
model preload chạy background sau khi server đã lắng nghe. Không dùng `/health/ready` làm startup
probe khi tổng thời gian tải model có thể vượt 240 giây.

## 15. Nối backend với Cloud Run

Trong `.env.production` của VM:

```dotenv
AI_SERVICE_ENABLED=true
AI_SERVICE_MOCK=false
AI_SERVICE_BASE_URL=https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app
AI_SERVICE_INTERNAL_API_KEY=<same-secret-as-cloud-run>
AI_SERVICE_TIMEOUT_SECONDS=900
AI_SERVICE_SYNC_BATCH_SIZE=50
```

Recreate riêng backend, không restart MySQL/Qdrant/frontend nếu không cần:

```bash
cd /opt/dATN
sudo docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.vm.yml \
  up -d --no-deps --force-recreate spring-api
```

## 16. Tạo collection và sync đúng 500 sản phẩm

### 16.1 Collections Cohere Embed v4

Chạy trên VM và chỉ tạo nếu collection chưa tồn tại. Text và image cùng dùng vector 1536 chiều:

```bash
curl -fsS -X PUT \
  http://10.148.0.4:6333/collections/product_text_vectors_cohere_embed_v4_1536 \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"size":1536,"distance":"Cosine"},"on_disk_payload":true}'

curl -fsS -X PUT \
  http://10.148.0.4:6333/collections/product_image_vectors_cohere_embed_v4_1536 \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"size":1536,"distance":"Cosine"},"on_disk_payload":true}'
```

Nếu collection đã có dữ liệu, snapshot trước; không xóa để “thử lại” khi chưa được phép.

### 16.2 Warm-up trước sync

Từ VM:

```bash
curl -fsS \
  https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app/health
```

`/health/ready` chỉ trả thành công sau khi các managed client embedding/reranker được khởi tạo và
YOLO đã load.
Deploy revision mới với no traffic hoặc traffic tag, giữ ít nhất một instance để background preload
chạy, rồi poll endpoint này từ VM trước khi chuyển traffic. Không bắt đầu sync nếu readiness chưa
đạt; lỗi tải model phải được xử lý bằng token/cache hoặc build artifact ổn định, không gửi nhiều
request song song để thử lại.

### 16.3 Sync

Endpoint `/admin/**` yêu cầu JWT role ADMIN. Lấy admin JWT qua flow login, tạo đúng một job rồi poll
job đó; timeout phía operator không làm mất trạng thái và không phải gửi lại mutation:

Với catalog ảnh và Bedrock throttling backoff, cấu hình Spring API
`AI_SERVICE_TIMEOUT_SECONDS=600` để một batch không bị cắt giữa chừng.

```bash
JOB_ID=$(
  curl -fsS -X POST \
    'http://34.21.254.51:8080/admin/ai-sync/jobs/limit?limit=500' \
    -H "Authorization: Bearer $ADMIN_JWT" \
  | jq -r '.job_id'
)

curl -fsS \
  "http://34.21.254.51:8080/admin/ai-sync/jobs/$JOB_ID" \
  -H "Authorization: Bearer $ADMIN_JWT" \
| jq
```

Không gửi job sync thứ hai khi job đầu còn `QUEUED` hoặc `RUNNING`.

Gate bắt buộc:

```text
total_count=500
success_count=500
failure_count=0
batch_count=10
image_indexed_count>0
image_failure_count được rà soát và giải thích
failed_product_ids=[]
```

Kiểm tra Qdrant:

```bash
curl -fsS \
  http://10.148.0.4:6333/collections/product_text_vectors_cohere_embed_v4_1536 \
  | jq '.result | {status, points_count, indexed_vectors_count, vector_size:.config.params.vectors.size}'
```

`points_count` phải đúng 500. Warning ảnh 403 cần ghi log riêng nhưng không được che giấu text sync
failure.

## 17. Verification toàn stack

### 17.1 VM containers

```bash
gcloud compute ssh datn-stack-vm --zone=asia-southeast1-b --command='\
  sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

curl -fsSI http://34.21.254.51/
curl -fsS http://34.21.254.51:8080/api/blogs >/dev/null
curl -fsS http://10.148.0.4:6333/healthz
```

Repo hiện không expose `/actuator/health`; dùng public read endpoint như `/api/blogs` làm backend
smoke test.

### 17.2 Cloud Run

```bash
gcloud run services describe service-ai-gptoss-pilot \
  --region=asia-southeast1 \
  --format='yaml(status.latestReadyRevisionName,status.traffic,spec.template.spec.containers)'

gcloud compute ssh datn-stack-vm --zone=asia-southeast1-b --command='\
  curl -fsS https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app/health'
```

Runtime logs không được import/load CUDA, Torch, Transformers, Ultralytics và không còn
`UnrecognizedClientException`. `/health/ready` phải trả `models.yolo=false` nhưng `ready=true`.

### 17.3 Search top 5

```bash
gcloud compute ssh datn-stack-vm --zone=asia-southeast1-b --command='\
  curl -fsS -H "Content-Type: application/json" \
  -d '\''{"query":"ao khoac nam mau den","top_k":5}'\'' \
  https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app/search/text'
```

Gate:

- HTTP 200;
- `results` không rỗng với query có sản phẩm phù hợp;
- không quá 5 `product_ids`/results;
- Bedrock query analysis không fallback do credential;
- Qdrant query và reranker không phát sinh exception.

Hiện gate “không rỗng” chưa đạt vì mismatch metadata/filter đã ghi ở mục 2.4.

### 17.4 Assistant/Bedrock

```bash
gcloud compute ssh datn-stack-vm --zone=asia-southeast1-b --command='\
  curl -fsS --max-time 180 \
  -H "Content-Type: application/json" \
  -d '\''{"session_id":"smoke-bedrock","user_id":"admin","message":"Goi y ao khoac nam mau den","locale":"vi-VN"}'\'' \
  https://service-ai-gptoss-pilot-971468826250.asia-southeast1.run.app/assistant/chat'
```

Chỉ đạt khi response hợp lệ và log không có `llm_analyze_user_query_failed`.

## 18. Log và theo dõi

### 18.1 Docker VM

```bash
gcloud compute ssh datn-stack-vm --zone=asia-southeast1-b --command='\
  sudo docker logs --tail 300 datn-spring-api-1; \
  sudo docker logs --tail 100 datn-frontend-1; \
  sudo docker logs --tail 100 datn-qdrant-1; \
  sudo docker logs --tail 100 datn-mysql-1'
```

### 18.2 Cloud Run

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="service-ai-gptoss-pilot"' \
  --project=project-7a5551d7-985f-4ecc-985 \
  --limit=200 \
  --order=desc \
  --format=json
```

Lọc lỗi Bedrock:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="service-ai-gptoss-pilot" AND jsonPayload.message="llm_analyze_user_query_failed"' \
  --limit=20 --order=desc --format=json
```

Không in toàn bộ env của container vì có thể lộ secret.

## 19. Rollback

### 19.1 Cloud Run

```bash
gcloud run revisions list \
  --service=service-ai-gptoss-pilot \
  --region=asia-southeast1

gcloud run services update-traffic service-ai-gptoss-pilot \
  --region=asia-southeast1 \
  --to-revisions=<LAST_GOOD_REVISION>=100
```

Không rollback về image CUDA 12.x. Revision “last good” phải đạt health, CUDA, Bedrock và search
gate, không chỉ `Ready=True`.

### 19.2 Frontend/backend

- Tag image VM theo commit/release để có thể quay lại.
- Đổi image về tag trước rồi recreate riêng `spring-api` hoặc `frontend`.
- Không restart MySQL/Qdrant khi rollback application nếu không cần.

### 19.3 MySQL

- Không xóa volume để rollback.
- Restore dump vào DB/container tạm và kiểm tra trước.
- Chỉ thay production DB sau khi xác nhận schema/data.

### 19.4 Qdrant

- Giữ snapshot và collection pilot cũ.
- Không drop collection đang phục vụ cho đến khi collection mới sync đủ và smoke test đạt.
- Vector dimension đổi thì tạo collection versioned mới; không mutate collection cũ tại chỗ.

Các lệnh cấm trong deploy/rollback thông thường:

```text
docker compose down -v
docker volume rm datn_mysql_data
docker volume rm datn_qdrant_storage
git reset --hard
```

## 20. Thứ tự chạy khi tiếp tục từ trạng thái hiện tại

Không cần tạo lại VM hoặc sync lại ngay. Tiếp tục theo thứ tự:

1. Sửa/canonicalize metadata filter hoặc chuyển color/gender/category sang soft boost phù hợp.
2. Chạy test search/filter/ranking cục bộ.
3. Build image CPU managed-only tag mới bằng Kaniko.
4. Tạo `service-ai-bedrock-bearer-token` và `service-ai-gemini-api-key` trong Secret Manager.
5. Deploy revision Cloud Run mới với hai secret; bỏ hai biến IAM sai.
6. Xác nhận health, không có local/GPU model, Gemini API, reranker và Bedrock.
7. Snapshot Qdrant collection hiện tại.
8. Recreate/version collection nếu thay đổi payload/indexing yêu cầu reindex.
9. Chạy đúng một limited sync 500.
10. Kiểm tra Qdrant đúng 500 points.
11. Smoke text search top 5 và assistant chat.
12. Chỉ khi tất cả gate đạt mới đánh dấu deployment hoàn thành.

## 21. Checklist nghiệm thu cuối

- [ ] VM `datn-stack-vm` RUNNING, IP/private network đúng.
- [ ] Frontend HTTP 200.
- [ ] Backend `/api/blogs` HTTP 200 và kết nối MySQL.
- [ ] MySQL healthy, volume `datn_mysql_data` còn nguyên.
- [ ] Qdrant healthy, volume `datn_qdrant_storage` còn nguyên.
- [ ] Firewall không public MySQL/Qdrant.
- [ ] Cloud Run Ready, traffic 100% vào revision mới.
- [ ] Revision CPU managed-only; không cài CUDA/Torch/Transformers/Ultralytics.
- [ ] `PRELOAD_MODELS=true`, `/health/ready` đạt với `models.yolo=false`.
- [ ] Bedrock dùng `AWS_BEARER_TOKEN_BEDROCK`, không còn credential IAM giả.
- [ ] Bedrock GPT OSS 120B Tokyo trả response hợp lệ.
- [ ] Text collection dimension 4096/Cosine.
- [ ] Sync chính xác 500/500, failure 0, Qdrant points 500.
- [ ] Text/image/hybrid trả tối đa 5 sản phẩm.
- [ ] Query có dữ liệu phù hợp không trả rỗng do hard filter/case mismatch.
- [ ] Discovery Engine API đã bật, runtime service account có quyền rank và managed reranker không lỗi.
- [ ] Generative Language API key chỉ giới hạn đúng API, billing/credits còn hoạt động, Gemini
      Embedding 2 text và image đều trả vector 1536 chiều.
- [ ] Backup MySQL và Qdrant snapshot đã lưu.
- [ ] Có revision/image/tag rollback đã xác nhận tốt.
