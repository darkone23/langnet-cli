from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from langnet.reader.ctsv2 import ctsv2_segment_address, ctsv2_text_id
from langnet.reader.models import (
    ReaderBookArtifact,
    ReaderBookPathParts,
    ReaderEdition,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceFile,
    ReaderSourceMetadata,
    ReaderSourceWitness,
    ReaderWork,
)
from langnet.reader.paths import reader_book_path
from langnet.reader.search_normalization import normalize_segment_for_search
from langnet.reader.storage import (
    create_book_db,
    delete_reader_works,
    list_source_index,
    register_book,
    register_segment_rows,
    register_source_files,
    register_source_metadata,
    register_source_witnesses,
)

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency guard
    yaml = None  # type: ignore[assignment]

PL_COLUMN_RE = re.compile(
    r"\b\d{3}\.\d{4}[A-D]?\b|\b\d{3}\.\d{4}[A-D]?\\\|\b|\b\d{3}\.\d{4}[A-D]?\|"
)
GREEK_SCRIPT_RE = re.compile(r"[\u0370-\u03FF]")
EXPORT_NOISE_RE = re.compile(r"\b(?:EPUB|MOBI|PDF|RTF|TXT|Download|E Wikisource)\b", re.IGNORECASE)
IMAGE_LINK_RE = re.compile(r"!\[.*?\]\(.*?\)")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
SPACE_RE = re.compile(r"\s+")
MAX_SEGMENT_CHARS = 2200
WIKISOURCE_FOOTER_PREFIXES = (
    "receptum de",
    "categoriae:",
    "novissima mutatio",
    "nonobstantibus ceteris condicionibus",
    "consilium de secreto",
    "repudiationes",
    "code of conduct",
    "elaboratores",
    "statistica",
    "cookie statement",
    "pagina mobilis",
    "toggle the table of contents",
    "add languages",
    "something went wrong",
)


@dataclass(frozen=True)
class PlWikisourceStageConfig:
    manifest_path: Path
    works_tsv_path: Path | None = None
    raw_dir: Path | None = None
    output_dir: Path | None = None
    titles: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlWikisourceSegment:
    segment_id: str
    work_id: str
    title: str
    author: str
    language: str
    citation_path: str
    segment_kind: str
    text: str
    source_url: str
    source_path: str
    series: str
    volume_id: str
    columns: str
    column_markers: tuple[str, ...]
    quality_status: str
    boundary_confidence: str


@dataclass(frozen=True)
class PlWikisourceCatalogImportConfig:
    catalog_path: Path
    summary_path: Path = Path(
        "data/build/reader_import_staging/patrologia_latina/pl122/stage-pl-wikisource-summary.json"
    )
    data_root: Path | None = None
    collection_id: str = "patrologia_latina_wikisource"
    replace_collection: bool = True


@dataclass(frozen=True)
class PgPilotStageConfig:
    manifest_path: Path
    raw_dir: Path | None = None
    output_dir: Path | None = None
    raw_pages: tuple[str, ...] = ()
    title: str | None = None
    author: str | None = None
    language: str = "grc"
    source_url: str | None = None
    max_pages: int | None = None
    quality_status: str = "machine_text_needs_segmentation"
    boundary_confidence: str = "low_medium"


@dataclass(frozen=True)
class PgPilotSegment:
    segment_id: str
    work_id: str
    title: str
    author: str
    language: str
    citation_path: str
    segment_kind: str
    text: str
    source_url: str
    source_path: str
    source_id: str
    series: str
    volume_id: str
    quality_status: str
    boundary_confidence: str


@dataclass(frozen=True)
class PgPilotCatalogImportConfig:
    catalog_path: Path
    summary_path: Path = Path(
        "data/build/reader_import_staging/patrologia_graeca/pilot/stage-pg-pilot-summary.json"
    )
    data_root: Path | None = None
    collection_id: str = "patrologia_graeca_pilot"
    replace_collection: bool = True
    namespace: str = "pg_pilot"


@dataclass(frozen=True)
class BrunoEsotericStageConfig:
    manifest_path: Path
    raw_dir: Path | None = None
    output_dir: Path | None = None
    titles: tuple[str, ...] = ()


@dataclass(frozen=True)
class StagedJsonlCatalogImportConfig:
    catalog_path: Path
    segments_path: Path
    collection_id: str
    namespace: str
    edition_label: str
    edition_suffix: str = "staged_jsonl"
    data_root: Path | None = None
    replace_work: bool = True
    acquisition_source: str = "manifest_backed_staged_jsonl"


