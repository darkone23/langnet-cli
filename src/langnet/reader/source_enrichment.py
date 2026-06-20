from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import duckdb

from langnet.reader.author_normalization import normalize_reader_author
from langnet.reader.models import (
    ReaderMetadataOverlay,
    ReaderMetadataOverlayEvidence,
    ReaderSourceMetadata,
    ReaderWorkMapNode,
)
from langnet.reader.storage import register_source_metadata


@dataclass(frozen=True)
class DcsCorpusRow:
    text: str
    author: str
    time_slot: str
    subject: str
    completed: bool
    has_show: bool
    has_bib: bool
    has_dict: bool
    has_freq: bool
    scope_hint: str


_DCS_SCOPE_HINTS = {
    "Mahabharata": "Sanskrit Epic Literature",
    "Ramayana": "Sanskrit Epic Literature",
    "Kavya": "Sanskrit Kavya",
    "Alamkarashastra": "Sanskrit Kavya",
    "Natyashastra": "Sanskrit Drama",
    "Paniniya": "Sanskrit Grammar",
    "Nirukta": "Sanskrit Grammar",
    "Kosha": "Sanskrit Lexicography",
    "Nyaya": "Nyaya",
    "Samkhya": "Sanskrit Philosophy",
    "Vaisheshika": "Sanskrit Philosophy",
    "Darshana": "Sanskrit Philosophy",
    "Yoga": "Sanskrit Philosophy",
    "Buddhist": "Buddhist Scripture",
    "Rgveda": "Vedic Texts",
    "Atharvaveda": "Vedic Texts",
    "Yajurveda": "Vedic Texts",
    "Brahmana": "Vedic Texts",
    "Aranyaka": "Vedic Texts",
    "Upanishad": "Vedic Texts",
    "Kalpa": "Vedic Ritual and Exegesis",
    "Grhyasutra": "Vedic Ritual and Exegesis",
    "Shrautasutra": "Vedic Ritual and Exegesis",
    "Dharmasutra": "Dharmashastra",
    "Dharmashastra": "Dharmashastra",
    "Purana": "Purana",
    "Ayurveda": "Ayurveda",
    "Rasashastra": "Ayurveda",
    "Jyotisha": "Sanskrit Astronomy and Mathematics",
    "Katha": "Sanskrit Narrative Literature",
    "Bhakti": "Stotra",
    "Arthashastra": "Sanskrit Technical Literature",
    "Kamashastra": "Sanskrit Technical Literature",
    "Dhanurveda": "Sanskrit Technical Literature",
    "Ratnashastra": "Sanskrit Technical Literature",
}
_PERSEUS_FIELD_LABELS = ("URN", "Author", "Editor", "Translator", "Year Published", "Language")
_PERSEUS_FIELD_RE = re.compile(r"(?P<label>URN|Author|Editor|Translator|Year Published|Language):")
_PERSEUS_SUBJECT_FACET_RE = re.compile(
    r"^- \[(?P<subject>.+?)\]"
    r"\((?P<url>https://catalog\.perseus\.org/\?[^)]+)\)\s+"
    r"(?P<count>\d+)\s*$"
)
MIN_COMPACT_PERSEUS_FIELD_COUNT = 2
CTS_WORK_TAIL_PARTS = 2
_PERSEUS_LANGUAGE_CODES = {
    "greek": "grc",
    "ancient greek": "grc",
    "latin": "lat",
}


def parse_dcs_corpus_table(text: str, *, source_path: Path) -> list[DcsCorpusRow]:
    del source_path
    rows: list[DcsCorpusRow] = []
    cleaned = "\n".join(_dcs_corpus_table_lines(text))
    if not cleaned:
        return []
    reader = csv.DictReader(StringIO(cleaned), delimiter="\t")
    for raw_row in reader:
        text_name = _cell(raw_row, "Text")
        if not text_name:
            continue
        subject = _cell(raw_row, "Subject")
        rows.append(
            DcsCorpusRow(
                text=text_name,
                author=_cell(raw_row, "Author"),
                time_slot=_cell(raw_row, "Time slot"),
                subject=subject,
                completed=_flag(_cell(raw_row, "Completed")),
                has_show=_flag(_cell(raw_row, "Show")),
                has_bib=_flag(_cell(raw_row, "Bib.")),
                has_dict=_flag(_cell(raw_row, "Dict.")),
                has_freq=_flag(_cell(raw_row, "Freq.")),
                scope_hint=_DCS_SCOPE_HINTS.get(subject, ""),
            )
        )
    return rows


