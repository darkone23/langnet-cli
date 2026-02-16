"""
CTS URN Indexer built from the Perseus CTS corpora (Latin + Greek).
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
from langnet.types import JSONMapping

from .core import IndexerBase, IndexStatus

logger = logging.getLogger(__name__)

CTS_NS = "http://chs.harvard.edu/xmlns/cts"
TI = {"ti": CTS_NS}
ENTRY_TYPE_MARKER = 0x10
MIN_TITLE_LENGTH = 4


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


class CtsUrnIndexer(IndexerBase):
    def __init__(self, output_path: Path, config: JSONMapping | None = None):
        super().__init__(output_path, config)
        config = config or {}
        perseus_value = config.get("perseus_dir") or config.get("source_dir")
        if isinstance(perseus_value, (str, Path)):
            self.perseus_dir = Path(perseus_value).expanduser()
        else:
            self.perseus_dir = Path.home() / "perseus"

        legacy_value = config.get("legacy_dir") if config else None
        if isinstance(legacy_value, (str, Path)):
            self.legacy_dir = Path(legacy_value)
        else:
            self.legacy_dir = Path.home() / "langnet-tools" / "diogenes" / "Classics-Data"
        self.force_rebuild = config.get("force_rebuild", False)
        self.wipe_existing = config.get("wipe_existing", True)
        self.include_legacy = config.get("include_legacy", True)
        self.batch_size = config.get("batch_size", 1000)
        self._entries: list[WorkEntry] = []
        self._editions: list[EditionEntry] = []
        self._connection: duckdb.DuckDBPyConnection | None = None

    def build(self) -> bool:
        try:
            self.update_status(IndexStatus.BUILDING)
            if self.output_path.exists() and self.wipe_existing:
                logger.info(f"Deleting existing index at {self.output_path}")
                self.output_path.unlink()

            if self.is_built() and not self.force_rebuild:
                logger.info("CTS URN index already exists, skipping build")
                self.update_status(IndexStatus.BUILT)
                return True

            logger.info(f"Building CTS URN index from Perseus at {self.perseus_dir}")
            self._parse_source_data()
            self._build_duckdb()
            if self.validate():
                self.update_status(IndexStatus.BUILT)
                self._log_stats()
                return True
            self.update_status(IndexStatus.ERROR)
            return False
        except Exception as e:
            logger.error(f"Failed to build CTS URN index: {e}")
            self.update_status(IndexStatus.ERROR)
            return False

    def _parse_source_data(self) -> None:
        self._entries = []
        self._editions = []

        latin_root = self.perseus_dir / "canonical-latinLit" / "data"
        greek_root = self.perseus_dir / "canonical-greekLit" / "data"

        if not latin_root.exists() and not greek_root.exists():
            raise FileNotFoundError(
                f"Expected Perseus corpora under {self.perseus_dir}, "
                "found neither latinLit nor greekLit"
            )

        for root, namespace, language in (
            (latin_root, "latinLit", "lat"),
            (greek_root, "greekLit", "grc"),
        ):
            if not root.exists():
                logger.warning(f"Corpus root missing: {root}")
                continue
            corpus_entries, corpus_editions = self._collect_corpus(root, namespace, language)
            self._entries.extend(corpus_entries)
            self._editions.extend(corpus_editions)
            parsed_counts = (len(corpus_entries), len(corpus_editions))
            logger.info(
                "Parsed %s works and %s editions from %s", parsed_counts[0], parsed_counts[1], root
            )

        if not self._entries:
            raise RuntimeError("No CTS works parsed from Perseus data")
        if self.include_legacy:
            self._augment_with_legacy()

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
                logger.warning(f"Failed to parse textgroup {cts_file}: {exc}")

        # Second pass: works + editions
        for cts_file in sorted(corpus_root.glob("**/__cts__.xml")):
            try:
                root = ET.parse(cts_file).getroot()
                if not root.tag.endswith("work"):
                    continue

                work_urn = root.attrib.get("urn", "")
                author_urn = root.attrib.get("groupUrn", "")
                author_id = _normalize_author_id(author_urn)
                author_info = authors.get(author_id, {})
                author_name = author_info.get("author_name") or author_id or author_urn
                work_title = _get_text(root, "title") or work_urn
                lang = (
                    root.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", language)
                    or language
                )
                work_ref = _normalize_work_reference(work_urn)

                entry = WorkEntry(
                    author_id=author_id,
                    author_urn=author_urn,
                    author_name=author_name,
                    work_urn=work_urn,
                    work_title=work_title,
                    language=lang,
                    namespace=namespace,
                    work_reference=work_ref,
                    source_path=cts_file,
                )

                for ed in root.findall("ti:edition", TI):
                    edition_urn = ed.attrib.get("urn", "")
                    edition_lang = (
                        ed.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", lang) or lang
                    )
                    label = _get_text(ed, "label")
                    description = _get_text(ed, "description")
                    edition = EditionEntry(
                        edition_urn=edition_urn,
                        work_urn=work_urn,
                        label=label,
                        description=description,
                        language=edition_lang,
                        source_path=cts_file,
                    )
                    entry.editions.append(edition)
                    editions.append(edition)

                works.append(entry)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to parse work {cts_file}: {exc}")

        return works, editions

    def _augment_with_legacy(self) -> None:
        """
        Merge legacy PHI/TLG idt data for works missing from the Perseus corpus.

        We prefer Perseus metadata, so we only add records whose CTS URNs are absent.
        """
        if not self.legacy_dir or not self.legacy_dir.exists():
            logger.info("Legacy Classics-Data path not found; skipping legacy merge")
            return

        existing = {e.work_urn for e in self._entries}
        legacy_entries = self._collect_legacy(self.legacy_dir)
        added = 0
        for entry in legacy_entries:
            if entry.work_urn in existing:
                continue
            self._entries.append(entry)
            existing.add(entry.work_urn)
            added += 1
        # Manual supplements for well-known PHI gaps (e.g., Auct. ad Herennium)
        supplements = [
            WorkEntry(
                author_id="phi0474_ps",
                author_urn="urn:cts:latinLit:phi0474",
                # Keep display aligned with canonical author to avoid pseudo labelling in UI.
                author_name="Cicero, Marcus Tullius",
                work_urn="urn:cts:latinLit:phi0474.phi073",
                work_title="Rhetorica ad Herennium",
                language="lat",
                namespace="latinLit",
                work_reference="phi0474_073",
                source_path=Path("supplemental"),
            )
        ]
        for entry in supplements:
            if entry.work_urn not in existing:
                self._entries.append(entry)
                existing.add(entry.work_urn)
                added += 1

        if added:
            logger.info(f"Added {added} legacy works from {self.legacy_dir}")

    def _collect_legacy(self, legacy_root: Path) -> list[WorkEntry]:
        """Parse legacy authtab/idt data from Classics-Data (phi-latin / tlg_e)."""
        works: list[WorkEntry] = []
        for data_dir, is_greek in (
            (legacy_root / "phi-latin", False),
            (legacy_root / "tlg_e", True),
        ):
            if not data_dir.exists():
                continue
            auth_file = data_dir / "authtab.dir"
            authors = self._parse_auth_file(auth_file) if auth_file.exists() else {}
            works.extend(self._parse_idt_files(data_dir, authors, is_greek))
        return works

    def _parse_auth_file(self, auth_file: Path) -> dict[str, dict[str, str]]:
        authors: dict[str, dict[str, str]] = {}
        try:
            with open(auth_file, "rb") as f:
                data = f.read()
            if b"*TLG" in data:
                pattern = rb"TLG(\d{4}) &1([^&]+?) &([^\xff]+)\xff"
                language = "grc"
                namespace = "greekLit"
                prefix = "tlg"
            elif b"*LAT" in data:
                pattern = rb"LAT(\d{4}) &1([^&]+?)&([^\xff]+)\xff"
                language = "lat"
                namespace = "latinLit"
                prefix = "phi"  # normalize to phi for CTS lookups
            else:
                logger.error(f"Unknown data format in {auth_file}")
                return authors
            matches = re.findall(pattern, data)
            for num, raw_name, raw_topic in matches:
                author_id = f"{prefix}{num.decode('ascii')}"
                name = raw_name.decode("latin-1").strip()
                topic = raw_topic.decode("latin-1").strip()
                clean_name = _clean_author_name(name)
                authors[author_id] = {
                    "name": clean_name,
                    "language": language,
                    "namespace": namespace,
                    "topic": topic,
                    "num": num.decode("ascii"),
                }
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error parsing auth file: {e}")
        logger.info(f"Parsed {len(authors)} authors from {auth_file}")
        return authors

    def _parse_idt_files(
        self, data_dir: Path, authors: dict[str, dict[str, str]], is_greek: bool
    ) -> list[WorkEntry]:
        works: list[WorkEntry] = []
        for idt_path in data_dir.glob("*.idt"):
            works.extend(self._parse_single_idt(idt_path, authors, is_greek))
        logger.info(f"Parsed {len(works)} legacy works from {data_dir}")
        return works

    def _parse_single_idt(
        self, idt_path: Path, authors: dict[str, dict[str, str]], is_greek: bool
    ) -> list[WorkEntry]:
        try:
            stem = idt_path.stem
            if stem.startswith("doccan"):
                return []
            num_match = re.search(r"(\d+)", stem)
            if not num_match:
                return []
            num = num_match.group(1)

            prefix = "tlg" if is_greek else "phi"
            author_id = f"{prefix}{num.zfill(4)}"
            author = self._resolve_author_metadata(authors, author_id, is_greek, stem)
            author_id = author.get("resolved_id", author_id)

            author_name, work_titles = self._extract_work_title_from_idt(idt_path)
            if not work_titles:
                return []

            works: list[WorkEntry] = []
            for work_idx, title in enumerate(work_titles, start=1):
                work_num_str = f"{prefix}{work_idx:03d}"
                cts_urn = f"urn:cts:{author['namespace']}:{author_id}.{work_num_str}"
                works.append(
                    WorkEntry(
                        author_id=author_id,
                        author_urn="",
                        author_name=author_name or author["name"],
                        work_urn=cts_urn,
                        work_title=title,
                        language=author.get("language", "lat"),
                        namespace=author.get("namespace", "latinLit"),
                        work_reference=f"{author_id}_{work_idx}",
                        source_path=idt_path,
                    )
                )
            return works
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to parse {idt_path}: {exc}")
            return []

    def _resolve_author_metadata(
        self, authors: dict[str, dict[str, str]], author_id: str, is_greek: bool, stem: str
    ) -> dict[str, str]:
        alt_ids = [author_id]
        if not is_greek:
            alt_ids.append(f"lat{author_id[3:]}")
        for aid in alt_ids:
            if aid in authors:
                author = dict(authors[aid])
                author["resolved_id"] = aid if aid.startswith(("phi", "tlg")) else author_id
                return author
        return {
            "name": stem,
            "language": "grc" if is_greek else "lat",
            "namespace": "greekLit" if is_greek else "latinLit",
            "resolved_id": author_id,
        }

    def _extract_work_title_from_idt(self, idt_path: Path) -> tuple[str, list[str]]:
        """Minimal parser for binary .idt files to recover author + work titles."""
        data = self._read_idt_file(idt_path)
        if data is None:
            return "", []

        author_name, work_titles = self._scan_idt_entries(data)
        if not author_name:
            author_name = idt_path.stem
        if not work_titles:
            return author_name, [idt_path.stem]

        return author_name, work_titles

    def _read_idt_file(self, idt_path: Path) -> bytes | None:
        try:
            with open(idt_path, "rb") as f:
                return f.read()
        except OSError as exc:
            logger.warning(f"Could not read {idt_path}: {exc}")
            return None

    def _scan_idt_entries(self, data: bytes) -> tuple[str, list[str]]:
        author_name = ""
        work_titles: list[str] = []
        i = 0

        while i < len(data):
            if i + 8 >= len(data):
                break

            if data[i] == ENTRY_TYPE_MARKER:
                entry_type = data[i + 1] if i + 1 < len(data) else 0
                title_len = data[i + 2] if i + 2 < len(data) else 0

                if i + 3 + title_len <= len(data):
                    title_bytes = data[i + 3 : i + 3 + title_len]
                    title = title_bytes.decode("latin-1", errors="ignore").strip()
                    if title and len(title) >= MIN_TITLE_LENGTH:
                        if entry_type == 0:
                            author_name = _clean_author_name(title)
                        elif entry_type == 1:
                            work_titles.append(_clean_work_title(title))
                    i += 3 + title_len
                    continue

            i += 1

        return author_name, work_titles

    def _build_duckdb(self) -> None:
        logger.info(f"Building DuckDB index at {self.output_path}")
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
        logger.info("DuckDB index built successfully")

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
        logger.info("Inserting data in batches...")

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
        logger.info("Validating CTS URN index...")
        if not self.output_path.exists():
            logger.error("Index file does not exist")
            return False
        try:
            return self._validate_duckdb()
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def _validate_duckdb(self) -> bool:
        if not self._connection:
            self._connection = duckdb.connect(str(self.output_path))
        result = self._connection.execute("SELECT COUNT(*) FROM author_index").fetchone()
        author_count = result[0] if result else 0
        result = self._connection.execute("SELECT COUNT(*) FROM works").fetchone()
        work_count = result[0] if result else 0
        if author_count == 0 or work_count == 0:
            logger.error(f"Empty database: {author_count} authors, {work_count} works")
            return False
        logger.info(f"Validation passed: {author_count} authors, {work_count} works")
        return True

    def get_stats(self) -> JSONMapping:
        stats = {
            "type": "cts_urn",
            "format": "duckdb",
            "size_mb": self.get_size_mb(),
            "built": self.is_built(),
            "status": self.status.value,
            "path": str(self.output_path),
        }
        if self.is_built():
            try:
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
                supplement_result = self._connection.execute(
                    "SELECT COUNT(*) FROM works WHERE source_path = 'supplemental'"
                ).fetchone()
                stats["supplement_count"] = supplement_result[0] if supplement_result else 0
                result = self._connection.execute(
                    "SELECT value FROM indexer_config WHERE key = 'build_date'"
                ).fetchone()
                stats["build_date"] = result[0] if result else "unknown"
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                stats["error"] = str(e)
        return stats

    def _log_stats(self) -> None:
        stats = self.get_stats()
        authors = stats.get("author_count")
        works = stats.get("work_count")
        editions = stats.get("edition_count")
        size = stats["size_mb"]
        logger.info(
            "CTS URN Index Stats: Authors=%s, Works=%s, Editions=%s, Size=%.2f MB",
            authors,
            works,
            editions,
            size,
        )

    def cleanup(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def query_abbreviation(self, abbrev: str, language: str = "lat") -> list[str]:
        if not self.is_built():
            return []
        try:
            if not self._connection:
                self._connection = duckdb.connect(str(self.output_path))
            result = self._connection.execute(
                """SELECT DISTINCT w.cts_urn, w.work_title, a.author_name,
                 CASE WHEN LOWER(a.author_name) LIKE LOWER(?) THEN 0 ELSE 1 END as match_priority
                 FROM works w
                 JOIN author_index a ON w.author_id = a.author_id
                 WHERE LOWER(a.language) = LOWER(?)
                   AND (LOWER(a.author_name) LIKE LOWER(?) OR LOWER(w.work_title) LIKE LOWER(?))
                 ORDER BY match_priority, a.author_name, w.work_title
                 LIMIT 10""",
                (f"%{abbrev}%", language, f"%{abbrev}%", f"%{abbrev}%"),
            ).fetchall()
            return [f"{row[2]}: {row[1]} -> {row[0]}" for row in result]
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []
