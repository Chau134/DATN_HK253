# AI Ecommerce Search Assistant

Clean FastAPI project for an AI ecommerce search assistant. Model-heavy work is isolated behind lazy services so the API structure, configuration, indexing, search, LLM providers, and assistant workflow can evolve independently.

## Project shape

```text
src/ecommerce_search_assistant/
├── api/
│   ├── dependencies.py
│   ├── router.py
│   └── routes/
│       ├── health.py
│       ├── assistant.py
│       ├── internal_indexing.py
│       └── search.py
├── core/
│   ├── config.py
│   └── logging.py
├── infrastructure/
│   ├── qdrant.py
│   └── springboot.py
├── schemas/
│   ├── assistant.py
│   ├── chat.py
│   ├── indexing.py
│   ├── media.py
│   ├── product.py
│   └── search.py
├── services/
│   ├── assistant/
│   │   ├── checkpointer.py
│   │   ├── factory.py
│   │   ├── state.py
│   │   └── workflow.py
│   ├── cropping/
│   │   ├── factory.py
│   │   └── yolo.py
│   ├── embeddings/
│   │   ├── factory.py
│   │   ├── formatting.py
│   │   ├── image.py
│   │   ├── interfaces.py
│   │   ├── mock.py
│   │   └── text.py
│   ├── bedrock/
│   │   └── service.py
│   ├── llm/
│   │   ├── factory.py
│   │   ├── interfaces.py
│   │   └── service.py
│   ├── query_understanding/
│   │   ├── factory.py
│   │   └── service.py
│   ├── indexing/
│   │   ├── factory.py
│   │   ├── image_loader.py
│   │   └── product.py
│   └── search/
│       ├── factory.py
│       └── service.py
└── main.py
```

## Local run

```bash
cp .env.example .env
python -m pip install -e '.[dev,local-models]'
python -m uvicorn ecommerce_search_assistant.main:app --reload
```

For local direct Cohere Trial Key usage without Docker Compose, edit `service-ai/.env`:

```env
EMBEDDING_PROVIDER=cohere
COHERE_API_KEY=your-cohere-trial-key
COHERE_EMBEDDING_MODEL_NAME=embed-v4.0
EMBEDDING_OUTPUT_DIMENSIONALITY=1536
QDRANT_TEXT_VECTOR_SIZE=1536
QDRANT_IMAGE_VECTOR_SIZE=1536
RERANK_ENABLED=false
LLM_PROVIDER=fallback
YOLO_ENABLED=false
PRELOAD_MODELS=false
```

Then run from `service-ai`:

