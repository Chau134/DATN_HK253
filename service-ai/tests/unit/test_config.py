import pytest

from ecommerce_search_assistant.core.config import Settings, get_settings


def test_settings_load_env_values(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "phase-11-test-app")
    monkeypatch.setenv("CORS_ORIGINS", "http://one.test,http://two.test")
    monkeypatch.setenv("SPRINGBOOT_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("SPRINGBOOT_RETRY_ATTEMPTS", "3")
    monkeypatch.setenv("SPRINGBOOT_RETRY_BACKOFF_SECONDS", "0.5")
    monkeypatch.setenv("NORMALIZE_EMBEDDINGS", "false")
    monkeypatch.setenv("IMAGE_YOLO_CATEGORY_HARD_FILTER_CLASS_IDS", "1,3")
    get_settings.cache_clear()

    settings = Settings(_env_file=None)

    assert settings.app_name == "phase-11-test-app"
    assert settings.cors_origins == ["http://one.test", "http://two.test"]
    assert settings.springboot_timeout_seconds == 12.5
    assert settings.springboot_retry_attempts == 3
    assert settings.springboot_retry_backoff_seconds == 0.5
    assert settings.springboot_product_context_endpoint == "/api/internal/ai/products/context"
    assert settings.assistant_user_memory_enabled is True
    assert settings.assistant_user_memory_backend == "auto"
    assert settings.assistant_user_memory_ttl_seconds == 15552000
    assert settings.reranker_model_name == "semantic-ranker-default@latest"
    assert settings.reranker_location == "global"
    assert settings.reranker_config_id == "default_ranking_config"
    assert settings.yolo_enabled is False
    assert settings.normalize_embeddings is False
    assert settings.image_yolo_category_hard_filter_class_ids == [1, 3]
    assert settings.text_catalog_metadata_cache_ttl_seconds == 1800
    get_settings.cache_clear()


def test_default_search_limits_must_not_exceed_runtime_cap() -> None:
    with pytest.raises(ValueError, match="must not exceed MAX_SEARCH_TOP_K"):
        Settings(_env_file=None, TEXT_TOP_K=51, MAX_SEARCH_TOP_K=50)


def test_embedding_defaults_use_bedrock_cohere_v4_with_matching_dimensions() -> None:
    settings = Settings(_env_file=None)

    assert settings.embedding_provider == "bedrock"
    assert settings.bedrock_embedding_model_id == "cohere.embed-v4:0"
    assert settings.embedding_output_dimensionality == 1536
    assert settings.qdrant_text_vector_size == 1536
    assert settings.qdrant_image_vector_size == 1536
    assert settings.qdrant_text_collection.endswith("_100_products")
    assert settings.qdrant_image_collection.endswith("_100_products")


def test_managed_embedding_rejects_qdrant_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="QDRANT_TEXT_VECTOR_SIZE must match"):
        Settings(
            _env_file=None,
            EMBEDDING_PROVIDER="bedrock",
            EMBEDDING_OUTPUT_DIMENSIONALITY=1536,
            QDRANT_TEXT_VECTOR_SIZE=768,
            QDRANT_IMAGE_VECTOR_SIZE=1536,
        )


def test_managed_reranker_requires_google_cloud_project() -> None:
    with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT is required"):
        Settings(_env_file=None, RERANK_ENABLED=True, GOOGLE_CLOUD_PROJECT=None)
