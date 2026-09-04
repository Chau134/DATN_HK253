from __future__ import annotations

from dataclasses import dataclass
import logging
from time import sleep

from qdrant_client import QdrantClient, models

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.core.logging import configure_logging

logger = logging.getLogger(__name__)

_DISTANCE_MAP = {
    "COSINE": models.Distance.COSINE,
    "DOT": models.Distance.DOT,
    "EUCLID": models.Distance.EUCLID,
    "MANHATTAN": models.Distance.MANHATTAN,
}

_PAYLOAD_INDEXES: tuple[tuple[str, models.PayloadSchemaType], ...] = (
    ("product_id", models.PayloadSchemaType.KEYWORD),
    ("category_codes", models.PayloadSchemaType.KEYWORD),
    ("category_keys", models.PayloadSchemaType.KEYWORD),
    ("category_aliases", models.PayloadSchemaType.KEYWORD),
    ("brand_key", models.PayloadSchemaType.KEYWORD),
    ("color_keys", models.PayloadSchemaType.KEYWORD),
    ("material_keys", models.PayloadSchemaType.KEYWORD),
    ("use_case_keys", models.PayloadSchemaType.KEYWORD),
    ("size_keys", models.PayloadSchemaType.KEYWORD),
    ("gender_key", models.PayloadSchemaType.KEYWORD),
    ("audience_keys", models.PayloadSchemaType.KEYWORD),
    ("normalized_title", models.PayloadSchemaType.KEYWORD),
    ("normalized_title_vi", models.PayloadSchemaType.KEYWORD),
    ("normalized_title_tokens", models.PayloadSchemaType.KEYWORD),
    ("metadata_schema_version", models.PayloadSchemaType.INTEGER),
    ("active", models.PayloadSchemaType.BOOL),
    ("selling_price", models.PayloadSchemaType.FLOAT),
)


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    vector_size: int
    distance: models.Distance


@dataclass(frozen=True)
class CollectionSetupResult:
    name: str
    collection_created: bool
    payload_indexes_created: tuple[str, ...]


@dataclass(frozen=True)
class QdrantSetupResult:
    collections: tuple[CollectionSetupResult, ...]


def build_qdrant_client(settings: Settings) -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


def get_collection_specs(settings: Settings) -> tuple[CollectionSpec, CollectionSpec]:
    distance = _DISTANCE_MAP[settings.qdrant_distance]
    return (
        CollectionSpec(
            name=settings.qdrant_text_collection,
            vector_size=settings.qdrant_text_vector_size,
            distance=distance,
        ),
        CollectionSpec(
            name=settings.qdrant_image_collection,
            vector_size=settings.qdrant_image_vector_size,
            distance=distance,
        ),
    )


def wait_until_qdrant_is_ready(
    client: QdrantClient,
    *,
    attempts: int = 20,
    delay_seconds: float = 1.0,
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            client.get_collections()
            return
        except Exception as exc:  # pragma: no cover - exercised in real container startup.
            last_error = exc
            logger.info(
                "qdrant_not_ready",
                extra={"attempt": attempt, "attempts": attempts},
            )
            sleep(delay_seconds)

    raise RuntimeError("Qdrant did not become ready before bootstrap timed out") from last_error


def ensure_qdrant_setup(
    client: QdrantClient,
    settings: Settings,
    *,
    wait_for_ready: bool = False,
) -> QdrantSetupResult:
    if wait_for_ready:
        wait_until_qdrant_is_ready(client)

    collection_results = tuple(_ensure_collection(client, spec) for spec in get_collection_specs(settings))
    return QdrantSetupResult(collections=collection_results)


def bootstrap_qdrant(settings: Settings | None = None) -> QdrantSetupResult:
    resolved_settings = settings or get_settings()
    client = build_qdrant_client(resolved_settings)
    return ensure_qdrant_setup(client, resolved_settings, wait_for_ready=True)


def _ensure_collection(client: QdrantClient, spec: CollectionSpec) -> CollectionSetupResult:
    collection_created = False
    if not client.collection_exists(spec.name):
        client.create_collection(
            collection_name=spec.name,
            vectors_config=models.VectorParams(
                size=spec.vector_size,
                distance=spec.distance,
            ),
        )
        collection_created = True
    else:
        _warn_on_dimension_mismatch(client, spec)

    existing_payload_indexes = _get_payload_index_names(client, spec.name)
    created_indexes: list[str] = []
    for field_name, field_schema in _PAYLOAD_INDEXES:
        if field_name in existing_payload_indexes:
            continue

        client.create_payload_index(
            collection_name=spec.name,
            field_name=field_name,
            field_schema=field_schema,
            wait=True,
        )
        created_indexes.append(field_name)

    logger.info(
        "qdrant_collection_bootstrapped",
        extra={
            "collection": spec.name,
            "collection_created": collection_created,
            "payload_indexes_created": created_indexes,
        },
    )
    return CollectionSetupResult(
        name=spec.name,
        collection_created=collection_created,
        payload_indexes_created=tuple(created_indexes),
    )


def _warn_on_dimension_mismatch(client: QdrantClient, spec: CollectionSpec) -> None:
    try:
        info = client.get_collection(spec.name)
        vectors = info.config.params.vectors
        existing_size = getattr(vectors, "size", None)
    except Exception:  # pragma: no cover - defensive; never block bootstrap on introspection.
        logger.warning("qdrant_dimension_check_failed", extra={"collection": spec.name})
        return

    if existing_size is not None and existing_size != spec.vector_size:
        logger.warning(
            "qdrant_dimension_mismatch",
            extra={
                "collection": spec.name,
                "existing_size": existing_size,
                "expected_size": spec.vector_size,
                "action": "drop and recreate the collection, then re-index all products",
            },
        )


def _get_payload_index_names(client: QdrantClient, collection_name: str) -> set[str]:
    collection_info = client.get_collection(collection_name)
    payload_schema = collection_info.payload_schema or {}
    return set(payload_schema)


def main() -> int:
    settings = get_settings()
    configure_logging(settings)
    result = bootstrap_qdrant(settings)
    logger.info(
        "qdrant_bootstrap_completed",
        extra={
            "collections": [
                {
                    "name": collection.name,
                    "collection_created": collection.collection_created,
                    "payload_indexes_created": list(collection.payload_indexes_created),
                }
                for collection in result.collections
            ],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
