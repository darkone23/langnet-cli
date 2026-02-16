from __future__ import annotations

from pathlib import Path

import duckdb
import orjson
from google.protobuf.json_format import MessageToDict, ParseDict
from query_spec import NormalizedQuery

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "langnet.sql"


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply core schema to the provided DuckDB connection."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


def _fetch_single_count(result) -> int:
    """Safely extract a single count value from a fetchone result."""
    row = result.fetchone()
    if row is None:
        return 0
    return row[0]


def ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Idempotently apply schema only if the normalization table is missing.

    Avoids re-executing the full project schema on every cache lookup.
    """
    TABLE_NAME = "query_normalization_index"
    result = conn.execute(
        f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{TABLE_NAME}'"
    )
    exists = _fetch_single_count(result)
    if exists:
        return
    apply_schema(conn)


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
        data = orjson.loads(normalized_json)
        return ParseDict(data, NormalizedQuery())

    def upsert(
        self,
        query_hash: str,
        raw_query: str,
        language: str,
        normalized: NormalizedQuery,
        source_response_ids: list[str] | None = None,
    ) -> None:
        candidates_json = orjson.dumps(
            [
                {"lemma": c.lemma, "encodings": dict(c.encodings), "sources": list(c.sources)}
                for c in normalized.candidates
            ]
        ).decode("utf-8")
        response_ids_json = (
            orjson.dumps(source_response_ids).decode("utf-8") if source_response_ids else None
        )
        # Serialize normalized query using protobuf binary format
        normalized_json = orjson.dumps(MessageToDict(normalized)).decode("utf-8")
        self.conn.execute(
            """
            INSERT OR REPLACE INTO query_normalization_index
            (
                query_hash,
                raw_query,
                language,
                normalized_json,
                canonical_forms,
                source_response_ids,
                created_at,
                last_accessed
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            [
                query_hash,
                raw_query,
                language,
                normalized_json,
                candidates_json,
                response_ids_json,
            ],
        )

    def get_source_response_ids(self, query_hash: str) -> list[str]:
        """Get the raw response IDs that contributed to this normalization."""
        row = self.conn.execute(
            """
            SELECT source_response_ids
            FROM query_normalization_index
            WHERE query_hash = ?
            """,
            [query_hash],
        ).fetchone()
        if not row or row[0] is None:
            return []
        return orjson.loads(row[0])
