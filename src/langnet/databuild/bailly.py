from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

import duckdb
import pyarrow as pa
from returns.result import Failure, Success

from langnet.normalizer.utils import normalize_greekish_token
from langnet.parsing.bailly_text import repair_bailly_line_break_hyphenation
from langnet.storage.db import connect_duckdb_ro

from .base import BuildErrorStats, BuildResult, BuildStatus, LexiconStats
from .paths import default_bailly_path

LEX_ID = "BAILLY_FR_GRC"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    entry_id VARCHAR PRIMARY KEY,
    lemma VARCHAR NOT NULL,
    lemma_norm VARCHAR NOT NULL,
    source_kind VARCHAR NOT NULL,
    source_path VARCHAR,
    page_start INTEGER,
    page_end INTEGER,
    raw_text TEXT,
    block_count INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entry_blocks (
    entry_id VARCHAR NOT NULL,
    path VARCHAR NOT NULL,
    marker VARCHAR NOT NULL,
    text TEXT NOT NULL,
    layout_json TEXT,
    ordinal INTEGER NOT NULL,
    PRIMARY KEY (entry_id, path)
);

CREATE INDEX IF NOT EXISTS entries_lemma_norm_idx ON entries(lemma_norm);
CREATE INDEX IF NOT EXISTS entry_blocks_entry_path_idx ON entry_blocks(entry_id, path);
"""


@dataclass
class BaillyBuildConfig:
    """Configuration for building Bailly's PDF-derived structured index."""

    source_path: Path
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 500
    wipe_existing: bool = True
    force_rebuild: bool = False


