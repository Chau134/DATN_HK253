from dataclasses import dataclass, field
from io import BytesIO

import httpx
from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings


@dataclass
class ImageLoadService:
    settings: Settings = field(default_factory=get_settings)

    def load_from_url(self, image_url: str) -> Image.Image:
        timeout = httpx.Timeout(self.settings.springboot_timeout_seconds)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(image_url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "").partition(";")[0].strip().lower()
        if content_type and not content_type.startswith("image/"):
            raise ValueError(f"unsupported image content type: {content_type}")

        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if len(response.content) > max_bytes:
            raise ValueError(f"image exceeds MAX_UPLOAD_MB={self.settings.max_upload_mb}")

        image = Image.open(BytesIO(response.content))
        image.load()
        return image.convert("RGB")
