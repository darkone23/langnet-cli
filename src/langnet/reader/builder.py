from __future__ import annotations

import hashlib
import re
import shutil
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from itertools import islice
from pathlib import Path

import duckdb
from returns.result import Failure, Success

from langnet.databuild.base import BuildErrorStats, BuildResult, BuildStatus, ReaderCorpusStats
from langnet.databuild.paths import default_reader_catalog_path
from langnet.reader.adapters import (
    ParsedBook,
    _legacy_metadata_text,
    normalize_digiliblt_author,
    parse_dcs_conllu,
    parse_dcs_conllu_group,
    parse_digiliblt_tei,
    parse_legacy_text_dump,
    parse_legacy_text_dump_with_idt,
    parse_perseus_tei,
    parse_sanskrit_json,
    parse_sanskrit_plain_text,
    parse_sanskrit_plain_text_group,
    resolve_digiliblt_author,
)
from langnet.reader.alias_registry import load_aliases
from langnet.reader.author_index import compact_author_id
from langnet.reader.author_normalization import (
    canonical_author_from_html_index_item,
    normalize_reader_author,
)
from langnet.reader.citation_map import load_citation_maps
from langnet.reader.contained_work import load_contained_works
from langnet.reader.ctsv2 import ctsv2_text_id
from langnet.reader.division_metadata import accepted_division_metadata, load_division_metadata
from langnet.reader.legacy_metadata import (
    legacy_source_files,
    legacy_source_metadata,
    parse_html_author_index,
    parse_tlg_canon_source_metadata,
)
from langnet.reader.metadata_attribution import load_metadata_attributions
from langnet.reader.metadata_overlay import accepted_metadata_overlays, load_metadata_overlays
from langnet.reader.models import (
    ReaderAlias,
    ReaderBookArtifact,
    ReaderCitationReference,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceFile,
    ReaderSourceMetadata,
    ReaderSourceWitness,
    ReaderWorkRelation,
)
from langnet.reader.opengreekandlatin import (
    discover_ogl_sources,
    is_ogl_source_xml,
    looks_like_ogl_tei,
    ogl_source_files,
    ogl_source_metadata,
    parse_ogl_tei,
    selected_ogl_sources,
)
from langnet.reader.source_enrichment import (
    parse_dcs_chapter_info_metadata,
    sync_dcs_corpus_metadata,
)
from langnet.reader.storage import (
    ReaderBookRegistration,
    create_catalog_db,
    delete_reader_works,
    register_aliases,
    register_books,
    register_citation_maps,
    register_citation_references,
    register_contained_works,
    register_division_metadata,
    register_metadata_attributions,
    register_metadata_overlays,
    register_segment_rows,
    register_source_files,
    register_source_metadata,
    register_source_witnesses,
    register_work_map_nodes,
    register_work_relations,
)
from langnet.reader.work_map import accepted_work_map_nodes, load_work_map_nodes

CTS_URN_MIN_PARTS = 4
NUMBERED_SANSKRIT_CODE_LENGTH = 8
NUMBERED_SANSKRIT_MIN_LINE_LENGTH = NUMBERED_SANSKRIT_CODE_LENGTH + 1
NUMBERED_SANSKRIT_MIN_MATCHES = 3
PRIMARY_READER_LANGUAGES = {"lat", "grc", "san"}
SANSKRIT_TRANSLATION_PATH_PARTS = {"translation", "translations"}


@dataclass(frozen=True)
class ReaderBuildConfig:
    perseus_dir: Path | None = None
    first1k_greek_dir: Path | None = None
    digiliblt_dir: Path | None = None
    phi_latin_dir: Path | None = None
    tlg_e_dir: Path | None = None
    sanskrit_dir: Path | None = None
    opengreekandlatin_latin_dir: Path | None = None
    opengreekandlatin_csel_dir: Path | None = None
    opengreekandlatin_patrologia_dir: Path | None = None
    opengreekandlatin_church_fathers_dir: Path | None = None
    alias_dir: Path | None = None
    metadata_overlay_dir: Path | None = Path("data/curated/reader_metadata")
    metadata_attribution_dir: Path | None = Path("data/curated/reader_attributions")
    contained_work_dir: Path | None = Path("data/curated/reader_contained_works")
    work_map_dir: Path | None = Path("data/curated/reader_work_maps")
    division_metadata_dir: Path | None = Path("data/curated/reader_division_metadata")
    citation_map_dir: Path | None = Path("data/curated/reader_citation_maps")
    output_root: Path | None = None
    cts_index_path: Path | None = Path("data/build/cts_urn.duckdb")
    limit: int | None = None
    wipe_existing: bool = True
    force_rebuild: bool = False
    progress_every: int | None = None
    progress_callback: Callable[[ReaderBuildProgress], None] | None = None
    source_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ReaderBuildProgress:
    parsed_sources: int
    artifact_count: int
    segment_count: int
    latest_source: str


@dataclass(frozen=True)
class _ParsedSource:
    parsed: ParsedBook
    adapter: str


@dataclass
class _PendingBookWrite:
    book_path: Path
    sources: list[_ParsedSource]
    segments: list[ReaderSegment]
    addresses: list[ReaderSegmentAddress]
    citation_references: list[ReaderCitationReference]

    @classmethod
    def start(cls, book_path: Path) -> _PendingBookWrite:
        return cls(
            book_path=book_path, sources=[], segments=[], addresses=[], citation_references=[]
        )

    def append(self, source: _ParsedSource) -> None:
        work_id = source.parsed.work.work_id
        if any(existing.parsed.work.work_id == work_id for existing in self.sources):
            self.sources = [
                existing for existing in self.sources if existing.parsed.work.work_id != work_id
            ]
            self.segments = [segment for segment in self.segments if segment.work_id != work_id]
            self.addresses = [
                address
                for address in self.addresses
                if not address.segment_id.startswith(f"{work_id}:")
            ]
            self.citation_references = [
                reference for reference in self.citation_references if reference.work_id != work_id
            ]
        self.sources.append(source)
        self.segments.extend(source.parsed.segments)
        self.addresses.extend(source.parsed.addresses)
        self.citation_references.extend(source.parsed.citation_references)


