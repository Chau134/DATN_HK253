from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import json
from pathlib import Path
import random
import re
from typing import Any, Callable

from run_eval import ROOT, extract_cases


EVAL_DIR = Path(__file__).resolve().parent
REVIEW_DIR = EVAL_DIR / "review"
DEFAULT_IMAGE_SOURCES = REVIEW_DIR / "image_sources.json"
DEFAULT_APPROVALS = REVIEW_DIR / "ground_truth_approvals.json"
CASES_PER_GROUP = 5
TEST_GROUPS = (
    "available-image",
    "different-color",
    "different-material",
    "specific-use",
    "external-image",
)
TEST_TYPES = {
    "available-image": "similar_style_available_image",
    "different-color": "similar_style_different_color",
    "different-material": "similar_style_different_material",
    "specific-use": "similar_style_specific_use",
    "external-image": "similar_style_external_image",
}
FIXED_ASSIGNMENTS = {
    # Reuse the four project-owner URLs that still belong to database/100.sql.
    "available-image": ("982", ""),
    "different-color": ("421", "blue"),
    "different-material": ("1290", "cotton"),
    "specific-use": ("843", "thu đông"),
}
# Preserve stable case numbering while replacing a weak visual pairing.
# 1038 (square-neck bodysuit) and its event candidate 1045 (halter bodysuit)
# were too different in silhouette. 711 and 710 are near-identical pocket
# T-shirt variants, while only 710 carries the exact "dạo phố" use-case tag.
CASE_REPLACEMENTS = {
    ("different-color", "83"): ("83", "pink"),
    ("different-color", "1035"): ("1035", "navy"),
    ("specific-use", "1038"): ("711", "dạo phố"),
}
DISABLED_SOURCE_IDS = {"1038"}
REFERENCE_IMAGE_OVERRIDES = {
    # MAIN contains two models and several garments; FLAT_1 isolates product 711.
    "711": (
        "https://pub-5a1bb641c66b47c794fbd182d1cfef7b.r2.dev/"
        "products/711/6152-05643033250-f1.jpg"
    ),
}
COLOR_LABELS_VI = {
    "beige": "be",
    "black": "đen",
    "blue": "xanh dương",
    "brown": "nâu",
    "green": "xanh lá",
    "grey": "xám",
    "multicolor": "đa màu",
    "navy": "xanh navy",
    "orange": "cam",
    "pink": "hồng",
    "purple": "tím",
    "red": "đỏ",
    "white": "trắng",
    "yellow": "vàng",
}
MATERIAL_LABELS_VI = {
    "acrylic": "acrylic",
    "cotton": "cotton",
    "denim": "denim",
    "elastane": "elastane",
    "leather": "da",
    "linen": "linen",
    "lyocell": "lyocell",
    "polyamide": "polyamide",
    "polyester": "polyester",
    "silk": "lụa",
    "viscose": "viscose",
    "wool": "len",
}
MATERIAL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(value) for value in MATERIAL_LABELS_VI) + r")\b",
    re.IGNORECASE,
)
CATEGORY_ALIASES = {
    "áo bodysuit": "áo bodysuit nữ",
    "bodysuit nữ": "áo bodysuit nữ",
    "jumpsuit": "jumpsuit nữ",
    "áo gi lê nữ": "áo gile nữ",
}


@dataclass(frozen=True)
class ReviewProduct:
    product_id: str
    product_name_vi: str
    category_vi: str
    search_attributes_vi: str
    use_cases: tuple[str, ...]
    colors: tuple[str, ...]
    materials: tuple[str, ...]
    catalog_image_url: str


@dataclass(frozen=True)
class Proposal:
    test_group: str
    test_type: str
    category_vi: str
    target_value: str
    candidates: tuple[ReviewProduct, ...]

    @property
    def signature(self) -> tuple[str, str, str]:
        return self.test_group, self.category_vi, self.target_value


