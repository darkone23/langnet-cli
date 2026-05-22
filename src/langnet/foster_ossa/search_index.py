from __future__ import annotations

import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from langnet.databuild.paths import (
    default_foster_ossa_path,
    default_foster_ossa_search_index_path,
)
from langnet.storage.db import connect_duckdb_ro

FOSTER_OSSA_SEARCH_INDEX_SCHEMA_VERSION = "langnet.foster_ossa_search_index.v1"
FOSTER_OSSA_SEARCH_RESULT_SCHEMA_VERSION = "langnet.foster_ossa_search.v1"
LANCE_DATASET_SUFFIX = ".lance"
LANCE_FTS_INDEX_OPTIONS = """
base_tokenizer='simple',
language='English',
lower_case=true,
stem=false,
remove_stop_words=false,
ascii_folding=false,
with_position=true,
replace=true
"""
SEARCH_INDEX_POLARS_SCHEMA = {
    "source_ref": pl.String,
    "record_kind": pl.String,
    "page_number": pl.Int64,
    "encounter_id": pl.String,
    "section": pl.String,
    "title": pl.String,
    "display_text": pl.String,
    "search_text": pl.String,
    "text_hash": pl.String,
    "source_db_path": pl.String,
    "index_schema_version": pl.String,
    "indexed_at": pl.String,
}


