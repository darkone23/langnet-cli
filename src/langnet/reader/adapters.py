from __future__ import annotations

import html
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from langnet.reader.models import (
    ReaderEdition,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderWork,
)

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
CTS_WORK_TAIL_PARTS = 2
PERSEUS_MIN_FILENAME_PARTS = 3
PERSEUS_TEXT_DIV_TYPES = {"edition", "translation", "commentary"}
PERSEUS_TEXT_ROOT_TYPES = PERSEUS_TEXT_DIV_TYPES | {"text"}
PERSEUS_MILESTONE_LEVELS = {
    "book": 0,
    "chapter": 1,
    "section": 2,
    "line": 3,
}
PERSEUS_LANGUAGE_CODES = {
    "en": "eng",
    "eng": "eng",
    "grc": "grc",
    "greek": "grc",
    "la": "lat",
    "lat": "lat",
}
XML_PREDEFINED_ENTITIES = {"amp", "apos", "gt", "lt", "quot"}
PERSEUS_ENTITY_REPLACEMENTS = {
    "Perseus.OCR": "",
    "Perseus.publish": "",
}
PERSEUS_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9_.-]*);")
XML_INVALID_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
SANSKRIT_NUMBERED_SAMPLE_LINES = 500
SANSKRIT_NUMBERED_MIN_SAMPLE_MATCHES = 3
SANSKRIT_NUMBERED_LINE_RE = re.compile(r"^(?P<code>\d{8})\s+(?P<text>.+)$")
GRETIL_AUTHOR_RE = re.compile(r"(?:^|_)sa_(?P<author>[^-_.]+)-")
GRETIL_WORK_RE = re.compile(r"(?:^|_)sa_(?P<body>[^.]+)$")
LEGACY_ENGLISH_WORDS = frozenset(
    {
        "and",
        "are",
        "both",
        "but",
        "for",
        "from",
        "have",
        "his",
        "is",
        "lord",
        "not",
        "of",
        "shall",
        "that",
        "the",
        "their",
        "them",
        "unto",
        "was",
        "were",
        "which",
        "with",
    }
)
LEGACY_ENGLISH_ANCHOR_WORDS = frozenset({"and", "of", "shall", "that", "the", "unto", "which"})
LEGACY_LATIN_WORDS = frozenset(
    {
        "ad",
        "cum",
        "de",
        "est",
        "et",
        "in",
        "non",
        "per",
        "pro",
        "quae",
        "quam",
        "qui",
        "quod",
        "sed",
        "sunt",
        "ut",
    }
)
LEGACY_ENGLISH_MIN_WORDS = 6
LEGACY_ENGLISH_MIN_ANCHOR_WORDS = 2
LEGACY_ENGLISH_MIN_RATIO = 2
GRETIL_TITLE_PREFIX_EXACT = {
    "aSTasAhasrikA",
    "advayazatikA",
    "IzopaniSad",
    "larger",
}
GRETIL_TITLE_PREFIX_SUFFIXES = (
    "avadAna",
    "kAvya",
    "mAlA",
    "purANa",
    "prajJApAramitA",
    "saMhitA",
    "smRti",
    "sUtra",
    "tantra",
    "upaniSad",
    "vyAkaraNa",
    "zAstra",
)
GRETIL_VARIANT_MARKER_RE = re.compile(r"^[A-Z]$|^\d+(?:-\d+)?$")
GRETIL_TITLE_TRAILING_DESCRIPTORS_RE = re.compile(r"-(?:alt|comm\d*|ed[^-]*)$")
SANSKRIT_TEXT_WORK_METADATA = {
    "latyayanashrautasutra": ("Lāṭyāyana Śrautasūtra", "Lāṭyāyana"),
    "sadvimsabrahmana": ("Ṣaḍviṃśa Brāhmaṇa", "Anonymous"),
}
SANSKRIT_PDF_ENCODING = str.maketrans(
    {
        "À": "ā",
        "Á": "ī",
        "Â": "ū",
        "Ã": "ṛ",
        "Å": "ṝ",
        "Æ": "ḷ",
        "Ç": "ṅ",
        "È": "ñ",
        "É": "ṇ",
        "Ê": "ṭ",
        "Ë": "ḍ",
        "Ì": "ś",
        "Í": "ṣ",
        "Î": "ṃ",
        "Ï": "ḥ",
        "Þ": "Ś",
    }
)
DIGILIBLT_TITLE_AUTHORS = {
    "Appendix Probi": "Probus (Ps.)",
    "Asclepius": "Anonymous",
    "Mallius Theodorus de metris": "Mallius Theodorus",
    "[Priscianus] de accentibus": "Priscianus (Ps.)",
    "Rufinus, Commentaria in metra Terentiana": "Rufinus Antiochensis",
    "Rufinus, De compositione et de numeris oratorum": "Rufinus Antiochensis",
    "Peregrinatio Egeriae": "Egeria",
    "[Victorini siue Palaemonis] Ars": "Victorinus sive Palaemon",
    "Periochae Liuii": "Livius",
    "[Gaius] Gai Institutionum epitome": "Gaius",
    "Augustini Ars Breuiata": "Augustinus",
    "Servius, Centimeter": "Servius",
}
DIGILIBLT_AUTHOR_CANONICAL = {
    "Aphtonius = Marius Victorinus (Ps.)": "Aphthonius = Marius Victorinus (Ps.)",
    "Augustinus, Aurelius": "Augustinus",
    "Aurelius Victor Ps.": "Aurelius Victor (Ps.)",
    "Boethius (Anicius Manlius Seuerinus Boethius)": "Boethius",
    "Cassiodorus (Flauius Magnus Aurelius Cassiodorus Senator)": "Cassiodorus",
    "Censorinus (ps.)": "Censorinus (Ps.)",
    "Donatus, Aelius": "Aelius Donatus",
    "Gargilius Martialis Ps.": "Gargilius Martialis (Ps.)",
    "Iulius Rufinianus Ps.": "Iulius Rufinianus (Ps.)",
    "Macrobius Ambrosius Theodosius": "Macrobius",
    "Ps. Sergius": "Sergius (Ps.)",
    "Seruius": "Servius",
    "Vegetius (Flauius Vegetius Renatus)": "Flavius Vegetius Renatus",
    "ps. Phocas": "Phocas (Ps.)",
    "pseudo-Agennius Vrbicus": "Agennius Vrbicus (Ps.)",
}


@dataclass(frozen=True)
class ParsedBook:
    work: ReaderWork
    edition: ReaderEdition
    segments: list[ReaderSegment]
    addresses: list[ReaderSegmentAddress]


@dataclass(frozen=True)
class _PerseusLineContext:
    work: ReaderWork
    edition: ReaderEdition
    segments: list[ReaderSegment]
    addresses: list[ReaderSegmentAddress]
    seen_citations: set[str]


@dataclass(frozen=True)
class _ReaderBookSeed:
    collection_id: str
    language: str
    title: str
    author: str
    source_id: str
    edition_label: str
    source_path: Path
    author_id: str | None = None
    cts_work_urn: str | None = None


@dataclass(frozen=True)
class _ReaderSegmentRow:
    sort_key: int
    segment_kind: str
    citation_path: str
    text: str
    source_text: str | None = None


@dataclass(frozen=True)
class _LegacyParsedRow:
    work_number: str
    row: _ReaderSegmentRow


@dataclass(frozen=True)
class LegacyIdtWork:
    author_id: str
    author_name: str
    work_number: str
    work_name: str
    start_block: int
    level_labels: tuple[str, ...] = ()


