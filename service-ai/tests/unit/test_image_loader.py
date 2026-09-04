from io import BytesIO

import httpx
import pytest
from PIL import Image

from ecommerce_search_assistant.services.indexing.image_loader import ImageLoadService


class _FakeHttpClient:
    def __init__(self, response: httpx.Response, **_: object) -> None:
        self._response = response

    def __enter__(self) -> "_FakeHttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get(self, _: str) -> httpx.Response:
        return self._response


def _response(content: bytes, content_type: str) -> httpx.Response:
    request = httpx.Request("GET", "https://cdn.test/media")
    return httpx.Response(
        200,
        content=content,
        headers={"Content-Type": content_type},
        request=request,
    )


def test_load_from_url_rejects_non_image_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _response(b"#EXTM3U\n", "application/vnd.apple.mpegurl")
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: _FakeHttpClient(response, **kwargs))

    with pytest.raises(ValueError, match="unsupported image content type: application/vnd.apple.mpegurl"):
        ImageLoadService().load_from_url("https://cdn.test/video/master.m3u8")


def test_load_from_url_accepts_image_content_type_with_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="PNG")
    response = _response(buffer.getvalue(), "image/png; charset=binary")
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: _FakeHttpClient(response, **kwargs))

    image = ImageLoadService().load_from_url("https://cdn.test/image.png")

    assert image.mode == "RGB"
    assert image.size == (2, 2)