class ReaderBuilder:
    def __init__(self, config: ReaderBuildConfig) -> None:
        self.config = config
        self.output_root = config.output_root or default_reader_catalog_path().parent
        self.catalog_path = self.output_root / "catalog.duckdb"
        self.source_errors: list[tuple[Path, str, str]] = []
        self._author_authority: dict[str, tuple[str, str | None]] | None = None
        self._source_hashes: dict[Path, str] = {}
        self._metadata_overlays = (
            load_metadata_overlays(config.metadata_overlay_dir)
            if config.metadata_overlay_dir is not None
            else []
        )
        self._metadata_attributions = (
            load_metadata_attributions(config.metadata_attribution_dir)
            if config.metadata_attribution_dir is not None
            else []
        )
        self._contained_works = (
            load_contained_works(config.contained_work_dir)
            if config.contained_work_dir is not None
            else []
        )
        self._work_map_nodes = (
            load_work_map_nodes(config.work_map_dir) if config.work_map_dir is not None else []
        )
        self._division_metadata = (
            load_division_metadata(config.division_metadata_dir)
            if config.division_metadata_dir is not None
            else []
        )
        self._citation_maps = (
            load_citation_maps(config.citation_map_dir)
            if config.citation_map_dir is not None
            else []
        )
        self._accepted_metadata_overlays = accepted_metadata_overlays(self._metadata_overlays)
        self._selected_source_paths = {
            path.expanduser().resolve() for path in self.config.source_paths
        }

    def build(self) -> BuildResult[ReaderCorpusStats | BuildErrorStats]:
        try:
            if self.output_root.exists() and self.config.wipe_existing:
                shutil.rmtree(self.output_root)
            create_catalog_db(self.catalog_path)

            aliases = load_aliases(self.config.alias_dir) if self.config.alias_dir else []
            self._register_curated_metadata()
            self._register_legacy_source_metadata()
            self._register_digiliblt_source_metadata()
            self._register_sanskrit_source_metadata()
            self._register_perseus_source_metadata()
            self._register_first1k_greek_source_metadata()
            self._register_opengreekandlatin_source_metadata()

            artifact_count = 0
            segment_count = 0
            parsed_sources = 0
            book_registrations: list[ReaderBookRegistration] = []
            citation_references: list[ReaderCitationReference] = []
            pending_book: _PendingBookWrite | None = None
            for raw_source in self._iter_sources():
                source = self._apply_metadata_overlays(
                    self._normalize_author_source(self._canonicalize_source(raw_source))
                )
                source = self._apply_ctsv2_identity(source)
                if not source.parsed.segments:
                    continue
                book_path = self._book_path(source.parsed)
                if pending_book is not None and pending_book.book_path != book_path:
                    artifact_count, segment_count = self._flush_pending_book(
                        pending_book,
                        book_registrations,
                        citation_references,
                        artifact_count=artifact_count,
                        segment_count=segment_count,
                    )
                    pending_book = None
                if pending_book is None:
                    pending_book = _PendingBookWrite.start(book_path)
                pending_book.append(source)
                parsed_sources += 1
                self._emit_progress(
                    parsed_sources=parsed_sources,
                    artifact_count=artifact_count + len(pending_book.sources),
                    segment_count=segment_count + len(pending_book.segments),
                    latest_source=source.parsed.edition.source_path,
                )
            if pending_book is not None:
                artifact_count, segment_count = self._flush_pending_book(
                    pending_book,
                    book_registrations,
                    citation_references,
                    artifact_count=artifact_count,
                    segment_count=segment_count,
                )
            book_registrations = _dedupe_book_registrations_for_catalog(
                _ensure_unique_canonical_text_ids(book_registrations)
            )
            register_books(self.catalog_path, book_registrations)
            self._delete_superseded_sanskrit_json_works(book_registrations)
            self._delete_superseded_legacy_works_with_perseus()
            self._delete_superseded_legacy_works_with_first1k()
            surviving_registrations = _registrations_for_work_ids(
                book_registrations,
                self._catalog_work_ids(),
            )
            self._register_sanskrit_source_enrichment_metadata()
            register_source_witnesses(
                self.catalog_path,
                _source_witnesses_for_registrations(surviving_registrations),
                replace=not self.config.source_paths,
            )
            register_work_relations(
                self.catalog_path,
                _work_relations_for_contained_works(self._contained_works),
            )
            alias_count = self._register_aliases_and_citation_references(
                aliases,
                surviving_registrations,
                citation_references,
            )
            self._register_source_errors()
            catalog_work_count, catalog_artifact_count, catalog_segment_count = (
                self._catalog_counts()
            )

            stats = ReaderCorpusStats(
                catalog_path=str(self.catalog_path),
                artifact_count=catalog_artifact_count,
                work_count=catalog_work_count,
                segment_count=catalog_segment_count,
                alias_count=alias_count,
                source_error_count=len(self.source_errors),
            )
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.catalog_path,
                stats=Success(stats),
            )
        except Exception as exc:
            error = BuildErrorStats(error=str(exc))
            return BuildResult(
                status=BuildStatus.FAILED,
                output_path=self.catalog_path,
                stats=Failure(error),
                message=str(exc),
            )

    def _register_curated_metadata(self) -> None:
        register_metadata_overlays(self.catalog_path, self._metadata_overlays)
        register_metadata_attributions(self.catalog_path, self._metadata_attributions)
        register_contained_works(self.catalog_path, self._contained_works)
        register_work_map_nodes(
            self.catalog_path,
            accepted_work_map_nodes(self._work_map_nodes),
        )
        register_division_metadata(
            self.catalog_path,
            accepted_division_metadata(self._division_metadata),
        )
        register_citation_maps(self.catalog_path, self._citation_maps)

    def _flush_pending_book(
        self,
        pending_book: _PendingBookWrite,
        book_registrations: list[ReaderBookRegistration],
        citation_references: list[ReaderCitationReference],
        *,
        artifact_count: int,
        segment_count: int,
    ) -> tuple[int, int]:
        register_segment_rows(
            pending_book.book_path,
            segments=pending_book.segments,
            addresses=pending_book.addresses,
        )
        for source in pending_book.sources:
            artifact = self._artifact(source, pending_book.book_path)
            book_registrations.append(
                ReaderBookRegistration(
                    source.parsed.work,
                    source.parsed.edition,
                    artifact,
                )
            )
            artifact_count += 1
            segment_count += len(source.parsed.segments)
        citation_references.extend(pending_book.citation_references)
        return artifact_count, segment_count

    def _register_aliases_and_citation_references(
        self,
        aliases: list[ReaderAlias],
        surviving_registrations: list[ReaderBookRegistration],
        citation_references: list[ReaderCitationReference],
    ) -> int:
        registered_aliases = _aliases_for_registrations(aliases, surviving_registrations)
        register_aliases(
            self.catalog_path,
            registered_aliases,
            replace=not self.config.source_paths,
        )
        surviving_work_ids = {registration.work.work_id for registration in surviving_registrations}
        register_citation_references(
            self.catalog_path,
            [
                reference
                for reference in citation_references
                if reference.work_id in surviving_work_ids
            ],
            replace=not self.config.source_paths,
            replace_work_ids=surviving_work_ids,
        )
        return len(registered_aliases)

    def _delete_superseded_sanskrit_json_works(
        self,
        registrations: list[ReaderBookRegistration],
    ) -> None:
        stems = {
            stem
            for registration in registrations
            if registration.work.collection_id == "sanskrit_texts"
            and (stem := _sanskrit_gretil_comparable_source_id(registration.work.source_id))
        }
        stems.update(self._existing_sanskrit_text_gretil_stems())
        work_ids = [
            f"langnet:reader:sanskrit_json:{_slug(f'corpus_{stem}')}" for stem in sorted(stems)
        ]
        delete_reader_works(self.catalog_path, work_ids)

    def _existing_sanskrit_text_gretil_stems(self) -> set[str]:
        if not self.catalog_path.exists():
            return set()
        with duckdb.connect(str(self.catalog_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT source_id
                FROM works
                WHERE language = 'san'
                  AND collection_id = 'sanskrit_texts'
                  AND source_id LIKE 'GRETIL_sa_%'
                """
            ).fetchall()
        return {
            stem
            for (source_id,) in rows
            if (stem := _sanskrit_gretil_comparable_source_id(str(source_id))) is not None
        }

    def _delete_superseded_legacy_works_with_perseus(self) -> None:
        if not self.catalog_path.exists():
            return
        with duckdb.connect(str(self.catalog_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT legacy.work_id
                FROM works AS legacy
                JOIN works AS perseus
                  ON legacy.cts_work_urn = perseus.cts_work_urn
                 AND legacy.language = perseus.language
                WHERE legacy.collection_id IN ('phi', 'tlg')
                  AND perseus.collection_id = 'perseus'
                  AND legacy.work_id <> perseus.work_id
                  AND legacy.cts_work_urn IS NOT NULL
                  AND legacy.cts_work_urn <> ''
                """
            ).fetchall()
        delete_reader_works(self.catalog_path, [str(work_id) for (work_id,) in rows])

    def _delete_superseded_legacy_works_with_first1k(self) -> None:
        if not self.catalog_path.exists():
            return
        with duckdb.connect(str(self.catalog_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT legacy.work_id
                FROM works AS legacy
                JOIN works AS first1k
                  ON (
                    (
                      legacy.cts_work_urn = first1k.cts_work_urn
                      AND legacy.cts_work_urn IS NOT NULL
                      AND legacy.cts_work_urn <> ''
                    )
                    OR (
                      legacy.canonical_text_id = first1k.canonical_text_id
                      AND legacy.canonical_text_id IS NOT NULL
                      AND legacy.canonical_text_id <> ''
                    )
                  )
                 AND legacy.language = first1k.language
                WHERE legacy.collection_id IN ('phi', 'tlg')
                  AND first1k.collection_id = 'first1kgreek'
                  AND legacy.work_id <> first1k.work_id
                """
            ).fetchall()
        delete_reader_works(self.catalog_path, [str(work_id) for (work_id,) in rows])

    def _catalog_work_ids(self) -> set[str]:
        if not self.catalog_path.exists():
            return set()
        with duckdb.connect(str(self.catalog_path), read_only=True) as conn:
            rows = conn.execute("SELECT work_id FROM works").fetchall()
        return {str(work_id) for (work_id,) in rows}

    def _catalog_counts(self) -> tuple[int, int, int]:
        if not self.catalog_path.exists():
            return 0, 0, 0
        with duckdb.connect(str(self.catalog_path), read_only=True) as conn:
            work_row = conn.execute("SELECT COUNT(*) FROM works").fetchone()
            artifact_row = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(segment_count), 0)
                FROM artifacts
                """
            ).fetchone()
        if work_row is None or artifact_row is None:
            return 0, 0, 0
        artifact_count, segment_count = artifact_row
        work_count = int(work_row[0])
        return work_count, int(artifact_count), int(segment_count)

    def _emit_progress(
        self,
        *,
        parsed_sources: int,
        artifact_count: int,
        segment_count: int,
        latest_source: Path,
    ) -> None:
        if not self.config.progress_every or self.config.progress_every < 1:
            return
        if parsed_sources % self.config.progress_every != 0:
            return
        if self.config.progress_callback is None:
            return
        self.config.progress_callback(
            ReaderBuildProgress(
                parsed_sources=parsed_sources,
                artifact_count=artifact_count,
                segment_count=segment_count,
                latest_source=str(latest_source),
            )
        )

    def _iter_sources(self) -> Iterator[_ParsedSource]:
        if self.config.source_paths:
            yield from self._source_stream()
            return
        if self.config.limit is None:
            yield from self._source_stream()
            return
        yield from islice(self._source_stream(), self.config.limit)

    def _path_selected(self, path: Path) -> bool:
        return not self._selected_source_paths or path.expanduser().resolve() in (
            self._selected_source_paths
        )

    def _any_path_selected(self, paths: list[Path]) -> bool:
        return not self._selected_source_paths or any(self._path_selected(path) for path in paths)

    def _source_stream(self) -> Iterator[_ParsedSource]:
        yield from self._legacy_sources(self.config.phi_latin_dir, "phi_legacy", "phi", "lat")
        yield from self._legacy_sources(self.config.tlg_e_dir, "tlg_legacy", "tlg", "grc")
        yield from self._sanskrit_sources()
        yield from self._digiliblt_sources()
        yield from self._perseus_sources()
        yield from self._first1k_greek_sources()
        yield from self._opengreekandlatin_latin_sources()
        yield from self._opengreekandlatin_csel_sources()
        yield from self._opengreekandlatin_patrologia_sources()
        yield from self._opengreekandlatin_church_fathers_sources()

    def _register_legacy_source_metadata(self) -> None:
        for root, collection_id in (
            (self.config.phi_latin_dir, "phi"),
            (self.config.tlg_e_dir, "tlg"),
        ):
            if root is None:
                continue
            register_source_files(
                self.catalog_path,
                legacy_source_files(root, collection_id),
            )
            register_source_metadata(
                self.catalog_path,
                legacy_source_metadata(root, collection_id),
            )

    def _register_digiliblt_source_metadata(self) -> None:
        root = self.config.digiliblt_dir
        if root is None or not root.exists():
            return
        files = [
            ReaderSourceFile(
                collection_id="digiliblt",
                source_path=path,
                file_role="digiliblt_tei",
                file_status="text",
                source_id=path.stem,
                source_hash=_file_hash(path),
                size_bytes=path.stat().st_size,
            )
            for path in sorted(root.glob("*.xml"))
        ]
        register_source_files(self.catalog_path, files)
        metadata: list[ReaderSourceMetadata] = []
        for path in sorted(root.glob("*.xml")):
            metadata.extend(_digiliblt_source_metadata(path))
        register_source_metadata(self.catalog_path, metadata)

    def _register_sanskrit_source_metadata(self) -> None:
        if self.config.sanskrit_dir is None or not self.config.sanskrit_dir.exists():
            return
        files: list[ReaderSourceFile] = []
        for path in sorted(self.config.sanskrit_dir.rglob("*.json")):
            files.append(_source_file("sanskrit_json", path, "sanskrit_json"))
        for path in self._sanskrit_plain_text_paths():
            if _is_sanskrit_translation_path(path):
                continue
            role = (
                "sanskrit_numbered_plain"
                if _looks_numbered_sanskrit_safe(path)
                else "sanskrit_plain"
            )
            files.append(_source_file("sanskrit_texts", path, role))
        for path in self._sanskrit_conllu_paths():
            files.append(_source_file("sanskrit_dcs", path, "sanskrit_dcs_conllu"))
        chapter_info_path = self._dcs_chapter_info_path()
        if chapter_info_path is not None:
            files.append(
                _metadata_source_file(
                    "sanskrit_dcs",
                    chapter_info_path,
                    "sanskrit_dcs_chapter_info",
                )
            )
        corpus_table_path = self._dcs_corpus_table_path()
        if corpus_table_path is not None:
            files.append(
                _metadata_source_file(
                    "sanskrit_dcs",
                    corpus_table_path,
                    "sanskrit_dcs_corpus_table",
                )
            )
        register_source_files(self.catalog_path, files)
        metadata: list[ReaderSourceMetadata] = []
        for path in self._sanskrit_plain_text_paths():
            if _is_sanskrit_translation_path(path):
                continue
            metadata.extend(_sanskrit_plain_text_source_metadata(path))
        if metadata:
            register_source_metadata(self.catalog_path, metadata)

    def _register_sanskrit_source_enrichment_metadata(self) -> None:
        if self.config.sanskrit_dir is None or not self.config.sanskrit_dir.exists():
            return
        chapter_info_path = self._dcs_chapter_info_path()
        if chapter_info_path is not None:
            register_source_metadata(
                self.catalog_path,
                parse_dcs_chapter_info_metadata(
                    chapter_info_path.read_text(encoding="utf-8"),
                    source_path=chapter_info_path,
                ),
            )
        corpus_table_path = self._dcs_corpus_table_path()
        if corpus_table_path is not None:
            sync_dcs_corpus_metadata(
                self.catalog_path,
                corpus_table_path.read_text(encoding="utf-8"),
                source_path=corpus_table_path,
            )

    def _register_perseus_source_metadata(self) -> None:
        if self.config.perseus_dir is None or not self.config.perseus_dir.exists():
            return
        files = [
            _source_file("perseus", path, "perseus_tei")
            for path in sorted(self.config.perseus_dir.rglob("*.xml"))
            if _is_perseus_text_xml(path)
        ]
        register_source_files(self.catalog_path, files)

    def _register_first1k_greek_source_metadata(self) -> None:
        if self.config.first1k_greek_dir is None or not self.config.first1k_greek_dir.exists():
            return
        files = [
            _source_file("first1kgreek", path, "first1kgreek_tei")
            for path in self._first1k_greek_text_paths()
        ]
        register_source_files(self.catalog_path, files)

    def _register_opengreekandlatin_source_metadata(self) -> None:
        roots = (
            (self.config.opengreekandlatin_latin_dir, "opengreekandlatin_latin"),
            (self.config.opengreekandlatin_csel_dir, "opengreekandlatin_csel"),
            (self.config.opengreekandlatin_patrologia_dir, "opengreekandlatin_patrologia"),
            (self.config.opengreekandlatin_church_fathers_dir, "opengreekandlatin_church_fathers"),
        )
        for root, collection_id in roots:
            if root is None or not root.exists():
                continue
            candidates = discover_ogl_sources(root, collection_id)
            register_source_files(
                self.catalog_path,
                ogl_source_files(candidates),
            )
            register_source_metadata(
                self.catalog_path,
                ogl_source_metadata(candidates),
            )

    def _perseus_sources(self) -> Iterator[_ParsedSource]:
        if self.config.perseus_dir is None:
            return
        for path in sorted(self.config.perseus_dir.rglob("*.xml")):
            if not self._path_selected(path):
                continue
            if _is_perseus_text_xml(path):
                try:
                    yield _ParsedSource(parse_perseus_tei(path), "perseus_tei")
                except Exception as exc:  # noqa: BLE001
                    self._record_source_error(path, "perseus", exc)

    def _first1k_greek_sources(self) -> Iterator[_ParsedSource]:
        if self.config.first1k_greek_dir is None:
            return
        for path in self._first1k_greek_text_paths():
            if not self._path_selected(path):
                continue
            try:
                parsed = parse_perseus_tei(path, collection_id="first1kgreek")
                if parsed.work.language != "grc":
                    continue
                yield _ParsedSource(parsed, "first1kgreek_tei")
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(path, "first1kgreek", exc)

    def _opengreekandlatin_latin_sources(self) -> Iterator[_ParsedSource]:
        yield from self._opengreekandlatin_sources(
            self.config.opengreekandlatin_latin_dir,
            collection_id="opengreekandlatin_latin",
        )

    def _opengreekandlatin_csel_sources(self) -> Iterator[_ParsedSource]:
        yield from self._opengreekandlatin_sources(
            self.config.opengreekandlatin_csel_dir,
            collection_id="opengreekandlatin_csel",
        )

    def _opengreekandlatin_patrologia_sources(self) -> Iterator[_ParsedSource]:
        yield from self._opengreekandlatin_sources(
            self.config.opengreekandlatin_patrologia_dir,
            collection_id="opengreekandlatin_patrologia",
        )

    def _opengreekandlatin_church_fathers_sources(self) -> Iterator[_ParsedSource]:
        yield from self._opengreekandlatin_sources(
            self.config.opengreekandlatin_church_fathers_dir,
            collection_id="opengreekandlatin_church_fathers",
        )

    def _opengreekandlatin_sources(
        self,
        root: Path | None,
        *,
        collection_id: str,
    ) -> Iterator[_ParsedSource]:
        if root is None:
            return
        for candidate in selected_ogl_sources(root, collection_id):
            path = candidate.source_path
            if not self._path_selected(path):
                continue
            try:
                parsed = parse_ogl_tei(candidate)
                yield _ParsedSource(parsed, f"{collection_id}_tei")
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(path, collection_id, exc)

    def _opengreekandlatin_text_paths(
        self,
        root: Path | None,
        collection_id: str = "opengreekandlatin_latin",
    ) -> list[Path]:
        if root is None or not root.exists():
            return []
        return [candidate.source_path for candidate in selected_ogl_sources(root, collection_id)]

    def _is_opengreekandlatin_source_xml(self, path: Path) -> bool:
        return is_ogl_source_xml(path)

    def _first1k_greek_text_paths(self) -> list[Path]:
        root = self.config.first1k_greek_dir
        if root is None or not root.exists():
            return []
        data_root = root / "data"
        search_root = data_root if data_root.exists() else root
        paths = [
            path
            for path in sorted(search_root.rglob("*.xml"))
            if path.name != "__cts__.xml" and _is_perseus_text_xml(path)
        ]
        if self.config.source_paths:
            return paths
        return _preferred_first1k_greek_text_paths(paths)

    def _digiliblt_sources(self) -> Iterator[_ParsedSource]:
        if self.config.digiliblt_dir is None:
            return
        for path in sorted(self.config.digiliblt_dir.rglob("*.xml")):
            if not self._path_selected(path):
                continue
            try:
                yield _ParsedSource(parse_digiliblt_tei(path), "digiliblt_tei")
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(path, "digiliblt", exc)

    def _legacy_sources(
        self, root: Path | None, adapter: str, collection_id: str, language: str
    ) -> Iterator[_ParsedSource]:
        if root is None:
            return
        for path in sorted(root.rglob("*.txt")):
            if not self._path_selected(path):
                continue
            if collection_id == "tlg" and path.stem.lower().startswith("doccan"):
                continue
            idt_path = path.with_suffix(".idt")
            try:
                if idt_path.exists():
                    for parsed in parse_legacy_text_dump_with_idt(
                        path,
                        idt_path=idt_path,
                        collection_id=collection_id,
                        language=language,
                    ):
                        if not _is_primary_legacy_reader_book(parsed):
                            continue
                        yield _ParsedSource(parsed, f"{collection_id}_idt_legacy")
                else:
                    parsed = parse_legacy_text_dump(
                        path,
                        collection_id=collection_id,
                        language=language,
                    )
                    if not _is_primary_legacy_reader_book(parsed):
                        continue
                    yield _ParsedSource(parsed, adapter)
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(path, collection_id, exc)

    def _sanskrit_sources(self) -> Iterator[_ParsedSource]:
        if self.config.sanskrit_dir is None:
            return
        yield from self._sanskrit_json_sources()
        yield from self._sanskrit_plain_text_sources()
        yield from self._sanskrit_dcs_sources()

    def _sanskrit_json_sources(self) -> Iterator[_ParsedSource]:
        if self.config.sanskrit_dir is None:
            return
        plain_text_gretil_stems = self._sanskrit_plain_text_gretil_stems()
        for path in sorted(self.config.sanskrit_dir.rglob("*.json")):
            if not self._path_selected(path):
                continue
            gretil_stem = _sanskrit_gretil_comparable_stem(path)
            if gretil_stem is not None and gretil_stem in plain_text_gretil_stems:
                continue
            try:
                yield _ParsedSource(parse_sanskrit_json(path), "sanskrit_json")
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(path, "sanskrit", exc)

    def _sanskrit_plain_text_sources(self) -> Iterator[_ParsedSource]:
        grouped_paths = self._sanskrit_grouped_plain_text_paths()
        grouped_path_set = {path for paths in grouped_paths for path in paths}
        for paths in grouped_paths:
            if any(_is_sanskrit_translation_path(path) for path in paths):
                continue
            if not self._any_path_selected(paths):
                continue
            try:
                yield _ParsedSource(
                    parse_sanskrit_plain_text_group(
                        paths,
                        collection_id="sanskrit_texts",
                        language="san",
                    ),
                    "sanskrit_split_plain",
                )
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(paths[0], "sanskrit_texts", exc)

        for path in self._sanskrit_plain_text_paths():
            if path in grouped_path_set:
                continue
            if _is_sanskrit_translation_path(path):
                continue
            if not self._path_selected(path):
                continue
            try:
                parsed = parse_sanskrit_plain_text(
                    path,
                    collection_id="sanskrit_texts",
                    language="san",
                )
                adapter = (
                    "sanskrit_numbered_plain"
                    if parsed.edition.label == "numbered plain text"
                    else "sanskrit_plain"
                )
                yield _ParsedSource(
                    parsed,
                    adapter,
                )
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(path, "sanskrit_texts", exc)

    def _sanskrit_dcs_sources(self) -> Iterator[_ParsedSource]:
        for paths in self._sanskrit_conllu_groups():
            if not self._any_path_selected(paths):
                continue
            try:
                if len(paths) == 1:
                    yield _ParsedSource(parse_dcs_conllu(paths[0]), "sanskrit_dcs_conllu")
                else:
                    yield _ParsedSource(
                        parse_dcs_conllu_group(paths),
                        "sanskrit_dcs_conllu",
                    )
            except Exception as exc:  # noqa: BLE001
                self._record_source_error(paths[0], "sanskrit_dcs", exc)

    def _sanskrit_plain_text_paths(self) -> list[Path]:
        if self.config.sanskrit_dir is None:
            return []
        paths: list[Path] = []
        for path in sorted(self.config.sanskrit_dir.rglob("*.txt")):
            if _is_sanskrit_translation_path(path):
                continue
            if _is_raw_sanskrit_ocr_chunk_with_split(path):
                continue
            paths.append(path)
        return paths

    def _sanskrit_plain_text_gretil_stems(self) -> set[str]:
        return {
            stem
            for path in self._sanskrit_plain_text_paths()
            if (stem := _sanskrit_gretil_comparable_stem(path)) is not None
        }

    def _sanskrit_grouped_plain_text_paths(self) -> list[list[Path]]:
        groups: dict[Path, list[Path]] = defaultdict(list)
        for path in self._sanskrit_plain_text_paths():
            if _is_sanskrit_split_chunk(path):
                groups[path.parent].append(path)
        return [sorted(paths) for _dir, paths in sorted(groups.items())]

    def _sanskrit_conllu_paths(self) -> list[Path]:
        if self.config.sanskrit_dir is None:
            return []
        dcs_root = self.config.sanskrit_dir / "dcs"
        roots = [dcs_root] if dcs_root.exists() else [self.config.sanskrit_dir]
        paths: list[Path] = []
        for root in roots:
            paths.extend(sorted(root.rglob("*.conllu")))
            paths.extend(sorted(root.rglob("*.conllu_parsed")))
        return paths

    def _sanskrit_conllu_groups(self) -> list[list[Path]]:
        groups: dict[str, list[Path]] = defaultdict(list)
        for path in self._sanskrit_conllu_paths():
            groups[_dcs_group_key(path)].append(path)
        return [sorted(paths) for _key, paths in sorted(groups.items())]

    def _dcs_chapter_info_path(self) -> Path | None:
        if self.config.sanskrit_dir is None:
            return None
        for path in _dcs_lookup_candidates(self.config.sanskrit_dir, ("chapter-info.xml",)):
            if path.exists():
                return path
        return None

    def _dcs_corpus_table_path(self) -> Path | None:
        if self.config.sanskrit_dir is None:
            return None
        filenames = (
            "dcs-corpus.tsv",
            "dcs-corpus.txt",
            "dcs-corpus.md",
            "corpus.tsv",
            "corpus.txt",
            "corpus.md",
        )
        for path in _dcs_lookup_candidates(self.config.sanskrit_dir, filenames):
            if path.exists():
                return path
        return None

    def _artifact(self, source: _ParsedSource, book_path: Path) -> ReaderBookArtifact:
        parsed = source.parsed
        return ReaderBookArtifact(
            artifact_id=_slug(f"{parsed.work.work_id}:{parsed.edition.edition_id}"),
            work_id=parsed.work.work_id,
            edition_id=parsed.edition.edition_id,
            artifact_path=book_path,
            source_path=parsed.edition.source_path,
            adapter=source.adapter,
            source_hash=self._file_hash(parsed.edition.source_path),
            segment_count=len(parsed.segments),
            token_count=sum(len(segment.text.split()) for segment in parsed.segments),
        )

    def _file_hash(self, path: Path) -> str:
        try:
            key = path.resolve()
        except OSError:
            key = path
        source_hash = self._source_hashes.get(key)
        if source_hash is None:
            source_hash = _file_hash(path)
            self._source_hashes[key] = source_hash
        return source_hash

    def _canonicalize_source(self, source: _ParsedSource) -> _ParsedSource:
        work = source.parsed.work
        if not work.author_id:
            return source
        canonical = self._canonical_author(work.author_id)
        if canonical is None:
            return source
        author_name, author_urn = canonical
        parsed = ParsedBook(
            work=replace(
                work,
                author=author_name,
                author_id=author_urn or work.author_id,
            ),
            edition=source.parsed.edition,
            segments=source.parsed.segments,
            addresses=source.parsed.addresses,
            citation_references=source.parsed.citation_references,
        )
        return _ParsedSource(parsed=parsed, adapter=source.adapter)

    def _normalize_author_source(self, source: _ParsedSource) -> _ParsedSource:
        work = source.parsed.work
        normalized_author = normalize_reader_author(work.author)
        if normalized_author == work.author:
            return source
        parsed = ParsedBook(
            work=replace(work, author=normalized_author),
            edition=source.parsed.edition,
            segments=source.parsed.segments,
            addresses=source.parsed.addresses,
            citation_references=source.parsed.citation_references,
        )
        return _ParsedSource(parsed=parsed, adapter=source.adapter)

    def _apply_metadata_overlays(self, source: _ParsedSource) -> _ParsedSource:
        work = source.parsed.work
        edition = source.parsed.edition
        for overlay in self._accepted_metadata_overlays:
            if not _overlay_matches_work(overlay, work):
                continue
            if overlay.field == "author":
                work = replace(work, author=normalize_reader_author(overlay.value))
            elif overlay.field == "author_id":
                work = replace(work, author_id=overlay.value)
            elif overlay.field == "title":
                work = replace(work, title=overlay.value)
            elif overlay.field == "language":
                work = replace(work, language=overlay.value)
                edition = replace(edition, language=overlay.value)
            elif overlay.field == "cts_work_urn":
                work = replace(work, cts_work_urn=overlay.value)
        if work == source.parsed.work and edition == source.parsed.edition:
            return source
        return _ParsedSource(
            parsed=ParsedBook(
                work=work,
                edition=edition,
                segments=source.parsed.segments,
                addresses=source.parsed.addresses,
                citation_references=source.parsed.citation_references,
            ),
            adapter=source.adapter,
        )

    def _apply_ctsv2_identity(self, source: _ParsedSource) -> _ParsedSource:
        work = source.parsed.work
        if work.canonical_text_id:
            return source
        incipit = next(
            (segment.text for segment in source.parsed.segments if segment.text.strip()),
            "",
        )
        canonical_text_id = ctsv2_text_id(work.language, work.title, incipit)
        return _ParsedSource(
            parsed=ParsedBook(
                work=replace(work, canonical_text_id=canonical_text_id),
                edition=source.parsed.edition,
                segments=source.parsed.segments,
                addresses=source.parsed.addresses,
                citation_references=source.parsed.citation_references,
            ),
            adapter=source.adapter,
        )

    def _canonical_author(self, author_id: str) -> tuple[str, str | None] | None:
        return self._load_author_authority().get(author_id)

    def _load_author_authority(self) -> dict[str, tuple[str, str | None]]:
        if self._author_authority is not None:
            return self._author_authority
        authority: dict[str, tuple[str, str | None]] = {}
        path = self.config.cts_index_path
        if path is not None and path.exists():
            with duckdb.connect(str(path), read_only=True) as conn:
                rows = conn.execute(
                    """
                    SELECT author_id, author_name, author_urn
                    FROM author_index
                    WHERE author_name IS NOT NULL AND author_name != ''
                    """
                ).fetchall()
            for author_id, author_name, author_urn in rows:
                clean_author_name = _legacy_metadata_text(str(author_name))
                if not _usable_authority_name(clean_author_name):
                    continue
                authority[str(author_id)] = (clean_author_name, str(author_urn) or None)
                if author_urn:
                    authority[str(author_urn)] = (clean_author_name, str(author_urn))
        for author_id, author_name in self._html_author_authority().items():
            current = authority.get(author_id)
            if current is None or normalize_reader_author(current[0]) == "Pseudo":
                authority[author_id] = (author_name, current[1] if current else None)
        for author_id, author_name in self._tlg_canon_author_authority().items():
            current = authority.get(author_id)
            if current is None or not _usable_authority_name(current[0]):
                authority[author_id] = (author_name, current[1] if current else None)
        self._author_authority = authority
        return authority

    def _html_author_authority(self) -> dict[str, str]:
        if self.config.tlg_e_dir is None:
            return {}
        html_path = self.config.tlg_e_dir / "cd.authors.php"
        if not html_path.exists():
            return {}
        authority: dict[str, str] = {}
        for row in parse_html_author_index(html_path, collection_id="tlg"):
            parsed = canonical_author_from_html_index_item(row.value)
            if parsed is None:
                continue
            author_id, author_name = parsed
            authority[author_id] = author_name
        return authority

    def _tlg_canon_author_authority(self) -> dict[str, str]:
        authority = self._tlg_canon_author_authority_from_catalog()
        if authority:
            return authority
        if self.config.tlg_e_dir is None:
            return {}
        for path in sorted(self.config.tlg_e_dir.glob("doccan*.txt")):
            for row in parse_tlg_canon_source_metadata(path, collection_id="tlg"):
                if row.subject_kind != "author" or row.key != "tlg_canon_author_name":
                    continue
                name = normalize_reader_author(row.value)
                if _usable_authority_name(name):
                    authority[row.subject_id] = name
        return authority

    def _tlg_canon_author_authority_from_catalog(self) -> dict[str, str]:
        if not self.catalog_path.exists():
            return {}
        try:
            with duckdb.connect(str(self.catalog_path), read_only=True) as conn:
                rows = conn.execute(
                    """
                    SELECT subject_id, value
                    FROM source_metadata
                    WHERE collection_id = 'tlg'
                      AND subject_kind = 'author'
                      AND key = 'tlg_canon_author_name'
                      AND value IS NOT NULL
                      AND trim(value) != ''
                    """
                ).fetchall()
        except duckdb.Error:
            return {}
        return {
            str(author_id): normalize_reader_author(str(author_name))
            for author_id, author_name in rows
            if _usable_authority_name(str(author_name))
        }

    def _record_source_error(self, path: Path, collection_id: str, exc: Exception) -> None:
        self.source_errors.append((path, collection_id, str(exc)))

    def _register_source_errors(self) -> None:
        if not self.source_errors:
            return
        register_source_files(
            self.catalog_path,
            [
                ReaderSourceFile(
                    collection_id=collection_id,
                    source_path=path,
                    file_role="text",
                    file_status="error",
                    source_id=path.stem,
                    size_bytes=path.stat().st_size if path.exists() else None,
                )
                for path, collection_id, _error in self.source_errors
            ],
        )
        register_source_metadata(
            self.catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id=collection_id,
                    subject_kind="source_file",
                    subject_id=path.stem,
                    key="import_error",
                    value=error,
                    source_path=path,
                )
                for path, collection_id, error in self.source_errors
            ],
        )

    def _book_path(self, parsed: ParsedBook) -> Path:
        if parsed.work.collection_id in {"phi", "tlg"}:
            author = parsed.work.author_id or parsed.work.author
            return (
                self.output_root
                / "books"
                / _slug(parsed.work.collection_id)
                / _namespace(parsed.work.work_id)
                / _slug(author)
                / f"{_slug(parsed.edition.source_path.stem)}.duckdb"
            )
        author = parsed.work.author_id or parsed.work.author
        return (
            self.output_root
            / "books"
            / _slug(parsed.work.collection_id)
            / _namespace(parsed.work.work_id)
            / _slug(author)
            / _slug(parsed.work.source_id)
            / f"{_slug(parsed.edition.edition_id)}.duckdb"
        )