def parse_perseus_tei(path: Path) -> ParsedBook:
    root = _parse_perseus_xml(path)
    edition_node = _find_perseus_text_node(root)
    edition_urn = ""
    if edition_node is not None:
        edition_urn = edition_node.attrib.get("n", "").strip()
    else:
        edition_node = _find_first(root, "text")
        edition_urn = _perseus_edition_urn_from_path(path) or ""
    if edition_node is None:
        msg = f"{path}: missing TEI text div"
        raise ValueError(msg)

    if not edition_urn.startswith("urn:cts:"):
        msg = f"{path}: edition div n must be a CTS URN"
        raise ValueError(msg)

    work_urn = _work_urn_from_edition_urn(edition_urn)
    language = _normalize_perseus_language(
        edition_node.attrib.get(XML_LANG) or _language_from_cts_urn(work_urn)
    )
    title = _find_text(root, "title") or _work_tail(work_urn)
    author = _find_text(root, "author") or "Unknown"
    author_id, source_id = _source_ids_from_work_urn(work_urn)

    edition = ReaderEdition(
        edition_id=edition_urn,
        work_id=work_urn,
        label=f"{title} ({edition_urn.rsplit('.', 1)[-1]})",
        language=language,
        source_path=path,
        cts_edition_urn=edition_urn,
    )
    work = ReaderWork(
        work_id=work_urn,
        collection_id="perseus",
        language=language,
        title=title,
        author=author,
        author_id=author_id,
        source_id=source_id,
        cts_work_urn=work_urn,
    )

    segments: list[ReaderSegment] = []
    addresses: list[ReaderSegmentAddress] = []
    context = _PerseusLineContext(
        work=work,
        edition=edition,
        segments=segments,
        addresses=addresses,
        seen_citations=set(),
    )
    _collect_perseus_lines(edition_node, [], context)
    if not segments:
        _collect_perseus_milestone_segments(edition_node, [], context)

    return ParsedBook(work=work, edition=edition, segments=segments, addresses=addresses)


def _parse_perseus_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as original_error:
        text = path.read_text(encoding="utf-8")
        repaired = _repair_perseus_xml_text(text)
        if repaired == text:
            return _recover_perseus_xml(repaired, original_error=original_error)
        try:
            return ET.fromstring(repaired)
        except ET.ParseError:
            return _recover_perseus_xml(repaired, original_error=original_error)


def _recover_perseus_xml(text: str, *, original_error: ET.ParseError) -> ET.Element:
    try:
        from lxml import etree as LET  # type: ignore[import-untyped]  # noqa: PLC0415
    except ImportError:
        raise original_error
    parser = LET.XMLParser(recover=True, resolve_entities=False, no_network=True)
    root = LET.fromstring(text.encode("utf-8"), parser=parser)
    if root is None:
        raise original_error
    return root


def _repair_perseus_xml_text(text: str) -> str:
    text = XML_INVALID_CONTROL_RE.sub("", text)
    return PERSEUS_ENTITY_RE.sub(_repair_perseus_entity, text)


def _repair_perseus_entity(match: re.Match[str]) -> str:
    name = match.group(1)
    if name in XML_PREDEFINED_ENTITIES:
        return match.group(0)
    if name in PERSEUS_ENTITY_REPLACEMENTS:
        return PERSEUS_ENTITY_REPLACEMENTS[name]
    unescaped = html.unescape(match.group(0))
    if unescaped != match.group(0):
        return unescaped
    return ""


def parse_digiliblt_tei(path: Path) -> ParsedBook:
    root = ET.parse(path).getroot()
    title = _find_text(root, "title") or path.stem
    author, _resolution = resolve_digiliblt_author(
        explicit_author=_find_text(root, "author"),
        title=title,
        source_desc=_find_text(root, "sourceDesc") or "",
    )
    source_id = path.stem
    seed = _ReaderBookSeed(
        collection_id="digiliblt",
        language="lat",
        title=title,
        author=author,
        source_id=source_id,
        edition_label="digilibLT TEI",
        source_path=path,
    )
    body = _find_first(root, "body") or root
    paragraphs = [
        _normalize_text("".join(node.itertext()))
        for node in body.iter()
        if _local_name(node.tag) == "p"
    ]
    return _parsed_reader_book(
        seed,
        [(index, "paragraph", text) for index, text in _numbered_nonempty(paragraphs)],
    )


def resolve_digiliblt_author(
    *,
    explicit_author: str | None,
    title: str,
    source_desc: str,
) -> tuple[str, str]:
    if explicit_author:
        canonical = normalize_digiliblt_author(explicit_author)
        resolution = "normalized_author" if canonical != explicit_author else "source_author"
        return canonical, resolution
    if title in DIGILIBLT_TITLE_AUTHORS:
        return DIGILIBLT_TITLE_AUTHORS[title], "resolved_from_title"
    lowered = f"{title} {source_desc}".lower()
    if "incerti auctoris" in lowered:
        return "Uncertain author", "verified_uncertain"
    if "anonymus" in lowered or "anonymi " in lowered or "anonymous" in lowered:
        return "Anonymous", "verified_anonymous"
    return "Unattributed", "source_author_blank"


def normalize_digiliblt_author(author: str) -> str:
    return DIGILIBLT_AUTHOR_CANONICAL.get(author, author)


def _sanskrit_author_from_path(path: Path) -> str | None:
    match = GRETIL_AUTHOR_RE.search(path.stem)
    if match is None:
        return None
    prefix = match.group("author")
    if _gretil_prefix_looks_like_work_title(prefix, path.stem):
        return None
    return _gretil_code_to_iast(prefix)


def _sanskrit_title_from_path(path: Path) -> str | None:
    match = GRETIL_WORK_RE.search(path.stem)
    if match is None:
        return None
    body = match.group("body")
    if "-" in body:
        prefix, title = body.split("-", 1)
        if _gretil_prefix_looks_like_work_title(prefix, path.stem):
            title = body
    else:
        title = body
    title = GRETIL_TITLE_TRAILING_DESCRIPTORS_RE.sub("", title)
    return _gretil_title_code_to_iast(title)


def _gretil_prefix_looks_like_work_title(prefix: str, stem: str) -> bool:
    if "-or-" in stem:
        return True
    body = stem.split("sa_", 1)[-1]
    if "-" in body:
        _prefix, rest = body.split("-", 1)
        if GRETIL_VARIANT_MARKER_RE.match(rest):
            return True
    return prefix in GRETIL_TITLE_PREFIX_EXACT or prefix.endswith(GRETIL_TITLE_PREFIX_SUFFIXES)


def _gretil_title_code_to_iast(value: str) -> str:
    return " ".join(
        word[:1].upper() + word[1:]
        for word in _gretil_code_to_iast(value.replace("-", " ")).split()
    )


def _gretil_code_to_iast(value: str) -> str:
    replacements = {
        "A": "ā",
        "I": "ī",
        "U": "ū",
        "R": "ṛ",
        "L": "ḷ",
        "M": "ṃ",
        "H": "ḥ",
        "G": "ṅ",
        "J": "ñ",
        "T": "ṭ",
        "D": "ḍ",
        "N": "ṇ",
        "z": "ś",
        "S": "ṣ",
    }
    text = "".join(replacements.get(ch, ch) for ch in value.replace("_", " "))
    return text[:1].upper() + text[1:]


def parse_sanskrit_json(path: Path) -> ParsedBook:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{path}: Sanskrit JSON root must be an object"
        raise ValueError(msg)
    title = str(payload.get("text") or path.stem)
    author = str(payload.get("author") or _sanskrit_author_from_path(path) or "Unknown")
    edition_label = str(payload.get("edition") or "json")
    seed = _ReaderBookSeed(
        collection_id="sanskrit_json",
        language="san",
        title=title,
        author=author,
        source_id=_path_source_id(path),
        edition_label=edition_label,
        source_path=path,
    )
    lines_value = payload.get("lines", [])
    if not isinstance(lines_value, list):
        msg = f"{path}: Sanskrit JSON lines must be a list"
        raise ValueError(msg)
    lines = [_sanskrit_json_line_text(line) for line in lines_value]
    return _parsed_reader_book(
        seed,
        [(index, "line", text) for index, text in _numbered_nonempty(lines)],
    )