def stage_pl_wikisource(config: PlWikisourceStageConfig) -> dict[str, Any]:
    manifest = _load_manifest(config.manifest_path)
    raw_dir = config.raw_dir or _manifest_path(
        manifest, "raw_storage", config.manifest_path.parent / "raw"
    )
    output_dir = config.output_dir or _manifest_path(
        manifest,
        "staging_storage",
        Path("data/build/reader_import_staging/patrologia_latina/pl122"),
    )
    works_tsv = config.works_tsv_path or output_dir / "works.tsv"
    output_dir.mkdir(parents=True, exist_ok=True)

    requested_titles = {_norm_title(title) for title in config.titles}
    rows = _read_work_rows(works_tsv)
    if requested_titles:
        rows = [row for row in rows if _norm_title(row.get("title", "")) in requested_titles]
    else:
        rows = [row for row in rows if row.get("status") == "staged_sample"]

    staged: list[dict[str, Any]] = []
    for row in rows:
        raw_path = _find_raw_markdown(raw_dir, row)
        text = raw_path.read_text(encoding="utf-8")
        segments = _segments_for_row(row, raw_path, text)
        safe_id = _safe_slug(row.get("title", "work"))
        jsonl_path = output_dir / f"{safe_id}.segments.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for segment in segments:
                handle.write(json.dumps(asdict(segment), ensure_ascii=False, sort_keys=True) + "\n")
        staged.append(
            {
                "title": row.get("title", ""),
                "author": row.get("author", ""),
                "source_url": row.get("work_url", ""),
                "source_path": str(raw_path),
                "segments_path": str(jsonl_path),
                "segment_count": len(segments),
                "token_count": sum(_token_count(segment.text) for segment in segments),
                "quality_status": row.get("quality_status", "machine_text_needs_segmentation"),
                "boundary_confidence": row.get("boundary_confidence", "medium"),
            }
        )

    payload = {
        "schema_version": "langnet.reader.source_acquisition.pl_wikisource.v1",
        "mode": "stage-pl-wikisource",
        "manifest_path": str(config.manifest_path),
        "works_tsv_path": str(works_tsv),
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "work_count": len(staged),
        "segment_count": sum(int(item["segment_count"]) for item in staged),
        "token_count": sum(int(item["token_count"]) for item in staged),
        "items": staged,
    }
    (output_dir / "stage-pl-wikisource-summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def import_pl_wikisource_catalog(config: PlWikisourceCatalogImportConfig) -> dict[str, Any]:
    summary = json.loads(config.summary_path.read_text(encoding="utf-8"))
    if config.replace_collection:
        existing_work_ids = {
            str(row.get("work_id"))
            for row in list_source_index(
                config.catalog_path,
                collection_id=config.collection_id,
                limit=10000,
            )
            if row.get("work_id")
        }
        delete_reader_works(config.catalog_path, existing_work_ids)
    imported: list[dict[str, Any]] = []
    for item in summary.get("items", []):
        if not isinstance(item, dict):
            continue
        segments_path = Path(str(item["segments_path"]))
        staged_segments = _read_staged_segments(segments_path)
        if not staged_segments:
            continue
        first = staged_segments[0]
        title = str(first["title"])
        author = str(first["author"])
        language = str(first.get("language") or "lat")
        source_id = f"pl122.{_safe_slug(title)}"
        source_url = str(first.get("source_url") or item.get("source_url") or "")
        canonical_text_id = ctsv2_text_id(
            language, title, _incipit_for_title(title, staged_segments)
        )
        work_id = canonical_text_id
        author_id = "patrologia-latina-wikisource:joannes-scotus-eriugena"
        edition_id = f"{work_id}:wikisource-pl122"
        book_path = reader_book_path(
            ReaderBookPathParts(
                collection=config.collection_id,
                namespace="pl122",
                author_id=author_id,
                work_id=_safe_slug(title),
                edition_id="wikisource",
            ),
            data_root=config.data_root,
        )
        create_book_db(book_path)
        reader_segments, addresses = _reader_segments_for_import(
            staged_segments,
            work_id=work_id,
            edition_id=edition_id,
            canonical_text_id=canonical_text_id,
        )
        token_count = sum(_token_count(segment.text) for segment in reader_segments)
        source_path = Path(
            str(first.get("source_path") or item.get("source_path") or segments_path)
        )
        source_hash = _hash_paths([segments_path, source_path])
        register_segment_rows(book_path, segments=reader_segments, addresses=addresses)
        work = ReaderWork(
            work_id=work_id,
            collection_id=config.collection_id,
            language=language,
            title=title,
            author=author,
            author_id=author_id,
            source_id=source_id,
            cts_work_urn=None,
            canonical_text_id=canonical_text_id,
        )
        edition = ReaderEdition(
            edition_id=edition_id,
            work_id=work_id,
            label="Latin Wikisource PL122",
            language=language,
            source_path=source_path,
            cts_edition_urn=None,
        )
        artifact = ReaderBookArtifact(
            artifact_id=f"{work_id}:wikisource-pl122:artifact",
            work_id=work_id,
            edition_id=edition_id,
            artifact_path=book_path,
            source_path=segments_path,
            adapter="pl_wikisource_staged_jsonl",
            source_hash=source_hash,
            segment_count=len(reader_segments),
            token_count=token_count,
        )
        register_book(config.catalog_path, work, edition, artifact)
        register_source_files(
            config.catalog_path,
            [
                ReaderSourceFile(
                    collection_id=config.collection_id,
                    source_path=source_path,
                    file_role="source_text",
                    file_status=str(
                        first.get("quality_status") or "machine_text_needs_segmentation"
                    ),
                    source_id=source_id,
                    source_hash=source_hash,
                    size_bytes=source_path.stat().st_size if source_path.exists() else None,
                ),
                ReaderSourceFile(
                    collection_id=config.collection_id,
                    source_path=segments_path,
                    file_role="staging_jsonl",
                    file_status="segmented_staging",
                    source_id=source_id,
                    source_hash=source_hash,
                    size_bytes=segments_path.stat().st_size,
                ),
            ],
        )
        register_source_metadata(
            config.catalog_path,
            _source_metadata_for_import(
                collection_id=config.collection_id,
                work_id=work_id,
                source_id=source_id,
                source_path=source_path,
                first=first,
                source_url=source_url,
                segments_path=segments_path,
            ),
        )
        register_source_witnesses(
            config.catalog_path,
            [
                ReaderSourceWitness(
                    canonical_text_id=canonical_text_id,
                    work_id=work_id,
                    collection_id=config.collection_id,
                    language=language,
                    witness_id=f"{source_id}:wikisource-pl122",
                    source_id=source_id,
                    source_urn=source_url,
                    source_path=source_path,
                    status="imported_from_staging",
                    confidence=str(first.get("boundary_confidence") or "medium"),
                    note="Imported from Latin Wikisource PL122 staged JSONL; preserve quality status for review.",
                )
            ],
            replace=False,
        )
        imported.append(
            {
                "title": title,
                "author": author,
                "work_id": work_id,
                "canonical_text_id": canonical_text_id,
                "source_id": source_id,
                "book_path": str(book_path),
                "source_path": str(source_path),
                "segments_path": str(segments_path),
                "segment_count": len(reader_segments),
                "token_count": token_count,
            }
        )
    return {
        "schema_version": "langnet.reader.source_acquisition.pl_wikisource_import.v1",
        "mode": "import-pl-wikisource",
        "catalog_path": str(config.catalog_path),
        "summary_path": str(config.summary_path),
        "collection_id": config.collection_id,
        "work_count": len(imported),
        "segment_count": sum(int(item["segment_count"]) for item in imported),
        "token_count": sum(int(item["token_count"]) for item in imported),
        "items": imported,
    }


def stage_pg_pilot(config: PgPilotStageConfig) -> dict[str, Any]:
    manifest = _load_manifest(config.manifest_path)
    raw_dir = config.raw_dir or _manifest_path(
        manifest, "raw_storage", config.manifest_path.parent / "raw"
    )
    output_dir = config.output_dir or _manifest_path(
        manifest,
        "staging_storage",
        Path("data/build/reader_import_staging/patrologia_graeca/pilot"),
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_pages = _collect_pg_raw_pages(
        raw_dir,
        raw_pages=config.raw_pages,
        max_pages=config.max_pages,
    )
    sample_title = (
        str(config.title).strip()
        if config.title
        else "Patrologia Graeca pilot sample (OGL-PatrologiaGraecaDev)"
    )
    sample_author = str(config.author).strip() if config.author else "Unknown author"
    language = (config.language or "grc").strip() or "grc"
    series = str(manifest.get("series") or "Patrologia Graeca")
    volume_id = str(manifest.get("volume_id") or "Vol.-1")
    source_id = str(manifest.get("source_id") or "patrologia_graeca:pilot")
    source_url = str(config.source_url or "")
    quality_status = str(config.quality_status or "machine_text_needs_segmentation")
    boundary_confidence = str(config.boundary_confidence or "low_medium")

    work_id = f"pg_pilot:{_safe_slug(sample_title)}"
    segments = _segments_for_pg_pages(
        title=sample_title,
        author=sample_author,
        language=language,
        source_id=source_id,
        source_url=source_url,
        series=series,
        volume_id=volume_id,
        quality_status=quality_status,
        boundary_confidence=boundary_confidence,
        raw_pages=raw_pages,
    )
    if not segments:
        raise ValueError("no usable PG text segments found in selected raw pages")

    safe_title = _safe_slug(sample_title)
    jsonl_path = output_dir / f"{safe_title}.segments.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for segment in segments:
            handle.write(json.dumps(asdict(segment), ensure_ascii=False, sort_keys=True) + "\n")

    payload = {
        "schema_version": "langnet.reader.source_acquisition.pg_pilot.v1",
        "mode": "stage-pg-pilot",
        "manifest_path": str(config.manifest_path),
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "work_count": 1,
        "segment_count": len(segments),
        "token_count": sum(_token_count(segment.text) for segment in segments),
        "items": [
            {
                "work_id": work_id,
                "title": sample_title,
                "author": sample_author,
                "language": language,
                "source_id": source_id,
                "source_url": source_url,
                "source_paths": [str(path) for path in raw_pages],
                "segments_path": str(jsonl_path),
                "segment_count": len(segments),
                "token_count": sum(_token_count(segment.text) for segment in segments),
                "quality_status": quality_status,
                "boundary_confidence": boundary_confidence,
            }
        ],
    }
    (output_dir / "stage-pg-pilot-summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def import_pg_pilot_catalog(config: PgPilotCatalogImportConfig) -> dict[str, Any]:
    summary = json.loads(config.summary_path.read_text(encoding="utf-8"))
    if config.replace_collection:
        existing_work_ids = {
            str(row.get("work_id"))
            for row in list_source_index(
                config.catalog_path,
                collection_id=config.collection_id,
                limit=10000,
            )
            if row.get("work_id")
        }
        delete_reader_works(config.catalog_path, existing_work_ids)
    imported: list[dict[str, Any]] = []
    for item in summary.get("items", []):
        if not isinstance(item, dict):
            continue
        segments_path = Path(str(item["segments_path"]))
        staged_segments = _read_staged_segments(segments_path)
        if not staged_segments:
            continue
        first = staged_segments[0]
        title = str(first.get("title") or item.get("title") or "")
        author = str(first.get("author") or item.get("author") or "Unknown author")
        language = str(first.get("language") or item.get("language") or "grc")
        source_id = str(
            first.get("source_id") or item.get("source_id") or "patrologia_graeca:pilot"
        )
        item_work_id = str(item.get("work_id") or "")
        canonical_text_id = ctsv2_text_id(
            language, title, _incipit_for_title(title, staged_segments)
        )
        work_id = item_work_id or canonical_text_id
        source_url = str(first.get("source_url") or item.get("source_url") or "")
        source_paths = [Path(path) for path in item.get("source_paths", []) if path]
        source_path = (
            source_paths[0]
            if source_paths
            else Path(str(first.get("source_path") or segments_path))
        )
        book_path = reader_book_path(
            ReaderBookPathParts(
                collection=config.collection_id,
                namespace=config.namespace,
                author_id=_safe_slug(str(first.get("author") or source_id)),
                work_id=_safe_slug(title),
                edition_id="pg_pilot_ocr",
            ),
            data_root=config.data_root,
        )
        create_book_db(book_path)
        edition_id = f"{work_id}:pg_pilot_ocr"
        reader_segments, addresses = _reader_segments_for_import(
            staged_segments,
            work_id=work_id,
            edition_id=edition_id,
            canonical_text_id=canonical_text_id,
        )
        token_count = sum(_token_count(segment.text) for segment in reader_segments)
        source_hash = _hash_paths([segments_path] + source_paths)
        register_segment_rows(book_path, segments=reader_segments, addresses=addresses)
        source_id_for_rows = f"{source_id}:{_safe_slug(title)}"
        work = ReaderWork(
            work_id=work_id,
            collection_id=config.collection_id,
            language=language,
            title=title,
            author=author,
            source_id=source_id_for_rows,
            cts_work_urn=None,
            canonical_text_id=canonical_text_id,
        )
        edition = ReaderEdition(
            edition_id=edition_id,
            work_id=work_id,
            label="Patrologia Graeca pilot OCR",
            language=language,
            source_path=source_path,
            cts_edition_urn=None,
        )
        artifact = ReaderBookArtifact(
            artifact_id=f"{work_id}:pg_pilot_ocr:artifact",
            work_id=work_id,
            edition_id=edition_id,
            artifact_path=book_path,
            source_path=segments_path,
            adapter="pg_pilot_staged_jsonl",
            source_hash=source_hash,
            segment_count=len(reader_segments),
            token_count=token_count,
        )
        register_book(config.catalog_path, work, edition, artifact)
        source_files = [
            ReaderSourceFile(
                collection_id=config.collection_id,
                source_path=source_path,
                file_role="source_text",
                file_status=str(first.get("quality_status") or "machine_text_needs_segmentation"),
                source_id=source_id_for_rows,
                source_hash=source_hash,
                size_bytes=source_path.stat().st_size if source_path.exists() else None,
            ),
            ReaderSourceFile(
                collection_id=config.collection_id,
                source_path=segments_path,
                file_role="staging_jsonl",
                file_status="segmented_staging",
                source_id=source_id_for_rows,
                source_hash=source_hash,
                size_bytes=segments_path.stat().st_size,
            ),
        ]
        for source_path_value in source_paths:
            if source_path_value == source_path:
                continue
            source_files.append(
                ReaderSourceFile(
                    collection_id=config.collection_id,
                    source_path=source_path_value,
                    file_role="source_text",
                    file_status=str(
                        first.get("quality_status") or "machine_text_needs_segmentation"
                    ),
                    source_id=source_id_for_rows,
                    source_hash=source_hash,
                    size_bytes=source_path_value.stat().st_size
                    if source_path_value.exists()
                    else None,
                )
            )
        register_source_files(config.catalog_path, source_files)
        register_source_metadata(
            config.catalog_path,
            _source_metadata_for_import(
                collection_id=config.collection_id,
                work_id=work_id,
                source_id=source_id_for_rows,
                source_path=source_path,
                first=first,
                source_url=source_url,
                segments_path=segments_path,
                acquisition_source="patrologia_graeca_pilot",
            ),
        )
        register_source_witnesses(
            config.catalog_path,
            [
                ReaderSourceWitness(
                    canonical_text_id=canonical_text_id,
                    work_id=work_id,
                    collection_id=config.collection_id,
                    language=language,
                    witness_id=f"{source_id_for_rows}:pilot_ocr",
                    source_id=source_id_for_rows,
                    source_urn=source_url,
                    source_path=source_path,
                    status="imported_from_staging",
                    confidence=str(first.get("boundary_confidence") or "low_medium"),
                    note="Imported from Patrologia Graeca pilot staged JSONL; preserve quality status for review.",
                )
            ],
            replace=False,
        )
        imported.append(
            {
                "title": title,
                "author": author,
                "work_id": work_id,
                "canonical_text_id": canonical_text_id,
                "source_id": source_id_for_rows,
                "book_path": str(book_path),
                "source_path": str(source_path),
                "segments_path": str(segments_path),
                "segment_count": len(reader_segments),
                "token_count": token_count,
            }
        )
    return {
        "schema_version": "langnet.reader.source_acquisition.pg_pilot_import.v1",
        "mode": "import-pg-pilot",
        "catalog_path": str(config.catalog_path),
        "summary_path": str(config.summary_path),
        "collection_id": config.collection_id,
        "work_count": len(imported),
        "segment_count": sum(int(item["segment_count"]) for item in imported),
        "token_count": sum(int(item["token_count"]) for item in imported),
        "items": imported,
    }


def stage_bruno_esoteric(config: BrunoEsotericStageConfig) -> dict[str, Any]:
    manifest = _load_manifest(config.manifest_path)
    raw_dir = config.raw_dir or _manifest_path(
        manifest, "raw_storage", config.manifest_path.parent / "raw"
    )
    output_dir = config.output_dir or _manifest_path(
        manifest,
        "staging_storage",
        Path("data/build/reader_import_staging/bruno/esotericarchives"),
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    requested_titles = {_norm_title(title) for title in config.titles}
    work_rows = [
        row
        for row in manifest.get("works", [])
        if isinstance(row, dict)
        and (
            _norm_title(str(row.get("title") or "")) in requested_titles
            if requested_titles
            else row.get("status") in {None, "staged_sample", "candidate"}
        )
    ]
    staged: list[dict[str, Any]] = []
    for row in work_rows:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        raw_file = str(row.get("raw_file") or f"{_safe_slug(title)}.md")
        raw_path = raw_dir / raw_file
        markdown = raw_path.read_text(encoding="utf-8")
        segments = _bruno_esoteric_segments(row, raw_path, markdown)
        safe_title = _safe_slug(title)
        jsonl_path = output_dir / f"{safe_title}.segments.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for segment in segments:
                handle.write(json.dumps(segment, ensure_ascii=False, sort_keys=True) + "\n")
        staged.append(
            {
                "title": title,
                "author": str(row.get("author") or "Giordano Bruno"),
                "source_url": str(row.get("work_url") or row.get("source_url") or ""),
                "source_path": str(raw_path),
                "segments_path": str(jsonl_path),
                "segment_count": len(segments),
                "token_count": sum(
                    _token_count(str(segment.get("text") or "")) for segment in segments
                ),
                "quality_status": str(row.get("quality_status") or "html_needs_boilerplate_strip"),
                "boundary_confidence": str(row.get("boundary_confidence") or "medium"),
            }
        )

    payload = {
        "schema_version": "langnet.reader.source_acquisition.bruno_esoteric.v1",
        "mode": "stage-bruno-esoteric",
        "manifest_path": str(config.manifest_path),
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "work_count": len(staged),
        "segment_count": sum(int(item["segment_count"]) for item in staged),
        "token_count": sum(int(item["token_count"]) for item in staged),
        "items": staged,
    }
    (output_dir / "stage-bruno-esoteric-summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def import_staged_jsonl_catalog(config: StagedJsonlCatalogImportConfig) -> dict[str, Any]:
    staged_segments = _read_staged_segments(config.segments_path)
    if not staged_segments:
        return {
            "schema_version": "langnet.reader.source_acquisition.staged_jsonl_import.v1",
            "mode": "import-staged-jsonl",
            "catalog_path": str(config.catalog_path),
            "segments_path": str(config.segments_path),
            "collection_id": config.collection_id,
            "work_count": 0,
            "segment_count": 0,
            "token_count": 0,
            "items": [],
        }
    first = staged_segments[0]
    title = str(first.get("title") or "Untitled staged reader work")
    author = str(first.get("author") or "Unknown author")
    language = str(first.get("language") or "lat")
    staged_work_id = str(first.get("work_id") or "").strip()
    canonical_text_id = ctsv2_text_id(language, title, _incipit_for_title(title, staged_segments))
    work_id = staged_work_id or canonical_text_id
    edition_id = f"{work_id}:{config.edition_suffix}"
    source_id = str(first.get("source_id") or f"{config.collection_id}:{_safe_slug(title)}")
    source_url = str(first.get("source_url") or "")
    author_id = f"{config.collection_id}:{_safe_slug(author)}"
    source_path = Path(str(first.get("source_path") or config.segments_path))
    control_source_path_value = str(first.get("control_source_path") or "").strip()
    control_source_path = Path(control_source_path_value) if control_source_path_value else None
    source_paths = [config.segments_path, source_path]
    if control_source_path is not None:
        source_paths.append(control_source_path)
    if config.replace_work:
        delete_reader_works(config.catalog_path, {work_id})
    book_path = reader_book_path(
        ReaderBookPathParts(
            collection=config.collection_id,
            namespace=config.namespace,
            author_id=_safe_slug(author),
            work_id=_safe_slug(title),
            edition_id=config.edition_suffix,
        ),
        data_root=config.data_root,
    )
    create_book_db(book_path)
    reader_segments, addresses = _reader_segments_for_import(
        staged_segments,
        work_id=work_id,
        edition_id=edition_id,
        canonical_text_id=canonical_text_id,
    )
    token_count = sum(_token_count(segment.text) for segment in reader_segments)
    source_hash = _hash_paths(source_paths)
    register_segment_rows(book_path, segments=reader_segments, addresses=addresses)
    register_book(
        config.catalog_path,
        ReaderWork(
            work_id=work_id,
            collection_id=config.collection_id,
            language=language,
            title=title,
            author=author,
            author_id=author_id,
            source_id=source_id,
            cts_work_urn=None,
            canonical_text_id=canonical_text_id,
        ),
        ReaderEdition(
            edition_id=edition_id,
            work_id=work_id,
            label=config.edition_label,
            language=language,
            source_path=source_path,
            cts_edition_urn=None,
        ),
        ReaderBookArtifact(
            artifact_id=f"{work_id}:{config.edition_suffix}:artifact",
            work_id=work_id,
            edition_id=edition_id,
            artifact_path=book_path,
            source_path=config.segments_path,
            adapter="manifest_backed_staged_jsonl",
            source_hash=source_hash,
            segment_count=len(reader_segments),
            token_count=token_count,
        ),
    )
    source_files = [
        ReaderSourceFile(
            collection_id=config.collection_id,
            source_path=source_path,
            file_role="source_text",
            file_status=str(first.get("quality_status") or "staged_candidate"),
            source_id=source_id,
            source_hash=source_hash,
            size_bytes=source_path.stat().st_size if source_path.exists() else None,
        ),
        ReaderSourceFile(
            collection_id=config.collection_id,
            source_path=config.segments_path,
            file_role="staging_jsonl",
            file_status=str(first.get("review_status") or "segmented_staging"),
            source_id=source_id,
            source_hash=source_hash,
            size_bytes=config.segments_path.stat().st_size,
        ),
    ]
    if control_source_path is not None:
        source_files.append(
            ReaderSourceFile(
                collection_id=config.collection_id,
                source_path=control_source_path,
                file_role="control_witness",
                file_status=str(first.get("quality_status") or "source_control"),
                source_id=str(first.get("control_source_id") or source_id),
                source_hash=source_hash,
                size_bytes=control_source_path.stat().st_size
                if control_source_path.exists()
                else None,
            )
        )
    register_source_files(config.catalog_path, source_files)
    register_source_metadata(
        config.catalog_path,
        _source_metadata_for_import(
            collection_id=config.collection_id,
            work_id=work_id,
            source_id=source_id,
            source_path=source_path,
            first=first,
            source_url=source_url,
            segments_path=config.segments_path,
            acquisition_source=config.acquisition_source,
        )
        + _staged_jsonl_extra_metadata(
            collection_id=config.collection_id,
            work_id=work_id,
            source_id=source_id,
            source_path=source_path,
            first=first,
        ),
    )
    witnesses = [
        ReaderSourceWitness(
            canonical_text_id=canonical_text_id,
            work_id=work_id,
            collection_id=config.collection_id,
            language=language,
            witness_id=f"{source_id}:{config.edition_suffix}",
            source_id=source_id,
            source_urn=source_url,
            source_path=source_path,
            status=str(first.get("review_status") or "imported_from_staging"),
            confidence=str(first.get("boundary_confidence") or "medium"),
            note="Imported from manifest-backed staged JSONL; preserve quality/review status in reader provenance.",
        )
    ]
    if control_source_path is not None:
        witnesses.append(
            ReaderSourceWitness(
                canonical_text_id=canonical_text_id,
                work_id=work_id,
                collection_id=config.collection_id,
                language=language,
                witness_id=f"{source_id}:control",
                source_id=str(first.get("control_source_id") or source_id),
                source_urn="",
                source_path=control_source_path,
                status="control_witness",
                confidence=str(first.get("boundary_confidence") or "medium"),
                note="Control witness recorded from staged segment metadata.",
            )
        )
    register_source_witnesses(config.catalog_path, witnesses, replace=False)
    return {
        "schema_version": "langnet.reader.source_acquisition.staged_jsonl_import.v1",
        "mode": "import-staged-jsonl",
        "catalog_path": str(config.catalog_path),
        "segments_path": str(config.segments_path),
        "collection_id": config.collection_id,
        "work_count": 1,
        "segment_count": len(reader_segments),
        "token_count": token_count,
        "items": [
            {
                "title": title,
                "author": author,
                "work_id": work_id,
                "canonical_text_id": canonical_text_id,
                "source_id": source_id,
                "book_path": str(book_path),
                "source_path": str(source_path),
                "segments_path": str(config.segments_path),
                "segment_count": len(reader_segments),
                "token_count": token_count,
            }
        ],
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
        if isinstance(loaded, dict):
            return loaded
    return _minimal_yaml_mapping(text)


def _minimal_yaml_mapping(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if not line or line.startswith(" ") or line.lstrip().startswith("-") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip() or None
    return data


def _bruno_esoteric_segments(
    row: dict[str, Any], raw_path: Path, markdown: str
) -> list[dict[str, Any]]:
    title = str(row.get("title") or "").strip()
    author = str(row.get("author") or "Giordano Bruno").strip() or "Giordano Bruno"
    language = str(row.get("language") or "lat").strip() or "lat"
    start_heading = str(row.get("start_heading") or title).strip()
    source_url = str(row.get("work_url") or row.get("source_url") or "").strip()
    source_id = str(row.get("source_id") or f"bruno:esotericarchives:{_safe_slug(title)}")
    quality_status = str(row.get("quality_status") or "html_needs_boilerplate_strip")
    review_status = str(row.get("status") or "staged_sample")
    boundary_confidence = str(row.get("boundary_confidence") or "medium")

    lines = _bruno_body_lines(markdown, start_heading=start_heading)
    paragraphs = _bruno_paragraphs(lines)
    segments: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        if not _useful_paragraph(paragraph):
            continue
        for chunk in _split_long_paragraph(paragraph):
            segment_index = len(segments) + 1
            segments.append(
                {
                    "segment_id": f"{source_id}:{segment_index:05d}",
                    "work_id": source_id,
                    "title": title,
                    "author": author,
                    "language": language,
                    "citation_path": f"p{segment_index}",
                    "segment_kind": "paragraph",
                    "text": chunk.strip(),
                    "source_id": source_id,
                    "source_url": source_url,
                    "source_path": str(raw_path),
                    "quality_status": quality_status,
                    "review_status": review_status,
                    "boundary_confidence": boundary_confidence,
                }
            )
    return segments


def _bruno_body_lines(markdown: str, *, start_heading: str) -> list[str]:
    lines = markdown.splitlines()
    start_key = _norm_title(start_heading)
    started = not start_key
    body: list[str] = []
    for raw_line in lines:
        line = _clean_markdown_line(raw_line)
        if not line:
            if started:
                body.append("")
            continue
        heading_text = _clean_markdown_line(raw_line.lstrip("#").strip())
        heading_key = _norm_title(heading_text)
        if not started:
            if heading_key == start_key:
                started = True
            continue
        if _is_bruno_nav_or_footer_line(raw_line, line):
            continue
        if line.startswith("#"):
            continue
        if _is_bruno_heading_or_credit(line):
            continue
        body.append(line)
    return body


def _bruno_paragraphs(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                paragraphs.append(_join_paragraph(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(_join_paragraph(current))
    return paragraphs


def _is_bruno_nav_or_footer_line(raw_line: str, line: str) -> bool:
    stripped = line.strip()
    raw_stripped = raw_line.strip()
    if raw_stripped.startswith("- [") and re.search(
        r"\[(Home|Contents|Prev|Next|timeline)\]", raw_stripped, re.IGNORECASE
    ):
        return True
    if stripped in {"magia", "umbris", "vinculis", "bruno/"}:
        return True
    return stripped == "* * *"


def _is_bruno_heading_or_credit(line: str) -> bool:
    lowered = line.lower()
    if lowered.startswith("giordano bruno:"):
        return True
    if "digital edition" in lowered or "html edition" in lowered:
        return True
    if lowered.startswith("license ") or "creativecommons.org/licenses" in lowered:
        return True
    if lowered.startswith("for a translation"):
        return True
    if lowered.startswith("this is bruno") or lowered.startswith("bruno wrote"):
        return True
    if lowered.startswith("this is giordano bruno"):
        return True
    if lowered == "iordani bruni nolani":
        return True
    return lowered in {"de magia", "de vincvlis in genere", "de vmbris idearvm."}


def _manifest_path(manifest: dict[str, Any], key: str, fallback: Path) -> Path:
    value = manifest.get(key)
    if isinstance(value, str) and value.strip():
        return Path(value).expanduser()
    return fallback


def _read_work_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _find_raw_markdown(raw_dir: Path, row: dict[str, str]) -> Path:
    title_norm = _norm_title(row.get("title", ""))
    candidates = sorted(raw_dir.glob("*.md"))
    for path in candidates:
        if title_norm and title_norm in _norm_title(path.stem):
            return path
    for path in candidates:
        head = path.read_text(encoding="utf-8", errors="ignore")[:2000]
        if title_norm and title_norm in _norm_title(head):
            return path
    raise FileNotFoundError(
        f"no raw markdown found for {row.get('title', '<untitled>')} in {raw_dir}"
    )


def _collect_pg_raw_pages(
    raw_dir: Path,
    raw_pages: tuple[str, ...],
    max_pages: int | None,
) -> list[Path]:
    if raw_pages:
        page_paths = [_resolve_pg_raw_page(raw_dir, value) for value in raw_pages]
    else:
        page_paths = sorted(raw_dir.rglob("*.txt"))
    if max_pages is not None:
        page_paths = page_paths[:max_pages]
    if not page_paths:
        raise FileNotFoundError(
            f"no PG raw .txt pages found in {raw_dir}; add --raw-page paths or populate the raw directory"
        )
    return page_paths


def _resolve_pg_raw_page(raw_dir: Path, raw_page: str) -> Path:
    candidate = Path(raw_page)
    if candidate.is_absolute():
        if candidate.exists():
            return candidate
    else:
        direct = raw_dir / candidate
        if direct.exists():
            return direct
    wildcard = raw_page if re.search(r"[*?\[]", raw_page) else f"**/{raw_page}"
    matches = sorted(raw_dir.glob(wildcard))
    if not matches:
        raise FileNotFoundError(f"pg raw page {raw_page!r} not found under {raw_dir}")
    if len(matches) > 1:
        raise ValueError(
            f"pg raw page {raw_page!r} matches multiple files under {raw_dir}: {matches}"
        )
    return matches[0]


def _segments_for_pg_pages(
    *,
    title: str,
    author: str,
    language: str,
    source_id: str,
    source_url: str,
    series: str,
    volume_id: str,
    quality_status: str,
    boundary_confidence: str,
    raw_pages: list[Path],
) -> list[PgPilotSegment]:
    work_id = f"pg_pilot:{_safe_slug(title)}"
    segments: list[PgPilotSegment] = []
    segment_index = 0
    for page_path in sorted(raw_pages):
        text = page_path.read_text(encoding="utf-8", errors="ignore")
        body_lines = [
            _normalize_pg_line(line) for line in text.splitlines() if _normalize_pg_line(line)
        ]
        page_started = False
        paragraphs = []
        current: list[str] = []
        for line in body_lines:
            if not page_started:
                if not _contains_reading_text(line):
                    continue
                page_started = True
            if current and _starts_pg_segment(line):
                paragraphs.append(_join_paragraph(current))
                current = [line]
            else:
                current.append(line)
        if current:
            paragraphs.append(_join_paragraph(current))
        for paragraph in paragraphs:
            if not _useful_paragraph(paragraph):
                continue
            chunks = _split_long_paragraph(paragraph)
            for chunk in chunks:
                segment_index += 1
                citation = f"{page_path.stem}:{segment_index}"
                segments.append(
                    PgPilotSegment(
                        segment_id=f"{work_id}:{segment_index:05d}",
                        work_id=work_id,
                        title=title,
                        author=author,
                        language=language,
                        citation_path=citation,
                        segment_kind="page_paragraph",
                        text=chunk.strip(),
                        source_url=source_url,
                        source_path=str(page_path),
                        source_id=source_id,
                        series=series,
                        volume_id=volume_id,
                        quality_status=quality_status,
                        boundary_confidence=boundary_confidence,
                    )
                )
    return segments


def _normalize_pg_line(line: str) -> str:
    return SPACE_RE.sub(" ", line.replace("\ufeff", "").strip())


def _contains_reading_text(line: str) -> bool:
    if not line or len(line) < 8:
        return False
    if re.fullmatch(r"\d+", line):
        return False
    return bool(GREEK_SCRIPT_RE.search(line) or re.search(r"[A-Za-z]", line))


def _starts_pg_segment(line: str) -> bool:
    if _contains_reading_text(line) and line.isupper() and len(line) < 120:
        return True
    return False


def _segments_for_row(
    row: dict[str, str], raw_path: Path, markdown: str
) -> list[PlWikisourceSegment]:
    work_id = f"pl122:{_safe_slug(row.get('title', 'work'))}"
    body_lines = _body_lines(markdown, row.get("title", ""))
    paragraphs = _paragraphs(body_lines)
    chunks: list[str] = []
    for paragraph in paragraphs:
        chunks.extend(_split_long_paragraph(paragraph))
    chunks = _merge_marker_only_chunks(chunks)

    segments: list[PlWikisourceSegment] = []
    for index, chunk in enumerate(chunks, start=1):
        markers = tuple(_clean_marker(marker) for marker in PL_COLUMN_RE.findall(chunk))
        citation = markers[0] if markers else str(index)
        segment_kind = "column_paragraph" if markers else "paragraph"
        segments.append(
            PlWikisourceSegment(
                segment_id=f"{work_id}:{index:05d}",
                work_id=work_id,
                title=row.get("title", ""),
                author=row.get("author", ""),
                language=row.get("language", "lat"),
                citation_path=citation,
                segment_kind=segment_kind,
                text=chunk,
                source_url=row.get("work_url", ""),
                source_path=str(raw_path),
                series=row.get("series", "Patrologia Latina"),
                volume_id=row.get("volume_id", "PL122"),
                columns=row.get("columns", ""),
                column_markers=markers,
                quality_status=row.get("quality_status", "machine_text_needs_segmentation"),
                boundary_confidence=row.get("boundary_confidence", "medium"),
            )
        )
    return segments


def _merge_marker_only_chunks(chunks: list[str]) -> list[str]:
    merged: list[str] = []
    pending_marker = ""
    for chunk in chunks:
        if _is_marker_only_chunk(chunk):
            pending_marker = f"{pending_marker} {chunk}".strip()
            continue
        if pending_marker:
            chunk = f"{pending_marker} {chunk}".strip()
            pending_marker = ""
        merged.append(chunk)
    if pending_marker:
        merged.append(pending_marker)
    return merged


def _clean_pl_markers(line: str) -> str:
    text = PL_COLUMN_RE.sub("", line)
    return SPACE_RE.sub(" ", text).replace("\\|", " ").replace("|", " ").strip()


def _is_marker_only_chunk(chunk: str) -> bool:
    without_markers = _clean_pl_markers(chunk).strip()
    return not without_markers and bool(PL_COLUMN_RE.search(chunk))


def _is_front_matter_line(line: str, title: str) -> bool:
    normalized = _normalize_front_matter_candidate(line)
    if not normalized:
        return False
    normalized_title = _norm_title(title)
    if _norm_title(normalized) == normalized_title:
        return True

    low = normalized.casefold()
    if low.startswith("- monetum ad lectore") or low.startswith("monitum ad lectore"):
        return True
    if low.startswith("editio princeps") or low.startswith("editio:"):
        return True
    if low.startswith("fons:") and "corpus corporum" in low:
        return True
    if low.startswith("cod") and " ms" in low:
        return True
    if "j. p. migne" in low and normalized_title in _norm_title(low):
        return True
    if (
        any(fragment in low for fragment in ("iohannes scotus eriugena", "joannes scotus eriugena"))
        and normalized_title
        and normalized_title in _norm_title(low)
    ):
        return True
    marker_match = PL_COLUMN_RE.match(normalized)
    if marker_match:
        without_marker = PL_COLUMN_RE.sub("", normalized)
        without_marker = _clean_pl_markers(without_marker).strip()
        without_marker_low = without_marker.casefold()
        if without_marker_low.startswith("monitum ad lectore"):
            return True
        if _norm_title(without_marker) == normalized_title:
            return True
    return False


def _body_lines(markdown: str, title: str) -> list[str]:
    lines = [_clean_markdown_line(line) for line in markdown.splitlines()]
    title_norm = _norm_title(title)
    start = 0
    for index, line in enumerate(lines):
        normalized = _norm_title(line)
        if title_norm and normalized == title_norm:
            start = index + 1
        if "122." in line and index > 5:
            start = max(start, index)
            break
    body: list[str] = []
    body_started = False
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if body_started:
                body.append("")
            continue
        if not body_started and _is_front_matter_line(stripped, title):
            markers = " ".join(_clean_marker(marker) for marker in PL_COLUMN_RE.findall(stripped))
            if markers:
                body.append(markers)
            continue
        if not body_started and _is_marker_only_chunk(stripped):
            continue
        body_started = True
        if _is_wikisource_footer_line(stripped):
            break
        if _is_boilerplate_line(stripped, title):
            continue
        body.append(stripped)
    if not body_started:
        return [line for line in lines[start:] if line.strip()]
    return body


def _clean_markdown_line(line: str) -> str:
    line = IMAGE_LINK_RE.sub("", line)
    line = MARKDOWN_LINK_RE.sub(r"\1", line)
    line = line.replace("\\|", "|")
    line = line.replace("«", '"').replace("»", '"')
    return SPACE_RE.sub(" ", line).strip()


def _normalize_front_matter_candidate(line: str) -> str:
    text = _clean_markdown_line(line)
    text = text.lstrip("-*• \t").strip()
    if not text:
        return ""
    return text


def _is_boilerplate_line(line: str, title: str) -> bool:
    line = _normalize_front_matter_candidate(line)
    if not line:
        return False
    if EXPORT_NOISE_RE.search(line):
        return True
    low = line.casefold()
    exact_noise = {
        "jump to content",
        "de wikisource",
        "scriptor:iohannes scotus eriugena",
        "editio: j. p. migne",
        "editio princeps",
        "fons: corpus corporum",
        "monitum ad lectore",
        "saeculo ix",
        "quaerere",
    }
    if low in exact_noise:
        return True
    if low.startswith("- opera omnia"):
        return True
    if low.startswith("- novissima mutatio"):
        return True
    if low.startswith("- consilium de secreto"):
        return True
    if low.startswith("iohannes scotus eriugena") and _norm_title(title) in _norm_title(low):
        return True
    if low.startswith("migne patrologia latina tomus"):
        return True
    return False


def _is_wikisource_footer_line(line: str) -> bool:
    normalized = _normalize_front_matter_candidate(line).casefold()
    if not normalized:
        return False
    return any(normalized.startswith(prefix) for prefix in WIKISOURCE_FOOTER_PREFIXES)


def _paragraphs(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                paragraphs.append(_join_paragraph(current))
                current = []
            continue
        if current and _starts_new_segment(line):
            paragraphs.append(_join_paragraph(current))
            current = [line]
        else:
            current.append(line)
    if current:
        paragraphs.append(_join_paragraph(current))
    return [p for p in paragraphs if _useful_paragraph(p)]


def _starts_new_segment(line: str) -> bool:
    if PL_COLUMN_RE.search(line):
        return True
    if re.fullmatch(r"[IVXLCDM]+\.", line):
        return True
    if re.fullmatch(r"\d+\.", line):
        return True
    if line.isupper() and len(line) < 120:
        return True
    return False


def _join_paragraph(lines: list[str]) -> str:
    return SPACE_RE.sub(" ", " ".join(lines)).strip()


def _useful_paragraph(text: str) -> bool:
    if len(text) < 8:
        return bool(PL_COLUMN_RE.search(text))
    if text.count("|") > 6 and len(text) < 160:
        return False
    return True


def _split_long_paragraph(text: str) -> list[str]:
    if len(text) <= MAX_SEGMENT_CHARS:
        return [text]
    sentences = re.split(r"(?<=[.;:?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + 1 + len(sentence) > MAX_SEGMENT_CHARS:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks


def _norm_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "work"


def _clean_marker(value: str) -> str:
    return value.replace("|", "").replace("\\", "")


def _token_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _read_staged_segments(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _incipit_from_segments(segments: list[dict[str, Any]]) -> str:
    for segment in segments:
        text = str(segment.get("text") or "")
        stripped = PL_COLUMN_RE.sub("", text).replace("|", "").strip()
        if stripped:
            return stripped
    return ""


def _incipit_for_title(title: str, segments: list[dict[str, Any]]) -> str:
    normalized_title = _norm_title(title)
    overrides = {
        "de praedestinatione": "Dominis illustribus et merito Christianae fidei",
        "de divisione naturae": "MAGISTER Saepe mihi cogitanti diligentiusque",
    }
    return overrides.get(normalized_title) or _incipit_from_segments(segments)


def _reader_segments_for_import(
    staged_segments: list[dict[str, Any]],
    *,
    work_id: str,
    edition_id: str,
    canonical_text_id: str,
) -> tuple[list[ReaderSegment], list[ReaderSegmentAddress]]:
    segments: list[ReaderSegment] = []
    addresses: list[ReaderSegmentAddress] = []
    citation_count: dict[str, int] = {}
    for index, row in enumerate(staged_segments, start=1):
        citation_path = str(row.get("citation_path") or row.get("citation") or index)
        if citation_path in citation_count:
            citation_count[citation_path] += 1
            citation_path = f"{citation_path}::{citation_count[citation_path]}"
        else:
            citation_count[citation_path] = 0
        segment_id = f"{work_id}:{index:05d}"
        text = str(row.get("text") or "").strip()
        segments.append(
            ReaderSegment(
                segment_id=segment_id,
                work_id=work_id,
                edition_id=edition_id,
                segment_kind=str(row.get("segment_kind") or "paragraph"),
                citation_path=citation_path,
                text=text,
                source_text=text,
                normalized_text=normalize_segment_for_search(
                    str(row.get("language") or "lat"), text
                ).search_text,
                sort_key=index,
            )
        )
        addresses.append(
            ReaderSegmentAddress(
                segment_id=segment_id,
                address=ctsv2_segment_address(canonical_text_id, citation_path),
                address_kind="ctsv2",
                citation_path=citation_path,
            )
        )
    return segments, addresses


def _hash_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode("utf-8"))
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _source_metadata_for_import(
    *,
    collection_id: str,
    work_id: str,
    source_id: str,
    source_path: Path,
    first: dict[str, Any],
    source_url: str,
    segments_path: Path,
    acquisition_source: str = "latin_wikisource",
) -> list[ReaderSourceMetadata]:
    values = {
        "series": str(first.get("series") or "Patrologia Latina"),
        "volume_id": str(first.get("volume_id") or "PL122"),
        "columns": str(first.get("columns") or ""),
        "source_url": source_url,
        "segments_path": str(segments_path),
        "quality_status": str(first.get("quality_status") or ""),
        "boundary_confidence": str(first.get("boundary_confidence") or ""),
        "acquisition_source": acquisition_source,
    }
    rows = [
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="work",
            subject_id=work_id,
            key=key,
            value=value,
            source_path=source_path,
        )
        for key, value in values.items()
        if value
    ]
    rows.extend(
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="source",
            subject_id=source_id,
            key=key,
            value=value,
            source_path=source_path,
        )
        for key, value in values.items()
        if value
    )
    return rows


def _staged_jsonl_extra_metadata(
    *,
    collection_id: str,
    work_id: str,
    source_id: str,
    source_path: Path,
    first: dict[str, Any],
) -> list[ReaderSourceMetadata]:
    values = {
        "review_status": str(first.get("review_status") or ""),
        "control_source_id": str(first.get("control_source_id") or ""),
        "control_source_path": str(first.get("control_source_path") or ""),
        "book_or_part": str(first.get("book_or_part") or ""),
        "chapter_or_section": str(first.get("chapter_or_section") or ""),
    }
    rows = [
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="work",
            subject_id=work_id,
            key=key,
            value=value,
            source_path=source_path,
        )
        for key, value in values.items()
        if value
    ]
    rows.extend(
        ReaderSourceMetadata(
            collection_id=collection_id,
            subject_kind="source",
            subject_id=source_id,
            key=key,
            value=value,
            source_path=source_path,
        )
        for key, value in values.items()
        if value
    )
    return rows
