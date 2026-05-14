from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from langnet.reader.author_index import (
    author_index_entry,
    author_section_sort_key,
    author_selector_matches,
    compact_author_id,
    is_synthetic_author_selector,
    normalize_section_key,
)
from langnet.reader.models import (
    ReaderAlias,
    ReaderBookArtifact,
    ReaderContainedWork,
    ReaderEdition,
    ReaderMetadataAttribution,
    ReaderMetadataOverlay,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceFile,
    ReaderSourceMetadata,
    ReaderWork,
)

CATALOG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS works (
    work_id VARCHAR PRIMARY KEY,
    collection_id VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    author_id VARCHAR,
    source_id VARCHAR NOT NULL,
    cts_work_urn VARCHAR
);

CREATE TABLE IF NOT EXISTS editions (
    edition_id VARCHAR PRIMARY KEY,
    work_id VARCHAR NOT NULL,
    label VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    cts_edition_urn VARCHAR
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id VARCHAR PRIMARY KEY,
    work_id VARCHAR NOT NULL,
    edition_id VARCHAR NOT NULL,
    artifact_path VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    adapter VARCHAR NOT NULL,
    source_hash VARCHAR NOT NULL,
    segment_count INTEGER NOT NULL,
    token_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS aliases (
    alias VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    display VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    sources VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS source_files (
    collection_id VARCHAR NOT NULL,
    source_path VARCHAR PRIMARY KEY,
    file_role VARCHAR NOT NULL,
    file_status VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    source_hash VARCHAR,
    size_bytes BIGINT
);

CREATE TABLE IF NOT EXISTS source_metadata (
    collection_id VARCHAR NOT NULL,
    subject_kind VARCHAR NOT NULL,
    subject_id VARCHAR NOT NULL,
    key VARCHAR NOT NULL,
    value TEXT NOT NULL,
    source_path VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS metadata_overlays (
    collection_id VARCHAR NOT NULL,
    match_field VARCHAR NOT NULL,
    match_value VARCHAR NOT NULL,
    field VARCHAR NOT NULL,
    value TEXT NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);

CREATE TABLE IF NOT EXISTS metadata_attributions (
    collection_id VARCHAR NOT NULL,
    match_field VARCHAR NOT NULL,
    match_value VARCHAR NOT NULL,
    relation_type VARCHAR NOT NULL,
    agent TEXT NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);

CREATE TABLE IF NOT EXISTS contained_works (
    contained_work_id VARCHAR NOT NULL,
    parent_work_id VARCHAR NOT NULL,
    collection_id VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    cts_work_urn VARCHAR,
    start_citation VARCHAR NOT NULL,
    end_citation VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);

CREATE INDEX IF NOT EXISTS works_language_idx ON works(language);
CREATE INDEX IF NOT EXISTS works_collection_idx ON works(collection_id);
CREATE INDEX IF NOT EXISTS artifacts_work_idx ON artifacts(work_id);
CREATE INDEX IF NOT EXISTS artifacts_edition_idx ON artifacts(edition_id);
CREATE INDEX IF NOT EXISTS aliases_alias_idx ON aliases(language, alias);
CREATE INDEX IF NOT EXISTS source_files_collection_idx ON source_files(collection_id);
CREATE INDEX IF NOT EXISTS source_metadata_subject_idx
    ON source_metadata(collection_id, subject_kind, subject_id);
CREATE INDEX IF NOT EXISTS metadata_overlays_match_idx
    ON metadata_overlays(collection_id, match_field, match_value);
CREATE INDEX IF NOT EXISTS metadata_attributions_match_idx
    ON metadata_attributions(collection_id, match_field, match_value);
CREATE INDEX IF NOT EXISTS metadata_attributions_agent_idx
    ON metadata_attributions(agent);
CREATE INDEX IF NOT EXISTS contained_works_parent_idx ON contained_works(parent_work_id);
CREATE INDEX IF NOT EXISTS contained_works_language_idx ON contained_works(language);
"""

BOOK_TABLE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS segments (
    segment_id VARCHAR PRIMARY KEY,
    work_id VARCHAR NOT NULL,
    edition_id VARCHAR NOT NULL,
    segment_kind VARCHAR NOT NULL,
    citation_path VARCHAR NOT NULL,
    text TEXT NOT NULL,
    source_text TEXT,
    normalized_text TEXT NOT NULL,
    sort_key INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS addresses (
    address VARCHAR PRIMARY KEY,
    segment_id VARCHAR NOT NULL,
    address_kind VARCHAR NOT NULL,
    citation_path VARCHAR NOT NULL
);
"""

BOOK_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS segments_sort_idx ON segments(sort_key);
CREATE INDEX IF NOT EXISTS addresses_segment_idx ON addresses(segment_id);
"""


def _connect(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def create_catalog_db(path: Path) -> None:
    with _connect(path) as conn:
        conn.execute(CATALOG_SCHEMA_SQL)


def create_book_db(path: Path) -> None:
    with _connect(path) as conn:
        conn.execute(BOOK_TABLE_SCHEMA_SQL)
        conn.execute(BOOK_INDEX_SQL)
        _ensure_book_schema(conn)


def _ensure_book_schema(conn: duckdb.DuckDBPyConnection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info('segments')").fetchall()}
    if "source_text" not in columns:
        conn.execute("ALTER TABLE segments ADD COLUMN source_text TEXT")


@dataclass(frozen=True)
class ReaderBookRegistration:
    work: ReaderWork
    edition: ReaderEdition
    artifact: ReaderBookArtifact


def register_book(
    catalog_path: Path,
    work: ReaderWork,
    edition: ReaderEdition,
    artifact: ReaderBookArtifact,
) -> None:
    register_books(catalog_path, [(work, edition, artifact)])


def register_books(
    catalog_path: Path,
    entries: Iterable[
        ReaderBookRegistration | tuple[ReaderWork, ReaderEdition, ReaderBookArtifact]
    ],
) -> None:
    normalized_entries = [
        (
            entry.work,
            entry.edition,
            entry.artifact,
        )
        if isinstance(entry, ReaderBookRegistration)
        else entry
        for entry in entries
    ]
    if not normalized_entries:
        return
    normalized_entries = _dedupe_book_registrations(normalized_entries)
    create_catalog_db(catalog_path)
    work_rows = [
        (
            work.work_id,
            work.collection_id,
            work.language,
            work.title,
            work.author,
            work.author_id,
            work.source_id,
            work.cts_work_urn,
        )
        for work, _edition, _artifact in normalized_entries
    ]
    edition_rows = [
        (
            edition.edition_id,
            edition.work_id,
            edition.label,
            edition.language,
            str(edition.source_path),
            edition.cts_edition_urn,
        )
        for _work, edition, _artifact in normalized_entries
    ]
    artifact_rows = [
        (
            artifact.artifact_id,
            artifact.work_id,
            artifact.edition_id,
            str(artifact.artifact_path),
            str(artifact.source_path),
            artifact.adapter,
            artifact.source_hash,
            artifact.segment_count,
            artifact.token_count,
        )
        for _work, _edition, artifact in normalized_entries
    ]
    with _connect(catalog_path) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            work_frame = pl.DataFrame(
                work_rows,
                schema={
                    "work_id": pl.Utf8,
                    "collection_id": pl.Utf8,
                    "language": pl.Utf8,
                    "title": pl.Utf8,
                    "author": pl.Utf8,
                    "author_id": pl.Utf8,
                    "source_id": pl.Utf8,
                    "cts_work_urn": pl.Utf8,
                },
                orient="row",
            )
            edition_frame = pl.DataFrame(
                edition_rows,
                schema={
                    "edition_id": pl.Utf8,
                    "work_id": pl.Utf8,
                    "label": pl.Utf8,
                    "language": pl.Utf8,
                    "source_path": pl.Utf8,
                    "cts_edition_urn": pl.Utf8,
                },
                orient="row",
            )
            artifact_frame = pl.DataFrame(
                artifact_rows,
                schema={
                    "artifact_id": pl.Utf8,
                    "work_id": pl.Utf8,
                    "edition_id": pl.Utf8,
                    "artifact_path": pl.Utf8,
                    "source_path": pl.Utf8,
                    "adapter": pl.Utf8,
                    "source_hash": pl.Utf8,
                    "segment_count": pl.Int64,
                    "token_count": pl.Int64,
                },
                orient="row",
            )
            conn.register("work_rows", work_frame)
            conn.register("edition_rows", edition_frame)
            conn.register("artifact_rows", artifact_frame)
            conn.execute("DELETE FROM works WHERE work_id IN (SELECT work_id FROM work_rows)")
            conn.execute(
                "DELETE FROM editions WHERE edition_id IN (SELECT edition_id FROM edition_rows)"
            )
            conn.execute(
                "DELETE FROM artifacts WHERE artifact_id IN (SELECT artifact_id FROM artifact_rows)"
            )
            conn.execute(
                """
                INSERT INTO works (
                    work_id, collection_id, language, title, author, author_id,
                    source_id, cts_work_urn
                )
                SELECT
                    work_id, collection_id, language, title, author, author_id,
                    source_id, cts_work_urn
                FROM work_rows
                """
            )
            conn.execute(
                """
                INSERT INTO editions (
                    edition_id, work_id, label, language, source_path, cts_edition_urn
                )
                SELECT edition_id, work_id, label, language, source_path, cts_edition_urn
                FROM edition_rows
                """
            )
            conn.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, work_id, edition_id, artifact_path, source_path, adapter,
                    source_hash, segment_count, token_count
                )
                SELECT
                    artifact_id, work_id, edition_id, artifact_path, source_path, adapter,
                    source_hash, segment_count, token_count
                FROM artifact_rows
                """
            )
            conn.unregister("work_rows")
            conn.unregister("edition_rows")
            conn.unregister("artifact_rows")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def _dedupe_book_registrations(
    entries: list[tuple[ReaderWork, ReaderEdition, ReaderBookArtifact]],
) -> list[tuple[ReaderWork, ReaderEdition, ReaderBookArtifact]]:
    by_work_id: dict[str, tuple[ReaderWork, ReaderEdition, ReaderBookArtifact]] = {}
    by_edition_id: dict[str, str] = {}
    by_artifact_id: dict[str, str] = {}
    for entry in entries:
        work, edition, artifact = entry
        old_work_id = by_edition_id.get(edition.edition_id)
        if old_work_id is not None and old_work_id != work.work_id:
            by_work_id.pop(old_work_id, None)
        old_work_id = by_artifact_id.get(artifact.artifact_id)
        if old_work_id is not None and old_work_id != work.work_id:
            by_work_id.pop(old_work_id, None)
        by_work_id[work.work_id] = entry
        by_edition_id[edition.edition_id] = work.work_id
        by_artifact_id[artifact.artifact_id] = work.work_id
    return list(by_work_id.values())


def register_segment_rows(
    book_path: Path,
    *,
    segments: Iterable[ReaderSegment],
    addresses: Iterable[ReaderSegmentAddress],
    replace_work_id: str | None = None,
) -> None:
    segment_rows = [
        (
            segment.segment_id,
            segment.work_id,
            segment.edition_id,
            segment.segment_kind,
            segment.citation_path,
            segment.text,
            segment.source_text,
            segment.normalized_text,
            segment.sort_key,
        )
        for segment in segments
    ]
    address_rows = [
        (
            address.address,
            address.segment_id,
            address.address_kind,
            address.citation_path,
        )
        for address in addresses
    ]
    with _connect(book_path) as conn:
        conn.execute(BOOK_TABLE_SCHEMA_SQL)
        _ensure_book_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            if replace_work_id is None:
                conn.execute("DELETE FROM segments")
                conn.execute("DELETE FROM addresses")
            else:
                conn.execute(
                    """
                    DELETE FROM addresses
                    WHERE segment_id IN (
                        SELECT segment_id FROM segments WHERE work_id = ?
                    )
                    """,
                    [replace_work_id],
                )
                conn.execute("DELETE FROM segments WHERE work_id = ?", [replace_work_id])
            if segment_rows:
                segment_frame = pl.DataFrame(
                    segment_rows,
                    schema={
                        "segment_id": pl.Utf8,
                        "work_id": pl.Utf8,
                        "edition_id": pl.Utf8,
                        "segment_kind": pl.Utf8,
                        "citation_path": pl.Utf8,
                        "text": pl.Utf8,
                        "source_text": pl.Utf8,
                        "normalized_text": pl.Utf8,
                        "sort_key": pl.Int64,
                    },
                    orient="row",
                )
                conn.register("segment_rows", segment_frame)
                conn.execute(
                    """
                    INSERT INTO segments (
                        segment_id, work_id, edition_id, segment_kind, citation_path,
                        text, source_text, normalized_text, sort_key
                    )
                    SELECT
                        segment_id, work_id, edition_id, segment_kind, citation_path,
                        text, source_text, normalized_text, sort_key
                    FROM segment_rows
                    """,
                )
                conn.unregister("segment_rows")
            if address_rows:
                address_frame = pl.DataFrame(
                    address_rows,
                    schema={
                        "address": pl.Utf8,
                        "segment_id": pl.Utf8,
                        "address_kind": pl.Utf8,
                        "citation_path": pl.Utf8,
                    },
                    orient="row",
                )
                conn.register("address_rows", address_frame)
                conn.execute(
                    """
                    INSERT INTO addresses (address, segment_id, address_kind, citation_path)
                    SELECT address, segment_id, address_kind, citation_path
                    FROM address_rows
                    """,
                )
                conn.unregister("address_rows")
            conn.execute(BOOK_INDEX_SQL)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def register_aliases(catalog_path: Path, aliases: Iterable[ReaderAlias]) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            alias.alias,
            alias.language,
            alias.kind,
            alias.target,
            alias.display,
            alias.source_file,
            ",".join(alias.sources),
        )
        for alias in aliases
    ]
    with _connect(catalog_path) as conn:
        conn.execute("DELETE FROM aliases")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "alias": pl.Utf8,
                    "language": pl.Utf8,
                    "kind": pl.Utf8,
                    "target": pl.Utf8,
                    "display": pl.Utf8,
                    "source_file": pl.Utf8,
                    "sources": pl.Utf8,
                },
                orient="row",
            )
            conn.register("alias_rows", frame)
            conn.execute(
                """
                INSERT INTO aliases (
                    alias, language, kind, target, display, source_file, sources
                )
                SELECT alias, language, kind, target, display, source_file, sources
                FROM alias_rows
                """,
            )
            conn.unregister("alias_rows")