def _namespace(work_id: str) -> str:
    if work_id.startswith("urn:cts:"):
        parts = work_id.split(":")
        if len(parts) >= CTS_URN_MIN_PARTS:
            return _slug(parts[2])
    return "langnet"


def _overlay_matches_work(overlay, work) -> bool:
    if overlay.collection_id != work.collection_id:
        return False
    if overlay.match_field == "author_id":
        work_author_id = work.author_id
        if not work_author_id:
            return False
        return compact_author_id(overlay.match_value) == compact_author_id(work_author_id)
    work_value = {
        "source_id": work.source_id,
        "work_id": work.work_id,
        "cts_work_urn": work.cts_work_urn,
    }.get(overlay.match_field)
    return overlay.match_value == work_value


def _is_perseus_text_xml(path: Path) -> bool:
    return path.name not in {"__cts__.xml", "build.xml", "expath-pkg.xml", "repo.xml"}


def _looks_like_opengreekandlatin_tei(path: Path) -> bool:
    return looks_like_ogl_tei(path)


def _preferred_opengreekandlatin_text_paths(root: Path, paths: list[Path]) -> list[Path]:
    candidates = discover_ogl_sources(root, "opengreekandlatin_latin")
    selected_paths = {
        candidate.source_path
        for candidate in candidates
        if candidate.import_status == "text_imported"
    }
    return [path for path in paths if path in selected_paths]


