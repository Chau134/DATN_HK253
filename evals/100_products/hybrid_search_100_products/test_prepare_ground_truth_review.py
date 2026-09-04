from collections import Counter
from pathlib import Path

from prepare_ground_truth_review import (
    CASES_PER_GROUP,
    FIXED_ASSIGNMENTS,
    TEST_GROUPS,
    build_missing_image_rows,
    build_review_manifest,
    extract_review_products,
    load_catalog_image_source_ids,
    load_image_sources,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evals" / "hybrid_search_100_products"


def _products():
    return extract_review_products(ROOT / "database" / "100.sql")


def test_database_snapshot_generates_five_cases_per_group() -> None:
    products = _products()
    cases, candidates = build_review_manifest(products)
    summary = validate_manifest(
        cases,
        candidates,
        {product.product_id for product in products},
    )

    assert len(products) == 100
    assert len(cases) == 25
    assert summary["valid"] is True
    assert summary["test_group_counts"] == {
        group: CASES_PER_GROUP for group in TEST_GROUPS
    }
    assert len({case["image_source_product_id"] for case in cases}) == 25
    assert all(case["review_status"] == "PENDING_IMAGE" for case in cases)
    assert all(not case["external_image_url"] for case in cases)


def test_complete_image_config_makes_all_cases_ready_for_ground_truth_review() -> None:
    products = _products()
    source_path = EVAL_DIR / "review" / "image_sources.json"
    image_sources = load_image_sources(source_path)
    catalog_source_ids = load_catalog_image_source_ids(source_path)
    cases, candidates = build_review_manifest(
        products,
        image_sources=image_sources,
        catalog_image_source_ids=catalog_source_ids,
    )
    summary = validate_manifest(
        cases,
        candidates,
        {product.product_id for product in products},
    )
    linked = [case for case in cases if case["external_image_url"]]

    assert summary["valid"] is True
    assert summary["provided_image_count"] == 25
    assert summary["missing_image_count"] == 0
    assert {case["image_source_product_id"] for case in linked} == set(image_sources)
    assert len({case["test_group"] for case in linked}) == 5
    assert {
        case["image_source_product_id"]
        for case in linked
        if case["image_source_kind"] == "catalog_database"
    } == catalog_source_ids
    assert all(
        case["review_status"] == "PENDING_GROUND_TRUTH_REVIEW"
        for case in linked
    )


def test_fixed_color_and_material_sources_do_not_match_requested_attribute() -> None:
    products = _products()
    products_by_id = {product.product_id: product for product in products}
    cases, _ = build_review_manifest(products)

    for group in ("different-color", "different-material"):
        source_id, _ = FIXED_ASSIGNMENTS[group]
        case = next(
            row for row in cases if row["image_source_product_id"] == source_id
        )
        source = products_by_id[source_id]
        if group == "different-color":
            assert case["requested_color"] not in source.colors
        else:
            assert case["requested_material"] not in source.materials


def test_weak_specific_use_bodysuit_case_is_replaced_by_similar_tshirt_pair() -> None:
    products = _products()
    cases, _ = build_review_manifest(products)
    replacement = next(
        case for case in cases if case["case_id"] == "hybrid-review-specific-use-004"
    )

    assert replacement["image_source_product_id"] == "711"
    assert replacement["requested_use_case"] == "dạo phố"
    assert replacement["target_category_vi"] == "áo thun nữ"
    assert "710" in replacement["candidate_product_ids"].split("|")
    assert all(case["image_source_product_id"] != "1038" for case in cases)


def test_weak_color_targets_are_replaced_with_visually_valid_targets() -> None:
    products = _products()
    cases, _ = build_review_manifest(products)
    by_source = {case["image_source_product_id"]: case for case in cases}

    assert by_source["83"]["requested_color"] == "pink"
    assert "84" in by_source["83"]["candidate_product_ids"].split("|")
    assert by_source["1035"]["requested_color"] == "navy"
    assert by_source["1035"]["candidate_product_ids"] == "1043"


def test_every_candidate_and_source_belongs_to_current_database() -> None:
    products = _products()
    valid_ids = {product.product_id for product in products}
    cases, candidates = build_review_manifest(products)

    assert {case["image_source_product_id"] for case in cases} <= valid_ids
    assert {row["candidate_product_id"] for row in candidates} <= valid_ids
    assert not any(
        case["image_source_product_id"] in case["candidate_product_ids"].split("|")
        for case in cases
        if case["test_group"] in {"different-color", "different-material"}
    )


def test_missing_image_export_contains_one_row_per_unlinked_case() -> None:
    products = _products()
    image_sources = {
        product_id: url
        for product_id, url in load_image_sources(
            EVAL_DIR / "review" / "image_sources.json"
        ).items()
        if product_id in {"421", "843", "982", "1290"}
    }
    cases, _ = build_review_manifest(products, image_sources=image_sources)
    missing = build_missing_image_rows(cases, products)

    assert len(missing) == 21
    assert len({row["image_source_product_id"] for row in missing}) == 21
    assert Counter(row["test_group"] for row in missing) == {
        "available-image": 4,
        "different-color": 4,
        "different-material": 4,
        "specific-use": 4,
        "external-image": 5,
    }
    assert all(row["catalog_image_for_reference"] for row in missing)
