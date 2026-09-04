from typing import Any

from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.infrastructure import springboot as springboot_module
from ecommerce_search_assistant.infrastructure.springboot import SpringBootClient


class _FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, Any]]:
        return [{"id": 2, "title": "Second"}, {"id": 1, "title": "First"}]


class _FakeHttpClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def __enter__(self) -> "_FakeHttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return _FakeResponse()


class _FailingHttpClient(_FakeHttpClient):
    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        raise springboot_module.httpx.ConnectTimeout("backend unavailable")

class _TransientFailingHttpClient(_FakeHttpClient):
    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        if len(self.requests) == 1:
            raise springboot_module.httpx.ConnectTimeout("temporary timeout")
        return _FakeResponse()




def test_get_products_by_ids_uses_one_authenticated_batch_request(monkeypatch) -> None:
    fake_http_client = _FakeHttpClient()
    monkeypatch.setattr(
        springboot_module.httpx,
        "Client",
        lambda **_: fake_http_client,
    )
    settings = Settings(
        _env_file=None,
        SPRINGBOOT_BASE_URL="http://spring.test",
        SPRINGBOOT_API_KEY="secret",
        SPRINGBOOT_RETRY_ATTEMPTS=0,
    )

    result = SpringBootClient(settings=settings).get_products_by_ids(["2", "1", "2", " "])

    assert result.data == [{"id": 2, "title": "Second"}, {"id": 1, "title": "First"}]
    assert result.warnings == []
    assert len(fake_http_client.requests) == 1
    assert fake_http_client.requests[0]["method"] == "POST"
    assert fake_http_client.requests[0]["url"] == "http://spring.test/api/internal/ai/products/context"
    assert fake_http_client.requests[0]["headers"]["X-API-Key"] == "secret"
    assert fake_http_client.requests[0]["json"] == {"product_ids": ["2", "1"]}

def test_get_products_by_ids_retries_transient_context_timeout(monkeypatch) -> None:
    fake_http_client = _TransientFailingHttpClient()
    monkeypatch.setattr(
        springboot_module.httpx,
        "Client",
        lambda **_: fake_http_client,
    )
    settings = Settings(
        _env_file=None,
        SPRINGBOOT_BASE_URL="http://spring.test",
        ASSISTANT_PRODUCT_CONTEXT_RETRY_ATTEMPTS=1,
        SPRINGBOOT_RETRY_BACKOFF_SECONDS=0,
    )

    result = SpringBootClient(settings=settings).get_products_by_ids(["2", "1"])

    assert result.data == [{"id": 2, "title": "Second"}, {"id": 1, "title": "First"}]
    assert result.warnings == []
    assert len(fake_http_client.requests) == 2




def test_get_products_by_ids_skips_http_for_empty_ids(monkeypatch) -> None:
    fake_http_client = _FakeHttpClient()
    monkeypatch.setattr(springboot_module.httpx, "Client", lambda **_: fake_http_client)

    result = SpringBootClient(settings=Settings(_env_file=None)).get_products_by_ids(["", " "])

    assert result.data == []
    assert fake_http_client.requests == []


def test_get_products_by_ids_reuses_catalog_scoped_context_cache(monkeypatch) -> None:
    fake_http_client = _FakeHttpClient()
    monkeypatch.setattr(springboot_module.httpx, "Client", lambda **_: fake_http_client)
    settings = Settings(
        _env_file=None,
        SPRINGBOOT_BASE_URL="http://spring.test",
        SPRINGBOOT_RETRY_ATTEMPTS=0,
        ASSISTANT_PRODUCT_CONTEXT_CACHE_TTL_SECONDS=300,
        ASSISTANT_PRODUCT_CONTEXT_CACHE_SIZE=10,
        QDRANT_TEXT_COLLECTION="catalog-v1",
    )
    client = SpringBootClient(settings=settings)

    first = client.get_products_by_ids(["2", "1"])
    second = client.get_products_by_ids(["1", "2"])

    assert [item["id"] for item in first.data] == [2, 1]
    assert [item["id"] for item in second.data] == [1, 2]
    assert len(fake_http_client.requests) == 1


def test_product_context_circuit_opens_after_failure(monkeypatch) -> None:
    fake_http_client = _FailingHttpClient()
    monkeypatch.setattr(springboot_module.httpx, "Client", lambda **_: fake_http_client)
    settings = Settings(
        _env_file=None,
        SPRINGBOOT_BASE_URL="http://spring.test",
        ASSISTANT_PRODUCT_CONTEXT_RETRY_ATTEMPTS=0,
        ASSISTANT_PRODUCT_CONTEXT_CIRCUIT_FAILURE_THRESHOLD=1,
    )
    client = SpringBootClient(settings=settings)

    first = client.get_products_by_ids(["1"])
    second = client.get_products_by_ids(["2"])

    assert first.warnings == ["spring_boot_unavailable"]
    assert second.warnings == ["spring_boot_unavailable"]
    assert len(fake_http_client.requests) == 1


def test_product_context_uses_stale_cache_when_backend_fails(monkeypatch) -> None:
    fake_http_client = _FailingHttpClient()
    monkeypatch.setattr(springboot_module.httpx, "Client", lambda **_: fake_http_client)
    settings = Settings(
        _env_file=None,
        SPRINGBOOT_BASE_URL="http://spring.test",
        ASSISTANT_PRODUCT_CONTEXT_RETRY_ATTEMPTS=0,
        ASSISTANT_PRODUCT_CONTEXT_STALE_TTL_SECONDS=300,
        QDRANT_TEXT_COLLECTION="catalog-v1",
    )
    client = SpringBootClient(settings=settings)
    client._product_context_cache["catalog-v1:1"] = (
        springboot_module.monotonic() - 1,
        {"id": 1, "title": "Stale product"},
    )

    result = client.get_products_by_ids(["1"])

    assert result.data == [{"id": 1, "title": "Stale product"}]
    assert result.warnings == ["spring_boot_unavailable"]
