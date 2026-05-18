"""Poppler ``pdftohtml -xml`` reader for Bailly layout extraction."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO
from xml.etree import ElementTree as ET

from langnet.normalizer.utils import contains_greek, normalize_greekish_token
from langnet.parsing.bailly_text import repair_bailly_line_break_hyphenation

DICTIONARY_BODY_START_PAGE = 81
DICTIONARY_BODY_END_PAGE = 2574
BODY_TOP_MIN = 55
HEADWORD_FONT_SIZE = 14
LEFT_COLUMN_HEADWORD_MIN = 90
LEFT_COLUMN_HEADWORD_MAX = 119
RIGHT_COLUMN_HEADWORD_MIN = 470
RIGHT_COLUMN_HEADWORD_MAX = 504
ROMAN_MARKERS = {"I", "II", "III", "IV", "V"}
LETTER_MARKERS = {"A", "B", "C", "D", "E"}


@dataclass(frozen=True)
class PopplerFont:
    id: str
    size: int
    family: str
    color: str


@dataclass(frozen=True)
class PopplerText:
    text: str
    top: int
    left: int
    width: int
    height: int
    font_id: str
    bold: bool
    italic: bool


@dataclass(frozen=True)
class PopplerPage:
    number: int
    width: int
    height: int
    fonts: dict[str, PopplerFont]
    texts: list[PopplerText]


@dataclass(frozen=True)
class PopplerLine:
    page: int
    top: int
    left: int
    text: str
    chunks: list[PopplerText]


@dataclass(frozen=True)
class _PageChunk:
    page: PopplerPage
    chunk: PopplerText


@dataclass
class _EntryAccumulator:
    entry_id: str
    lemma: str
    lemma_norm: str
    page_start: int
    chunks: list[_PageChunk]


@dataclass(frozen=True)
class BaillyXmlPageAudit:
    page: int
    path: str
    section: str
    text_node_count: int
    entry_count: int
    first_lemma: str
    last_lemma: str
    warning: str

    def as_tsv_row(self) -> list[str]:
        return [
            str(self.page),
            self.path,
            self.section,
            str(self.text_node_count),
            str(self.entry_count),
            self.first_lemma,
            self.last_lemma,
            self.warning,
        ]


@dataclass(frozen=True)
class BaillyXmlAuditReport:
    page_count: int
    min_page: int | None
    max_page: int | None
    missing_pages: list[int]
    pages: list[BaillyXmlPageAudit]


def classify_bailly_page(page_number: int) -> str:
    """Classify physical Bailly PDF pages by book section."""
    if page_number < DICTIONARY_BODY_START_PAGE:
        return "front_matter"
    if page_number <= DICTIONARY_BODY_END_PAGE:
        return "dictionary_body"
    return "back_matter"


def audit_bailly_xml_pages(xml_dir: Path) -> BaillyXmlAuditReport:
    """Audit generated per-page Bailly XML files."""
    page_audits: list[BaillyXmlPageAudit] = []
    for path in sorted(xml_dir.glob("bailly-2020-p*.xml")):
        page_audits.append(_audit_xml_page(path))
    page_numbers = [audit.page for audit in page_audits]
    min_page = min(page_numbers) if page_numbers else None
    max_page = max(page_numbers) if page_numbers else None
    missing_pages = (
        [page for page in range(min_page, max_page + 1) if page not in set(page_numbers)]
        if min_page is not None and max_page is not None
        else []
    )
    return BaillyXmlAuditReport(
        page_count=len(page_audits),
        min_page=min_page,
        max_page=max_page,
        missing_pages=missing_pages,
        pages=page_audits,
    )


def extract_page_entries(page: PopplerPage) -> list[dict[str, Any]]:
    """Extract first-pass structural entries from one Poppler XML page.

    This is layout-driven: headwords come from the page's headword font/position,
    and structural blocks come from bold visible markers in reading order.
    """
    chunks = _reading_order_chunks(page)
    starts = [idx for idx, chunk in enumerate(chunks) if _is_headword_chunk(page, chunk)]
    entry_counts_by_column: dict[int, int] = {}
    entries: list[dict[str, Any]] = []
    for start_pos, start_idx in enumerate(starts):
        headword = chunks[start_idx]
        column = _column_for(page, headword)
        entry_counts_by_column[column] = entry_counts_by_column.get(column, 0) + 1
        next_idx = starts[start_pos + 1] if start_pos + 1 < len(starts) else len(chunks)
        entry_chunks = chunks[start_idx:next_idx]
        lemma = _lemma_from_headword(headword.text)
        blocks = _entry_blocks(page, entry_chunks)
        entry_id = f"bailly-p{page.number:03d}-c{column}-{entry_counts_by_column[column]:04d}"
        entries.append(
            {
                "entry_id": entry_id,
                "lemma": lemma,
                "lemma_norm": normalize_greekish_token(lemma) or lemma,
                "source": {"kind": "pdf", "page_start": page.number, "page_end": page.number},
                "raw_text": _join_chunk_text(entry_chunks),
                "blocks": blocks,
            }
        )
    return entries


def extract_book_entries_from_pages(
    pages: list[PopplerPage] | Iterator[PopplerPage],
) -> list[dict[str, Any]]:
    """Extract structural entries across page boundaries.

    Page-level extraction deliberately ignores text before the first headword on
    a page. The book-level pass keeps the previous entry open, so continuation
    pages and page-leading continuation columns are attached structurally.
    """
    entries: list[dict[str, Any]] = []
    current: _EntryAccumulator | None = None
    entry_counts_by_page_column: dict[tuple[int, int], int] = {}

    def finish_current() -> None:
        nonlocal current
        if current is None:
            return
        page_end = current.chunks[-1].page.number if current.chunks else current.page_start
        raw_chunks = [page_chunk.chunk for page_chunk in current.chunks]
        entries.append(
            {
                "entry_id": current.entry_id,
                "lemma": current.lemma,
                "lemma_norm": current.lemma_norm,
                "source": {"kind": "pdf", "page_start": current.page_start, "page_end": page_end},
                "raw_text": _join_chunk_text(raw_chunks),
                "blocks": _entry_blocks_from_page_chunks(current.chunks),
            }
        )
        current = None

    for page in pages:
        if classify_bailly_page(page.number) != "dictionary_body":
            continue
        chunks = _reading_order_chunks(page)
        starts = [idx for idx, chunk in enumerate(chunks) if _is_headword_chunk(page, chunk)]
        if not starts:
            if current is not None:
                current.chunks.extend(_PageChunk(page, chunk) for chunk in chunks)
            continue

        if starts[0] > 0 and current is not None:
            current.chunks.extend(_PageChunk(page, chunk) for chunk in chunks[: starts[0]])

        for start_pos, start_idx in enumerate(starts):
            finish_current()
            headword = chunks[start_idx]
            column = _column_for(page, headword)
            count_key = (page.number, column)
            entry_counts_by_page_column[count_key] = (
                entry_counts_by_page_column.get(count_key, 0) + 1
            )
            next_idx = starts[start_pos + 1] if start_pos + 1 < len(starts) else len(chunks)
            lemma = _lemma_from_headword(headword.text)
            current = _EntryAccumulator(
                entry_id=f"bailly-p{page.number:03d}-c{column}-{entry_counts_by_page_column[count_key]:04d}",
                lemma=lemma,
                lemma_norm=normalize_greekish_token(lemma) or lemma,
                page_start=page.number,
                chunks=[_PageChunk(page, chunk) for chunk in chunks[start_idx:next_idx]],
            )
    finish_current()
    return entries


def _audit_xml_page(path: Path) -> BaillyXmlPageAudit:
    warning = ""
    try:
        pages = list(iter_poppler_pages(path))
    except ET.ParseError as exc:
        page_number = _page_number_from_path(path)
        return BaillyXmlPageAudit(
            page=page_number,
            path=path.name,
            section=classify_bailly_page(page_number),
            text_node_count=0,
            entry_count=0,
            first_lemma="",
            last_lemma="",
            warning=f"parse_error:{exc.__class__.__name__}",
        )
    if len(pages) != 1:
        warning = f"page_count:{len(pages)}"
    if not pages:
        page_number = _page_number_from_path(path)
        return BaillyXmlPageAudit(
            page=page_number,
            path=path.name,
            section=classify_bailly_page(page_number),
            text_node_count=0,
            entry_count=0,
            first_lemma="",
            last_lemma="",
            warning=warning or "no_page",
        )

    page = pages[0]
    entries = (
        extract_page_entries(page) if classify_bailly_page(page.number) == "dictionary_body" else []
    )
    if classify_bailly_page(page.number) == "dictionary_body" and not entries and page.texts:
        warning = _append_warning(warning, "continuation_candidate")
    return BaillyXmlPageAudit(
        page=page.number,
        path=path.name,
        section=classify_bailly_page(page.number),
        text_node_count=len(page.texts),
        entry_count=len(entries),
        first_lemma=str(entries[0]["lemma"]) if entries else "",
        last_lemma=str(entries[-1]["lemma"]) if entries else "",
        warning=warning,
    )


def _page_number_from_path(path: Path) -> int:
    try:
        return int(path.stem.rsplit("p", 1)[1])
    except (IndexError, ValueError):
        return 0


def _append_warning(existing: str, new: str) -> str:
    return f"{existing};{new}" if existing else new


def iter_poppler_pages(source: str | Path | TextIO) -> Iterator[PopplerPage]:
    """Yield pages from Poppler's ``pdftohtml -xml`` output."""
    context = ET.iterparse(source, events=("end",))
    for _, elem in context:
        if elem.tag != "page":
            continue
        yield _parse_page(elem)
        elem.clear()


