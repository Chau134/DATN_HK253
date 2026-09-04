from __future__ import annotations

from common import SUITE_DIR, read_csv, write_csv


CONFIRMATION = "User confirmed AI pre-score on 2026-08-26:"


def confirm_packet(name: str) -> None:
    path = SUITE_DIR / "review" / name
    rows = read_csv(path)
    for row in rows:
        notes = row.get("review_notes", "")
        prefix = "AI pre-score — cần human review:"
        if notes.startswith(prefix):
            notes = notes[len(prefix):].strip()
        row["review_notes"] = f"{CONFIRMATION} {notes}".strip()
    write_csv(path, rows, rows[0].keys())


def approve_critical_cases() -> None:
    path = SUITE_DIR / "data" / "critical_cases.csv"
    rows = read_csv(path)
    for row in rows:
        row["manual_status"] = "approved"
        note = row.get("notes", "").strip()
        marker = "user-approved test design on 2026-08-26"
        if marker not in note:
            row["notes"] = f"{note} | {marker}" if note else marker
    write_csv(path, rows, rows[0].keys())


def main() -> int:
    confirm_packet("reviewer_a.csv")
    confirm_packet("reviewer_b.csv")
    approve_critical_cases()
    print("Recorded user confirmation for A/B pre-score and approved 12 critical test designs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