@dataclass(frozen=True)
class SelectedProposal:
    proposal: Proposal
    source: ReviewProduct


def _sql_text_attributes(sql: str, key: str) -> dict[str, str]:
    pattern = re.compile(
        rf"\(\d+,(\d+),'{re.escape(key)}',NULL,'[^']*','[^']*','((?:''|[^'])*)'\)"
    )
    return {
        match.group(1): match.group(2).replace("''", "'")
        for match in pattern.finditer(sql)
    }


def _sql_direct_attributes(sql: str, key: str) -> dict[str, str]:
    pattern = re.compile(
        rf"\(\d+,(\d+),'{re.escape(key)}','((?:''|[^'])*)','[^']*','[^']*',NULL\)"
    )
    return {
        match.group(1): match.group(2).replace("''", "'")
        for match in pattern.finditer(sql)
    }


def _split_values(value: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(part.strip().casefold() for part in value.split(",") if part.strip())
    )


def _category_label(value: str) -> str:
    label = value.split(",", 1)[0].strip().casefold()
    return CATEGORY_ALIASES.get(label, label)


def extract_review_products(sql_path: Path) -> list[ReviewProduct]:
    sql = sql_path.read_text(encoding="utf-8")
    names = _sql_text_attributes(sql, "search_name_vi")
    categories = _sql_text_attributes(sql, "search_category_vi")
    attributes = _sql_text_attributes(sql, "search_attributes_vi")
    usages = _sql_text_attributes(sql, "search_use_cases_vi")
    color_families = _sql_text_attributes(sql, "color_family")
    compositions = _sql_direct_attributes(sql, "material_composition")
    image_urls = {
        case["expected_product_id"]: case["image_url"] for case in extract_cases(sql_path)
    }

    if len(names) != 100:
        raise RuntimeError(f"Expected 100 products in {sql_path}, found {len(names)}")

    products: list[ReviewProduct] = []
    for product_id in sorted(names, key=int):
        materials = tuple(
            dict.fromkeys(
                match.group(1).casefold()
                for match in MATERIAL_PATTERN.finditer(compositions.get(product_id, ""))
            )
        )
        products.append(
            ReviewProduct(
                product_id=product_id,
                product_name_vi=names[product_id],
                category_vi=_category_label(categories.get(product_id, "")),
                search_attributes_vi=attributes.get(product_id, ""),
                use_cases=_split_values(usages.get(product_id, "")),
                colors=_split_values(color_families.get(product_id, "")),
                materials=materials,
                catalog_image_url=image_urls[product_id],
            )
        )
    return products


def _attribute_proposals(
    products: list[ReviewProduct],
    *,
    test_group: str,
    values: Callable[[ReviewProduct], tuple[str, ...]],
) -> list[Proposal]:
    groups: dict[tuple[str, str], list[ReviewProduct]] = defaultdict(list)
    for product in products:
        if not product.category_vi:
            continue
        for value in values(product):
            if value:
                groups[(product.category_vi, value)].append(product)
    return [
        Proposal(
            test_group=test_group,
            test_type=TEST_TYPES[test_group],
            category_vi=category,
            target_value=value,
            candidates=tuple(sorted(group, key=lambda product: int(product.product_id))),
        )
        for (category, value), group in sorted(groups.items())
        if group
    ]


def _category_proposals(
    products: list[ReviewProduct],
    *,
    test_group: str,
) -> list[Proposal]:
    groups: dict[str, list[ReviewProduct]] = defaultdict(list)
    for product in products:
        if product.category_vi:
            groups[product.category_vi].append(product)
    return [
        Proposal(
            test_group=test_group,
            test_type=TEST_TYPES[test_group],
            category_vi=category,
            target_value="",
            candidates=tuple(sorted(group, key=lambda product: int(product.product_id))),
        )
        for category, group in sorted(groups.items())
        if len(group) >= 2
    ]