def parse_dcs_chapter_info_metadata(
    xml_text: str,
    *,
    source_path: Path,
) -> list[ReaderSourceMetadata]:
    root = ET.fromstring(xml_text)
    rows: list[ReaderSourceMetadata] = []
    for chapter in root.findall(".//chapter"):
        text_id = _xml_text(chapter, "textId")
        if not text_id:
            continue
        subject_id = f"dcs_{text_id}"
        values = [
            ("dcs_chapter_name", _xml_text(chapter, "chapterName")),
            ("dcs_chapter_id", _xml_text(chapter, "chapterId")),
            ("dcs_chapter_position", _xml_text(chapter, "chapterPosition")),
            ("dcs_chapter_path", _xml_text(chapter, "path")),
            ("dcs_time_slot", _xml_text(chapter, "dcsTimeSlot")),
        ]
        rows.extend(
            _source_metadata_row(
                collection_id="sanskrit_dcs",
                subject_id=subject_id,
                key=key,
                value=value,
                source_path=source_path,
            )
            for key, value in values
            if value
        )
    return rows


def parse_perseus_catalog_results(
    markdown: str,
    *,
    collection_id: str,
    subject: str,
    source_url: str,
    source_path: Path | None = None,
) -> list[ReaderSourceMetadata]:
    rows: list[ReaderSourceMetadata] = []
    for block in re.split(r"(?m)^#{5}\s+\d+\\?\.\s+", markdown):
        fields = _perseus_fields(block)
        urn = fields.get("URN", "")
        subject_id = _perseus_work_source_id(urn)
        if not subject_id:
            continue
        values = [
            ("perseus_subject", subject),
            ("perseus_edition_urn", urn),
            ("perseus_author", fields.get("Author", "")),
            ("perseus_editor", fields.get("Editor", "")),
            ("perseus_translator", fields.get("Translator", "")),
            ("perseus_year_published", fields.get("Year Published", "")),
            ("perseus_language", fields.get("Language", "")),
            ("perseus_catalog_url", source_url),
        ]
        rows.extend(
            _source_metadata_row(
                collection_id=collection_id,
                subject_id=subject_id,
                key=key,
                value=value,
                source_path=source_path or Path(source_url),
            )
            for key, value in values
            if value
        )
    return rows