class BaillyBuilder:
    """Build a Bailly Greek→French index from PDF-derived structural JSONL."""

    def __init__(self, config: BaillyBuildConfig) -> None:
        self.source_path = config.source_path.expanduser()
        self.output_path = config.output_path or default_bailly_path()
        self.limit = config.limit
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[LexiconStats | BuildErrorStats]:
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(
                    f"Bailly PDF structural JSONL not found at {self.source_path}"
                )
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
            apply_bailly_schema(self._conn)
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
        batch: list[Mapping[str, Any]] = []
        for entry in self._iter_jsonl_entries():
            if self.limit is not None and total + len(batch) >= self.limit:
                break
            batch.append(entry)
            if len(batch) >= self.batch_size:
                total += self._insert_batch(batch)
                batch = []
        if batch:
            total += self._insert_batch(batch)
        return total

    def _insert_batch(self, entries: Sequence[Mapping[str, Any]]) -> int:
        assert self._conn is not None
        entry_rows = [_entry_row(entry) for entry in entries]
        block_rows = [
            _block_row(str(entry["entry_id"]), block, ordinal)
            for entry in entries
            for ordinal, block in enumerate(_sequence(entry.get("blocks")))
        ]
        entry_table = _entry_arrow_table(entry_rows)
        block_table = _block_arrow_table(block_rows)
        self._conn.execute("BEGIN TRANSACTION")
        try:
            self._conn.register("bailly_entry_batch", entry_table)
            self._conn.execute(
                """
                DELETE FROM entry_blocks
                WHERE entry_id IN (SELECT entry_id FROM bailly_entry_batch)
                """
            )
            self._conn.execute(
                """
                INSERT OR REPLACE INTO entries (
                    entry_id,
                    lemma,
                    lemma_norm,
                    source_kind,
                    source_path,
                    page_start,
                    page_end,
                    raw_text,
                    block_count,
                    updated_at
                )
                SELECT
                    entry_id,
                    lemma,
                    lemma_norm,
                    source_kind,
                    source_path,
                    page_start,
                    page_end,
                    raw_text,
                    block_count,
                    CURRENT_TIMESTAMP
                FROM bailly_entry_batch
                """,
            )
            if block_rows:
                self._conn.register("bailly_block_batch", block_table)
                self._conn.execute(
                    """
                    INSERT INTO entry_blocks (
                        entry_id,
                        path,
                        marker,
                        text,
                        layout_json,
                        ordinal
                    )
                    SELECT
                        entry_id,
                        path,
                        marker,
                        text,
                        layout_json,
                        ordinal
                    FROM bailly_block_batch
                    """,
                )
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        finally:
            _unregister_quietly(self._conn, "bailly_entry_batch")
            _unregister_quietly(self._conn, "bailly_block_batch")
        self._conn.execute("COMMIT")
        return len(entries)

    def _iter_jsonl_entries(self) -> Iterator[Mapping[str, Any]]:
        with self.source_path.open(encoding="utf-8") as source:
            for line_num, line in enumerate(source, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                loaded = json.loads(stripped)
                if not isinstance(loaded, Mapping):
                    raise ValueError(f"Expected object on JSONL line {line_num}")
                yield loaded

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


def apply_bailly_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the Bailly structured dictionary tables."""
    for stmt in SCHEMA_SQL.strip().split(";"):
        sql_stmt = stmt.strip()
        if sql_stmt:
            conn.execute(sql_stmt)


def insert_pdf_structural_entry(
    conn: duckdb.DuckDBPyConnection,
    entry: Mapping[str, Any],
) -> None:
    """Insert one PDF-derived Bailly structural entry.

    The input is expected to be downstream of PDF layout extraction. Bailly.app scrape data
    should be used for verification fixtures, not as the source of database rows.
    """
    source = _mapping(entry.get("source"))
    blocks = list(_sequence(entry.get("blocks")))
    entry_id = str(entry["entry_id"])
    conn.execute(
        """
        INSERT OR REPLACE INTO entries (
            entry_id,
            lemma,
            lemma_norm,
            source_kind,
            source_path,
            page_start,
            page_end,
            raw_text,
            block_count,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        [
            entry_id,
            str(entry["lemma"]),
            str(entry["lemma_norm"]),
            str(source.get("kind") or "pdf"),
            str(source.get("path") or ""),
            _optional_int(source.get("page_start")),
            _optional_int(source.get("page_end")),
            repair_bailly_line_break_hyphenation(str(entry.get("raw_text") or "")),
            len(blocks),
        ],
    )
    conn.execute("DELETE FROM entry_blocks WHERE entry_id = ?", [entry_id])
    if blocks:
        conn.executemany(
            """
            INSERT INTO entry_blocks (
                entry_id,
                path,
                marker,
                text,
                layout_json,
                ordinal
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [_block_row(entry_id, block, ordinal) for ordinal, block in enumerate(blocks)],
        )


def lookup_bailly_entries(
    headword: str,
    db_path: Path | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Resolve Bailly entries from the local PDF-derived DuckDB index."""
    db_path = db_path or default_bailly_path()
    if not db_path.exists():
        return []
    keys = _lookup_keys(headword)
    if not keys:
        return []
    placeholders = ",".join(["?"] * len(keys))
    with connect_duckdb_ro(db_path) as conn:
        entry_rows = conn.execute(
            f"""
            SELECT
                entry_id,
                lemma,
                lemma_norm,
                source_kind,
                source_path,
                page_start,
                page_end,
                raw_text,
                block_count
            FROM entries
            WHERE lemma IN ({placeholders})
               OR lemma_norm IN ({placeholders})
               OR replace(replace(lemma, '·', ''), '·', '') IN ({placeholders})
               OR replace(lemma_norm, '_', '') IN ({placeholders})
            ORDER BY page_start NULLS LAST, entry_id
            """,
            [*keys, *keys, *keys, *keys],
        ).fetchall()
        if not entry_rows:
            return []
        entry_rows = sorted(entry_rows, key=lambda row: _lookup_rank(row, keys))[:limit]
        entry_ids = [row[0] for row in entry_rows]
        block_placeholders = ",".join(["?"] * len(entry_ids))
        block_rows = conn.execute(
            f"""
            SELECT entry_id, path, marker, text, layout_json, ordinal
            FROM entry_blocks
            WHERE entry_id IN ({block_placeholders})
            ORDER BY entry_id, ordinal
            """,
            entry_ids,
        ).fetchall()
    blocks_by_entry: dict[str, list[dict[str, Any]]] = {}
    for row in block_rows:
        blocks_by_entry.setdefault(row[0], []).append(
            {
                "path": row[1],
                "marker": row[2],
                "text": row[3],
                "layout": json.loads(row[4]) if row[4] else {},
                "ordinal": row[5],
            }
        )
    return [_lookup_entry_from_row(row, blocks_by_entry.get(row[0], [])) for row in entry_rows]


def _lookup_keys(headword: str) -> list[str]:
    raw = headword.strip()
    comma_head = raw.split(",", 1)[0].strip()
    no_dot = _undotted_headword(raw)
    comma_no_dot = _undotted_headword(comma_head)
    candidates = [
        raw,
        comma_head,
        no_dot,
        comma_no_dot,
        raw.lower(),
        comma_head.lower(),
        _undotted_normalized_key(raw.lower()),
        _undotted_normalized_key(comma_head.lower()),
        normalize_greekish_token(raw) or "",
        normalize_greekish_token(comma_head) or "",
        _undotted_normalized_key(normalize_greekish_token(raw) or ""),
        _undotted_normalized_key(normalize_greekish_token(comma_head) or ""),
    ]
    keys: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            keys.append(candidate)
    return keys


def _lookup_rank(row: tuple[Any, ...], keys: Sequence[str]) -> tuple[int, int, int, str]:
    lemma = str(row[1])
    lemma_norm = str(row[2])
    lemma_variants = {lemma, _undotted_headword(lemma)}
    norm_variants = {lemma_norm, _undotted_normalized_key(lemma_norm)}
    for idx, key in enumerate(keys):
        if key in lemma_variants:
            return (0, idx, int(row[5]) if row[5] is not None else 999999, str(row[0]))
    for idx, key in enumerate(keys):
        if key in norm_variants:
            return (1, idx, int(row[5]) if row[5] is not None else 999999, str(row[0]))
    return (2, len(keys), int(row[5]) if row[5] is not None else 999999, str(row[0]))


def _undotted_headword(value: str) -> str:
    return value.replace("·", "").replace("·", "")


def _undotted_normalized_key(value: str) -> str:
    return value.replace("_", "").replace("-", "")


def _lookup_entry_from_row(row: tuple[Any, ...], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "entry_id": row[0],
        "lemma": row[1],
        "lemma_norm": row[2],
        "page_start": row[5],
        "page_end": row[6],
        "source": {
            "kind": row[3],
            "path": row[4],
            "page_start": row[5],
            "page_end": row[6],
        },
        "raw_text": row[7],
        "block_count": row[8],
        "blocks": blocks,
    }


def _entry_row(
    entry: Mapping[str, Any],
) -> tuple[str, str, str, str, str, int | None, int | None, str, int]:
    source = _mapping(entry.get("source"))
    blocks = list(_sequence(entry.get("blocks")))
    return (
        str(entry["entry_id"]),
        str(entry["lemma"]),
        str(entry["lemma_norm"]),
        str(source.get("kind") or "pdf"),
        str(source.get("path") or ""),
        _optional_int(source.get("page_start")),
        _optional_int(source.get("page_end")),
        repair_bailly_line_break_hyphenation(str(entry.get("raw_text") or "")),
        len(blocks),
    )


def _block_row(
    entry_id: str,
    block: Mapping[str, Any],
    ordinal: int,
) -> tuple[str, str, str, str, str, int]:
    layout = _mapping(block.get("layout"))
    return (
        entry_id,
        str(block["path"]),
        str(block["marker"]),
        repair_bailly_line_break_hyphenation(str(block["text"])),
        json.dumps(layout, ensure_ascii=False, sort_keys=True),
        ordinal,
    )


def _entry_arrow_table(
    rows: Sequence[tuple[str, str, str, str, str, int | None, int | None, str, int]],
) -> pa.Table:
    return pa.table(
        {
            "entry_id": [row[0] for row in rows],
            "lemma": [row[1] for row in rows],
            "lemma_norm": [row[2] for row in rows],
            "source_kind": [row[3] for row in rows],
            "source_path": [row[4] for row in rows],
            "page_start": [row[5] for row in rows],
            "page_end": [row[6] for row in rows],
            "raw_text": [row[7] for row in rows],
            "block_count": [row[8] for row in rows],
        }
    )


def _block_arrow_table(rows: Sequence[tuple[str, str, str, str, str, int]]) -> pa.Table:
    return pa.table(
        {
            "entry_id": [row[0] for row in rows],
            "path": [row[1] for row in rows],
            "marker": [row[2] for row in rows],
            "text": [row[3] for row in rows],
            "layout_json": [row[4] for row in rows],
            "ordinal": [row[5] for row in rows],
        }
    )


def _unregister_quietly(conn: duckdb.DuckDBPyConnection, name: str) -> None:
    with suppress(duckdb.CatalogException):
        conn.unregister(name)


def _mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return {}


def _sequence(value: object) -> Sequence[Mapping[str, Any]]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [cast(Mapping[str, Any], item) for item in value if isinstance(item, Mapping)]
    return []


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(cast(Any, value))