def page_lines(page: PopplerPage, *, y_tolerance: int = 3) -> list[PopplerLine]:
    """Group absolutely positioned text chunks into visual lines."""
    lines: list[list[PopplerText]] = []
    for chunk in sorted(page.texts, key=lambda item: (item.top, item.left)):
        if not lines or abs(lines[-1][0].top - chunk.top) > y_tolerance:
            lines.append([chunk])
        else:
            lines[-1].append(chunk)
    return [_line_from_chunks(page.number, chunks) for chunks in lines]


def _parse_page(elem: ET.Element) -> PopplerPage:
    fonts = {
        font.attrib["id"]: PopplerFont(
            id=font.attrib["id"],
            size=int(font.attrib.get("size") or 0),
            family=font.attrib.get("family") or "",
            color=font.attrib.get("color") or "",
        )
        for font in elem.findall("fontspec")
    }
    texts = [_parse_text(text_elem) for text_elem in elem.findall("text")]
    return PopplerPage(
        number=int(elem.attrib["number"]),
        width=int(elem.attrib["width"]),
        height=int(elem.attrib["height"]),
        fonts=fonts,
        texts=texts,
    )


def _parse_text(elem: ET.Element) -> PopplerText:
    text = "".join(elem.itertext()).strip()
    return PopplerText(
        text=text,
        top=int(elem.attrib["top"]),
        left=int(elem.attrib["left"]),
        width=int(elem.attrib["width"]),
        height=int(elem.attrib["height"]),
        font_id=elem.attrib["font"],
        bold=elem.find("b") is not None,
        italic=elem.find("i") is not None,
    )