def parse_perseus_subject_facets(markdown: str, *, language: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in markdown.splitlines():
        match = _PERSEUS_SUBJECT_FACET_RE.match(raw_line.strip())
        if match is None:
            continue
        rows.append(
            {
                "language": language,
                "subject": match.group("subject"),
                "url": match.group("url"),
                "count": int(match.group("count")),
            }
        )
    return rows


def sync_dcs_corpus_metadata(
    catalog_path: Path,
    table_text: str,
    *,
    source_path: Path,
) -> dict[str, Any]:
    corpus_rows = parse_dcs_corpus_table(table_text, source_path=source_path)
    source_ids_by_title = _sanskrit_dcs_source_ids_by_title(catalog_path)
    metadata_rows: list[ReaderSourceMetadata] = []
    unmatched_texts: list[str] = []
    for row in corpus_rows:
        source_id = source_ids_by_title.get(_normalized_title(row.text))
        if not source_id:
            unmatched_texts.append(row.text)
            continue
        metadata_rows.extend(_dcs_corpus_metadata_rows(source_id, row, source_path=source_path))
    register_source_metadata(catalog_path, metadata_rows)
    return {
        "matched_count": len(corpus_rows) - len(unmatched_texts),
        "metadata_count": len(metadata_rows),
        "unmatched_texts": unmatched_texts,
    }


def perseus_candidate_metadata_overlays(catalog_path: Path) -> list[ReaderMetadataOverlay]:
    """
    Emit candidate display overlays from Perseus source metadata.

    Subject membership, dates, editors, and other enrichment fields remain
    source metadata. This helper only proposes corrections for fields that the
    reader catalog displays directly.
    """
    if not catalog_path.exists():
        return []
    metadata_by_subject = _perseus_metadata_by_subject(catalog_path)
    if not metadata_by_subject:
        return []
    overlays: list[ReaderMetadataOverlay] = []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        work_rows = conn.execute(
            """
            SELECT collection_id, source_id, author, language, cts_work_urn
            FROM works
            WHERE collection_id = 'perseus'
            ORDER BY source_id
            """
        ).fetchall()
    for collection_id, source_id, author, language, cts_work_urn in work_rows:
        subject_id = str(source_id or "")
        metadata = metadata_by_subject.get(subject_id)
        if not metadata:
            continue
        overlays.extend(
            _perseus_candidate_overlays_for_work(
                collection_id=str(collection_id or ""),
                source_id=subject_id,
                author=str(author or ""),
                language=str(language or ""),
                cts_work_urn=str(cts_work_urn or ""),
                metadata=metadata,
            )
        )
    return overlays


def dcs_chapter_info_work_map_candidates(
    catalog_path: Path,
    xml_text: str,
    *,
    source_path: Path,
) -> list[ReaderWorkMapNode]:
    """Return candidate work-map chapter nodes from reliable DCS chapter-info rows."""
    if not catalog_path.exists():
        return []
    work_ids_by_source_id = _sanskrit_dcs_work_ids_by_source_id(catalog_path)
    if not work_ids_by_source_id:
        return []
    root = ET.fromstring(xml_text)
    nodes: list[ReaderWorkMapNode] = []
    for chapter in root.findall(".//chapter"):
        text_id = _xml_text(chapter, "textId")
        chapter_name = _xml_text(chapter, "chapterName")
        chapter_id = _xml_text(chapter, "chapterId")
        chapter_position = _xml_text(chapter, "chapterPosition")
        chapter_path = _xml_text(chapter, "path")
        source_id = f"dcs_{text_id}" if text_id else ""
        work_id = work_ids_by_source_id.get(source_id)
        if not (work_id and chapter_name and chapter_id and chapter_position and chapter_path):
            continue
        try:
            ordinal = int(chapter_position)
        except ValueError:
            continue
        nodes.append(
            ReaderWorkMapNode(
                work_id=work_id,
                node_id=f"{source_id}:chapter:{chapter_id}",
                level=1,
                kind="chapter",
                label=chapter_name,
                native_label=chapter_name,
                ordinal=ordinal,
                start_citation=chapter_name,
                end_citation=chapter_name,
                provenance="native",
                confidence="medium",
                status="candidate",
                note="Candidate chapter node generated from DCS chapter-info.xml.",
                source_file=str(source_path),
                evidence=(
                    ReaderMetadataOverlayEvidence(
                        source_type="dcs_chapter_info",
                        citation=chapter_path,
                        label="DCS chapter-info.xml",
                    ),
                ),
            )
        )
    return nodes


def _perseus_candidate_overlays_for_work(  # noqa: PLR0913
    *,
    collection_id: str,
    source_id: str,
    author: str,
    language: str,
    cts_work_urn: str,
    metadata: dict[str, str],
) -> list[ReaderMetadataOverlay]:
    overlays: list[ReaderMetadataOverlay] = []
    evidence = _perseus_overlay_evidence(metadata)
    source_file = metadata.get("__source_path", "")
    perseus_author = metadata.get("perseus_author", "")
    if perseus_author and normalize_reader_author(author) != normalize_reader_author(
        perseus_author
    ):
        overlays.append(
            _perseus_overlay(
                collection_id=collection_id,
                source_id=source_id,
                field="author",
                value=perseus_author,
                source_file=source_file,
                evidence=evidence,
            )
        )
    perseus_language = _PERSEUS_LANGUAGE_CODES.get(metadata.get("perseus_language", "").casefold())
    if perseus_language and language != perseus_language:
        overlays.append(
            _perseus_overlay(
                collection_id=collection_id,
                source_id=source_id,
                field="language",
                value=perseus_language,
                source_file=source_file,
                evidence=evidence,
            )
        )
    perseus_work_urn = _work_urn_from_edition_urn(metadata.get("perseus_edition_urn", ""))
    if perseus_work_urn and cts_work_urn != perseus_work_urn:
        overlays.append(
            _perseus_overlay(
                collection_id=collection_id,
                source_id=source_id,
                field="cts_work_urn",
                value=perseus_work_urn,
                source_file=source_file,
                evidence=evidence,
            )
        )
    return overlays


def _perseus_overlay(  # noqa: PLR0913
    *,
    collection_id: str,
    source_id: str,
    field: str,
    value: str,
    source_file: str,
    evidence: ReaderMetadataOverlayEvidence,
) -> ReaderMetadataOverlay:
    return ReaderMetadataOverlay(
        collection_id=collection_id,
        match_field="source_id",
        match_value=source_id,
        field=field,
        value=value,
        status="candidate",
        confidence="medium",
        note="Candidate display correction from Perseus Catalog source metadata.",
        source_file=source_file,
        evidence=(evidence,),
    )


def _perseus_overlay_evidence(metadata: dict[str, str]) -> ReaderMetadataOverlayEvidence:
    citation = metadata.get("perseus_catalog_url") or metadata.get("__source_path", "")
    return ReaderMetadataOverlayEvidence(
        source_type="perseus_catalog",
        citation=citation,
        label="Perseus Catalog source metadata",
    )


def _perseus_metadata_by_subject(catalog_path: Path) -> dict[str, dict[str, str]]:
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = conn.execute(
            """
            SELECT subject_id, key, value, source_path
            FROM source_metadata
            WHERE collection_id = 'perseus'
              AND subject_kind = 'work'
              AND key LIKE 'perseus_%'
            ORDER BY subject_id, key
            """
        ).fetchall()
    metadata_by_subject: dict[str, dict[str, str]] = {}
    for subject_id, key, value, source_path in rows:
        metadata = metadata_by_subject.setdefault(str(subject_id), {})
        metadata[str(key)] = str(value or "")
        if source_path and "__source_path" not in metadata:
            metadata["__source_path"] = str(source_path)
    return metadata_by_subject


def _work_urn_from_edition_urn(urn: str) -> str:
    if not urn.startswith("urn:cts:"):
        return ""
    namespace, _, work_tail = urn.rpartition(":")
    parts = work_tail.split(".")
    if len(parts) < CTS_WORK_TAIL_PARTS:
        return ""
    return f"{namespace}:{'.'.join(parts[:CTS_WORK_TAIL_PARTS])}"


def _dcs_corpus_metadata_rows(
    source_id: str,
    row: DcsCorpusRow,
    *,
    source_path: Path,
) -> list[ReaderSourceMetadata]:
    values = [
        ("dcs_author", row.author),
        ("dcs_time_slot", row.time_slot),
        ("dcs_subject", row.subject),
        ("dcs_scope_hint", row.scope_hint),
        ("dcs_completed", _bool_text(row.completed)),
        ("dcs_has_show", _bool_text(row.has_show)),
        ("dcs_has_bib", _bool_text(row.has_bib)),
        ("dcs_has_dict", _bool_text(row.has_dict)),
        ("dcs_has_freq", _bool_text(row.has_freq)),
    ]
    return [
        _source_metadata_row(
            collection_id="sanskrit_dcs",
            subject_id=source_id,
            key=key,
            value=value,
            source_path=source_path,
        )
        for key, value in values
        if value
    ]


def _sanskrit_dcs_source_ids_by_title(catalog_path: Path) -> dict[str, str]:
    if not catalog_path.exists():
        return {}
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = conn.execute(
            """
            SELECT title, source_id
            FROM works
            WHERE collection_id = 'sanskrit_dcs'
            """
        ).fetchall()
    return {_normalized_title(str(title)): str(source_id) for title, source_id in rows}


def _sanskrit_dcs_work_ids_by_source_id(catalog_path: Path) -> dict[str, str]:
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = conn.execute(
            """
            SELECT source_id, work_id
            FROM works
            WHERE collection_id = 'sanskrit_dcs'
            """
        ).fetchall()
    return {str(source_id): str(work_id) for source_id, work_id in rows}


def _source_metadata_row(
    *,
    collection_id: str,
    subject_id: str,
    key: str,
    value: str,
    source_path: Path,
) -> ReaderSourceMetadata:
    return ReaderSourceMetadata(
        collection_id=collection_id,
        subject_kind="work",
        subject_id=subject_id,
        key=key,
        value=value,
        source_path=source_path,
    )


def _perseus_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key = ""
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        compact_fields = _compact_perseus_fields(line)
        if compact_fields:
            fields.update({key: value for key, value in compact_fields.items() if value})
            current_key = ""
            continue
        if line.endswith(":"):
            current_key = line[:-1]
            fields.setdefault(current_key, "")
            continue
        label, sep, value = line.partition(":")
        if sep and label in _PERSEUS_FIELD_LABELS:
            fields[label] = value.strip()
            current_key = ""
            continue
        if current_key and not fields[current_key]:
            fields[current_key] = line
    return fields


def _compact_perseus_fields(line: str) -> dict[str, str]:
    matches = list(_PERSEUS_FIELD_RE.finditer(line))
    if len(matches) < MIN_COMPACT_PERSEUS_FIELD_COUNT:
        return {}
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
        fields[match.group("label")] = line[match.end() : end].strip()
    return fields


def _perseus_work_source_id(urn: str) -> str:
    if not urn.startswith("urn:cts:"):
        return ""
    tail = urn.rsplit(":", 1)[-1]
    parts = tail.split(".")
    if len(parts) < CTS_WORK_TAIL_PARTS:
        return ""
    return ".".join(parts[:CTS_WORK_TAIL_PARTS])


def _cell(row: dict[str, str], key: str) -> str:
    value = str(row.get(key) or "").replace("\xa0", " ").strip()
    return "" if value == "---" else value


def _dcs_corpus_table_lines(text: str) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    start_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("Text\t") and "\tTime slot\t" in line
        ),
        None,
    )
    if start_index is None:
        return lines
    table_lines: list[str] = []
    for line in lines[start_index:]:
        if "\t" not in line:
            break
        table_lines.append(line)
    return table_lines


def _flag(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped and stripped != "---")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _normalized_title(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _xml_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""
