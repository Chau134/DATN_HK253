from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import logging
from pathlib import Path
import sqlite3
from threading import RLock
from time import time
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ecommerce_search_assistant.core.config import Settings

logger = logging.getLogger(__name__)

PreferenceField = Literal[
    "preferred_categories",
    "preferred_brands",
    "preferred_colors",
    "preferred_sizes",
    "preferred_materials",
    "preferred_gender",
    "budget_min",
    "budget_max",
]


class PreferenceVersionConflict(RuntimeError):
    def __init__(self, *, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"preference_version_conflict expected={expected} actual={actual}")


class UserPreferenceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_categories: list[str] = Field(default_factory=list)
    preferred_brands: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_sizes: list[str] = Field(default_factory=list)
    preferred_materials: list[str] = Field(default_factory=list)
    preferred_gender: str | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    style_notes: list[str] = Field(default_factory=list)
    avoidance_notes: list[str] = Field(default_factory=list)
    superseded_values: dict[str, list[Any]] = Field(default_factory=dict)
    version: int = Field(default=0, ge=0)
    updated_at_epoch: int = 0
    source_turn_sequence: int | None = Field(default=None, ge=1)
    source_session_hash: str | None = None
    source_request_hash: str | None = None

    @field_validator(
        "preferred_categories",
        "preferred_brands",
        "preferred_colors",
        "preferred_sizes",
        "preferred_materials",
        "style_notes",
        "avoidance_notes",
        mode="after",
    )
    @classmethod
    def dedupe_list_values(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))

    @model_validator(mode="after")
    def validate_budget_range(self) -> "UserPreferenceProfile":
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValueError("budget_min cannot be greater than budget_max")
        return self

    def merged(self, update: "UserPreferenceUpdate", max_notes: int) -> "UserPreferenceProfile":
        superseded_values = {
            key: list(values)
            for key, values in self.superseded_values.items()
        }
        budget_min = update.budget_min if update.budget_min is not None else self.budget_min
        budget_max = update.budget_max if update.budget_max is not None else self.budget_max
        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            if update.budget_min is not None and update.budget_max is None:
                _record_superseded(superseded_values, "budget_max", self.budget_max, None)
                budget_max = None
            elif update.budget_max is not None and update.budget_min is None:
                _record_superseded(superseded_values, "budget_min", self.budget_min, None)
                budget_min = None

        for field_name in update.replace_fields:
            _record_superseded(
                superseded_values,
                field_name,
                getattr(self, field_name),
                getattr(update, field_name),
            )

        return UserPreferenceProfile.model_validate(
            {
                "preferred_categories": self._merged_list("preferred_categories", update),
                "preferred_brands": self._merged_list("preferred_brands", update),
                "preferred_colors": self._merged_list("preferred_colors", update),
                "preferred_sizes": self._merged_list("preferred_sizes", update),
                "preferred_materials": self._merged_list("preferred_materials", update),
                "preferred_gender": update.preferred_gender or self.preferred_gender,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "style_notes": _merge_recent(update.style_notes, self.style_notes)[:max_notes],
                "avoidance_notes": _merge_recent(update.avoidance_notes, self.avoidance_notes)[:max_notes],
                "superseded_values": superseded_values,
                "version": self.version + 1,
                "updated_at_epoch": int(time()),
                "source_turn_sequence": update.source_turn_sequence,
                "source_session_hash": update.source_session_hash,
                "source_request_hash": update.source_request_hash,
            }
        )

    def _merged_list(
        self,
        field_name: Literal[
            "preferred_categories", "preferred_brands", "preferred_colors",
            "preferred_sizes", "preferred_materials",
        ],
        update: "UserPreferenceUpdate",
    ) -> list[str]:
        incoming = getattr(update, field_name)
        if field_name in update.replace_fields:
            return incoming
        return _merge_recent(incoming, getattr(self, field_name))

    def prompt_payload(self) -> dict[str, object]:
        return self.model_dump(
            exclude={
                "superseded_values",
                "version",
                "updated_at_epoch",
                "source_turn_sequence",
                "source_session_hash",
                "source_request_hash",
            },
            exclude_none=True,
            exclude_defaults=True,
        )


class UserPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_categories: list[str] = Field(default_factory=list)
    preferred_brands: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_sizes: list[str] = Field(default_factory=list)
    preferred_materials: list[str] = Field(default_factory=list)
    preferred_gender: str | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    style_notes: list[str] = Field(default_factory=list)
    avoidance_notes: list[str] = Field(default_factory=list)
    replace_fields: set[PreferenceField] = Field(default_factory=set)
    source_turn_sequence: int | None = Field(default=None, ge=1)
    source_session_hash: str | None = None
    source_request_hash: str | None = None

    @model_validator(mode="after")
    def validate_budget_range(self) -> "UserPreferenceUpdate":
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValueError("budget_min cannot be greater than budget_max")
        return self


class UserPreferenceStore(Protocol):
    def get(self, user_id: str) -> UserPreferenceProfile:
        ...

    def merge(
        self,
        user_id: str,
        update: UserPreferenceUpdate,
        *,
        expected_version: int | None = None,
    ) -> UserPreferenceProfile:
        ...

    def clear(self, user_id: str) -> None:
        ...


@dataclass
class NullUserPreferenceStore:
    def get(self, user_id: str) -> UserPreferenceProfile:
        del user_id
        return UserPreferenceProfile()

    def merge(
        self,
        user_id: str,
        update: UserPreferenceUpdate,
        *,
        expected_version: int | None = None,
    ) -> UserPreferenceProfile:
        del user_id, update, expected_version
        return UserPreferenceProfile()

    def clear(self, user_id: str) -> None:
        del user_id


@dataclass
class InMemoryUserPreferenceStore:
    max_notes: int = 5
    _profiles: dict[str, UserPreferenceProfile] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def get(self, user_id: str) -> UserPreferenceProfile:
        with self._lock:
            return self._profiles.get(_user_key(user_id), UserPreferenceProfile()).model_copy(deep=True)

    def merge(
        self,
        user_id: str,
        update: UserPreferenceUpdate,
        *,
        expected_version: int | None = None,
    ) -> UserPreferenceProfile:
        with self._lock:
            key = _user_key(user_id)
            current = self._profiles.get(key, UserPreferenceProfile())
            _assert_expected_version(current, expected_version)
            profile = current.merged(update, self.max_notes)
            self._profiles[key] = profile
            return profile.model_copy(deep=True)

    def clear(self, user_id: str) -> None:
        with self._lock:
            self._profiles.pop(_user_key(user_id), None)


class SqliteUserPreferenceStore:
    def __init__(self, path: str, ttl_seconds: int, max_notes: int) -> None:
        preference_path = Path(path)
        preference_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(preference_path, check_same_thread=False)
        self._ttl_seconds = ttl_seconds
        self._max_notes = max_notes
        self._lock = RLock()
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assistant_user_preferences (
                    user_key TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    expires_at_epoch INTEGER NOT NULL
                )
                """
            )

    def get(self, user_id: str) -> UserPreferenceProfile:
        key = _user_key(user_id)
        with self._lock:
            row = self._connection.execute(
                "SELECT profile_json, expires_at_epoch FROM assistant_user_preferences WHERE user_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return UserPreferenceProfile()
            if int(row[1]) <= int(time()):
                self.clear(user_id)
                return UserPreferenceProfile()
            return _profile_from_json(row[0])

    def merge(
        self,
        user_id: str,
        update: UserPreferenceUpdate,
        *,
        expected_version: int | None = None,
    ) -> UserPreferenceProfile:
        with self._lock:
            current = self.get(user_id)
            _assert_expected_version(current, expected_version)
            profile = current.merged(update, self._max_notes)
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO assistant_user_preferences(user_key, profile_json, expires_at_epoch)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_key) DO UPDATE SET
                        profile_json = excluded.profile_json,
                        expires_at_epoch = excluded.expires_at_epoch
                    """,
                    (
                        _user_key(user_id),
                        profile.model_dump_json(),
                        int(time()) + self._ttl_seconds,
                    ),
                )
            return profile

    def clear(self, user_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM assistant_user_preferences WHERE user_key = ?",
                (_user_key(user_id),),
            )


