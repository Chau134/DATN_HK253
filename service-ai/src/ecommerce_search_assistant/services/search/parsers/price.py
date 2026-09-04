from __future__ import annotations

from dataclasses import dataclass, field
import re


_UNIT = r"k|nghin|ngan|tr|trieu|m|million|d|dong|vnd"
_AMOUNT = rf"(?:\d+\s*m\s*\d{{1,3}}|\d+(?:[.,]\d+)?\s*(?:{_UNIT})?)"
_RANGE_PATTERN = re.compile(
    rf"(?<![a-z0-9])(?:tu\s+)?(?P<first>{_AMOUNT})\s*(?:-|den|toi|to)\s*"
    rf"(?P<second>{_AMOUNT})(?![a-z0-9])"
)
_MAX_PREFIX_PATTERN = re.compile(
    rf"(?:duoi(?:\s+tam)?|toi da|max|under|below|less than|nho hon|khong qua)\s*"
    rf"(?:tam|khoang)?\s*(?P<amount>{_AMOUNT})(?![a-z0-9])"
)
_MAX_SUFFIX_PATTERN = re.compile(
    rf"(?<![a-z0-9])(?P<amount>{_AMOUNT})\s*(?:tro xuong|do lai|or less)(?![a-z0-9])"
)
_MIN_PREFIX_PATTERN = re.compile(
    rf"(?:tren|tu|toi thieu|min|hon|lon hon)\s*(?P<amount>{_AMOUNT})(?![a-z0-9])"
)
_MIN_SUFFIX_PATTERN = re.compile(
    rf"(?<![a-z0-9])(?P<amount>{_AMOUNT})\s*(?:tro len|or more)(?![a-z0-9])"
)
_AROUND_PATTERN = re.compile(
    rf"(?:khoang|tam|around|about)\s*(?P<amount>{_AMOUNT})(?![a-z0-9])"
)
_EXPLICIT_AMOUNT_PATTERN = re.compile(
    rf"(?<![a-z0-9])(?:\d+\s*m\s*\d{{1,3}}|\d+(?:[.,]\d+)?\s*(?:{_UNIT}))(?![a-z0-9])"
)
_MIXED_MILLION_PATTERN = re.compile(r"(?P<whole>\d+)\s*m\s*(?P<fraction>\d{1,3})")
_STANDARD_AMOUNT_PATTERN = re.compile(rf"(?P<number>\d+(?:[.,]\d+)?)\s*(?P<unit>{_UNIT})?")


_WORD_NUMBER_VALUES = {
    'mot': 1,
    'hai': 2,
    'ba': 3,
    'bon': 4,
    'tu': 4,
    'nam': 5,
    'sau': 6,
    'bay': 7,
    'tam': 8,
    'chin': 9,
    'muoi': 10,
}
_WORD_NUMBER = '|'.join(_WORD_NUMBER_VALUES)
_WORD_MILLION_PATTERN = re.compile(
    rf'\b(?P<number>{_WORD_NUMBER})\s+trieu\b'
)
_WORD_HUNDRED_PATTERN = re.compile(
    rf'\b(?P<number>{_WORD_NUMBER})\s+tram(?P<unit>\s+(?:nghin|ngan))?\b'
)
_WORD_RANGE_START_PATTERN = re.compile(
    rf'\b(?P<number>{_WORD_NUMBER})\s+(?P<separator>den|toi|to)\s+(?=\d)'
)


@dataclass(frozen=True)
class PriceExtraction:
    min_price: float | None = None
    max_price: float | None = None
    matched_terms: tuple[str, ...] = ()
    confidence: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


