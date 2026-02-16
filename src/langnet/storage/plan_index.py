from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import duckdb

from query_spec import ExecutedPlan, ToolPlan, ToolResponseRef

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "langnet.sql"


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply schema for plan-related indices."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


class PlanIndex:
    """
    DuckDB-backed index for raw query → ToolPlan.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def get(self, query_hash: str) -> ToolPlan | None:
        row = self.conn.execute(
            """
            SELECT plan_data
            FROM query_plan_index
            WHERE query_hash = ?
            """,
            [query_hash],
        ).fetchone()
        if not row:
            return None
        return ToolPlan.from_json(row[0])

    def upsert(self, query_hash: str, query: str, language: str, plan: ToolPlan) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO query_plan_index
            (query_hash, query, language, plan_id, plan_hash, plan_data, created_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            [
                query_hash,
                query,
                language,
                plan.plan_id,
                plan.plan_hash,
                plan.to_json(),
            ],
        )


class PlanResponseIndex:
    """
    DuckDB-backed index for plan_hash → response ids.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def get(self, plan_hash: str) -> ExecutedPlan | None:
        row = self.conn.execute(
            """
            SELECT plan_id, tool_response_ids
            FROM plan_response_index
            WHERE plan_hash = ?
            """,
            [plan_hash],
        ).fetchone()
        if not row:
            return None
        response_ids = json.loads(row[1]) if row[1] else []
        executed = ExecutedPlan(plan_id=row[0], plan_hash=plan_hash, from_cache=True)
        for ref in response_ids:
            executed.responses.append(ToolResponseRef.from_json(json.dumps(ref)))
        return executed

    def upsert(
        self, plan_hash: str, plan_id: str, response_refs: Sequence[ToolResponseRef]
    ) -> None:
        encoded_refs = [json.loads(ref.to_json()) for ref in response_refs]
        self.conn.execute(
            """
            INSERT OR REPLACE INTO plan_response_index
            (plan_hash, plan_id, tool_response_ids, created_at, last_accessed)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            [plan_hash, plan_id, json.dumps(encoded_refs)],
        )