class RedisUserPreferenceStore:
    def __init__(self, redis_url: str, ttl_seconds: int, max_notes: int) -> None:
        from redis import Redis

        self._client = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds
        self._max_notes = max_notes

    def get(self, user_id: str) -> UserPreferenceProfile:
        payload = self._client.get(_redis_key(user_id))
        return _profile_from_json(payload) if payload else UserPreferenceProfile()

    def merge(
        self,
        user_id: str,
        update: UserPreferenceUpdate,
        *,
        expected_version: int | None = None,
    ) -> UserPreferenceProfile:
        from redis.exceptions import WatchError

        key = _redis_key(user_id)
        for _ in range(5):
            with self._client.pipeline() as pipeline:
                try:
                    pipeline.watch(key)
                    payload = pipeline.get(key)
                    current = _profile_from_json(payload) if payload else UserPreferenceProfile()
                    _assert_expected_version(current, expected_version)
                    profile = current.merged(update, self._max_notes)
                    pipeline.multi()
                    pipeline.setex(key, self._ttl_seconds, profile.model_dump_json())
                    pipeline.execute()
                    return profile
                except WatchError:
                    continue
        raise RuntimeError("user_preference_update_conflict")

    def clear(self, user_id: str) -> None:
        self._client.delete(_redis_key(user_id))


def build_user_preference_store(settings: Settings) -> UserPreferenceStore:
    if not settings.assistant_user_memory_enabled or settings.assistant_user_memory_backend == "disabled":
        return NullUserPreferenceStore()

    backend = settings.assistant_user_memory_backend
    if backend == "auto":
        backend = "redis" if settings.checkpoint_backend == "redis" else "sqlite"

    if backend == "redis":
        if not settings.redis_url:
            raise ValueError("REDIS_URL is required for Redis user preference memory")
        return RedisUserPreferenceStore(
            settings.redis_url,
            settings.assistant_user_memory_ttl_seconds,
            settings.assistant_user_memory_max_notes,
        )
    if backend == "sqlite":
        return SqliteUserPreferenceStore(
            f"{settings.sqlite_checkpoint_path}.preferences",
            settings.assistant_user_memory_ttl_seconds,
            settings.assistant_user_memory_max_notes,
        )
    raise ValueError(f"Unsupported ASSISTANT_USER_MEMORY_BACKEND={backend}")


def _merge_recent(new_values: list[str], old_values: list[str], limit: int = 20) -> list[str]:
    return list(dict.fromkeys([*new_values, *old_values]))[:limit]


def _assert_expected_version(
    profile: UserPreferenceProfile,
    expected_version: int | None,
) -> None:
    if expected_version is not None and profile.version != expected_version:
        raise PreferenceVersionConflict(expected=expected_version, actual=profile.version)


def _record_superseded(
    superseded_values: dict[str, list[Any]],
    field_name: str,
    old_value: Any,
    new_value: Any,
) -> None:
    old_values = old_value if isinstance(old_value, list) else [old_value]
    new_values = set(new_value if isinstance(new_value, list) else [new_value])
    history = superseded_values.setdefault(field_name, [])
    for value in old_values:
        if value is not None and value not in new_values and value not in history:
            history.append(value)
    del history[:-20]
    if not history:
        superseded_values.pop(field_name, None)


def _profile_from_json(payload: str) -> UserPreferenceProfile:
    try:
        return UserPreferenceProfile.model_validate_json(payload)
    except (ValueError, TypeError, json.JSONDecodeError):
        logger.warning("assistant_user_preference_payload_invalid")
        return UserPreferenceProfile()


def _user_key(user_id: str) -> str:
    return sha256(user_id.strip().encode("utf-8")).hexdigest()


def _redis_key(user_id: str) -> str:
    return f"assistant:user-preferences:v1:{_user_key(user_id)}"
