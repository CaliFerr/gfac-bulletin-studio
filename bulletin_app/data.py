from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ProgramEntry:
    """Canonical representation of one program item."""

    order: int
    title: str
    extra: str
    name: str


@dataclass(frozen=True)
class BulletinSection:
    title: str
    time: str
    entries: list[ProgramEntry]


_ORDER_KEYS = ("order", "Order", "position", "Position")
_TITLE_KEYS = ("title", "Title")
_NAME_KEYS = ("name", "Name", "subheading", "Subheading")
_EXTRA_KEYS = ("extra", "Extra", "small_subheading", "Small_Subheading")
_SECTION_ROWS = {
    ("filipino service", "9:00 am"),
    ("sabbath school", "10:00 am"),
    ("hour of worship", "11:15am"),
    ("hour of worship", "11:15 am"),
}


def load_program_entries(csv_path: str | Path) -> list[ProgramEntry]:
    """Load program rows from CSV and normalize them into a stable schema."""

    rows = _load_normalized_rows(csv_path)
    entries: list[ProgramEntry] = []
    for index, row in enumerate(rows, start=1):
        if _is_section_row(row):
            continue

        order = _parse_order(_pick_first(row, _ORDER_KEYS), fallback=index)
        title = _normalize_text(_pick_first(row, _TITLE_KEYS))
        name = _normalize_text(_pick_first(row, _NAME_KEYS))
        extra = _normalize_multiline_text(_pick_first(row, _EXTRA_KEYS))

        if not any((title, name, extra)):
            continue

        entries.append(
            ProgramEntry(
                order=order,
                title=title,
                extra=extra,
                name=name,
            )
        )

    return sorted(entries, key=lambda entry: (entry.order, entry.title.lower(), entry.name.lower()))


def load_bulletin_sections(csv_path: str | Path) -> list[BulletinSection]:
    rows = _load_normalized_rows(csv_path)
    sections = {
        ("filipino service", "9:00 am"): BulletinSection("Filipino Service", "9:00 am", []),
        ("sabbath school", "10:00 am"): BulletinSection("Sabbath School", "10:00 am", []),
        ("hour of worship", "11:15 am"): BulletinSection("Hour Of Worship", "11:15 am", []),
    }
    current_key: tuple[str, str] | None = None
    order = 1

    for row in rows:
        title = _normalize_text(_pick_first(row, _TITLE_KEYS))
        name = _normalize_text(_pick_first(row, _NAME_KEYS))
        extra = _normalize_multiline_text(_pick_first(row, _EXTRA_KEYS))
        section_key = _section_key(title, name)

        if section_key is not None:
            current_key = _canonical_section_key(section_key)
            continue

        if current_key is None or not any((title, name, extra)):
            continue

        sections[current_key].entries.append(
            ProgramEntry(
                order=order,
                title=title,
                name=name,
                extra=extra,
            )
        )
        order += 1

    return [
        sections[("filipino service", "9:00 am")],
        sections[("sabbath school", "10:00 am")],
        sections[("hour of worship", "11:15 am")],
    ]


def read_csv_rows(csv_path: str | Path) -> list[dict[str, str]]:
    """Return raw CSV rows for slide-generation compatibility."""

    return _load_normalized_rows(csv_path)


def iter_extra_lines(extra: str) -> Iterable[str]:
    for line in extra.splitlines():
        cleaned = line.strip()
        if cleaned:
            yield cleaned


def _pick_first(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return ""


def _load_normalized_rows(csv_path: str | Path) -> list[dict[str, str]]:
    path = Path(csv_path)
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized: dict[str, str] = {}
            for key, value in row.items():
                normalized[(key or "").strip()] = value or ""
            rows.append(normalized)
        return rows


def _normalize_text(value: str) -> str:
    return (value or "").replace("\\n", "\n").strip()


def _normalize_multiline_text(value: str) -> str:
    lines = [line.strip() for line in _normalize_text(value).splitlines()]
    return "\n".join(line for line in lines if line)


def _parse_order(value: str, fallback: int) -> int:
    cleaned = (value or "").strip()
    if not cleaned:
        return fallback

    try:
        return int(cleaned)
    except ValueError:
        return fallback


def _section_key(title: str, name: str) -> tuple[str, str] | None:
    candidate = (title.strip().lower(), name.strip().lower())
    if candidate in _SECTION_ROWS:
        return candidate
    return None


def _canonical_section_key(key: tuple[str, str]) -> tuple[str, str]:
    if key[0] == "hour of worship":
        return ("hour of worship", "11:15 am")
    return key


def _is_section_row(row: dict[str, str]) -> bool:
    title = _normalize_text(_pick_first(row, _TITLE_KEYS))
    name = _normalize_text(_pick_first(row, _NAME_KEYS))
    return _section_key(title, name) is not None
