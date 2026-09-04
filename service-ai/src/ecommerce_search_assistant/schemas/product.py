from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from ecommerce_search_assistant.schemas.base import SchemaModel
from ecommerce_search_assistant.schemas.types import NonEmptyString


class AiCategory(SchemaModel):
    category_code: str | None = None
    category_level: str | None = None
    category_name: str | None = None
    category_name_vi: str | None = None

    @property
    def name(self) -> str | None:
        return self.category_name

    @property
    def name_vi(self) -> str | None:
        return self.category_name_vi

    @property
    def level(self) -> str | None:
        return self.category_level

    @property
    def code(self) -> str | None:
        return self.category_code


class ProductIndexItem(SchemaModel):
    product_id: NonEmptyString
    product_display_name: str | None = None
    product_display_name_vi: str | None = None
    brand_name: str | None = None
    base_colour: str | None = None
    base_colour_vi: str | None = None
    material: str | None = None
    material_vi: str | None = None
    fit: str | None = None
    fit_vi: str | None = None
    season: str | None = None
    season_vi: str | None = None
    product_usage: str | None = None
    product_usage_vi: str | None = None
    gender: str | None = None
    gender_vi: str | None = None
    description: str | None = None
    description_vi: str | None = None
    categories: list[AiCategory] = Field(default_factory=list)
    option_value: list[NonEmptyString] = Field(default_factory=list)
    unified_size: list[NonEmptyString] = Field(default_factory=list)
    inventory_count: int | None = Field(default=None, ge=0)
    available: bool = False
    active: bool = False
    selling_price: float | None = Field(default=None, ge=0)
    vat: float | None = Field(default=None, ge=0)
    image_urls: list[NonEmptyString] = Field(default_factory=list)
    attributes: dict[str, str] = Field(default_factory=dict)
    attributes_vi: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime | None = None

    @field_validator("active", "available", mode="before")
    @classmethod
    def default_business_flags(cls, value: Any) -> bool:
        if value is None:
            return False
        return bool(value)

    @model_validator(mode="after")
    def validate_indexable_content(self) -> "ProductIndexItem":
        has_text = any(
            (
                self.product_display_name,
                self.product_display_name_vi,
                self.brand_name,
                self.base_colour,
                self.base_colour_vi,
                self.material,
                self.material_vi,
                self.fit,
                self.fit_vi,
                self.season,
                self.season_vi,
                self.product_usage,
                self.product_usage_vi,
                self.gender,
                self.gender_vi,
                self.description,
                self.description_vi,
            )
        ) or bool(
            self.categories
            or self.option_value
            or self.unified_size
            or self.attributes
            or self.attributes_vi
        )
        has_images = bool(self.image_urls)
        if not has_text and not has_images:
            raise ValueError("at least product_display_name, description, or image_urls is required for indexing")
        return self


class ProductIndexRequest(SchemaModel):
    items: list[ProductIndexItem] = Field(min_length=1)
