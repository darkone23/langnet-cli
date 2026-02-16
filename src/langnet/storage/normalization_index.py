from __future__ import annotations

import json
from pathlib import Path

import duckdb
from query_spec import NormalizedQuery

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "langnet.sql"


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply core schema to the provided DuckDB connection."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


class NormalizationIndex:
    """
    DuckDB-backed index for raw query → normalized query results.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def get(self, query_hash: str) -> NormalizedQuery | None:
        row = self.conn.execute(
            """
            SELECT normalized_json
            FROM query_normalization_index
            WHERE query_hash = ?
            """,
            [query_hash],
        ).fetchone()
        if not row:
            return None
        normalized_json = row[0]
        return NormalizedQuery().from_json(normalized_json)

    def upsert(
        self, query_hash: str, raw_query: str, language: str, normalized: NormalizedQuery
    ) -> None:
        candidates_json = json.dumps(
            [
                {"lemma": c.lemma, "encodings": c.encodings, "sources": c.sources}
                for c in normalized.candidates
            ]
        )
        self.conn.execute(
            """
            INSERT OR REPLACE INTO query_normalization_index
            (
                query_hash,
                raw_query,
                language,
                normalized_json,
                canonical_forms,
                created_at,
                last_accessed
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            [
                query_hash,
                raw_query,
                language,
                normalized.to_json(),
                candidates_json,
            ],
        )
