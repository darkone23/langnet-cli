from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, replace
from itertools import islice
from pathlib import Path

import duckdb
from returns.result import Failure, Success

from langnet.execution.handlers.gaffiot import normalize_gaffiot_headword

from .base import BuildErrorStats, BuildResult, BuildStatus, LexiconStats
from .paths import default_whitakers_path, project_root

logger = logging.getLogger(__name__)

LEX_ID = "WHITAKERS_WORDS_LAT"
STEM_WIDTH = 19
STEM_FIELD_COUNT = 4
STEM_BLOCK_WIDTH = STEM_WIDTH * STEM_FIELD_COUNT
POS_START = STEM_BLOCK_WIDTH
POS_END = 83
CODES_END = 110
NOUN_GENDER_INDEX = 2
DEFAULT_SOURCE = project_root().parent / "whitakers-words" / "DICTLINE.GEN"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    entry_id BIGINT PRIMARY KEY,
    headword_raw VARCHAR NOT NULL,
    headword_norm VARCHAR NOT NULL,
    source_stem VARCHAR NOT NULL,
    pos VARCHAR,
    codes VARCHAR,
    plain_text TEXT
);

CREATE INDEX IF NOT EXISTS whitakers_entries_headword_norm_idx ON entries(headword_norm);
CREATE INDEX IF NOT EXISTS whitakers_entries_headword_entry_idx
    ON entries(headword_norm, entry_id);