def _preferred_first1k_greek_text_paths(paths: list[Path]) -> list[Path]:
    by_work_dir: dict[Path, list[Path]] = defaultdict(list)
    for path in paths:
        by_work_dir[path.parent].append(path)
    return [
        sorted(group, key=_first1k_greek_text_preference_key)[0]
        for _, group in sorted(by_work_dir.items(), key=lambda item: str(item[0]))
    ]


def _first1k_greek_text_preference_key(path: Path) -> tuple[int, str]:
    match = re.search(r"\.1st1K-grc(?P<edition>\d+)\.xml$", path.name)
    if not match:
        return 100, path.name
    edition = int(match.group("edition"))
    return edition - 1, path.name


def _digiliblt_source_metadata(path: Path) -> list[ReaderSourceMetadata]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [
            ReaderSourceMetadata(
                collection_id="digiliblt",
                subject_kind="source_file",
                subject_id=path.stem,
                key="metadata_parse_error",
                value=str(exc),
                source_path=path,
            )
        ]
    explicit_author = _find_xml_text(root, "author")
    title = _find_xml_text(root, "title")
    edition = _find_xml_text(root, "sourceDesc")
    author, author_resolution = resolve_digiliblt_author(
        explicit_author=explicit_author or None,
        title=title,
        source_desc=edition,
    )
    values = {
        "source_id": _find_xml_text(root, "idno"),
        "title": title,
        "author": author,
        "edition": edition,
        "language": _digiliblt_language(root),
        "publisher": _find_xml_text(root, "publisher"),
        "publication_date": _find_xml_text(root, "date"),
    }
    rows = [
        ReaderSourceMetadata(
            collection_id="digiliblt",
            subject_kind="work",
            subject_id=path.stem,
            key=key,
            value=value,
            source_path=path,
        )
        for key, value in values.items()
        if value
    ]
    for key in ("source_id", "title", "edition", "language"):
        if not values[key]:
            rows.append(
                ReaderSourceMetadata(
                    collection_id="digiliblt",
                    subject_kind="work",
                    subject_id=path.stem,
                    key="metadata_issue",
                    value=f"missing_{key}",
                    source_path=path,
                )
            )
    if not explicit_author:
        rows.append(
            ReaderSourceMetadata(
                collection_id="digiliblt",
                subject_kind="work",
                subject_id=path.stem,
                key="metadata_issue",
                value="source_author_blank",
                source_path=path,
            )
        )
        rows.append(
            ReaderSourceMetadata(
                collection_id="digiliblt",
                subject_kind="work",
                subject_id=path.stem,
                key="author_resolution",
                value=author_resolution,
                source_path=path,
            )
        )
    elif normalize_digiliblt_author(explicit_author) != explicit_author:
        rows.append(
            ReaderSourceMetadata(
                collection_id="digiliblt",
                subject_kind="work",
                subject_id=path.stem,
                key="source_author",
                value=explicit_author,
                source_path=path,
            )
        )
        rows.append(
            ReaderSourceMetadata(
                collection_id="digiliblt",
                subject_kind="work",
                subject_id=path.stem,
                key="author_resolution",
                value=author_resolution,
                source_path=path,
            )
        )
    return rows


