from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import duckdb
from returns.result import Failure, Success

from langnet.foster_ossa.models import FosterOssaPage
from langnet.foster_ossa.structure import (
    detect_concept_mentions,
    detect_encounters,
    structured_page_rows,
)
from langnet.foster_ossa.toc import parse_toc_entries
from langnet.storage.db import connect_duckdb_ro

from .base import BuildErrorStats, BuildResult, BuildStatus, FosterOssaStats
from .paths import default_foster_ossa_path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pages (
    page_number INTEGER PRIMARY KEY,
    source_path VARCHAR NOT NULL,
    extraction_tool VARCHAR NOT NULL,
    text TEXT NOT NULL,
    text_hash VARCHAR NOT NULL,
    warning VARCHAR NOT NULL DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sections (
    page_number INTEGER PRIMARY KEY,
    section VARCHAR NOT NULL,
    text_hash VARCHAR NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id VARCHAR PRIMARY KEY,
    experience INTEGER NOT NULL,
    encounter INTEGER NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    heading VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS concept_mentions (
    mention_id VARCHAR PRIMARY KEY,
    term VARCHAR NOT NULL,
    normalized_term VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    page_number INTEGER NOT NULL,
    encounter_id VARCHAR,
    context TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS toc_entries (
    toc_id VARCHAR PRIMARY KEY,
    source_page_number INTEGER NOT NULL,
    section_kind VARCHAR NOT NULL,
    experience INTEGER NOT NULL,
    encounter INTEGER,
    global_encounter INTEGER,
    encounter_id VARCHAR,
    latin_title TEXT NOT NULL,
    english_title TEXT NOT NULL,
    printed_page INTEGER NOT NULL,
    inferred_page_number INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS summaries (
    summary_id VARCHAR PRIMARY KEY,
    summary_kind VARCHAR NOT NULL,
    key VARCHAR NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS foster_ossa_pages_page_idx ON pages(page_number);
CREATE INDEX IF NOT EXISTS foster_ossa_pages_text_idx ON pages(text);
CREATE INDEX IF NOT EXISTS foster_ossa_sections_section_idx ON sections(section);
CREATE INDEX IF NOT EXISTS foster_ossa_encounters_page_idx ON encounters(page_start, page_end);
CREATE INDEX IF NOT EXISTS foster_ossa_mentions_term_idx
    ON concept_mentions(normalized_term);
CREATE INDEX IF NOT EXISTS foster_ossa_mentions_page_idx ON concept_mentions(page_number);
CREATE INDEX IF NOT EXISTS foster_ossa_toc_experience_idx ON toc_entries(experience);
CREATE INDEX IF NOT EXISTS foster_ossa_toc_encounter_idx ON toc_entries(encounter_id);
"""


@dataclass(frozen=True)
class FosterOssaBuildConfig:
    source_path: Path
    output_path: Path | None = None
    limit: int | None = None
    wipe_existing: bool = True
    force_rebuild: bool = False


class FosterOssaBuilder:
    """Build a local DuckDB index from Foster Ossa extracted page JSONL."""

    def __init__(self, config: FosterOssaBuildConfig) -> None:
        self.source_path = config.source_path.expanduser()
        self.output_path = (
            config.output_path.expanduser()
            if config.output_path is not None
            else default_foster_ossa_path()
        )
        self.limit = config.limit
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[FosterOssaStats | BuildErrorStats]:
        created_output = False
        failure: Exception | None = None
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(f"Foster Ossa page JSONL not found at {self.source_path}")
            if self.output_path.exists():
                if self.wipe_existing or self.force_rebuild:
                    self.output_path.unlink()
                else:
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            created_output = not self.output_path.exists()
            self._conn = duckdb.connect(str(self.output_path))
            apply_foster_ossa_schema(self._conn)
            self._load_pages()
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(self.get_stats()),
            )
        except Exception as exc:  # noqa: BLE001
            failure = exc
            return BuildResult(
                status=BuildStatus.FAILED,
                output_path=self.output_path,
                stats=Failure(BuildErrorStats(error=str(exc))),
                message=str(exc),
            )
        finally:
            self.cleanup()
            if failure is not None and created_output and self.output_path.exists():
                self.output_path.unlink()

    def _load_pages(self) -> None:
        assert self._conn is not None
        pages = list(self._iter_jsonl_pages())
        _validate_unique_page_numbers(pages)
        structured_pages = structured_page_rows(pages)
        encounters = detect_encounters(pages)
        mentions = detect_concept_mentions(pages, encounters)
        toc_entries = parse_toc_entries(pages)

        page_rows = [
            (
                page.page_number,
                page.source_path,
                page.extraction_tool,
                page.text,
                page.text_hash,
                page.warning,
            )
            for page in pages
        ]
        section_rows = [
            (page.page_number, page.section, page.text_hash) for page in structured_pages
        ]
        encounter_rows = [
            (
                encounter.encounter_id,
                encounter.experience,
                encounter.encounter,
                encounter.page_start,
                encounter.page_end,
                encounter.heading,
                encounter.title,
            )
            for encounter in encounters
        ]
        mention_rows = [
            (
                _mention_id(mention.term, mention.page_number, ordinal),
                mention.term,
                mention.normalized_term,
                mention.category,
                mention.page_number,
                mention.encounter_id,
                mention.context,
            )
            for ordinal, mention in enumerate(mentions)
        ]
        toc_rows = [
            (
                entry.toc_id,
                entry.source_page_number,
                entry.section_kind,
                entry.experience,
                entry.encounter,
                entry.global_encounter,
                entry.encounter_id,
                entry.latin_title,
                entry.english_title,
                entry.printed_page,
                entry.inferred_page_number,
            )
            for entry in toc_entries
        ]

        self._conn.execute("BEGIN TRANSACTION")
        try:
            _delete_existing_rows(self._conn)
            if page_rows:
                self._conn.executemany(
                    """
                    INSERT OR REPLACE INTO pages (
                        page_number,
                        source_path,
                        extraction_tool,
                        text,
                        text_hash,
                        warning,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    page_rows,
                )
            if section_rows:
                self._conn.executemany(
                    """
                    INSERT OR REPLACE INTO sections (
                        page_number,
                        section,
                        text_hash,
                        updated_at
                    )
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    section_rows,
                )
            if encounter_rows:
                self._conn.executemany(
                    """
                    INSERT OR REPLACE INTO encounters (
                        encounter_id,
                        experience,
                        encounter,
                        page_start,
                        page_end,
                        heading,
                        title,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    encounter_rows,
                )
            if mention_rows:
                self._conn.executemany(
                    """
                    INSERT OR REPLACE INTO concept_mentions (
                        mention_id,
                        term,
                        normalized_term,
                        category,
                        page_number,
                        encounter_id,
                        context,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    mention_rows,
                )
            if toc_rows:
                self._conn.executemany(
                    """
                    INSERT OR REPLACE INTO toc_entries (
                        toc_id,
                        source_page_number,
                        section_kind,
                        experience,
                        encounter,
                        global_encounter,
                        encounter_id,
                        latin_title,
                        english_title,
                        printed_page,
                        inferred_page_number,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    toc_rows,
                )
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")

    def _iter_jsonl_pages(self) -> Iterator[FosterOssaPage]:
        count = 0
        with self.source_path.open(encoding="utf-8") as source:
            for line_num, line in enumerate(source, start=1):
                if self.limit is not None and count >= self.limit:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                loaded = json.loads(stripped)
                if not isinstance(loaded, Mapping):
                    raise ValueError(f"Expected object on JSONL line {line_num}")
                yield _page_from_mapping(loaded, line_num)
                count += 1

    def get_stats(self) -> FosterOssaStats:
        size_mb = None
        page_count = None
        section_count = None
        encounter_count = None
        concept_mention_count = None
        summary_count = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 3)
            conn = self._conn or duckdb.connect(str(self.output_path), read_only=True)
            try:
                page_count = _count_table(conn, "pages")
                section_count = _count_table(conn, "sections")
                encounter_count = _count_table(conn, "encounters")
                concept_mention_count = _count_table(conn, "concept_mentions")
                summary_count = _count_table(conn, "summaries")
            finally:
                if conn is not self._conn:
                    conn.close()
        return FosterOssaStats(
            path=str(self.output_path),
            page_count=page_count,
            section_count=section_count,
            encounter_count=encounter_count,
            concept_mention_count=concept_mention_count,
            summary_count=summary_count,
            size_mb=size_mb,
        )

    def cleanup(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def apply_foster_ossa_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the Foster Ossa extracted-page index tables."""
    for stmt in SCHEMA_SQL.strip().split(";"):
        sql_stmt = stmt.strip()
        if sql_stmt:
            conn.execute(sql_stmt)


def search_foster_ossa(
    query: str,
    *,
    db_path: Path | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    db_path = db_path or default_foster_ossa_path()
    if not db_path.exists():
        return []
    normalized_query = query.casefold().strip()
    if not normalized_query:
        return []
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(
            """
            SELECT pages.page_number, sections.section, pages.text
            FROM pages
            LEFT JOIN sections ON pages.page_number = sections.page_number
            WHERE lower(pages.text) LIKE ? ESCAPE '\\'
            ORDER BY pages.page_number
            LIMIT ?
            """,
            [f"%{_escape_like(normalized_query)}%", limit],
        ).fetchall()
    return [{"page_number": row[0], "section": row[1] or "", "text": row[2]} for row in rows]


def lookup_concept_mentions(
    term: str,
    *,
    db_path: Path | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    db_path = db_path or default_foster_ossa_path()
    if not db_path.exists():
        return []
    normalized_term = _normalize_lookup_term(term)
    if not normalized_term:
        return []
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                term,
                normalized_term,
                category,
                page_number,
                encounter_id,
                context
            FROM concept_mentions
            WHERE normalized_term = ?
            ORDER BY page_number, mention_id
            LIMIT ?
            """,
            [normalized_term, limit],
        ).fetchall()
    return [
        {
            "term": row[0],
            "normalized_term": row[1],
            "category": row[2],
            "page_number": row[3],
            "encounter_id": row[4],
            "context": row[5],
        }
        for row in rows
    ]


def lookup_encounter(
    encounter_id: str,
    *,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    db_path = db_path or default_foster_ossa_path()
    if not db_path.exists():
        return None
    with connect_duckdb_ro(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                encounter_id,
                experience,
                encounter,
                page_start,
                page_end,
                heading,
                title
            FROM encounters
            WHERE encounter_id = ?
            """,
            [encounter_id],
        ).fetchone()
    if row is None:
        return None
    return {
        "encounter_id": row[0],
        "experience": row[1],
        "encounter": row[2],
        "page_start": row[3],
        "page_end": row[4],
        "heading": row[5],
        "title": row[6],
    }


def lookup_toc_entries(
    *,
    db_path: Path | None = None,
    experience: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    db_path = db_path or default_foster_ossa_path()
    if not db_path.exists() or limit == 0:
        return []
    conditions: list[str] = []
    params: list[Any] = []
    if experience is not None:
        conditions.append("experience = ?")
        params.append(experience)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                toc_id,
                source_page_number,
                section_kind,
                experience,
                encounter,
                global_encounter,
                encounter_id,
                latin_title,
                english_title,
                printed_page,
                inferred_page_number
            FROM toc_entries
            {where}
            ORDER BY experience, coalesce(encounter, 0), printed_page
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    return [
        {
            "toc_id": row[0],
            "source_page_number": row[1],
            "section_kind": row[2],
            "experience": row[3],
            "encounter": row[4],
            "global_encounter": row[5],
            "encounter_id": row[6],
            "latin_title": row[7],
            "english_title": row[8],
            "printed_page": row[9],
            "inferred_page_number": row[10],
        }
        for row in rows
    ]


def page_rows_for_summary(
    *,
    db_path: Path | None = None,
    limit: int | None = None,
    encounter_id: str | None = None,
) -> list[dict[str, Any]]:
    db_path = db_path or default_foster_ossa_path()
    if not db_path.exists():
        return []
    if limit == 0:
        return []
    conditions: list[str] = []
    params: list[Any] = []
    if encounter_id:
        conditions.append(
            """
            pages.page_number BETWEEN (
                SELECT page_start FROM encounters WHERE encounter_id = ?
            ) AND (
                SELECT page_end FROM encounters WHERE encounter_id = ?
            )
            """
        )
        params.extend([encounter_id, encounter_id])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT pages.page_number, sections.section, pages.text, pages.text_hash
        FROM pages
        LEFT JOIN sections ON pages.page_number = sections.page_number
        {where}
        ORDER BY pages.page_number
    """
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "page_number": row[0],
            "section": row[1] or "",
            "text": row[2],
            "text_hash": row[3],
        }
        for row in rows
    ]


def toc_entry_rows_for_summary(
    *,
    db_path: Path | None = None,
    limit: int | None = None,
    encounter_id: str | None = None,
) -> list[dict[str, Any]]:
    db_path = db_path or default_foster_ossa_path()
    if not db_path.exists() or limit == 0:
        return []
    conditions: list[str] = []
    params: list[Any] = []
    if encounter_id:
        conditions.append("encounter_id = ?")
        params.append(encounter_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    limit_clause = "LIMIT ?" if limit is not None else ""
    if limit is not None:
        params.append(limit)
    query = f"""
        WITH toc_spans AS (
            SELECT
                toc_id,
                source_page_number,
                section_kind,
                experience,
                encounter,
                global_encounter,
                encounter_id,
                latin_title,
                english_title,
                inferred_page_number AS page_start,
                coalesce(
                    lead(inferred_page_number) OVER (
                        ORDER BY coalesce(global_encounter, 999999), experience, encounter
                    ),
                    (SELECT max(page_number) + 1 FROM pages)
                ) - 1 AS page_end
            FROM toc_entries
        ),
        limited_spans AS (
            SELECT *
            FROM toc_spans
            {where}
            ORDER BY coalesce(global_encounter, 999999), experience, encounter
            {limit_clause}
        )
        SELECT
            limited_spans.toc_id,
            limited_spans.source_page_number,
            limited_spans.section_kind,
            limited_spans.experience,
            limited_spans.encounter,
            limited_spans.global_encounter,
            limited_spans.encounter_id,
            limited_spans.latin_title,
            limited_spans.english_title,
            limited_spans.page_start,
            limited_spans.page_end,
            pages.page_number,
            sections.section,
            pages.text,
            pages.text_hash
        FROM limited_spans
        LEFT JOIN pages
            ON pages.page_number BETWEEN limited_spans.page_start AND limited_spans.page_end
        LEFT JOIN sections ON sections.page_number = pages.page_number
        ORDER BY
            coalesce(limited_spans.global_encounter, 999999),
            limited_spans.experience,
            limited_spans.encounter,
            pages.page_number
    """
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    page_hashes: dict[str, list[str]] = {}
    for row in rows:
        toc_id = row[0]
        if toc_id not in grouped:
            grouped[toc_id] = {
                "source_ref": toc_id,
                "toc_id": toc_id,
                "source_page_number": row[1],
                "section_kind": row[2],
                "experience": row[3],
                "encounter": row[4],
                "global_encounter": row[5],
                "encounter_id": row[6],
                "latin_title": row[7],
                "english_title": row[8],
                "page_start": row[9],
                "page_end": row[10],
                "pages": [],
                "text": "",
                "text_hash": "",
            }
            page_hashes[toc_id] = []
        if row[11] is None:
            continue
        grouped[toc_id]["pages"].append(
            {
                "page_number": row[11],
                "section": row[12] or "",
                "text_hash": row[14],
            }
        )
        grouped[toc_id]["text"] = (
            f"{grouped[toc_id]['text']}\n\n{row[13]}".strip()
            if grouped[toc_id]["text"]
            else row[13]
        )
        page_hashes[toc_id].append(row[14])
    for toc_id, row in grouped.items():
        row["text_hash"] = sha256("\n".join(page_hashes[toc_id]).encode("utf-8")).hexdigest()
    return list(grouped.values())


def _page_from_mapping(row: Mapping[str, Any], line_num: int) -> FosterOssaPage:
    for field in ("page_number", "source_path", "extraction_tool", "text"):
        if field not in row:
            raise ValueError(f"Missing required page field on JSONL line {line_num}: {field}")
    try:
        page_number = int(row["page_number"])
        source_path = str(row["source_path"])
        extraction_tool = str(row["extraction_tool"])
        text = str(row["text"]).strip()
    except KeyError as exc:
        raise ValueError(f"Missing required page field on JSONL line {line_num}: {exc}") from exc
    text_hash = str(row.get("text_hash") or sha256(text.encode("utf-8")).hexdigest())
    warning = str(row.get("warning") or "")
    return FosterOssaPage(
        page_number=page_number,
        source_path=source_path,
        extraction_tool=extraction_tool,
        text=text,
        text_hash=text_hash,
        warning=warning,
    )


def _validate_unique_page_numbers(pages: list[FosterOssaPage]) -> None:
    seen: set[int] = set()
    for page in pages:
        if page.page_number in seen:
            raise ValueError(f"Duplicate Foster Ossa page_number {page.page_number}")
        seen.add(page.page_number)


def _normalize_lookup_term(term: str) -> str:
    return term.strip().strip(".").casefold().replace(" ", "_")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _mention_id(term: str, page_number: int, ordinal: int) -> str:
    return f"foster-ossa:p{page_number}:{ordinal:06d}:{_normalize_lookup_term(term)}"


def _delete_existing_rows(conn: duckdb.DuckDBPyConnection) -> None:
    for table in (
        "summaries",
        "toc_entries",
        "concept_mentions",
        "encounters",
        "sections",
        "pages",
    ):
        conn.execute(f"DELETE FROM {table}")


def _count_table(conn: duckdb.DuckDBPyConnection, table: str) -> int:
    result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(result[0]) if result else 0
