from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
from returns.result import Failure, Success

from langnet.normalizer.utils import strip_accents
from langnet.storage.db import connect_duckdb_ro

from .base import BuildErrorStats, BuildResult, BuildStatus, LexiconStats
from .paths import default_lewis_1890_path

LEX_ID = "LEWIS_1890_EN_LAT"
DEFAULT_SOURCE = (
    Path.home()
    / "cltk_data"
    / "lat"
    / "lexicon"
    / "cltk_lat_lewis_elementary_lexicon"
    / "lewis.yaml"
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    entry_id VARCHAR PRIMARY KEY,
    headword_raw VARCHAR NOT NULL,
    headword_norm VARCHAR NOT NULL,
    source_key VARCHAR NOT NULL,
    plain_text TEXT NOT NULL,
    entry_hash VARCHAR NOT NULL,
    source_path VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS lewis_1890_headword_norm_idx ON entries(headword_norm);
CREATE INDEX IF NOT EXISTS lewis_1890_headword_entry_idx ON entries(headword_norm, entry_id);
"""


@dataclass
class Lewis1890BuildConfig:
    """Configuration for building CLTK's Lewis 1890 Latin-English index."""

    source_path: Path | None = None
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 500
    wipe_existing: bool = True
    force_rebuild: bool = False


class Lewis1890Builder:
    """Build a local DuckDB index from CLTK's Lewis 1890 YAML source."""

    def __init__(self, config: Lewis1890BuildConfig) -> None:
        self.source_path = (config.source_path or DEFAULT_SOURCE).expanduser()
        self.output_path = config.output_path or default_lewis_1890_path()
        self.limit = config.limit
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[LexiconStats | BuildErrorStats]:
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(f"Lewis 1890 YAML not found at {self.source_path}")
            if self.output_path.exists():
                if self.wipe_existing:
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.output_path))
            apply_lewis_1890_schema(self._conn)
            processed = self._load_entries()
            stats = replace(self.get_stats(), entry_count=processed)
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(stats),
            )
        except Exception as exc:  # noqa: BLE001
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
        total = 0
        batch: list[dict[str, str]] = []
        for entry in _iter_yaml_entries(self.source_path):
            if self.limit is not None and total + len(batch) >= self.limit:
                break
            batch.append(entry)
            if len(batch) >= self.batch_size:
                total += self._insert_batch(batch)
                batch = []
        if batch:
            total += self._insert_batch(batch)
        return total

    def _insert_batch(self, entries: Sequence[Mapping[str, str]]) -> int:
        assert self._conn is not None
        rows = [_entry_row(entry, self.source_path) for entry in entries]
        table = _entry_arrow_table(rows)
        self._conn.register("lewis_1890_entry_batch", table)
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO entries (
                    entry_id,
                    headword_raw,
                    headword_norm,
                    source_key,
                    plain_text,
                    entry_hash,
                    source_path,
                    updated_at
                )
                SELECT
                    entry_id,
                    headword_raw,
                    headword_norm,
                    source_key,
                    plain_text,
                    entry_hash,
                    source_path,
                    CURRENT_TIMESTAMP
                FROM lewis_1890_entry_batch
                """
            )
        finally:
            self._conn.unregister("lewis_1890_entry_batch")
        return len(entries)

    def get_stats(self) -> LexiconStats:
        size_mb = None
        entry_count = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 3)
            conn = self._conn or duckdb.connect(str(self.output_path), read_only=True)
            try:
                result = conn.execute("SELECT COUNT(*) FROM entries").fetchone()
                entry_count = result[0] if result else 0
            finally:
                if conn is not self._conn:
                    conn.close()
        return LexiconStats(
            lex_id=LEX_ID,
            path=str(self.output_path),
            entry_count=entry_count,
            size_mb=size_mb,
        )

    def cleanup(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def apply_lewis_1890_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create Lewis 1890 dictionary tables."""
    for stmt in SCHEMA_SQL.strip().split(";"):
        sql_stmt = stmt.strip()
        if sql_stmt:
            conn.execute(sql_stmt)