def parse_sanskrit_plain_text(
    path: Path,
    *,
    collection_id: str,
    language: str,
) -> ParsedBook:
    if collection_id == "sanskrit_texts" and language == "san" and _looks_numbered_sanskrit(path):
        return parse_sanskrit_numbered_text(path)
    text = path.read_text(encoding="utf-8")
    header_metadata = _sanskrit_plain_header_metadata(text.splitlines())
    seed = _ReaderBookSeed(
        collection_id=collection_id,
        language=language,
        title=header_metadata.get("title") or _sanskrit_title_from_path(path) or path.stem,
        author=header_metadata.get("author") or _sanskrit_author_from_path(path) or "Unknown",
        source_id=_path_source_id(path),
        edition_label="plain text",
        source_path=path,
    )
    lines = [_normalize_text(line) for line in text.splitlines()]
    return _parsed_reader_book(
        seed,
        [(index, "line", text) for index, text in _numbered_nonempty(lines)],
    )


def parse_sanskrit_plain_text_group(
    paths: list[Path],
    *,
    collection_id: str,
    language: str,
) -> ParsedBook:
    if not paths:
        msg = "Sanskrit plain text group requires at least one file"
        raise ValueError(msg)
    sorted_paths = sorted(paths, key=_natural_path_key)
    work_dir = sorted_paths[0].parent.parent
    curated_metadata = SANSKRIT_TEXT_WORK_METADATA.get(work_dir.name)
    title, author = curated_metadata or (_title_from_slug(work_dir.name), "Unknown")
    if curated_metadata is None:
        header_metadata = _sanskrit_group_header_metadata(sorted_paths)
        title = header_metadata.get("title") or title
        author = header_metadata.get("author") or author
    seed = _ReaderBookSeed(
        collection_id=collection_id,
        language=language,
        title=title,
        author=author,
        source_id=f"{work_dir.name}_{sorted_paths[0].parent.name}",
        edition_label="split plain text",
        source_path=sorted_paths[0],
    )
    seen: set[str] = set()
    rows: list[_ReaderSegmentRow] = []
    for path in sorted_paths:
        lines = [
            _normalize_text(line.lstrip("\ufeff"))
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        for line_index, text in _numbered_nonempty(lines):
            rows.append(
                _ReaderSegmentRow(
                    sort_key=len(rows) + 1,
                    segment_kind="line",
                    citation_path=_unique_plain_citation_path(
                        f"{path.stem}.{line_index}",
                        seen=seen,
                    ),
                    text=text,
                )
            )
    return _parsed_reader_book_with_citations(seed, rows)


def _sanskrit_plain_header_metadata(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for raw_line in lines[:20]:
        line = raw_line.strip().lstrip("\ufeff")
        if not line.startswith("#"):
            if line:
                break
            continue
        key, separator, value = line[1:].partition(":")
        if not separator:
            continue
        normalized_key = key.strip().casefold()
        clean_value = _normalize_text(value)
        if not clean_value:
            continue
        if normalized_key == "author":
            metadata["author"] = clean_value
        elif normalized_key == "text":
            metadata["title"] = clean_value
    return metadata


def _sanskrit_group_header_metadata(paths: list[Path]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for path in paths[:5]:
        lines = path.read_text(encoding="utf-8").splitlines()
        metadata.update(_sanskrit_plain_header_metadata(lines))
        if "title" in metadata and "author" in metadata:
            break
    return metadata


def parse_sanskrit_numbered_text(path: Path) -> ParsedBook:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = _sanskrit_numbered_title(lines) or path.stem
    seed = _ReaderBookSeed(
        collection_id="sanskrit_texts",
        language="san",
        title=title,
        author="Unknown",
        source_id=_path_source_id(path),
        edition_label="numbered plain text",
        source_path=path,
    )
    seen: set[str] = set()
    rows: list[_ReaderSegmentRow] = []
    for line in lines:
        match = SANSKRIT_NUMBERED_LINE_RE.match(line.strip())
        if match is None:
            continue
        citation_path = _unique_plain_citation_path(
            _sanskrit_numbered_citation(match.group("code")),
            seen=seen,
        )
        source_text = _normalize_text(_decode_sanskrit_pdf_encoding(match.group("text")))
        text = source_text.replace("_", " ")
        rows.append(
            _ReaderSegmentRow(
                sort_key=len(rows) + 1,
                segment_kind="line",
                citation_path=citation_path,
                text=text,
                source_text=source_text,
            )
        )
    return _parsed_reader_book_with_citations(seed, rows)


def parse_legacy_text_dump(
    path: Path,
    *,
    collection_id: str,
    language: str,
) -> ParsedBook:
    seed = _ReaderBookSeed(
        collection_id=collection_id,
        language=language,
        title=path.stem,
        author="Unknown",
        source_id=_slug(path.stem),
        edition_label="legacy text dump",
        source_path=path,
    )
    return _legacy_book_from_raw(seed, path.read_bytes(), language=language)


def parse_legacy_text_dump_with_idt(
    path: Path,
    *,
    idt_path: Path,
    collection_id: str,
    language: str,
) -> list[ParsedBook]:
    works = _parse_legacy_idt(idt_path)
    if not works:
        return [parse_legacy_text_dump(path, collection_id=collection_id, language=language)]

    raw = path.read_bytes()
    parsed_rows = _legacy_rows_from_raw(raw, language=language)
    rows_by_work = _legacy_rows_by_inline_work(parsed_rows, works)
    rows_by_language: dict[str, list[_LegacyParsedRow]] = {language: parsed_rows}
    rows_by_work_language: dict[str, dict[str, list[_ReaderSegmentRow]]] = {}
    books: list[ParsedBook] = []
    for index, work in enumerate(works):
        source_id = f"{path.stem}.{work.work_number}"
        rows: list[_ReaderSegmentRow] = (
            rows_by_work.get(work.work_number, []) if rows_by_work else []
        )
        next_start = works[index + 1].start_block if index + 1 < len(works) else None
        start = work.start_block * LEGACY_BLOCK_SIZE
        end = next_start * LEGACY_BLOCK_SIZE if next_start is not None else len(raw)
        sample_text = _legacy_work_sample_text(rows=rows, raw=raw[start:end])
        work_language = _legacy_work_language(
            collection_id=collection_id,
            source_stem=path.stem,
            default_language=language,
            work=work,
            sample_text=sample_text,
        )
        if rows_by_work and work_language != language:
            if work_language not in rows_by_language:
                rows_by_language[work_language] = _legacy_rows_from_raw(
                    raw,
                    language=work_language,
                )
            if work_language not in rows_by_work_language:
                rows_by_work_language[work_language] = _legacy_rows_by_inline_work(
                    rows_by_language[work_language],
                    works,
                )
            rows = rows_by_work_language[work_language].get(work.work_number, rows)
        author_id = _legacy_author_id(
            collection_id=collection_id,
            path_stem=path.stem,
            author_id=work.author_id,
        )
        seed = _ReaderBookSeed(
            collection_id=collection_id,
            language=work_language,
            title=work.work_name,
            author=work.author_name,
            source_id=source_id,
            edition_label=_legacy_edition_label(work.level_labels),
            source_path=path,
            author_id=author_id,
            cts_work_urn=_legacy_cts_work_urn(
                collection_id=collection_id,
                author_id=author_id,
                work_number=work.work_number,
            ),
        )
        if rows_by_work:
            books.append(_parsed_reader_book_with_citations(seed, rows))
            continue
        books.append(_legacy_book_from_raw(seed, raw[start:end], language=work_language))
    return books


def parse_legacy_idt_metadata(path: Path) -> list[LegacyIdtWork]:
    return _parse_legacy_idt(path)


def parse_dcs_conllu(path: Path) -> ParsedBook:
    text = path.read_text(encoding="utf-8")
    metadata = _dcs_metadata(text)
    title = metadata.get("text") or path.stem
    source_id = metadata.get("text_id") or _slug(title)
    seed = _ReaderBookSeed(
        collection_id="sanskrit_dcs",
        language="san",
        title=title,
        author="Unknown",
        source_id=f"dcs_{source_id}",
        edition_label="DCS CoNLL-U",
        source_path=path,
    )
    return _parsed_reader_book_with_citations(seed, _dcs_conllu_rows(text))


def parse_dcs_conllu_group(paths: Iterable[Path]) -> ParsedBook:
    sorted_paths = sorted(paths)
    if not sorted_paths:
        msg = "DCS CoNLL-U group must contain at least one file"
        raise ValueError(msg)
    first_text = sorted_paths[0].read_text(encoding="utf-8")
    metadata = _dcs_metadata(first_text)
    title = metadata.get("text") or sorted_paths[0].parent.name
    source_id = metadata.get("text_id") or _slug(title)
    seed = _ReaderBookSeed(
        collection_id="sanskrit_dcs",
        language="san",
        title=title,
        author="Unknown",
        source_id=f"dcs_{source_id}",
        edition_label="DCS CoNLL-U",
        source_path=sorted_paths[0],
    )
    rows: list[_ReaderSegmentRow] = []
    seen_citations: set[str] = set()
    for index, path in enumerate(sorted_paths):
        text = first_text if index == 0 else path.read_text(encoding="utf-8")
        metadata = _dcs_metadata(text)
        chapter_id = metadata.get("chapter_id", "")
        for row in _dcs_conllu_rows(
            text,
            offset=len(rows),
        ):
            citation_path = _unique_dcs_citation_path(
                row.citation_path,
                chapter_id=chapter_id,
                seen=seen_citations,
            )
            rows.append(
                _ReaderSegmentRow(
                    sort_key=row.sort_key,
                    segment_kind=row.segment_kind,
                    citation_path=citation_path,
                    text=row.text,
                )
            )
    return _parsed_reader_book_with_citations(seed, rows)


def _dcs_conllu_rows(text: str, *, offset: int = 0) -> list[_ReaderSegmentRow]:
    rows: list[_ReaderSegmentRow] = []
    for block in re.split(r"\n\s*\n", text):
        sentence_text = ""
        sent_id = ""
        for line in block.splitlines():
            if line.startswith("# text ="):
                sentence_text = _normalize_text(line.split("=", 1)[1])
            elif line.startswith("# sent_id ="):
                sent_id = _normalize_text(line.split("=", 1)[1])
        if sentence_text:
            citation_path = sent_id or str(len(rows) + 1)
            rows.append(
                _ReaderSegmentRow(
                    sort_key=offset + len(rows) + 1,
                    segment_kind="sentence",
                    citation_path=citation_path,
                    text=sentence_text,
                )
            )
    return rows


def _unique_dcs_citation_path(
    citation_path: str,
    *,
    chapter_id: str,
    seen: set[str],
) -> str:
    candidate = citation_path
    if candidate in seen and chapter_id:
        candidate = f"{chapter_id}.{citation_path}"
    suffix = 2
    while candidate in seen:
        candidate = f"{citation_path}.{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def _legacy_book_from_raw(
    seed: _ReaderBookSeed,
    raw: bytes,
    *,
    language: str,
) -> ParsedBook:
    if not any(byte >= LEGACY_HIGH_BIT for byte in raw):
        return _legacy_book_from_text(seed, raw.decode("latin-1", errors="ignore"))
    rows = [parsed.row for parsed in _legacy_rows_from_raw(raw, language=language)]
    return _parsed_reader_book_with_citations(seed, rows)


def _legacy_work_sample_text(
    *,
    rows: list[_ReaderSegmentRow],
    raw: bytes,
) -> str:
    if rows:
        return " ".join(row.text for row in rows[:50])
    return _decode_legacy_text(raw[: LEGACY_BLOCK_SIZE // 2])


def _legacy_work_language(
    *,
    collection_id: str,
    source_stem: str,
    default_language: str,
    work: LegacyIdtWork,
    sample_text: str,
) -> str:
    if collection_id != "phi":
        return default_language

    work_title = work.work_name.casefold()
    author_name = work.author_name.casefold()
    source_metadata = f"{source_stem} {author_name}".casefold()
    language = default_language
    if "hebrew bible" in source_metadata or "mt or bhs" in source_metadata:
        language = "heb"
    elif (
        "coptic" in source_metadata or "sahidic" in source_metadata or "sahiddic" in source_metadata
    ):
        language = "cop"
    elif (
        "septuagint" in source_metadata
        or "old greek bible" in source_metadata
        or "greek new testament" in source_metadata
    ):
        language = "grc"
    elif "(latin" in work_title or "latin works" in work_title:
        language = "lat"
    elif (
        "(english" in work_title
        or "english bible" in source_metadata
        or (default_language == "lat" and _legacy_text_looks_english(sample_text))
    ):
        language = "eng"
    return language


def _legacy_text_looks_english(text: str) -> bool:
    words = re.findall(r"[A-Za-z]+", text.casefold())
    if not words:
        return False
    english_hits = sum(1 for word in words if word in LEGACY_ENGLISH_WORDS)
    english_anchors = {word for word in words if word in LEGACY_ENGLISH_ANCHOR_WORDS}
    latin_hits = sum(1 for word in words if word in LEGACY_LATIN_WORDS)
    return (
        english_hits >= LEGACY_ENGLISH_MIN_WORDS
        and len(english_anchors) >= LEGACY_ENGLISH_MIN_ANCHOR_WORDS
        and english_hits >= max(1, latin_hits) * LEGACY_ENGLISH_MIN_RATIO
    )


def _legacy_author_id(*, collection_id: str, path_stem: str, author_id: str) -> str:
    digits = "".join(ch for ch in author_id if ch.isdigit())
    if collection_id == "tlg":
        return path_stem if path_stem.startswith("tlg") else f"tlg:{author_id or path_stem}"
    if collection_id == "phi":
        if path_stem.startswith("lat") and digits:
            return f"phi{digits.zfill(4)}"
        if path_stem.startswith("phi"):
            return path_stem
        return f"phi{digits.zfill(4)}" if digits else path_stem
    return author_id or path_stem


def _legacy_cts_work_urn(
    *,
    collection_id: str,
    author_id: str | None,
    work_number: str,
) -> str | None:
    if not author_id or not work_number.isdigit():
        return None
    if collection_id == "tlg" and re.fullmatch(r"tlg\d{4}", author_id):
        return f"urn:cts:greekLit:{author_id}.tlg{work_number.zfill(3)}"
    if collection_id == "phi" and re.fullmatch(r"phi\d{4}", author_id):
        return f"urn:cts:latinLit:{author_id}.phi{work_number.zfill(3)}"
    return None


def _legacy_rows_from_raw(raw: bytes, *, language: str) -> list[_LegacyParsedRow]:
    parsed_rows: list[_LegacyParsedRow] = []
    seen_citations_by_work: dict[str, set[str]] = {}
    state = _LegacyBookmarkState()
    line = bytearray()
    i = 0
    while i < len(raw):
        byte = raw[i]
        if byte == 0:
            i += 1
            continue
        if byte < LEGACY_HIGH_BIT:
            line.append(byte)
            i += 1
            continue
        _append_legacy_line(
            parsed_rows,
            line,
            state=state,
            seen_citations_by_work=seen_citations_by_work,
            language=language,
        )
        line.clear()
        i = _parse_legacy_control_run(raw, i, state)
        if i >= len(raw) or _is_legacy_eof(raw, i):
            break
    _append_legacy_line(
        parsed_rows,
        line,
        state=state,
        seen_citations_by_work=seen_citations_by_work,
        language=language,
    )
    return parsed_rows


def _legacy_rows_by_inline_work(
    parsed_rows: list[_LegacyParsedRow],
    works: list[LegacyIdtWork],
) -> dict[str, list[_ReaderSegmentRow]]:
    work_numbers = {work.work_number for work in works}
    if not any(parsed.work_number in work_numbers for parsed in parsed_rows):
        return {}
    rows_by_work = {work_number: [] for work_number in work_numbers}
    for parsed in parsed_rows:
        if parsed.work_number in rows_by_work:
            work_rows = rows_by_work[parsed.work_number]
            work_rows.append(
                _ReaderSegmentRow(
                    sort_key=len(work_rows) + 1,
                    segment_kind=parsed.row.segment_kind,
                    citation_path=parsed.row.citation_path,
                    text=parsed.row.text,
                    source_text=parsed.row.source_text,
                )
            )
    return rows_by_work


def _legacy_book_from_text(seed: _ReaderBookSeed, text: str) -> ParsedBook:
    rows = []
    for index, line in _numbered_nonempty(_normalize_text(line) for line in text.splitlines()):
        if not _has_ascii_letter(line):
            continue
        segment_kind = "section" if line.startswith("<") else "line"
        rows.append((index, segment_kind, line))
    return _parsed_reader_book(seed, rows)


def _collect_perseus_lines(
    node: ET.Element,
    citation_parts: list[str],
    context: _PerseusLineContext,
) -> None:
    for child in list(node):
        child_parts = citation_parts
        if _is_perseus_textpart(child):
            number = child.attrib.get("n", "").strip()
            child_parts = [*citation_parts, number] if number else citation_parts
            if _is_leaf_textpart_segment(child) or _has_only_unnumbered_line_descendants(child):
                citation_path = ".".join(child_parts)
                text = _normalize_text("".join(child.itertext()))
                _append_perseus_segment(
                    context,
                    citation_path=citation_path,
                    segment_kind=child.attrib.get("subtype", "section"),
                    text=text,
                )
        if _local_name(child.tag) == "l" and child.attrib.get("n"):
            citation_path = ".".join([*citation_parts, child.attrib["n"].strip()])
            text = _normalize_text("".join(child.itertext()))
            _append_perseus_segment(
                context,
                citation_path=citation_path,
                segment_kind="line",
                text=text,
            )
        _collect_perseus_lines(child, child_parts, context)


def _collect_perseus_milestone_segments(
    node: ET.Element,
    citation_parts: list[str],
    context: _PerseusLineContext,
) -> None:
    _walk_perseus_milestone_segments(node, citation_parts, citation_parts, context)


def _walk_perseus_milestone_segments(
    node: ET.Element,
    citation_parts: list[str],
    active_parts: list[str],
    context: _PerseusLineContext,
) -> list[str]:
    current_active = active_parts
    for child in list(node):
        child_citation_parts = citation_parts
        child_active_parts = current_active
        if _is_perseus_numbered_div(child):
            number = child.attrib.get("n", "").strip()
            child_citation_parts = [*citation_parts, number]
            child_active_parts = child_citation_parts

        local_name = _local_name(child.tag)
        if local_name == "p":
            current_active = _append_perseus_prose_segments(
                child,
                citation_parts=child_citation_parts,
                active_parts=child_active_parts,
                context=context,
            )
            continue
        if local_name == "l" and child.attrib.get("n"):
            citation_path = ".".join([*child_citation_parts, child.attrib["n"].strip()])
            text = _normalize_text("".join(child.itertext()))
            _append_perseus_segment(
                context,
                citation_path=citation_path,
                segment_kind="line",
                text=text,
            )
            continue

        returned_active = _walk_perseus_milestone_segments(
            child,
            child_citation_parts,
            child_active_parts,
            context,
        )
        if child_citation_parts == citation_parts:
            current_active = returned_active
    return current_active


def _append_perseus_prose_segments(
    node: ET.Element,
    *,
    citation_parts: list[str],
    active_parts: list[str],
    context: _PerseusLineContext,
) -> list[str]:
    current_parts = list(active_parts or citation_parts)
    current_kind = "section" if current_parts else "paragraph"
    chunks: list[str] = [node.text or ""]

    def emit() -> None:
        text = _normalize_text("".join(chunks))
        chunks.clear()
        if not text:
            return
        citation_path = ".".join(current_parts) if current_parts else str(len(context.segments) + 1)
        _append_perseus_segment(
            context,
            citation_path=citation_path,
            segment_kind=current_kind,
            text=text,
        )

    for child in list(node):
        if _local_name(child.tag) == "milestone":
            emit()
            current_parts = _perseus_milestone_parts(
                current_parts or citation_parts,
                unit=child.attrib.get("unit", ""),
                number=child.attrib.get("n", ""),
            )
            current_kind = child.attrib.get("unit", "").strip() or current_kind
            chunks.append(child.tail or "")
            continue
        chunks.append("".join(child.itertext()))
        chunks.append(child.tail or "")
    emit()
    return current_parts


def _perseus_milestone_parts(
    parts: list[str],
    *,
    unit: str,
    number: str,
) -> list[str]:
    number = number.strip()
    if not number:
        return parts
    level = PERSEUS_MILESTONE_LEVELS.get(unit.strip())
    if level is None:
        return [*parts, number]
    next_parts = list(parts)
    while len(next_parts) <= level:
        next_parts.append("")
    next_parts[level] = number
    return [part for part in next_parts[: level + 1] if part]


def _find_perseus_text_node(root: ET.Element) -> ET.Element | None:
    for node in root.iter():
        if (
            _local_name(node.tag) == "div"
            and node.attrib.get("type") in PERSEUS_TEXT_DIV_TYPES
            and node.attrib.get("n", "").strip().startswith("urn:cts:")
        ):
            return node
    return None


def _is_perseus_textpart(node: ET.Element) -> bool:
    return _local_name(node.tag) == "div" and node.attrib.get("type") == "textpart"


def _is_perseus_numbered_div(node: ET.Element) -> bool:
    local_name = _local_name(node.tag)
    if not (local_name == "div" or re.fullmatch(r"div\d+", local_name)):
        return False
    number = node.attrib.get("n", "").strip()
    if not number or number.startswith("urn:cts:"):
        return False
    return node.attrib.get("type") not in PERSEUS_TEXT_ROOT_TYPES


def _is_leaf_textpart_segment(node: ET.Element) -> bool:
    has_nested_textpart = any(_is_perseus_textpart(child) for child in list(node))
    if has_nested_textpart:
        return False
    has_line_descendant = any(_local_name(child.tag) == "l" for child in node.iter())
    return not has_line_descendant and bool(_normalize_text("".join(node.itertext())))


def _has_only_unnumbered_line_descendants(node: ET.Element) -> bool:
    if any(_is_perseus_textpart(child) for child in list(node)):
        return False
    line_nodes = [child for child in node.iter() if _local_name(child.tag) == "l"]
    return bool(line_nodes) and all(not child.attrib.get("n") for child in line_nodes)


def _append_perseus_segment(
    context: _PerseusLineContext,
    *,
    citation_path: str,
    segment_kind: str,
    text: str,
) -> None:
    if not citation_path or not text:
        return
    unique_citation_path = _unique_plain_citation_path(
        citation_path,
        seen=context.seen_citations,
    )
    segment_id = f"{context.work.work_id}:{unique_citation_path}"
    context.segments.append(
        ReaderSegment(
            segment_id=segment_id,
            work_id=context.work.work_id,
            edition_id=context.edition.edition_id,
            segment_kind=segment_kind,
            citation_path=unique_citation_path,
            text=text,
            normalized_text=_normalize_text(text.casefold()),
            sort_key=len(context.segments) + 1,
        )
    )
    context.addresses.append(
        ReaderSegmentAddress(
            segment_id=segment_id,
            address=f"{context.work.work_id}:{unique_citation_path}",
            address_kind="cts",
            citation_path=unique_citation_path,
        )
    )


def _parsed_reader_book(
    seed: _ReaderBookSeed,
    rows: list[tuple[int, str, str]],
) -> ParsedBook:
    return _parsed_reader_book_with_citations(
        seed,
        [
            _ReaderSegmentRow(
                sort_key=sort_key,
                segment_kind=segment_kind,
                citation_path=str(sort_key),
                text=text,
            )
            for sort_key, segment_kind, text in rows
        ],
    )


def _parsed_reader_book_with_citations(
    seed: _ReaderBookSeed,
    rows: list[_ReaderSegmentRow],
) -> ParsedBook:
    work_id = f"langnet:reader:{seed.collection_id}:{_slug(seed.source_id)}"
    edition_id = f"{work_id}:edition"
    work = ReaderWork(
        work_id=work_id,
        collection_id=seed.collection_id,
        language=seed.language,
        title=seed.title,
        author=seed.author,
        source_id=seed.source_id,
        author_id=seed.author_id,
        cts_work_urn=seed.cts_work_urn,
    )
    edition = ReaderEdition(
        edition_id=edition_id,
        work_id=work_id,
        label=seed.edition_label,
        language=seed.language,
        source_path=seed.source_path,
    )
    segments: list[ReaderSegment] = []
    addresses: list[ReaderSegmentAddress] = []
    for row in rows:
        segment_id = f"{work_id}:{row.citation_path}"
        segments.append(
            ReaderSegment(
                segment_id=segment_id,
                work_id=work_id,
                edition_id=edition_id,
                segment_kind=row.segment_kind,
                citation_path=row.citation_path,
                text=row.text,
                normalized_text=_normalize_text(row.text.casefold()),
                sort_key=row.sort_key,
                source_text=row.source_text,
            )
        )
        addresses.append(
            ReaderSegmentAddress(
                segment_id=segment_id,
                address=f"{work_id}:{row.citation_path}",
                address_kind="langnet",
                citation_path=row.citation_path,
            )
        )
    return ParsedBook(work=work, edition=edition, segments=segments, addresses=addresses)


LEGACY_BLOCK_SIZE = 8192
IDT_ESCAPE_MARKER = 0xEF
IDT_FIELD_MARKER = 0x10
IDT_LABEL_MARKER = 0x11
IDT_TERMINATOR = 0xFF
IDT_SECTION_INDEX_RECORD = 3
IDT_LAST_CITATION_RECORD = 10
IDT_EXCEPTION_RECORDS = {11, 13}
LEGACY_HIGH_BIT = 0x80
LEGACY_EOF_MARKER = 0xF0
LEGACY_END_BLOCK_MARKER = 0xFE
LEGACY_MASK = 0x7F
LEGACY_RIGHT_MASK = 0x0F
LEGACY_LEFT_MASK = 0x70
LEGACY_EXCEPTION_LEVEL = 7
LEGACY_REDUNDANT_LEVEL = 6
LEGACY_RIGHT_INLINE_LIMIT = 8
LEGACY_RIGHT_ONE_BYTE = 8
LEGACY_RIGHT_NUM_CHAR = 9
LEGACY_RIGHT_NUM_STRING = 10
LEGACY_RIGHT_TWO_BYTE = 11
LEGACY_RIGHT_TWO_BYTE_CHAR = 12
LEGACY_RIGHT_TWO_BYTE_STRING = 13
LEGACY_RIGHT_APPEND_CHAR = 14
LEGACY_RIGHT_STRING = 15
LEGACY_PUNCT = ("", "?", "*", "/", "!", "|", "=", "+", "%", "&", ":", ".", "*")
LEGACY_BRACKET_OPEN = (
    "",
    "(",
    "<",
    "{",
    "[[",
    "[",
    "[",
    "[",
    "[",
    "[",
    "[",
    "(",
    "->",
    "[",
    "[",
    "[",
    "[[",
    "[[",
)
LEGACY_BRACKET_CLOSE = (
    "",
    ")",
    ">",
    "}",
    "]]",
    "]",
    "]",
    "]",
    "]",
    "]",
    "]",
    ")",
    "<-",
    "]",
    "]",
    "]",
    "]]",
    "]]",
)


@dataclass
class _LegacyBookmarkState:
    auth_num: str = ""
    work_num: str = ""
    levels: dict[int, str] | None = None

    def __post_init__(self) -> None:
        if self.levels is None:
            self.levels = {}


def _decode_legacy_text(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    text = text.replace("\x00", "")
    return re.sub(r"[\x80-\x9f]+", "\n", text)


def _append_legacy_line(
    rows: list[_LegacyParsedRow],
    line: bytearray,
    *,
    state: _LegacyBookmarkState,
    seen_citations_by_work: dict[str, set[str]],
    language: str,
) -> None:
    if not line:
        return
    source_text = line.decode("latin-1", errors="ignore")
    text = _legacy_reader_text(source_text, language=language)
    if not text or not _has_alnum(text):
        return
    work_number = state.work_num
    seen_citations = seen_citations_by_work.setdefault(work_number, set())
    citation_path = _unique_plain_citation_path(
        _legacy_citation_path(state) or str(len(rows) + 1),
        seen=seen_citations,
    )
    segment_kind = "section" if text.startswith("<") else "line"
    rows.append(
        _LegacyParsedRow(
            work_number=work_number,
            row=_ReaderSegmentRow(
                sort_key=len(rows) + 1,
                segment_kind=segment_kind,
                citation_path=citation_path,
                text=text,
                source_text=source_text,
            ),
        )
    )


def _parse_legacy_control_run(
    raw: bytes,
    start: int,
    state: _LegacyBookmarkState,
) -> int:
    i = start
    while i < len(raw) and raw[i] >= LEGACY_HIGH_BIT:
        code = raw[i]
        if _is_legacy_eof(raw, i):
            return len(raw)
        if code == LEGACY_END_BLOCK_MARKER:
            i += 1
            while i < len(raw) and raw[i] == 0:
                i += 1
            continue
        if code == IDT_ESCAPE_MARKER:
            i = _parse_legacy_escape(raw, i, state)
            continue
        i = _parse_legacy_bookmark(raw, i, state, code)
    return i


def _is_legacy_eof(raw: bytes, index: int) -> bool:
    return (
        raw[index] == LEGACY_EOF_MARKER
        and index + 1 < len(raw)
        and raw[index + 1] == LEGACY_END_BLOCK_MARKER
    )


def _parse_legacy_escape(raw: bytes, index: int, state: _LegacyBookmarkState) -> int:
    if index + 1 >= len(raw):
        return len(raw)
    level = raw[index + 1] & LEGACY_MASK
    if not _has_legacy_terminator(raw, index + 2):
        return index + 2
    value, next_index = _read_legacy_ascii(raw, index + 2)
    if not value:
        return next_index
    if level == 0:
        state.auth_num = value
        if state.levels is not None:
            state.levels.clear()
    elif level == 1:
        state.work_num = value
        if state.levels is not None:
            state.levels.clear()
    return next_index


def _parse_legacy_bookmark(  # noqa: C901, PLR0912
    raw: bytes,
    index: int,
    state: _LegacyBookmarkState,
    code: int,
) -> int:
    levels = state.levels if state.levels is not None else {}
    left = (code & LEGACY_LEFT_MASK) >> 4
    right = code & LEGACY_RIGHT_MASK

    if left == LEGACY_EXCEPTION_LEVEL:
        return index + 1
    if left == LEGACY_REDUNDANT_LEVEL:
        return _skip_legacy_level_six(raw, index, right)

    if left:
        for lower in range(left):
            levels[lower] = "1"

    next_index = index + 1
    current = levels.get(left, "")
    if right == 0:
        levels[left] = _increment_legacy_counter(current)
    elif 0 < right < LEGACY_RIGHT_INLINE_LIMIT:
        levels[left] = str(right)
    elif right == LEGACY_RIGHT_ONE_BYTE and next_index < len(raw):
        levels[left] = str(raw[next_index] & LEGACY_MASK)
        next_index += 1
    elif right == LEGACY_RIGHT_NUM_CHAR and next_index + 1 < len(raw):
        levels[left] = f"{raw[next_index] & LEGACY_MASK}{chr(raw[next_index + 1] & LEGACY_MASK)}"
        next_index += 2
    elif right == LEGACY_RIGHT_NUM_STRING and next_index < len(raw):
        number = raw[next_index] & LEGACY_MASK
        value, next_index = _read_legacy_ascii(raw, next_index + 1)
        levels[left] = f"{number}{value}"
    elif right == LEGACY_RIGHT_TWO_BYTE and next_index + 1 < len(raw):
        number = ((raw[next_index] & LEGACY_MASK) << LEGACY_EXCEPTION_LEVEL) + (
            raw[next_index + 1] & LEGACY_MASK
        )
        levels[left] = str(number)
        next_index += 2
    elif right == LEGACY_RIGHT_TWO_BYTE_CHAR and next_index + 2 < len(raw):
        number = ((raw[next_index] & LEGACY_MASK) << LEGACY_EXCEPTION_LEVEL) + (
            raw[next_index + 1] & LEGACY_MASK
        )
        levels[left] = f"{number}{chr(raw[next_index + 2] & LEGACY_MASK)}"
        next_index += 3
    elif right == LEGACY_RIGHT_TWO_BYTE_STRING and next_index + 1 < len(raw):
        number = ((raw[next_index] & LEGACY_MASK) << LEGACY_EXCEPTION_LEVEL) + (
            raw[next_index + 1] & LEGACY_MASK
        )
        value, next_index = _read_legacy_ascii(raw, next_index + 2)
        levels[left] = f"{number}{value}"
    elif right == LEGACY_RIGHT_APPEND_CHAR and next_index < len(raw):
        levels[left] = f"{current}{chr(raw[next_index] & LEGACY_MASK)}"
        next_index += 1
    elif right == LEGACY_RIGHT_STRING:
        levels[left], next_index = _read_legacy_ascii(raw, next_index)
    else:
        next_index = index + 1
    return next_index


def _skip_legacy_level_six(raw: bytes, index: int, right: int) -> int:
    next_index = index + 2
    if right in {LEGACY_RIGHT_ONE_BYTE, LEGACY_RIGHT_NUM_STRING}:
        next_index += 1
    elif right in {
        LEGACY_RIGHT_NUM_CHAR,
        LEGACY_RIGHT_TWO_BYTE,
        LEGACY_RIGHT_TWO_BYTE_STRING,
    }:
        next_index += 2
    elif right == LEGACY_RIGHT_TWO_BYTE_CHAR:
        next_index += 3
    if right in {
        LEGACY_RIGHT_NUM_STRING,
        LEGACY_RIGHT_TWO_BYTE_STRING,
        LEGACY_RIGHT_STRING,
    }:
        _, next_index = _read_legacy_ascii(raw, next_index)
    return min(next_index, len(raw))


def _read_legacy_ascii(raw: bytes, start: int) -> tuple[str, int]:
    chars: list[str] = []
    index = start
    while index < len(raw) and raw[index] != IDT_TERMINATOR:
        chars.append(chr(raw[index] & LEGACY_MASK))
        index += 1
    return "".join(chars), min(index + 1, len(raw))


def _has_legacy_terminator(raw: bytes, start: int) -> bool:
    index = start
    while index < len(raw) and raw[index] >= LEGACY_HIGH_BIT:
        if raw[index] == IDT_TERMINATOR:
            return True
        index += 1
    return False


def _increment_legacy_counter(value: str) -> str:
    match = re.search(r"([A-Za-z]*[0-9]*)$", value)
    suffix = match.group(1) if match else ""
    if not suffix:
        return "1"
    if suffix.isdigit():
        return str(int(suffix) + 1)
    letter_match = re.search(r"([A-Za-z])$", suffix)
    if letter_match:
        letter = letter_match.group(1)
        replacement = chr(ord(letter) + 1)
        return f"{value[: -len(letter)]}{replacement}"
    return f"{value}1"


def _legacy_citation_path(state: _LegacyBookmarkState) -> str:
    levels = state.levels or {}
    return ".".join(levels[level] for level in sorted(levels, reverse=True) if levels.get(level))


def _legacy_reader_text(text: str, *, language: str) -> str:
    text = _strip_legacy_formatting(text, convert_latin_accents=False)
    if language == "grc":
        text = _legacy_greek_beta_to_unicode(text)
    else:
        text = _legacy_inline_greek_beta_to_unicode(text)
        text = _legacy_latin_accents(text)
    return _normalize_text(text)


def _strip_legacy_formatting(text: str, *, convert_latin_accents: bool) -> str:
    text = text.replace("`", " ")
    text = re.sub(r"[%](\d+)", _legacy_punctuation_replacement, text)
    text = re.sub(r'"\d*', '"', text)
    text = re.sub(r"[@]\d*", " ", text)
    text = re.sub(r"\^\d*", " ", text)
    text = text.replace("_", " -- ")
    text = re.sub(r"[\$&]\d*", _legacy_language_marker_replacement, text)
    text = re.sub(r"\[(\d+)", lambda match: _legacy_table_value(LEGACY_BRACKET_OPEN, match), text)
    text = re.sub(r"\](\d+)", lambda match: _legacy_table_value(LEGACY_BRACKET_CLOSE, match), text)
    text = re.sub(r"([<>{}])\d+", r"\1", text)
    text = re.sub(r"#\d+", "#", text)
    if convert_latin_accents:
        text = _legacy_latin_accents(text)
    return text


def _legacy_latin_accents(text: str) -> str:
    text = re.sub(r"([aeiouAEIOU])/", lambda match: _legacy_latin_accent(match, "acute"), text)
    text = re.sub(r"([aeiouAEIOU])\\", lambda match: _legacy_latin_accent(match, "grave"), text)
    text = re.sub(
        r"([aeiouAEIOU])=",
        lambda match: _legacy_latin_accent(match, "circumflex"),
        text,
    )
    return re.sub(
        r"([aeiouAEIOU])\+",
        lambda match: _legacy_latin_accent(match, "diaeresis"),
        text,
    )


def _legacy_punctuation_replacement(match: re.Match[str]) -> str:
    index = int(match.group(1))
    if index < len(LEGACY_PUNCT):
        return LEGACY_PUNCT[index]
    return ""


def _legacy_language_marker_replacement(match: re.Match[str]) -> str:
    marker = match.group(0)[0]
    return f" {marker} "


def _legacy_table_value(values: tuple[str, ...], match: re.Match[str]) -> str:
    index = int(match.group(1))
    if index < len(values):
        return values[index]
    return ""


def _legacy_latin_accent(match: re.Match[str], accent: str) -> str:
    combining = {
        "acute": "\u0301",
        "grave": "\u0300",
        "circumflex": "\u0302",
        "diaeresis": "\u0308",
    }[accent]
    return unicodedata.normalize("NFC", f"{match.group(1)}{combining}")


def _legacy_greek_beta_to_unicode(text: str) -> str:
    try:
        from betacode import conv as betacode_conv  # type: ignore[import-untyped]  # noqa: PLC0415
    except ImportError:
        return text
    parts = re.split(r"(\s[&$]\s)", text)
    greek = True
    output: list[str] = []
    for part in parts:
        if part == " & ":
            greek = False
            continue
        if part == " $ ":
            greek = True
            continue
        if greek and part.strip():
            normalized_part = _normalize_legacy_beta_diacritic_order(part)
            output.append(str(betacode_conv.beta_to_uni(normalized_part)))
        else:
            output.append(part)
    return "".join(output)


def _legacy_inline_greek_beta_to_unicode(text: str) -> str:
    try:
        from betacode import conv as betacode_conv  # type: ignore[import-untyped]  # noqa: PLC0415
    except ImportError:
        return text
    parts = re.split(r"(\s[&$]\s)", text)
    greek = False
    output: list[str] = []
    for part in parts:
        if part == " $ ":
            greek = True
            continue
        if part == " & ":
            greek = False
            continue
        if greek and part.strip():
            normalized_part = _normalize_legacy_beta_diacritic_order(part)
            output.append(str(betacode_conv.beta_to_uni(normalized_part)))
        else:
            output.append(part)
    return "".join(output)


def _normalize_legacy_beta_diacritic_order(text: str) -> str:
    return re.sub(r"\(/\*([A-Z])", r"*(/\1", text)


def _parse_legacy_idt(path: Path) -> list[LegacyIdtWork]:  # noqa: C901
    data = path.read_bytes()
    author_id = path.stem
    author_name = path.stem
    works: list[LegacyIdtWork] = []
    i = 0
    while i < len(data):
        code = data[i]
        if code == 0:
            break
        if code in {IDT_SECTION_INDEX_RECORD, IDT_LAST_CITATION_RECORD}:
            i = _skip_idt_index_record(data, i, code)
            continue
        if code in IDT_EXCEPTION_RECORDS:
            i += 3
            continue
        if code not in {1, 2} or i + 7 >= len(data):
            i += 1
            continue

        start_block = (data[i + 3] << 8) + data[i + 4]
        if data[i + 5] != IDT_ESCAPE_MARKER:
            i += 1
            continue
        level = data[i + 6] & 0x7F
        identifier, i = _read_idt_ascii(data, i + 7)
        if i + 3 > len(data) or data[i] != IDT_FIELD_MARKER:
            continue
        value_level = data[i + 1]
        value, i = _read_idt_pascal(data, i + 2)
        if level == 0 and value_level == 0:
            author_id = identifier
            author_name = _legacy_metadata_text(value)
            continue
        if level != 1 or value_level != 1:
            continue

        labels = []
        while i + 3 <= len(data) and data[i] == IDT_LABEL_MARKER:
            label, i = _read_idt_pascal(data, i + 2)
            labels.append(_legacy_metadata_text(label))
        works.append(
            LegacyIdtWork(
                author_id=author_id,
                author_name=author_name,
                work_number=identifier,
                work_name=_legacy_metadata_text(value),
                start_block=start_block,
                level_labels=tuple(labels),
            )
        )
    return works


def _skip_idt_index_record(data: bytes, index: int, code: int) -> int:
    state = _LegacyBookmarkState()
    next_index = (
        min(index + 4, len(data)) if code == IDT_SECTION_INDEX_RECORD else min(index + 1, len(data))
    )
    if next_index < len(data) and data[next_index] >= LEGACY_HIGH_BIT:
        return _parse_legacy_control_run(data, next_index, state)
    return next_index


def _read_idt_ascii(data: bytes, start: int) -> tuple[str, int]:
    chars = []
    i = start
    while i < len(data) and data[i] != IDT_TERMINATOR:
        chars.append(chr(data[i] & 0x7F))
        i += 1
    return "".join(chars), min(i + 1, len(data))


def _read_idt_pascal(data: bytes, start: int) -> tuple[str, int]:
    if start >= len(data):
        return "", start
    length = data[start]
    value_start = start + 1
    value_end = min(value_start + length, len(data))
    return data[value_start:value_end].decode("latin-1"), value_end


def _legacy_edition_label(level_labels: tuple[str, ...]) -> str:
    if not level_labels:
        return "legacy text dump + IDT"
    return f"legacy text dump + IDT ({', '.join(level_labels)})"


def _legacy_metadata_text(text: str) -> str:
    text = text.replace("`", " ")
    text = re.sub(r"[%](\d+)", _legacy_punctuation_replacement, text)
    text = re.sub(r'"\d*', '"', text)
    text = re.sub(r"[@]\d*", " ", text)
    text = re.sub(r"\^\d*", " ", text)
    text = re.sub(r"[\$&]\d*", "", text)
    text = re.sub(r"[\[\]{}<>]\d*", "", text)
    text = re.sub(r"#\d+", "#", text)
    text = re.sub(r"([aeiouAEIOU])/", lambda match: _legacy_latin_accent(match, "acute"), text)
    text = re.sub(r"([aeiouAEIOU])\\", lambda match: _legacy_latin_accent(match, "grave"), text)
    text = re.sub(
        r"([aeiouAEIOU])=",
        lambda match: _legacy_latin_accent(match, "circumflex"),
        text,
    )
    text = re.sub(
        r"([aeiouAEIOU])\+",
        lambda match: _legacy_latin_accent(match, "diaeresis"),
        text,
    )
    return _normalize_text(text)


def _has_ascii_letter(value: str) -> bool:
    return any("A" <= char <= "Z" or "a" <= char <= "z" for char in value)


def _has_alnum(value: str) -> bool:
    return any(char.isalnum() for char in value)


def _dcs_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("## "):
            continue
        key, sep, value = line[3:].partition(":")
        if sep:
            metadata[key.strip()] = _normalize_text(value)
    return metadata


def _numbered_nonempty(lines: Iterable[str]) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for line in lines:
        if line:
            rows.append((len(rows) + 1, line))
    return rows


def _sanskrit_json_line_text(line: object) -> str:
    if isinstance(line, str):
        return _normalize_text(line)
    if not isinstance(line, list):
        return ""
    tokens: list[str] = []
    for token in line:
        if isinstance(token, dict):
            token_map = cast(dict[str, object], token)
            value = token_map.get("w")
            if isinstance(value, str):
                tokens.append(value)
    return _normalize_text(" ".join(tokens))


def _find_first(
    root: ET.Element, local_name: str, attributes: dict[str, str] | None = None
) -> ET.Element | None:
    for node in root.iter():
        if _local_name(node.tag) != local_name:
            continue
        if attributes and any(node.attrib.get(key) != value for key, value in attributes.items()):
            continue
        return node
    return None


def _find_text(root: ET.Element, local_name: str) -> str | None:
    node = _find_first(root, local_name)
    if node is None:
        return None
    text = _normalize_text("".join(node.itertext()))
    return text or None


def _local_name(tag: str) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def _decode_sanskrit_pdf_encoding(text: str) -> str:
    return text.translate(SANSKRIT_PDF_ENCODING)


def _looks_numbered_sanskrit(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False
    matches = sum(
        1
        for line in lines[:SANSKRIT_NUMBERED_SAMPLE_LINES]
        if SANSKRIT_NUMBERED_LINE_RE.match(line.strip())
    )
    return matches >= SANSKRIT_NUMBERED_MIN_SAMPLE_MATCHES


def _sanskrit_numbered_title(lines: list[str]) -> str | None:
    for line in lines:
        value = _normalize_text(line)
        if not value:
            continue
        if SANSKRIT_NUMBERED_LINE_RE.match(value):
            return None
        if value.startswith(("Searchable file", "(", "To search", "e.g.", "To copy")):
            continue
        return _decode_sanskrit_pdf_encoding(value)
    return None


def _sanskrit_numbered_citation(code: str) -> str:
    return ".".join(str(int(part)) for part in (code[:2], code[2:4], code[4:7], code[7:]))


def _unique_plain_citation_path(citation_path: str, *, seen: set[str]) -> str:
    candidate = citation_path
    suffix = 2
    while candidate in seen:
        candidate = f"{citation_path}.{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._") or "unknown"


def _work_urn_from_edition_urn(edition_urn: str) -> str:
    prefix, tail = edition_urn.rsplit(":", 1)
    work_tail = ".".join(tail.split(".")[:CTS_WORK_TAIL_PARTS])
    return f"{prefix}:{work_tail}"


def _language_from_cts_urn(work_urn: str) -> str:
    if ":latinLit:" in work_urn:
        return "lat"
    if ":greekLit:" in work_urn:
        return "grc"
    return "und"


def _normalize_perseus_language(value: str) -> str:
    return PERSEUS_LANGUAGE_CODES.get(value.strip().lower(), value.strip() or "und")


def _perseus_edition_urn_from_path(path: Path) -> str | None:
    stem = path.stem
    parts = stem.split(".")
    if len(parts) < PERSEUS_MIN_FILENAME_PARTS:
        return None
    author_id, work_id = parts[:2]
    if "canonical-latinLit" in path.parts:
        namespace = "latinLit"
    elif "canonical-greekLit" in path.parts:
        namespace = "greekLit"
    elif author_id.startswith(("phi", "stoa")):
        namespace = "latinLit"
    elif author_id.startswith("tlg"):
        namespace = "greekLit"
    else:
        return None
    if not work_id.startswith(("phi", "stoa", "tlg")):
        return None
    return f"urn:cts:{namespace}:{stem}"


def _work_tail(work_urn: str) -> str:
    return work_urn.rsplit(":", 1)[-1]


def _source_ids_from_work_urn(work_urn: str) -> tuple[str, str]:
    tail = _work_tail(work_urn)
    parts = tail.split(".")
    if len(parts) < CTS_WORK_TAIL_PARTS:
        return work_urn, tail
    namespace = work_urn.rsplit(":", 2)[-2]
    author_id = f"urn:cts:{namespace}:{parts[0]}"
    return author_id, ".".join(parts[:CTS_WORK_TAIL_PARTS])


def _path_source_id(path: Path) -> str:
    return _slug(f"{path.parent.name}_{path.stem}")


def _natural_path_key(path: Path) -> tuple[object, ...]:
    parts: list[object] = []
    for token in re.split(r"(\d+)", path.stem):
        if token.isdigit():
            parts.append(int(token))
        elif token:
            parts.append(token)
    return (*path.parts[:-1], *parts, path.suffix)


def _title_from_slug(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()