def _sanskrit_plain_text_source_metadata(path: Path) -> list[ReaderSourceMetadata]:
    subject_id = _path_source_id(path)
    rows: list[ReaderSourceMetadata] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        return [
            ReaderSourceMetadata(
                collection_id="sanskrit_texts",
                subject_kind="source_file",
                subject_id=subject_id,
                key="metadata_parse_error",
                value=str(exc),
                source_path=path,
            )
        ]
    for raw_line in lines[:50]:
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue
        if not line.startswith("#"):
            break
        key, separator, value = line[1:].partition(":")
        if separator:
            metadata_key = _sanskrit_plain_text_metadata_key(key)
            metadata_value = _normalize_metadata_value(value)
        else:
            metadata_key = "gretil_header"
            metadata_value = _normalize_metadata_value(key)
        if not metadata_value:
            continue
        rows.append(
            ReaderSourceMetadata(
                collection_id="sanskrit_texts",
                subject_kind="work",
                subject_id=subject_id,
                key=metadata_key,
                value=metadata_value,
                source_path=path,
            )
        )
    return rows


def _sanskrit_plain_text_metadata_key(value: str) -> str:
    normalized = _slug(value.casefold().replace(" ", "_").replace("-", "_"))
    return f"gretil_{normalized}" if normalized else "gretil_header"