def normalize_word_price_amounts(text: str) -> str:
    normalized = re.sub(r'\bnua\s+trieu\b', '500 nghin', text.casefold())
    normalized = _WORD_MILLION_PATTERN.sub(
        lambda match: str(_WORD_NUMBER_VALUES[match.group('number')]) + ' trieu',
        normalized,
    )
    normalized = _WORD_HUNDRED_PATTERN.sub(
        lambda match: (
            str(_WORD_NUMBER_VALUES[match.group('number')] * 100)
            + (match.group('unit') or '')
        ),
        normalized,
    )
    return _WORD_RANGE_START_PATTERN.sub(
        lambda match: (
            str(_WORD_NUMBER_VALUES[match.group('number')])
            + ' '
            + match.group('separator')
            + ' '
        ),
        normalized,
    )


def extract_price(text: str) -> PriceExtraction:
    normalized_text = normalize_word_price_amounts(text)
    metadata: dict[str, object] = {}
    matched_terms: list[str] = []
    confidence = 0.0
    min_price: float | None = None
    max_price: float | None = None

    range_match = _RANGE_PATTERN.search(normalized_text)
    if range_match:
        first = range_match.group("first")
        second = range_match.group("second")
        first_unit = _amount_unit(first)
        second_unit = _amount_unit(second)
        min_price = parse_price_amount(first, fallback_unit=second_unit)
        max_price = parse_price_amount(second, fallback_unit=first_unit)
        matched_terms.append(range_match.group(0))
        confidence = 0.95
    else:
        max_match = _MAX_PREFIX_PATTERN.search(normalized_text) or _MAX_SUFFIX_PATTERN.search(normalized_text)
        min_match = _MIN_PREFIX_PATTERN.search(normalized_text) or _MIN_SUFFIX_PATTERN.search(normalized_text)
        around_match = _AROUND_PATTERN.search(normalized_text)
        if max_match:
            max_price = parse_price_amount(max_match.group("amount"))
            matched_terms.append(max_match.group(0))
            confidence = max(confidence, 0.92)
        if min_match:
            min_price = parse_price_amount(min_match.group("amount"))
            matched_terms.append(min_match.group(0))
            confidence = max(confidence, 0.9)
        if around_match and min_price is None and max_price is None:
            amount = parse_price_amount(around_match.group("amount"))
            min_price, max_price = amount * 0.8, amount * 1.2
            matched_terms.append(around_match.group(0))
            metadata["price_segment"] = "around"
            confidence = 0.75
        if min_price is None and max_price is None:
            standalone = _EXPLICIT_AMOUNT_PATTERN.search(normalized_text)
            if standalone:
                amount = parse_price_amount(standalone.group(0))
                min_price, max_price = amount * 0.8, amount * 1.2
                matched_terms.append(standalone.group(0))
                metadata["price_segment"] = "around"
                confidence = 0.65

    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price
        metadata["price_range_swapped"] = True
    return PriceExtraction(min_price, max_price, tuple(matched_terms), confidence, metadata)


def parse_price_amount(value: str, *, fallback_unit: str | None = None) -> float:
    compact = value.strip().casefold()
    mixed_match = _MIXED_MILLION_PATTERN.fullmatch(compact)
    if mixed_match:
        fraction = mixed_match.group("fraction")
        return (float(mixed_match.group("whole")) + int(fraction) / (10 ** len(fraction))) * 1_000_000

    match = _STANDARD_AMOUNT_PATTERN.fullmatch(compact)
    if match is None:
        raise ValueError(f"Unsupported price amount: {value}")
    unit = match.group("unit") or fallback_unit
    number = _parse_number(match.group("number"), unit)
    if unit in {"k", "nghin", "ngan"}:
        return number * 1_000
    if unit in {"tr", "trieu", "m", "million"}:
        return number * 1_000_000
    if unit is None and number < 1_000:
        return number * 1_000
    return number


def _parse_number(value: str, unit: str | None) -> float:
    if unit in {"d", "dong", "vnd", None} and re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", value):
        return float(re.sub(r"[.,]", "", value))
    return float(value.replace(",", "."))


def _amount_unit(value: str) -> str | None:
    if _MIXED_MILLION_PATTERN.fullmatch(value.strip().casefold()):
        return "m"
    match = _STANDARD_AMOUNT_PATTERN.fullmatch(value.strip().casefold())
    return match.group("unit") if match else None
