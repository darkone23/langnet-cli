from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, replace
from decimal import Decimal
from itertools import islice
from pathlib import Path

import duckdb
import time
from bs4 import BeautifulSoup
from returns.result import Failure, Success

from .base import BuildErrorStats, BuildResult, BuildStatus, CdslStats
from .paths import default_cdsl_path

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    dict_id VARCHAR NOT NULL,
    key VARCHAR NOT NULL,
    key_normalized VARCHAR NOT NULL,
    key2 VARCHAR,
    key2_normalized VARCHAR,
    lnum DOUBLE NOT NULL,
    hom INTEGER,
    h_type VARCHAR,
    data TEXT NOT NULL,
    body TEXT,
    plain_text TEXT,
    page_ref VARCHAR,
    PRIMARY KEY (dict_id, lnum)
);

CREATE TABLE IF NOT EXISTS headwords (
    dict_id VARCHAR NOT NULL,
    key VARCHAR NOT NULL,
    key_normalized VARCHAR NOT NULL,
    lnum DOUBLE NOT NULL,
    hom INTEGER,
    is_primary BOOLEAN NOT NULL DEFAULT true,
    search_key VARCHAR,
    PRIMARY KEY (dict_id, key_normalized, lnum, is_primary, hom),
    FOREIGN KEY (dict_id, lnum) REFERENCES entries(dict_id, lnum)
);

CREATE TABLE IF NOT EXISTS dict_metadata (
    dict_id VARCHAR PRIMARY KEY,
    title VARCHAR,
    short_title VARCHAR,
    author VARCHAR,
    publisher VARCHAR,
    pub_place VARCHAR,
    year INTEGER,
    description TEXT,
    source_url VARCHAR,
    encoding_date VARCHAR,
    license TEXT
);

CREATE TABLE IF NOT EXISTS indexer_config (key TEXT PRIMARY KEY, value TEXT);

