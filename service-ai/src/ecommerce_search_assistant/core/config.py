from functools import lru_cache
from typing import Annotated, Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_csv(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _parse_int_csv(value: Any) -> list[int]:
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        return []
    return [int(item) for item in items]


def _empty_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        validate_default=True,
    )

    app_name: str = Field(default="ai-ecommerce-assistant", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, ge=1, le=65535, alias="APP_PORT")
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"],
        alias="CORS_ORIGINS",
    )

    internal_api_key: str = Field(default="change-me", alias="INTERNAL_API_KEY")
    springboot_api_key: str = Field(default="change-me", alias="SPRINGBOOT_API_KEY")

    springboot_base_url: str = Field(default="http://localhost:8080", alias="SPRINGBOOT_BASE_URL")
    springboot_product_search_endpoint: str = Field(
        default="/api/products/search",
        alias="SPRINGBOOT_PRODUCT_SEARCH_ENDPOINT",
    )
    springboot_product_detail_endpoint: str = Field(
        default="/api/products",
        alias="SPRINGBOOT_PRODUCT_DETAIL_ENDPOINT",
    )
    springboot_product_context_endpoint: str = Field(
        default="/api/internal/ai/products/context",
        alias="SPRINGBOOT_PRODUCT_CONTEXT_ENDPOINT",
    )
    springboot_timeout_seconds: float = Field(default=10, gt=0, alias="SPRINGBOOT_TIMEOUT_SECONDS")
    springboot_retry_attempts: int = Field(default=2, ge=0, le=10, alias="SPRINGBOOT_RETRY_ATTEMPTS")
    springboot_retry_backoff_seconds: float = Field(
        default=0.25,
        ge=0,
        le=60,
        alias="SPRINGBOOT_RETRY_BACKOFF_SECONDS",
    )
    assistant_product_context_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=30,
        alias="ASSISTANT_PRODUCT_CONTEXT_TIMEOUT_SECONDS",
    )
    assistant_product_context_retry_attempts: int = Field(
        default=1,
        ge=0,
        le=2,
        alias="ASSISTANT_PRODUCT_CONTEXT_RETRY_ATTEMPTS",
    )
    assistant_product_context_circuit_failure_threshold: int = Field(
        default=2,
        ge=1,
        le=20,
        alias="ASSISTANT_PRODUCT_CONTEXT_CIRCUIT_FAILURE_THRESHOLD",
    )
    assistant_product_context_circuit_reset_seconds: float = Field(
        default=30.0,
        ge=1,
        le=600,
        alias="ASSISTANT_PRODUCT_CONTEXT_CIRCUIT_RESET_SECONDS",
    )
    assistant_product_context_limit: int = Field(default=5, gt=0, alias="ASSISTANT_PRODUCT_CONTEXT_LIMIT")
    assistant_recommendation_limit: int = Field(
        default=3,
        gt=0,
        le=10,
        alias="ASSISTANT_RECOMMENDATION_LIMIT",
    )

    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_text_collection: str = Field(
        default="product_text_vectors_cohere_embed_v4_1536_metadata_v4_100_products",
        alias="QDRANT_TEXT_COLLECTION",
    )
    qdrant_image_collection: str = Field(
        default="product_image_vectors_cohere_embed_v4_1536_100_products",
        alias="QDRANT_IMAGE_COLLECTION",
    )
    qdrant_text_vector_size: int = Field(default=1536, gt=0, alias="QDRANT_TEXT_VECTOR_SIZE")
    qdrant_image_vector_size: int = Field(default=1536, gt=0, alias="QDRANT_IMAGE_VECTOR_SIZE")
    qdrant_distance: Literal["COSINE", "DOT", "EUCLID", "MANHATTAN"] = Field(
        default="COSINE",
        alias="QDRANT_DISTANCE",
    )
    product_index_workers: int = Field(
        default=1,
        ge=1,
        le=32,
        alias="PRODUCT_INDEX_WORKERS",
    )
    product_image_download_workers: int = Field(
        default=8,
        ge=1,
        le=32,
        alias="PRODUCT_IMAGE_DOWNLOAD_WORKERS",
    )

    llm_provider: Literal["fallback", "bedrock"] = Field(default="fallback", alias="LLM_PROVIDER")

    # GPT OSS 120B is invoked in-region from the Tokyo Bedrock runtime endpoint.
    bedrock_region: str = Field(default="ap-northeast-1", alias="BEDROCK_REGION")
    bedrock_model_id: str | None = Field(
        default="openai.gpt-oss-120b-1:0",
        alias="BEDROCK_MODEL_ID",
    )
    bedrock_temperature: float = Field(default=0.2, ge=0, le=2, alias="BEDROCK_TEMPERATURE")
    bedrock_top_p: float | None = Field(default=None, ge=0, le=1, alias="BEDROCK_TOP_P")
    bedrock_max_tokens: int = Field(default=2048, gt=0, alias="BEDROCK_MAX_TOKENS")
    bedrock_query_understanding_max_tokens: int = Field(
        default=1536,
        ge=128,
        le=2048,
        alias="BEDROCK_QUERY_UNDERSTANDING_MAX_TOKENS",
    )
    bedrock_timeout_seconds: float = Field(default=30, gt=0, alias="BEDROCK_TIMEOUT_SECONDS")
    bedrock_retry_attempts: int = Field(default=2, ge=0, le=10, alias="BEDROCK_RETRY_ATTEMPTS")
    bedrock_endpoint_url: str | None = Field(default=None, alias="BEDROCK_ENDPOINT_URL")

    yolo_enabled: bool = Field(default=False, alias="YOLO_ENABLED")
    yolo_weights_path: str = Field(default="./weights/yolo.pt", alias="YOLO_WEIGHTS_PATH")
    yolo_device: str = Field(default="cpu", alias="YOLO_DEVICE")
    yolo_conf_threshold: float = Field(default=0.35, ge=0, le=1, alias="YOLO_CONF_THRESHOLD")
    yolo_iou_threshold: float = Field(default=0.5, ge=0, le=1, alias="YOLO_IOU_THRESHOLD")
    yolo_input_size: int = Field(default=640, gt=0, alias="YOLO_INPUT_SIZE")
    yolo_min_crop_side_px: int = Field(default=24, ge=1, alias="YOLO_MIN_CROP_SIDE_PX")

    embedding_provider: Literal["local", "bedrock", "cohere", "gemini_api", "vertex_ai"] = Field(
        default="bedrock",
        alias="EMBEDDING_PROVIDER",
    )
    cohere_api_key: SecretStr | None = Field(default=None, alias="COHERE_API_KEY")
    cohere_embedding_model_name: str = Field(
        default="embed-v4.0",
        min_length=1,
        alias="COHERE_EMBEDDING_MODEL_NAME",
    )
    bedrock_embedding_model_id: str = Field(
        default="cohere.embed-v4:0",
        min_length=1,
        alias="BEDROCK_EMBEDDING_MODEL_ID",
    )
    bedrock_embedding_image_max_side: int = Field(
        default=512,
        ge=64,
        le=2458,
        alias="BEDROCK_EMBEDDING_IMAGE_MAX_SIDE",
    )
    bedrock_embedding_min_request_interval_seconds: float = Field(
        default=1.0,
        ge=0,
        le=60,
        alias="BEDROCK_EMBEDDING_MIN_REQUEST_INTERVAL_SECONDS",
    )
    bedrock_embedding_throttle_retry_attempts: int = Field(
        default=6,
        ge=0,
        le=12,
        alias="BEDROCK_EMBEDDING_THROTTLE_RETRY_ATTEMPTS",
    )
    bedrock_embedding_throttle_backoff_seconds: float = Field(
        default=2.0,
        ge=0,
        le=60,
        alias="BEDROCK_EMBEDDING_THROTTLE_BACKOFF_SECONDS",
    )
    bedrock_embedding_throttle_max_backoff_seconds: float = Field(
        default=30.0,
        ge=0,
        le=300,
        alias="BEDROCK_EMBEDDING_THROTTLE_MAX_BACKOFF_SECONDS",
    )
    vertex_embedding_model_name: str = Field(
        default="gemini-embedding-2",
        alias="VERTEX_EMBEDDING_MODEL_NAME",
    )
    embedding_output_dimensionality: int = Field(
        default=1536,
        ge=128,
        le=3072,
        alias="EMBEDDING_OUTPUT_DIMENSIONALITY",
    )
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="global", alias="GOOGLE_CLOUD_LOCATION")
    google_genai_api_version: str = Field(default="v1beta", alias="GOOGLE_GENAI_API_VERSION")
    google_cloud_api_key: SecretStr | None = Field(default=None, alias="GOOGLE_CLOUD_API_KEY")
    google_cloud_api_key_file: str | None = Field(
        default=None,
        alias="GOOGLE_CLOUD_API_KEY_FILE",
    )
    google_cloud_reranker_access_token_file: str | None = Field(
        default=None,
        alias="GOOGLE_CLOUD_RERANKER_ACCESS_TOKEN_FILE",
    )

    # Local models remain available as an explicit development fallback. Production
    # selects a managed provider and never imports or loads these weights.
    text_embedding_model_name: str = Field(default="Qwen/Qwen3-Embedding-8B", alias="TEXT_EMBEDDING_MODEL_NAME")
    image_embedding_model_name: str = Field(
        default="Qwen/Qwen3-VL-Embedding-2B",
        alias="IMAGE_EMBEDDING_MODEL_NAME",
    )
    image_embedding_trust_remote_code: bool = Field(default=True, alias="IMAGE_EMBEDDING_TRUST_REMOTE_CODE")
    embedding_device: Literal["cpu", "cuda"] = Field(default="cuda", alias="EMBEDDING_DEVICE")
    embedding_dtype: Literal["float16", "float32", "bfloat16"] = Field(
        default="float16",
        alias="EMBEDDING_DTYPE",
    )
    embedding_batch_size: int = Field(default=16, gt=0, alias="EMBEDDING_BATCH_SIZE")
    normalize_embeddings: bool = Field(default=True, alias="NORMALIZE_EMBEDDINGS")

    # Qwen3-Embedding requires an instruction prefix on queries (documents get none).
    text_embedding_use_prompt: bool = Field(default=True, alias="TEXT_EMBEDDING_USE_PROMPT")
    text_embedding_query_instruction: str = Field(
        default="Given a shopping search query, retrieve relevant product descriptions",
        alias="TEXT_EMBEDDING_QUERY_INSTRUCTION",
    )
    text_embedding_query_prompt: str = Field(
        default="Instruct: {task}\nQuery: {text}",
        alias="TEXT_EMBEDDING_QUERY_PROMPT",
    )

    temp_upload_dir: str = Field(default="./tmp/uploads", alias="TEMP_UPLOAD_DIR")
    max_upload_mb: int = Field(default=10, gt=0, alias="MAX_UPLOAD_MB")
    allowed_image_mime_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"],
        alias="ALLOWED_IMAGE_MIME_TYPES",
    )
    image_min_width: int = Field(default=1, gt=0, alias="IMAGE_MIN_WIDTH")
    image_min_height: int = Field(default=1, gt=0, alias="IMAGE_MIN_HEIGHT")
    image_max_side: int = Field(default=1600, gt=0, alias="IMAGE_MAX_SIDE")

    text_top_k: int = Field(default=5, gt=0, alias="TEXT_TOP_K")
    text_candidate_pool_size: int = Field(default=50, gt=0, le=100, alias="TEXT_CANDIDATE_POOL_SIZE")
    text_inferred_filters_soft_enabled: bool = Field(
        default=True,
        alias="TEXT_INFERRED_FILTERS_SOFT_ENABLED",
    )
    text_trusted_color_hard_filter_enabled: bool = Field(
        default=False,
        alias="TEXT_TRUSTED_COLOR_HARD_FILTER_ENABLED",
    )
    text_typo_correction_enabled: bool = Field(
        default=True,
        alias="TEXT_TYPO_CORRECTION_ENABLED",
    )
    text_filter_recovery_enabled: bool = Field(default=True, alias="TEXT_FILTER_RECOVERY_ENABLED")
    text_filter_recovery_min_candidates: int = Field(
        default=5,
        ge=1,
        le=100,
        alias="TEXT_FILTER_RECOVERY_MIN_CANDIDATES",
    )
    text_filter_recovery_min_top_score: float = Field(
        default=0.25,
        ge=-1,
        le=1,
        alias="TEXT_FILTER_RECOVERY_MIN_TOP_SCORE",
    )
    text_filter_recovery_min_lexical_coverage: float = Field(
        default=0.25,
        ge=0,
        le=1,
        alias="TEXT_FILTER_RECOVERY_MIN_LEXICAL_COVERAGE",
    )
    text_filter_recovery_time_budget_ms: int = Field(
        default=1000,
        ge=0,
        le=10000,
        alias="TEXT_FILTER_RECOVERY_TIME_BUDGET_MS",
    )
    text_lexical_fusion_enabled: bool = Field(default=True, alias="TEXT_LEXICAL_FUSION_ENABLED")
    text_out_of_catalog_rejection_enabled: bool = Field(
        default=True,
        alias="TEXT_OUT_OF_CATALOG_REJECTION_ENABLED",
    )
    image_top_k: int = Field(default=5, gt=0, alias="IMAGE_TOP_K")
    max_search_top_k: int = Field(default=50, gt=0, le=100, alias="MAX_SEARCH_TOP_K")
    image_candidate_pool_size: int = Field(default=20, gt=0, alias="IMAGE_CANDIDATE_POOL_SIZE")
    image_product_overfetch_factor: int = Field(default=4, ge=1, le=20, alias="IMAGE_PRODUCT_OVERFETCH_FACTOR")
    image_query_per_crop_limit_cap: int = Field(default=200, gt=0, le=1000, alias="IMAGE_QUERY_PER_CROP_LIMIT_CAP")
    image_yolo_category_soft_boost_weight: float = Field(
        default=0.03,
        ge=0,
        le=1,
        alias="IMAGE_YOLO_CATEGORY_SOFT_BOOST_WEIGHT",
    )
    image_yolo_category_soft_min_confidence: float = Field(
        default=0.35,
        ge=0,
        le=1,
        alias="IMAGE_YOLO_CATEGORY_SOFT_MIN_CONFIDENCE",
    )
    image_yolo_category_hard_filter_confidence: float = Field(
        default=0.90,
        ge=0,
        le=1,
        alias="IMAGE_YOLO_CATEGORY_HARD_FILTER_CONFIDENCE",
    )
    image_yolo_category_hard_filter_class_ids: Annotated[list[int], NoDecode] = Field(
        default_factory=list,
        alias="IMAGE_YOLO_CATEGORY_HARD_FILTER_CLASS_IDS",
    )
    image_business_boost_enabled: bool = Field(default=False, alias="IMAGE_BUSINESS_BOOST_ENABLED")
    image_business_boost_weight: float = Field(default=0.02, ge=0, le=1, alias="IMAGE_BUSINESS_BOOST_WEIGHT")
    hybrid_top_k: int = Field(default=5, gt=0, alias="HYBRID_TOP_K")
    hybrid_candidate_pool_size: int = Field(
        default=50,
        gt=0,
        le=100,
        alias="HYBRID_CANDIDATE_POOL_SIZE",
    )
    hybrid_product_overfetch_factor: int = Field(
        default=4,
        ge=1,
        le=10,
        alias="HYBRID_PRODUCT_OVERFETCH_FACTOR",
    )
    hybrid_candidate_pool_cap: int = Field(
        default=100,
        gt=0,
        le=500,
        alias="HYBRID_CANDIDATE_POOL_CAP",
    )
    hybrid_inferred_filters_soft_enabled: bool = Field(
        default=True,
        alias="HYBRID_INFERRED_FILTERS_SOFT_ENABLED",
    )
    hybrid_filter_recovery_enabled: bool = Field(
        default=True,
        alias="HYBRID_FILTER_RECOVERY_ENABLED",
    )
    hybrid_lexical_fusion_enabled: bool = Field(
        default=True,
        alias="HYBRID_LEXICAL_FUSION_ENABLED",
    )
    hybrid_parallel_branches_enabled: bool = Field(
        default=True,
        alias="HYBRID_PARALLEL_BRANCHES_ENABLED",
    )
    rerank_top_k: int = Field(default=20, gt=0, le=100, alias="RERANK_TOP_K")
    hybrid_search_policy: Literal["legacy", "image_conditioned"] = Field(default="legacy", alias="HYBRID_SEARCH_POLICY")
    hybrid_conditioned_recovery_enabled: bool = Field(default=True, alias="HYBRID_CONDITIONED_RECOVERY_ENABLED")
    hybrid_conditioned_ranking: Literal["image", "rrf"] = Field(default="image", alias="HYBRID_CONDITIONED_RANKING")
    hybrid_conditioned_grouped_retrieval_enabled: bool = Field(default=False, alias="HYBRID_CONDITIONED_GROUPED_RETRIEVAL_ENABLED")
    hybrid_conditioned_budget_ms: int = Field(default=4500, gt=0, alias="HYBRID_CONDITIONED_BUDGET_MS")
    hybrid_conditioned_min_visual_score: float = Field(default=0.0, ge=-1, le=1, alias="HYBRID_CONDITIONED_MIN_VISUAL_SCORE")
    hybrid_conditioned_preference_weight: float = Field(default=0.02, ge=0, le=0.1, alias="HYBRID_CONDITIONED_PREFERENCE_WEIGHT")
    hybrid_conditioned_dominant_color_ranking_enabled: bool = Field(
        default=True,
        alias="HYBRID_CONDITIONED_DOMINANT_COLOR_RANKING_ENABLED",
    )
    hybrid_conditioned_diagnostics_enabled: bool = Field(default=False, alias="HYBRID_CONDITIONED_DIAGNOSTICS_ENABLED")
    hybrid_image_weight: float = Field(default=0.45, ge=0, le=1, alias="HYBRID_IMAGE_WEIGHT")
    hybrid_text_weight: float = Field(default=0.35, ge=0, le=1, alias="HYBRID_TEXT_WEIGHT")
    hybrid_filter_weight: float = Field(default=0.15, ge=0, le=1, alias="HYBRID_FILTER_WEIGHT")
    hybrid_business_weight: float = Field(default=0.05, ge=0, le=1, alias="HYBRID_BUSINESS_WEIGHT")
    hybrid_soft_attribute_boost_enabled: bool = Field(
        default=False,
        alias="HYBRID_SOFT_ATTRIBUTE_BOOST_ENABLED",
    )
    hybrid_color_boost_weight: float = Field(default=0.05, ge=0, le=1, alias="HYBRID_COLOR_BOOST_WEIGHT")
    hybrid_gender_boost_weight: float = Field(default=0.03, ge=0, le=1, alias="HYBRID_GENDER_BOOST_WEIGHT")
    hybrid_use_case_boost_weight: float = Field(
        default=0.12,
        ge=0,
        le=1,
        alias="HYBRID_USE_CASE_BOOST_WEIGHT",
    )
    hybrid_use_case_overlap_boost_enabled: bool = Field(
        default=True,
        alias="HYBRID_USE_CASE_OVERLAP_BOOST_ENABLED",
    )
    hybrid_query_parse_cache_size: int = Field(
        default=512,
        ge=0,
        le=10000,
        alias="HYBRID_QUERY_PARSE_CACHE_SIZE",
    )
    hybrid_image_embedding_cache_size: int = Field(
        default=256,
        ge=0,
        le=5000,
        alias="HYBRID_IMAGE_EMBEDDING_CACHE_SIZE",
    )
    hybrid_image_embedding_cache_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        le=86400,
        alias="HYBRID_IMAGE_EMBEDDING_CACHE_TTL_SECONDS",
    )

    # Text search soft ranking. Opt-in boosts applied AFTER the Qdrant vector search on the text
    # flow only. Independent of the hybrid weighted sum, so they are NOT checked by
    # validate_search_weights. When both flags are off, the text score equals the raw vector score.
    text_soft_attribute_boost_enabled: bool = Field(
        default=False, alias="TEXT_SOFT_ATTRIBUTE_BOOST_ENABLED"
    )
    text_business_boost_enabled: bool = Field(default=False, alias="TEXT_BUSINESS_BOOST_ENABLED")
    text_color_boost_weight: float = Field(default=0.05, ge=0, le=1, alias="TEXT_COLOR_BOOST_WEIGHT")
    text_gender_boost_weight: float = Field(default=0.03, ge=0, le=1, alias="TEXT_GENDER_BOOST_WEIGHT")
    text_business_boost_weight: float = Field(
        default=0.02, ge=0, le=1, alias="TEXT_BUSINESS_BOOST_WEIGHT"
    )
    text_exact_title_boost_weight: float = Field(
        default=1.0, ge=0, le=5, alias="TEXT_EXACT_TITLE_BOOST_WEIGHT"
    )
    text_phrase_boost_weight: float = Field(
        default=0.30, ge=0, le=2, alias="TEXT_PHRASE_BOOST_WEIGHT"
    )
    text_token_coverage_boost_weight: float = Field(
        default=0.20, ge=0, le=2, alias="TEXT_TOKEN_COVERAGE_BOOST_WEIGHT"
    )
    text_prefix_boost_weight: float = Field(
        default=0.10, ge=0, le=2, alias="TEXT_PREFIX_BOOST_WEIGHT"
    )
    text_inferred_filter_boost_weight: float = Field(
        default=0.05, ge=0, le=1, alias="TEXT_INFERRED_FILTER_BOOST_WEIGHT"
    )
    text_use_case_boost_weight: float = Field(
        default=0.10,
        ge=0,
        le=1,
        alias='TEXT_USE_CASE_BOOST_WEIGHT',
    )
    text_llm_fast_path_enabled: bool = Field(
        default=True,
        alias="TEXT_LLM_FAST_PATH_ENABLED",
    )
    text_llm_fast_path_min_tokens: int = Field(
        default=3,
        ge=1,
        le=20,
        alias="TEXT_LLM_FAST_PATH_MIN_TOKENS",
    )
    text_llm_analysis_cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        le=86400,
        alias="TEXT_LLM_ANALYSIS_CACHE_TTL_SECONDS",
    )
    text_llm_analysis_cache_size: int = Field(
        default=512,
        ge=0,
        le=100000,
        alias="TEXT_LLM_ANALYSIS_CACHE_SIZE",
    )
    text_query_embedding_cache_ttl_seconds: int = Field(
        default=600,
        ge=0,
        le=86400,
        alias="TEXT_QUERY_EMBEDDING_CACHE_TTL_SECONDS",
    )
    text_query_embedding_cache_size: int = Field(
        default=1000,
        ge=0,
        le=100000,
        alias="TEXT_QUERY_EMBEDDING_CACHE_SIZE",
    )
    text_catalog_metadata_cache_ttl_seconds: int = Field(
        default=1800,
        ge=60,
        le=86400,
        alias="TEXT_CATALOG_METADATA_CACHE_TTL_SECONDS",
    )
    text_specific_token_boost_weight: float = Field(
        default=0.20,
        ge=0,
        le=2,
        alias="TEXT_SPECIFIC_TOKEN_BOOST_WEIGHT",
    )
    text_fuzzy_token_boost_weight: float = Field(
        default=0.12,
        ge=0,
        le=1,
        alias="TEXT_FUZZY_TOKEN_BOOST_WEIGHT",
    )
    # After the color family is matched, an exact-shade product ("Hồng" for a
    # "màu hồng" query) is ranked above a family variant ("Hồng pastel"). This is
    # a ranking-only boost, never a hard filter, so variants still appear.
    text_exact_shade_boost_weight: float = Field(
        default=0.15,
        ge=0,
        le=1,
        alias="TEXT_EXACT_SHADE_BOOST_WEIGHT",
    )
    text_fuzzy_token_min_similarity: float = Field(
        default=0.82,
        ge=0.7,
        le=1,
        alias="TEXT_FUZZY_TOKEN_MIN_SIMILARITY",
    )

    # Managed Agent Search Ranking API. Reorders the top rerank_top_k text/hybrid
    # candidates and does not participate in the hybrid weighted sum.
    rerank_enabled: bool = Field(default=False, alias="RERANK_ENABLED")
    reranker_model_name: str = Field(
        default="semantic-ranker-default@latest",
        min_length=1,
        alias="RERANKER_MODEL_NAME",
    )
    reranker_location: str = Field(default="global", min_length=1, alias="RERANKER_LOCATION")
    reranker_config_id: str = Field(
        default="default_ranking_config",
        min_length=1,
        alias="RERANKER_CONFIG_ID",
    )
    reranker_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=120,
        alias="RERANKER_TIMEOUT_SECONDS",
    )

    preload_models: bool = Field(default=False, alias="PRELOAD_MODELS")

    checkpoint_backend: Literal["sqlite", "postgres", "redis"] = Field(
        default="sqlite",
        alias="CHECKPOINT_BACKEND",
    )
    sqlite_checkpoint_path: str = Field(
        default="./data/langgraph_checkpoints.sqlite",
        alias="SQLITE_CHECKPOINT_PATH",
    )
    postgres_dsn: str | None = Field(default=None, alias="POSTGRES_DSN")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    assistant_recent_message_limit: int = Field(
        default=12,
        ge=2,
        le=50,
        alias="ASSISTANT_RECENT_MESSAGE_LIMIT",
    )
    assistant_conversation_summary_max_chars: int = Field(
        default=3000,
        ge=500,
        le=20000,
        alias="ASSISTANT_CONVERSATION_SUMMARY_MAX_CHARS",
    )
    assistant_conversation_context_max_chars: int = Field(
        default=8000,
        ge=1000,
        le=50000,
        alias="ASSISTANT_CONVERSATION_CONTEXT_MAX_CHARS",
    )
    assistant_query_context_max_chars: int = Field(
        default=4000,
        ge=1000,
        le=50000,
        alias="ASSISTANT_QUERY_CONTEXT_MAX_CHARS",
    )
    assistant_user_memory_enabled: bool = Field(default=True, alias="ASSISTANT_USER_MEMORY_ENABLED")
    assistant_user_memory_backend: Literal["auto", "disabled", "sqlite", "redis"] = Field(
        default="auto",
        alias="ASSISTANT_USER_MEMORY_BACKEND",
    )
    assistant_user_memory_ttl_seconds: int = Field(
        default=15552000,
        ge=3600,
        le=63072000,
        alias="ASSISTANT_USER_MEMORY_TTL_SECONDS",
    )
    assistant_user_memory_max_notes: int = Field(
        default=5,
        ge=1,
        le=20,
        alias="ASSISTANT_USER_MEMORY_MAX_NOTES",
    )
    assistant_eval_trace_enabled: bool = Field(
        default=False,
        alias="ASSISTANT_EVAL_TRACE_ENABLED",
    )
    assistant_evaluation_variant: Literal["rag", "llm_no_rag"] = Field(
        default="rag",
        alias="ASSISTANT_EVALUATION_VARIANT",
    )
    assistant_product_context_cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        le=86400,
        alias="ASSISTANT_PRODUCT_CONTEXT_CACHE_TTL_SECONDS",
    )
    assistant_product_context_cache_size: int = Field(
        default=2000,
        ge=0,
        le=100000,
        alias="ASSISTANT_PRODUCT_CONTEXT_CACHE_SIZE",
    )
    assistant_product_context_stale_ttl_seconds: int = Field(
        default=1800,
        ge=0,
        le=86400,
        alias="ASSISTANT_PRODUCT_CONTEXT_STALE_TTL_SECONDS",
    )

    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    otel_exporter_otlp_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    @field_validator("cors_origins", "allowed_image_mime_types", mode="before")
    @classmethod
    def parse_csv_values(cls, value: Any) -> list[str]:
        return _parse_csv(value)

    @field_validator("image_yolo_category_hard_filter_class_ids", mode="before")
    @classmethod
    def parse_int_csv_values(cls, value: Any) -> list[int]:
        return _parse_int_csv(value)

    @field_validator(
        "qdrant_api_key",
        "bedrock_model_id",
        "bedrock_top_p",
        "bedrock_endpoint_url",
        "google_cloud_project",
        "postgres_dsn",
        "redis_url",
        "sentry_dsn",
        "otel_exporter_otlp_endpoint",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: Any) -> str:
        return str(value).upper()

    @field_validator("qdrant_distance", mode="before")
    @classmethod
    def normalize_qdrant_distance(cls, value: Any) -> str:
        return str(value).upper()

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: Any) -> str:
        return str(value).lower()

    @field_validator("checkpoint_backend", mode="before")
    @classmethod
    def normalize_checkpoint_backend(cls, value: Any) -> str:
        return str(value).lower()

    @field_validator("assistant_user_memory_backend", mode="before")
    @classmethod
    def normalize_user_memory_backend(cls, value: Any) -> str:
        return str(value).lower()

    @field_validator("embedding_provider", mode="before")
    @classmethod
    def normalize_embedding_provider(cls, value: Any) -> str:
        return str(value).lower()

    @field_validator("embedding_device", "embedding_dtype", mode="before")
    @classmethod
    def normalize_embedding_device(cls, value: Any) -> str:
        return str(value).lower()

    @model_validator(mode="after")
    def validate_search_weights(self) -> Self:
        total_weight = (
            self.hybrid_image_weight
            + self.hybrid_text_weight
            + self.hybrid_filter_weight
            + self.hybrid_business_weight
        )
        if abs(total_weight - 1.0) > 0.000001:
            raise ValueError("hybrid search weights must sum to 1.0")
        default_limits = (self.text_top_k, self.image_top_k, self.hybrid_top_k)
        if any(limit > self.max_search_top_k for limit in default_limits):
            raise ValueError("TEXT_TOP_K, IMAGE_TOP_K and HYBRID_TOP_K must not exceed MAX_SEARCH_TOP_K")
        if self.text_candidate_pool_size > self.max_search_top_k:
            raise ValueError("TEXT_CANDIDATE_POOL_SIZE must not exceed MAX_SEARCH_TOP_K")
        if self.hybrid_candidate_pool_size > self.max_search_top_k:
            raise ValueError("HYBRID_CANDIDATE_POOL_SIZE must not exceed MAX_SEARCH_TOP_K")
        if (
            self.image_yolo_category_hard_filter_confidence
            < self.image_yolo_category_soft_min_confidence
        ):
            raise ValueError(
                "IMAGE_YOLO_CATEGORY_HARD_FILTER_CONFIDENCE must be greater than or equal to "
                "IMAGE_YOLO_CATEGORY_SOFT_MIN_CONFIDENCE"
            )
        if self.embedding_provider in {"bedrock", "cohere", "gemini_api", "vertex_ai"}:
            if self.qdrant_text_vector_size != self.embedding_output_dimensionality:
                raise ValueError(
                    "QDRANT_TEXT_VECTOR_SIZE must match EMBEDDING_OUTPUT_DIMENSIONALITY "
                    "when a managed embedding provider is enabled"
                )
            if self.qdrant_image_vector_size != self.embedding_output_dimensionality:
                raise ValueError(
                    "QDRANT_IMAGE_VECTOR_SIZE must match EMBEDDING_OUTPUT_DIMENSIONALITY "
                    "when a managed embedding provider is enabled"
                )
        if self.rerank_enabled and not (self.google_cloud_project or "").strip():
            raise ValueError("GOOGLE_CLOUD_PROJECT is required when RERANK_ENABLED=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
