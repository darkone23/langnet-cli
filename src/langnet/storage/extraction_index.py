from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from pathlib import Path

import duckdb

from langnet.clients.base import RawResponseEffect

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

    def store(
        self,
        response: RawResponseEffect,
        kind: str,
        canonical: str | None,
        payload: dict | list | None,
    ) -> str:
        extraction_id = _new_extraction_id()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO extraction_index
            (extraction_id, response_id, tool, kind, canonical, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                extraction_id,
                response.response_id,
                response.tool,
                kind,
                canonical,
                json.dumps(payload or {}),
            ],
        )
        return extraction_id

    def get_by_canonical(self, canonical: str) -> Iterable[tuple[str, str]]:
        rows = self.conn.execute(
            """
            SELECT extraction_id, tool
            FROM extraction_index
            WHERE canonical = ?
            """,
            [canonical],
        ).fetchall()
        return [(row[0], row[1]) for row in rows]
