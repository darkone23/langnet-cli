from __future__ import annotations

import json
from pathlib import Path

import duckdb
from query_spec import ToolResponseRef

from langnet.clients.base import RawResponseEffect

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "langnet.sql"


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


class RawResponseIndex:
    """
    DuckDB-backed index for transport-level raw responses.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def store(self, effect: RawResponseEffect) -> ToolResponseRef:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO raw_response_index
            (
                response_id,
                tool,
                call_id,
                endpoint,
                status_code,
                content_type,
                headers,
                body,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                effect.response_id,
                effect.tool,
                effect.call_id,
                effect.endpoint,
                effect.status_code,
                effect.content_type,
                json.dumps(effect.headers),
                effect.body,
            ],
        )
        return ToolResponseRef(
            tool=effect.tool,
            call_id=effect.call_id,
            response_id=effect.response_id,
            cached=False,
        )

    def get(self, response_id: str) -> RawResponseEffect | None:
        row = self.conn.execute(
            """
            SELECT tool, call_id, endpoint, status_code, content_type, headers, body
            FROM raw_response_index
            WHERE response_id = ?
            """,
            [response_id],
        ).fetchone()
        if not row:
            return None
        headers = json.loads(row[5]) if row[5] else {}
        return RawResponseEffect(
            response_id=response_id,
            tool=row[0],
            call_id=row[1],
            endpoint=row[2],
            status_code=row[3],
            content_type=row[4] or "",
            headers=headers,
            body=row[6],
        )