def _reading_order_chunks(page: PopplerPage) -> list[PopplerText]:
    chunks: list[PopplerText] = []
    for column in (1, 2):
        column_texts = [
            chunk
            for chunk in page.texts
            if _column_for(page, chunk) == column and _is_body_chunk(chunk)
        ]
        column_page = PopplerPage(
            number=page.number,
            width=page.width,
            height=page.height,
            fonts=page.fonts,
            texts=column_texts,
        )
        for line in page_lines(column_page):
            chunks.extend(line.chunks)
    return chunks


def _is_body_chunk(chunk: PopplerText) -> bool:
    return chunk.top > BODY_TOP_MIN


def _column_for(page: PopplerPage, chunk: PopplerText) -> int:
    return 1 if chunk.left < page.width // 2 else 2


def _is_headword_chunk(page: PopplerPage, chunk: PopplerText) -> bool:
    font = page.fonts.get(chunk.font_id)
    if font is None:
        return False
    return (
        chunk.top > BODY_TOP_MIN
        and contains_greek(chunk.text)
        and "Hippias" in font.family
        and font.size == HEADWORD_FONT_SIZE
        and (
            LEFT_COLUMN_HEADWORD_MIN <= chunk.left <= LEFT_COLUMN_HEADWORD_MAX
            or RIGHT_COLUMN_HEADWORD_MIN <= chunk.left <= RIGHT_COLUMN_HEADWORD_MAX
        )
    )


def _lemma_from_headword(text: str) -> str:
    return text.split(",", 1)[0].strip()


def _entry_blocks(page: PopplerPage, chunks: list[PopplerText]) -> list[dict[str, Any]]:
    return _entry_blocks_from_page_chunks([_PageChunk(page, chunk) for chunk in chunks])


