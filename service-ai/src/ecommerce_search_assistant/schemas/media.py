from base64 import b64decode
from binascii import Error as BinasciiError

from pydantic import Field, field_validator, model_validator

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.schemas.base import SchemaModel
from ecommerce_search_assistant.schemas.types import NonEmptyString


class ImagePayload(SchemaModel):
    content_type: NonEmptyString
    data_base64: NonEmptyString = Field(description="Raw base64 image bytes, without a data URI prefix.")
    filename: str | None = None

    @field_validator("content_type", mode="before")
    @classmethod
    def normalize_content_type(cls, value: object) -> str:
        return str(value).lower()

    @model_validator(mode="after")
    def validate_upload(self) -> "ImagePayload":
        settings = get_settings()
        if self.content_type not in settings.allowed_image_mime_types:
            allowed = ", ".join(settings.allowed_image_mime_types)
            raise ValueError(f"content_type must be one of: {allowed}")

        try:
            raw_bytes = b64decode(self.data_base64, validate=True)
        except (BinasciiError, ValueError) as exc:
            raise ValueError("data_base64 must contain valid base64-encoded bytes") from exc

        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(raw_bytes) > max_bytes:
            raise ValueError(f"image payload exceeds MAX_UPLOAD_MB={settings.max_upload_mb}")
        return self