def _normalize_metadata_value(value: str) -> str:
    return " ".join(value.split()).strip()


def _find_xml_text(root: ET.Element, local_name: str) -> str:
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] == local_name:
            return " ".join("".join(node.itertext()).split())
    return ""


def _digiliblt_language(root: ET.Element) -> str:
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] == "language":
            ident = node.attrib.get("ident", "").strip()
            if ident:
                return "lat" if ident == "la" else ident
            value = " ".join("".join(node.itertext()).split()).lower()
            if value in {"latino", "latin"}:
                return "lat"
            return value
    return "lat"


def _aliases_for_registrations(
    aliases: list[ReaderAlias],
    registrations: list[ReaderBookRegistration],
) -> list[ReaderAlias]:
    work_ids = {registration.work.work_id for registration in registrations}
    cts_work_urns = {
        registration.work.cts_work_urn
        for registration in registrations
        if registration.work.cts_work_urn is not None
    }
    canonical_text_ids = {
        registration.work.canonical_text_id
        for registration in registrations
        if registration.work.canonical_text_id is not None
    }
    curated = [
        alias
        for alias in aliases
        if alias.target in work_ids
        or alias.target in cts_work_urns
        or alias.target in canonical_text_ids
    ]
    generated: list[ReaderAlias] = []
    seen = {(alias.language, alias.alias, alias.target) for alias in curated}
    for registration in registrations:
        work = registration.work
        target = work.canonical_text_id or work.cts_work_urn or work.work_id
        display = f"{work.author}, {work.title}" if work.author else work.title
        for alias_value, kind, sources in (
            (work.canonical_text_id, "canonical_text_id", ("ctsv2",)),
            (work.cts_work_urn, "source_urn", (work.collection_id,)),
            (work.work_id, "work_id", (work.collection_id,)),
            (work.source_id, "source_id", (work.collection_id,)),
        ):
            if not alias_value:
                continue
            key = (work.language, alias_value, target)
            if key in seen:
                continue
            seen.add(key)
            generated.append(
                ReaderAlias(
                    alias=alias_value,
                    language=work.language,
                    kind=kind,
                    target=target,
                    display=display,
                    source_file="generated:reader-builder",
                    sources=sources,
                )
            )
    return [*curated, *_unambiguous_aliases(generated)]