CREATE INDEX IF NOT EXISTS whitakers_entries_source_stem_idx ON entries(source_stem);
"""


@dataclass
class WhitakersBuildConfig:
    """
    Configuration for building a local Whitaker's Words Latin word index.
    """

    source_path: Path | None = None
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 5000
    wipe_existing: bool = True
    force_rebuild: bool = False


@dataclass(frozen=True)
class _WhitakersEntry:
    entry_id: int
    headword_raw: str
    headword_norm: str
    source_stem: str
    pos: str
    codes: str
    plain_text: str


class WhitakersBuilder:
    """
    Build a browseable Latin word index from Whitaker's generated DICTLINE.GEN.
    """

    def __init__(self, config: WhitakersBuildConfig) -> None:
        self.source_path = (config.source_path or DEFAULT_SOURCE).expanduser()
        self.output_path = config.output_path or default_whitakers_path()
        self.limit = config.limit
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[LexiconStats | BuildErrorStats]:
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(f"Whitaker's DICTLINE.GEN not found at {self.source_path}")
            if self.output_path.exists():
                if self.wipe_existing:
                    logger.info("Deleting existing Whitaker index at %s", self.output_path)
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    logger.info("Whitaker index already exists; skipping rebuild")
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.output_path))
            for stmt in SCHEMA_SQL.strip().split(";"):
                sql_stmt = stmt.strip()
                if sql_stmt:
                    self._conn.execute(sql_stmt)

            processed = self._load_entries()
            stats = replace(
                self.get_stats(),
                entry_count=processed,
                headword_count=processed,
            )
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(stats),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to build Whitaker index: %s", exc)
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
        start_time = time.perf_counter()
        total = 0
        batch: list[tuple[object, ...]] = []
        for entry in islice(self._iter_entries(), self.limit):
            batch.append(
                (
                    entry.entry_id,
                    entry.headword_raw,
                    entry.headword_norm,
                    entry.source_stem,
                    entry.pos,
                    entry.codes,
                    entry.plain_text,
                )
            )
            if len(batch) >= self.batch_size:
                total += len(batch)
                self._flush_entries(batch)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.info(
                    "Inserted Whitaker batch: %s entries (total=%s, elapsed_ms=%s)",
                    len(batch),
                    total,
                    elapsed_ms,
                )
                batch.clear()
        if batch:
            total += len(batch)
            self._flush_entries(batch)
        return total

    def _iter_entries(self):
        with self.source_path.open(encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                entry = _parse_dictline(line_number, line.rstrip("\n\r"))
                if entry is not None:
                    yield entry

    def _flush_entries(self, batch: list[tuple[object, ...]]) -> None:
        assert self._conn is not None
        self._conn.executemany("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)", batch)

    def get_stats(self) -> LexiconStats:
        count = 0
        if self._conn is not None:
            row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
            count = int(row[0]) if row else 0
        elif self.output_path.exists():
            try:
                with duckdb.connect(str(self.output_path), read_only=True) as conn:
                    row = conn.execute("SELECT COUNT(*) FROM entries").fetchone()
                    count = int(row[0]) if row else 0
            except Exception:  # noqa: BLE001
                count = 0
        size_mb = (
            round(self.output_path.stat().st_size / (1024 * 1024), 2)
            if self.output_path.exists()
            else None
        )
        return LexiconStats(
            lex_id=LEX_ID,
            path=str(self.output_path),
            entry_count=count,
            headword_count=count,
            size_mb=size_mb,
        )

    def cleanup(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def _parse_dictline(line_number: int, line: str) -> _WhitakersEntry | None:
    if not line.strip() or len(line) < POS_START:
        return None
    stems = [
        line[index : index + STEM_WIDTH].strip() for index in range(0, STEM_BLOCK_WIDTH, STEM_WIDTH)
    ]
    source_stem = _first_real_stem(stems)
    if not source_stem:
        return None
    pos = line[POS_START:POS_END].strip().split(" ", 1)[0]
    codes = line[POS_END:CODES_END].strip()
    plain_text = line[CODES_END:].strip()
    headword_raw = _derive_headword(stems, pos, codes)
    headword_norm = normalize_gaffiot_headword(headword_raw)
    if not headword_norm:
        return None
    return _WhitakersEntry(
        entry_id=line_number,
        headword_raw=headword_raw,
        headword_norm=headword_norm,
        source_stem=source_stem,
        pos=pos,
        codes=codes,
        plain_text=plain_text,
    )


def _first_real_stem(stems: list[str]) -> str:
    for stem in stems:
        if stem and stem.lower() != "zzz":
            return stem
    return ""


def _derive_headword(stems: list[str], pos: str, codes: str) -> str:
    stem = _first_real_stem(stems)
    code_parts = codes.split()
    if pos == "N":
        return _derive_noun_headword(stem, code_parts)
    if pos == "V":
        return _derive_verb_headword(stem, code_parts)
    if pos == "ADJ":
        return _derive_adjective_headword(stem, code_parts)
    return stem


def _derive_noun_headword(stem: str, code_parts: list[str]) -> str:
    declension = code_parts[0] if code_parts else ""
    gender = code_parts[NOUN_GENDER_INDEX] if len(code_parts) > NOUN_GENDER_INDEX else ""
    headword = stem
    if declension == "1" and not stem.endswith("a"):
        headword = f"{stem}a"
    elif declension == "2":
        if gender == "N" and not stem.endswith(("um", "on")):
            headword = f"{stem}um"
        elif not stem.endswith(("us", "er", "ir", "os", "um", "on")):
            headword = f"{stem}us"
    elif declension == "4":
        if gender == "N" and not stem.endswith("u"):
            headword = f"{stem}u"
        elif not stem.endswith("us"):
            headword = f"{stem}us"
    elif declension == "5" and not re.search(r"(es|ies)$", stem):
        headword = f"{stem}es"
    return headword


def _derive_verb_headword(stem: str, code_parts: list[str]) -> str:
    conjugation = code_parts[0] if code_parts else ""
    if stem.endswith(("o", "or")):
        return stem
    if conjugation == "2":
        return f"{stem}eo"
    if conjugation == "4":
        return f"{stem}io"
    return f"{stem}o"


def _derive_adjective_headword(stem: str, code_parts: list[str]) -> str:
    declension = code_parts[0] if code_parts else ""
    if declension == "1" and not stem.endswith(("us", "a", "um", "er")):
        return f"{stem}us"
    return stem
