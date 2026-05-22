from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TypedDict

from langnet.foster_ossa.models import FosterOssaPage, FosterOssaTocEntry

PRINTED_TO_PHYSICAL_PAGE_OFFSET = 46
TOC_PAGE_MAX = 20
FIRST_EXPERIENCE_GLOBAL_MAX = 35
THIRD_EXPERIENCE_GLOBAL_MAX = 70
FOURTH_EXPERIENCE_GLOBAL_MAX = 105
EXPERIENCE_BY_LATIN = {
    "prima": 1,
    "secunda": 2,
    "secvnda": 2,
    "tertia": 3,
    "quarta": 4,
    "qvarta": 4,
    "quinta": 5,
    "qvinta": 5,
}
EXPERIENCE_RE = re.compile(
    r"\b(?P<latin>prima|secunda|secvnda|tertia|quarta|qvarta|quinta|qvinta)\s+"
    r"experientia\b",
    re.IGNORECASE,
)
ENTRY_START_RE = re.compile(
    r"^(?P<local>\d{1,3})[.)]?\s*"
    r"(?:\((?P<global>\d(?:\s*\d){0,2})\)\s*)?"
    r"(?P<rest>.+)$"
)
PRINTED_PAGE_RE = re.compile(r"^(?P<title>.+?)\s+(?P<page>\d{1,4})$")
SKIP_LINE_PREFIXES = ("contents", "ossa latinitatis sola")


class _PendingTocEntry(TypedDict):
    source_page_number: int
    experience: int
    encounter: int
    global_encounter: int | None
    title_parts: list[str]


class _TocRow(TypedDict):
    toc_id: str
    source_page_number: int
    section_kind: str
    experience: int
    encounter: int
    global_encounter: int | None
    encounter_id: str
    latin_title: str
    english_title: str
    printed_page: int
    inferred_page_number: int


def parse_toc_entries(pages: Sequence[FosterOssaPage]) -> list[FosterOssaTocEntry]:
    rows: list[_TocRow] = []
    current_experience: int | None = None
    pending: _PendingTocEntry | None = None
    english_row_index: int | None = None
    for page in pages:
        if page.page_number > TOC_PAGE_MAX:
            continue
        for line in _clean_lines(page.text):
            start = ENTRY_START_RE.match(line)
            if start and current_experience is not None:
                pending = {
                    "source_page_number": page.page_number,
                    "experience": current_experience,
                    "encounter": int(start.group("local")),
                    "global_encounter": (
                        _parse_global_encounter(start.group("global"))
                        if start.group("global")
                        else None
                    ),
                    "title_parts": [start.group("rest").strip()],
                }
                english_row_index = _try_finalize_pending(rows, pending)
                if english_row_index is not None:
                    pending = None
                continue
            if pending is not None:
                pending["title_parts"].append(line)
                english_row_index = _try_finalize_pending(rows, pending)
                if english_row_index is not None:
                    pending = None
                continue
            experience = _experience_from_line(line)
            if experience is not None:
                current_experience = experience
                pending = None
                english_row_index = None
                continue
            if english_row_index is not None and _looks_like_english_title(line):
                row = rows[english_row_index]
                row["english_title"] = _join_title_parts([str(row["english_title"]), line])
    return [_toc_entry_from_row(row) for row in rows]


def _try_finalize_pending(
    rows: list[_TocRow],
    pending: _PendingTocEntry,
) -> int | None:
    title = _join_title_parts(pending["title_parts"])
    split = PRINTED_PAGE_RE.match(title)
    if split is None:
        return None
    printed_page = int(split.group("page"))
    latin_title = split.group("title").strip(" .")
    pending_experience = int(pending["experience"])
    encounter = int(pending["encounter"])
    global_encounter = pending["global_encounter"]
    experience = (
        _experience_from_global(int(global_encounter))
        if global_encounter is not None
        else pending_experience
    )
    rows.append(
        {
            "toc_id": f"toc:{experience}.{encounter}",
            "source_page_number": int(pending["source_page_number"]),
            "section_kind": "encounter",
            "experience": experience,
            "encounter": encounter,
            "global_encounter": (
                int(global_encounter)
                if global_encounter is not None
                else _default_global(experience, encounter)
            ),
            "encounter_id": f"{experience}.{encounter}",
            "latin_title": latin_title,
            "english_title": "",
            "printed_page": printed_page,
            "inferred_page_number": printed_page + PRINTED_TO_PHYSICAL_PAGE_OFFSET,
        }
    )
    return len(rows) - 1


def _toc_entry_from_row(row: _TocRow) -> FosterOssaTocEntry:
    return FosterOssaTocEntry(
        toc_id=str(row["toc_id"]),
        source_page_number=int(row["source_page_number"]),
        section_kind=str(row["section_kind"]),
        experience=int(row["experience"]),
        encounter=int(row["encounter"]) if row["encounter"] is not None else None,
        global_encounter=(
            int(row["global_encounter"]) if row["global_encounter"] is not None else None
        ),
        encounter_id=str(row["encounter_id"]) if row["encounter_id"] is not None else None,
        latin_title=str(row["latin_title"]),
        english_title=str(row["english_title"]),
        printed_page=int(row["printed_page"]),
        inferred_page_number=int(row["inferred_page_number"]),
    )


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        cleaned = " ".join(raw_line.replace("\x07", " ").split()).strip()
        if not cleaned:
            continue
        if cleaned.casefold().startswith(SKIP_LINE_PREFIXES):
            continue
        if cleaned in {"•", "First Experience", "Second Experience", "Third Experience"}:
            continue
        lines.append(cleaned)
    return lines


def _experience_from_line(line: str) -> int | None:
    match = EXPERIENCE_RE.search(line)
    if match is None:
        return None
    return EXPERIENCE_BY_LATIN[match.group("latin").casefold()]


def _looks_like_english_title(line: str) -> bool:
    first = line[:1]
    if not first:
        return False
    return first.islower() or line.startswith("the ") or line.startswith("Block ")


def _join_title_parts(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part.strip())


def _default_global(experience: int, encounter: int) -> int | None:
    return encounter if experience == 1 else None


def _parse_global_encounter(raw: str) -> int:
    return int("".join(raw.split()))


def _experience_from_global(global_encounter: int) -> int:
    if global_encounter <= FIRST_EXPERIENCE_GLOBAL_MAX:
        return 1
    if global_encounter <= THIRD_EXPERIENCE_GLOBAL_MAX:
        return 3
    if global_encounter <= FOURTH_EXPERIENCE_GLOBAL_MAX:
        return 4
    return 5
