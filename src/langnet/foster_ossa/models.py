from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class FosterOssaPage:
    page_number: int
    source_path: str
    extraction_tool: str
    text: str
    text_hash: str
    warning: str = ""

    @classmethod
    def from_text(
        cls,
        *,
        page_number: int,
        source_path: str,
        extraction_tool: str,
        text: str,
        warning: str = "",
    ) -> FosterOssaPage:
        stripped_text = text.strip()
        return cls(
            page_number=page_number,
            source_path=source_path,
            extraction_tool=extraction_tool,
            text=stripped_text,
            text_hash=sha256(stripped_text.encode("utf-8")).hexdigest(),
            warning=warning,
        )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FosterOssaStructuredPage:
    page_number: int
    source_path: str
    extraction_tool: str
    section: str
    text: str
    text_hash: str
    warning: str = ""

    @classmethod
    def from_page(
        cls,
        page: FosterOssaPage,
        *,
        section: str,
    ) -> FosterOssaStructuredPage:
        return cls(
            page_number=page.page_number,
            source_path=page.source_path,
            extraction_tool=page.extraction_tool,
            section=section,
            text=page.text,
            text_hash=page.text_hash,
            warning=page.warning,
        )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FosterOssaEncounter:
    encounter_id: str
    experience: int
    encounter: int
    page_start: int
    page_end: int
    heading: str
    title: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FosterOssaConceptMention:
    term: str
    normalized_term: str
    category: str
    page_number: int
    encounter_id: str | None
    context: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FosterOssaTocEntry:
    toc_id: str
    source_page_number: int
    section_kind: str
    experience: int
    encounter: int | None
    global_encounter: int | None
    encounter_id: str | None
    latin_title: str
    english_title: str
    printed_page: int
    inferred_page_number: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FosterOssaSummaryPlan:
    source_ref: str
    scope: str
    model: str
    prompt_version: str
    input_hash: str
    input_text: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