def _ensure_unique_canonical_text_ids(
    registrations: list[ReaderBookRegistration],
) -> list[ReaderBookRegistration]:
    by_text_id: dict[tuple[str, str], list[ReaderBookRegistration]] = defaultdict(list)
    for registration in registrations:
        canonical_text_id = registration.work.canonical_text_id
        if not canonical_text_id:
            continue
        by_text_id[(registration.work.language, canonical_text_id)].append(registration)

    replacements: dict[str, str] = {}
    used: set[tuple[str, str]] = set()
    for (language, canonical_text_id), group in by_text_id.items():
        if len(group) == 1:
            used.add((language, canonical_text_id))
            continue
        for index, registration in enumerate(group, start=1):
            suffix = _ctsv2_disambiguator(registration, fallback_index=index)
            candidate = f"{canonical_text_id}-{suffix}"
            disambiguation_index = index
            while (language, candidate) in used:
                disambiguation_index += 1
                candidate = f"{canonical_text_id}-{suffix}-{disambiguation_index}"
            used.add((language, candidate))
            replacements[registration.work.work_id] = candidate

    if not replacements:
        return registrations
    return [
        _replace_registration_work(
            registration,
            canonical_text_id=replacements.get(registration.work.work_id),
        )
        for registration in registrations
    ]


