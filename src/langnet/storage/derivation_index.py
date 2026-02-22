from __future__ import annotations

from pathlib import Path

import duckdb
import orjson

from langnet.execution.effects import DerivationEffect

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "langnet.sql"


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


class DerivationIndex:
    """
    DuckDB-backed index for derivations produced from parsed extractions.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn
        self._schema_applied = False

    def _ensure_schema(self) -> None:
        if not self._schema_applied:
            apply_schema(self.conn)
            self._schema_applied = True

    def store_effect(self, effect: DerivationEffect) -> str:
        self._ensure_schema()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO derivation_index
            (derivation_id, extraction_id, tool, kind, canonical, payload, derive_duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                effect.derivation_id,
                effect.extraction_id,
                effect.tool,
                effect.kind,
                effect.canonical,
                orjson.dumps(effect.payload or {}).decode("utf-8"),
                effect.derive_duration_ms,
            ],
        )
        return effect.derivation_id
