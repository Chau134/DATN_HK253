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
from ecommerce_search_assistant.services.search.canonicalization import (
    CANONICALIZER_VERSION,
    catalog_product_color_keys,
)


def main() -> int:
    args = parse_args()
    settings = get_settings()
    collections = args.collection or [
        settings.qdrant_text_collection,
        settings.qdrant_image_collection,
    ]
    client = build_qdrant_client(settings)

    if args.rollback_dir:
        results = [
            rollback_collection(
                client,
                collection,
                args.rollback_dir / backup_name(collection),
                args.batch_size,
            )
            for collection in collections
        ]
        print(json.dumps({"mode": "rollback", "collections": results}, ensure_ascii=False, indent=2))
        return 0

    results: list[dict[str, Any]] = []
    for collection in collections:
        points = list(scroll_points(client, collection, args.batch_size))
        result, changes = audit_collection(
            collection,
            points,
            expected_products=args.expected_products,
        )
        result["mode"] = "apply" if args.apply else "dry-run"
        result["vectors_reembedded"] = 0

        if args.apply:
            if args.backup_dir is None:
                raise RuntimeError("--backup-dir is required with --apply")
            backup = args.backup_dir.resolve() / backup_name(collection)
            result["backup"] = str(backup)
            result["backup_sha256"] = write_backup(backup, collection, changes)
            apply_changes(client, collection, changes, args.batch_size)
            after_points = list(scroll_points(client, collection, args.batch_size))
            after, remaining = audit_collection(
                collection,
                after_points,
                expected_products=args.expected_products,
            )
            result["after"] = after
            result["remaining_changed_points"] = len(remaining)
            if remaining:
                raise RuntimeError(
                    f"{collection}: migration did not converge; "
                    f"{len(remaining)} points still differ"
                )
        results.append(result)

    print(json.dumps({"collections": results}, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit or repair color_keys in the configured Qdrant text and image "
            "collections without changing vectors. Dry-run is the default."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback-dir", type=Path)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument(
        "--collection",
        action="append",
        help="Collection to process; repeat for multiple collections.",
    )
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


def target_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "color_keys": catalog_product_color_keys(
            payload.get("base_colour"), payload.get("base_colour_vi")
        ),
        "canonicalizer_version": CANONICALIZER_VERSION,
    }


def audit_collection(
    collection: str,
    points: list[Any],
    *,
    expected_products: int,
) -> tuple[dict[str, Any], list[tuple[Any, dict[str, Any], dict[str, Any]]]]:
    product_ids = [
        str((point.payload or {}).get("product_id") or "").strip()
        for point in points
    ]
    unique_products = {product_id for product_id in product_ids if product_id}
    if len(unique_products) != expected_products or any(not item for item in product_ids):
        raise RuntimeError(
            f"{collection}: expected {expected_products} distinct products with no "
            f"blank ids, got points={len(points)}, "
            f"distinct_products={len(unique_products)}, "
            f"blank_product_ids={sum(not item for item in product_ids)}"
        )

    changes: list[tuple[Any, dict[str, Any], dict[str, Any]]] = []
    transitions: Counter[str] = Counter()
    color_changed = 0
    for point in points:
        payload = dict(point.payload or {})
        target = target_payload(payload)
        current_colors = payload.get("color_keys")
        target_colors = target["color_keys"]
        crosses_white_cream_boundary = (
            "white" in (current_colors or [])
            and "cream" in target_colors
            and "white" not in target_colors
        ) or (
            "cream" in (current_colors or [])
            and "white" in target_colors
            and "cream" not in target_colors
        )
        if not crosses_white_cream_boundary:
            continue
        old = {
            "color_keys": payload.get("color_keys"),
            "canonicalizer_version": payload.get("canonicalizer_version"),
        }
        changes.append((point.id, old, target))
        if old["color_keys"] != target["color_keys"]:
            color_changed += 1
            transitions[
                f"{json.dumps(old['color_keys'], ensure_ascii=False)} -> "
                f"{json.dumps(target['color_keys'], ensure_ascii=False)}"
            ] += 1

    result = {
        "collection": collection,
        "scanned_points": len(points),
        "distinct_products": len(unique_products),
        "blank_product_ids": sum(not item for item in product_ids),
        "changed_points": len(changes),
        "color_changed_points": color_changed,
        "color_transitions": dict(transitions.most_common()),
        "target_canonicalizer_version": CANONICALIZER_VERSION,
    }
    return result, changes


def apply_changes(
    client: Any,
    collection: str,
    changes: list[tuple[Any, dict[str, Any], dict[str, Any]]],
    batch_size: int,
) -> None:
    for start in range(0, len(changes), batch_size):
        operations = [
            models.SetPayloadOperation(
                set_payload=models.SetPayload(payload=target, points=[point_id])
            )
            for point_id, _, target in changes[start : start + batch_size]
        ]
        if operations:
            client.batch_update_points(
                collection_name=collection,
                update_operations=operations,
                wait=True,
            )


def backup_name(collection: str) -> str:
    safe = "".join(character if character.isalnum() or character in "-_." else "_" for character in collection)
    return f"{safe}.color-keys.jsonl"


def write_backup(
    path: Path,
    collection: str,
    changes: list[tuple[Any, dict[str, Any], dict[str, Any]]],
) -> str:
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
                    "point_count": len(changes),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )
        for point_id, old, _ in changes:
            handle.write(
                json.dumps(
                    {"type": "point", "point_id": str(point_id), "payload": old},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rollback_collection(
    client: Any,
    collection: str,
    path: Path,
    batch_size: int,
) -> dict[str, Any]:
    manifest: dict[str, Any] | None = None
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("type") == "manifest":
                manifest = record
            elif record.get("type") == "point":
                records.append(record)
    if manifest is None or manifest.get("collection") != collection:
        raise RuntimeError(f"{path}: backup manifest does not match {collection}")
    if len(records) != int(manifest.get("point_count", -1)):
        raise RuntimeError(f"{path}: backup point count does not match manifest")

    for start in range(0, len(records), batch_size):
        operations = [
            models.SetPayloadOperation(
                set_payload=models.SetPayload(
                    payload=record["payload"],
                    points=[record["point_id"]],
                )
            )
            for record in records[start : start + batch_size]
        ]
        if operations:
            client.batch_update_points(
                collection_name=collection,
                update_operations=operations,
                wait=True,
            )
    return {
        "collection": collection,
        "restored_points": len(records),
        "backup": str(path.resolve()),
        "vectors_reembedded": 0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