def build_foster_ossa_search_index(
    *,
    db_path: Path | None = None,
    index_path: Path | None = None,
    replace: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    source_db_path = (db_path or default_foster_ossa_path()).expanduser()
    dataset_path = _lance_dataset_path(index_path or default_foster_ossa_search_index_path())
    if not source_db_path.exists():
        raise FileNotFoundError(f"Foster Ossa DuckDB index not found: {source_db_path}")
    if replace and dataset_path.exists():
        shutil.rmtree(dataset_path)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    indexed_at = datetime.now(UTC).isoformat()
    rows = _index_rows(source_db_path, indexed_at=indexed_at, limit=limit)
    with duckdb.connect(":memory:") as conn:
        _load_lance(conn)
        if rows:
            _write_lance_rows(conn, dataset_path, rows)
        else:
            _write_empty_lance_dataset(conn, dataset_path)
        _create_lance_fts_indexes(conn, dataset_path)
    kind_counts = Counter(str(row["record_kind"]) for row in rows)
    return {
        "backend": "duckdb-lance",
        "dataset_path": str(dataset_path),
        "source_db_path": str(source_db_path),
        "record_count": len(rows),
        "record_kind_counts": dict(sorted(kind_counts.items())),
        "schema_version": FOSTER_OSSA_SEARCH_INDEX_SCHEMA_VERSION,
        "fts_indexed": True,
        "replaced": replace,
    }


def foster_ossa_search_index_status(index_path: Path | None = None) -> dict[str, Any]:
    dataset_path = _lance_dataset_path(index_path or default_foster_ossa_search_index_path())
    if not dataset_path.exists():
        return {
            "exists": False,
            "backend": "duckdb-lance",
            "dataset_path": str(dataset_path),
            "record_count": 0,
            "record_kind_counts": {},
            "schema_version": None,
            "source_db_path": None,
            "fts_indexes": [],
        }
    with duckdb.connect(":memory:") as conn:
        _load_lance(conn)
        dataset = _sql_literal(dataset_path)
        count_row = conn.execute(f"SELECT count(*) FROM {dataset}").fetchone()
        assert count_row is not None
        kind_counts = {
            str(kind): int(count)
            for kind, count in conn.execute(
                f"""
                SELECT record_kind, count(*)
                FROM {dataset}
                GROUP BY record_kind
                ORDER BY record_kind
                """
            ).fetchall()
        }
        row = conn.execute(
            f"""
            SELECT any_value(index_schema_version), any_value(source_db_path), max(indexed_at)
            FROM {dataset}
            """
        ).fetchone()
        assert row is not None
        return {
            "exists": True,
            "backend": "duckdb-lance",
            "dataset_path": str(dataset_path),
            "record_count": int(count_row[0]),
            "record_kind_counts": kind_counts,
            "schema_version": row[0],
            "source_db_path": row[1],
            "indexed_at": row[2],
            "fts_indexes": _lance_index_names(conn, dataset_path),
        }


def validate_foster_ossa_search_index(index_path: Path | None = None) -> dict[str, Any]:
    status = foster_ossa_search_index_status(index_path)
    issues: list[dict[str, str]] = []
    if not status["exists"]:
        issues.append(
            {
                "code": "index_missing",
                "message": f"Foster Ossa search index missing: {status['dataset_path']}",
            }
        )
        return {"status": status, "issues": issues}
    if status.get("schema_version") != FOSTER_OSSA_SEARCH_INDEX_SCHEMA_VERSION:
        issues.append(
            {
                "code": "schema_version",
                "message": "Foster Ossa search index schema version is not supported.",
            }
        )
    index_names = set(status.get("fts_indexes") or [])
    for required_index in ("display_text_idx", "search_text_idx", "title_idx"):
        if required_index not in index_names:
            issues.append(
                {
                    "code": "fts_index_missing",
                    "message": (
                        f"Foster Ossa search index missing Lance FTS index: {required_index}"
                    ),
                }
            )
    return {"status": status, "issues": issues}


def search_foster_ossa_lance(
    query: str,
    *,
    index_path: Path | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    dataset_path = _lance_dataset_path(index_path or default_foster_ossa_search_index_path())
    normalized_query = _search_query(query)
    if not dataset_path.exists() or not normalized_query or limit == 0:
        results: list[dict[str, Any]] = []
    else:
        with duckdb.connect(":memory:") as conn:
            _load_lance(conn)
            rows = _dict_rows(
                conn,
                f"""
                SELECT s.*, s._score AS score
                FROM lance_fts(
                    {_sql_literal(dataset_path)},
                    'search_text',
                    ?,
                    k = ?
                ) s
                ORDER BY
                    CASE s.record_kind WHEN 'page' THEN 0 ELSE 1 END,
                    s._score DESC,
                    s.page_number,
                    s.source_ref
                LIMIT ?
                """,
                [normalized_query, max(limit * 5, 50), limit],
            )
            results = [_result_item(row) for row in rows]
    return {
        "schema_version": FOSTER_OSSA_SEARCH_RESULT_SCHEMA_VERSION,
        "backend": "duckdb-lance",
        "index_path": str(dataset_path),
        "request": {"query": query, "limit": limit},
        "results": results,
    }


def _index_rows(
    db_path: Path,
    *,
    indexed_at: str,
    limit: int | None,
) -> list[dict[str, Any]]:
    with connect_duckdb_ro(db_path) as conn:
        page_rows = _dict_rows(
            conn,
            """
            SELECT
                p.page_number,
                coalesce(s.section, '') AS section,
                coalesce(e.encounter_id, '') AS encounter_id,
                p.text,
                p.text_hash
            FROM pages p
            LEFT JOIN sections s ON s.page_number = p.page_number
            LEFT JOIN encounters e ON p.page_number BETWEEN e.page_start AND e.page_end
            ORDER BY p.page_number
            """,
        )
        encounter_rows = _dict_rows(
            conn,
            """
            SELECT
                e.encounter_id,
                e.page_start,
                e.page_end,
                e.heading,
                e.title,
                coalesce(s.section, '') AS section
            FROM encounters e
            LEFT JOIN sections s ON s.page_number = e.page_start
            ORDER BY e.experience, e.encounter
            """,
        )
    rows = [_page_index_row(db_path, row, indexed_at=indexed_at) for row in page_rows]
    pages_by_number = {int(row["page_number"]): row for row in page_rows}
    rows.extend(
        _encounter_index_row(db_path, row, pages_by_number, indexed_at=indexed_at)
        for row in encounter_rows
    )
    return rows[:limit] if limit is not None else rows


def _page_index_row(db_path: Path, row: dict[str, Any], *, indexed_at: str) -> dict[str, Any]:
    page_number = int(row["page_number"])
    display_text = _clean_text(str(row["text"]))
    encounter_id = str(row.get("encounter_id") or "")
    return {
        "source_ref": f"page:{page_number}",
        "record_kind": "page",
        "page_number": page_number,
        "encounter_id": encounter_id,
        "section": str(row.get("section") or ""),
        "title": "",
        "display_text": display_text,
        "search_text": _normalize_search_text(display_text),
        "text_hash": str(row["text_hash"]),
        "source_db_path": str(db_path),
        "index_schema_version": FOSTER_OSSA_SEARCH_INDEX_SCHEMA_VERSION,
        "indexed_at": indexed_at,
    }


def _encounter_index_row(
    db_path: Path,
    row: dict[str, Any],
    pages_by_number: dict[int, dict[str, Any]],
    *,
    indexed_at: str,
) -> dict[str, Any]:
    page_start = int(row["page_start"])
    page_end = int(row["page_end"])
    page_texts = [
        _clean_text(str(pages_by_number[page_number]["text"]))
        for page_number in range(page_start, page_end + 1)
        if page_number in pages_by_number
    ]
    title = _clean_text(f"{row['heading']} {row['title']}".strip())
    display_text = _clean_text("\n\n".join([title, *page_texts]))
    return {
        "source_ref": f"encounter:{row['encounter_id']}",
        "record_kind": "encounter",
        "page_number": page_start,
        "encounter_id": str(row["encounter_id"]),
        "section": str(row.get("section") or ""),
        "title": title,
        "display_text": display_text,
        "search_text": _normalize_search_text(display_text),
        "text_hash": _normalize_search_text(
            "|".join(_page_hashes(page_start, page_end, pages_by_number))
        ),
        "source_db_path": str(db_path),
        "index_schema_version": FOSTER_OSSA_SEARCH_INDEX_SCHEMA_VERSION,
        "indexed_at": indexed_at,
    }


def _page_hashes(
    page_start: int,
    page_end: int,
    pages_by_number: dict[int, dict[str, Any]],
) -> list[str]:
    return [
        str(pages_by_number[page_number]["text_hash"])
        for page_number in range(page_start, page_end + 1)
        if page_number in pages_by_number
    ]


def _write_lance_rows(
    conn: duckdb.DuckDBPyConnection,
    dataset_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    frame = pl.DataFrame(rows, schema=SEARCH_INDEX_POLARS_SCHEMA)
    conn.register("foster_ossa_search_rows", frame)
    conn.execute(
        f"""
        COPY (
            SELECT *
            FROM foster_ossa_search_rows
        ) TO {_sql_literal(dataset_path)} (
            FORMAT lance,
            MODE 'overwrite'
        )
        """
    )
    conn.unregister("foster_ossa_search_rows")


def _write_empty_lance_dataset(conn: duckdb.DuckDBPyConnection, dataset_path: Path) -> None:
    frame = pl.DataFrame([], schema=SEARCH_INDEX_POLARS_SCHEMA)
    conn.register("foster_ossa_search_rows", frame)
    conn.execute(
        f"""
        COPY (
            SELECT *
            FROM foster_ossa_search_rows
        ) TO {_sql_literal(dataset_path)} (
            FORMAT lance,
            MODE 'overwrite',
            WRITE_EMPTY_FILE true
        )
        """
    )
    conn.unregister("foster_ossa_search_rows")


def _create_lance_fts_indexes(conn: duckdb.DuckDBPyConnection, dataset_path: Path) -> None:
    for index_name, column_name in (
        ("search_text_idx", "search_text"),
        ("display_text_idx", "display_text"),
        ("title_idx", "title"),
    ):
        conn.execute(
            f"""
            CREATE INDEX {index_name}
            ON {_sql_literal(dataset_path)} ({column_name})
            USING INVERTED WITH ({LANCE_FTS_INDEX_OPTIONS})
            """
        )


def _result_item(row: dict[str, Any]) -> dict[str, Any]:
    encounter_id = str(row.get("encounter_id") or "")
    page_number = int(row["page_number"])
    return {
        "score": float(row.get("score") or row.get("_score") or 0.0),
        "source_ref": str(row["source_ref"]),
        "record_kind": str(row["record_kind"]),
        "page_number": page_number,
        "encounter_id": encounter_id or None,
        "section": str(row.get("section") or ""),
        "title": str(row.get("title") or ""),
        "text": str(row["display_text"]),
        "snippet": str(row["display_text"])[:500],
        "target": _target(encounter_id, page_number),
    }


def _target(encounter_id: str, page_number: int) -> dict[str, Any]:
    if encounter_id:
        return {
            "command": "foster-ossa encounter",
            "encounter_id": encounter_id,
            "page": page_number,
        }
    return {"command": "foster-ossa search", "page": page_number}


def _load_lance(conn: duckdb.DuckDBPyConnection) -> None:
    try:
        conn.execute("LOAD lance")
    except duckdb.Error:
        conn.execute("INSTALL lance FROM community")
        conn.execute("LOAD lance")


def _lance_dataset_path(index_path: Path) -> Path:
    expanded = index_path.expanduser()
    return expanded if expanded.suffix == LANCE_DATASET_SUFFIX else expanded.with_suffix(".lance")


def _lance_index_names(conn: duckdb.DuckDBPyConnection, dataset_path: Path) -> list[str]:
    try:
        rows = conn.execute(f"SHOW INDEXES ON {_sql_literal(dataset_path)}").fetchall()
    except duckdb.Error:
        return []
    return [str(row[0]) for row in rows]


def _dict_rows(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object] | None = None,
) -> list[dict[str, Any]]:
    result = conn.execute(query, params or [])
    columns = [column[0] for column in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _normalize_search_text(text: str) -> str:
    return _clean_text(text).casefold()


def _search_query(query: str) -> str:
    return " ".join(_normalize_search_text(query).split())


def _sql_literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"