def register_metadata_overlays(
    catalog_path: Path,
    overlays: Iterable[ReaderMetadataOverlay],
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            overlay.collection_id,
            overlay.match_field,
            overlay.match_value,
            overlay.field,
            overlay.value,
            overlay.status,
            overlay.confidence,
            overlay.note,
            overlay.source_file,
            evidence.source_type,
            evidence.citation,
            evidence.label,
            evidence.retrieved_at,
        )
        for overlay in overlays
        for evidence in overlay.evidence
    ]
    with _connect(catalog_path) as conn:
        conn.execute("DELETE FROM metadata_overlays")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "collection_id": pl.Utf8,
                    "match_field": pl.Utf8,
                    "match_value": pl.Utf8,
                    "field": pl.Utf8,
                    "value": pl.Utf8,
                    "status": pl.Utf8,
                    "confidence": pl.Utf8,
                    "note": pl.Utf8,
                    "source_file": pl.Utf8,
                    "evidence_source_type": pl.Utf8,
                    "evidence_citation": pl.Utf8,
                    "evidence_label": pl.Utf8,
                    "evidence_retrieved_at": pl.Utf8,
                },
                orient="row",
            )
            conn.register("metadata_overlay_rows", frame)
            conn.execute(
                """
                INSERT INTO metadata_overlays (
                    collection_id, match_field, match_value, field, value, status,
                    confidence, note, source_file, evidence_source_type, evidence_citation,
                    evidence_label, evidence_retrieved_at
                )
                SELECT
                    collection_id, match_field, match_value, field, value, status,
                    confidence, note, source_file, evidence_source_type, evidence_citation,
                    evidence_label, evidence_retrieved_at
                FROM metadata_overlay_rows
                """,
            )
            conn.unregister("metadata_overlay_rows")


