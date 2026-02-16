from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from .base import BuildResult, BuildStatus
from .paths import default_cts_path

logger = logging.getLogger(__name__)

CTS_NS = "http://chs.harvard.edu/xmlns/cts"
TI = {"ti": CTS_NS}
ENTRY_TYPE_MARKER = 0x10
MIN_TITLE_LENGTH = 4
LEGACY_CATALOG_MIN_FIELDS = 7


def _clean_author_name(raw_name: str) -> str:
    """Clean raw author name by removing &1 prefix and & Topic suffix."""
    if not raw_name:
        return raw_name
    if raw_name.startswith("&1"):
        raw_name = raw_name[2:]
    if "&" in raw_name:
        raw_name = raw_name.split("&")[0]
    return raw_name.strip()


def _clean_work_title(raw_title: str) -> str:
    """Clean raw work title by removing unwanted characters."""
    return raw_title.strip() if raw_title else raw_title


@dataclass
class EditionEntry:
    edition_urn: str
    work_urn: str
    label: str
    description: str
    language: str
    source_path: Path


@dataclass
class WorkEntry:
    author_id: str
    author_urn: str
    author_name: str
    work_urn: str
    work_title: str
    language: str
    namespace: str
    work_reference: str
    source_path: Path
    editions: list[EditionEntry] = field(default_factory=list)


def _normalize_author_id(urn: str) -> str:
    """Extract author id (phi/tlg…) from a CTS urn."""
    return urn.split(":")[-1] if urn else ""


def _author_id_from_work_urn(work_urn: str) -> str:
    """
    Derive author id from a work URN by stripping the work component.
    Example: urn:cts:latinLit:phi0959.phi006 -> phi0959
    """
    work_part = work_urn.split(":")[-1] if work_urn else ""
    return work_part.split(".")[0] if "." in work_part else work_part


def _normalize_work_reference(work_urn: str) -> str:
    """Return a stable work reference used for ordering."""
    if not work_urn:
        return ""
    if ":" in work_urn:
        work_urn = work_urn.split(":")[-1]
    return work_urn


def _get_text(element: ET.Element, tag: str) -> str:
    found = element.find(f"ti:{tag}", TI)
    return found.text.strip() if found is not None and found.text else ""


@dataclass
class CtsBuildConfig:
    """Configuration for CtsUrnBuilder."""

    perseus_dir: Path | None = None
    legacy_dir: Path | None = None
    output_path: Path | None = None
    include_legacy: bool = True
    batch_size: int = 1000
    wipe_existing: bool = True
    force_rebuild: bool = False
    max_works: int | None = None