def _proposal_pools(products: list[ReviewProduct]) -> dict[str, list[Proposal]]:
    return {
        "available-image": _category_proposals(
            products, test_group="available-image"
        ),
        "different-color": _attribute_proposals(
            products,
            test_group="different-color",
            values=lambda product: product.colors,
        ),
        "different-material": _attribute_proposals(
            products,
            test_group="different-material",
            values=lambda product: product.materials,
        ),
        "specific-use": _attribute_proposals(
            products,
            test_group="specific-use",
            values=lambda product: product.use_cases,
        ),
        "external-image": _category_proposals(
            products, test_group="external-image"
        ),
    }


def _source_is_compatible(source: ReviewProduct, proposal: Proposal) -> bool:
    if source.category_vi != proposal.category_vi:
        return False
    if proposal.test_group == "different-color":
        return proposal.target_value not in source.colors
    if proposal.test_group == "different-material":
        return proposal.target_value not in source.materials
    return True


def _select_suite(
    products: list[ReviewProduct],
    *,
    seed: int,
) -> list[SelectedProposal]:
    products_by_id = {product.product_id: product for product in products}
    pools = _proposal_pools(products)
    reserved_source_ids = {
        source_id for source_id, _ in FIXED_ASSIGNMENTS.values()
    } | {
        new_source_id
        for (_, old_source_id), (new_source_id, _) in CASE_REPLACEMENTS.items()
        if new_source_id != old_source_id
    }
    used_source_ids: set[str] = set()
    selected: list[SelectedProposal] = []

    for group_index, test_group in enumerate(TEST_GROUPS):
        pool = list(pools[test_group])
        random.Random(seed + group_index).shuffle(pool)
        group_selected: list[SelectedProposal] = []
        used_signatures: set[tuple[str, str, str]] = set()
        replaceable_source_ids = {
            old_source_id
            for replacement_group, old_source_id in CASE_REPLACEMENTS
            if replacement_group == test_group
        }

        fixed = FIXED_ASSIGNMENTS.get(test_group)
        if fixed:
            source_id, target_value = fixed
            source = products_by_id.get(source_id)
            proposal = next(
                (
                    item
                    for item in pool
                    if source is not None
                    and item.category_vi == source.category_vi
                    and item.target_value == target_value
                    and _source_is_compatible(source, item)
                ),
                None,
            )
            if source is None or proposal is None:
                raise RuntimeError(
                    f"Fixed assignment is no longer feasible: "
                    f"group={test_group}, source={source_id}, target={target_value!r}"
                )
            group_selected.append(SelectedProposal(proposal=proposal, source=source))
            used_source_ids.add(source_id)
            used_signatures.add(proposal.signature)

        for proposal in pool:
            if len(group_selected) >= CASES_PER_GROUP:
                break
            if proposal.signature in used_signatures:
                continue
            source = next(
                (
                    product
                    for product in products
                        if product.product_id not in used_source_ids
                        and product.product_id not in reserved_source_ids
                        and (
                            product.product_id not in DISABLED_SOURCE_IDS
                            or product.product_id in replaceable_source_ids
                        )
                    and _source_is_compatible(product, proposal)
                ),
                None,
            )
            if source is None:
                continue
            group_selected.append(SelectedProposal(proposal=proposal, source=source))
            used_source_ids.add(source.product_id)
            used_signatures.add(proposal.signature)

        for (replacement_group, old_source_id), (
            new_source_id,
            target_value,
        ) in CASE_REPLACEMENTS.items():
            if replacement_group != test_group:
                continue
            replacement_index = next(
                (
                    index
                    for index, item in enumerate(group_selected)
                    if item.source.product_id == old_source_id
                ),
                None,
            )
            new_source = products_by_id.get(new_source_id)
            replacement_proposal = next(
                (
                    item
                    for item in pool
                    if new_source is not None
                    and item.category_vi == new_source.category_vi
                    and item.target_value == target_value
                    and _source_is_compatible(new_source, item)
                ),
                None,
            )
            if replacement_index is None or new_source is None or replacement_proposal is None:
                raise RuntimeError(
                    "Configured case replacement is no longer feasible: "
                    f"group={test_group}, old_source={old_source_id}, "
                    f"new_source={new_source_id}, target={target_value!r}"
                )
            used_source_ids.discard(old_source_id)
            used_source_ids.add(new_source_id)
            group_selected[replacement_index] = SelectedProposal(
                proposal=replacement_proposal,
                source=new_source,
            )

        if len(group_selected) != CASES_PER_GROUP:
            raise RuntimeError(
                f"Could not build {CASES_PER_GROUP} feasible cases for {test_group}; "
                f"built {len(group_selected)}"
            )
        selected.extend(group_selected)

    return selected