CREATE INDEX IF NOT EXISTS idx_headwords_dict_key ON headwords(dict_id, key_normalized);
CREATE INDEX IF NOT EXISTS idx_headwords_dict_hom ON headwords(dict_id, hom);
CREATE INDEX IF NOT EXISTS idx_headwords_search_key ON headwords(dict_id, search_key);
CREATE INDEX IF NOT EXISTS idx_entries_dict_lnum ON entries(dict_id, lnum);
"""


@dataclass
class ParsedEntry:
    dict_id: str
    key: str
    key_normalized: str
    key2: str | None
    key2_normalized: str | None
    lnum: float
    hom: int | None
    h_type: str | None
    search_key: str
    data: str
    body: str | None
    plain_text: str | None
    page_ref: str | None


def _normalize_key(key: str | None) -> str:
    return key.lower().strip() if key else ""


def _search_key(key: str | None) -> str:
    """
    Build a search-friendly key: lowercase SLP1-ish string with punctuation removed.
    This helps match variants that include accent markers or sandhi separators.
    """
    if not key:
        return ""
    lowered = key.lower()
    # Strip characters commonly used for accent or separation in key2.
    for ch in ["-", "/", "'", '"', "_", "~", " "]:
        lowered = lowered.replace(ch, "")
    return lowered


def _parse_xml_entry(
    raw_data: str, dict_id: str, fallback_key: str, fallback_lnum: float
) -> ParsedEntry:
    soup = BeautifulSoup(raw_data, "lxml-xml")
    root = soup.find(True)  # first element

    h_type = root.name.upper() if root else None
    header = soup.find("h")
    tail = soup.find("tail")

    key1_tag = header.find("key1") if header else None
    key2_tag = header.find("key2") if header else None
    hom_tag = header.find("hom") if header else None

    key1 = key1_tag.text.strip() if key1_tag and key1_tag.text else fallback_key
    key2 = key2_tag.text.strip() if key2_tag and key2_tag.text else None
    hom_val = int(hom_tag.text) if hom_tag and hom_tag.text and hom_tag.text.isdigit() else None

    lnum_tag = tail.find("L") if tail else None
    lnum_str = lnum_tag.text.strip() if lnum_tag and lnum_tag.text else str(fallback_lnum)
    try:
        lnum = float(Decimal(lnum_str))
    except Exception:
        lnum = fallback_lnum

    pc_tag = tail.find("pc") if tail else None
    page_ref = pc_tag.text.strip() if pc_tag and pc_tag.text else None

    body_tag = soup.find("body")
    body_content = None
    plain_text = None
    if body_tag:
        body_content = body_tag.decode()
        plain_text = body_tag.get_text(" ", strip=True)

    normalized_key = _normalize_key(key1)
    normalized_key2 = _normalize_key(key2) if key2 else None

    # If key2 is a more informative spelling (with accents), prefer it for search.
    search_key = _search_key(key2 or key1)

    return ParsedEntry(
        dict_id=dict_id,
        key=key1,
        key_normalized=normalized_key,
        key2=key2,
        key2_normalized=normalized_key2,
        lnum=lnum,
        hom=hom_val,
        h_type=h_type,
        search_key=search_key,
        data=raw_data,
        body=body_content,
        plain_text=plain_text,
        page_ref=page_ref,
    )


def _chunked(iterable: Iterable, size: int):
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


@dataclass
class CdslBuildConfig:
    """Configuration for CdslBuilder."""

    dict_id: str
    source_dir: Path | None = None
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 1000
    wipe_existing: bool = True
    force_rebuild: bool = False


class CdslBuilder:
    """
    Build CDSL dictionary DuckDB from prebuilt CDSL SQLite files.
    """

    def __init__(self, config: CdslBuildConfig) -> None:
        self.dict_id = config.dict_id.upper()
        base_dir = (config.source_dir or (Path.home() / "cdsl_data" / "dict")).expanduser()
        self.dict_dir = base_dir / self.dict_id
        self.sqlite_path = self.dict_dir / "web" / "sqlite" / f"{self.dict_id.lower()}.sqlite"
        self.output_path = config.output_path or default_cdsl_path(self.dict_id)
        self.limit = config.limit
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[CdslStats | BuildErrorStats]:
        try:
            if not self.sqlite_path.exists():
                raise FileNotFoundError(f"CDSL SQLite not found at {self.sqlite_path}")

            if self.output_path.exists():
                if self.wipe_existing:
                    logger.info("Deleting existing CDSL index at %s", self.output_path)
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    logger.info("CDSL index already exists; skipping rebuild")
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            logger.info(
                "Building CDSL index",
                extra={
                    "dict": self.dict_id,
                    "sqlite": str(self.sqlite_path),
                    "output": str(self.output_path),
                    "batch_size": self.batch_size,
                    "limit": self.limit,
                },
            )
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.output_path))
            for stmt in SCHEMA_SQL.strip().split(";"):
                sql_stmt = stmt.strip()
                if sql_stmt:
                    self._conn.execute(sql_stmt)
            processed = self._load_entries()
            self._conn.execute(
                "INSERT INTO indexer_config (key, value) VALUES "
                "('dict_id', ?), ('build_date', CURRENT_TIMESTAMP), ('entry_count', ?)",
                [self.dict_id, processed],
            )
            stats = replace(self.get_stats(), processed=processed)
            logger.info(
                "Finished CDSL index",
                extra={
                    "dict": self.dict_id,
                    "output": str(self.output_path),
                    "processed": processed,
                    "size_mb": stats.size_mb,
                },
            )
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(stats),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to build CDSL index for %s: %s", self.dict_id, exc)
            return BuildResult(
                status=BuildStatus.FAILED,
                output_path=self.output_path,
                stats=Failure(BuildErrorStats(error=str(exc))),
                message=str(exc),
            )
        finally:
            self.cleanup()

    def _load_entries(self) -> int:
        assert self._conn is not None
        sqlite_conn = sqlite3.connect(str(self.sqlite_path))
        cursor = sqlite_conn.execute(f"SELECT key, lnum, data FROM {self.dict_id}")
        total_entries = 0
        fetched = 0
        start_time = time.perf_counter()
        while True:
            rows = cursor.fetchmany(self.batch_size)
            if not rows:
                break
            if self.limit is not None and fetched >= self.limit:
                break

            entries_data = []
            headword_data = []
            for key, lnum, raw_xml in rows:
                fetched += 1
                if self.limit is not None and fetched > self.limit:
                    break
                try:
                    fallback_lnum = float(Decimal(lnum))
                except Exception:
                    fallback_lnum = 0.0

                parsed = _parse_xml_entry(raw_xml, self.dict_id, key, fallback_lnum)
                entries_data.append(
                    (
                        parsed.dict_id,
                        parsed.key,
                        parsed.key_normalized,
                        parsed.key2,
                        parsed.key2_normalized,
                        parsed.lnum,
                        parsed.hom if parsed.hom is not None else 0,
                        parsed.h_type,
                        parsed.data,
                        parsed.body,
                        parsed.plain_text,
                        parsed.page_ref,
                    )
                )
                headword_data.append(
                    (
                        parsed.dict_id,
                        parsed.key,
                        parsed.key_normalized,
                        parsed.lnum,
                        parsed.hom if parsed.hom is not None else 0,
                        True,
                        parsed.search_key,
                    )
                )
                if parsed.key2:
                    headword_data.append(
                        (
                            parsed.dict_id,
                            parsed.key2,
                            parsed.key2_normalized or parsed.key2.lower(),
                            parsed.lnum,
                            parsed.hom if parsed.hom is not None else 0,
                            False,
                            _search_key(parsed.key2),
                        )
                    )

            if entries_data:
                self._conn.executemany(
                    "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", entries_data
                )
            if headword_data:
                self._conn.executemany(
                    "INSERT INTO headwords VALUES (?, ?, ?, ?, ?, ?, ?)", headword_data
                )
            total_entries += len(entries_data)
            logger.info(
                "Inserted batch for %s: %s entries (total %s, elapsed_ms=%s)",
                self.dict_id,
                len(entries_data),
                total_entries,
                round((time.perf_counter() - start_time) * 1000, 2),
            )
        sqlite_conn.close()
        return total_entries

    def get_stats(self) -> CdslStats:
        size_mb = None
        entry_count = headword_count = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 3)
        conn = duckdb.connect(str(self.output_path))
        try:
            result = conn.execute("SELECT COUNT(*) FROM entries").fetchone()
            entry_count = result[0] if result else 0
            result = conn.execute("SELECT COUNT(*) FROM headwords").fetchone()
            headword_count = result[0] if result else 0
        finally:
            conn.close()
        return CdslStats(
            dict_id=self.dict_id,
            path=str(self.output_path),
            entry_count=entry_count,
            headword_count=headword_count,
            size_mb=size_mb,
        )

    def cleanup(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