class CtsUrnBuilder:
    """
    Build CTS URN lookup DuckDB from Perseus + Packard/legacy corpora.
    """

    def __init__(self, config: CtsBuildConfig) -> None:
        self.perseus_dir = (config.perseus_dir or Path.home() / "perseus").expanduser()
        self.legacy_dir = (config.legacy_dir or Path.home() / "Classics-Data").expanduser()
        self.output_path = config.output_path or default_cts_path()
        self.include_legacy = config.include_legacy
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self.max_works = config.max_works

        self._entries: list[WorkEntry] = []
        self._editions: list[EditionEntry] = []
        self._connection: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult:
        try:
            if self.output_path.exists():
                if self.wipe_existing:
                    logger.info("Deleting existing CTS index at %s", self.output_path)
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    logger.info("CTS index already exists; skipping rebuild")
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=self.get_stats(),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            logger.info("Building CTS URN index from %s", self.perseus_dir)
            self._parse_source_data()
            self._build_duckdb()
            valid = self.validate()
            status = BuildStatus.SUCCESS if valid else BuildStatus.FAILED
            return BuildResult(status=status, output_path=self.output_path, stats=self.get_stats())
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to build CTS URN index: %s", exc)
            return BuildResult(
                status=BuildStatus.FAILED,
                output_path=self.output_path,
                stats={"error": str(exc)},
                message=str(exc),
            )
        finally:
            self.cleanup()

    def _parse_source_data(self) -> None:
        self._entries = []
        self._editions = []

        latin_root = self.perseus_dir / "canonical-latinLit" / "data"
        greek_root = self.perseus_dir / "canonical-greekLit" / "data"

        if not latin_root.exists() and not greek_root.exists():
            raise FileNotFoundError(
                f"Expected Perseus corpora under {self.perseus_dir}, "
                "found neither latinLit nor greekLit",
            )

        for root, namespace, language in (
            (latin_root, "latinLit", "lat"),
            (greek_root, "greekLit", "grc"),
        ):
            if not root.exists():
                logger.debug("Corpus root missing: %s", root)
                continue
            corpus_entries, corpus_editions = self._collect_corpus(root, namespace, language)
            self._entries.extend(corpus_entries)
            self._editions.extend(corpus_editions)
            logger.info(
                "Parsed %s works and %s editions from %s",
                len(corpus_entries),
                len(corpus_editions),
                root,
            )

        if self.include_legacy and self.legacy_dir.exists():
            self._augment_with_legacy()
        elif self.include_legacy:
            logger.info("Legacy/Packard data not found at %s; skipping", self.legacy_dir)

        if self.max_works is not None and self._entries:
            self._entries = self._entries[: self.max_works]
            allowed = {e.work_urn for e in self._entries}
            self._editions = [ed for ed in self._editions if ed.work_urn in allowed]
            logger.info("Limited CTS entries to first %s works for sampling", self.max_works)

        if not self._entries:
            raise RuntimeError("No CTS works parsed from Perseus data")

    def _collect_corpus(
        self, corpus_root: Path, namespace: str, language: str
    ) -> tuple[list[WorkEntry], list[EditionEntry]]:
        authors: dict[str, dict[str, str]] = {}
        works: list[WorkEntry] = []
        editions: list[EditionEntry] = []

        # First pass: textgroup metadata
        for cts_file in sorted(corpus_root.glob("**/__cts__.xml")):
            try:
                root = ET.parse(cts_file).getroot()
                if not root.tag.endswith("textgroup"):
                    continue
                urn = root.attrib.get("urn", "")
                author_id = _normalize_author_id(urn)
                if not author_id:
                    continue
                authors[author_id] = {
                    "author_urn": urn,
                    "author_name": _get_text(root, "groupname") or author_id,
                    "language": root.attrib.get(
                        "{http://www.w3.org/XML/1998/namespace}lang", language
                    )
                    or language,
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to parse textgroup %s: %s", cts_file, exc)

        # Second pass: works + editions
        for cts_file in sorted(corpus_root.glob("**/__cts__.xml")):
            try:
                root = ET.parse(cts_file).getroot()
                if not root.tag.endswith("work"):
                    continue

                work_urn = root.attrib.get("urn", "")
                author_id = _author_id_from_work_urn(work_urn)
                if author_id not in authors:
                    continue
                author_info = authors[author_id]

                work_title = _get_text(root, "title")
                work_ref = _normalize_work_reference(work_urn)
                work_entry = WorkEntry(
                    author_id=author_id,
                    author_urn=author_info["author_urn"],
                    author_name=author_info["author_name"],
                    work_urn=work_urn,
                    work_title=work_title,
                    language=author_info["language"],
                    namespace=namespace,
                    work_reference=work_ref,
                    source_path=cts_file,
                )

                for edition in root.findall("ti:edition", TI):
                    edition_urn = edition.attrib.get("urn", "")
                    label = _get_text(edition, "label") or work_title
                    description = _get_text(edition, "description")
                    language_code = edition.attrib.get(
                        "{http://www.w3.org/XML/1998/namespace}lang", language
                    )
                    editions.append(
                        EditionEntry(
                            edition_urn=edition_urn,
                            work_urn=work_urn,
                            label=label,
                            description=description,
                            language=language_code or language,
                            source_path=cts_file,
                        )
                    )
                works.append(work_entry)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to parse work %s: %s", cts_file, exc)

        return works, editions

    def _augment_with_legacy(self) -> None:
        legacy_catalog = self.legacy_dir / "Perseus_catalog" / "Perseus_parsed_catalog.txt"
        if not legacy_catalog.exists():
            logger.info("Legacy catalog not found at %s; skipping legacy merge", legacy_catalog)
            return

        with legacy_catalog.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) < LEGACY_CATALOG_MIN_FIELDS:
                    continue
                work_urn, language, author_name, work_title, namespace, _, source_path = parts[:7]
                author_id = _author_id_from_work_urn(work_urn)
                if not author_id:
                    continue
                work_ref = _normalize_work_reference(work_urn)
                self._entries.append(
                    WorkEntry(
                        author_id=author_id,
                        author_urn=work_urn,
                        author_name=author_name or author_id,
                        work_urn=work_urn,
                        work_title=work_title or work_ref,
                        language=language or "lat",
                        namespace=namespace or "legacy",
                        work_reference=work_ref,
                        source_path=Path(source_path),
                    )
                )

    def _build_duckdb(self) -> None:
        logger.info("Writing CTS index to %s", self.output_path)
        self._connection = duckdb.connect(str(self.output_path))
        self._connection.execute("INSTALL 'json';")
        self._connection.execute("LOAD 'json';")
        self._create_tables_duckdb()
        self._batch_insert_duckdb()
        self._create_indexes_duckdb()
        self._connection.execute(
            "INSERT INTO indexer_config (key, value) VALUES "
            "('format', 'duckdb'), ('build_date', CURRENT_TIMESTAMP), ('entry_count', ?)",
            [len(self._entries)],
        )

    def _create_tables_duckdb(self) -> None:
        if not self._connection:
            return
        self._connection.execute(
            "CREATE TABLE author_index (author_id TEXT PRIMARY KEY, author_name TEXT NOT NULL, "
            "language TEXT, namespace TEXT, author_urn TEXT)"
        )
        self._connection.execute(
            "CREATE TABLE works (work_urn TEXT PRIMARY KEY, canon_id TEXT, author_id TEXT, "
            "work_title TEXT, work_reference TEXT, cts_urn TEXT, language TEXT, namespace TEXT, "
            "source_path TEXT, FOREIGN KEY (author_id) REFERENCES author_index(author_id))"
        )
        self._connection.execute(
            "CREATE TABLE editions (edition_urn TEXT PRIMARY KEY, work_urn TEXT, label TEXT, "
            "description TEXT, language TEXT, source_path TEXT, "
            "FOREIGN KEY (work_urn) REFERENCES works(work_urn))"
        )
        self._connection.execute("CREATE TABLE indexer_config (key TEXT PRIMARY KEY, value TEXT)")

    def _batch_insert_duckdb(self) -> None:
        if not self._connection:
            return
        logger.info("Inserting CTS data...")

        seen_authors = set()
        author_data = []
        for e in self._entries:
            if e.author_id and e.author_id not in seen_authors:
                author_data.append(
                    (e.author_id, e.author_name, e.language, e.namespace, e.author_urn)
                )
                seen_authors.add(e.author_id)

        if author_data:
            self._connection.executemany(
                "INSERT INTO author_index VALUES (?, ?, ?, ?, ?)", author_data
            )

        work_data = [
            (
                e.work_urn,
                _normalize_work_reference(e.work_urn),
                e.author_id,
                e.work_title,
                e.work_reference,
                e.work_urn,  # cts_urn (compat with mapper)
                e.language,
                e.namespace,
                str(e.source_path),
            )
            for e in self._entries
        ]
        if work_data:
            self._connection.executemany(
                "INSERT INTO works VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", work_data
            )

        edition_data = [
            (
                ed.edition_urn,
                ed.work_urn,
                ed.label,
                ed.description,
                ed.language,
                str(ed.source_path),
            )
            for ed in self._editions
            if ed.edition_urn
        ]
        if edition_data:
            self._connection.executemany(
                "INSERT INTO editions VALUES (?, ?, ?, ?, ?, ?)", edition_data
            )

        logger.info(
            "Inserted %s authors, %s works, %s editions",
            len(seen_authors),
            len(self._entries),
            len(edition_data),
        )

    def _create_indexes_duckdb(self) -> None:
        if not self._connection:
            return
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id); "
            "CREATE INDEX IF NOT EXISTS idx_works_reference ON works(work_reference); "
            "CREATE INDEX IF NOT EXISTS idx_works_title ON works(work_title); "
            "CREATE INDEX IF NOT EXISTS idx_works_urn ON works(cts_urn); "
            "CREATE INDEX IF NOT EXISTS idx_editions_work ON editions(work_urn);"
        )

    def validate(self) -> bool:
        logger.info("Validating CTS URN index at %s", self.output_path)
        if not self.output_path.exists():
            logger.error("CTS index file does not exist")
            return False
        try:
            return self._validate_duckdb()
        except Exception as exc:  # noqa: BLE001
            logger.error("Validation error: %s", exc)
            return False

    def _validate_duckdb(self) -> bool:
        if not self._connection:
            self._connection = duckdb.connect(str(self.output_path))
        result = self._connection.execute("SELECT COUNT(*) FROM author_index").fetchone()
        author_count = result[0] if result else 0
        result = self._connection.execute("SELECT COUNT(*) FROM works").fetchone()
        work_count = result[0] if result else 0
        if author_count == 0 or work_count == 0:
            logger.error("Empty CTS database: %s authors, %s works", author_count, work_count)
            return False
        return True

    def get_stats(self) -> dict[str, object]:
        stats: dict[str, object] = {
            "type": "cts_urn",
            "format": "duckdb",
            "path": str(self.output_path),
        }
        if self.output_path.exists():
            stats["size_mb"] = round(self.output_path.stat().st_size / (1024 * 1024), 3)
        if self.output_path.exists():
            if not self._connection:
                self._connection = duckdb.connect(str(self.output_path))
            result = self._connection.execute("SELECT COUNT(*) FROM author_index").fetchone()
            stats["author_count"] = result[0] if result else 0
            result = self._connection.execute("SELECT COUNT(*) FROM works").fetchone()
            stats["work_count"] = result[0] if result else 0
            result = self._connection.execute("SELECT COUNT(*) FROM editions").fetchone()
            stats["edition_count"] = result[0] if result else 0
            perseus_result = self._connection.execute(
                "SELECT COUNT(*) FROM works WHERE source_path LIKE '%perseus%'"
            ).fetchone()
            stats["perseus_count"] = perseus_result[0] if perseus_result else 0
            legacy_result = self._connection.execute(
                "SELECT COUNT(*) FROM works WHERE source_path LIKE '%Classics-Data%'"
            ).fetchone()
            stats["legacy_count"] = legacy_result[0] if legacy_result else 0
        return stats

    def cleanup(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
