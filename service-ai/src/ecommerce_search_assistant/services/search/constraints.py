from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ecommerce_search_assistant.schemas.search import SearchFilter
from ecommerce_search_assistant.services.search.filtering import (
    merge_filters,
    merge_missing_filters,
    normalize_filter_values,
)

ConstraintSource = Literal["explicit", "rule", "llm"]
ConstraintMode = Literal["hard", "soft"]

_FILTER_FIELDS = tuple(SearchFilter.model_fields)
_DETERMINISTIC_HARD_FIELDS = frozenset({"min_price", "max_price", "sizes"})
_RECOVERY_RETAINED_HARD_FIELDS = frozenset({"min_price", "max_price", "gender", "colors"})
# A dictionary (exact alias) category match is precise enough to hard-filter,
# but only when it is unambiguous. Fuzzy matches and multi-category queries stay
# soft so a wrong guess never drops the correct product entirely.
_HARD_CATEGORY_MIN_CONFIDENCE = 0.9


@dataclass(frozen=True)
class ResolvedConstraint:
    field: str
    value: object
    source: ConstraintSource
    confidence: float
    mode: ConstraintMode
    match_type: str | None = None


@dataclass(frozen=True)
class ResolvedSearchConstraints:
    """Internal filter model that keeps request and inferred provenance separate."""

    constraints: tuple[ResolvedConstraint, ...] = ()
    hard_filters: SearchFilter | None = None
    explicit_hard_filters: SearchFilter | None = None
    inferred_filters: SearchFilter | None = None
    recovery_filters: SearchFilter | None = None
    soft_filters: SearchFilter | None = None
    response_filters: SearchFilter | None = None
    downgraded_fields: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_inferred_hard_filters(self) -> bool:
        explicit_fields = set(_filter_data(self.explicit_hard_filters))
        return any(
            constraint.mode == "hard"
            and constraint.source != "explicit"
            and constraint.field not in explicit_fields
            for constraint in self.constraints
        )

    @property
    def has_recoverable_inferred_hard_filters(self) -> bool:
        """Return whether recovery would actually relax an inferred constraint."""

        recovery_fields = set(_filter_data(self.recovery_filters))
        return any(
            constraint.mode == "hard"
            and constraint.source != "explicit"
            and constraint.field not in recovery_fields
            for constraint in self.constraints
        )