def _query_and_image_requirement(proposal: Proposal) -> tuple[str, str]:
    category = proposal.category_vi
    if proposal.test_group == "different-color":
        color = COLOR_LABELS_VI.get(proposal.target_value, proposal.target_value)
        return (
            f"tìm {category} có kiểu dáng giống ảnh nhưng màu {color}",
            (
                f"Ảnh phải là {category} có kiểu dáng gần candidate nhưng màu ảnh khác "
                f"màu yêu cầu '{color}'."
            ),
        )
    if proposal.test_group == "different-material":
        material = MATERIAL_LABELS_VI.get(
            proposal.target_value, proposal.target_value
        )
        return (
            f"tìm {category} có kiểu dáng giống ảnh nhưng chất liệu {material}",
            (
                f"Ảnh phải là {category} có kiểu dáng gần candidate nhưng chất liệu ảnh "
                f"khác '{material}' nếu nguồn ảnh cho phép xác minh."
            ),
        )
    if proposal.test_group == "specific-use":
        return (
            f"tìm {category} có kiểu dáng giống ảnh để {proposal.target_value}",
            (
                f"Ảnh phải là {category} có kiểu dáng gần candidate; reviewer xác nhận "
                f"candidate phù hợp mục đích '{proposal.target_value}'."
            ),
        )
    if proposal.test_group == "available-image":
        return (
            f"tìm {category} có kiểu dáng giống ảnh",
            f"Ảnh sản phẩm có sẵn; reviewer chọn các {category} có kiểu dáng tương tự.",
        )
    return (
        f"tìm {category} có kiểu dáng giống ảnh tham chiếu",
        (
            f"Ảnh tham chiếu ngoài catalog phải thể hiện rõ {category}; reviewer chọn "
            "candidate trong database có kiểu dáng tương tự."
        ),
    )


