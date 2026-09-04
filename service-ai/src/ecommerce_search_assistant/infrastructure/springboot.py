from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from threading import RLock
from time import monotonic, sleep
from typing import Any, Generic, TypeVar
from urllib.parse import quote

import httpx

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.core.metrics import assistant_metrics

logger = logging.getLogger(__name__)

T = TypeVar("T")

_TRANSIENT_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
SPRING_BOOT_UNAVAILABLE_WARNING = "spring_boot_unavailable"


@dataclass(frozen=True)
class SpringBootResult(Generic[T]):
    data: T
    warnings: list[str] = field(default_factory=list)


@dataclass
class SpringBootClient:
    settings: Settings = field(default_factory=get_settings)
    _product_context_cache: OrderedDict[str, tuple[float, dict[str, Any]]] = field(
        default_factory=OrderedDict,
        init=False,
        repr=False,
    )
    _product_context_cache_lock: RLock = field(
        default_factory=RLock,
        init=False,
        repr=False,
    )
    _http_client: httpx.Client | None = field(default=None, init=False, repr=False)
    _http_client_lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _product_context_circuit_lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _product_context_consecutive_failures: int = field(default=0, init=False, repr=False)
    _product_context_circuit_open_until: float = field(default=0.0, init=False, repr=False)

    def get_products_by_ids(self, product_ids: list[str]) -> SpringBootResult[list[dict[str, Any]]]:
        unique_product_ids = list(dict.fromkeys(
            product_id
            for raw_product_id in product_ids
            if (product_id := str(raw_product_id).strip())
        ))
        if not unique_product_ids:
            return SpringBootResult(data=[])

        cached, missing = self._cached_products(unique_product_ids)
        if not missing:
            assistant_metrics.record_product_context_cache(hits=len(cached), misses=0)
            return SpringBootResult(data=[cached[value] for value in unique_product_ids if value in cached])

        if self._product_context_circuit_is_open():
            stale = self._stale_products(missing)
            combined = {**cached, **stale}
            assistant_metrics.record_product_context_cache(
                hits=len(cached) + len(stale),
                misses=max(0, len(missing) - len(stale)),
            )
            return SpringBootResult(
                data=[combined[value] for value in unique_product_ids if value in combined],
                warnings=[SPRING_BOOT_UNAVAILABLE_WARNING],
            )

        result = self._request_json(
            "POST",
            self._endpoint_url(self.settings.springboot_product_context_endpoint),
            json_body={"product_ids": missing},
            failure_warning=SPRING_BOOT_UNAVAILABLE_WARNING,
            timeout_seconds=self.settings.assistant_product_context_timeout_seconds,
            retry_attempts=self.settings.assistant_product_context_retry_attempts,
        )
        loaded = _normalize_product_collection(result.data)
        if result.warnings:
            self._record_product_context_failure()
        else:
            self._record_product_context_success()
            self._cache_products(loaded)
        loaded_by_id = {
            str(item.get("product_id") or item.get("id")): item
            for item in loaded
            if item.get("product_id") is not None or item.get("id") is not None
        }
        stale = self._stale_products(missing) if result.warnings else {}
        combined = {**stale, **cached, **loaded_by_id}
        assistant_metrics.record_product_context_cache(
            hits=len(cached) + len(stale),
            misses=max(0, len(missing) - len(stale)),
        )
        return SpringBootResult(
            data=[combined[value] for value in unique_product_ids if value in combined],
            warnings=result.warnings,
        )

    def _cached_products(
        self,
        product_ids: list[str],
    ) -> tuple[dict[str, dict[str, Any]], list[str]]:
        ttl = self.settings.assistant_product_context_cache_ttl_seconds
        limit = self.settings.assistant_product_context_cache_size
        if ttl <= 0 or limit <= 0:
            return {}, list(product_ids)
        now = monotonic()
        namespace = self.settings.qdrant_text_collection
        cached: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        with self._product_context_cache_lock:
            for product_id in product_ids:
                key = f"{namespace}:{product_id}"
                entry = self._product_context_cache.get(key)
                if entry is None or entry[0] <= now:
                    if (
                        entry is not None
                        and entry[0] + self.settings.assistant_product_context_stale_ttl_seconds <= now
                    ):
                        self._product_context_cache.pop(key, None)
                    missing.append(product_id)
                    continue
                self._product_context_cache.move_to_end(key)
                cached[product_id] = dict(entry[1])
        return cached, missing

    def _stale_products(self, product_ids: list[str]) -> dict[str, dict[str, Any]]:
        stale_ttl = self.settings.assistant_product_context_stale_ttl_seconds
        if stale_ttl <= 0:
            return {}
        now = monotonic()
        stale: dict[str, dict[str, Any]] = {}
        namespace = self.settings.qdrant_text_collection
        with self._product_context_cache_lock:
            for product_id in product_ids:
                entry = self._product_context_cache.get(f"{namespace}:{product_id}")
                if entry is not None and entry[0] <= now < entry[0] + stale_ttl:
                    stale[product_id] = dict(entry[1])
        return stale

    def _product_context_circuit_is_open(self) -> bool:
        with self._product_context_circuit_lock:
            return monotonic() < self._product_context_circuit_open_until

    def _record_product_context_success(self) -> None:
        with self._product_context_circuit_lock:
            self._product_context_consecutive_failures = 0
            self._product_context_circuit_open_until = 0.0

    def _record_product_context_failure(self) -> None:
        with self._product_context_circuit_lock:
            self._product_context_consecutive_failures += 1
            if (
                self._product_context_consecutive_failures
                >= self.settings.assistant_product_context_circuit_failure_threshold
            ):
                self._product_context_circuit_open_until = (
                    monotonic() + self.settings.assistant_product_context_circuit_reset_seconds
                )

    def _cache_products(self, products: list[dict[str, Any]]) -> None:
        ttl = self.settings.assistant_product_context_cache_ttl_seconds
        limit = self.settings.assistant_product_context_cache_size
        if ttl <= 0 or limit <= 0:
            return
        expires_at = monotonic() + ttl
        namespace = self.settings.qdrant_text_collection
        with self._product_context_cache_lock:
            for product in products:
                product_id = product.get("product_id") or product.get("id")
                if product_id is None:
                    continue
                key = f"{namespace}:{product_id}"
                self._product_context_cache[key] = (expires_at, dict(product))
                self._product_context_cache.move_to_end(key)
            while len(self._product_context_cache) > limit:
                self._product_context_cache.popitem(last=False)

    def search_products_by_filter(self, filters: Any) -> SpringBootResult[list[dict[str, Any]]]:
        result = self._request_json(
            "POST",
            self._endpoint_url(self.settings.springboot_product_search_endpoint),
            json_body=_normalize_filter_payload(filters),
            failure_warning=SPRING_BOOT_UNAVAILABLE_WARNING,
        )
        return SpringBootResult(
            data=_normalize_product_collection(result.data),
            warnings=result.warnings,
        )

    # Compatibility shims for earlier phases.
    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self._get_product_by_id(product_id).data

    def get_products(self, product_ids: list[str]) -> list[dict[str, Any]]:
        return self.get_products_by_ids(product_ids).data

    def _get_product_by_id(self, product_id: str) -> SpringBootResult[dict[str, Any] | None]:
        result = self._request_json(
            "GET",
            self._product_detail_url(product_id),
            allow_not_found=True,
            failure_warning=SPRING_BOOT_UNAVAILABLE_WARNING,
        )
        return SpringBootResult(
            data=_normalize_object_payload(product_id, result.data),
            warnings=result.warnings,
        )

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        allow_not_found: bool = False,
        failure_warning: str,
        timeout_seconds: float | None = None,
        retry_attempts: int | None = None,
    ) -> SpringBootResult[Any | None]:
        retries = (
            self.settings.springboot_retry_attempts
            if retry_attempts is None
            else retry_attempts
        )
        total_attempts = retries + 1
        timeout = httpx.Timeout(timeout_seconds or self.settings.springboot_timeout_seconds)
        headers = {
            "Accept": "application/json",
            "X-API-Key": self.settings.springboot_api_key,
        }

        client = self._get_http_client()
        for attempt_index in range(total_attempts):
            try:
                response = client.request(
                        method,
                        url,
                        timeout=timeout,
                        headers=headers,
                        params=params,
                        json=json_body,
                    )
                if response.status_code == 404 and allow_not_found:
                    logger.info("springboot_resource_not_found", extra={"url": url})
                    return SpringBootResult(data=None, warnings=[failure_warning])
                if self._should_retry_response(response.status_code, attempt_index, retries):
                    self._log_retry(url, response.status_code, attempt_index)
                    self._sleep_before_retry(attempt_index)
                    continue

                response.raise_for_status()
                return SpringBootResult(data=response.json())
            except httpx.RequestError as exc:
                if attempt_index < retries:
                    self._log_retry(url, exc.__class__.__name__, attempt_index)
                    self._sleep_before_retry(attempt_index)
                    continue
                logger.warning(
                    "springboot_request_failed",
                    extra={"url": url, "error_type": exc.__class__.__name__},
                    exc_info=True,
                )
            except httpx.HTTPStatusError as exc:
                if self._should_retry_response(exc.response.status_code, attempt_index, retries):
                    self._log_retry(url, exc.response.status_code, attempt_index)
                    self._sleep_before_retry(attempt_index)
                    continue
                logger.warning(
                    "springboot_response_failed",
                    extra={"url": url, "status_code": exc.response.status_code},
                    exc_info=True,
                )
            except ValueError:
                logger.warning("springboot_invalid_json", extra={"url": url}, exc_info=True)

            return SpringBootResult(data=None, warnings=[failure_warning])

        return SpringBootResult(data=None, warnings=[failure_warning])

    def _get_http_client(self) -> httpx.Client:
        with self._http_client_lock:
            if self._http_client is None:
                self._http_client = httpx.Client(follow_redirects=True)
            return self._http_client

    def close(self) -> None:
        with self._http_client_lock:
            if self._http_client is not None:
                self._http_client.close()
                self._http_client = None

    def _product_detail_url(self, product_id: str) -> str:
        endpoint = self.settings.springboot_product_detail_endpoint.rstrip("/")
        return self._endpoint_url(f"{endpoint}/{quote(product_id, safe='')}")

    def _endpoint_url(self, endpoint: str) -> str:
        base_url = self.settings.springboot_base_url.rstrip("/")
        normalized_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base_url}{normalized_endpoint}"

    def _sleep_before_retry(self, attempt_index: int) -> None:
        delay_seconds = self.settings.springboot_retry_backoff_seconds * (2**attempt_index)
        if delay_seconds > 0:
            sleep(delay_seconds)

    @staticmethod
    def _should_retry_response(status_code: int, attempt_index: int, retries: int) -> bool:
        return status_code in _TRANSIENT_STATUS_CODES and attempt_index < retries

    @staticmethod
    def _log_retry(url: str, reason: object, attempt_index: int) -> None:
        logger.warning(
            "springboot_request_retrying",
            extra={"url": url, "reason": str(reason), "retry_index": attempt_index + 1},
        )


def _normalize_filter_payload(filters: Any) -> dict[str, Any]:
    if filters is None:
        return {}
    if hasattr(filters, "model_dump"):
        return dict(filters.model_dump(exclude_none=True))
    if isinstance(filters, Mapping):
        return {str(key): value for key, value in filters.items() if value is not None}
    return {}


def _normalize_product_collection(payload: Any | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [_normalize_object_payload("", item) or {"payload": item} for item in payload]
    if isinstance(payload, dict):
        for key in ("products", "items", "content", "data"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [_normalize_object_payload("", item) or {"payload": item} for item in nested]
        return [payload]
    return [{"payload": payload}]


def _normalize_object_payload(product_id: str, payload: Any | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    fallback = {"payload": payload}
    if product_id:
        fallback["product_id"] = product_id
    return fallback


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    return list(dict.fromkeys(warning for warning in warnings if warning))
