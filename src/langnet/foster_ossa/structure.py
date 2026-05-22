from __future__ import annotations

import re
from collections.abc import Sequence

from langnet.foster_ossa.models import (
    FosterOssaConceptMention,
    FosterOssaEncounter,
    FosterOssaPage,
    FosterOssaStructuredPage,
)

EXPERIENCE_BY_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
ENCOUNTER_RE = re.compile(r"\b(?P<roman>I{1,3}|IV|V)\s+Encounter\s+(?P<n>\d+)\s+\(\d+\)")
ENCOUNTER_LINE_RE = re.compile(
    r"^\s*encounter\s+(?P<n>\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
CONCEPT_TERMS = {
    "nom.": "abbreviation",
    "acc.": "abbreviation",
    "gen.": "abbreviation",
    "dat.": "abbreviation",
    "abl.": "abbreviation",
    "voc.": "abbreviation",
    "loc.": "abbreviation",
    "function": "method",
    "functions": "method",
    "subject": "syntax",
    "object": "syntax",
    "Time 1": "verb_time",
    "Time 2": "verb_time",
    "T.1": "verb_time",
    "T.2": "verb_time",
}
ENCOUNTER_SECTIONS = {
    "first_experience",
    "second_experience",
    "third_experience",
    "fourth_experience",
    "fifth_experience",
}
EXPERIENCE_BY_SECTION = {
    "first_experience": 1,
    "second_experience": 2,
    "third_experience": 3,
    "fourth_experience": 4,
    "fifth_experience": 5,
}
SECTION_PAGE_RANGES: tuple[tuple[int, int | None, str], ...] = (
    (787, None, "indexes"),
    (776, None, "bibliography"),
    (155, 200, "reading_sheets_first_experience"),
    (651, None, "fifth_experience"),
    (455, None, "fourth_experience"),
    (251, None, "third_experience"),
    (201, None, "second_experience"),
    (49, None, "first_experience"),
)


def classify_page_section(page_number: int, text: str) -> str:
    for start_page, end_page, section in SECTION_PAGE_RANGES:
        if page_number >= start_page and (end_page is None or page_number <= end_page):
            return section
    return "front_matter"


def structured_page_rows(
    pages: Sequence[FosterOssaPage],
) -> list[FosterOssaStructuredPage]:
    return [
        FosterOssaStructuredPage.from_page(
            page,
            section=classify_page_section(page.page_number, page.text),
        )
        for page in pages
    ]


def detect_encounters(pages: Sequence[FosterOssaPage]) -> list[FosterOssaEncounter]:
    starts: list[tuple[int, int, int, str, str, FosterOssaPage]] = []
    seen_ids: set[tuple[int, int]] = set()
    for page in pages:
        section = classify_page_section(page.page_number, page.text)
        if section not in ENCOUNTER_SECTIONS:
            continue
        for experience, encounter, heading, title in _page_encounter_starts(page, section):
            encounter_key = (experience, encounter)
            if encounter_key in seen_ids:
                continue
            seen_ids.add(encounter_key)
            starts.append((page.page_number, experience, encounter, heading, title, page))

    encounters: list[FosterOssaEncounter] = []
    last_page = max((page.page_number for page in pages), default=0)
    pages_by_number = {page.page_number: page for page in pages}
    for index, (page_number, experience, encounter, heading, title, page) in enumerate(starts):
        next_page = starts[index + 1][0] if index + 1 < len(starts) else last_page + 1
        section_end = _section_span_end(page, pages_by_number, last_page)
        page_end = min(next_page - 1, section_end)
        encounters.append(
            FosterOssaEncounter(
                encounter_id=f"{experience}.{encounter}",
                experience=experience,
                encounter=encounter,
                page_start=page_number,
                page_end=max(page_number, page_end),
                heading=heading,
                title=title,
            )
        )
    return encounters


def _page_encounter_starts(
    page: FosterOssaPage,
    section: str,
) -> list[tuple[int, int, str, str]]:
    line_match = ENCOUNTER_LINE_RE.search(page.text)
    if line_match is not None:
        experience = EXPERIENCE_BY_SECTION[section]
        encounter = int(line_match.group("n"))
        return [
            (
                experience,
                encounter,
                line_match.group(0).strip(),
                _first_content_line_after_index(page.text, line_match.end()),
            )
        ]

    starts: list[tuple[int, int, str, str]] = []
    for match in ENCOUNTER_RE.finditer(page.text):
        starts.append(
            (
                EXPERIENCE_BY_ROMAN[match.group("roman")],
                int(match.group("n")),
                match.group(0),
                _first_content_line_after_index(page.text, match.end()),
            )
        )
    return starts


def detect_concept_mentions(
    pages: Sequence[FosterOssaPage],
    encounters: Sequence[FosterOssaEncounter] | None = None,
) -> list[FosterOssaConceptMention]:
    encounter_rows = encounters or detect_encounters(pages)
    mentions: list[FosterOssaConceptMention] = []
    for page in pages:
        encounter_id = _encounter_id_for_page(page.page_number, encounter_rows)
        for term, category in CONCEPT_TERMS.items():
            for match in _term_pattern(term).finditer(page.text):
                matched_term = match.group(0)
                mentions.append(
                    FosterOssaConceptMention(
                        term=matched_term,
                        normalized_term=_normalize_term(matched_term),
                        category=category,
                        page_number=page.page_number,
                        encounter_id=encounter_id,
                        context=_context_window(page.text, match.start(), match.end()),
                    )
                )
    return mentions


def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)


def _first_content_line_after_index(text: str, start: int) -> str:
    tail = text[start:]
    for line in tail.splitlines():
        stripped = line.strip(" \t—:-")
        if stripped:
            return stripped
    return ""


def _context_window(text: str, start: int, end: int, radius: int = 80) -> str:
    prefix = text[max(0, start - radius) : start]
    term = text[start:end]
    suffix = text[end : end + radius]
    return " ".join(f"{prefix}{term}{suffix}".split())


def _normalize_term(term: str) -> str:
    return term.strip(".").casefold().replace(" ", "_")


def _encounter_id_for_page(
    page_number: int,
    encounters: Sequence[FosterOssaEncounter],
) -> str | None:
    for encounter in encounters:
        if encounter.page_start <= page_number <= encounter.page_end:
            return encounter.encounter_id
    return None


def _section_span_end(
    start_page: FosterOssaPage,
    pages_by_number: dict[int, FosterOssaPage],
    last_page: int,
) -> int:
    start_section = classify_page_section(start_page.page_number, start_page.text)
    page_number = start_page.page_number
    while page_number + 1 <= last_page:
        next_page = pages_by_number.get(page_number + 1)
        if next_page is None:
            break
        next_section = classify_page_section(next_page.page_number, next_page.text)
        if next_section != start_section:
            break
        page_number += 1
    return page_number
