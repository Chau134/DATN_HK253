from __future__ import annotations

from dataclasses import dataclass
import re


_ALPHA_SIZE = r"xxs|xs|s|m|l|xl|xxl|xxxl"
_NAMED_PATTERN = re.compile(r"(?<![a-z0-9])(?:one[ -]?size|free[ -]?size)(?![a-z0-9])")
_PREFIXED_PATTERN = re.compile(
    rf"(?<![a-z0-9])(?:size|sz|co)\s*[:#-]?\s*(?P<size>{_ALPHA_SIZE}|\d{{2,3}})(?![a-z0-9])"
)
_ALPHA_PATTERN = re.compile(rf"(?<![a-z0-9])(?:{_ALPHA_SIZE})(?![a-z0-9])")
_NUMERIC_PATTERN = re.compile(r"(?<![a-z0-9.,])(?:2[0-9]|[3-5][0-9]|60)(?![a-z0-9.,])")
_VALID_PATTERN = re.compile(rf"(?:{_ALPHA_SIZE}|\d{{2,3}}|one[ -]?size|free[ -]?size)")


@dataclass(frozen=True)
class SizeExtraction:
    values: tuple[str, ...] = ()
    matched_terms: tuple[str, ...] = ()
    confidence: float = 0.0


def extract_sizes(text: str) -> SizeExtraction:
    normalized_text = text.casefold()
    values: list[str] = []
    matched_terms: list[str] = []
    occupied: list[tuple[int, int]] = []

    for pattern in (_NAMED_PATTERN, _PREFIXED_PATTERN):
        for match in pattern.finditer(normalized_text):
            raw_value = match.groupdict().get("size") or match.group(0)
            values.append(_normalize_size(raw_value))
            matched_terms.append(match.group(0))
            occupied.append(match.span())

    for pattern in (_ALPHA_PATTERN, _NUMERIC_PATTERN):
        for match in pattern.finditer(normalized_text):
            if any(start <= match.start() and match.end() <= end for start, end in occupied):
                continue
            values.append(_normalize_size(match.group(0)))
            matched_terms.append(match.group(0))

    return SizeExtraction(
        tuple(dict.fromkeys(values)),
        tuple(dict.fromkeys(matched_terms)),
        0.9 if values else 0.0,
    )


def is_valid_size(value: str) -> bool:
    return _VALID_PATTERN.fullmatch(value.strip().casefold()) is not None


def _normalize_size(value: str) -> str:
    normalized = re.sub(r"[ -]+", " ", value.strip().casefold())
    return "one size" if normalized in {"one size", "free size"} else normalized
