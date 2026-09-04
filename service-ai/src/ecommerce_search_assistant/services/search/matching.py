from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from collections.abc import Mapping


_EXCLUDED_TOKENS = {"be", "den", "m", "nam", "nu", "s"}


@dataclass(frozen=True)
class FuzzyMatch:
    value: str | None = None
    query_term: str | None = None
    alias: str | None = None
    confidence: float = 0.0
    ambiguous: bool = False


def fuzzy_alias_match(
    text: str,
    aliases: Mapping[str, str],
    *,
    threshold: float = 0.88,
    ambiguity_margin: float = 0.03,
) -> FuzzyMatch:
    max_words = max((len(alias.split()) for alias in aliases), default=1)
    spans = _query_spans(text, max_words)
    best_by_value: dict[str, tuple[float, str, str]] = {}
    for span in spans:
        for alias, value in aliases.items():
            if abs(len(span.split()) - len(alias.split())) > 1:
                continue
            score = SequenceMatcher(None, span, alias).ratio()
            if score > best_by_value.get(value, (0.0, "", ""))[0]:
                best_by_value[value] = (score, span, alias)

    ranked = sorted(
        ((score, value, span, alias) for value, (score, span, alias) in best_by_value.items()),
        reverse=True,
    )
    if not ranked or ranked[0][0] < threshold:
        return FuzzyMatch()
    score, value, span, alias = ranked[0]
    if len(ranked) > 1 and ranked[1][0] >= threshold and score - ranked[1][0] < ambiguity_margin:
        return FuzzyMatch(query_term=span, alias=alias, confidence=score, ambiguous=True)
    return FuzzyMatch(value=value, query_term=span, alias=alias, confidence=score)


def _query_spans(text: str, max_words: int) -> list[str]:
    words = [word for word in text.split() if word.isalpha()]
    spans: list[str] = []
    for start in range(len(words)):
        for width in range(1, min(max_words, len(words) - start) + 1):
            span = " ".join(words[start : start + width])
            if len(span) > 3 and span not in _EXCLUDED_TOKENS:
                spans.append(span)
    return spans
