from __future__ import annotations

import re
import unicodedata


_MOJIBAKE_MARKERS = ("Ã", "Ä", "Æ", "á»", "áº")


def normalize_query_text(value: str | None) -> str:
    text = _normalize_unicode(value)
    text = text.replace("₫", " d ")
    text = re.sub(r"[/;:_]+", " ", text)
    text = re.sub(r"(?<=\D)-(?=\D)", " ", text)
    text = re.sub(r"(?<!\d)[,.]+|[,.]+(?!\d)", " ", text)
    text = re.sub(r"[^a-z0-9&.,+\-\s]+", " ", text)
    text = re.sub(r"\bshoe\b", "shoes", text)
    text = re.sub(r"\bsneaker\b", "sneakers", text)
    return _collapse_spaces(text)


def normalize_metadata_text(value: str | None) -> str:
    text = _normalize_unicode(value)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _collapse_spaces(text)


def normalize_alias_key(value: str | None) -> str:
    return normalize_metadata_text(value)


def contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text) is not None


def repair_mojibake(value: str) -> str:
    repaired = value
    for _ in range(2):
        if not any(marker in repaired for marker in _MOJIBAKE_MARKERS):
            break
        try:
            candidate = repaired.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        current_score = sum(repaired.count(marker) for marker in _MOJIBAKE_MARKERS)
        candidate_score = sum(candidate.count(marker) for marker in _MOJIBAKE_MARKERS)
        if candidate_score >= current_score:
            break
        repaired = candidate
    return repaired


def _normalize_unicode(value: str | None) -> str:
    if not value:
        return ""
    text = repair_mojibake(value)
    text = unicodedata.normalize("NFKC", text).strip().casefold().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
