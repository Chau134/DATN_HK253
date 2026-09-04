from typing import Literal

from pydantic import Field

from ecommerce_search_assistant.schemas.base import SchemaModel
from ecommerce_search_assistant.schemas.types import NonEmptyString

IndexFailureStage = Literal[
    "delete",
    "text_embedding",
    "text_upsert",
    "image_download",
    "yolo_crop",
    "image_embedding",
    "image_upsert",
]


class IndexFailure(SchemaModel):
    product_id: NonEmptyString
    stage: IndexFailureStage
    reason: NonEmptyString
    image_url: str | None = None


class ProductIndexResponse(SchemaModel):
    indexed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    image_indexed_count: int = Field(default=0, ge=0)
    image_failed_count: int = Field(default=0, ge=0)
    failures: list[IndexFailure] = Field(default_factory=list)


class ProductDeleteResponse(SchemaModel):
    product_id: NonEmptyString
    deleted: bool = True