```powershell
python -m pip install -e ".[dev]"
python -m ecommerce_search_assistant.infrastructure.qdrant
python -m uvicorn ecommerce_search_assistant.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

For Docker Compose with a Bedrock API key, run this from the repository root:

```powershell
.\service-ai\scripts\start-service-ai.ps1
```

For a short-term key, pass the exact AWS Region in which the key was generated:

```powershell
.\service-ai\scripts\start-service-ai.ps1 -BedrockRegion ap-southeast-1
```

The script prompts for the key without echoing it, passes it only to the Compose
process, recreates `service-ai`, and waits for `/health/ready`. If Bedrock rejects
the key or model warmup fails, the script exits with the latest container logs.
Readiness is checked against the container itself, so a separate local Uvicorn
process on port 8000 cannot produce a false result.
It does not save the key to `.env` or another repository file.

Capability-specific readiness and Prometheus-compatible search metrics:

```bash
curl http://localhost:8000/health/ready/text_search
curl http://localhost:8000/metrics
```

Text search uses a guarded deterministic fast path for catalog-like queries and
keeps LLM query understanding for ambiguous requests. Configure it with
`TEXT_LLM_FAST_PATH_ENABLED` and `TEXT_LLM_FAST_PATH_MIN_TOKENS`. Catalog
metadata is cached for `TEXT_CATALOG_METADATA_CACHE_TTL_SECONDS` (30 minutes by
default), avoiding a Qdrant metadata scan in the middle of a normal benchmark.
Stage latency, LLM/fast-path counts, recovery decisions, request outcomes, and
result counts are exported without raw-query labels.

Catalog-aware rejection is enabled by
`TEXT_OUT_OF_CATALOG_REJECTION_ENABLED`. An impossible price or unknown explicit
brand is rejected immediately. Other inferred invalid attributes are rejected
only when the query also lacks strong lexical evidence in the catalog's
normalized titles; this prevents a missing color/material metadata value from
blocking a real title. Explicit request filters remain authoritative and
continue through the normal hard-filter path.

## Configuration

All runtime configuration lives in `.env` and is loaded through `pydantic-settings`. The current phase covers app, security, Spring Boot, Qdrant, Bedrock LLM, YOLO, embeddings, uploads, search tuning, checkpoint storage, and optional observability settings.

`CORS_ORIGINS` and `ALLOWED_IMAGE_MIME_TYPES` use comma-separated values. Hybrid search weights are validated at startup and must sum to `1.0`.

LLM calls are selected with `LLM_PROVIDER`. Use `LLM_PROVIDER=bedrock` for Bedrock calls through the AWS SDK credential chain. Use `LLM_PROVIDER=fallback` for deterministic local behavior without a remote LLM call.

Assistant query understanding uses a smaller latency-oriented budget than reply
generation. `ASSISTANT_QUERY_CONTEXT_MAX_CHARS` bounds only the conversation
context sent to query analysis, while `ASSISTANT_CONVERSATION_CONTEXT_MAX_CHARS`
continues to bound the richer reply context. For Bedrock,
`BEDROCK_QUERY_UNDERSTANDING_MAX_TOKENS` limits the compact structured JSON
response independently of `BEDROCK_MAX_TOKENS`. The concurrent load runner uses
the NFR-01 acceptance gate of Assistant P95 <= 5 seconds by default.

## Domain schemas

Phase 2 adds Pydantic request and response contracts for product indexing, text search, image search, hybrid search, and assistant chat. Search filters remain optional, product indexing requires a non-empty `product_id` plus text or image content, and image payload schemas enforce `MAX_UPLOAD_MB` and allowed MIME types from config.

## Qdrant bootstrap

Phase 3 adds an idempotent Qdrant bootstrap module at `ecommerce_search_assistant.infrastructure.qdrant`. It creates the text and image vector collections from config, then ensures payload indexes exist for:

- `product_id`
- `category_codes`
- `category_keys`
- `brand_key`
- `color_keys`
- `material_keys`
- `size_keys`
- `gender_key`, `audience_keys`
- `normalized_title`, `normalized_title_vi`
- `metadata_schema_version`
- `active`
- `selling_price`

Only normalized titles are retained for deterministic exact-title retrieval; full display metadata
still comes from Spring Boot. Product updates
delete the product's old text and image points before embedding and upserting the current metadata.
Category identity comes from Spring's `category_code`; a shared taxonomy expands compound categories
into atomic filter keys (for example, `shirt_blouse` becomes `shirt` and `blouse`). Name-based
canonicalization remains only as a compatibility fallback for older indexing requests.

Run the bootstrap manually after dependencies are installed:

```bash
python -m ecommerce_search_assistant.infrastructure.qdrant
```

Bootstrap only creates collections when missing; it never resizes an existing one. If a collection's vector size differs from `QDRANT_*_VECTOR_SIZE`, it logs a `qdrant_dimension_mismatch` warning telling you to drop and recreate it.

## Managed Cohere Embed v4 profiles

The service defaults to `EMBEDDING_PROVIDER=bedrock` with managed `cohere.embed-v4:0` for both text and image embeddings. Both collections use 1536 dimensions by default. The Bedrock adapter authenticates through the standard AWS credential chain and does not download embedding weights into the service. For local use with a Cohere dashboard Trial Key, set `EMBEDDING_PROVIDER=cohere`, `COHERE_API_KEY`, and `COHERE_EMBEDDING_MODEL_NAME=embed-v4.0`; this calls Cohere directly through the Cohere SDK. Product images are embedded once per product batch. `EMBEDDING_PROVIDER=local` remains an explicit development fallback.

Cohere Embed v4 uses a different vector space from Gemini and the previous Qwen models, so both Qdrant collections must be recreated under new names and all products re-indexed. Never mix vectors from different models or dimensions.

Steps:

1. Stop the service.
2. Preserve/snapshot the old collections and configure new collection names. Do not resize or overwrite the old collections.
3. Recreate collections: `python -m ecommerce_search_assistant.infrastructure.qdrant`.
4. Re-index every product through the internal indexing routes from Spring Boot so both the new vectors and the `embedding_text` payload used by the reranker are written from the live MySQL catalog.
5. Restart the service.

Reranking is off by default. Set `RERANK_ENABLED=true` after enabling the Google Cloud Discovery
Engine API and granting the runtime identity `discoveryengine.rankingConfigs.rank`. The managed
Ranking API defaults to `semantic-ranker-default@latest`; no reranker weights are downloaded or
loaded in this service. Text search retrieves `max(output_top_k, RERANK_TOP_K)` candidates, reranks
up to `RERANK_TOP_K`, and
only then cuts the response to `output_top_k`; hybrid search also reranks its top candidate window.
Image-only search is unaffected. Reranking falls back to retrieval order if the managed API errors.
`PRELOAD_MODELS=true` initializes managed clients (including the configured LLM) and warms enabled
local components during startup. `GET /health/ready` reports overall readiness plus the independent
`text_search`, `image_search`, and `assistant_llm` capabilities. Call
`GET /health/ready/{capability}` to check one capability without an unrelated lazy component causing
HTTP 503; for example, an image embedding that has not been warmed does not block
`GET /health/ready/text_search`.

Image-only retrieval uses its own `IMAGE_CANDIDATE_POOL_SIZE` and does not depend on
`RERANK_TOP_K`. Client-provided `top_k` is capped by `MAX_SEARCH_TOP_K` (default `50`); the request
schema has an absolute cap of `100`, and requests above the configured runtime cap return HTTP 422.

## Embedding services

Phase 4 adds dedicated text and image embedding service interfaces. The `bedrock` provider uses `BEDROCK_EMBEDDING_MODEL_ID`, `BEDROCK_REGION`, `EMBEDDING_OUTPUT_DIMENSIONALITY`, and the AWS credential chain. Documents are embedded with `search_document`; text and image queries use `search_query`. The `gemini_api` and `vertex_ai` providers remain available as managed fallbacks, while `local` uses `TEXT_EMBEDDING_MODEL_NAME`, `IMAGE_EMBEDDING_MODEL_NAME`, `EMBEDDING_DEVICE`, and `EMBEDDING_BATCH_SIZE`.

Product document text is built with the agreed line format:

```text
Product display name: {product_display_name}
Vietnamese product display name: {product_display_name_vi}
Brand name: {brand_name}
Base colour: {base_colour}
Vietnamese base colour: {base_colour_vi}
Material: {material}
Vietnamese material: {material_vi}
Fit: {fit}
Vietnamese fit: {fit_vi}
Season: {season}
Vietnamese season: {season_vi}
Product usage: {product_usage}
Vietnamese product usage: {product_usage_vi}
Gender: {gender}
Vietnamese gender: {gender_vi}
Description: {description}
Vietnamese description: {description_vi}
Category names: {category_names}
Vietnamese category names: {category_names_vi}
Category levels: {category_levels}
Option values: {option_value}
Unified sizes: {unified_size}
Search attributes: {selected product_attributes values}
```

Deterministic `MockTextEmbeddingService` and `MockImageEmbeddingService` are included for tests that should not download models or require GPU.

## YOLO crop service

Phase 5 adds `YoloCropService` for Google Lens-style transient object crops. It lazy-loads weights from `YOLO_WEIGHTS_PATH`, runs detection on `YOLO_DEVICE`, ranks reasonable boxes by confidence, returns in-memory `CropResult` objects with `bbox`, `confidence`, and `class_id`, and falls back to the original image when no detection is usable. Crops are never persisted to disk.

## Indexing pipeline

Phase 6 adds internal Spring Boot-facing indexing endpoints. All internal routes require `X-Internal-API-Key: <INTERNAL_API_KEY>`. Product payloads follow the Spring Boot `AiProductIndexItemDto` contract and use snake_case JSON keys.

- `POST /internal/index/products/batch`
- `POST /internal/index/products/{product_id}`
- `DELETE /internal/index/products/{product_id}`
- `POST /internal/reindex`

`ProductIndexingService` builds the text document, embeds/upserts the text point, downloads each product image URL, runs YOLO crop detection, embeds returned crops or original fallback, and upserts image points. The Qdrant payload is intentionally compact and stores filter/index metadata, not full product descriptions. Update and reindex delete old vectors by `product_id` before indexing the latest payload. Delete removes matching points from both text and image collections by Qdrant payload filter.

The active local Qdrant storage contains the 1,000-product MySQL catalog. Populate and update it
through Spring's AI sync endpoints, which read the live MySQL database rather than SQL/JSON files.
The container bootstraps missing text and image collections before starting Uvicorn.

Metadata schema 4 adds normalized title fields and atomic material keys (for example, a composition
containing sheep leather produces `leather` and `sheep-leather`). Deploy it to the versioned text
collection configured by `QDRANT_TEXT_COLLECTION`; bootstrap and fully reindex before cutover. The
bootstrap remains non-destructive, so the previous collection stays available for rollback.

Text typo correction and category-filter recovery have independent rollback switches:

```dotenv
TEXT_TYPO_CORRECTION_ENABLED=true
TEXT_FILTER_RECOVERY_ENABLED=true
TEXT_FILTER_RECOVERY_MIN_CANDIDATES=5
TEXT_FILTER_RECOVERY_MIN_TOP_SCORE=0.25
TEXT_FILTER_RECOVERY_MIN_LEXICAL_COVERAGE=0.25
TEXT_FILTER_RECOVERY_TIME_BUDGET_MS=1000
```

Set either feature flag to `false` and restart `service-ai` to roll back that behavior. The payload
migration is additive and does not need to be removed when either flag is disabled.

Spring Boot is authoritative for indexed sellability. A valid `flag:active` product attribute
overrides variant-derived active state; without an override, at least one active variant is required.
A sellable variant must be active, available, and have positive inventory. Missing `active` or
`available` flags in direct indexing requests default to `false`. Business ranking only gives its
configured boost when both `available=true` and `inventory_count > 0`; stock quantity and promotion
discounts do not increase that boost.

After deploying a sellability-policy change, run a one-time full product sync so existing Qdrant
payloads receive the new `active`, `available`, and `inventory_count` values; collection recreation
is not required.

Broken image URLs are skipped and returned in `failures` with `image_failed_count`; a product can still count as indexed when text indexing succeeds and only some images fail.

## Search service

Phase 7 adds core search endpoints:

- `POST /search/text`
- `POST /search/image`
- `POST /search/image/detections`
- `POST /search/hybrid`

Text and hybrid search run deterministic parsing before optional LLM assistance.
Structured hybrid phrases keep literal category/color/material as hard constraints,
and LLM output cannot add a color or material absent from the query. Hybrid
responses expose `explicit_filters`, `inferred_filters`, `relaxed_filters`, and
per-result constraint satisfaction metadata; full product data stays in Spring Boot.

Text search keeps explicit request filters as hard Qdrant constraints and treats category, brand,
material, color, and gender inferred from free text as ranking signals. It embeds the full normalized
query, retrieves `TEXT_CANDIDATE_POOL_SIZE` vector candidates, unions exact normalized-title matches,
then applies lexical/vector fusion before optional managed reranking. Deterministic inferred price or
size constraints can be retried without those inferred constraints when the first retrieval is weak;
explicit request filters are never relaxed. The behavior is controlled by
`TEXT_INFERRED_FILTERS_SOFT_ENABLED`, `TEXT_FILTER_RECOVERY_ENABLED`, and
`TEXT_LEXICAL_FUSION_ENABLED`. Invalid free-text constraints can be rejected
before retrieval with `TEXT_OUT_OF_CATALOG_REJECTION_ENABLED`; this rejection
is exported as a bounded recovery decision metric.

Hybrid search applies the same constraint provenance model: only explicit request filters (plus
high-confidence deterministic size/price rules) are sent to Qdrant, while inferred category, brand,
material, color, and gender remain ranking signals. It unions exact matches for the original query with
semantic candidates for the rewritten query, uses `HYBRID_CANDIDATE_POOL_SIZE`, and runs text/image
retrieval concurrently. Recovery can drop inferred hard constraints but never explicit request filters.
These behaviors are independently reversible through `HYBRID_INFERRED_FILTERS_SOFT_ENABLED`,
`HYBRID_FILTER_RECOVERY_ENABLED`, `HYBRID_LEXICAL_FUSION_ENABLED`, and
`HYBRID_PARALLEL_BRANCHES_ENABLED`.

Image detection returns YOLO boxes before image search so the frontend can let the user adjust or redraw the product region. Box coordinates use original-image pixels:

```json
{
  "bbox": {"left": 12, "top": 20, "right": 180, "bottom": 240},
  "confidence": 0.91,
  "class_id": 0,
  "is_fallback": false
}
```

`POST /search/image` and `POST /search/hybrid` accept an optional `crop_box` with the same shape. When `crop_box` is present, search embeds that user-selected crop instead of running automatic YOLO crop selection.

## LLM provider services

Phase 8 centralizes remote LLM usage behind `get_llm_service()`. Bedrock is constrained to intent detection, query rewrite, filter extraction, assistant wording from retrieved candidates, match explanation, and clarification questions. It must not invent product IDs, stock status, final prices, or business decisions. Model output is parsed through Pydantic before use, with deterministic fallbacks when Bedrock is disabled or fails.

## LangGraph assistant

Phase 9 adds `POST /assistant/chat`, backed by a LangGraph workflow with persisted checkpoints. The assistant namespaces memory by `user_id:session_id`, stores recent user/assistant messages plus a bounded rolling summary, and maintains schema-validated state for active constraints, superseded values, preferences/avoidances, unresolved questions, decisions, and multiple candidate-list anchors with provenance. Query understanding and reply generation receive this context in an explicit precedence order, so corrections replace old values and follow-ups can distinguish "cái thứ 1 lúc đầu" from "cái thứ 1 vừa rồi".

Clients may send optional `request_id` and `turn_sequence` fields. Requests on the same thread are serialized; retrying the same `request_id` returns the persisted response without creating another turn, while a skipped or stale sequence returns HTTP `409 turn_sequence_conflict`. The Spring gateway forwards both fields.

Greetings, thanks, goodbyes, capability questions, and other small-talk turns use a dedicated `conversation_reply` node. They do not trigger product retrieval or Spring Boot metadata calls; the configured LLM writes a short context-aware Vietnamese response, with a safe deterministic fallback when the provider is unavailable.

Explicit statements such as "mình thích màu đen", "size của mình là L", or "ngân sách của mình dưới 800k" update a bounded long-term preference profile keyed by a hashed `user_id`. Profiles are isolated from session checkpoints, expire by TTL, and are supplied to prompts as untrusted soft preferences. One-off searches are not persisted. Users can clear the profile by asking the assistant to forget/delete their preferences.

The workflow runs query understanding, routes to text/image/hybrid search or clarification, optionally loads product context from Spring Boot, then generates the assistant reply. Product detail context is fetched through `SpringBootClient`; the assistant still only returns candidate IDs, scores, source, filters, rewritten query, warning messages when realtime metadata is degraded, and message text.

Checkpoint storage is selected through `CHECKPOINT_BACKEND`:

- `sqlite` uses `SQLITE_CHECKPOINT_PATH` for local development.
- `postgres` requires `POSTGRES_DSN`.
- `redis` requires `REDIS_URL`.

`ASSISTANT_USER_MEMORY_BACKEND=auto` follows Redis checkpoints in production and otherwise uses an adjacent local SQLite preference file. Configure retention with `ASSISTANT_USER_MEMORY_TTL_SECONDS`; set `ASSISTANT_USER_MEMORY_ENABLED=false` to disable long-term preference storage.

Preference corrections are field-level atomic replacements. Profiles carry a monotonic version,
timestamp, hashed source session/request and source turn; superseded values remain audit history
but are removed from active prompt context. Memory-only recall/summary intents bypass query analysis
and product retrieval. Named/ordinal result anchors survive transcript compaction; unresolved anchors
return a clarification instead of selecting a nearby product.

`ASSISTANT_EVAL_TRACE_ENABLED=true` exposes a redacted `evaluation_trace` for offline evaluation
only; keep it `false` in production. Product metadata is batch-loaded and cached per Qdrant text
collection using `ASSISTANT_PRODUCT_CONTEXT_CACHE_TTL_SECONDS` and
`ASSISTANT_PRODUCT_CONTEXT_CACHE_SIZE`.

`GET /metrics` exposes content-free assistant memory gauges/counters and bounded source labels. Prometheus rules alert on repeated summary hard limits, checkpoint failures, failed recall probes, and abnormal latency growth across later turns.

Assistant metrics also expose route counts, LLM/Spring call counts, product-context cache hits and
misses, fallback reasons, and per-stage latency count/sum/max. Evaluation traces record the same
stage split for p50/p95 reporting without exposing conversation text.

Spring Boot persists thumbs-up/down feedback against `chat_message_id`. The frontend sends feedback through `POST /api/assistant/feedback`; authenticated account IDs are derived from the security principal and anonymous browsers receive isolated persistent IDs.

## Spring Boot integration client

Phase 10 expands `SpringBootClient` into the realtime metadata bridge:

- `get_products_by_ids(product_ids)`
- `search_products_by_filter(filters)`

The client reads base URL, API key, endpoint paths, timeout, retry count, and retry backoff from env. It retries transient network/HTTP failures, treats Spring Boot as the source of truth for price, stock, promotion, and display metadata, and returns the warning code `spring_boot_unavailable` instead of breaking the assistant response when metadata cannot be loaded.

`get_products_by_ids` sends one authenticated batch request to `POST /api/internal/ai/products/context`. Spring Boot loads the requested products in the same order and hydrates their realtime metadata in batches; `SPRINGBOOT_API_KEY` must match Spring Boot's `AI_SERVICE_INTERNAL_API_KEY`.
