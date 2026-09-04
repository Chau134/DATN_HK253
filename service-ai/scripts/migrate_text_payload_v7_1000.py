from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from qdrant_client import models

from ecommerce_search_assistant.core.config import get_settings
from ecommerce_search_assistant.infrastructure.qdrant import build_qdrant_client
from ecommerce_search_assistant.services.indexing.product import (
    _resolve_article_type_category_keys,
    _title_article_type_keys,
)
from ecommerce_search_assistant.services.search.canonicalization import (
    CANONICALIZER_VERSION,
    METADATA_SCHEMA_VERSION,
    audience_keys_for_gender,
    canonicalize_brand_key,
    canonicalize_gender_key,
    canonicalize_material_keys,
    canonicalize_size_keys,
    canonicalize_use_case_keys,
    catalog_product_color_keys,
)
from ecommerce_search_assistant.services.search.category_taxonomy import (
    category_aliases_for_keys,
)


CANONICAL_FIELDS = (
    "category_keys",
    "category_aliases",
    "brand_key",
    "color_keys",
    "material_keys",
    "use_case_keys",
    "size_keys",
    "gender_key",
    "audience_keys",
    "normalized_title_tokens",
    "title_tokens",
    "metadata_schema_version",
    "canonicalizer_version",
)


def main() -> int:
    args = parse_args()
    settings = get_settings()
    collection = args.collection or settings.qdrant_text_collection
    client = build_qdrant_client(settings)

    if args.rollback:
        return rollback(client, collection, args.rollback, args.batch_size)

    points = list(scroll_points(client, collection, args.batch_size))
    audit = audit_points(points, args.expected_products)
    changes = changed_points(points)
    result: dict[str, Any] = {
        "collection": collection,
        "mode": "apply" if args.apply else "dry-run",
        **audit,
        "changed_points": len(changes),
        "changed_fields": dict(sorted(changed_field_counts(changes).items())),
        "target_schema_version": METADATA_SCHEMA_VERSION,
        "target_canonicalizer_version": CANONICALIZER_VERSION,
        "vectors_reembedded": 0,
    }

    if not args.apply:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.backup is None:
        raise RuntimeError("--backup is required with --apply")
    backup_path = args.backup.resolve()
    backup_sha256 = write_backup(backup_path, collection, points)
    result["backup"] = str(backup_path)
    result["backup_sha256"] = backup_sha256

    apply_changes(client, collection, changes, args.batch_size)
    after_points = list(scroll_points(client, collection, args.batch_size))
    after_audit = audit_points(after_points, args.expected_products)
    remaining = changed_points(after_points)
    result["after"] = after_audit
    result["remaining_changed_points"] = len(remaining)
    if remaining:
        raise RuntimeError(f"migration is not converged: {len(remaining)} points still differ")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit or migrate the 1,000-product text collection to canonical "
            "metadata schema v7 without changing vectors. Dry-run is default."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", type=Path, default=None)
    parser.add_argument("--backup", type=Path, default=None)
    parser.add_argument("--collection", default=None)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--expected-products", type=int, default=1000)
    return parser.parse_args()


def scroll_points(client: Any, collection: str, batch_size: int) -> Iterable[Any]:
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        yield from points
        if offset is None:
            return


def audit_points(points: list[Any], expected_products: int) -> dict[str, Any]:
    product_ids = [str((point.payload or {}).get("product_id") or "").strip() for point in points]
    unique_ids = {product_id for product_id in product_ids if product_id}
    if len(points) != expected_products or len(unique_ids) != expected_products:
        raise RuntimeError(
            f"expected {expected_products} points/products, got "
            f"points={len(points)} unique_products={len(unique_ids)}"
        )
    versions = Counter(
        str((point.payload or {}).get("metadata_schema_version", "missing"))
        for point in points
    )
    return {
        "scanned_points": len(points),
        "distinct_products": len(unique_ids),
        "blank_product_ids": sum(not product_id for product_id in product_ids),
        "schema_versions": dict(sorted(versions.items())),
        "missing_category_keys": count_missing(points, "category_keys"),
        "missing_color_keys": count_missing(points, "color_keys"),
        "missing_material_keys": count_missing(points, "material_keys"),
        "missing_use_case_keys": count_missing(points, "use_case_keys"),
        "raw_material_without_keys": count_raw_without_keys(
            points, ("material", "material_vi"), "material_keys"
        ),
        "raw_usage_without_keys": count_raw_without_keys(
            points,
            ("product_usage", "product_usage_vi", "season", "season_vi"),
            "use_case_keys",
        ),
    }


def changed_points(points: list[Any]) -> list[tuple[Any, dict[str, Any], tuple[str, ...]]]:
    changes: list[tuple[Any, dict[str, Any], tuple[str, ...]]] = []
    for point in points:
        payload = dict(point.payload or {})
        update = payload_update(payload)
        fields = tuple(
            field for field in CANONICAL_FIELDS if payload.get(field) != update.get(field)
        )
        if fields:
            changes.append((point.id, update, fields))
    return changes


