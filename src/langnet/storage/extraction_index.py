from __future__ import annotations

import uuid
from collections.abc import Iterable
from pathlib import Path

import duckdb
import orjson

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import ExtractionEffect

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "langnet.sql"


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


def _new_extraction_id() -> str:
    return str(uuid.uuid4())


class ExtractionIndex:
    """
    DuckDB-backed index for parsed extractions derived from raw responses.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn
        self._schema_applied = False

    def _ensure_schema(self) -> None:
        if not self._schema_applied:
            apply_schema(self.conn)
            self._schema_applied = True

    def store(
        self,
        response: RawResponseEffect,
        kind: str,
        canonical: str | None,
        payload: dict | list | None,
        load_duration_ms: int = 0,
    ) -> str:
        extraction_id = _new_extraction_id()
        self._ensure_schema()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO extraction_index
            (extraction_id, response_id, tool, kind, canonical, payload, load_duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                extraction_id,
                response.response_id,
                response.tool,
                kind,
                canonical,
                orjson.dumps(payload or {}).decode("utf-8"),
                load_duration_ms,
            ],
        )
        return extraction_id

    def store_effect(self, effect: ExtractionEffect) -> str:
        """Store a prebuilt ExtractionEffect."""
        self._ensure_schema()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO extraction_index
            (extraction_id, response_id, tool, kind, canonical, payload, load_duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                effect.extraction_id,
                effect.response_id,
                effect.tool,
                effect.kind,
                effect.canonical,
                orjson.dumps(effect.payload or {}).decode("utf-8"),
                effect.load_duration_ms,
            ],
        )
        return effect.extraction_id

    def get_by_canonical(self, canonical: str) -> Iterable[tuple[str, str]]:
        self._ensure_schema()
        rows = self.conn.execute(
            """
            SELECT extraction_id, tool
            FROM extraction_index
            WHERE canonical = ?
            """,
            [canonical],
        ).fetchall()
        return [(row[0], row[1]) for row in rows]