def normalize_lewis_1890_headword(raw: str) -> str:
    """Normalize a Latin headword for Lewis 1890 lookup and index ordering."""
    stripped = (raw or "").strip()
    if "," in stripped:
        stripped = stripped.split(",", 1)[0]
    stripped = stripped.lstrip("0123456789. ").strip()
    expanded = stripped.replace("æ", "ae").replace("Æ", "ae").replace("œ", "oe").replace("Œ", "oe")
    normalized = strip_accents(expanded.lower())
    return "".join(ch for ch in normalized if ch.isalnum() or ch in {"_", "-"}).strip("-_")


def lookup_lewis_1890_entries(headword: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Resolve a Latin headword from the local Lewis 1890 DuckDB index."""
    return lookup_lewis_1890_entries_by_headword([headword], db_path)


def lookup_lewis_1890_entries_by_headword(
    headwords: list[str], db_path: Path | None = None
) -> list[dict[str, Any]]:
    """Resolve local Lewis 1890 entries from ordered headword candidates."""
    keys: list[str] = []
    seen: set[str] = set()
    for headword in headwords:
        key = normalize_lewis_1890_headword(headword)
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    if not keys:
        return []
    if db_path is None:
        db_path = default_lewis_1890_path()
    if not db_path.exists():
        return []

    entries_by_key: dict[str, list[dict[str, Any]]] = {}
    placeholders = ",".join(["?"] * len(keys))
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                entry_id,
                headword_raw,
                headword_norm,
                source_key,
                plain_text,
                entry_hash
            FROM entries
            WHERE headword_norm IN ({placeholders})
            ORDER BY headword_norm, entry_id
            """,
            keys,
        ).fetchall()
    for row in rows:
        entry = {
            "entry_id": row[0],
            "headword_raw": row[1],
            "headword_norm": row[2],
            "source_key": row[3],
            "plain_text": row[4],
            "entry_hash": row[5],
        }
        entries_by_key.setdefault(str(row[2]), []).append(entry)
    return [entry for key in keys for entry in entries_by_key.get(key, [])]


def _iter_yaml_entries(source_path: Path) -> Sequence[dict[str, str]]:
    try:
        import yaml  # type: ignore[import-untyped]  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PyYAML is required to read CLTK Lewis 1890 YAML source") from exc

    loaded = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise ValueError(f"Expected mapping in Lewis 1890 YAML source: {source_path}")
    entries: list[dict[str, str]] = []
    for source_key, plain_text in loaded.items():
        if source_key is None or plain_text is None:
            continue
        key = str(source_key).strip()
        text = str(plain_text).strip()
        if key and text:
            entries.append({"source_key": key, "plain_text": text})
    return entries


def _entry_row(
    entry: Mapping[str, str], source_path: Path
) -> tuple[str, str, str, str, str, str, str]:
    source_key = entry["source_key"]
    plain_text = entry["plain_text"]
    headword_raw = _headword_from_entry_text(plain_text, source_key)
    headword_norm = normalize_lewis_1890_headword(headword_raw) or normalize_lewis_1890_headword(
        source_key
    )
    entry_id = f"lewis-1890:{source_key}"
    entry_hash = hashlib.sha256(f"{source_key}\0{plain_text}".encode()).hexdigest()
    return (
        entry_id,
        headword_raw,
        headword_norm,
        source_key,
        plain_text,
        entry_hash,
        str(source_path),
    )


def _headword_from_entry_text(plain_text: str, source_key: str) -> str:
    stripped = plain_text.strip()
    if not stripped:
        return source_key
    token = stripped.split(None, 1)[0].strip(" ,;:.()[]")
    return token or source_key


def _entry_arrow_table(rows: Sequence[tuple[str, str, str, str, str, str, str]]) -> pa.Table:
    return pa.table(
        {
            "entry_id": [row[0] for row in rows],
            "headword_raw": [row[1] for row in rows],
            "headword_norm": [row[2] for row in rows],
            "source_key": [row[3] for row in rows],
            "plain_text": [row[4] for row in rows],
            "entry_hash": [row[5] for row in rows],
            "source_path": [row[6] for row in rows],
        }
    )