def register_metadata_attributions(
    catalog_path: Path,
    attributions: Iterable[ReaderMetadataAttribution],
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            attribution.collection_id,
            attribution.match_field,
            attribution.match_value,
            attribution.relation_type,
            attribution.agent,
            attribution.status,
            attribution.confidence,
            attribution.note,
            attribution.source_file,
            evidence.source_type,
            evidence.citation,
            evidence.label,
            evidence.retrieved_at,
        )
        for attribution in attributions
        for evidence in attribution.evidence
    ]
    with _connect(catalog_path) as conn:
        conn.execute("DELETE FROM metadata_attributions")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "collection_id": pl.Utf8,
                    "match_field": pl.Utf8,
                    "match_value": pl.Utf8,
                    "relation_type": pl.Utf8,
                    "agent": pl.Utf8,
                    "status": pl.Utf8,
                    "confidence": pl.Utf8,
                    "note": pl.Utf8,
                    "source_file": pl.Utf8,
                    "evidence_source_type": pl.Utf8,
                    "evidence_citation": pl.Utf8,
                    "evidence_label": pl.Utf8,
                    "evidence_retrieved_at": pl.Utf8,
                },
                orient="row",
            )
            conn.register("metadata_attribution_rows", frame)
            conn.execute(
                """
                INSERT INTO metadata_attributions (
                    collection_id, match_field, match_value, relation_type, agent,
                    status, confidence, note, source_file, evidence_source_type,
                    evidence_citation, evidence_label, evidence_retrieved_at
                )
                SELECT
                    collection_id, match_field, match_value, relation_type, agent,
                    status, confidence, note, source_file, evidence_source_type,
                    evidence_citation, evidence_label, evidence_retrieved_at
                FROM metadata_attribution_rows
                """,
            )
            conn.unregister("metadata_attribution_rows")


def register_contained_works(
    catalog_path: Path,
    contained_works: Iterable[ReaderContainedWork],
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            work.contained_work_id,
            work.parent_work_id,
            work.collection_id,
            work.language,
            work.title,
            work.author,
            work.source_id,
            work.cts_work_urn,
            work.start_citation,
            work.end_citation,
            work.status,
            work.confidence,
            work.note,
            work.source_file,
            evidence.source_type,
            evidence.citation,
            evidence.label,
            evidence.retrieved_at,
        )
        for work in contained_works
        for evidence in work.evidence
    ]
    with _connect(catalog_path) as conn:
        conn.execute("DROP TABLE IF EXISTS contained_works")
        conn.execute(
            """
            CREATE TABLE contained_works (
                contained_work_id VARCHAR NOT NULL,
                parent_work_id VARCHAR NOT NULL,
                collection_id VARCHAR NOT NULL,
                language VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                author VARCHAR NOT NULL,
                source_id VARCHAR NOT NULL,
                cts_work_urn VARCHAR,
                start_citation VARCHAR NOT NULL,
                end_citation VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                confidence VARCHAR NOT NULL,
                note TEXT NOT NULL,
                source_file VARCHAR NOT NULL,
                evidence_source_type VARCHAR NOT NULL,
                evidence_citation TEXT NOT NULL,
                evidence_label TEXT NOT NULL,
                evidence_retrieved_at VARCHAR
            )
            """
        )
        conn.execute("DELETE FROM contained_works")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "contained_work_id": pl.Utf8,
                    "parent_work_id": pl.Utf8,
                    "collection_id": pl.Utf8,
                    "language": pl.Utf8,
                    "title": pl.Utf8,
                    "author": pl.Utf8,
                    "source_id": pl.Utf8,
                    "cts_work_urn": pl.Utf8,
                    "start_citation": pl.Utf8,
                    "end_citation": pl.Utf8,
                    "status": pl.Utf8,
                    "confidence": pl.Utf8,
                    "note": pl.Utf8,
                    "source_file": pl.Utf8,
                    "evidence_source_type": pl.Utf8,
                    "evidence_citation": pl.Utf8,
                    "evidence_label": pl.Utf8,
                    "evidence_retrieved_at": pl.Utf8,
                },
                orient="row",
            )
            conn.register("contained_work_rows", frame)
            conn.execute(
                """
                INSERT INTO contained_works (
                    contained_work_id, parent_work_id, collection_id, language, title,
                    author, source_id, cts_work_urn, start_citation, end_citation,
                    status, confidence, note, source_file, evidence_source_type,
                    evidence_citation, evidence_label, evidence_retrieved_at
                )
                SELECT
                    contained_work_id, parent_work_id, collection_id, language, title,
                    author, source_id, cts_work_urn, start_citation, end_citation,
                    status, confidence, note, source_file, evidence_source_type,
                    evidence_citation, evidence_label, evidence_retrieved_at
                FROM contained_work_rows
                """
            )
            conn.unregister("contained_work_rows")


def register_source_files(catalog_path: Path, source_files: Iterable[ReaderSourceFile]) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            source_file.collection_id,
            str(source_file.source_path),
            source_file.file_role,
            source_file.file_status,
            source_file.source_id,
            source_file.source_hash,
            source_file.size_bytes,
        )
        for source_file in source_files
    ]
    if not rows:
        return
    with _connect(catalog_path) as conn:
        frame = pl.DataFrame(
            rows,
            schema={
                "collection_id": pl.Utf8,
                "source_path": pl.Utf8,
                "file_role": pl.Utf8,
                "file_status": pl.Utf8,
                "source_id": pl.Utf8,
                "source_hash": pl.Utf8,
                "size_bytes": pl.Int64,
            },
            orient="row",
        )
        conn.register("source_file_rows", frame)
        conn.execute(
            """
            DELETE FROM source_files
            WHERE source_path IN (SELECT source_path FROM source_file_rows)
            """
        )
        conn.execute(
            """
            INSERT INTO source_files (
                collection_id, source_path, file_role, file_status,
                source_id, source_hash, size_bytes
            )
            SELECT
                collection_id, source_path, file_role, file_status,
                source_id, source_hash, size_bytes
            FROM source_file_rows
            """,
        )
        conn.unregister("source_file_rows")


