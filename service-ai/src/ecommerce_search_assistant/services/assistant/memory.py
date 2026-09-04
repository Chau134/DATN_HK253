from __future__ import annotations

import re
import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CandidateAnchor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    product_ids: list[str] = Field(default_factory=list)
    provenance: str = "unknown"
    turn_index: int = 0


class ConversationMemory(BaseModel):
    """Bounded, content-aware state that survives transcript compaction."""

    model_config = ConfigDict(extra="ignore")

    turn_index: int = 0
    active_intent: str | None = None
    active_constraints: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    avoidances: list[str] = Field(default_factory=list)
    superseded_values: dict[str, list[Any]] = Field(default_factory=dict)
    candidate_anchors: dict[str, CandidateAnchor] = Field(default_factory=dict)
    unresolved_questions: list[str] = Field(default_factory=list)
    confirmed_decisions: list[str] = Field(default_factory=list)
    summary_compaction_count: int = 0

    def prompt_payload(self, *, include_history: bool = False) -> dict[str, Any]:
        excluded = set() if include_history else {"superseded_values"}
        return self.model_dump(
            exclude=excluded,
            exclude_none=True,
            exclude_defaults=True,
        )


_CORRECTION_CUES = (
    "khong phai",
    "doi sang",
    "thay bang",
    "sua lai",
    "y minh la",
    "actually",
    "instead",
    "change to",
)
_PREFERENCE_CUES = (
    "toi thich",
    "minh thich",
    "em thich",
    "toi uu tien",
    "minh uu tien",
    "gu cua toi",
    "gu cua minh",
    "i like",
    "i prefer",
)
_AVOIDANCE_CUES = (
    "toi khong thich",
    "minh khong thich",
    "toi khong muon",
    "minh khong muon",
    "tranh ",
    "i dislike",
    "avoid ",
)
_DECISION_CUES = (
    "toi chot",
    "minh chot",
    "toi chon",
    "minh chon",
    "lay mau",
    "chot mau",
    "i choose",
    "i'll take",
)
_NAME_PATTERNS = (
    re.compile(r"\bgoi danh sach (?:nay )?la ([a-z0-9 _-]{1,40})\b"),
    re.compile(r"\bluu danh sach (?:nay )?(?:voi ten|ten) ([a-z0-9 _-]{1,40})\b"),
    re.compile(r"\bname (?:this )?list ([a-z0-9 _-]{1,40})\b"),
)
_MEMORY_RECALL_CUES = (
    "nhac lai",
    "toi da noi gi",
    "minh da noi gi",
    "toi da chon gi",
    "minh da chon gi",
    "so thich hien tai",
    "so thich cua toi",
    "so thich cua minh",
    "what did i say",
    "what did i choose",
    "my current preferences",
    "remind me",
)
_CONVERSATION_SUMMARY_CUES = (
    "tong hop",
    "tom tat cuoc tro chuyen",
    "tom tat nhung gi",
    "conversation summary",
    "summarize our conversation",
)
_NEW_SEARCH_CUES = (
    "tim ",
    "goi y",
    "de xuat",
    "recommend",
    "search",
    "san pham moi",
)


def load_conversation_memory(payload: dict[str, Any] | None) -> ConversationMemory:
    try:
        return ConversationMemory.model_validate(payload or {})
    except (TypeError, ValueError):
        return ConversationMemory()


def update_conversation_memory(
    payload: dict[str, Any] | None,
    *,
    message: str,
    intent: str | None,
    filters: dict[str, Any] | None,
    final_product_ids: list[dict[str, Any]],
    route: str,
    clarifying_question: str | None,
    assistant_reply: str,
    summary_compacted: bool,
) -> ConversationMemory:
    memory = load_conversation_memory(payload)
    memory.turn_index += 1
    if intent:
        memory.active_intent = intent

    normalized = normalize_memory_text(message)
    correction = any(cue in normalized for cue in _CORRECTION_CUES)
    for field, value in (filters or {}).items():
        if value is None or value == []:
            continue
        old_value = memory.active_constraints.get(field)
        if old_value is not None and old_value != value:
            superseded = memory.superseded_values.setdefault(field, [])
            if old_value not in superseded:
                superseded.append(old_value)
                del superseded[:-10]
        # Explicit filters from the current turn already have precedence in the
        # workflow. Persist their resolved value instead of retaining both.
        memory.active_constraints[field] = value

    if any(cue in normalized for cue in _PREFERENCE_CUES):
        memory.preferences.update(filters or {})
    if any(cue in normalized for cue in _AVOIDANCE_CUES):
        _append_bounded(memory.avoidances, message.strip()[:300], 20)
    if correction and filters:
        # Corrections are also useful when the original value was only present
        # in a compacted transcript rather than active_constraints.
        memory.preferences.update(filters)

    if clarifying_question:
        _append_bounded(memory.unresolved_questions, clarifying_question[:300], 10)
    elif memory.unresolved_questions and assistant_reply.strip():
        memory.unresolved_questions.pop(0)
    if any(cue in normalized for cue in _DECISION_CUES):
        _append_bounded(memory.confirmed_decisions, message.strip()[:300], 10)

    product_ids = [
        str(item["product_id"])
        for item in final_product_ids
        if item.get("product_id") is not None
    ][:20]
    if product_ids:
        anchor = CandidateAnchor(
            product_ids=product_ids,
            provenance=route,
            turn_index=memory.turn_index,
        )
        if "first" not in memory.candidate_anchors:
            memory.candidate_anchors["first"] = anchor.model_copy(deep=True)
        memory.candidate_anchors["latest"] = anchor.model_copy(deep=True)
        memory.candidate_anchors[f"turn_{memory.turn_index}"] = anchor.model_copy(deep=True)
        explicit_name = extract_candidate_anchor_name(message)
        if explicit_name:
            memory.candidate_anchors[f"named:{explicit_name}"] = anchor.model_copy(deep=True)
        _trim_candidate_anchors(memory.candidate_anchors)
    else:
        explicit_name = extract_candidate_anchor_name(message)
        latest = memory.candidate_anchors.get("latest")
        if explicit_name and latest:
            memory.candidate_anchors[f"named:{explicit_name}"] = latest.model_copy(deep=True)
            _trim_candidate_anchors(memory.candidate_anchors)

    if summary_compacted:
        memory.summary_compaction_count += 1
    return memory


