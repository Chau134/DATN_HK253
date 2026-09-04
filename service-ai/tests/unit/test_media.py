from base64 import b64encode

import pytest
from pydantic import ValidationError

from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.schemas.media import ImagePayload


def test_image_upload_validation_accepts_allowed_mime_and_rejects_bad_inputs(settings: Settings) -> None:
    valid_payload = ImagePayload(
        content_type="image/png",
        data_base64=b64encode(b"small-image").decode("ascii"),
    )
    assert valid_payload.content_type == "image/png"

    with pytest.raises(ValidationError):
        ImagePayload(
            content_type="image/webp",
            data_base64=b64encode(b"small-image").decode("ascii"),
        )

    with pytest.raises(ValidationError):
        ImagePayload(
            content_type="image/png",
            data_base64=b64encode(b"x" * (1024 * 1024 + 1)).decode("ascii"),
        )