def _replace_registration_work(
    registration: ReaderBookRegistration,
    *,
    canonical_text_id: str | None,
) -> ReaderBookRegistration:
    if canonical_text_id is None:
        return registration
    return ReaderBookRegistration(
        work=replace(registration.work, canonical_text_id=canonical_text_id),
        edition=registration.edition,
        artifact=registration.artifact,
    )


def _ctsv2_disambiguator(
    registration: ReaderBookRegistration,
    *,
    fallback_index: int,
) -> str:
    work = registration.work
    for value in (work.source_id, work.cts_work_urn, work.work_id):
        suffix = _ascii_slug(value)
        if suffix:
            return suffix
    return f"text-{fallback_index}"


def _ascii_slug(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", without_marks).strip("-")


def _registrations_for_work_ids(
    registrations: list[ReaderBookRegistration],
    work_ids: set[str],
) -> list[ReaderBookRegistration]:
    return [registration for registration in registrations if registration.work.work_id in work_ids]


def _dedupe_book_registrations_for_catalog(
    registrations: list[ReaderBookRegistration],
) -> list[ReaderBookRegistration]:
    by_work_id: dict[str, ReaderBookRegistration] = {}
    by_edition_id: dict[str, str] = {}
    by_artifact_id: dict[str, str] = {}
    for registration in registrations:
        old_work_id = by_edition_id.get(registration.edition.edition_id)
        if old_work_id is not None and old_work_id != registration.work.work_id:
            by_work_id.pop(old_work_id, None)
        old_work_id = by_artifact_id.get(registration.artifact.artifact_id)
        if old_work_id is not None and old_work_id != registration.work.work_id:
            by_work_id.pop(old_work_id, None)
        by_work_id[registration.work.work_id] = registration
        by_edition_id[registration.edition.edition_id] = registration.work.work_id
        by_artifact_id[registration.artifact.artifact_id] = registration.work.work_id
    return list(by_work_id.values())


def _unambiguous_aliases(aliases: list[ReaderAlias]) -> list[ReaderAlias]:
    targets_by_alias: dict[tuple[str, str], set[str]] = defaultdict(set)
    for alias in aliases:
        targets_by_alias[(alias.language, alias.alias)].add(alias.target)
    return [alias for alias in aliases if len(targets_by_alias[(alias.language, alias.alias)]) == 1]


def _source_witnesses_for_registrations(
    registrations: list[ReaderBookRegistration],
) -> list[ReaderSourceWitness]:
    witnesses: list[ReaderSourceWitness] = []
    for registration in registrations:
        work = registration.work
        if not work.canonical_text_id:
            continue
        witness_id = work.cts_work_urn or work.source_id or work.work_id
        witnesses.append(
            ReaderSourceWitness(
                canonical_text_id=work.canonical_text_id,
                work_id=work.work_id,
                collection_id=work.collection_id,
                language=work.language,
                witness_id=witness_id,
                source_id=work.source_id,
                source_urn=work.cts_work_urn or "",
                source_path=registration.edition.source_path,
                status="accepted",
                confidence="medium",
                note="Generated during reader build from accepted source registration.",
            )
        )
    return witnesses


def _work_relations_for_contained_works(
    contained_works: list,
) -> list[ReaderWorkRelation]:
    relations: list[ReaderWorkRelation] = []
    for contained in contained_works:
        if contained.status != "accepted":
            continue
        relations.append(
            ReaderWorkRelation(
                source_id=contained.contained_work_id,
                target_id=contained.parent_work_id,
                relation_type="contained_in",
                status=contained.status,
                confidence=contained.confidence,
                note=contained.note,
                source_file=contained.source_file,
            )
        )
        relations.append(
            ReaderWorkRelation(
                source_id=contained.parent_work_id,
                target_id=contained.contained_work_id,
                relation_type="contains",
                status=contained.status,
                confidence=contained.confidence,
                note=contained.note,
                source_file=contained.source_file,
            )
        )
    return relations


def _usable_authority_name(name: str) -> bool:
    normalized = normalize_reader_author(name)
    if normalized.casefold() in {"", "unknown"}:
        return False
    return any(char.isalpha() for char in normalized)


def _source_file(collection_id: str, path: Path, role: str) -> ReaderSourceFile:
    return ReaderSourceFile(
        collection_id=collection_id,
        source_path=path,
        file_role=role,
        file_status="text",
        source_id=_path_source_id(path),
        source_hash=_file_hash(path),
        size_bytes=path.stat().st_size,
    )


def _metadata_source_file(collection_id: str, path: Path, role: str) -> ReaderSourceFile:
    return ReaderSourceFile(
        collection_id=collection_id,
        source_path=path,
        file_role=role,
        file_status="metadata",
        source_id=_path_source_id(path),
        source_hash=_file_hash(path),
        size_bytes=path.stat().st_size,
    )


def _dcs_lookup_candidates(root: Path, filenames: tuple[str, ...]) -> list[Path]:
    lookup_roots = (
        root / "dcs" / "data" / "conllu" / "lookup",
        root / "data" / "conllu" / "lookup",
        root / "dcs" / "lookup",
        root / "lookup",
        root,
    )
    return [lookup_root / filename for lookup_root in lookup_roots for filename in filenames]


def _looks_numbered_sanskrit_safe(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:100]
    except UnicodeDecodeError:
        return False
    matches = 0
    for line in lines:
        stripped = line.strip()
        if (
            len(stripped) > NUMBERED_SANSKRIT_MIN_LINE_LENGTH
            and stripped[:NUMBERED_SANSKRIT_CODE_LENGTH].isdigit()
            and stripped[NUMBERED_SANSKRIT_CODE_LENGTH].isspace()
        ):
            matches += 1
    return matches >= NUMBERED_SANSKRIT_MIN_MATCHES


def _is_sanskrit_translation_path(path: Path) -> bool:
    return any(part.casefold() in SANSKRIT_TRANSLATION_PATH_PARTS for part in path.parts)


def _is_primary_legacy_reader_book(parsed: ParsedBook) -> bool:
    if parsed.work.collection_id not in {"phi", "tlg"}:
        return True
    return parsed.work.language in PRIMARY_READER_LANGUAGES


def _is_sanskrit_split_chunk(path: Path) -> bool:
    return path.parent.name == "split" and path.parent.parent.name != ""


def _is_raw_sanskrit_ocr_chunk_with_split(path: Path) -> bool:
    return (
        path.parent.name == "ocr"
        and path.parent.parent.joinpath("split").is_dir()
        and any(path.parent.parent.joinpath("split").glob("*.txt"))
    )


def _path_source_id(path: Path) -> str:
    return _slug(f"{path.parent.name}_{path.stem}")


def _sanskrit_gretil_comparable_stem(path: Path) -> str | None:
    return _sanskrit_gretil_comparable_source_id(_path_source_id(path))


def _sanskrit_gretil_comparable_source_id(source_id: str) -> str | None:
    for prefix in ("corpus_", "GRETIL_"):
        source_id = source_id.removeprefix(prefix)
    return source_id if source_id.startswith("sa_") else None


def _dcs_group_key(path: Path) -> str:
    parts = path.parts
    if "files" in parts:
        index = parts.index("files")
        if index + 1 < len(parts):
            return "/".join(parts[: index + 2])
    return str(path.parent)


def _slug(value: str) -> str:
    slug = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    return slug.strip("._") or "unknown"


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