def changed_field_counts(
    changes: list[tuple[Any, dict[str, Any], tuple[str, ...]]],
) -> Counter[str]:
    return Counter(field for _, _, fields in changes for field in fields)


def payload_update(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_title = str(payload.get("normalized_title") or "")
    normalized_title_vi = str(payload.get("normalized_title_vi") or "")
    source_category_keys = string_values(payload.get("source_category_keys"))
    if not source_category_keys:
        source_category_keys = string_values(payload.get("category_keys"))
    title_category_keys = _title_article_type_keys(normalized_title, normalized_title_vi)
    category_keys = _resolve_article_type_category_keys(
        source_category_keys,
        title_category_keys,
    )
    gender_key = canonicalize_gender_key(first_text(payload, "gender", "gender_vi"))
    title_tokens = list(
        dict.fromkeys(
            token
            for title in (normalized_title_vi, normalized_title)
            for token in title.split()
            if token
        )
    )
    return {
        "category_keys": category_keys,
        "category_aliases": category_aliases_for_keys(category_keys),
        "brand_key": canonicalize_brand_key(str(payload.get("brand_name") or "")),
        "color_keys": catalog_product_color_keys(
            payload.get("base_colour"), payload.get("base_colour_vi")
        ),
        "material_keys": canonicalize_material_keys(
            [payload.get("material"), payload.get("material_vi")]
        ),
        "use_case_keys": canonicalize_use_case_keys(
            [
                payload.get("product_usage"),
                payload.get("product_usage_vi"),
                payload.get("season"),
                payload.get("season_vi"),
            ]
        ),
        "size_keys": canonicalize_size_keys(
            [
                *string_values(payload.get("option_value")),
                *string_values(payload.get("unified_size")),
            ]
        ),
        "gender_key": gender_key,
        "audience_keys": audience_keys_for_gender(gender_key),
        "normalized_title_tokens": title_tokens,
        "title_tokens": title_tokens,
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "canonicalizer_version": CANONICALIZER_VERSION,
    }


def apply_changes(
    client: Any,
    collection: str,
    changes: list[tuple[Any, dict[str, Any], tuple[str, ...]]],
    batch_size: int,
) -> None:
    for start in range(0, len(changes), batch_size):
        operations = [
            models.SetPayloadOperation(
                set_payload=models.SetPayload(payload=update, points=[point_id])
            )
            for point_id, update, _ in changes[start : start + batch_size]
        ]
        if operations:
            client.batch_update_points(
                collection_name=collection,
                update_operations=operations,
                wait=True,
            )


def write_backup(path: Path, collection: str, points: list[Any]) -> str:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite existing backup: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                {
                    "type": "manifest",
                    "collection": collection,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "point_count": len(points),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )
        for point in points:
            handle.write(
                json.dumps(
                    {
                        "type": "point",
                        "point_id": str(point.id),
                        "payload": dict(point.payload or {}),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rollback(client: Any, collection: str, path: Path, batch_size: int) -> int:
    records = []
    manifest: dict[str, Any] | None = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("type") == "manifest":
                manifest = record
            elif record.get("type") == "point":
                records.append(record)
    if manifest is None or manifest.get("collection") != collection:
        raise RuntimeError("backup manifest does not match the target collection")
    if len(records) != int(manifest.get("point_count", -1)):
        raise RuntimeError("backup point count does not match its manifest")
    for start in range(0, len(records), batch_size):
        operations = [
            models.OverwritePayloadOperation(
                overwrite_payload=models.SetPayload(
                    payload=record["payload"],
                    points=[record["point_id"]],
                )
            )
            for record in records[start : start + batch_size]
        ]
        client.batch_update_points(
            collection_name=collection,
            update_operations=operations,
            wait=True,
        )
    print(
        json.dumps(
            {
                "collection": collection,
                "mode": "rollback",
                "restored_points": len(records),
                "backup": str(path.resolve()),
                "vectors_reembedded": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None and str(item)]
    return []


def first_text(payload: dict[str, Any], *fields: str) -> str:
    return next(
        (str(payload.get(field)) for field in fields if payload.get(field)),
        "",
    )


def count_missing(points: list[Any], field: str) -> int:
    return sum(not (point.payload or {}).get(field) for point in points)


def count_raw_without_keys(
    points: list[Any],
    raw_fields: tuple[str, ...],
    key_field: str,
) -> int:
    return sum(
        any((point.payload or {}).get(field) for field in raw_fields)
        and not (point.payload or {}).get(key_field)
        for point in points
    )


if __name__ == "__main__":
    raise SystemExit(main())