def load_image_sources(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    provided = payload.get("provided_images", {})
    if not isinstance(provided, dict):
        raise RuntimeError("image_sources.json: provided_images must be an object")
    return {
        str(product_id): str(url).strip()
        for product_id, url in provided.items()
        if str(url).strip()
    }


def load_catalog_image_source_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("catalog_image_product_ids", [])
    if not isinstance(values, list):
        raise RuntimeError(
            "image_sources.json: catalog_image_product_ids must be an array"
        )
    return {str(product_id) for product_id in values}


def load_ground_truth_approvals(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"reviewer": "", "cases": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", {})
    if not isinstance(cases, dict):
        raise RuntimeError("ground_truth_approvals.json: cases must be an object")
    return {
        "reviewer": str(payload.get("reviewer", "")).strip(),
        "cases": cases,
    }


def apply_ground_truth_approvals(
    case_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    approval_config: dict[str, Any],
) -> None:
    cases_by_id = {str(row["case_id"]): row for row in case_rows}
    approvals = approval_config.get("cases", {})
    unknown_case_ids = sorted(set(approvals) - set(cases_by_id))
    if unknown_case_ids:
        raise RuntimeError(
            f"Ground-truth approvals reference unknown cases: {unknown_case_ids}"
        )

    candidates_by_case: dict[str, set[str]] = defaultdict(set)
    for row in candidate_rows:
        candidates_by_case[str(row["case_id"])].add(
            str(row["candidate_product_id"])
        )

    reviewer = str(approval_config.get("reviewer", "")).strip()
    approved_by_case: dict[str, dict[str, int]] = {}
    for case_id, raw in approvals.items():
        if not isinstance(raw, dict):
            raise RuntimeError(f"{case_id}: approval must be an object")
        grades = {
            str(product_id): int(grade)
            for product_id, grade in raw.get("approved_grades", {}).items()
        }
        if not grades:
            raise RuntimeError(f"{case_id}: approved_grades must not be empty")
        invalid_grades = {
            product_id: grade
            for product_id, grade in grades.items()
            if grade not in {2, 3}
        }
        if invalid_grades:
            raise RuntimeError(
                f"{case_id}: approved grades must be 2 or 3: {invalid_grades}"
            )
        invalid_ids = sorted(set(grades) - candidates_by_case[case_id], key=int)
        if invalid_ids:
            raise RuntimeError(
                f"{case_id}: approved IDs are not candidates: {invalid_ids}"
            )
        case = cases_by_id[case_id]
        if not case["external_image_url"]:
            raise RuntimeError(f"{case_id}: cannot approve a case without an image")
        approved_by_case[case_id] = grades
        case["review_status"] = "APPROVED"
        case["approved_product_ids"] = "|".join(grades)
        case["reviewer"] = reviewer
        case["review_notes"] = str(raw.get("review_notes", "")).strip()

    for row in candidate_rows:
        case_id = str(row["case_id"])
        if case_id not in approved_by_case:
            continue
        product_id = str(row["candidate_product_id"])
        grade = approved_by_case[case_id].get(product_id)
        if grade is not None:
            row["review_decision"] = "APPROVE"
            row["reviewed_relevance_grade"] = grade
            row["review_notes"] = "Approved after visual query/candidate review"
        else:
            row["review_decision"] = "REJECT"
            row["reviewed_relevance_grade"] = 0
            row["review_notes"] = "Rejected after visual query/candidate review"


def build_review_manifest(
    products: list[ReviewProduct],
    *,
    image_sources: dict[str, str] | None = None,
    catalog_image_source_ids: set[str] | None = None,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    image_sources = image_sources or {}
    catalog_image_source_ids = catalog_image_source_ids or set()
    selections = _select_suite(products, seed=seed)
    case_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()

    for selection in selections:
        proposal = selection.proposal
        source = selection.source
        counters[proposal.test_group] += 1
        case_id = (
            f"hybrid-review-{proposal.test_group}-"
            f"{counters[proposal.test_group]:03d}"
        )
        query_text, image_requirement = _query_and_image_requirement(proposal)
        image_url = image_sources.get(source.product_id, "")
        candidate_ids = [product.product_id for product in proposal.candidates]
        case_rows.append(
            {
                "case_id": case_id,
                "test_group": proposal.test_group,
                "test_type": proposal.test_type,
                "query_text": query_text,
                "external_image_url": image_url,
                "image_source_product_id": source.product_id,
                "image_source_kind": (
                    "catalog_database"
                    if image_url and source.product_id in catalog_image_source_ids
                    else (
                        "user_provided_external"
                        if image_url
                        else "awaiting_user_link"
                    )
                ),
                "observed_image_category": source.category_vi,
                "observed_image_color": "|".join(source.colors),
                "observed_image_material": "|".join(source.materials),
                "image_source_notes": (
                    "Catalog image from database/100.sql"
                    if image_url and source.product_id in catalog_image_source_ids
                    else ("URL supplied by project owner" if image_url else "")
                ),
                "image_requirement": image_requirement,
                "target_category_vi": proposal.category_vi,
                "requested_color": (
                    proposal.target_value
                    if proposal.test_group == "different-color"
                    else ""
                ),
                "requested_material": (
                    proposal.target_value
                    if proposal.test_group == "different-material"
                    else ""
                ),
                "requested_use_case": (
                    proposal.target_value
                    if proposal.test_group == "specific-use"
                    else ""
                ),
                "candidate_product_ids": "|".join(candidate_ids),
                "review_status": (
                    "PENDING_GROUND_TRUTH_REVIEW" if image_url else "PENDING_IMAGE"
                ),
                "approved_product_ids": "",
                "reviewer": "",
                "review_notes": "",
            }
        )
        for product in proposal.candidates:
            candidate_rows.append(
                {
                    "case_id": case_id,
                    "test_group": proposal.test_group,
                    "candidate_product_id": product.product_id,
                    "candidate_product_name_vi": product.product_name_vi,
                    "candidate_category_vi": product.category_vi,
                    "candidate_colors": "|".join(product.colors),
                    "candidate_materials": "|".join(product.materials),
                    "candidate_attributes_vi": product.search_attributes_vi,
                    "candidate_catalog_image_url": product.catalog_image_url,
                    "metadata_relevance_grade": (
                        1
                        if proposal.test_group
                        in {"available-image", "external-image"}
                        else 2
                    ),
                    "review_decision": "PENDING",
                    "reviewed_relevance_grade": "",
                    "review_notes": "",
                }
            )
    return case_rows, candidate_rows


def validate_manifest(
    case_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    valid_product_ids: set[str],
    *,
    expected_case_count: int = CASES_PER_GROUP * len(TEST_GROUPS),
) -> dict[str, Any]:
    case_ids = [str(row["case_id"]) for row in case_rows]
    candidates_by_case: dict[str, list[str]] = defaultdict(list)
    for row in candidate_rows:
        candidates_by_case[str(row["case_id"])].append(
            str(row["candidate_product_id"])
        )

    invalid_candidate_ids = sorted(
        {
            product_id
            for product_ids in candidates_by_case.values()
            for product_id in product_ids
            if product_id not in valid_product_ids
        },
        key=int,
    )
    invalid_source_ids = sorted(
        {
            str(row["image_source_product_id"])
            for row in case_rows
            if str(row["image_source_product_id"]) not in valid_product_ids
        },
        key=int,
    )
    duplicate_sources = sorted(
        product_id
        for product_id, count in Counter(
            str(row["image_source_product_id"]) for row in case_rows
        ).items()
        if count > 1
    )
    group_counts = Counter(str(row["test_group"]) for row in case_rows)
    missing_image_cases = [
        str(row["case_id"]) for row in case_rows if not row["external_image_url"]
    ]
    summary = {
        "case_count": len(case_rows),
        "cases_per_group": CASES_PER_GROUP,
        "test_group_counts": dict(group_counts),
        "test_type_counts": dict(
            Counter(str(row["test_type"]) for row in case_rows)
        ),
        "candidate_row_count": len(candidate_rows),
        "unique_case_ids": len(case_ids) == len(set(case_ids)),
        "unique_image_source_ids": not duplicate_sources,
        "duplicate_image_source_product_ids": duplicate_sources,
        "invalid_source_product_ids": invalid_source_ids,
        "invalid_candidate_product_ids": invalid_candidate_ids,
        "cases_missing_candidates": sorted(set(case_ids) - set(candidates_by_case)),
        "provided_image_count": len(case_rows) - len(missing_image_cases),
        "missing_image_count": len(missing_image_cases),
        "missing_image_case_ids": missing_image_cases,
        "ground_truth_policy": "pending_manual_review",
        "approved_ready_case_count": sum(
            1
            for row in case_rows
            if row["review_status"] == "APPROVED"
            and row["external_image_url"]
            and row["approved_product_ids"]
        ),
    }
    summary["valid"] = (
        summary["case_count"] == expected_case_count
        and summary["unique_case_ids"]
        and summary["unique_image_source_ids"]
        and group_counts == Counter({group: CASES_PER_GROUP for group in TEST_GROUPS})
        and not invalid_source_ids
        and not invalid_candidate_ids
        and not summary["cases_missing_candidates"]
    )
    return summary


def build_missing_image_rows(
    case_rows: list[dict[str, Any]],
    products: list[ReviewProduct],
) -> list[dict[str, Any]]:
    products_by_id = {product.product_id: product for product in products}
    rows: list[dict[str, Any]] = []
    for case in case_rows:
        if case["external_image_url"]:
            continue
        source = products_by_id[str(case["image_source_product_id"])]
        rows.append(
            {
                "case_id": case["case_id"],
                "test_group": case["test_group"],
                "query_text": case["query_text"],
                "image_source_product_id": source.product_id,
                "source_product_name_vi": source.product_name_vi,
                "source_category_vi": source.category_vi,
                "catalog_image_for_reference": REFERENCE_IMAGE_OVERRIDES.get(
                    source.product_id, source.catalog_image_url
                ),
                "required_external_image_url": "",
                "image_requirement": case["image_requirement"],
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate 25 balanced hybrid cases (5 groups x 5 cases) for "
            "human ground-truth review"
        )
    )
    parser.add_argument("--sql", type=Path, default=ROOT / "database" / "100.sql")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--image-sources", type=Path, default=DEFAULT_IMAGE_SOURCES
    )
    parser.add_argument(
        "--approvals",
        type=Path,
        default=DEFAULT_APPROVALS,
        help="Optional reproducible human-review decisions.",
    )
    parser.add_argument(
        "--cases-output",
        type=Path,
        default=REVIEW_DIR / "test_cases_pending_review.csv",
    )
    parser.add_argument(
        "--candidates-output",
        type=Path,
        default=REVIEW_DIR / "ground_truth_candidates_pending_review.csv",
    )
    parser.add_argument(
        "--missing-images-output",
        type=Path,
        default=REVIEW_DIR / "missing_image_links.csv",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=REVIEW_DIR / "generation_summary.json",
    )
    args = parser.parse_args()

    products = extract_review_products(args.sql)
    image_sources = load_image_sources(args.image_sources)
    catalog_image_source_ids = load_catalog_image_source_ids(args.image_sources)
    valid_product_ids = {product.product_id for product in products}
    unknown_image_ids = sorted(set(image_sources) - valid_product_ids, key=int)
    if unknown_image_ids:
        raise RuntimeError(
            "image_sources.json contains products outside database/100.sql: "
            f"{unknown_image_ids}"
        )

    case_rows, candidate_rows = build_review_manifest(
        products,
        image_sources=image_sources,
        catalog_image_source_ids=catalog_image_source_ids,
        seed=args.seed,
    )
    approval_config = load_ground_truth_approvals(args.approvals)
    apply_ground_truth_approvals(case_rows, candidate_rows, approval_config)
    summary = validate_manifest(case_rows, candidate_rows, valid_product_ids)
    summary["unused_provided_image_product_ids"] = sorted(
        set(image_sources)
        - {str(row["image_source_product_id"]) for row in case_rows},
        key=int,
    )
    summary["catalog_image_source_count"] = sum(
        row["image_source_kind"] == "catalog_database" for row in case_rows
    )
    summary["reviewed_case_count"] = len(approval_config["cases"])
    summary["ground_truth_policy"] = (
        "versioned_human_review"
        if approval_config["cases"]
        else "pending_manual_review"
    )
    missing_rows = build_missing_image_rows(case_rows, products)

    write_csv(args.cases_output, case_rows)
    write_csv(args.candidates_output, candidate_rows)
    write_csv(args.missing_images_output, missing_rows)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