def register_source_metadata(
    catalog_path: Path,
    metadata_rows: Iterable[ReaderSourceMetadata],
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            row.collection_id,
            row.subject_kind,
            row.subject_id,
            row.key,
            row.value,
            str(row.source_path),
        )
        for row in metadata_rows
    ]
    if not rows:
        return
    with _connect(catalog_path) as conn:
        frame = pl.DataFrame(
            rows,
            schema={
                "collection_id": pl.Utf8,
                "subject_kind": pl.Utf8,
                "subject_id": pl.Utf8,
                "key": pl.Utf8,
                "value": pl.Utf8,
                "source_path": pl.Utf8,
            },
            orient="row",
        )
        conn.register("source_metadata_rows", frame)
        conn.execute(
            """
            DELETE FROM source_metadata
            WHERE source_path IN (SELECT DISTINCT source_path FROM source_metadata_rows)
            """
        )
        conn.execute(
            """
            INSERT INTO source_metadata (
                collection_id, subject_kind, subject_id, key, value, source_path
            )
            SELECT collection_id, subject_kind, subject_id, key, value, source_path
            FROM source_metadata_rows
            """,
        )
        conn.unregister("source_metadata_rows")


def _dict_rows(
    conn: duckdb.DuckDBPyConnection, query: str, params: list[object] | None = None
) -> list[dict[str, Any]]:
    cursor = conn.execute(query, params or [])
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _table_exists(conn: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = ?
        LIMIT 1
        """,
        [table_name],
    ).fetchone()
    return row is not None


def _catalog_artifacts(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            """
            SELECT artifact_id, work_id, edition_id, artifact_path, source_path, adapter,
                   source_hash, segment_count, token_count
            FROM artifacts
            ORDER BY work_id, edition_id, artifact_id
            """,
        )


def _contained_work(catalog_path: Path, work_ref: str) -> dict[str, Any] | None:
    if not catalog_path.exists():
        return None
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "contained_works"):
            return None
        rows = _dict_rows(
            conn,
            """
            SELECT DISTINCT
                contained_work_id, parent_work_id, collection_id, language, title, author,
                source_id, cts_work_urn, start_citation, end_citation, status, confidence,
                note, source_file
            FROM contained_works
            WHERE status = 'accepted'
              AND (contained_work_id = ? OR cts_work_urn = ?)
            ORDER BY CASE WHEN contained_work_id = ? THEN 0 ELSE 1 END, contained_work_id
            LIMIT 1
            """,
            [work_ref, work_ref, work_ref],
        )
    return rows[0] if rows else None


def _segment_sort_key_for_work(
    catalog_path: Path,
    work_id: str,
    citation_path: str,
) -> int | None:
    for artifact in _catalog_artifacts(catalog_path):
        if artifact["work_id"] != work_id:
            continue
        book_path = Path(str(artifact["artifact_path"]))
        if not book_path.exists():
            continue
        with duckdb.connect(str(book_path), read_only=True) as conn:
            sort_key = _segment_sort_key(conn, work_id, citation_path)
            if sort_key is not None:
                return sort_key
    return None


def _cts_work_id(address: str) -> str | None:
    if not address.startswith("urn:cts:") or ":" not in address:
        return None
    work_id, _sep, citation = address.rpartition(":")
    if not citation:
        return None
    return work_id


def _segment_address_parts(address: str) -> tuple[str, str] | None:
    work_ref, separator, citation_path = address.rpartition(":")
    if not separator or not work_ref or not citation_path:
        return None
    return work_ref, citation_path


def _address_lookup_candidates(catalog_path: Path, address: str) -> list[str]:
    candidates = [address]
    parts = _segment_address_parts(address)
    if parts is not None:
        work_ref, citation_path = parts
        resolved_work_id = resolve_work_ref(catalog_path, work_ref)
        if resolved_work_id:
            candidates.append(f"{resolved_work_id}:{citation_path}")
    return list(dict.fromkeys(candidates))


def _address_work_id_from_artifacts(address: str, artifacts: list[dict[str, Any]]) -> str | None:
    matches = {
        str(artifact["work_id"])
        for artifact in artifacts
        if address.startswith(f"{artifact['work_id']}:")
    }
    if not matches:
        return _cts_work_id(address)
    return max(matches, key=len)


def _book_has_address(book_path: Path, address: str) -> bool:
    if not book_path.exists():
        return False
    with duckdb.connect(str(book_path), read_only=True) as conn:
        row = conn.execute(
            "SELECT 1 FROM addresses WHERE address = ? LIMIT 1",
            [address],
        ).fetchone()
    return row is not None


def _segment_source_text_expr(conn: duckdb.DuckDBPyConnection) -> str:
    columns = {row[1] for row in conn.execute("PRAGMA table_info('segments')").fetchall()}
    return "s.source_text" if "source_text" in columns else "s.text AS source_text"


def _segment_sort_key(
    conn: duckdb.DuckDBPyConnection,
    work_id: str,
    citation_path: str,
) -> int | None:
    row = conn.execute(
        """
        SELECT sort_key
        FROM segments
        WHERE work_id = ? AND citation_path = ?
        ORDER BY sort_key
        LIMIT 1
        """,
        [work_id, citation_path],
    ).fetchone()
    return int(row[0]) if row else None


def lookup_artifact_for_address(catalog_path: Path, address: str) -> dict[str, Any] | None:
    result = _lookup_artifact_and_address_for_address(catalog_path, address)
    return result[0] if result is not None else None


def _lookup_artifact_and_address_for_address(
    catalog_path: Path, address: str
) -> tuple[dict[str, Any], str] | None:
    artifacts = _catalog_artifacts(catalog_path)
    candidates = _address_lookup_candidates(catalog_path, address)
    for candidate in candidates:
        work_id = _address_work_id_from_artifacts(candidate, artifacts)
        if work_id is not None:
            for artifact in artifacts:
                if artifact["work_id"] == work_id and _book_has_address(
                    Path(str(artifact["artifact_path"])),
                    candidate,
                ):
                    return artifact, candidate

    for candidate in candidates:
        for artifact in artifacts:
            if _book_has_address(Path(str(artifact["artifact_path"])), candidate):
                return artifact, candidate
    return None


def lookup_segment_by_address(catalog_path: Path, address: str) -> dict[str, Any] | None:
    result = _lookup_artifact_and_address_for_address(catalog_path, address)
    if result is None:
        return None
    artifact, query_address = result
    book_path = Path(str(artifact["artifact_path"]))
    if not book_path.exists():
        return None
    with duckdb.connect(str(book_path), read_only=True) as conn:
        source_text_expr = _segment_source_text_expr(conn)
        rows = _dict_rows(
            conn,
            f"""
            SELECT
                s.segment_id, s.work_id, s.edition_id, s.segment_kind, s.citation_path,
                s.text, {source_text_expr}, s.normalized_text, s.sort_key, a.address, a.address_kind
            FROM addresses a
            JOIN segments s ON s.segment_id = a.segment_id
            WHERE a.address = ?
            LIMIT 1
            """,
            [query_address],
        )
    if not rows:
        return None
    segment = {**rows[0], "artifact": artifact}
    if query_address != address:
        segment["stored_address"] = segment["address"]
        segment["address"] = address
    return segment


def lookup_alias(
    catalog_path: Path,
    alias: str,
    *,
    language: str | None = None,
) -> dict[str, Any] | None:
    if not catalog_path.exists():
        return None
    where = "alias = ? AND language = ?" if language else "alias = ?"
    params: list[object] = [alias, language] if language else [alias]
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = _dict_rows(
            conn,
            f"""
            SELECT alias, language, kind, target, display, source_file, sources
            FROM aliases
            WHERE {where}
            ORDER BY language, target
            LIMIT 1
            """,
            params,
        )
    return rows[0] if rows else None


def resolve_work_ref(catalog_path: Path, work_ref: str) -> str | None:
    alias = lookup_alias(catalog_path, work_ref)
    if alias is not None:
        target = alias.get("target")
        return str(target) if target is not None else None
    if not catalog_path.exists():
        return None
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        row = conn.execute(
            """
            SELECT work_id
            FROM works
            WHERE work_id = ? OR cts_work_urn = ?
            ORDER BY CASE WHEN work_id = ? THEN 0 ELSE 1 END, work_id
            LIMIT 1
            """,
            [work_ref, work_ref, work_ref],
        ).fetchone()
    return str(row[0]) if row else None


def resolve_text_work_ref(catalog_path: Path, work_ref: str) -> str | None:
    contained = _contained_work(catalog_path, work_ref)
    if contained is not None:
        return str(contained["parent_work_id"])
    return resolve_work_ref(catalog_path, work_ref)


def get_work(catalog_path: Path, work_ref: str) -> dict[str, Any] | None:
    contained = _contained_work(catalog_path, work_ref)
    if contained is not None:
        return {
            "work_id": contained["contained_work_id"],
            "collection_id": contained["collection_id"],
            "language": contained["language"],
            "title": contained["title"],
            "author": contained["author"],
            "author_id": None,
            "source_id": contained["source_id"],
            "cts_work_urn": contained["cts_work_urn"],
            "work_kind": "contained",
            "parent_work_id": contained["parent_work_id"],
            "start_citation": contained["start_citation"],
            "end_citation": contained["end_citation"],
            "confidence": contained["confidence"],
            "note": contained["note"],
        }
    work_id = resolve_work_ref(catalog_path, work_ref)
    if not work_id:
        return None
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = _dict_rows(
            conn,
            """
            SELECT
                work_id, collection_id, language, title, author, author_id, source_id,
                cts_work_urn
            FROM works
            WHERE work_id = ?
            LIMIT 1
            """,
            [work_id],
        )
    if not rows:
        return None
    return {**rows[0], "work_kind": "work"}


def lookup_segment_by_work_and_citation(
    catalog_path: Path,
    work_ref: str,
    citation_path: str,
) -> dict[str, Any] | None:
    work_id = resolve_text_work_ref(catalog_path, work_ref)
    if not work_id:
        return None
    for artifact in _catalog_artifacts(catalog_path):
        if artifact["work_id"] != work_id:
            continue
        book_path = Path(str(artifact["artifact_path"]))
        if not book_path.exists():
            continue
        with duckdb.connect(str(book_path), read_only=True) as conn:
            source_text_expr = _segment_source_text_expr(conn)
            rows = _dict_rows(
                conn,
                f"""
                SELECT
                    s.segment_id, s.work_id, s.edition_id, s.segment_kind, s.citation_path,
                    s.text, {source_text_expr}, s.normalized_text, s.sort_key
                FROM segments s
                WHERE s.work_id = ? AND s.citation_path = ?
                ORDER BY s.sort_key, s.segment_id
                LIMIT 1
                """,
                [work_id, citation_path],
            )
        if rows:
            address = f"{work_id}:{citation_path}"
            return {
                **rows[0],
                "address": address,
                "address_kind": "langnet",
                "artifact": artifact,
            }
    return None


def segment_navigation(catalog_path: Path, segment: dict[str, Any]) -> dict[str, Any]:
    work_id = str(segment["work_id"])
    sort_key = int(segment["sort_key"])
    artifact = segment.get("artifact")
    if not isinstance(artifact, dict):
        return {"previous": None, "next": None}
    book_path = Path(str(artifact["artifact_path"]))
    if not book_path.exists():
        return {"previous": None, "next": None}
    with duckdb.connect(str(book_path), read_only=True) as conn:
        previous_rows = _dict_rows(
            conn,
            """
            SELECT citation_path
            FROM segments
            WHERE work_id = ? AND sort_key < ?
            ORDER BY sort_key DESC, citation_path DESC
            LIMIT 1
            """,
            [work_id, sort_key],
        )
        next_rows = _dict_rows(
            conn,
            """
            SELECT citation_path
            FROM segments
            WHERE work_id = ? AND sort_key > ?
            ORDER BY sort_key, citation_path
            LIMIT 1
            """,
            [work_id, sort_key],
        )
    work = get_work(catalog_path, work_id)
    base_address = str(work.get("cts_work_urn")) if work and work.get("cts_work_urn") else work_id
    return {
        "previous": _navigation_item(previous_rows, base_address),
        "next": _navigation_item(next_rows, base_address),
    }


def _navigation_item(rows: list[dict[str, Any]], base_address: str) -> dict[str, str] | None:
    if not rows:
        return None
    citation_path = str(rows[0]["citation_path"])
    return {
        "citation_path": citation_path,
        "address": f"{base_address}:{citation_path}",
    }


def list_collections(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            """
            SELECT collection_id, COUNT(*) AS work_count
            FROM works
            GROUP BY collection_id
            ORDER BY collection_id
            """,
        )


def list_authors(
    catalog_path: Path,
    *,
    language: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if language:
        conditions.append("language = ?")
        params.append(language)
    if query:
        conditions.append("(lower(author) LIKE ? OR lower(coalesce(author_id, '')) LIKE ?)")
        params.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    limit_sql = "LIMIT ? OFFSET ?" if limit is not None else ""
    if limit is not None:
        params.extend([limit, offset])
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            f"""
            SELECT author_id, author, language, collection_id, COUNT(*) AS work_count
            FROM works
            {where}
            GROUP BY author_id, author, language, collection_id
            ORDER BY language, author, collection_id
            {limit_sql}
            """,
            params,
        )


def list_author_index(  # noqa: PLR0913
    catalog_path: Path,
    *,
    language: str | None = None,
    section: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    rows = _raw_author_rows(catalog_path, language=language)
    items = [author_index_entry(row) for row in rows]
    _disambiguate_duplicate_author_displays(catalog_path, items)
    if section:
        section_key = normalize_section_key(language, section)
        items = [item for item in items if item["section_key"] == section_key]
    if query:
        query_key = query.casefold()
        items = [
            item
            for item in items
            if query_key in str(item["index_name"]).casefold()
            or query_key in str(item["author_id"]).casefold()
            or query_key in str(item.get("source_author_id") or "").casefold()
            or any(query_key in str(name).casefold() for name in item["alternate_names"])
        ]
    items.sort(key=lambda item: (item["language"], item["sort_key"], item["display_name"]))
    if limit is None:
        return items[offset:]
    return items[offset : offset + limit]


def _disambiguate_duplicate_author_displays(
    catalog_path: Path,
    items: list[dict[str, Any]],
) -> None:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in items:
        key = (str(item["language"]), str(item["display_name"]).casefold())
        by_key.setdefault(key, []).append(item)
    canon_metadata_by_author_id = _tlg_canon_author_metadata(catalog_path)
    for group in by_key.values():
        author_ids = {str(item["author_id"]) for item in group}
        if len(author_ids) <= 1:
            continue
        used_labels: set[str] = set()
        for item in group:
            suffix = _author_disambiguation_suffix(item, canon_metadata_by_author_id)
            display = f"{item['display_name']} ({suffix})" if suffix else str(item["display_name"])
            while display.casefold() in used_labels:
                suffix = str(item.get("author_id") or suffix)
                display = f"{item['display_name']} ({suffix})"
            used_labels.add(display.casefold())
            item["display_name"] = display
            item["author"] = display
            item["sort_key"] = f"{item['sort_key']}:{display.casefold()}"


def _author_disambiguation_suffix(
    item: dict[str, Any],
    canon_metadata_by_author_id: dict[str, dict[str, str]],
) -> str:
    author_id = compact_author_id(str(item.get("source_author_id") or item.get("author_id") or ""))
    metadata = canon_metadata_by_author_id.get(author_id, {})
    label = _tlg_canon_author_name_label(
        str(item.get("index_name") or item.get("display_name") or ""),
        metadata.get("name", ""),
    )
    if label:
        return label
    category = metadata.get("category")
    if category:
        return category
    return author_id


def _tlg_canon_author_metadata(catalog_path: Path) -> dict[str, dict[str, str]]:
    if not catalog_path.exists():
        return {}
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "source_metadata"):
            return {}
        rows = conn.execute(
            """
            SELECT subject_id, key, value
            FROM source_metadata
            WHERE collection_id = 'tlg'
              AND subject_kind = 'author'
              AND key IN ('tlg_canon_author_name', 'tlg_canon_category')
              AND value IS NOT NULL
              AND trim(value) != ''
            ORDER BY subject_id, key
            """
        ).fetchall()
    names_by_author_id: dict[str, str] = {}
    categories_by_author_id: dict[str, str] = {}
    for subject_id, key, value in rows:
        author_id = compact_author_id(str(subject_id))
        if key == "tlg_canon_author_name":
            names_by_author_id[author_id] = str(value)
        elif key == "tlg_canon_category":
            categories_by_author_id[author_id] = str(value)
    metadata: dict[str, dict[str, str]] = {}
    for author_id, name in names_by_author_id.items():
        metadata.setdefault(author_id, {})["name"] = name
    for author_id, category in categories_by_author_id.items():
        metadata.setdefault(author_id, {})["category"] = category
    return metadata


def _tlg_canon_author_name_label(index_name: str, canon_name: str) -> str | None:
    index = " ".join(index_name.strip().split())
    canon = " ".join(canon_name.strip().split())
    if not index or not canon:
        return None
    if canon.casefold() == index.casefold():
        return None
    prefix = f"{index} "
    if canon.casefold().startswith(prefix.casefold()):
        label = canon[len(prefix) :].strip()
        if label:
            return label
    return None


def list_author_sections(
    catalog_path: Path,
    *,
    language: str,
) -> list[dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    for item in list_author_index(catalog_path, language=language):
        key = str(item["section_key"])
        section = sections.setdefault(
            key,
            {
                "key": key,
                "label": key,
                "native_label": key,
                "sort_key": author_section_sort_key(language, key),
                "author_count": 0,
                "work_count": 0,
            },
        )
        section["author_count"] = int(section["author_count"]) + 1
        section["work_count"] = int(section["work_count"]) + int(item["work_count"])
    return sorted(sections.values(), key=lambda section: str(section["sort_key"]))


def list_duplicate_audit(
    catalog_path: Path,
    *,
    kind: str = "authors",
    language: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if kind == "titles":
            return _dict_rows(
                conn,
                """
                WITH grouped AS (
                    SELECT
                        language,
                        lower(trim(title)) AS duplicate_key,
                        min(trim(title)) AS display,
                        COUNT(*) AS work_count,
                        COUNT(DISTINCT trim(author)) AS author_count,
                        list(DISTINCT trim(title) ORDER BY trim(title)) AS display_values,
                        list(work_id ORDER BY author, title, work_id) AS work_ids,
                        list(author ORDER BY author, title, work_id) AS authors
                    FROM works
                    WHERE (? IS NULL OR language = ?)
                      AND length(trim(title)) > 0
                    GROUP BY language, lower(trim(title))
                    HAVING COUNT(*) > 1
                )
                SELECT
                    'title' AS kind,
                    language,
                    duplicate_key,
                    display,
                    work_count,
                    author_count,
                    display_values,
                    work_ids,
                    authors,
                    CASE
                        WHEN author_count > 1 THEN 'preserve_title_disambiguate_by_author'
                        ELSE 'review_possible_edition_or_import_duplicate'
                    END AS suggested_policy
                FROM grouped
                ORDER BY work_count DESC, language, display
                LIMIT ?
                """,
                [language, language, limit],
            )
        return _dict_rows(
            conn,
            """
            WITH grouped AS (
                SELECT
                    language,
                    lower(trim(author)) AS duplicate_key,
                    min(trim(author)) AS display,
                    COUNT(*) AS work_count,
                    COUNT(DISTINCT coalesce(author_id, '')) AS authority_count,
                    list(DISTINCT trim(author) ORDER BY trim(author)) AS display_values,
                    list(DISTINCT coalesce(author_id, '') ORDER BY coalesce(author_id, ''))
                        AS author_ids,
                    list(work_id ORDER BY author, title, work_id) AS work_ids,
                    list(title ORDER BY author, title, work_id) AS titles
                FROM works
                WHERE (? IS NULL OR language = ?)
                  AND length(trim(author)) > 0
                GROUP BY language, lower(trim(author))
                HAVING COUNT(DISTINCT coalesce(author_id, '')) > 1
            )
            SELECT
                'author' AS kind,
                language,
                duplicate_key,
                display,
                work_count,
                authority_count,
                display_values,
                author_ids,
                work_ids,
                titles,
                'review_authority_collision' AS suggested_policy
            FROM grouped
            ORDER BY authority_count DESC, work_count DESC, language, display
            LIMIT ?
            """,
            [language, language, limit],
        )


def _raw_author_rows(
    catalog_path: Path,
    *,
    language: str | None = None,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if language:
        conditions.append("language = ?")
        params.append(language)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        contained_union = ""
        if _table_exists(conn, "contained_works"):
            contained_union = """
                UNION ALL
                SELECT
                    contained_work_id AS work_id,
                    '' AS source_author_id,
                    author,
                    language
                FROM contained_works
                WHERE status = 'accepted'
            """
        return _dict_rows(
            conn,
            f"""
            WITH author_work_rows AS (
                SELECT
                    work_id,
                    coalesce(author_id, '') AS source_author_id,
                    author,
                    language
                FROM works
                {contained_union}
            )
            SELECT
                source_author_id,
                author,
                language,
                COUNT(DISTINCT work_id) AS work_count
            FROM author_work_rows
            {where}
            GROUP BY source_author_id, author, language
            ORDER BY language, author
            """,
            params,
        )


AUTHORSHIP_RELATION_TYPES = (
    "attributed_author",
    "possible_author",
    "traditional_author",
    "misattributed_author",
)


def list_works(  # noqa: C901, PLR0912, PLR0913, PLR0915
    catalog_path: Path,
    *,
    language: str | None = None,
    collection_id: str | None = None,
    author: str | None = None,
    attributed_to: str | None = None,
    author_id: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    include_contained = collection_id is None or collection_id == "contained"
    conditions = []
    where_params: list[object] = []
    cte_params: list[object] = []
    if language:
        conditions.append("language = ?")
        where_params.append(language)
    if collection_id and collection_id != "contained":
        conditions.append("collection_id = ?")
        where_params.append(collection_id)
    if author:
        conditions.append("lower(author) LIKE ?")
        where_params.append(f"%{author.lower()}%")
        if not author.lower().startswith("pseudo"):
            conditions.append("lower(author) NOT LIKE 'pseudo-%'")
    filter_author_selector = is_synthetic_author_selector(author_id)
    if author_id and not filter_author_selector:
        author_id_key = author_id.casefold()
        conditions.append(
            """
            (
                lower(coalesce(author_id, '')) = ?
                OR lower(coalesce(author_id, '')) LIKE ?
                OR lower(source_id) LIKE ?
            )
            """
        )
        where_params.extend([author_id_key, f"%:{author_id_key}", f"{author_id_key}.%"])
    if query:
        query_like = f"%{query.lower()}%"
        conditions.append(
            """
            (
                lower(title) LIKE ?
                OR lower(author) LIKE ?
                OR lower(work_id) LIKE ?
                OR lower(source_id) LIKE ?
                OR lower(coalesce(cts_work_urn, '')) LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM aliases al
                    WHERE (al.target = works.work_id OR al.target = works.cts_work_urn)
                      AND (lower(al.alias) LIKE ? OR lower(al.display) LIKE ?)
                )
            )
            """
        )
        where_params.extend([query_like] * 7)
    attribution_cte = ""
    if attributed_to:
        attribution_cte = """
            WITH attribution_work_ids AS (
                SELECT DISTINCT w.work_id
                FROM works w
                JOIN metadata_attributions a ON (
                    (a.match_field = 'work_id' AND a.match_value = w.work_id)
                    OR (a.match_field = 'source_id' AND a.match_value = w.source_id)
                    OR (
                        a.match_field = 'cts_work_urn'
                        AND w.cts_work_urn IS NOT NULL
                        AND a.match_value = w.cts_work_urn
                    )
                )
                WHERE a.status = 'accepted'
                  AND a.relation_type IN (?, ?, ?, ?)
                  AND lower(a.agent) LIKE ?
            )
        """
        attribution_params = [*AUTHORSHIP_RELATION_TYPES, f"%{attributed_to.lower()}%"]
        cte_params.extend(attribution_params)
        conditions.append(
            "((lower(author) LIKE ?"
            + (
                ""
                if attributed_to.lower().startswith("pseudo")
                else " AND lower(author) NOT LIKE 'pseudo-%'"
            )
            + ") OR work_id IN (SELECT work_id FROM attribution_work_ids))"
        )
        where_params.append(f"%{attributed_to.lower()}%")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    should_limit_base_query = (
        limit is not None and not filter_author_selector and not include_contained
    )
    limit_sql = "LIMIT ? OFFSET ?" if should_limit_base_query else ""
    if should_limit_base_query:
        where_params.extend([limit, offset])
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if attributed_to and not _table_exists(conn, "metadata_attributions"):
            attribution_cte = """
                WITH attribution_work_ids AS (
                    SELECT NULL::VARCHAR AS work_id WHERE false
                )
            """
            cte_params = []
        rows = _dict_rows(
            conn,
            f"""
            {attribution_cte}
            SELECT
                work_id, collection_id, language, title, author, author_id, source_id,
                cts_work_urn, 'work' AS work_kind, NULL::VARCHAR AS parent_work_id,
                NULL::VARCHAR AS start_citation, NULL::VARCHAR AS end_citation
            FROM works
            {where}
            ORDER BY language, author, title, work_id
            {limit_sql}
            """,
            [*cte_params, *where_params],
        )
    if filter_author_selector and author_id:
        rows = [
            row
            for row in rows
            if author_selector_matches(
                selector=author_id,
                language=str(row.get("language") or ""),
                source_author_id=(
                    str(row["author_id"]) if row.get("author_id") is not None else None
                ),
                author=str(row.get("author") or ""),
            )
        ]
        if not include_contained:
            rows = rows[offset:]
        if limit is not None and not include_contained:
            rows = rows[:limit]
    if include_contained:
        rows.extend(
            _list_contained_work_rows(
                catalog_path,
                language=language,
                author=author,
                author_id=author_id,
                query=query,
            )
        )
        rows.sort(
            key=lambda row: (
                str(row.get("language") or ""),
                str(row.get("author") or ""),
                str(row.get("title") or ""),
                str(row.get("work_id") or ""),
            )
        )
        rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
    return rows


def _list_contained_work_rows(
    catalog_path: Path,
    *,
    language: str | None = None,
    author: str | None = None,
    author_id: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    if author_id and not is_synthetic_author_selector(author_id):
        return []
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "contained_works"):
            return []
        conditions = ["status = 'accepted'"]
        params: list[object] = []
        if language:
            conditions.append("language = ?")
            params.append(language)
        if author:
            conditions.append("lower(author) LIKE ?")
            params.append(f"%{author.lower()}%")
        if query:
            query_like = f"%{query.lower()}%"
            conditions.append(
                """
                (
                    lower(title) LIKE ?
                    OR lower(author) LIKE ?
                    OR lower(contained_work_id) LIKE ?
                    OR lower(source_id) LIKE ?
                    OR lower(coalesce(cts_work_urn, '')) LIKE ?
                )
                """
            )
            params.extend([query_like] * 5)
        where = " AND ".join(conditions)
        rows = _dict_rows(
            conn,
            f"""
            SELECT DISTINCT
                contained_work_id AS work_id,
                collection_id,
                language,
                title,
                author,
                NULL::VARCHAR AS author_id,
                source_id,
                cts_work_urn,
                'contained' AS work_kind,
                parent_work_id,
                start_citation,
                end_citation
            FROM contained_works
            WHERE {where}
            ORDER BY language, author, title, contained_work_id
            """,
            params,
        )
    if author_id:
        rows = [
            row
            for row in rows
            if author_selector_matches(
                selector=author_id,
                language=str(row.get("language") or ""),
                source_author_id=None,
                author=str(row.get("author") or ""),
            )
        ]
    return rows


def list_segments_for_work(  # noqa: PLR0913
    catalog_path: Path,
    work_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    from_citation: str | None = None,
    around: str | None = None,
    radius: int = 20,
) -> list[dict[str, Any]]:
    contained = _contained_work(catalog_path, work_id)
    resolved_work_id = (
        str(contained["parent_work_id"])
        if contained is not None
        else resolve_work_ref(catalog_path, work_id) or work_id
    )
    artifacts = [
        artifact
        for artifact in _catalog_artifacts(catalog_path)
        if artifact["work_id"] == resolved_work_id
    ]
    rows: list[dict[str, Any]] = []
    for artifact in artifacts:
        book_path = Path(str(artifact["artifact_path"]))
        if not book_path.exists():
            continue
        with duckdb.connect(str(book_path), read_only=True) as conn:
            if around:
                rows.extend(
                    _dict_rows(
                        conn,
                        """
                        WITH ordered AS (
                            SELECT
                                segment_id, work_id, edition_id, segment_kind, citation_path,
                                text, normalized_text, sort_key,
                                row_number() OVER (ORDER BY sort_key, citation_path) AS rn
                            FROM segments
                            WHERE work_id = ?
                        ),
                        anchor AS (
                            SELECT rn
                            FROM ordered
                            WHERE citation_path = ?
                            LIMIT 1
                        )
                        SELECT
                            segment_id, work_id, edition_id, segment_kind, citation_path,
                            text, normalized_text, sort_key
                        FROM ordered, anchor
                        WHERE ordered.rn BETWEEN anchor.rn - ? AND anchor.rn + ?
                        ORDER BY sort_key, citation_path
                        LIMIT ?
                        """,
                        [resolved_work_id, around, radius, radius, (radius * 2) + 1],
                    )
                )
                if len(rows) >= (radius * 2) + 1:
                    return rows[: (radius * 2) + 1]
                continue
            conditions = ["work_id = ?"]
            params: list[object] = [resolved_work_id]
            query_offset = offset
            query_limit = limit
            if contained is not None:
                start_sort_key = _segment_sort_key(
                    conn,
                    resolved_work_id,
                    str(contained["start_citation"]),
                )
                end_sort_key = _segment_sort_key(
                    conn,
                    resolved_work_id,
                    str(contained["end_citation"]),
                )
                if start_sort_key is None or end_sort_key is None:
                    continue
                conditions.append("sort_key BETWEEN ? AND ?")
                params.extend([start_sort_key, end_sort_key])
                query_offset = offset
            if from_citation:
                anchor_sort_key = _segment_sort_key(conn, resolved_work_id, from_citation)
                if anchor_sort_key is None:
                    continue
                conditions.append("sort_key >= ?")
                params.append(anchor_sort_key)
                query_offset = 0
            where = " AND ".join(conditions)
            params.extend([query_limit, query_offset])
            rows.extend(
                _dict_rows(
                    conn,
                    f"""
                    SELECT segment_id, work_id, edition_id, segment_kind, citation_path,
                           text, normalized_text, sort_key
                    FROM segments
                    WHERE {where}
                    ORDER BY sort_key, citation_path
                    LIMIT ? OFFSET ?
                    """,
                    params,
                )
            )
        if len(rows) >= limit:
            return rows[:limit]
    return rows


def list_aliases(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            """
            SELECT alias, language, kind, target, display, source_file, sources
            FROM aliases
            ORDER BY language, alias, target
            """,
        )


def list_alias_conflicts(catalog_path: Path) -> list[dict[str, Any]]:
    aliases = list_aliases(catalog_path)
    targets_by_key: dict[tuple[str, str], list[str]] = {}
    for alias in aliases:
        key = (str(alias["language"]), str(alias["alias"]))
        target = str(alias["target"])
        targets_by_key.setdefault(key, [])
        if target not in targets_by_key[key]:
            targets_by_key[key].append(target)
    return [
        {"language": language, "alias": alias, "targets": targets}
        for (language, alias), targets in sorted(targets_by_key.items())
        if len(targets) > 1
    ]


def list_metadata_overlays(  # noqa: PLR0913
    catalog_path: Path,
    *,
    collection_id: str | None = None,
    status: str | None = None,
    field: str | None = None,
    match_value: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if collection_id:
        conditions.append("collection_id = ?")
        params.append(collection_id)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if field:
        conditions.append("field = ?")
        params.append(field)
    if match_value:
        conditions.append("match_value = ?")
        params.append(match_value)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "metadata_overlays"):
            return []
        return _dict_rows(
            conn,
            f"""
            SELECT collection_id, match_field, match_value, field, value, status,
                   confidence, note, source_file, evidence_source_type, evidence_citation,
                   evidence_label, evidence_retrieved_at
            FROM metadata_overlays
            {where}
            ORDER BY collection_id, match_field, match_value, field, status, evidence_citation
            LIMIT ?
            """,
            params,
        )


def list_metadata_attributions(  # noqa: PLR0913
    catalog_path: Path,
    *,
    collection_id: str | None = None,
    status: str | None = None,
    relation_type: str | None = None,
    agent: str | None = None,
    match_value: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if collection_id:
        conditions.append("collection_id = ?")
        params.append(collection_id)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if relation_type:
        conditions.append("relation_type = ?")
        params.append(relation_type)
    if agent:
        conditions.append("agent = ?")
        params.append(agent)
    if match_value:
        conditions.append("match_value = ?")
        params.append(match_value)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "metadata_attributions"):
            return []
        return _dict_rows(
            conn,
            f"""
            SELECT collection_id, match_field, match_value, relation_type, agent,
                   status, confidence, note, source_file,
                   arg_min(evidence_source_type, evidence_citation) AS evidence_source_type,
                   min(evidence_citation) AS evidence_citation,
                   arg_min(evidence_label, evidence_citation) AS evidence_label,
                   arg_min(evidence_retrieved_at, evidence_citation) AS evidence_retrieved_at
            FROM metadata_attributions
            {where}
            GROUP BY collection_id, match_field, match_value, relation_type, agent,
                     status, confidence, note, source_file
            ORDER BY collection_id, match_field, match_value, relation_type, agent,
                     status, evidence_citation
            LIMIT ?
            """,
            params,
        )


def list_source_files(
    catalog_path: Path,
    *,
    collection_id: str | None = None,
    file_status: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if collection_id:
        conditions.append("collection_id = ?")
        params.append(collection_id)
    if file_status:
        conditions.append("file_status = ?")
        params.append(file_status)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            f"""
            SELECT collection_id, source_id, file_role, file_status, source_path,
                   source_hash, size_bytes
            FROM source_files
            {where}
            ORDER BY collection_id, file_role, source_path
            LIMIT ?
            """,
            params,
        )


def list_source_metadata(
    catalog_path: Path,
    *,
    collection_id: str | None = None,
    subject_kind: str | None = None,
    subject_id: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if collection_id:
        conditions.append("collection_id = ?")
        params.append(collection_id)
    if subject_kind:
        conditions.append("subject_kind = ?")
        params.append(subject_kind)
    if subject_id:
        conditions.append("subject_id = ?")
        params.append(subject_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            f"""
            SELECT collection_id, subject_kind, subject_id, key, value, source_path
            FROM source_metadata
            {where}
            ORDER BY collection_id, subject_kind, subject_id, key, value
            LIMIT ?
            """,
            params,
        )


def reader_summary(catalog_path: Path) -> dict[str, int]:
    if not catalog_path.exists():
        return {
            "collection_count": 0,
            "work_count": 0,
            "artifact_count": 0,
            "segment_count": 0,
            "alias_count": 0,
            "source_file_count": 0,
            "metadata_count": 0,
        }
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        collection_count = _scalar_int(conn, "SELECT COUNT(DISTINCT collection_id) FROM works")
        work_count = _scalar_int(conn, "SELECT COUNT(*) FROM works")
        artifact_count = _scalar_int(conn, "SELECT COUNT(*) FROM artifacts")
        segment_count = _scalar_int(conn, "SELECT COALESCE(SUM(segment_count), 0) FROM artifacts")
        alias_count = _scalar_int(conn, "SELECT COUNT(*) FROM aliases")
        source_file_count = _scalar_int(conn, "SELECT COUNT(*) FROM source_files")
        metadata_count = _scalar_int(conn, "SELECT COUNT(*) FROM source_metadata")
    return {
        "collection_count": int(collection_count),
        "work_count": int(work_count),
        "artifact_count": int(artifact_count),
        "segment_count": int(segment_count),
        "alias_count": int(alias_count),
        "source_file_count": int(source_file_count),
        "metadata_count": int(metadata_count),
    }


def _scalar_int(conn: duckdb.DuckDBPyConnection, query: str) -> int:
    row = conn.execute(query).fetchone()
    return int(row[0]) if row else 0
