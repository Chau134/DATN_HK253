from typing import Literal

from pydantic import Field, model_validator

from ecommerce_search_assistant.schemas.base import SchemaModel
from ecommerce_search_assistant.schemas.media import ImagePayload
from ecommerce_search_assistant.schemas.types import NonEmptyString


SCHEMA_MAX_SEARCH_TOP_K = 100


class SearchFilter(SchemaModel):
    category: str | None = None
    brand: str | None = None
    colors: list[NonEmptyString] | None = None
    color_match_mode: Literal["any", "all"] | None = None
    use_cases: list[NonEmptyString] | None = None
    sizes: list[NonEmptyString] | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    gender: str | None = None
    material: str | None = None

    @model_validator(mode="after")
    def validate_price_range(self) -> "SearchFilter":
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price cannot be greater than max_price")
        return self


class SearchResultItem(SchemaModel):
    product_id: NonEmptyString
    score: float
    source: Literal["text", "image", "hybrid"]
    rerank_score: float | None = None
    explicit_constraint_satisfied: bool | None = None
    explicit_constraint_satisfaction: dict[str, bool] | None = None


class ImageBoundingBox(SchemaModel):
    left: int = Field(ge=0)
    top: int = Field(ge=0)
    right: int = Field(gt=0)
    bottom: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_box(self) -> "ImageBoundingBox":
        if self.left >= self.right:
            raise ValueError("left must be less than right")
        if self.top >= self.bottom:
            raise ValueError("top must be less than bottom")
        return self


class ImageDetectionBox(SchemaModel):
    bbox: ImageBoundingBox
    confidence: float = Field(ge=0)
    class_id: int | None = None
    is_fallback: bool = False


class ImageDetectionRequest(SchemaModel):
    image: ImagePayload


class ImageDetectionResponse(SchemaModel):
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    detections: list[ImageDetectionBox] = Field(default_factory=list)


class SearchResponse(SchemaModel):
    rewritten_query: str | None = None
    filters: SearchFilter | None = None
    explicit_filters: SearchFilter | None = None
    inferred_filters: SearchFilter | None = None
    relaxed_filters: list[str] = Field(default_factory=list)
    constraint_failure_reason: str | None = None
    route: Literal["text_search", "image_search", "hybrid_search", "clarification", "non_product_answer"] | None = None
    product_ids: list[NonEmptyString] = Field(default_factory=list)
    results: list[SearchResultItem] = Field(default_factory=list)
    detections: list[ImageDetectionBox] = Field(default_factory=list)


class TextSearchRequest(SchemaModel):
    query: NonEmptyString
    filters: SearchFilter | None = None
    top_k: int | None = Field(default=None, gt=0, le=SCHEMA_MAX_SEARCH_TOP_K)


class ImageSearchRequest(SchemaModel):
    image: ImagePayload
    crop_box: ImageBoundingBox | None = None
    filters: SearchFilter | None = None
    top_k: int | None = Field(default=None, gt=0, le=SCHEMA_MAX_SEARCH_TOP_K)


class HybridSearchRequest(SchemaModel):
    query: str | None = None
    image: ImagePayload | None = None
    crop_box: ImageBoundingBox | None = None
    filters: SearchFilter | None = None
    top_k: int | None = Field(default=None, gt=0, le=SCHEMA_MAX_SEARCH_TOP_K)
    strategy: Literal["weighted"] = "weighted"

    @model_validator(mode="after")
    def validate_query_or_image(self) -> "HybridSearchRequest":
        if not self.query and self.image is None:
            raise ValueError("query or image is required for hybrid search")
        return self


class AutoSearchRequest(SchemaModel):
    query: str | None = None
    image: ImagePayload | None = None
    crop_box: ImageBoundingBox | None = None
    filters: SearchFilter | None = None
    top_k: int | None = Field(default=None, gt=0, le=SCHEMA_MAX_SEARCH_TOP_K)
    locale: NonEmptyString = "vi-VN"

    @model_validator(mode="after")
    def validate_query_or_image(self) -> "AutoSearchRequest":
        if not self.query and self.image is None:
            raise ValueError("query or image is required for auto search")
        return self
