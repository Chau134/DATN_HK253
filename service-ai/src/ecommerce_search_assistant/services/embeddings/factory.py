from functools import lru_cache

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.services.embeddings.bedrock import (
    BedrockCohereImageEmbeddingService,
    BedrockCohereTextEmbeddingService,
)
from ecommerce_search_assistant.services.embeddings.cohere import (
    CohereImageEmbeddingService,
    CohereTextEmbeddingService,
)
from ecommerce_search_assistant.services.embeddings.image import TransformersImageEmbeddingService
from ecommerce_search_assistant.services.embeddings.interfaces import ImageEmbeddingService, TextEmbeddingService
from ecommerce_search_assistant.services.embeddings.text import SentenceTransformerTextEmbeddingService
from ecommerce_search_assistant.services.embeddings.vertex import (
    VertexGeminiImageEmbeddingService,
    VertexGeminiTextEmbeddingService,
)


@lru_cache
def get_text_embedding_service() -> TextEmbeddingService:
    settings = get_settings()
    if settings.embedding_provider == "bedrock":
        return BedrockCohereTextEmbeddingService(settings=settings)
    if settings.embedding_provider == "cohere":
        return CohereTextEmbeddingService(settings=settings)
    if settings.embedding_provider in {"gemini_api", "vertex_ai"}:
        return VertexGeminiTextEmbeddingService(settings=settings)
    return SentenceTransformerTextEmbeddingService(settings=settings)


@lru_cache
def get_image_embedding_service() -> ImageEmbeddingService:
    settings = get_settings()
    if settings.embedding_provider == "bedrock":
        return BedrockCohereImageEmbeddingService(settings=settings)
    if settings.embedding_provider == "cohere":
        return CohereImageEmbeddingService(settings=settings)
    if settings.embedding_provider in {"gemini_api", "vertex_ai"}:
        return VertexGeminiImageEmbeddingService(settings=settings)
    return TransformersImageEmbeddingService(settings=settings)