def resolve_search_constraints(
    *,
    rule_filters: SearchFilter | None,
    llm_filters: SearchFilter | None,
    explicit_filters: SearchFilter | None,
    confidences: dict[str, float] | None = None,
    match_sources: dict[str, str] | None = None,
    category_ambiguous: bool = False,
    allow_category_hard: bool = False,
    allow_color_hard: bool = False,
) -> ResolvedSearchConstraints:
    """Resolve filters without allowing inferred metadata to become accidental hard constraints."""

    confidences = confidences or {}
    match_sources = match_sources or {}
    normalized_rule = normalize_filter_values(rule_filters)
    normalized_llm = normalize_filter_values(llm_filters)
    normalized_explicit = normalize_filter_values(explicit_filters)

    # Rule extraction has priority over the LLM, matching the previous merge policy.
    inferred = merge_missing_filters(normalized_rule, normalized_llm)
    response_filters = merge_filters(inferred, normalized_explicit)
    explicit_data = _filter_data(normalized_explicit)
    rule_data = _filter_data(normalized_rule)
    llm_data = _filter_data(normalized_llm)

    constraints: list[ResolvedConstraint] = []
    hard_data = dict(explicit_data)
    soft_data: dict[str, object] = {}
    downgraded: list[str] = []

    for field_name in _FILTER_FIELDS:
        if field_name in explicit_data:
            constraints.append(
                ResolvedConstraint(
                    field_name,
                    explicit_data[field_name],
                    "explicit",
                    1.0,
                    "hard",
                    "explicit",
                )
            )
            continue

        if field_name in rule_data:
            value = rule_data[field_name]
            source: ConstraintSource = "rule"
        elif field_name in llm_data:
            value = llm_data[field_name]
            source = "llm"
        else:
            continue

        confidence_key = _confidence_key(field_name)
        confidence = float(confidences.get(confidence_key, 0.65 if source == "llm" else 0.0))
        deterministic = (
            field_name in _DETERMINISTIC_HARD_FIELDS
            and source == "rule"
            and match_sources.get(confidence_key) == "regex"
            and confidence >= 0.9
        )
        # An unambiguous dictionary category match is precise enough to hard-filter
        # ("áo sơ mi" should not return tank tops), while a wrong extraction is made
        # safe by the recovery pass, which relaxes inferred hard filters back to a
        # soft boost when the filtered result set is too small.
        category_hard = (
            allow_category_hard
            and field_name == "category"
            and source == "rule"
            and not category_ambiguous
            and match_sources.get(confidence_key)
            in {"dictionary", "exact", "alias", "typo"}
            and confidence >= _HARD_CATEGORY_MIN_CONFIDENCE
        )
        # A color found by the deterministic dictionary is literal user intent
        # (for example "màu trắng" or "chàm đậm"). Apply it before vector
        # retrieval so a broad embedding candidate pool cannot discard the exact
        # shade. Colors supplied only by the LLM remain soft.
        dictionary_color_hard = (
            allow_color_hard
            and field_name == "colors"
            and source == "rule"
            and match_sources.get(confidence_key) == "dictionary"
            and confidence >= 0.95
        )
        mode: ConstraintMode = (
            "hard" if (deterministic or category_hard or dictionary_color_hard) else "soft"
        )
        constraints.append(
            ResolvedConstraint(
                field_name,
                value,
                source,
                confidence,
                mode,
                match_sources.get(confidence_key),
            )
        )
        if mode == "hard":
            hard_data[field_name] = value
        if category_hard or dictionary_color_hard:
            # Keep trusted hard constraints in the soft set too so their ranking
            # signal remains available to score the filtered candidate set.
            soft_data[field_name] = value
        elif mode != "hard":
            soft_data[field_name] = value
            downgraded.append(field_name)

    recovery_data = dict(explicit_data)
    for constraint in constraints:
        if (
            constraint.mode == "hard"
            and constraint.source != "explicit"
            and (
                constraint.field in _RECOVERY_RETAINED_HARD_FIELDS
                # Exact category phrases are user intent, not weak metadata.
                # Keep "quần dài", "áo thun", ... during recovery so a small
                # matching result set cannot be flooded by other product types.
                or (
                    constraint.field == "category"
                    and constraint.match_type in {"dictionary", "exact", "alias"}
                )
            )
        ):
            recovery_data[constraint.field] = constraint.value

    if response_filters and response_filters.color_match_mode == "all":
        if "colors" in hard_data:
            hard_data["color_match_mode"] = "all"
        if "colors" in recovery_data:
            recovery_data["color_match_mode"] = "all"

    return ResolvedSearchConstraints(
        constraints=tuple(constraints),
        hard_filters=_make_filter(hard_data),
        explicit_hard_filters=_make_filter(explicit_data),
        inferred_filters=_make_filter(
            {
                field_name: value
                for field_name, value in _filter_data(inferred).items()
                if field_name not in explicit_data
            }
        ),
        recovery_filters=_make_filter(recovery_data),
        soft_filters=_make_filter(soft_data),
        response_filters=response_filters,
        downgraded_fields=tuple(downgraded),
    )


def _confidence_key(field_name: str) -> str:
    return {"colors": "color", "sizes": "size", "min_price": "price", "max_price": "price"}.get(
        field_name,
        field_name,
    )


def _filter_data(filters: SearchFilter | None) -> dict[str, object]:
    return filters.model_dump(exclude_none=True) if filters is not None else {}


def _make_filter(data: dict[str, object]) -> SearchFilter | None:
    return SearchFilter(**data) if data else None
