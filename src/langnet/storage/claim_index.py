from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import duckdb
import orjson

from langnet.execution.effects import ClaimEffect

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "langnet.sql"


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


class ClaimIndex:
    """
    DuckDB-backed index for universal claims emitted after derivations.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn
        self._schema_applied = False

    def _ensure_schema(self) -> None:
        if not self._schema_applied:
            apply_schema(self.conn)
            self._schema_applied = True

    def store_effect(self, effect: ClaimEffect) -> str:
        self._ensure_schema()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO claims
            (claim_id, derivation_id, subject, predicate, value, provenance_chain, load_duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                effect.claim_id,
                effect.derivation_id,
                effect.subject,
                effect.predicate,
                orjson.dumps(effect.value or {}).decode("utf-8"),
                orjson.dumps([asdict(pc) for pc in effect.provenance_chain]).decode("utf-8"),
                effect.load_duration_ms,
            ],
        )
        return effect.claim_id
