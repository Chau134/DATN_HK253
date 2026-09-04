import pytest

from ecommerce_search_assistant.services.assistant.preferences import (
    InMemoryUserPreferenceStore,
    PreferenceVersionConflict,
    SqliteUserPreferenceStore,
    UserPreferenceUpdate,
)


def test_preference_store_merges_deduplicates_and_isolates_users() -> None:
    store = InMemoryUserPreferenceStore(max_notes=2)

    store.merge(
        "user-1",
        UserPreferenceUpdate(
            preferred_colors=["black"],
            preferred_sizes=["L"],
            style_notes=["Mình thích đồ tối màu"],
        ),
    )
    profile = store.merge(
        "user-1",
        UserPreferenceUpdate(
            preferred_colors=["white", "black"],
            style_notes=["Ưu tiên form rộng", "Mình thích đồ tối màu"],
        ),
    )

    assert profile.preferred_colors == ["white", "black"]
    assert profile.preferred_sizes == ["L"]
    assert profile.style_notes == ["Ưu tiên form rộng", "Mình thích đồ tối màu"]
    assert store.get("user-2").prompt_payload() == {}


def test_preference_store_can_clear_profile() -> None:
    store = InMemoryUserPreferenceStore()
    store.merge("user-1", UserPreferenceUpdate(preferred_colors=["black"]))

    store.clear("user-1")

    assert store.get("user-1").preferred_colors == []


def test_new_budget_bound_replaces_a_conflicting_old_bound() -> None:
    store = InMemoryUserPreferenceStore()
    store.merge("user-1", UserPreferenceUpdate(budget_max=500_000))

    profile = store.merge("user-1", UserPreferenceUpdate(budget_min=700_000))

    assert profile.budget_min == 700_000
    assert profile.budget_max is None


def test_sqlite_preference_store_persists_and_expires(tmp_path) -> None:
    path = str(tmp_path / "preferences.sqlite3")
    first_store = SqliteUserPreferenceStore(path, ttl_seconds=3600, max_notes=5)
    first_store.merge("user-1", UserPreferenceUpdate(preferred_sizes=["L"]))

    second_store = SqliteUserPreferenceStore(path, ttl_seconds=3600, max_notes=5)
    assert second_store.get("user-1").preferred_sizes == ["L"]
    assert second_store.get("user-2").prompt_payload() == {}

    expiring_store = SqliteUserPreferenceStore(
        str(tmp_path / "expiring.sqlite3"),
        ttl_seconds=0,
        max_notes=5,
    )
    expiring_store.merge("user-1", UserPreferenceUpdate(preferred_colors=["black"]))
    assert expiring_store.get("user-1").prompt_payload() == {}


def test_preference_update_can_replace_an_explicit_old_value() -> None:
    store = InMemoryUserPreferenceStore()
    store.merge("user-1", UserPreferenceUpdate(preferred_colors=["black"]))

    profile = store.merge(
        "user-1",
        UserPreferenceUpdate(
            preferred_colors=["blue"],
            replace_fields={"preferred_colors"},
        ),
    )

    assert profile.preferred_colors == ["blue"]


def test_preference_replacement_tracks_history_without_leaking_it_to_prompt() -> None:
    store = InMemoryUserPreferenceStore()
    first = store.merge(
        "user-1",
        UserPreferenceUpdate(
            preferred_colors=["black"],
            source_turn_sequence=1,
            source_session_hash="session-a",
        ),
        expected_version=0,
    )
    corrected = store.merge(
        "user-1",
        UserPreferenceUpdate(
            preferred_colors=["blue"],
            replace_fields={"preferred_colors"},
            source_turn_sequence=2,
            source_session_hash="session-a",
        ),
        expected_version=first.version,
    )

    assert corrected.version == 2
    assert corrected.preferred_colors == ["blue"]
    assert corrected.superseded_values == {"preferred_colors": ["black"]}
    assert "black" not in str(corrected.prompt_payload())
    assert corrected.source_turn_sequence == 2


def test_preference_store_rejects_stale_compare_and_set() -> None:
    store = InMemoryUserPreferenceStore()
    store.merge(
        "user-1",
        UserPreferenceUpdate(preferred_sizes=["M"]),
        expected_version=0,
    )

    with pytest.raises(PreferenceVersionConflict):
        store.merge(
            "user-1",
            UserPreferenceUpdate(preferred_sizes=["L"]),
            expected_version=0,
        )
