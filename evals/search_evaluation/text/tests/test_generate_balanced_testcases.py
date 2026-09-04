from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "07_generate_balanced_testcases.py"
SPEC = importlib.util.spec_from_file_location("text_generate_balanced_testcases", SCRIPT_PATH)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def _product(**overrides: str) -> dict[str, str]:
    product = {
        "product_id": "1",
        "product_name": "Áo yếm trắng",
        "category": "Áo hai dây, áo sát nách & áo yếm",
        "brand": "Zara",
        "color": "Trắng / Cam",
        "material": "48% Cotton, 43% Polyester, 9% Sợi co giãn (Elastane)",
        "gender": "Nữ",
        "price": "599000",
        "usage": "dạo phố, đi làm",
        "is_active": "true",
    }
    product.update(overrides)
    return product


def test_material_facets_are_components_instead_of_the_raw_composition() -> None:
    assert GENERATOR.facet_values(_product(), "material") == [
        "Cotton",
        "Polyester",
        "Elastane",
    ]


def test_color_and_usage_facets_are_split_explicitly() -> None:
    assert GENERATOR.facet_values(_product(), "color") == ["Trắng", "Cam"]
    assert GENERATOR.facet_values(_product(), "usage") == ["dạo phố", "đi làm"]


def test_facet_all_requires_every_selected_attribute() -> None:
    selected = {"material": "Cotton", "usage": "đi làm", "color": "Trắng"}

    assert GENERATOR.matches_facets(
        _product(),
        "Áo hai dây, áo sát nách & áo yếm",
        selected,
    )
    assert not GENERATOR.matches_facets(
        _product(material="100% Polyester"),
        "Áo hai dây, áo sát nách & áo yếm",
        selected,
    )
