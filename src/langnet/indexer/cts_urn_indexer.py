"""
CTS URN Indexer for classical text reference resolution.
"""

import duckdb
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging

from .core import IndexerBase, IndexStatus

logger = logging.getLogger(__name__)


def _clean_author_name(raw_name: str) -> str:
    """Clean raw author name by removing &1 prefix and & Topic suffix."""
    if not raw_name:
        return raw_name

    # Remove &1 prefix
    if raw_name.startswith("&1"):
        raw_name = raw_name[2:]

    # Remove & suffix and everything after it
    if "&" in raw_name:
        raw_name = raw_name.split("&")[0]

    # Clean up whitespace and special characters
    raw_name = raw_name.strip()

    return raw_name


def _clean_work_title(raw_title: str) -> str:
    """Clean raw work title by removing unwanted characters."""
    if not raw_title:
        return raw_title

    # Remove any trailing special characters that might be in the binary format
    raw_title = raw_title.strip()

    return raw_title


@dataclass
class AuthorWorkEntry:
    author_id: str
    author_name: str
    work_title: str
    work_reference: str
    cts_urn: str
    language: str = "lat"
    namespace: str = field(default_factory=lambda: "latinLit")


class CtsUrnIndexer(IndexerBase):
    def __init__(self, output_path: Path, config: Optional[Dict[str, Any]] = None):
        super().__init__(output_path, config)
        self.source_dir = (
            Path(config.get("source_dir", "/home/nixos/Classics-Data"))
            if config
            else Path("/home/nixos/Classics-Data")
        )
        self.force_rebuild = config.get("force_rebuild", False) if config else False
        self.batch_size = config.get("batch_size", 1000) if config else 1000
        self._entries: List[AuthorWorkEntry] = []
        self._connection: Optional[duckdb.DuckDBPyConnection] = None

    def build(self) -> bool:
        try:
            self.update_status(IndexStatus.BUILDING)
            if self.is_built() and not self.force_rebuild:
                logger.info("CTS URN index already exists, skipping build")
                self.update_status(IndexStatus.BUILT)
                return True
            logger.info(f"Building CTS URN index from {self.source_dir}")
            self._parse_source_data()
            self._build_duckdb()
            if self.validate():
                self.update_status(IndexStatus.BUILT)
                self._log_stats()
                return True
            else:
                self.update_status(IndexStatus.ERROR)
                return False
        except Exception as e:
            logger.error(f"Failed to build CTS URN index: {e}")
            self.update_status(IndexStatus.ERROR)
            return False

    def _parse_source_data(self) -> None:
        logger.info("Parsing source data using filename-based approach...")

        self._entries = []

        tlg_dir = self.source_dir / "tlg_e"
        phi_dir = self.source_dir / "phi-latin"

        if tlg_dir.exists():
            tlg_works = self._scan_idt_directory(tlg_dir, is_greek=True)
            self._entries.extend(tlg_works)
            logger.info(f"Processed {len(tlg_works)} TLG works")

        if phi_dir.exists():
            phi_works = self._scan_idt_directory(phi_dir, is_greek=False)
            self._entries.extend(phi_works)
            logger.info(f"Processed {len(phi_works)} PHI works")

        if not self._entries:
            raise FileNotFoundError(f"No .idt files found in {self.source_dir}")

        logger.info(f"Parsed {len(self._entries)} author-work entries total")

    def _scan_idt_directory(self, data_dir: Path, is_greek: bool) -> List[AuthorWorkEntry]:
        """Scan directory for .idt files and parse them."""
        works: List[AuthorWorkEntry] = []

        for idt_path in sorted(data_dir.glob("*.idt")):
            try:
                stem = idt_path.stem

                if stem.startswith("doccan"):
                    continue

                if stem.startswith("civ"):
                    prefix = "civ"
                    num_match = re.search(r"civ(\d+)", stem)
                elif stem.startswith("cop"):
                    prefix = "cop"
                    num_match = re.search(r"cop(\d+)", stem)
                else:
                    prefix = "lat" if not is_greek else "tlg"
                    num_match = re.search(r"(\d+)", stem)

                if not num_match:
                    continue

                num = num_match.group(1)
                author_id = f"{prefix}{int(num):04d}"

                author_name, work_titles = self._extract_work_title_from_idt(idt_path)

                if not work_titles:
                    work_titles = [stem]

                namespace = "greekLit" if is_greek else "latinLit"
                language = "grc" if is_greek else "lat"

                for work_idx, title in enumerate(work_titles, start=1):
                    work_num = f"{prefix}{work_idx:03d}"
                    cts_urn = f"urn:cts:{namespace}:{author_id}.{work_num}"

                    entry = AuthorWorkEntry(
                        author_id=author_id,
                        author_name=author_name,
                        work_title=title,
                        work_reference=f"{author_id}_{work_idx}",
                        cts_urn=cts_urn,
                        language=language,
                        namespace=namespace,
                    )
                    works.append(entry)

            except Exception as exc:
                logger.error(f"Failed to parse {idt_path}: {exc}")
                continue

        return works

    def _parse_auth_file(self, auth_file: Path) -> Dict[str, Any]:
        authors = {}
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
                prefix = "lat"
            else:
                logger.error(f"Unknown data format in {auth_file}")
                return authors
            matches = re.findall(pattern, data)
            for num, name, topic in matches:
                author_id = f"{prefix}{num.decode('ascii')}"
                name = name.decode("latin-1").strip()
                topic = topic.decode("latin-1").strip()
                # Clean the author name
                clean_name = _clean_author_name(name)
                authors[author_id] = {
                    "name": clean_name,
                    "language": language,
                    "namespace": namespace,
                    "topic": topic,
                    "tlg_number": num.decode("ascii"),
                }
        except Exception as e:
            logger.error(f"Error parsing auth file: {e}")
        logger.info(f"Parsed {len(authors)} authors from {auth_file}")
        return authors

    def _parse_idt_files(self, auth_file: Path, authors: Dict[str, Any]) -> List[Dict[str, Any]]:
        works: List[Dict[str, Any]] = []
        data_dir = auth_file.parent
        is_greek = "tlg" in str(data_dir).lower()
        for idt_path in data_dir.glob("*.idt"):
            try:
                stem = idt_path.stem
                if stem.startswith("doccan"):
                    continue
                num_match = re.search(r"(\d+)", stem)
                if not num_match:
                    continue
                num = num_match.group(1)

                prefix = "tlg" if is_greek else "lat"
                author_id = f"{prefix}{num}"

                if author_id not in authors:
                    for aid in authors:
                        if aid.endswith(num):
                            author_id = aid
                            break
                    else:
                        continue
                author = authors[author_id]
                author_name, work_titles = self._extract_work_title_from_idt(idt_path)

                if len(work_titles) == 0:
                    continue

                prefix = "tlg" if is_greek else "lat"
                for work_idx, title in enumerate(work_titles, start=1):
                    work_num_str = f"{prefix}{work_idx:03d}"
                    cts_urn = f"urn:cts:{author['namespace']}:{author_id}.{work_num_str}"
                    works.append(
                        {
                            "canon_id": f"{prefix}{num}_{work_idx}",
                            "author_id": author_id,
                            "author_name": author_name,
                            "title": title,
                            "reference": f"{prefix}{num}_{work_idx}",
                            "cts_urn": cts_urn,
                        }
                    )
            except Exception as exc:
                logger.error(f"Failed to parse {idt_path}: {exc}")
                continue
        logger.info(f"Parsed {len(works)} works from .idt files")
        return works

    def _extract_work_title_from_idt(self, idt_path: Path) -> tuple[str, list[str]]:
        with open(idt_path, "rb") as f:
            data = f.read()

        author_name = ""
        work_titles = []
        i = 0

        while i < len(data):
            if i + 8 >= len(data):
                break

            if data[i] == 0x10:
                entry_type = data[i + 1] if i + 1 < len(data) else 0
                title_len = data[i + 2] if i + 2 < len(data) else 0

                if i + 3 + title_len <= len(data):
                    title_bytes = data[i + 3 : i + 3 + title_len]
                    title = title_bytes.decode("latin-1", errors="ignore").strip()
                    if title and len(title) >= 4:
                        if entry_type == 0:
                            # Clean author name from idt file
                            author_name = _clean_author_name(title)
                        elif entry_type == 1:
                            # Clean work title
                            work_titles.append(_clean_work_title(title))
                    i += 3 + title_len
                    continue

            i += 1

        if not author_name:
            author_name = idt_path.stem
        if not work_titles:
            return author_name, [idt_path.stem]

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
            "INSERT INTO indexer_config (key, value) VALUES ('format', 'duckdb'), ('build_date', CURRENT_TIMESTAMP), ('entry_count', ?)",
            [len(self._entries)],
        )
        logger.info("DuckDB index built successfully")

    def _create_tables_duckdb(self) -> None:
        if not self._connection:
            return
        self._connection.execute(
            """CREATE TABLE author_index (author_id TEXT PRIMARY KEY, author_name TEXT NOT NULL, language TEXT, namespace TEXT)"""
        )
        self._connection.execute(
            """CREATE TABLE works (canon_id TEXT, author_id TEXT, work_title TEXT, work_reference TEXT, cts_urn TEXT, FOREIGN KEY (author_id) REFERENCES author_index(author_id))"""
        )
        self._connection.execute(
            """CREATE TABLE indexer_config (key TEXT PRIMARY KEY, value TEXT)"""
        )
        self._connection.execute(
            """CREATE INDEX idx_works_author ON works(author_id); CREATE INDEX idx_works_reference ON works(work_reference); CREATE INDEX idx_works_title ON works(work_title); CREATE INDEX idx_works_urn ON works(cts_urn);"""
        )

    def _batch_insert_duckdb(self) -> None:
        if not self._connection:
            return
        logger.info("Inserting data in batches...")

        # Deduplicate author data by author_id
        seen_authors = set()
        author_data = []
        for e in self._entries:
            if e.author_id not in seen_authors:
                author_data.append((e.author_id, e.author_name, e.language, e.namespace))
                seen_authors.add(e.author_id)

        if author_data:
            self._connection.executemany(
                "INSERT INTO author_index VALUES (?, ?, ?, ?)", author_data
            )

        work_data = [
            (e.author_id, e.author_id, e.work_title, e.work_reference, e.cts_urn)
            for e in self._entries
        ]
        if work_data:
            self._connection.executemany("INSERT INTO works VALUES (?, ?, ?, ?, ?)", work_data)
        logger.info(f"Inserted {len(seen_authors)} authors, {len(self._entries)} work entries")

    def _create_indexes_duckdb(self) -> None:
        pass

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

    def get_stats(self) -> Dict[str, Any]:
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
        logger.info(
            f"CTS URN Index Stats: Authors={stats.get('author_count')}, Works={stats.get('work_count')}, Size={stats['size_mb']:.2f} MB"
        )

    def cleanup(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def query_abbreviation(self, abbrev: str, language: str = "lat") -> List[str]:
        if not self.is_built():
            return []
        try:
            if not self._connection:
                self._connection = duckdb.connect(str(self.output_path))
            # Prioritize author name matches, then work title matches
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
