from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "migrate_text_payload_v7_1000.py"
SPEC = importlib.util.spec_from_file_location("migrate_text_payload_v7_1000", SCRIPT)
assert SPEC and SPEC.loader
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def payload(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "product_id": "1",
        "brand_name": "Zara",
        "base_colour": "Aubergine",
        "base_colour_vi": "Tím cà",
        "material": "95% Cotton, 5% Elastane",
        "material_vi": "95% Cotton, 5% Sợi co giãn (Elastane)",
        "gender": "Women",
        "gender_vi": "Nữ",
        "season": "All Season",
        "season_vi": "Quanh năm",
        "product_usage": "casual outing, daily wear",
        "product_usage_vi": "dạo phố, hằng ngày",
        "source_category_keys": ["bodysuit"],
        "category_keys": ["bodysuit"],
        "normalized_title": "aubergine bodysuit long sleeve",
        "normalized_title_vi": "bodysuit mau tim ca tay dai",
        "option_value": ["M"],
        "unified_size": ["M"],
        "metadata_schema_version": 6,
    }
    value.update(overrides)
    return value


def test_payload_update_bridges_legacy_color_and_populates_v7_keys() -> None:
    update = MIGRATION.payload_update(payload())

    assert "purple" in update["color_keys"]
    assert update["material_keys"] == ["cotton", "elastane"]
    assert {"streetwear", "casual"}.intersection(update["use_case_keys"])
    assert update["audience_keys"] == ["women"]
    assert update["metadata_schema_version"] == 7


def test_payload_update_is_idempotent_for_canonical_fields() -> None:
    original = payload()
    first = MIGRATION.payload_update(original)
    second = MIGRATION.payload_update({**original, **first})

    assert second == first


def test_backup_can_be_used_by_rollback(tmp_path: Path) -> None:
    points = [SimpleNamespace(id="point-1", payload=payload())]
    backup = tmp_path / "payload.jsonl"
    digest = MIGRATION.write_backup(backup, "products", points)
    client = SimpleNamespace(calls=[])

    def batch_update_points(**kwargs: object) -> None:
        client.calls.append(kwargs)

    client.batch_update_points = batch_update_points

    assert len(digest) == 64
    assert MIGRATION.rollback(client, "products", backup, 128) == 0
    assert len(client.calls) == 1
    operation = client.calls[0]["update_operations"][0]
    assert operation.overwrite_payload.payload["product_id"] == "1"
    manifest = json.loads(backup.read_text(encoding="utf-8").splitlines()[0])
    assert manifest["point_count"] == 1