def _entry_blocks_from_page_chunks(page_chunks: list[_PageChunk]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current_path = "00"
    current_marker = "head"
    current_marker_chunk: _PageChunk | None = None
    current_chunks: list[_PageChunk] = []
    path_state = _MarkerPathState()

    def flush() -> None:
        if not current_chunks and current_marker_chunk is None:
            return
        blocks.append(
            {
                "path": current_path,
                "marker": current_marker,
                "text": _join_chunk_text([page_chunk.chunk for page_chunk in current_chunks]),
                "layout": _block_layout(current_chunks, current_marker_chunk),
            }
        )

    for page_chunk in page_chunks:
        chunk = page_chunk.chunk
        if _is_structural_marker(page_chunk.page, chunk):
            flush()
            current_marker = _structural_marker_text(page_chunk.page, chunk)
            current_path = path_state.path_for(current_marker)
            current_marker_chunk = page_chunk
            current_chunks = []
        else:
            current_chunks.append(page_chunk)
    flush()
    return blocks


def _is_structural_marker(page: PopplerPage, chunk: PopplerText) -> bool:
    font = page.fonts.get(chunk.font_id)
    if font is not None and "fleche" in font.family:
        return True
    return chunk.bold and (
        chunk.text.isdigit() or chunk.text in ROMAN_MARKERS or chunk.text in LETTER_MARKERS
    )


def _structural_marker_text(page: PopplerPage, chunk: PopplerText) -> str:
    font = page.fonts.get(chunk.font_id)
    if font is not None and "fleche" in font.family:
        return "E"
    return chunk.text


class _MarkerPathState:
    def __init__(self) -> None:
        self._active_paths: dict[int, str] = {}
        self._active_markers: dict[int, str] = {}
        self._next_indexes: dict[int, int] = {1: 1}

    def path_for(self, marker: str) -> str:
        depth = self._depth_for(marker)
        index = self._next_indexes.get(depth, 1 if depth == 1 else 0)
        path = f"{index:02d}" if depth == 1 else f"{self._active_paths[depth - 1]}:{index:02d}"
        self._next_indexes[depth] = index + 1
        for stale_depth in [key for key in self._active_paths if key > depth]:
            del self._active_paths[stale_depth]
            del self._active_markers[stale_depth]
            self._next_indexes.pop(stale_depth, None)
        self._active_paths[depth] = path
        self._active_markers[depth] = marker
        self._next_indexes[depth + 1] = 0
        return path

    def _depth_for(self, marker: str) -> int:
        if marker in LETTER_MARKERS:
            return 1
        if marker in ROMAN_MARKERS:
            return 2 if self._active_markers.get(1) in LETTER_MARKERS else 1
        if marker.isdigit():
            for depth in sorted(self._active_markers, reverse=True):
                if self._active_markers[depth] in ROMAN_MARKERS:
                    return depth + 1
            if self._active_markers.get(1) in LETTER_MARKERS:
                return 2
            if self._active_paths:
                return max(self._active_paths) + 1
        return 1


def _join_chunk_text(chunks: list[PopplerText]) -> str:
    return _join_text_parts(chunk.text for chunk in chunks)


def _block_layout(chunks: list[_PageChunk], marker_chunk: _PageChunk | None) -> dict[str, Any]:
    relevant = [*chunks, *([marker_chunk] if marker_chunk is not None else [])]
    first = relevant[0]
    return {
        "page": first.page.number,
        "column": _column_for(first.page, first.chunk),
        "top": min(page_chunk.chunk.top for page_chunk in relevant),
        "left": min(page_chunk.chunk.left for page_chunk in relevant),
        "marker_x": marker_chunk.chunk.left if marker_chunk is not None else None,
        "text_start_x": min((page_chunk.chunk.left for page_chunk in chunks), default=None),
    }


def _line_from_chunks(page_number: int, chunks: list[PopplerText]) -> PopplerLine:
    ordered = sorted(chunks, key=lambda item: item.left)
    return PopplerLine(
        page=page_number,
        top=min(chunk.top for chunk in ordered),
        left=min(chunk.left for chunk in ordered),
        text=_join_text_parts(chunk.text for chunk in ordered),
        chunks=ordered,
    )


def _join_text_parts(parts: Iterator[str]) -> str:
    return repair_bailly_line_break_hyphenation(" ".join(part for part in parts if part).strip())