def resolve_candidate_reference(
    message: str,
    payload: dict[str, Any] | None,
    fallback_results: list[dict[str, Any]],
) -> tuple[list[str], str]:
    memory = load_conversation_memory(payload)
    normalized = normalize_memory_text(message)
    anchor_name = referenced_candidate_anchor_name(normalized)
    anchor: CandidateAnchor | None = None
    source = "none"
    if anchor_name:
        anchor = memory.candidate_anchors.get(anchor_name)
        source = anchor_name
        if anchor is None:
            return [], f"unresolved:{anchor_name}"
    if anchor is None:
        anchor = memory.candidate_anchors.get("latest")
        source = "latest" if anchor else "last_product_ids"

    product_ids = (
        list(anchor.product_ids)
        if anchor
        else [
            str(item["product_id"])
            for item in fallback_results
            if item.get("product_id") is not None
        ]
    )
    index = extract_ordinal_index(normalized)
    if index is None:
        if len(product_ids) == 1 and has_singular_reference(normalized):
            return [product_ids[0]], source
        return [], "none"
    if not product_ids:
        return [], "unresolved:ordinal"
    if 1 <= index <= len(product_ids):
        return [product_ids[index - 1]], source
    return [], "unresolved:ordinal"


def detect_memory_intent(message: str) -> str | None:
    """Return a deterministic memory-only intent, avoiding an analyze/search LLM call."""
    normalized = normalize_memory_text(message)
    if any(cue in normalized for cue in _NEW_SEARCH_CUES):
        return None
    if any(cue in normalized for cue in _CONVERSATION_SUMMARY_CUES):
        return "conversation_summary"
    if any(cue in normalized for cue in _MEMORY_RECALL_CUES):
        return "memory_recall"
    return None


def allowed_candidate_ids(payload: dict[str, Any] | None, fallback_results: list[dict[str, Any]]) -> set[str]:
    memory = load_conversation_memory(payload)
    allowed = {
        product_id
        for anchor in memory.candidate_anchors.values()
        for product_id in anchor.product_ids
    }
    allowed.update(
        str(item["product_id"])
        for item in fallback_results
        if item.get("product_id") is not None
    )
    return allowed


def extract_candidate_anchor_name(message: str) -> str | None:
    normalized = normalize_memory_text(message)
    for pattern in _NAME_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return _clean_anchor_name(match.group(1))
    return None


def referenced_candidate_anchor_name(normalized: str) -> str | None:
    if any(value in normalized for value in ("luc dau", "ban dau", "dau tien", "initial list")):
        return "first"
    if any(value in normalized for value in ("vua roi", "gan nhat", "latest list", "last list")):
        return "latest"
    match = re.search(r"\bdanh sach (?!nay|vua|gan|ban|luc)([a-z0-9_-]{1,40})\b", normalized)
    if match:
        return f"named:{_clean_anchor_name(match.group(1))}"
    match = re.search(r"\blist (?:named )?([a-z0-9_-]{1,40})\b", normalized)
    if match:
        return f"named:{_clean_anchor_name(match.group(1))}"
    return None


def extract_ordinal_index(normalized: str) -> int | None:
    match = re.search(
        r"\b(?:(?:cai|mau|san pham)\s*(?:thu\s*)?|thu\s+)(\d+)\b",
        normalized,
    )
    if match:
        return int(match.group(1))
    words = {"dau": 1, "nhat": 1, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5}
    for word, index in words.items():
        if re.search(rf"\b(?:thu\s+|(?:cai|mau|san pham)\s+(?:thu\s+)?){word}\b", normalized):
            return index
    return None


def has_singular_reference(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "cai do",
            "mau do",
            "san pham do",
            "mau vua roi",
            "san pham vua roi",
            "that one",
        )
    )


def normalize_memory_text(value: str) -> str:
    text = value.strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text)


def _clean_anchor_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.strip()).strip("-")[:40]


def _append_bounded(values: list[str], value: str, limit: int) -> None:
    if value and value not in values:
        values.append(value)
        del values[:-limit]


def _trim_candidate_anchors(anchors: dict[str, CandidateAnchor], limit: int = 20) -> None:
    protected = {"first", "latest"}
    removable = [
        key
        for key, _ in sorted(anchors.items(), key=lambda item: item[1].turn_index)
        if key not in protected and not key.startswith("named:")
    ]
    while len(anchors) > limit and removable:
        anchors.pop(removable.pop(0), None)
