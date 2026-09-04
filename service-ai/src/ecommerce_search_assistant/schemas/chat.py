from pydantic import Field, model_validator

from ecommerce_search_assistant.schemas.base import SchemaModel
from ecommerce_search_assistant.schemas.media import ImagePayload
from ecommerce_search_assistant.schemas.search import ImageBoundingBox
from ecommerce_search_assistant.schemas.types import NonEmptyString


class ChatRequest(SchemaModel):
    session_id: NonEmptyString
    user_id: NonEmptyString
    request_id: str | None = Field(default=None, min_length=1, max_length=128)
    turn_sequence: int | None = Field(default=None, ge=1)
    message: str | None = None
    image: ImagePayload | None = None
    crop_box: ImageBoundingBox | None = None
    locale: NonEmptyString = "vi-VN"

    @model_validator(mode="after")
    def validate_message_or_image(self) -> "ChatRequest":
        if not self.message and self.image is None:
            raise ValueError("message or image is required for chat")
        return self
