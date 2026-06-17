from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from langnet.reader.author_index import (
    author_index_entry,
    author_kind_uses_unknown_authority,
    author_search_key,
    author_section_sort_key,
    author_selector_matches,
    canonical_author_id_for_source,
    canonical_unknown_author_id,
    compact_author_id,
    is_synthetic_author_selector,
    normalize_section_key,
)
from langnet.reader.author_normalization import normalize_reader_author
from langnet.reader.citation_references import normalize_citation_reference
from langnet.reader.ctsv2 import ctsv2_segment_address, parse_ctsv2_resource
from langnet.reader.discovery_taxonomy import (
    DISCOVERY_GROUPS,
    DISCOVERY_TAGS,
    normalize_discovery_tags,
)
from langnet.reader.models import (
    ReaderAlias,
    ReaderAuthorClassification,
    ReaderBookArtifact,
    ReaderCitationMap,
    ReaderCitationReference,
    ReaderContainedWork,
    ReaderDivisionMetadata,
    ReaderEdition,
    ReaderMetadataAttribution,
    ReaderMetadataOverlay,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceFile,
    ReaderSourceMetadata,
    ReaderSourceWitness,
    ReaderWork,
    ReaderWorkClassification,
    ReaderWorkMapNode,
    ReaderWorkRelation,
)

ASCII_MAX_CODEPOINT = 127
CATALOG_ENGLISH_WORDS = frozenset(
    {
        "and",
        "are",
        "both",
        "but",
        "for",
        "from",
        "have",
        "his",
        "is",
        "lord",
        "not",
        "of",
        "shall",
        "that",
        "the",
        "their",
        "them",
        "unto",
        "was",
        "were",
        "which",
        "with",
    }
)
CATALOG_ENGLISH_ANCHOR_WORDS = frozenset({"and", "of", "shall", "that", "the", "unto", "which"})
CATALOG_LATIN_WORDS = frozenset(
    {
        "ad",
        "cum",
        "de",
        "est",
        "et",
        "in",
        "non",
        "per",
        "pro",
        "quae",
        "quam",
        "qui",
        "quod",
        "sed",
        "sunt",
        "ut",
    }
)
CATALOG_ENGLISH_MIN_WORDS = 6
CATALOG_ENGLISH_MIN_ANCHOR_WORDS = 2
CATALOG_LANGUAGE_MIN_RATIO = 2
CLASSIFICATION_SOURCE_LANGUAGE_TOKENS = {
    "lat": {"lat", "latin"},
    "grc": {"grc", "greek"},
    "san": {"san", "sanskrit"},
    "eng": {"eng", "english"},
}
SUPPORTED_READER_LANGUAGES = frozenset({"san", "grc", "lat"})

CATALOG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS works (
    work_id VARCHAR PRIMARY KEY,
    collection_id VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    author_id VARCHAR,
    source_id VARCHAR NOT NULL,
    cts_work_urn VARCHAR,
    canonical_text_id VARCHAR
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

CREATE TABLE IF NOT EXISTS source_witnesses (
    canonical_text_id VARCHAR NOT NULL,
    work_id VARCHAR NOT NULL,
    collection_id VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    witness_id VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    source_urn VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_relations (
    source_id VARCHAR NOT NULL,
    target_id VARCHAR NOT NULL,
    relation_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL
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

CREATE TABLE IF NOT EXISTS work_map_nodes (
    work_id VARCHAR NOT NULL,
    node_id VARCHAR NOT NULL,
    parent_node_id VARCHAR,
    level INTEGER NOT NULL,
    kind VARCHAR NOT NULL,
    label TEXT NOT NULL,
    native_label TEXT,
    ordinal INTEGER NOT NULL,
    start_citation VARCHAR NOT NULL,
    end_citation VARCHAR NOT NULL,
    provenance VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);

CREATE TABLE IF NOT EXISTS division_metadata (
    work_id VARCHAR NOT NULL,
    node_id VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    short_label TEXT NOT NULL,
    traditional_reference VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    generator_model VARCHAR NOT NULL,
    review_status VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);

CREATE TABLE IF NOT EXISTS citation_maps (
    citation_map_id VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    work_id VARCHAR NOT NULL,
    source_pattern VARCHAR NOT NULL,
    machine_pattern VARCHAR NOT NULL,
    projection_rule VARCHAR NOT NULL,
    example_source_reference VARCHAR NOT NULL,
    example_machine_citation VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);

CREATE TABLE IF NOT EXISTS citation_references (
    work_id VARCHAR NOT NULL,
    segment_id VARCHAR NOT NULL,
    citation_path VARCHAR NOT NULL,
    citation_ref VARCHAR NOT NULL,
    normalized_ref VARCHAR NOT NULL,
    source_kind VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    sort_key INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS work_classifications (
    work_id VARCHAR PRIMARY KEY,
    category VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    date_range VARCHAR NOT NULL,
    authorship_status VARCHAR NOT NULL,
    popularity_score INTEGER,
    popularity_tier VARCHAR NOT NULL,
    scope VARCHAR NOT NULL,
    scope_popularity_score INTEGER,
    scope_popularity_tier VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL,
    generator_models TEXT NOT NULL,
    generator_run_id VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    discovery_group_id VARCHAR NOT NULL DEFAULT '',
    discovery_tags TEXT NOT NULL DEFAULT '',
    global_popularity_score INTEGER,
    global_popularity_tier VARCHAR NOT NULL DEFAULT '',
    group_popularity_score INTEGER,
    group_popularity_tier VARCHAR NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS work_classification_tags (
    work_id VARCHAR NOT NULL,
    tag_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS author_classifications (
    author_id VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    source_author_id VARCHAR NOT NULL DEFAULT '',
    canonical_name VARCHAR NOT NULL,
    agent_kind VARCHAR NOT NULL,
    historicity_status VARCHAR NOT NULL,
    period VARCHAR NOT NULL DEFAULT '',
    date_range VARCHAR NOT NULL DEFAULT '',
    region VARCHAR NOT NULL DEFAULT '',
    cultural_context VARCHAR NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    prominence_score INTEGER,
    prominence_tier VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    note TEXT NOT NULL,
    generator_models TEXT NOT NULL,
    generator_run_id VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    PRIMARY KEY (author_id, language)
);

CREATE INDEX IF NOT EXISTS works_language_idx ON works(language);
CREATE INDEX IF NOT EXISTS works_collection_idx ON works(collection_id);
CREATE INDEX IF NOT EXISTS artifacts_work_idx ON artifacts(work_id);
CREATE INDEX IF NOT EXISTS artifacts_edition_idx ON artifacts(edition_id);
CREATE INDEX IF NOT EXISTS aliases_alias_idx ON aliases(language, alias);
CREATE INDEX IF NOT EXISTS source_files_collection_idx ON source_files(collection_id);
CREATE INDEX IF NOT EXISTS source_metadata_subject_idx
    ON source_metadata(collection_id, subject_kind, subject_id);
CREATE INDEX IF NOT EXISTS source_witnesses_text_idx
    ON source_witnesses(canonical_text_id, collection_id);
CREATE INDEX IF NOT EXISTS work_relations_source_idx
    ON work_relations(source_id, relation_type);
CREATE INDEX IF NOT EXISTS metadata_overlays_match_idx
    ON metadata_overlays(collection_id, match_field, match_value);
CREATE INDEX IF NOT EXISTS metadata_attributions_match_idx
    ON metadata_attributions(collection_id, match_field, match_value);
CREATE INDEX IF NOT EXISTS metadata_attributions_agent_idx
    ON metadata_attributions(agent);
CREATE INDEX IF NOT EXISTS contained_works_parent_idx ON contained_works(parent_work_id);
CREATE INDEX IF NOT EXISTS contained_works_language_idx ON contained_works(language);
CREATE INDEX IF NOT EXISTS work_map_nodes_work_idx ON work_map_nodes(work_id);
CREATE INDEX IF NOT EXISTS division_metadata_work_idx ON division_metadata(work_id, node_id);
CREATE INDEX IF NOT EXISTS citation_maps_work_idx ON citation_maps(work_id, source_id);
CREATE INDEX IF NOT EXISTS citation_references_ref_idx ON citation_references(normalized_ref);
CREATE INDEX IF NOT EXISTS citation_references_work_idx ON citation_references(work_id);
CREATE INDEX IF NOT EXISTS work_classifications_work_idx ON work_classifications(work_id);
CREATE INDEX IF NOT EXISTS work_classification_tags_tag_idx
    ON work_classification_tags(tag_id, work_id);
CREATE INDEX IF NOT EXISTS author_classifications_kind_idx
    ON author_classifications(language, agent_kind, historicity_status);
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
CTS_WORK_TAIL_PARTS = 2
GRANULAR_CITATION_MIN_PARTS = 3
ROMAN_CITATION_VALUES = {
    "i": 1,
    "v": 5,
    "x": 10,
    "l": 50,
    "c": 100,
    "d": 500,
    "m": 1000,
}
ROMAN_CITATION_RE = re.compile(r"[ivxlcdm]+", re.IGNORECASE)


def _connect_write(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=False)


def _connect_read(path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path), read_only=True)


def create_catalog_db(path: Path) -> None:
    with _connect_write(path) as conn:
        conn.execute(CATALOG_SCHEMA_SQL)
        _ensure_catalog_schema(conn)


def create_book_db(path: Path) -> None:
    with _connect_write(path) as conn:
        conn.execute(BOOK_TABLE_SCHEMA_SQL)
        conn.execute(BOOK_INDEX_SQL)
        _ensure_book_schema(conn)


def _ensure_book_schema(conn: duckdb.DuckDBPyConnection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info('segments')").fetchall()}
    if "source_text" not in columns:
        conn.execute("ALTER TABLE segments ADD COLUMN source_text TEXT")


def _ensure_catalog_schema(conn: duckdb.DuckDBPyConnection) -> None:  # noqa: C901
    if _table_exists(conn, "works"):
        _ensure_works_schema(conn)
    if _table_exists(conn, "work_classifications"):
        _ensure_work_classification_schema(conn)
    if _table_exists(conn, "author_classifications"):
        _ensure_author_classification_schema(conn)


def _ensure_works_schema(conn: duckdb.DuckDBPyConnection) -> None:
    columns = _table_columns(conn, "works")
    if "canonical_text_id" not in columns:
        conn.execute("ALTER TABLE works ADD COLUMN canonical_text_id VARCHAR")


def _ensure_work_classification_schema(conn: duckdb.DuckDBPyConnection) -> None:
    columns = _table_columns(conn, "work_classifications")
    if "scope" not in columns:
        conn.execute("ALTER TABLE work_classifications ADD COLUMN scope VARCHAR DEFAULT ''")
    if "scope_popularity_score" not in columns:
        conn.execute("ALTER TABLE work_classifications ADD COLUMN scope_popularity_score INTEGER")
    if "scope_popularity_tier" not in columns:
        conn.execute(
            "ALTER TABLE work_classifications ADD COLUMN scope_popularity_tier VARCHAR DEFAULT ''"
        )
    if "discovery_group_id" not in columns:
        conn.execute(
            "ALTER TABLE work_classifications ADD COLUMN discovery_group_id VARCHAR DEFAULT ''"
        )
    if "discovery_tags" not in columns:
        conn.execute("ALTER TABLE work_classifications ADD COLUMN discovery_tags TEXT DEFAULT ''")
    if "global_popularity_score" not in columns:
        conn.execute("ALTER TABLE work_classifications ADD COLUMN global_popularity_score INTEGER")
    if "global_popularity_tier" not in columns:
        conn.execute(
            "ALTER TABLE work_classifications ADD COLUMN global_popularity_tier VARCHAR DEFAULT ''"
        )
    if "group_popularity_score" not in columns:
        conn.execute("ALTER TABLE work_classifications ADD COLUMN group_popularity_score INTEGER")
    if "group_popularity_tier" not in columns:
        conn.execute(
            "ALTER TABLE work_classifications ADD COLUMN group_popularity_tier VARCHAR DEFAULT ''"
        )


def _ensure_author_classification_schema(conn: duckdb.DuckDBPyConnection) -> None:
    columns = _table_columns(conn, "author_classifications")
    if "source_author_id" not in columns:
        conn.execute(
            "ALTER TABLE author_classifications ADD COLUMN source_author_id VARCHAR DEFAULT ''"
        )


def _table_columns(conn: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()}


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
            work.canonical_text_id,
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
    with _connect_write(catalog_path) as conn:
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
                    "canonical_text_id": pl.Utf8,
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
            conn.execute("DELETE FROM editions WHERE work_id IN (SELECT work_id FROM work_rows)")
            conn.execute("DELETE FROM artifacts WHERE work_id IN (SELECT work_id FROM work_rows)")
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
                    source_id, cts_work_urn, canonical_text_id
                )
                SELECT
                    work_id, collection_id, language, title, author, author_id,
                    source_id, cts_work_urn, canonical_text_id
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


def delete_reader_works(catalog_path: Path, work_ids: Iterable[str]) -> None:
    work_id_values = sorted({work_id for work_id in work_ids if work_id})
    if not work_id_values:
        return
    create_catalog_db(catalog_path)
    frame = pl.DataFrame({"work_id": work_id_values}, schema={"work_id": pl.Utf8})
    with _connect_write(catalog_path) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.register("delete_work_ids", frame)
            conn.execute(
                """
                DELETE FROM aliases
                WHERE target IN (SELECT work_id FROM delete_work_ids)
                """
            )
            conn.execute(
                """
                DELETE FROM contained_works
                WHERE contained_work_id IN (SELECT work_id FROM delete_work_ids)
                   OR parent_work_id IN (SELECT work_id FROM delete_work_ids)
                """
            )
            conn.execute(
                "DELETE FROM work_map_nodes WHERE work_id IN (SELECT work_id FROM delete_work_ids)"
            )
            conn.execute(
                """
                DELETE FROM citation_references
                WHERE work_id IN (SELECT work_id FROM delete_work_ids)
                """
            )
            conn.execute(
                """
                DELETE FROM work_classification_tags
                WHERE work_id IN (SELECT work_id FROM delete_work_ids)
                """
            )
            conn.execute(
                """
                DELETE FROM work_classifications
                WHERE work_id IN (SELECT work_id FROM delete_work_ids)
                """
            )
            conn.execute(
                "DELETE FROM artifacts WHERE work_id IN (SELECT work_id FROM delete_work_ids)"
            )
            conn.execute(
                "DELETE FROM editions WHERE work_id IN (SELECT work_id FROM delete_work_ids)"
            )
            conn.execute("DELETE FROM works WHERE work_id IN (SELECT work_id FROM delete_work_ids)")
            conn.unregister("delete_work_ids")
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
    with _connect_write(book_path) as conn:
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


def register_citation_references(
    catalog_path: Path,
    references: Iterable[ReaderCitationReference],
    *,
    replace: bool = True,
    replace_work_ids: Iterable[str] | None = None,
) -> None:
    replacement_work_ids = set(replace_work_ids or ())
    rows = [
        (
            reference.work_id,
            reference.segment_id,
            reference.citation_path,
            reference.citation_ref,
            normalize_citation_reference(reference.citation_ref),
            reference.source_kind,
            reference.source_path,
            reference.sort_key,
        )
        for reference in references
    ]
    create_catalog_db(catalog_path)
    with _connect_write(catalog_path) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            if replace:
                conn.execute("DELETE FROM citation_references")
            else:
                work_ids = sorted({row[0] for row in rows} | replacement_work_ids)
                if work_ids:
                    work_frame = pl.DataFrame({"work_id": work_ids}, schema={"work_id": pl.Utf8})
                    conn.register("citation_reference_work_ids", work_frame)
                    conn.execute(
                        """
                        DELETE FROM citation_references
                        WHERE work_id IN (SELECT work_id FROM citation_reference_work_ids)
                        """
                    )
                    conn.unregister("citation_reference_work_ids")
            if rows:
                frame = pl.DataFrame(
                    rows,
                    schema={
                        "work_id": pl.Utf8,
                        "segment_id": pl.Utf8,
                        "citation_path": pl.Utf8,
                        "citation_ref": pl.Utf8,
                        "normalized_ref": pl.Utf8,
                        "source_kind": pl.Utf8,
                        "source_path": pl.Utf8,
                        "sort_key": pl.Int64,
                    },
                    orient="row",
                )
                conn.register("citation_reference_rows", frame)
                conn.execute(
                    """
                    INSERT INTO citation_references (
                        work_id, segment_id, citation_path, citation_ref, normalized_ref,
                        source_kind, source_path, sort_key
                    )
                    SELECT
                        work_id, segment_id, citation_path, citation_ref, normalized_ref,
                        source_kind, source_path, sort_key
                    FROM citation_reference_rows
                    """
                )
                conn.unregister("citation_reference_rows")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def register_aliases(
    catalog_path: Path,
    aliases: Iterable[ReaderAlias],
    *,
    replace: bool = True,
) -> None:
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
    with _connect_write(catalog_path) as conn:
        if replace:
            conn.execute("DELETE FROM aliases")
        if not rows:
            return
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
        if not replace:
            conn.execute(
                """
                DELETE FROM aliases
                WHERE (language, alias) IN (
                    SELECT language, alias FROM alias_rows
                )
                   OR target IN (
                    SELECT target FROM alias_rows
                )
                """
            )
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
    with _connect_write(catalog_path) as conn:
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
    with _connect_write(catalog_path) as conn:
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


def apply_metadata_overlays_to_catalog(  # noqa: C901
    catalog_path: Path,
    overlays: Iterable[ReaderMetadataOverlay],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not dry_run:
        create_catalog_db(catalog_path)
    accepted = [overlay for overlay in overlays if overlay.status == "accepted"]
    if not accepted or not catalog_path.exists():
        return {"applied_count": 0, "candidate_count": 0, "dry_run": dry_run, "updates": []}
    with _connect_read(catalog_path) as conn:
        work_rows = _dict_rows(
            conn,
            """
            SELECT work_id, collection_id, language, title, author, author_id, source_id,
                   cts_work_urn
            FROM works
            ORDER BY work_id
            """,
        )
    updates: list[dict[str, str]] = []
    for overlay in accepted:
        for row in work_rows:
            if not _metadata_overlay_matches_row(overlay, row):
                continue
            current = str(row.get(overlay.field) or "")
            value = _metadata_overlay_value(overlay)
            if current == value:
                continue
            updates.append(
                {
                    "work_id": str(row["work_id"]),
                    "field": overlay.field,
                    "from_value": current,
                    "to_value": value,
                    "match_field": overlay.match_field,
                    "match_value": overlay.match_value,
                }
            )
    if updates and not dry_run:
        with _connect_write(catalog_path) as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                for update in updates:
                    field = update["field"]
                    conn.execute(
                        f"UPDATE works SET {field} = ? WHERE work_id = ?",
                        [update["to_value"], update["work_id"]],
                    )
                    if field == "language":
                        conn.execute(
                            "UPDATE editions SET language = ? WHERE work_id = ?",
                            [update["to_value"], update["work_id"]],
                        )
                        conn.execute(
                            "UPDATE aliases SET language = ? WHERE target = ?",
                            [update["to_value"], update["work_id"]],
                        )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    return {
        "applied_count": 0 if dry_run else len(updates),
        "candidate_count": len(updates),
        "dry_run": dry_run,
        "updates": updates,
    }


def _metadata_overlay_matches_row(
    overlay: ReaderMetadataOverlay,
    row: Mapping[str, Any],
) -> bool:
    if overlay.collection_id != str(row.get("collection_id") or ""):
        return False
    if overlay.match_field == "author_id":
        return compact_author_id(overlay.match_value) == compact_author_id(
            str(row.get("author_id") or "")
        )
    return overlay.match_value == str(row.get(overlay.match_field) or "")


def _metadata_overlay_value(overlay: ReaderMetadataOverlay) -> str:
    if overlay.field == "author":
        return normalize_reader_author(overlay.value)
    return overlay.value


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
    with _connect_write(catalog_path) as conn:
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


def register_work_map_nodes(
    catalog_path: Path,
    nodes: Iterable[ReaderWorkMapNode],
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            node.work_id,
            node.node_id,
            node.parent_node_id,
            node.level,
            node.kind,
            node.label,
            node.native_label,
            node.ordinal,
            node.start_citation,
            node.end_citation,
            node.provenance,
            node.confidence,
            node.status,
            node.note,
            node.source_file,
            evidence.source_type,
            evidence.citation,
            evidence.label,
            evidence.retrieved_at,
        )
        for node in nodes
        for evidence in node.evidence
    ]
    with _connect_write(catalog_path) as conn:
        conn.execute("DELETE FROM work_map_nodes")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "work_id": pl.Utf8,
                    "node_id": pl.Utf8,
                    "parent_node_id": pl.Utf8,
                    "level": pl.Int64,
                    "kind": pl.Utf8,
                    "label": pl.Utf8,
                    "native_label": pl.Utf8,
                    "ordinal": pl.Int64,
                    "start_citation": pl.Utf8,
                    "end_citation": pl.Utf8,
                    "provenance": pl.Utf8,
                    "confidence": pl.Utf8,
                    "status": pl.Utf8,
                    "note": pl.Utf8,
                    "source_file": pl.Utf8,
                    "evidence_source_type": pl.Utf8,
                    "evidence_citation": pl.Utf8,
                    "evidence_label": pl.Utf8,
                    "evidence_retrieved_at": pl.Utf8,
                },
                orient="row",
            )
            conn.register("work_map_node_rows", frame)
            conn.execute(
                """
                INSERT INTO work_map_nodes (
                    work_id, node_id, parent_node_id, level, kind, label, native_label,
                    ordinal, start_citation, end_citation, provenance, confidence,
                    status, note, source_file, evidence_source_type, evidence_citation,
                    evidence_label, evidence_retrieved_at
                )
                SELECT
                    work_id, node_id, parent_node_id, level, kind, label, native_label,
                    ordinal, start_citation, end_citation, provenance, confidence,
                    status, note, source_file, evidence_source_type, evidence_citation,
                    evidence_label, evidence_retrieved_at
                FROM work_map_node_rows
                """
            )
            conn.unregister("work_map_node_rows")


def register_division_metadata(
    catalog_path: Path,
    rows: Iterable[ReaderDivisionMetadata],
    *,
    replace: bool = True,
) -> None:
    create_catalog_db(catalog_path)
    row_values = [
        (
            row.work_id,
            row.node_id,
            row.summary,
            row.short_label,
            row.traditional_reference,
            row.status,
            row.confidence,
            row.generator_model,
            row.review_status,
            row.note,
            row.source_file,
            evidence.source_type,
            evidence.citation,
            evidence.label,
            evidence.retrieved_at,
        )
        for row in rows
        for evidence in row.evidence
    ]
    with _connect_write(catalog_path) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            if replace:
                conn.execute("DELETE FROM division_metadata")
            if row_values:
                frame = pl.DataFrame(
                    row_values,
                    schema={
                        "work_id": pl.Utf8,
                        "node_id": pl.Utf8,
                        "summary": pl.Utf8,
                        "short_label": pl.Utf8,
                        "traditional_reference": pl.Utf8,
                        "status": pl.Utf8,
                        "confidence": pl.Utf8,
                        "generator_model": pl.Utf8,
                        "review_status": pl.Utf8,
                        "note": pl.Utf8,
                        "source_file": pl.Utf8,
                        "evidence_source_type": pl.Utf8,
                        "evidence_citation": pl.Utf8,
                        "evidence_label": pl.Utf8,
                        "evidence_retrieved_at": pl.Utf8,
                    },
                    orient="row",
                )
                conn.register("division_metadata_rows", frame)
                conn.execute(
                    """
                    INSERT INTO division_metadata (
                        work_id, node_id, summary, short_label, traditional_reference,
                        status, confidence, generator_model, review_status, note,
                        source_file, evidence_source_type, evidence_citation,
                        evidence_label, evidence_retrieved_at
                    )
                    SELECT
                        work_id, node_id, summary, short_label, traditional_reference,
                        status, confidence, generator_model, review_status, note,
                        source_file, evidence_source_type, evidence_citation,
                        evidence_label, evidence_retrieved_at
                    FROM division_metadata_rows
                    """
                )
                conn.unregister("division_metadata_rows")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def register_citation_maps(
    catalog_path: Path,
    maps: Iterable[ReaderCitationMap],
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            citation_map.citation_map_id,
            citation_map.source_id,
            citation_map.work_id,
            citation_map.source_pattern,
            citation_map.machine_pattern,
            citation_map.projection_rule,
            citation_map.example_source_reference,
            citation_map.example_machine_citation,
            citation_map.status,
            citation_map.confidence,
            citation_map.note,
            citation_map.source_file,
            evidence.source_type,
            evidence.citation,
            evidence.label,
            evidence.retrieved_at,
        )
        for citation_map in maps
        for evidence in citation_map.evidence
    ]
    with _connect_write(catalog_path) as conn:
        conn.execute("DELETE FROM citation_maps")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "citation_map_id": pl.Utf8,
                    "source_id": pl.Utf8,
                    "work_id": pl.Utf8,
                    "source_pattern": pl.Utf8,
                    "machine_pattern": pl.Utf8,
                    "projection_rule": pl.Utf8,
                    "example_source_reference": pl.Utf8,
                    "example_machine_citation": pl.Utf8,
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
            conn.register("citation_map_rows", frame)
            conn.execute(
                """
                INSERT INTO citation_maps (
                    citation_map_id, source_id, work_id, source_pattern,
                    machine_pattern, projection_rule, example_source_reference,
                    example_machine_citation, status, confidence, note, source_file,
                    evidence_source_type, evidence_citation, evidence_label,
                    evidence_retrieved_at
                )
                SELECT
                    citation_map_id, source_id, work_id, source_pattern,
                    machine_pattern, projection_rule, example_source_reference,
                    example_machine_citation, status, confidence, note, source_file,
                    evidence_source_type, evidence_citation, evidence_label,
                    evidence_retrieved_at
                FROM citation_map_rows
                """
            )
            conn.unregister("citation_map_rows")


def register_work_classifications(
    catalog_path: Path,
    classifications: Iterable[ReaderWorkClassification],
    *,
    merge: bool = False,
) -> None:
    create_catalog_db(catalog_path)
    requested_classification_list = list(classifications)
    work_id_map = _catalog_work_classification_id_map(catalog_path)
    classification_list = [
        replace(classification, work_id=resolved_work_id)
        for classification in requested_classification_list
        if (resolved_work_id := _resolve_work_classification_id(classification, work_id_map))
    ]
    rows = [
        (
            classification.work_id,
            classification.category,
            classification.period,
            classification.date_range,
            classification.authorship_status,
            classification.popularity_score,
            classification.popularity_tier,
            classification.scope,
            classification.scope_popularity_score,
            classification.scope_popularity_tier,
            classification.confidence,
            classification.note,
            classification.generator_models,
            classification.generator_run_id,
            classification.source_file,
            classification.discovery_group_id,
            classification.discovery_tags,
            classification.global_popularity_score,
            classification.global_popularity_tier,
            classification.group_popularity_score,
            classification.group_popularity_tier,
        )
        for classification in classification_list
    ]
    tag_rows = [
        (classification.work_id, tag)
        for classification in classification_list
        for tag in normalize_discovery_tags(classification.discovery_tags)
    ]
    with _connect_write(catalog_path) as conn:
        if merge:
            if not requested_classification_list:
                return
            work_id_frame = pl.DataFrame(
                [
                    (work_id,)
                    for classification in requested_classification_list
                    for work_id in _work_classification_delete_ids(classification, work_id_map)
                ],
                schema={"work_id": pl.Utf8},
                orient="row",
            )
            conn.register("work_classification_work_ids", work_id_frame)
            conn.execute(
                """
                DELETE FROM work_classification_tags
                WHERE work_id IN (SELECT work_id FROM work_classification_work_ids)
                """
            )
            conn.execute(
                """
                DELETE FROM work_classifications
                WHERE work_id IN (SELECT work_id FROM work_classification_work_ids)
                """
            )
            conn.unregister("work_classification_work_ids")
        else:
            conn.execute("DELETE FROM work_classifications")
            conn.execute("DELETE FROM work_classification_tags")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "work_id": pl.Utf8,
                    "category": pl.Utf8,
                    "period": pl.Utf8,
                    "date_range": pl.Utf8,
                    "authorship_status": pl.Utf8,
                    "popularity_score": pl.Int64,
                    "popularity_tier": pl.Utf8,
                    "scope": pl.Utf8,
                    "scope_popularity_score": pl.Int64,
                    "scope_popularity_tier": pl.Utf8,
                    "confidence": pl.Utf8,
                    "note": pl.Utf8,
                    "generator_models": pl.Utf8,
                    "generator_run_id": pl.Utf8,
                    "source_file": pl.Utf8,
                    "discovery_group_id": pl.Utf8,
                    "discovery_tags": pl.Utf8,
                    "global_popularity_score": pl.Int64,
                    "global_popularity_tier": pl.Utf8,
                    "group_popularity_score": pl.Int64,
                    "group_popularity_tier": pl.Utf8,
                },
                orient="row",
            )
            conn.register("work_classification_rows", frame)
            conn.execute(
                """
                INSERT INTO work_classifications (
                    work_id, category, period, date_range, authorship_status,
                    popularity_score, popularity_tier, scope, scope_popularity_score,
                    scope_popularity_tier, confidence, note,
                    generator_models, generator_run_id, source_file,
                    discovery_group_id, discovery_tags, global_popularity_score,
                    global_popularity_tier, group_popularity_score, group_popularity_tier
                )
                SELECT
                    work_id, category, period, date_range, authorship_status,
                    popularity_score, popularity_tier, scope, scope_popularity_score,
                    scope_popularity_tier, confidence, note,
                    generator_models, generator_run_id, source_file,
                    discovery_group_id, discovery_tags, global_popularity_score,
                    global_popularity_tier, group_popularity_score, group_popularity_tier
                FROM work_classification_rows
                """
            )
            conn.unregister("work_classification_rows")
        if tag_rows:
            tag_frame = pl.DataFrame(
                tag_rows,
                schema={"work_id": pl.Utf8, "tag_id": pl.Utf8},
                orient="row",
            )
            conn.register("work_classification_tag_rows", tag_frame)
            conn.execute(
                """
                INSERT INTO work_classification_tags (work_id, tag_id)
                SELECT work_id, tag_id
                FROM work_classification_tag_rows
                """
            )
            conn.unregister("work_classification_tag_rows")


def _catalog_work_classification_id_map(catalog_path: Path) -> dict[str, str]:
    with _connect_read(catalog_path) as conn:
        contained_union = ""
        if _table_exists(conn, "contained_works"):
            contained_union = """
                UNION ALL
                SELECT contained_work_id AS work_id, source_id, cts_work_urn
                FROM contained_works
                WHERE status = 'accepted'
            """
        rows = _dict_rows(
            conn,
            f"""
            SELECT work_id, source_id, cts_work_urn
            FROM works
            {contained_union}
            """,
        )
    candidates: dict[str, set[str]] = {}
    for row in rows:
        work_id = str(row.get("work_id") or "")
        for key in _work_classification_lookup_keys(
            work_id,
            str(row.get("source_id") or ""),
            str(row.get("cts_work_urn") or ""),
        ):
            candidates.setdefault(key, set()).add(work_id)
    return {key: next(iter(values)) for key, values in candidates.items() if len(values) == 1}


def _work_classification_lookup_keys(*values: str) -> set[str]:
    keys: set[str] = set()
    for value in values:
        raw = value.strip()
        if not raw:
            continue
        keys.add(raw)
        compact = raw.rsplit(":", 1)[-1]
        keys.add(compact)
        match = re.fullmatch(r"(tlg\d+[A-Za-z]?)\.(?:tlg)?(\d+[A-Za-z]?)", compact)
        if match:
            author_id = match.group(1)
            work_number = match.group(2)
            keys.add(f"{author_id}.{work_number}")
            keys.add(f"{author_id}.tlg{work_number}")
            keys.add(f"urn:cts:greekLit:{author_id}.tlg{work_number}")
            keys.add(f"langnet:reader:tlg:{author_id}.{work_number}")
            keys.add(f"langnet:reader:tlg:{author_id}.tlg{work_number}")
        match = re.fullmatch(r"(phi\d+[A-Za-z]?)\.(?:phi)?(\d+[A-Za-z]?)", compact)
        if match:
            author_id = match.group(1)
            work_number = match.group(2)
            keys.add(f"{author_id}.{work_number}")
            keys.add(f"{author_id}.phi{work_number}")
            keys.add(f"urn:cts:latinLit:{author_id}.phi{work_number}")
            keys.add(f"langnet:reader:phi:{author_id}.{work_number}")
            keys.add(f"langnet:reader:phi:{author_id}.phi{work_number}")
    return keys


def _resolve_work_classification_id(
    classification: ReaderWorkClassification,
    work_id_map: Mapping[str, str],
) -> str | None:
    for key in _work_classification_lookup_keys(classification.work_id):
        if key in work_id_map:
            return work_id_map[key]
    return None


def _work_classification_delete_ids(
    classification: ReaderWorkClassification,
    work_id_map: Mapping[str, str],
) -> set[str]:
    ids = {classification.work_id}
    resolved = _resolve_work_classification_id(classification, work_id_map)
    if resolved:
        ids.add(resolved)
    return ids


def prune_stale_work_classifications(
    catalog_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    stale_rows = _stale_work_classification_rows(catalog_path)
    if stale_rows and not dry_run:
        with _connect_write(catalog_path) as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                work_id_frame = pl.DataFrame(
                    [(row["work_id"],) for row in stale_rows],
                    schema={"work_id": pl.Utf8},
                    orient="row",
                )
                conn.register("stale_work_classification_ids", work_id_frame)
                conn.execute(
                    """
                    DELETE FROM work_classification_tags
                    WHERE work_id IN (SELECT work_id FROM stale_work_classification_ids)
                    """
                )
                conn.execute(
                    """
                    DELETE FROM work_classifications
                    WHERE work_id IN (SELECT work_id FROM stale_work_classification_ids)
                    """
                )
                conn.unregister("stale_work_classification_ids")
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    return {
        "candidate_count": len(stale_rows),
        "removed_count": 0 if dry_run else len(stale_rows),
        "dry_run": dry_run,
        "items": stale_rows,
    }


def _stale_work_classification_rows(catalog_path: Path) -> list[dict[str, str]]:
    with _connect_read(catalog_path) as conn:
        if not _table_exists(conn, "work_classifications"):
            return []
        rows = _dict_rows(
            conn,
            """
            SELECT
                w.work_id,
                w.language,
                w.title,
                c.source_file,
                c.generator_run_id
            FROM works w
            JOIN work_classifications c ON c.work_id = w.work_id
            ORDER BY w.work_id
            """,
        )
    stale_rows: list[dict[str, str]] = []
    for row in rows:
        source_language = _classification_source_language(row)
        work_language = str(row.get("language") or "")
        if source_language and work_language and source_language != work_language:
            stale_rows.append(
                {
                    "work_id": str(row.get("work_id") or ""),
                    "language": work_language,
                    "classification_source_language": source_language,
                    "title": str(row.get("title") or ""),
                    "source_file": str(row.get("source_file") or ""),
                    "generator_run_id": str(row.get("generator_run_id") or ""),
                }
            )
    return stale_rows


def _classification_source_language(row: Mapping[str, Any]) -> str | None:
    tokens = set(
        token
        for field in ("source_file", "generator_run_id")
        for token in re.split(r"[^a-z0-9]+", str(row.get(field) or "").casefold())
        if token
    )
    for language, language_tokens in CLASSIFICATION_SOURCE_LANGUAGE_TOKENS.items():
        if tokens & language_tokens:
            return language
    return None


def register_author_classifications(
    catalog_path: Path,
    classifications: Iterable[ReaderAuthorClassification],
    *,
    merge: bool = False,
) -> None:
    create_catalog_db(catalog_path)
    requested_classification_list = list(classifications)
    valid_keys = _catalog_author_classification_keys(catalog_path)
    classification_list = [
        classification
        for classification in requested_classification_list
        if _author_classification_matches_catalog(classification, valid_keys)
    ]
    rows = [
        (
            classification.author_id,
            classification.language,
            classification.source_author_id,
            classification.canonical_name,
            classification.agent_kind,
            classification.historicity_status,
            classification.period,
            classification.date_range,
            classification.region,
            classification.cultural_context,
            classification.bio,
            classification.prominence_score,
            classification.prominence_tier,
            classification.confidence,
            classification.note,
            classification.generator_models,
            classification.generator_run_id,
            classification.source_file,
        )
        for classification in classification_list
    ]
    with _connect_write(catalog_path) as conn:
        if merge:
            if not requested_classification_list:
                return
            key_frame = pl.DataFrame(
                [
                    (classification.author_id, classification.language)
                    for classification in requested_classification_list
                ],
                schema={"author_id": pl.Utf8, "language": pl.Utf8},
                orient="row",
            )
            conn.register("author_classification_keys", key_frame)
            conn.execute(
                """
                DELETE FROM author_classifications
                WHERE (author_id, language) IN (
                    SELECT author_id, language FROM author_classification_keys
                )
                """
            )
            conn.unregister("author_classification_keys")
        else:
            conn.execute("DELETE FROM author_classifications")
        if rows:
            frame = pl.DataFrame(
                rows,
                schema={
                    "author_id": pl.Utf8,
                    "language": pl.Utf8,
                    "source_author_id": pl.Utf8,
                    "canonical_name": pl.Utf8,
                    "agent_kind": pl.Utf8,
                    "historicity_status": pl.Utf8,
                    "period": pl.Utf8,
                    "date_range": pl.Utf8,
                    "region": pl.Utf8,
                    "cultural_context": pl.Utf8,
                    "bio": pl.Utf8,
                    "prominence_score": pl.Int64,
                    "prominence_tier": pl.Utf8,
                    "confidence": pl.Utf8,
                    "note": pl.Utf8,
                    "generator_models": pl.Utf8,
                    "generator_run_id": pl.Utf8,
                    "source_file": pl.Utf8,
                },
                orient="row",
            )
            conn.register("author_classification_rows", frame)
            conn.execute(
                """
                INSERT INTO author_classifications (
                    author_id, language, source_author_id, canonical_name, agent_kind,
                    historicity_status, period, date_range, region, cultural_context, bio,
                    prominence_score, prominence_tier,
                    confidence, note, generator_models, generator_run_id, source_file
                )
                SELECT
                    rows.author_id, rows.language, rows.source_author_id,
                    rows.canonical_name, rows.agent_kind, rows.historicity_status,
                    rows.period, rows.date_range, rows.region, rows.cultural_context,
                    rows.bio, rows.prominence_score, rows.prominence_tier,
                    rows.confidence, rows.note, rows.generator_models,
                    rows.generator_run_id, rows.source_file
                FROM author_classification_rows
                AS rows
                """
            )
            conn.unregister("author_classification_rows")


def _catalog_author_classification_keys(catalog_path: Path) -> set[tuple[str, str]]:
    with _connect_read(catalog_path) as conn:
        rows = _dict_rows(
            conn,
            """
            SELECT DISTINCT language, COALESCE(author_id, '') AS author_id, author
            FROM works
            WHERE COALESCE(author, '') <> ''
            """,
        )
    keys: set[tuple[str, str]] = set()
    for row in rows:
        language = str(row.get("language") or "")
        for key in _author_catalog_keys(
            language,
            str(row.get("author_id") or ""),
            str(row.get("author") or ""),
        ):
            keys.add((language, key))
    return keys


def _author_catalog_keys(language: str, source_author_id: str, author: str) -> set[str]:
    source_author_id = source_author_id.strip()
    keys = {source_author_id} if source_author_id else set()
    compact = compact_author_id(source_author_id)
    if compact:
        keys.add(compact)
    if source_author_id:
        keys.add(
            canonical_author_id_for_source(
                language,
                source_author_id,
                compact or source_author_id,
                author,
            )
        )
    else:
        keys.add(
            author_index_entry(
                {
                    "language": language,
                    "source_author_id": "",
                    "author": author,
                }
            )["author_id"]
        )
    return {key for key in keys if key}


def _author_classification_matches_catalog(
    classification: ReaderAuthorClassification,
    valid_keys: set[tuple[str, str]],
) -> bool:
    language = classification.language
    keys = {
        classification.author_id,
        classification.source_author_id,
        compact_author_id(classification.author_id),
        compact_author_id(classification.source_author_id),
        canonical_author_id_for_source(
            language,
            classification.source_author_id or classification.author_id,
            classification.author_id,
            classification.canonical_name,
        ),
    }
    return any((language, key) in valid_keys for key in keys if key)


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
    with _connect_write(catalog_path) as conn:
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
    with _connect_write(catalog_path) as conn:
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


def register_source_witnesses(
    catalog_path: Path,
    witnesses: Iterable[ReaderSourceWitness],
    *,
    replace: bool = True,
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            witness.canonical_text_id,
            witness.work_id,
            witness.collection_id,
            witness.language,
            witness.witness_id,
            witness.source_id,
            witness.source_urn,
            str(witness.source_path),
            witness.status,
            witness.confidence,
            witness.note,
        )
        for witness in witnesses
    ]
    with _connect_write(catalog_path) as conn:
        if replace:
            conn.execute("DELETE FROM source_witnesses")
        if not rows:
            return
        frame = pl.DataFrame(
            rows,
            schema={
                "canonical_text_id": pl.Utf8,
                "work_id": pl.Utf8,
                "collection_id": pl.Utf8,
                "language": pl.Utf8,
                "witness_id": pl.Utf8,
                "source_id": pl.Utf8,
                "source_urn": pl.Utf8,
                "source_path": pl.Utf8,
                "status": pl.Utf8,
                "confidence": pl.Utf8,
                "note": pl.Utf8,
            },
            orient="row",
        )
        conn.register("source_witness_rows", frame)
        if not replace:
            conn.execute(
                """
                DELETE FROM source_witnesses
                WHERE work_id IN (SELECT DISTINCT work_id FROM source_witness_rows)
                """
            )
        conn.execute(
            """
            INSERT INTO source_witnesses (
                canonical_text_id, work_id, collection_id, language, witness_id,
                source_id, source_urn, source_path, status, confidence, note
            )
            SELECT
                canonical_text_id, work_id, collection_id, language, witness_id,
                source_id, source_urn, source_path, status, confidence, note
            FROM source_witness_rows
            """
        )
        conn.unregister("source_witness_rows")


def register_work_relations(
    catalog_path: Path,
    relations: Iterable[ReaderWorkRelation],
) -> None:
    create_catalog_db(catalog_path)
    rows = [
        (
            relation.source_id,
            relation.target_id,
            relation.relation_type,
            relation.status,
            relation.confidence,
            relation.note,
            relation.source_file,
        )
        for relation in relations
    ]
    with _connect_write(catalog_path) as conn:
        conn.execute("DELETE FROM work_relations")
        if not rows:
            return
        frame = pl.DataFrame(
            rows,
            schema={
                "source_id": pl.Utf8,
                "target_id": pl.Utf8,
                "relation_type": pl.Utf8,
                "status": pl.Utf8,
                "confidence": pl.Utf8,
                "note": pl.Utf8,
                "source_file": pl.Utf8,
            },
            orient="row",
        )
        conn.register("work_relation_rows", frame)
        conn.execute(
            """
            INSERT INTO work_relations (
                source_id, target_id, relation_type, status, confidence, note, source_file
            )
            SELECT source_id, target_id, relation_type, status, confidence, note, source_file
            FROM work_relation_rows
            """
        )
        conn.unregister("work_relation_rows")


def repair_work_languages(catalog_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run:
        create_catalog_db(catalog_path)
    repairs = _catalog_work_language_repairs(catalog_path)
    if repairs and not dry_run:
        with _connect_write(catalog_path) as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                for repair in repairs:
                    conn.execute(
                        "UPDATE works SET language = ? WHERE work_id = ?",
                        [repair["to_language"], repair["work_id"]],
                    )
                    conn.execute(
                        "UPDATE editions SET language = ? WHERE work_id = ?",
                        [repair["to_language"], repair["work_id"]],
                    )
                    conn.execute(
                        "UPDATE aliases SET language = ? WHERE target = ?",
                        [repair["to_language"], repair["work_id"]],
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    return {
        "updated_count": 0 if dry_run else len(repairs),
        "candidate_count": len(repairs),
        "dry_run": dry_run,
        "repairs": repairs,
    }


def _catalog_work_language_repairs(catalog_path: Path) -> list[dict[str, str]]:
    with _connect_read(catalog_path) as conn:
        work_rows = _dict_rows(
            conn,
            """
            SELECT
                w.work_id, w.collection_id, w.language, w.title, w.author, w.source_id,
                a.artifact_path, a.adapter,
                (
                    SELECT sm.value
                    FROM source_metadata sm
                    WHERE sm.collection_id = w.collection_id
                      AND sm.subject_kind = 'author'
                      AND sm.key = 'authtab_language'
                      AND sm.subject_id IN (
                          coalesce(w.author_id, ''),
                          regexp_extract(w.source_id, '^[^.]+')
                      )
                    ORDER BY sm.source_path, sm.value
                    LIMIT 1
                ) AS metadata_language
            FROM works w
            LEFT JOIN artifacts a ON a.work_id = w.work_id
            ORDER BY w.work_id, a.artifact_id
            """,
        )
    seen: set[str] = set()
    repairs: list[dict[str, str]] = []
    for row in work_rows:
        work_id = str(row.get("work_id") or "")
        if not work_id or work_id in seen:
            continue
        seen.add(work_id)
        current_language = str(row.get("language") or "")
        repaired_language = _catalog_work_metadata_language(row)
        sample_text = ""
        if not repaired_language and _catalog_language_repair_needs_sample(row):
            sample_text = _catalog_work_sample_text(
                Path(str(row.get("artifact_path") or "")),
                work_id=work_id,
            )
            repaired_language = _catalog_primary_work_language(row, sample_text=sample_text)
        if repaired_language and repaired_language != current_language:
            repairs.append(
                {
                    "work_id": work_id,
                    "from_language": current_language,
                    "to_language": repaired_language,
                    "title": str(row.get("title") or ""),
                    "author": str(row.get("author") or ""),
                }
            )
    return repairs


def _catalog_language_repair_needs_sample(row: Mapping[str, Any]) -> bool:
    if str(row.get("collection_id") or "") != "phi":
        return False
    source_id = str(row.get("source_id") or "").casefold()
    source_family = source_id.split(".", 1)[0]
    return source_family.startswith(("civ", "cop"))


def _catalog_work_sample_text(artifact_path: Path, *, work_id: str) -> str:
    if not artifact_path or not artifact_path.exists():
        return ""
    try:
        with duckdb.connect(str(artifact_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT text
                FROM segments
                WHERE work_id = ?
                ORDER BY sort_key
                LIMIT 200
                """,
                [work_id],
            ).fetchall()
    except Exception:
        return ""
    return " ".join(str(row[0] or "") for row in rows)


def _catalog_primary_work_language(row: Mapping[str, Any], *, sample_text: str) -> str:
    current_language = str(row.get("language") or "")
    collection_id = str(row.get("collection_id") or "")
    repaired_language = current_language
    metadata_language = _catalog_work_metadata_language(row)
    if collection_id == "phi":
        if metadata_language:
            repaired_language = metadata_language
        elif _catalog_text_looks_english(sample_text):
            repaired_language = "eng"
        elif current_language == "eng" and _catalog_text_looks_latin(sample_text):
            repaired_language = "lat"
    return repaired_language


def _catalog_work_metadata_language(row: Mapping[str, Any]) -> str | None:
    if str(row.get("collection_id") or "") != "phi":
        return None
    source_family_language = _catalog_phi_source_family_language(row)
    if source_family_language:
        return source_family_language
    metadata_language = str(row.get("metadata_language") or "").strip()
    if metadata_language:
        return _catalog_normalize_metadata_language(metadata_language)
    title = str(row.get("title") or "").casefold()
    author = str(row.get("author") or "").casefold()
    if "(latin" in title or "latin works" in title:
        return "lat"
    if "(english" in title or "english bible" in author:
        return "eng"
    return None


def _catalog_phi_source_family_language(row: Mapping[str, Any]) -> str | None:
    title = str(row.get("title") or "").casefold()
    source_family = str(row.get("source_id") or "").casefold().split(".", 1)[0]
    language = _PHI_EXACT_SOURCE_FAMILY_LANGUAGES.get(source_family)
    text = " ".join(
        str(row.get(key) or "") for key in ("source_id", "author", "author_id", "title")
    ).casefold()
    if language is None:
        for family, family_language in _PHI_EXACT_SOURCE_FAMILY_LANGUAGES.items():
            if family in text:
                language = family_language
                break
    if language is None and ("english bible" in text or "(english" in title):
        language = "eng"
    if language is None and ("hebrew bible" in text or "mt or bhs" in text):
        language = "heb"
    if language is None and ("coptic" in text or "sahidic" in text or "sahiddic" in text):
        language = "cop"
    if language is None and (
        "septuagint" in text or "old greek bible" in text or "greek new testament" in text
    ):
        language = "grc"
    return language


_PHI_EXACT_SOURCE_FAMILY_LANGUAGES = {
    "civ0001": "heb",
    "civ0002": "grc",
    "civ0003": "grc",
    "civ0004": "lat",
    "civ0005": "eng",
    "civ0006": "eng",
    "cop0001": "cop",
}


def _catalog_normalize_metadata_language(value: str) -> str:
    normalized = value.strip().casefold()
    return {
        "g": "grc",
        "greek": "grc",
        "grc": "grc",
        "h": "heb",
        "hebrew": "heb",
        "heb": "heb",
        "c": "cop",
        "coptic": "cop",
        "cop": "cop",
        "l": "lat",
        "latin": "lat",
        "lat": "lat",
        "e": "lat",
        "english": "eng",
        "eng": "eng",
    }.get(normalized, normalized)


def _catalog_text_looks_english(text: str) -> bool:
    english_hits, latin_hits, english_anchor_count = _catalog_language_hits(text)
    return (
        english_hits >= CATALOG_ENGLISH_MIN_WORDS
        and english_anchor_count >= CATALOG_ENGLISH_MIN_ANCHOR_WORDS
        and english_hits >= max(1, latin_hits) * CATALOG_LANGUAGE_MIN_RATIO
    )


def _catalog_text_looks_latin(text: str) -> bool:
    english_hits, latin_hits, _english_anchor_count = _catalog_language_hits(text)
    return (
        latin_hits >= CATALOG_ENGLISH_MIN_WORDS
        and latin_hits >= max(1, english_hits) * CATALOG_LANGUAGE_MIN_RATIO
    )


def _catalog_language_hits(text: str) -> tuple[int, int, int]:
    words = re.findall(r"[A-Za-z]+", text.casefold())
    english_hits = sum(1 for word in words if word in CATALOG_ENGLISH_WORDS)
    english_anchor_count = len({word for word in words if word in CATALOG_ENGLISH_ANCHOR_WORDS})
    latin_hits = sum(1 for word in words if word in CATALOG_LATIN_WORDS)
    return english_hits, latin_hits, english_anchor_count


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


def _table_columns(conn: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    return {row[1] for row in conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()}


def _work_classification_select_columns(columns: set[str]) -> str:
    scope = "wc.scope" if "scope" in columns else "NULL::VARCHAR"
    scope_score = (
        "wc.scope_popularity_score" if "scope_popularity_score" in columns else "NULL::INTEGER"
    )
    scope_tier = (
        "wc.scope_popularity_tier" if "scope_popularity_tier" in columns else "NULL::VARCHAR"
    )
    discovery_group = (
        "wc.discovery_group_id" if "discovery_group_id" in columns else "NULL::VARCHAR"
    )
    discovery_tags = "wc.discovery_tags" if "discovery_tags" in columns else "NULL::VARCHAR"
    global_score = (
        "COALESCE(wc.global_popularity_score, wc.popularity_score)"
        if "global_popularity_score" in columns
        else "wc.popularity_score"
    )
    global_tier = (
        "COALESCE(NULLIF(wc.global_popularity_tier, ''), wc.popularity_tier)"
        if "global_popularity_tier" in columns
        else "wc.popularity_tier"
    )
    group_score = (
        "COALESCE(wc.group_popularity_score, wc.scope_popularity_score)"
        if "group_popularity_score" in columns and "scope_popularity_score" in columns
        else "wc.group_popularity_score"
        if "group_popularity_score" in columns
        else scope_score
    )
    group_tier = (
        "COALESCE(NULLIF(wc.group_popularity_tier, ''), wc.scope_popularity_tier)"
        if "group_popularity_tier" in columns and "scope_popularity_tier" in columns
        else "wc.group_popularity_tier"
        if "group_popularity_tier" in columns
        else scope_tier
    )
    return f"""
        wc.category AS classification_category,
        wc.period AS classification_period,
        wc.date_range AS classification_date_range,
        wc.authorship_status AS classification_authorship_status,
        wc.popularity_score AS classification_popularity_score,
        wc.popularity_tier AS classification_popularity_tier,
        {scope} AS classification_scope,
        {scope_score} AS classification_scope_popularity_score,
        {scope_tier} AS classification_scope_popularity_tier,
        {discovery_group} AS classification_discovery_group_id,
        {discovery_tags} AS classification_discovery_tags,
        {global_score} AS classification_global_popularity_score,
        {global_tier} AS classification_global_popularity_tier,
        {group_score} AS classification_group_popularity_score,
        {group_tier} AS classification_group_popularity_tier,
        wc.confidence AS classification_confidence,
        wc.note AS classification_notes,
        wc.generator_models AS classification_generator_models,
        wc.generator_run_id AS classification_generator_run_id,
        wc.source_file AS classification_source_file
    """


def _null_work_classification_select_columns() -> str:
    return """
        NULL::VARCHAR AS classification_category,
        NULL::VARCHAR AS classification_period,
        NULL::VARCHAR AS classification_date_range,
        NULL::VARCHAR AS classification_authorship_status,
        NULL::INTEGER AS classification_popularity_score,
        NULL::VARCHAR AS classification_popularity_tier,
        NULL::VARCHAR AS classification_scope,
        NULL::INTEGER AS classification_scope_popularity_score,
        NULL::VARCHAR AS classification_scope_popularity_tier,
        NULL::VARCHAR AS classification_discovery_group_id,
        NULL::VARCHAR AS classification_discovery_tags,
        NULL::INTEGER AS classification_global_popularity_score,
        NULL::VARCHAR AS classification_global_popularity_tier,
        NULL::INTEGER AS classification_group_popularity_score,
        NULL::VARCHAR AS classification_group_popularity_tier,
        NULL::VARCHAR AS classification_confidence,
        NULL::VARCHAR AS classification_notes,
        NULL::VARCHAR AS classification_generator_models,
        NULL::VARCHAR AS classification_generator_run_id,
        NULL::VARCHAR AS classification_source_file
    """


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
    resource = parse_ctsv2_resource(address)
    if resource is not None and resource.ref:
        resolved_work_id = resolve_work_ref(catalog_path, resource.text_id)
        if resolved_work_id:
            candidates.extend(
                f"{resolved_work_id}:{citation_path}"
                for citation_path in _citation_path_lookup_candidates(
                    catalog_path,
                    resolved_work_id,
                    resource.ref,
                )
            )
    parts = _segment_address_parts(address)
    if parts is not None:
        work_ref, citation_path = parts
        resolved_work_id = resolve_work_ref(catalog_path, work_ref)
        if resolved_work_id:
            candidates.extend(
                f"{resolved_work_id}:{candidate_path}"
                for candidate_path in _citation_path_lookup_candidates(
                    catalog_path,
                    resolved_work_id,
                    citation_path,
                )
            )
    return list(dict.fromkeys(candidates))


def _citation_path_lookup_candidates(
    catalog_path: Path,
    work_id: str,
    citation_path: str,
) -> list[str]:
    parts = [part.strip() for part in citation_path.split(".") if part.strip()]
    candidates = [citation_path]
    normalized_parts = [_numeric_citation_part(part) for part in parts]
    if (
        len(parts) >= GRANULAR_CITATION_MIN_PARTS
        and all(normalized_parts)
        and _work_accepts_drop_middle_citation_projection(catalog_path, work_id)
    ):
        candidates.append(f"{normalized_parts[0]}.{normalized_parts[-1]}")
    return list(dict.fromkeys(candidates))


def _work_accepts_drop_middle_citation_projection(catalog_path: Path, work_id: str) -> bool:
    if not catalog_path.exists():
        return False
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "citation_maps"):
            return False
        row = conn.execute(
            """
            SELECT 1
            FROM citation_maps
            WHERE work_id = ?
              AND status = 'accepted'
              AND projection_rule = 'drop_middle_numeric_part'
              AND source_pattern = 'book.chapter.section'
              AND machine_pattern = 'book.section'
            LIMIT 1
            """,
            [work_id],
        ).fetchone()
    return row is not None


def _numeric_citation_part(part: str) -> str | None:
    value = part.strip()
    if value.isdigit():
        return value
    normalized = value.casefold()
    if not ROMAN_CITATION_RE.fullmatch(normalized):
        return None
    return str(_roman_citation_to_int(normalized))


def _roman_citation_to_int(value: str) -> int:
    total = 0
    previous = 0
    for character in reversed(value):
        current = ROMAN_CITATION_VALUES[character]
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return total


def _address_work_id_from_artifacts(address: str, artifacts: list[dict[str, Any]]) -> str | None:
    matches = {
        str(artifact["work_id"])
        for artifact in artifacts
        if address.startswith(f"{artifact['work_id']}:")
    }
    if not matches:
        return _cts_work_id(address)
    return max(matches, key=lambda match: len(match))


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
    had_work_scoped_candidate = False
    for candidate in candidates:
        work_id = _address_work_id_from_artifacts(candidate, artifacts)
        if work_id is not None:
            had_work_scoped_candidate = True
            for artifact in artifacts:
                if artifact["work_id"] == work_id and _book_has_address(
                    Path(str(artifact["artifact_path"])),
                    candidate,
                ):
                    return artifact, candidate
    if had_work_scoped_candidate:
        return None

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
    _attach_segment_canonical_address(catalog_path, segment)
    return segment


def lookup_segments_by_citation_reference(
    catalog_path: Path,
    citation_ref: str,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    normalized_ref = normalize_citation_reference(citation_ref)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "citation_references"):
            return []
        rows = _dict_rows(
            conn,
            """
            SELECT work_id, segment_id, citation_path, citation_ref, normalized_ref,
                   source_kind, source_path, sort_key
            FROM citation_references
            WHERE normalized_ref = ?
            ORDER BY sort_key, work_id, segment_id
            """,
            [normalized_ref],
        )
    segments: list[dict[str, Any]] = []
    seen_segment_ids: set[str] = set()
    for row in rows:
        segment_id = str(row["segment_id"])
        if segment_id in seen_segment_ids:
            continue
        seen_segment_ids.add(segment_id)
        segment = lookup_segment_by_address(
            catalog_path, f"{row['work_id']}:{row['citation_path']}"
        )
        if segment is None:
            continue
        segment["citation_reference"] = row
        segments.append(segment)
    return segments


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
    resource = parse_ctsv2_resource(work_ref)
    if resource is not None:
        work_ref = resource.text_id
    alias = lookup_alias(catalog_path, work_ref)
    if alias is not None:
        target = alias.get("target")
        if target is None:
            return None
        target_text = str(target)
        if target_text == work_ref:
            return _resolve_work_ref_without_alias(catalog_path, target_text) or target_text
        resolved_target = _resolve_work_ref_without_alias(catalog_path, target_text)
        return resolved_target or target_text
    if not catalog_path.exists():
        return None
    return _resolve_work_ref_without_alias(catalog_path, work_ref)


def _resolve_work_ref_without_alias(catalog_path: Path, work_ref: str) -> str | None:
    if not catalog_path.exists():
        return None
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        columns = _table_columns(conn, "works")
        canonical_condition = " OR canonical_text_id = ?" if "canonical_text_id" in columns else ""
        params: list[object] = [work_ref, work_ref]
        if canonical_condition:
            params.append(work_ref)
        params.append(work_ref)
        row = conn.execute(
            f"""
            SELECT work_id
            FROM works
            WHERE work_id = ? OR cts_work_urn = ?{canonical_condition}
            ORDER BY CASE WHEN work_id = ? THEN 0 ELSE 1 END, work_id
            LIMIT 1
            """,
            params,
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
        item = {
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
        _attach_work_display_labels([item])
        return item
    work_id = resolve_work_ref(catalog_path, work_ref)
    if not work_id:
        return None
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        canonical_select = (
            "canonical_text_id"
            if "canonical_text_id" in _table_columns(conn, "works")
            else "NULL::VARCHAR AS canonical_text_id"
        )
        rows = _dict_rows(
            conn,
            f"""
            SELECT
                work_id, collection_id, language, title, author, author_id, source_id,
                cts_work_urn, {canonical_select}
            FROM works
            WHERE work_id = ?
            LIMIT 1
            """,
            [work_id],
        )
    if not rows:
        return None
    item = {**rows[0], "work_kind": "work"}
    _attach_work_display_labels([item])
    return item


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
            segment = {
                **rows[0],
                "address": address,
                "address_kind": "langnet",
                "artifact": artifact,
            }
            _attach_segment_canonical_address(catalog_path, segment)
            return segment
    return None


def _attach_segment_canonical_address(catalog_path: Path, segment: dict[str, Any]) -> None:
    work = get_work(catalog_path, str(segment.get("work_id") or ""))
    canonical_text_id = str(work.get("canonical_text_id") or "") if work else ""
    if not canonical_text_id:
        return
    citation_path = str(segment.get("citation_path") or "")
    segment["canonical_text_id"] = canonical_text_id
    segment["canonical_address"] = ctsv2_segment_address(canonical_text_id, citation_path)


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
    base_address = (
        str(work.get("canonical_text_id"))
        if work and work.get("canonical_text_id")
        else str(work.get("cts_work_urn"))
        if work and work.get("cts_work_urn")
        else work_id
    )
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
        "address": (
            ctsv2_segment_address(base_address, citation_path)
            if base_address.startswith("urn:ctsv2:")
            else f"{base_address}:{citation_path}"
        ),
    }


def list_collections(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = _dict_rows(
            conn,
            """
            WITH work_metrics AS (
                SELECT
                    work_id,
                    COALESCE(SUM(segment_count), 0) AS segment_count,
                    COALESCE(SUM(token_count), 0) AS word_count
                FROM artifacts
                GROUP BY work_id
            )
            SELECT
                w.collection_id,
                COUNT(*) AS work_count,
                COALESCE(SUM(m.segment_count), 0) AS segment_count,
                COALESCE(SUM(m.word_count), 0) AS word_count,
                'whitespace_tokens' AS word_count_method
            FROM works w
            LEFT JOIN work_metrics m ON m.work_id = w.work_id
            GROUP BY w.collection_id
            ORDER BY collection_id
            """,
        )
    for row in rows:
        row.update(_collection_display_metadata(str(row["collection_id"])))
    return rows


def _collection_display_metadata(collection_id: str) -> dict[str, str]:
    metadata = {
        "digiliblt": (
            "Digital Library of Late-Antique Latin Texts",
            "Late antique Latin texts from the DigilibLT corpus.",
        ),
        "first1kgreek": (
            "First1K Greek",
            "Greek texts from the First Thousand Years of Greek corpus.",
        ),
        "opengreekandlatin_church_fathers": (
            "OpenGreekAndLatin Church Fathers",
            "Greek patristic and biblical editions imported from OpenGreekAndLatin.",
        ),
        "opengreekandlatin_csel": (
            "Corpus Scriptorum Ecclesiasticorum Latinorum",
            "Latin Christian texts from the OpenGreekAndLatin CSEL corpus.",
        ),
        "opengreekandlatin_latin": (
            "OpenGreekAndLatin Latin",
            "Latin texts from OpenGreekAndLatin outside the larger CSEL and Patrologia collections.",
        ),
        "opengreekandlatin_patrologia": (
            "Patrologia Latina",
            "Latin patristic and medieval texts from the OpenGreekAndLatin Patrologia Latina corpus.",
        ),
        "perseus": (
            "Perseus",
            "Greek and Latin texts from the Perseus corpus.",
        ),
        "phi": (
            "PHI Latin",
            "Classical Latin texts from the PHI corpus.",
        ),
        "sanskrit_dcs": (
            "DCS Sanskrit",
            "Sanskrit reader texts imported from the Digital Corpus of Sanskrit.",
        ),
        "sanskrit_json": (
            "Sanskrit JSON",
            "Sanskrit reader texts imported from local structured JSON sources.",
        ),
        "sanskrit_texts": (
            "Sanskrit Texts",
            "Sanskrit reader texts imported from local plain-text sources.",
        ),
        "tlg": (
            "TLG Greek",
            "Greek texts from the TLG corpus.",
        ),
    }
    label, description = metadata.get(
        collection_id,
        (collection_id.replace("_", " ").title(), "Reader corpus collection."),
    )
    return {"label": label, "description": description}


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
        rows = _dict_rows(
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
    _add_contained_word_counts_to_author_rows(catalog_path, rows)
    return rows


def _add_contained_word_counts_to_author_rows(
    catalog_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "contained_works"):
            return
        contained_rows = _dict_rows(
            conn,
            """
            SELECT DISTINCT author, language, parent_work_id, start_citation, end_citation
            FROM contained_works
            WHERE status = 'accepted'
            """,
        )
    for contained in contained_rows:
        word_count = _word_count_for_citation_range(
            catalog_path,
            str(contained["parent_work_id"]),
            str(contained["start_citation"]),
            str(contained["end_citation"]),
        )
        for row in rows:
            if (
                str(row.get("source_author_id") or "") == ""
                and str(row.get("author") or "") == str(contained["author"])
                and str(row.get("language") or "") == str(contained["language"])
            ):
                row["word_count"] = int(row.get("word_count") or 0) + word_count
                row["word_count_method"] = "whitespace_tokens"


def list_author_index(  # noqa: PLR0913
    catalog_path: Path,
    *,
    language: str | None = None,
    section: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    agent_kind: str | None = None,
    historicity: str | None = None,
    sort: str = "catalog",
) -> list[dict[str, Any]]:
    rows = _raw_author_rows(catalog_path, language=language)
    items = [author_index_entry(row) for row in rows]
    items = _merge_duplicate_author_selectors(items)
    _disambiguate_duplicate_author_displays(catalog_path, items)
    _attach_author_classifications(catalog_path, items)
    _attach_canonical_author_authorities(items)
    if section:
        section_key = normalize_section_key(language, section)
        items = [item for item in items if item["section_key"] == section_key]
    if agent_kind:
        items = [item for item in items if item.get("author_agent_kind") == agent_kind]
    if historicity:
        items = [item for item in items if item.get("author_historicity_status") == historicity]
    if query:
        items = [
            item
            for item in items
            if _author_query_matches(
                query,
                item["index_name"],
                item["display_name"],
                item["author"],
                item["author_id"],
                item.get("source_author_id"),
                item.get("source_author_name"),
                item.get("canonical_author_id"),
                item.get("canonical_author_name"),
                item.get("author_canonical_name"),
                *item["alternate_names"],
            )
        ]
    if sort == "prominence":
        items.sort(key=_author_prominence_sort_key)
    else:
        items.sort(key=lambda item: (item["language"], item["sort_key"], item["display_name"]))
    if limit is None:
        return items[offset:]
    return items[offset : offset + limit]


def _author_prominence_sort_key(item: Mapping[str, Any]) -> tuple[object, ...]:
    score = item.get("author_prominence_score")
    return (
        score is None,
        -(int(score) if score is not None else 0),
        _author_prominence_tier_rank(str(item.get("author_prominence_tier") or "")),
        -(int(item.get("work_count") or 0)),
        -(int(item.get("word_count") or 0)),
        item["language"],
        item["sort_key"],
        item["display_name"],
    )


def _author_prominence_tier_rank(tier: str) -> int:
    return {
        "canonical": 0,
        "major": 1,
        "common": 2,
        "specialist": 3,
        "minor": 4,
    }.get(tier.casefold(), 9)


def _merge_duplicate_author_selectors(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        raw_identity = str(item.get("source_author_id") or item["author_id"])
        identity = compact_author_id(raw_identity) or raw_identity
        key = (str(item["language"]), identity)
        existing = merged_by_key.get(key)
        if existing is None:
            merged_by_key[key] = dict(item)
            continue
        chosen = _preferred_author_display_item(existing, item)
        existing.update(
            {
                "display_name": chosen["display_name"],
                "author": chosen["author"],
                "index_name": chosen["index_name"],
                "native_name": chosen["native_name"],
                "section_key": chosen["section_key"],
                "sort_key": chosen["sort_key"],
            }
        )
        existing["work_count"] = int(existing.get("work_count") or 0) + int(
            item.get("work_count") or 0
        )
        existing["word_count"] = int(existing.get("word_count") or 0) + int(
            item.get("word_count") or 0
        )
        existing["representative_titles"] = _merge_representative_titles(
            str(existing.get("representative_titles") or ""),
            str(item.get("representative_titles") or ""),
        )
        existing["alternate_names"] = sorted(
            {
                *[str(name) for name in existing.get("alternate_names", [])],
                *[str(name) for name in item.get("alternate_names", [])],
                str(item.get("display_name") or ""),
            }
            - {""}
        )
    return list(merged_by_key.values())


def _preferred_author_display_item(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    left_name = str(left.get("display_name") or "")
    right_name = str(right.get("display_name") or "")
    left_score = (
        sum(ord(char) > ASCII_MAX_CODEPOINT for char in left_name),
        len(left_name),
    )
    right_score = (
        sum(ord(char) > ASCII_MAX_CODEPOINT for char in right_name),
        len(right_name),
    )
    return right if right_score > left_score else left


def _merge_representative_titles(*values: str) -> str:
    titles: list[str] = []
    seen: set[str] = set()
    for value in values:
        for title in value.split(" | "):
            normalized = title.strip()
            if not normalized or normalized.casefold() in seen:
                continue
            seen.add(normalized.casefold())
            titles.append(normalized)
    return " | ".join(titles[:8])


def _author_query_matches(query: str, *values: object) -> bool:
    raw_query = query.casefold()
    folded_queries = _author_search_variants(query)
    if not raw_query and not folded_queries:
        return False
    for value in values:
        raw_value = str(value or "").casefold()
        if raw_query and raw_query in raw_value:
            return True
        folded_values = _author_search_variants(value)
        if any(
            query_value and query_value in candidate
            for query_value in folded_queries
            for candidate in folded_values
        ):
            return True
    return False


def _author_search_variants(value: object) -> set[str]:
    key = author_search_key(value)
    if not key:
        return set()
    variants = {key}
    variants.add(key.replace("mk", "nk").replace("mg", "ng"))
    variants.add(key.replace("nk", "mk").replace("ng", "mg"))
    return variants


def _attach_author_classifications(
    catalog_path: Path,
    items: list[dict[str, Any]],
) -> None:
    for item in items:
        item.setdefault("author_canonical_name", "")
        item.setdefault("author_agent_kind", "")
        item.setdefault("author_historicity_status", "")
        item.setdefault("author_period", "")
        item.setdefault("author_date_range", "")
        item.setdefault("author_region", "")
        item.setdefault("author_cultural_context", "")
        item.setdefault("author_bio", "")
        item.setdefault("author_prominence_score", None)
        item.setdefault("author_prominence_tier", "")
        item.setdefault("author_classification_confidence", "")
        item.setdefault("author_classification_notes", "")
        item.setdefault("author_classification_source_author_id", "")
        item.setdefault("author_generator_models", "")
        item.setdefault("author_generator_run_id", "")
        item.setdefault("author_classification_source_file", "")
    if not items or not catalog_path.exists():
        return
    languages = sorted({str(item["language"]) for item in items})
    if not languages:
        return
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "author_classifications"):
            return
        rows = _dict_rows(
            conn,
            f"""
            SELECT
                author_id, language, source_author_id,
                canonical_name, agent_kind, historicity_status,
                period, date_range, region, cultural_context, bio,
                prominence_score, prominence_tier,
                confidence, note, generator_models, generator_run_id, source_file
            FROM author_classifications
            WHERE language IN ({", ".join("?" for _ in languages)})
            """,
            languages,
        )
    by_key = {(str(row["author_id"]), str(row["language"])): row for row in rows}
    for item in items:
        row = by_key.get((str(item["author_id"]), str(item["language"])))
        if row is None:
            continue
        item["author_canonical_name"] = row["canonical_name"]
        item["author_classification_source_author_id"] = row["source_author_id"]
        item["author_agent_kind"] = row["agent_kind"]
        item["author_historicity_status"] = row["historicity_status"]
        item["author_period"] = row["period"]
        item["author_date_range"] = row["date_range"]
        item["author_region"] = row["region"]
        item["author_cultural_context"] = row["cultural_context"]
        item["author_bio"] = row["bio"]
        item["author_prominence_score"] = row["prominence_score"]
        item["author_prominence_tier"] = row["prominence_tier"]
        item["author_classification_confidence"] = row["confidence"]
        item["author_classification_notes"] = row["note"]
        item["author_generator_models"] = row["generator_models"]
        item["author_generator_run_id"] = row["generator_run_id"]
        item["author_classification_source_file"] = row["source_file"]


def _attach_canonical_author_authorities(items: list[dict[str, Any]]) -> None:
    for item in items:
        source_author_id = str(item.get("source_author_id") or "")
        source_author_name = _source_author_display_name(
            str(item.get("collection_id") or ""),
            source_author_id,
            str(item.get("display_name") or item.get("author") or "Unknown"),
        )
        agent_kind = str(item.get("author_agent_kind") or "")
        item["source_author_name"] = source_author_name
        item["source_author_kind"] = agent_kind
        item["source_author_canonical_name"] = item.get("author_canonical_name", "")
        item["source_author_period"] = item.get("author_period", "")
        item["source_author_date_range"] = item.get("author_date_range", "")
        item["source_author_region"] = item.get("author_region", "")
        item["source_author_cultural_context"] = item.get("author_cultural_context", "")
        item["source_author_bio"] = item.get("author_bio", "")
        item["source_author_prominence_score"] = item.get("author_prominence_score")
        item["source_author_prominence_tier"] = item.get("author_prominence_tier", "")
        item["source_author_classification_notes"] = item.get("author_classification_notes", "")
        if author_kind_uses_unknown_authority(agent_kind):
            item["canonical_author_id"] = canonical_unknown_author_id(
                str(item.get("language") or "")
            )
            item["canonical_author_name"] = "Unknown"
            item["canonical_author_kind"] = "anonymous_label"
            item["author_canonical_name"] = "Unknown"
            if not _is_plain_unknown_author_heading(source_author_name, source_author_id):
                item["author_period"] = ""
                item["author_date_range"] = ""
                item["author_region"] = ""
                item["author_cultural_context"] = ""
                item["author_bio"] = ""
                item["author_prominence_score"] = None
                item["author_prominence_tier"] = ""
        else:
            canonical_name = str(
                item.get("author_canonical_name") or source_author_name or "Unknown"
            )
            item["canonical_author_id"] = canonical_author_id_for_source(
                str(item.get("language") or ""),
                source_author_id,
                str(item.get("author_id") or ""),
                canonical_name,
            )
            item["canonical_author_name"] = canonical_name
            item["canonical_author_kind"] = agent_kind
        item["author"] = item["canonical_author_name"]


def _is_plain_unknown_author_heading(
    source_author_name: str,
    source_author_id: str,
) -> bool:
    if source_author_id.strip():
        return False
    return source_author_name.strip().casefold() in {"unknown", "anonymous"}


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
                "word_count": 0,
                "word_count_method": "whitespace_tokens",
            },
        )
        section["author_count"] = int(section["author_count"]) + 1
        section["work_count"] = int(section["work_count"]) + int(item["work_count"])
        section["word_count"] = int(section["word_count"]) + int(item.get("word_count") or 0)
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
        conditions.append("s.language = ?")
        params.append(language)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        contained_union = ""
        if _table_exists(conn, "contained_works"):
            contained_union = """
                UNION ALL
                SELECT DISTINCT
                    contained_work_id AS work_id,
                    title,
                    author,
                    '' AS source_author_id,
                    language,
                    0 AS word_count,
                    0 AS popularity_score
                FROM contained_works
                WHERE status = 'accepted'
            """
        classification_join = ""
        popularity_score_sql = "0 AS popularity_score"
        if _table_exists(conn, "work_classifications"):
            classification_join = "LEFT JOIN work_classifications c ON c.work_id = w.work_id"
            classification_columns = _table_columns(conn, "work_classifications")
            popularity_expressions = [
                f"c.{column}"
                for column in (
                    "global_popularity_score",
                    "popularity_score",
                    "group_popularity_score",
                )
                if column in classification_columns
            ]
            popularity_score_sql = (
                f"COALESCE({', '.join(popularity_expressions)}, 0) AS popularity_score"
                if popularity_expressions
                else "0 AS popularity_score"
            )
        rows = _dict_rows(
            conn,
            f"""
            WITH work_metrics AS (
                SELECT
                    work_id,
                    COALESCE(SUM(token_count), 0) AS word_count
                FROM artifacts
                GROUP BY work_id
            ),
            base_author_work_rows AS (
                SELECT
                    w.work_id,
                    w.title,
                    coalesce(w.author_id, '') AS source_author_id,
                    w.author,
                    w.language,
                    COALESCE(m.word_count, 0) AS word_count,
                    {popularity_score_sql}
                FROM works w
                LEFT JOIN work_metrics m ON m.work_id = w.work_id
                {classification_join}
            ),
            author_work_rows AS (
                SELECT
                    work_id,
                    title,
                    author,
                    source_author_id,
                    language,
                    word_count,
                    popularity_score
                FROM base_author_work_rows
                {contained_union}
            ),
            author_summary_rows AS (
                SELECT
                    source_author_id,
                    author,
                    language,
                    COUNT(DISTINCT work_id) AS work_count,
                    COALESCE(SUM(word_count), 0) AS word_count
                FROM author_work_rows
                GROUP BY source_author_id, author, language
            ),
            representative_title_rows AS (
                SELECT
                    source_author_id,
                    author,
                    language,
                    title,
                    MAX(popularity_score) AS popularity_score,
                    MAX(word_count) AS word_count
                FROM author_work_rows
                WHERE title IS NOT NULL AND trim(title) != ''
                GROUP BY source_author_id, author, language, title
            ),
            ranked_title_rows AS (
                SELECT
                    *,
                    row_number() OVER (
                        PARTITION BY source_author_id, author, language
                        ORDER BY popularity_score DESC, word_count DESC, title
                    ) AS representative_rank
                FROM representative_title_rows
            )
            SELECT
                s.source_author_id,
                s.author,
                s.language,
                s.work_count,
                s.word_count,
                'whitespace_tokens' AS word_count_method,
                COALESCE(
                    string_agg(t.title, ' | ' ORDER BY t.representative_rank),
                    ''
                ) AS representative_titles
            FROM author_summary_rows s
            LEFT JOIN ranked_title_rows t
                ON t.source_author_id = s.source_author_id
                AND t.author = s.author
                AND t.language = s.language
                AND t.representative_rank <= 8
            {where}
            GROUP BY s.source_author_id, s.author, s.language, s.work_count, s.word_count
            ORDER BY s.language, s.author
            """,
            params,
        )
    _add_contained_word_counts_to_author_rows(catalog_path, rows)
    return rows


AUTHORSHIP_RELATION_TYPES = (
    "attributed_author",
    "possible_author",
    "traditional_author",
    "misattributed_author",
    "translator",
)
SOURCE_METADATA_SUMMARY_KEYS = (
    "dcs_scope_hint",
    "dcs_subject",
    "dcs_time_slot",
    "dcs_author",
    "dcs_completed",
    "gretil_text",
    "gretil_author",
    "gretil_edition",
    "gretil_comments",
    "gretil_notes",
    "gretil_data_entry",
    "perseus_subject",
    "perseus_author",
    "perseus_editor",
    "perseus_translator",
    "perseus_year_published",
    "perseus_language",
)


def list_works(  # noqa: C901, PLR0912, PLR0913, PLR0915
    catalog_path: Path,
    *,
    language: str | None = None,
    collection_id: str | None = None,
    author: str | None = None,
    attributed_to: str | None = None,
    author_id: str | None = None,
    classification_scope: str | None = None,
    classification_group: str | None = None,
    classification_tag: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    sort: str = "catalog",
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as schema_conn:
        works_columns = _table_columns(schema_conn, "works")
    has_canonical_text_id = "canonical_text_id" in works_columns
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
    post_author_filter = _uses_post_author_filter(author_id)
    if author_id and not post_author_filter:
        author_id_key = author_id.casefold()
        compact_author_key = compact_author_id(author_id).casefold()
        conditions.append(
            """
            (
                lower(coalesce(author_id, '')) = ?
                OR lower(coalesce(author_id, '')) = ?
                OR lower(coalesce(author_id, '')) LIKE ?
                OR lower(coalesce(source_id, '')) LIKE ?
                OR lower(coalesce(source_id, '')) LIKE ?
                OR lower(coalesce(cts_work_urn, '')) LIKE ?
            )
            """
        )
        where_params.extend(
            [
                author_id_key,
                compact_author_key,
                f"%:{compact_author_key}",
                f"{author_id_key}.%",
                f"{compact_author_key}.%",
                f"{author_id_key}.%",
            ]
        )
    if query:
        query_like = f"%{query.lower()}%"
        canonical_query_sql = (
            "OR lower(coalesce(canonical_text_id, '')) LIKE ?" if has_canonical_text_id else ""
        )
        conditions.append(
            f"""
            (
                lower(title) LIKE ?
                OR lower(author) LIKE ?
                OR lower(works.work_id) LIKE ?
                OR lower(source_id) LIKE ?
                OR lower(coalesce(cts_work_urn, '')) LIKE ?
                {canonical_query_sql}
                OR EXISTS (
                    SELECT 1
                    FROM aliases al
                    WHERE (al.target = works.work_id OR al.target = works.cts_work_urn)
                      AND (lower(al.alias) LIKE ? OR lower(al.display) LIKE ?)
                )
            )
            """
        )
        where_params.extend([query_like] * (8 if has_canonical_text_id else 7))
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
                    OR (
                        a.match_field = 'author_id'
                        AND (
                            lower(a.match_value) = lower(coalesce(w.author_id, ''))
                            OR lower(a.match_value) = lower(regexp_extract(w.source_id, '^[^.]+'))
                            OR lower(coalesce(w.author_id, '')) LIKE '%:' || lower(a.match_value)
                        )
                    )
                )
                WHERE a.status = 'accepted'
                  AND a.relation_type IN (?, ?, ?, ?, ?)
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
            + ") OR works.work_id IN (SELECT work_id FROM attribution_work_ids))"
        )
        where_params.append(f"%{attributed_to.lower()}%")
    should_limit_base_query = limit is not None and not post_author_filter and not include_contained
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
        if _table_exists(conn, "work_classifications"):
            classification_table_columns = _table_columns(conn, "work_classifications")
            if classification_group:
                group_key = classification_group.lower()
                if "discovery_group_id" in classification_table_columns:
                    conditions.append("lower(coalesce(wc.discovery_group_id, '')) = ?")
                    where_params.append(group_key)
                elif "scope" in classification_table_columns:
                    conditions.append(
                        """
                        (
                            lower(coalesce(wc.scope, '')) LIKE ?
                            OR lower(coalesce(wc.category, '')) LIKE ?
                        )
                        """
                    )
                    group_like = f"%{group_key}%"
                    where_params.extend([group_like, group_like])
                else:
                    return []
            if classification_tag:
                if not _table_exists(conn, "work_classification_tags"):
                    return []
                conditions.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM work_classification_tags wct
                        WHERE wct.work_id = works.work_id
                          AND lower(wct.tag_id) = ?
                    )
                    """
                )
                where_params.append(classification_tag.lower())
            if classification_scope:
                if "scope" not in classification_table_columns:
                    return []
                scope_like = f"%{classification_scope.lower()}%"
                conditions.append(
                    """
                    (
                        lower(coalesce(wc.scope, '')) LIKE ?
                        OR lower(coalesce(wc.category, '')) LIKE ?
                    )
                    """
                )
                where_params.extend([scope_like, scope_like])
            classification_columns = _work_classification_select_columns(
                classification_table_columns
            )
            classification_join = """
                LEFT JOIN work_classifications wc ON wc.work_id = works.work_id
            """
        else:
            if classification_scope or classification_group or classification_tag:
                return []
            classification_columns = _null_work_classification_select_columns()
            classification_join = ""
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        order_sql = (
            """
            ORDER BY
                {popularity_score_column} IS NULL,
                {popularity_score_column} DESC,
                language, author, title, works.work_id
            """.format(
                popularity_score_column=(
                    "classification_group_popularity_score"
                    if sort == "group-popularity" or classification_group or classification_tag
                    else "classification_global_popularity_score"
                    if sort == "global-popularity"
                    else "classification_scope_popularity_score"
                    if classification_scope
                    else "classification_popularity_score"
                )
            )
            if sort in {"popularity", "global-popularity", "group-popularity"}
            else "ORDER BY language, author, title, works.work_id"
        )
        canonical_text_select = (
            "canonical_text_id" if has_canonical_text_id else "NULL::VARCHAR AS canonical_text_id"
        )
        rows = _dict_rows(
            conn,
            f"""
            {attribution_cte}
            SELECT
                works.work_id, collection_id, language, title, author, author_id, source_id,
                cts_work_urn,
                {canonical_text_select},
                'work' AS work_kind, NULL::VARCHAR AS parent_work_id,
                NULL::VARCHAR AS start_citation, NULL::VARCHAR AS end_citation,
                COALESCE(metrics.word_count, 0) AS word_count,
                'whitespace_tokens' AS word_count_method,
                {classification_columns}
            FROM works
            LEFT JOIN (
                SELECT work_id, COALESCE(SUM(token_count), 0) AS word_count
                FROM artifacts
                GROUP BY work_id
            ) metrics ON metrics.work_id = works.work_id
            {classification_join}
            {where}
            {order_sql}
            {limit_sql}
            """,
            [*cte_params, *where_params],
        )
    if include_contained:
        rows.extend(
            _list_contained_work_rows(
                catalog_path,
                language=language,
                author=author,
                author_id=None if post_author_filter else author_id,
                query=query,
                classification_scope=classification_scope,
                classification_group=classification_group,
                classification_tag=classification_tag,
            )
        )
        rows.sort(
            key=(
                _work_sort_key_group_popularity
                if sort == "group-popularity" or classification_group or classification_tag
                else _work_sort_key_global_popularity
                if sort == "global-popularity"
                else _work_sort_key_scope_popularity
                if sort == "popularity" and classification_scope
                else _work_sort_key_popularity
                if sort in {"popularity", "global-popularity", "group-popularity"}
                else _work_sort_key_catalog
            )
        )
    _attach_work_author_authorities(catalog_path, rows)
    if post_author_filter and author_id:
        rows = [row for row in rows if _work_author_matches_requested_id(row, author_id)]
    if include_contained or post_author_filter:
        rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
    _attach_source_metadata_summaries(catalog_path, rows)
    _attach_work_metadata_attributions(catalog_path, rows)
    _attach_work_display_labels(rows)
    return rows


def list_discovery_group_summaries(
    catalog_path: Path,
    *,
    language: str | None = None,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "work_classifications"):
            return []
        columns = _table_columns(conn, "work_classifications")
        if "discovery_group_id" not in columns:
            return []
        contained_union = _contained_discovery_work_rows_union(conn)
        conditions = ["coalesce(wc.discovery_group_id, '') <> ''"]
        params: list[object] = []
        if language:
            conditions.append("w.language = ?")
            params.append(language)
        rows = _dict_rows(
            conn,
            f"""
            WITH discovery_work_rows AS (
                SELECT work_id, author_id, author, language
                FROM works
                {contained_union}
            )
            SELECT
                wc.discovery_group_id AS id,
                COUNT(DISTINCT w.work_id) AS work_count,
                COUNT(DISTINCT w.work_id) AS classified_work_count,
                COUNT(
                    DISTINCT CASE
                        WHEN coalesce(w.author_id, '') <> '' THEN w.author_id
                        WHEN trim(coalesce(w.author, '')) <> ''
                         AND lower(trim(w.author)) <> 'unknown' THEN w.author
                        ELSE NULL
                    END
                ) AS author_count,
                MAX(wc.group_popularity_score) AS max_group_popularity_score
            FROM discovery_work_rows w
            JOIN work_classifications wc ON wc.work_id = w.work_id
            WHERE {" AND ".join(conditions)}
            GROUP BY wc.discovery_group_id
            """,
            params,
        )
    return _merge_discovery_counts(rows, DISCOVERY_GROUPS)


def _contained_discovery_work_rows_union(conn: Any) -> str:
    if not _table_exists(conn, "contained_works"):
        return ""
    return """
        UNION ALL
        SELECT DISTINCT
            contained_work_id AS work_id,
            NULL::VARCHAR AS author_id,
            author,
            language
        FROM contained_works
        WHERE status = 'accepted'
    """


def list_discovery_tag_summaries(
    catalog_path: Path,
    *,
    language: str | None = None,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "work_classifications"):
            return []
        columns = _table_columns(conn, "work_classifications")
        if "discovery_tags" not in columns:
            return []
        contained_union = _contained_discovery_work_rows_union(conn)
        conditions = ["coalesce(wc.discovery_tags, '') <> ''"]
        params: list[object] = []
        if language:
            conditions.append("w.language = ?")
            params.append(language)
        rows = _dict_rows(
            conn,
            f"""
            WITH discovery_work_rows AS (
                SELECT work_id, author_id, author, language
                FROM works
                {contained_union}
            )
            SELECT
                w.work_id,
                w.author_id,
                w.author,
                wc.discovery_tags,
                wc.group_popularity_score
            FROM discovery_work_rows w
            JOIN work_classifications wc ON wc.work_id = w.work_id
            WHERE {" AND ".join(conditions)}
            """,
            params,
        )
    counts: dict[str, dict[str, Any]] = {}
    for row in rows:
        work_id = str(row["work_id"])
        author_identity = _reader_author_count_identity(
            row.get("author_id"),
            row.get("author"),
        )
        group_score = row.get("group_popularity_score")
        for tag_id in normalize_discovery_tags(row.get("discovery_tags")):
            if tag_id not in DISCOVERY_TAGS:
                continue
            summary = counts.setdefault(
                tag_id,
                {
                    "id": tag_id,
                    "work_ids": set(),
                    "author_ids": set(),
                    "max_group_popularity_score": None,
                },
            )
            summary["work_ids"].add(work_id)
            if author_identity:
                summary["author_ids"].add(author_identity)
            if group_score is not None and (
                summary["max_group_popularity_score"] is None
                or int(group_score) > int(summary["max_group_popularity_score"])
            ):
                summary["max_group_popularity_score"] = int(group_score)
    rows_for_merge = [
        {
            "id": tag_id,
            "work_count": len(summary["work_ids"]),
            "classified_work_count": len(summary["work_ids"]),
            "author_count": len(summary["author_ids"]),
            "max_group_popularity_score": summary["max_group_popularity_score"],
        }
        for tag_id, summary in counts.items()
    ]
    return _merge_discovery_counts(rows_for_merge, DISCOVERY_TAGS)


def _reader_author_count_identity(author_id: object, author: object) -> str:
    clean_author_id = str(author_id or "").strip()
    if clean_author_id:
        return clean_author_id
    clean_author = str(author or "").strip()
    if clean_author and clean_author.casefold() != "unknown":
        return clean_author
    return ""


def list_discovery_shelves(
    catalog_path: Path,
    *,
    language: str | None = None,
    limit: int | None = None,
    sample_limit: int = 3,
) -> list[dict[str, Any]]:
    groups = list_discovery_group_summaries(catalog_path, language=language)
    if limit is not None:
        groups = groups[:limit]
    group_ids = [str(group["id"]) for group in groups]
    sample_rows_by_group = _discovery_shelf_sample_works(
        catalog_path,
        language=language,
        group_ids=group_ids,
        sample_limit=sample_limit,
    )
    shelves: list[dict[str, Any]] = []
    for group in groups:
        group_id = str(group["id"])
        sample_rows = sample_rows_by_group.get(group_id, [])
        sample_works = [
            {
                "work_id": str(row["work_id"]),
                "title": str(row["title"]),
                "author": str(row.get("author") or ""),
                "language": str(row.get("language") or ""),
                "source_id": str(row.get("source_id") or ""),
                "source_label": str(row.get("source_label") or ""),
                "edition_label": str(row.get("edition_label") or ""),
                "short_disambiguation_label": str(row.get("short_disambiguation_label") or ""),
                "classification_group_popularity_score": row.get(
                    "classification_group_popularity_score"
                ),
            }
            for row in sample_rows
        ]
        shelves.append(
            {
                "id": group_id,
                "label": group["label"],
                "description": group["description"],
                "query": {"group": group_id, "sort": "group-popularity"},
                "work_count": group["work_count"],
                "classified_work_count": group["classified_work_count"],
                "author_count": group["author_count"],
                "max_group_popularity_score": group["max_group_popularity_score"],
                "sample_works": sample_works,
            }
        )
    return shelves


def _discovery_shelf_sample_works(
    catalog_path: Path,
    *,
    language: str | None,
    group_ids: Sequence[str],
    sample_limit: int,
) -> dict[str, list[dict[str, Any]]]:
    if not catalog_path.exists() or not group_ids or sample_limit <= 0:
        return {}
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "work_classifications"):
            return {}
        columns = _table_columns(conn, "work_classifications")
        if "discovery_group_id" not in columns:
            return {}
        contained_union = ""
        if _table_exists(conn, "contained_works"):
            contained_union = """
                UNION ALL
                SELECT DISTINCT
                    contained_work_id AS work_id,
                    title,
                    author,
                    language,
                    source_id,
                    collection_id
                FROM contained_works
                WHERE status = 'accepted'
            """
        group_frame = pl.DataFrame(
            [(group_id,) for group_id in group_ids],
            schema={"group_id": pl.Utf8},
            orient="row",
        )
        conn.register("shelf_group_ids", group_frame)
        try:
            rows = _dict_rows(
                conn,
                f"""
                WITH ranked AS (
                    SELECT
                        wc.discovery_group_id AS shelf_group_id,
                        w.work_id,
                        w.title,
                        w.author,
                        w.language,
                        w.source_id,
                        w.collection_id,
                        wc.group_popularity_score
                            AS classification_group_popularity_score,
                        row_number() OVER (
                            PARTITION BY wc.discovery_group_id
                            ORDER BY
                                wc.group_popularity_score IS NULL,
                                wc.group_popularity_score DESC,
                                wc.global_popularity_score DESC,
                                wc.popularity_score DESC,
                                w.language,
                                w.author,
                                w.title,
                                w.work_id
                        ) AS shelf_rank
                    FROM (
                        SELECT work_id, title, author, language, source_id, collection_id
                        FROM works
                        {contained_union}
                    ) w
                    JOIN work_classifications wc ON wc.work_id = w.work_id
                    JOIN shelf_group_ids s ON s.group_id = wc.discovery_group_id
                    WHERE (? IS NULL OR w.language = ?)
                )
                SELECT
                    shelf_group_id,
                    work_id,
                    title,
                    author,
                    language,
                    source_id,
                    collection_id,
                    classification_group_popularity_score
                FROM ranked
                WHERE shelf_rank <= ?
                ORDER BY shelf_group_id, shelf_rank
                """,
                [language, language, sample_limit],
            )
        finally:
            conn.unregister("shelf_group_ids")
    samples: dict[str, list[dict[str, Any]]] = {group_id: [] for group_id in group_ids}
    for row in rows:
        samples.setdefault(str(row["shelf_group_id"]), []).append(row)
    return samples


def reader_discovery_coverage(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        base_rows = _dict_rows(
            conn,
            """
            SELECT
                w.language,
                COUNT(DISTINCT w.work_id) AS work_count,
                COUNT(
                    DISTINCT CASE
                        WHEN coalesce(w.author_id, '') <> '' THEN w.author_id
                        WHEN trim(coalesce(w.author, '')) <> ''
                         AND lower(trim(w.author)) <> 'unknown' THEN w.author
                        ELSE NULL
                    END
                ) AS author_count,
                COALESCE(SUM(metrics.segment_count), 0) AS segment_count,
                COALESCE(SUM(metrics.token_count), 0) AS token_count
            FROM works w
            LEFT JOIN (
                SELECT
                    work_id,
                    SUM(segment_count) AS segment_count,
                    SUM(token_count) AS token_count
                FROM artifacts
                GROUP BY work_id
            ) metrics ON metrics.work_id = w.work_id
            GROUP BY w.language
            ORDER BY w.language
            """,
        )
        classification_rows: list[dict[str, Any]] = []
        if _table_exists(conn, "work_classifications"):
            columns = _table_columns(conn, "work_classifications")
            discovery_group = "wc.discovery_group_id" if "discovery_group_id" in columns else "''"
            discovery_tags = "wc.discovery_tags" if "discovery_tags" in columns else "''"
            classification_rows = _dict_rows(
                conn,
                f"""
                SELECT
                    w.language,
                    w.work_id,
                    {discovery_group} AS discovery_group_id,
                    {discovery_tags} AS discovery_tags
                FROM works w
                JOIN work_classifications wc ON wc.work_id = w.work_id
                """,
            )
        author_classification_rows: list[dict[str, Any]] = []
        if _table_exists(conn, "author_classifications"):
            author_classification_rows = _dict_rows(
                conn,
                """
                SELECT language, COUNT(DISTINCT author_id) AS classified_author_count
                FROM author_classifications
                GROUP BY language
                """,
            )
    classification_by_language: dict[str, dict[str, Any]] = {}
    for row in classification_rows:
        language = str(row["language"])
        stats = classification_by_language.setdefault(
            language,
            {
                "classified_work_ids": set(),
                "discoverable_work_ids": set(),
                "groups": set(),
                "tags": set(),
            },
        )
        work_id = str(row["work_id"])
        stats["classified_work_ids"].add(work_id)
        group_id = str(row.get("discovery_group_id") or "")
        tag_ids = normalize_discovery_tags(row.get("discovery_tags"))
        if group_id:
            stats["groups"].add(group_id)
        for tag_id in tag_ids:
            stats["tags"].add(tag_id)
        if group_id or tag_ids:
            stats["discoverable_work_ids"].add(work_id)
    classified_authors = {
        str(row["language"]): int(row["classified_author_count"] or 0)
        for row in author_classification_rows
    }
    items: list[dict[str, Any]] = []
    for row in base_rows:
        language = str(row["language"])
        classification = classification_by_language.get(
            language,
            {
                "classified_work_ids": set(),
                "discoverable_work_ids": set(),
                "groups": set(),
                "tags": set(),
            },
        )
        group_count = len(classification["groups"])
        tag_count = len(classification["tags"])
        classified_author_count = classified_authors.get(language, 0)
        items.append(
            {
                "language": language,
                "work_count": int(row["work_count"] or 0),
                "author_count": int(row["author_count"] or 0),
                "segment_count": int(row["segment_count"] or 0),
                "token_count": int(row["token_count"] or 0),
                "classified_work_count": len(classification["classified_work_ids"]),
                "discoverable_work_count": len(classification["discoverable_work_ids"]),
                "classified_author_count": classified_author_count,
                "group_count": group_count,
                "tag_count": tag_count,
                "has_discovery_facets": bool(group_count or tag_count),
                "has_author_classifications": classified_author_count > 0,
                "supported_reader_language": language in SUPPORTED_READER_LANGUAGES,
            }
        )
    return items


def list_source_index(  # noqa: PLR0913
    catalog_path: Path,
    *,
    collection_id: str | None = None,
    language: str | None = None,
    source_id: str | None = None,
    work_id: str | None = None,
    query: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if collection_id:
        conditions.append("w.collection_id = ?")
        params.append(collection_id)
    if language:
        conditions.append("w.language = ?")
        params.append(language)
    if source_id:
        source_like = f"%{source_id.casefold()}%"
        conditions.append(
            """
            (
                lower(w.source_id) LIKE ?
                OR lower(coalesce(w.cts_work_urn, '')) LIKE ?
                OR lower(w.work_id) LIKE ?
            )
            """
        )
        params.extend([source_like, source_like, source_like])
    if work_id:
        conditions.append("w.work_id = ?")
        params.append(work_id)
    if query:
        query_like = f"%{query.casefold()}%"
        conditions.append(
            """
            (
                lower(w.title) LIKE ?
                OR lower(w.author) LIKE ?
                OR lower(w.source_id) LIKE ?
                OR lower(w.work_id) LIKE ?
                OR lower(coalesce(w.cts_work_urn, '')) LIKE ?
                OR lower(coalesce(w.canonical_text_id, '')) LIKE ?
                OR lower(coalesce(e.label, '')) LIKE ?
                OR lower(coalesce(e.source_path, '')) LIKE ?
            )
            """
        )
        params.extend([query_like] * 8)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.extend([limit, offset])
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            f"""
            WITH artifact_metrics AS (
                SELECT
                    work_id,
                    edition_id,
                    COUNT(*) AS artifact_count,
                    COALESCE(SUM(segment_count), 0) AS segment_count,
                    COALESCE(SUM(token_count), 0) AS token_count,
                    string_agg(DISTINCT adapter, ', ' ORDER BY adapter) AS adapters,
                    string_agg(DISTINCT artifact_path, ' | ' ORDER BY artifact_path)
                        AS artifact_paths
                FROM artifacts
                GROUP BY work_id, edition_id
            ),
            witness_counts AS (
                SELECT
                    canonical_text_id,
                    COUNT(*) AS source_witness_count,
                    string_agg(DISTINCT collection_id, ', ' ORDER BY collection_id)
                        AS source_witness_collections
                FROM source_witnesses
                GROUP BY canonical_text_id
            )
            SELECT
                w.collection_id,
                w.language,
                w.work_id,
                w.title,
                w.author,
                w.author_id,
                w.source_id,
                w.cts_work_urn,
                w.canonical_text_id,
                e.edition_id,
                e.label AS edition_label,
                e.source_path,
                e.cts_edition_urn,
                coalesce(sf.file_role, '') AS file_role,
                coalesce(sf.file_status, '') AS file_status,
                coalesce(sf.source_hash, '') AS source_hash,
                sf.size_bytes,
                coalesce(am.artifact_count, 0) AS artifact_count,
                coalesce(am.segment_count, 0) AS segment_count,
                coalesce(am.token_count, 0) AS token_count,
                coalesce(am.adapters, '') AS adapters,
                coalesce(am.artifact_paths, '') AS artifact_paths,
                coalesce(wc.source_witness_count, 0) AS source_witness_count,
                coalesce(wc.source_witness_collections, '') AS source_witness_collections
            FROM works w
            LEFT JOIN editions e ON e.work_id = w.work_id
            LEFT JOIN artifact_metrics am
              ON am.work_id = w.work_id AND am.edition_id = e.edition_id
            LEFT JOIN source_files sf ON sf.source_path = e.source_path
            LEFT JOIN witness_counts wc ON wc.canonical_text_id = w.canonical_text_id
            {where}
            ORDER BY w.collection_id, w.language, w.author, w.title, e.label, w.work_id
            LIMIT ? OFFSET ?
            """,
            params,
        )


def _merge_discovery_counts(
    rows: list[dict[str, Any]],
    taxonomy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    taxonomy_order = {taxonomy_id: index for index, taxonomy_id in enumerate(taxonomy)}
    items: list[dict[str, Any]] = []
    for row in rows:
        taxonomy_id = str(row.get("id") or "")
        entry = taxonomy.get(taxonomy_id)
        if entry is None:
            continue
        items.append(
            {
                "id": taxonomy_id,
                "label": entry.label,
                "description": entry.description,
                "work_count": int(row.get("work_count") or 0),
                "classified_work_count": int(row.get("classified_work_count") or 0),
                "author_count": int(row.get("author_count") or 0),
                "max_group_popularity_score": (
                    int(row["max_group_popularity_score"])
                    if row.get("max_group_popularity_score") is not None
                    else None
                ),
            }
        )
    return sorted(
        items,
        key=lambda item: (
            -int(item["work_count"]),
            -int(item["max_group_popularity_score"] or 0),
            taxonomy_order.get(str(item["id"]), len(taxonomy_order)),
        ),
    )


def _uses_post_author_filter(author_id: str | None) -> bool:
    return bool(
        author_id
        and (
            is_synthetic_author_selector(author_id)
            or author_id.startswith("urn:cts:langnet:author")
        )
    )


def _work_author_matches_requested_id(
    row: Mapping[str, Any],
    requested_author_id: str,
) -> bool:
    requested = requested_author_id.strip()
    if not requested:
        return False
    requested_key = requested.casefold()
    row_values = (
        row.get("author_id"),
        row.get("source_author_id"),
        row.get("canonical_author_id"),
    )
    if any(requested_key == str(value or "").casefold() for value in row_values):
        return True
    requested_compact = compact_author_id(requested)
    if requested_compact and any(
        requested_compact == compact_author_id(str(value or "")) for value in row_values
    ):
        return True
    return author_selector_matches(
        selector=requested,
        language=str(row.get("language") or ""),
        source_author_id=(
            str(row.get("source_author_id")) if row.get("source_author_id") is not None else None
        ),
        author=str(row.get("source_author") or row.get("author") or ""),
    )


def _attach_work_author_authorities(
    catalog_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    languages = sorted({str(row.get("language") or "") for row in rows if row.get("language")})
    author_items: list[dict[str, Any]] = []
    for language in languages:
        author_items.extend(list_author_index(catalog_path, language=language))
    by_source_id = {
        (str(item.get("language") or ""), str(item.get("source_author_id") or "")): item
        for item in author_items
        if item.get("source_author_id")
    }
    by_source_name = {
        (
            str(item.get("language") or ""),
            str(item.get("source_author_name") or item.get("display_name") or "").casefold(),
        ): item
        for item in author_items
    }
    source_metadata_names = _source_author_metadata_names(catalog_path, rows)
    for row in rows:
        language = str(row.get("language") or "")
        display_author_id = str(row.get("author_id") or "")
        display_author_name = str(row.get("author") or "Unknown")
        source_author_id, source_author_name = _source_author_identity(
            row,
            source_metadata_names,
            fallback_author_id=display_author_id,
            fallback_author_name=display_author_name,
        )
        item = by_source_id.get((language, display_author_id)) if display_author_id else None
        if item is None:
            item = by_source_name.get((language, display_author_name.casefold()))
        row["source_author"] = source_author_name
        row["source_author_id"] = source_author_id or None
        if item is None:
            canonical_author_name = _fallback_canonical_author_name(
                row,
                source_author_id=source_author_id,
                source_author_name=source_author_name,
                fallback_author_name=display_author_name,
            )
            row["canonical_author_id"] = canonical_author_id_for_source(
                language,
                display_author_id,
                display_author_id,
                canonical_author_name,
            )
            row["canonical_author_name"] = canonical_author_name
            row["canonical_author_kind"] = ""
            row["author"] = canonical_author_name
            continue
        row["canonical_author_id"] = item["canonical_author_id"]
        row["canonical_author_name"] = item["canonical_author_name"]
        row["canonical_author_kind"] = item["canonical_author_kind"]
        row["author"] = item["canonical_author_name"]


def _source_author_metadata_names(
    catalog_path: Path,
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str], str]:
    collection_ids = sorted(
        {str(row.get("collection_id") or "") for row in rows if row.get("collection_id")}
    )
    subject_ids = sorted(
        {
            candidate
            for row in rows
            for candidate in _source_author_subject_candidates(row)
            if candidate
        }
    )
    if not collection_ids or not subject_ids:
        return {}
    collection_placeholders = ", ".join("?" for _ in collection_ids)
    subject_placeholders = ", ".join("?" for _ in subject_ids)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "source_metadata"):
            return {}
        metadata_rows = _dict_rows(
            conn,
            f"""
            SELECT collection_id, subject_id, key, value
            FROM source_metadata
            WHERE subject_kind = 'author'
              AND collection_id IN ({collection_placeholders})
              AND subject_id IN ({subject_placeholders})
              AND key IN ('idt_author_name', 'authtab_author_name')
            ORDER BY
                collection_id,
                subject_id,
                CASE key WHEN 'idt_author_name' THEN 0 ELSE 1 END,
                source_path
            """,
            [*collection_ids, *subject_ids],
        )
    names: dict[tuple[str, str], str] = {}
    for metadata_row in metadata_rows:
        key = (
            str(metadata_row.get("collection_id") or ""),
            str(metadata_row.get("subject_id") or ""),
        )
        names.setdefault(key, str(metadata_row.get("value") or ""))
    return names


def _source_author_identity(
    row: Mapping[str, Any],
    source_metadata_names: Mapping[tuple[str, str], str],
    *,
    fallback_author_id: str,
    fallback_author_name: str,
) -> tuple[str, str]:
    collection_id = str(row.get("collection_id") or "")
    for subject_id in _source_author_subject_candidates(row):
        source_name = source_metadata_names.get((collection_id, subject_id))
        if source_name:
            return subject_id, _source_author_display_name(
                collection_id,
                subject_id,
                source_name,
            )
    return fallback_author_id, _source_author_display_name(
        collection_id,
        fallback_author_id,
        fallback_author_name,
    )


def _source_author_display_name(
    collection_id: str,
    source_author_id: str,
    source_author_name: str,
) -> str:
    if (
        collection_id in {"", "first1kgreek", "tlg"}
        and source_author_id in {"tlg9010", "urn:cts:greekLit:tlg9010"}
        and source_author_name == "Suda"
    ):
        return "Soudas"
    return source_author_name


def _fallback_canonical_author_name(
    row: Mapping[str, Any],
    *,
    source_author_id: str,
    source_author_name: str,
    fallback_author_name: str,
) -> str:
    collection_id = str(row.get("collection_id") or "")
    if (
        collection_id in {"first1kgreek", "tlg"}
        and source_author_id in {"tlg9010", "urn:cts:greekLit:tlg9010"}
        and source_author_name == "Soudas"
        and fallback_author_name == "Suda"
    ):
        return source_author_name
    return fallback_author_name


def _attach_work_display_labels(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        collection_id = str(row.get("collection_id") or "").strip()
        source_id = str(row.get("source_id") or "").strip()
        canonical_text_id = str(row.get("canonical_text_id") or "").strip()
        collection_label = collection_id.upper()
        row["source_label"] = (
            f"{collection_label} {source_id}".strip() if source_id else collection_label
        )
        row["edition_label"] = (
            f"{collection_label} reader text" if collection_label else "Reader text"
        )
        row["short_disambiguation_label"] = source_id or str(row.get("work_id") or "")
        row["canonical_address"] = canonical_text_id or str(
            row.get("cts_work_urn") or row.get("work_id") or ""
        )


def _source_author_subject_candidates(row: Mapping[str, Any]) -> tuple[str, ...]:
    source_id = str(row.get("source_id") or "").casefold()
    source_family = source_id.split(".", 1)[0]
    author_id = str(row.get("author_id") or "").casefold()
    candidates = []
    if source_family:
        candidates.append(source_family)
    if author_id and author_id not in candidates:
        candidates.append(author_id)
    return tuple(candidates)


def _attach_source_metadata_summaries(  # noqa: C901, PLR0912
    catalog_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows or not catalog_path.exists():
        return
    for row in rows:
        row["source_metadata_summary"] = ""
    candidates_by_collection: dict[str, set[str]] = {}
    for row in rows:
        for collection_id in _source_metadata_candidate_collections(row):
            candidates = candidates_by_collection.setdefault(collection_id, set())
            candidates.update(_source_metadata_candidate_subjects(row))
    if not candidates_by_collection:
        return
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "source_metadata"):
            return
        clauses: list[str] = []
        params: list[object] = []
        for collection_id, subject_ids in candidates_by_collection.items():
            if not subject_ids:
                continue
            placeholders = ", ".join("?" for _ in subject_ids)
            clauses.append(f"(collection_id = ? AND subject_id IN ({placeholders}))")
            params.extend([collection_id, *sorted(subject_ids)])
        if not clauses:
            return
        metadata_rows = _dict_rows(
            conn,
            f"""
            SELECT collection_id, subject_id, key, value
            FROM source_metadata
            WHERE subject_kind = 'work'
              AND key IN ({", ".join("?" for _ in SOURCE_METADATA_SUMMARY_KEYS)})
              AND ({" OR ".join(clauses)})
            ORDER BY collection_id, subject_id, key, value
            """,
            [*SOURCE_METADATA_SUMMARY_KEYS, *params],
        )
    values_by_subject: dict[tuple[str, str], dict[str, list[str]]] = {}
    for metadata_row in metadata_rows:
        key = str(metadata_row.get("key") or "").strip()
        value = str(metadata_row.get("value") or "").strip()
        collection_id = str(metadata_row.get("collection_id") or "").strip()
        subject_id = str(metadata_row.get("subject_id") or "").strip()
        if not key or not value or not collection_id or not subject_id:
            continue
        subject_values = values_by_subject.setdefault((collection_id, subject_id), {})
        _append_source_metadata_summary_value(subject_values, key, value)
    for row in rows:
        merged: dict[str, list[str]] = {}
        for collection_id in _source_metadata_candidate_collections(row):
            for subject_id in _source_metadata_candidate_subjects(row):
                for key, values in values_by_subject.get((collection_id, subject_id), {}).items():
                    for value in values:
                        _append_source_metadata_summary_value(merged, key, value)
        row["source_metadata_summary"] = "; ".join(
            f"{key}={' | '.join(merged[key])}"
            for key in SOURCE_METADATA_SUMMARY_KEYS
            if key in merged and merged[key]
        )


def _source_metadata_candidate_collections(row: Mapping[str, Any]) -> list[str]:
    collection_id = str(row.get("collection_id") or "").strip()
    collections = [collection_id] if collection_id else []
    if _cts_work_tail(str(row.get("cts_work_urn") or "")) and "perseus" not in collections:
        collections.append("perseus")
    return collections


def _source_metadata_candidate_subjects(row: Mapping[str, Any]) -> set[str]:
    candidates = {
        str(row.get(field) or "").strip()
        for field in ("source_id", "work_id", "cts_work_urn")
        if str(row.get(field) or "").strip()
    }
    cts_tail = _cts_work_tail(str(row.get("cts_work_urn") or ""))
    if cts_tail:
        candidates.add(cts_tail)
    return candidates


def _attach_work_metadata_attributions(
    catalog_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    for row in rows:
        row["metadata_attributions"] = []
        row["translator_names"] = []
        row["traditional_author_names"] = []
        row["attributed_author_names"] = []
    if not rows or not catalog_path.exists():
        return
    row_match_keys = [_work_attribution_match_keys(row) for row in rows]
    collection_ids = sorted(
        {str(row.get("collection_id") or "") for row in rows if row.get("collection_id")}
    )
    if not collection_ids:
        return
    collection_placeholders = ", ".join("?" for _ in collection_ids)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "metadata_attributions"):
            return
        attribution_rows = _dict_rows(
            conn,
            f"""
            SELECT collection_id, match_field, match_value, relation_type, agent,
                   status, confidence, note,
                   min(evidence_citation) AS evidence_citation,
                   arg_min(evidence_label, evidence_citation) AS evidence_label
            FROM metadata_attributions
            WHERE status = 'accepted'
              AND collection_id IN ({collection_placeholders})
            GROUP BY collection_id, match_field, match_value, relation_type, agent,
                     status, confidence, note
            ORDER BY relation_type, agent, evidence_citation
            """,
            collection_ids,
        )
    for row, match_keys in zip(rows, row_match_keys, strict=True):
        collection_id = str(row.get("collection_id") or "")
        for attribution in attribution_rows:
            if collection_id != str(attribution.get("collection_id") or ""):
                continue
            match_key = (
                str(attribution.get("match_field") or ""),
                str(attribution.get("match_value") or "").casefold(),
            )
            if match_key not in match_keys:
                continue
            relation_type = str(attribution.get("relation_type") or "")
            agent = str(attribution.get("agent") or "")
            row["metadata_attributions"].append(
                {
                    "relation_type": relation_type,
                    "agent": agent,
                    "status": str(attribution.get("status") or ""),
                    "confidence": str(attribution.get("confidence") or ""),
                    "note": str(attribution.get("note") or ""),
                    "evidence_citation": str(attribution.get("evidence_citation") or ""),
                    "evidence_label": str(attribution.get("evidence_label") or ""),
                }
            )
            _append_work_attribution_name(row, relation_type, agent)


def _work_attribution_match_keys(row: Mapping[str, Any]) -> set[tuple[str, str]]:
    source_id = str(row.get("source_id") or "")
    source_family = source_id.casefold().split(".", 1)[0]
    cts_work_urn = str(row.get("cts_work_urn") or "")
    author_id = str(row.get("author_id") or "")
    source_author_id = str(row.get("source_author_id") or "")
    candidates = {
        ("source_id", source_id),
        ("work_id", str(row.get("work_id") or "")),
        ("cts_work_urn", cts_work_urn),
        ("author_id", author_id),
        ("author_id", compact_author_id(author_id)),
        ("author_id", source_author_id),
        ("author_id", compact_author_id(source_author_id)),
        ("author_id", source_family),
    }
    return {(field, value.casefold()) for field, value in candidates if field and value}


def _append_work_attribution_name(
    row: dict[str, Any],
    relation_type: str,
    agent: str,
) -> None:
    if not agent:
        return
    if relation_type == "translator":
        _append_unique(row["translator_names"], agent)
    elif relation_type == "traditional_author":
        _append_unique(row["traditional_author_names"], agent)
        _append_unique(row["attributed_author_names"], agent)
    elif relation_type in {"attributed_author", "possible_author"}:
        _append_unique(row["attributed_author_names"], agent)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _cts_work_tail(value: str) -> str:
    if not value.startswith("urn:cts:"):
        return ""
    tail = value.rsplit(":", 1)[-1]
    parts = tail.split(".")
    if len(parts) < CTS_WORK_TAIL_PARTS:
        return ""
    return ".".join(parts[:CTS_WORK_TAIL_PARTS])


def _append_source_metadata_summary_value(
    values_by_key: dict[str, list[str]],
    key: str,
    value: str,
) -> None:
    values = values_by_key.setdefault(key, [])
    if key == "dcs_time_slot":
        if value.isdigit() and any(not current.isdigit() for current in values):
            return
        if not value.isdigit() and any(current.isdigit() for current in values):
            values.clear()
    if value not in values:
        values.append(value)


def _work_sort_key_catalog(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("language") or ""),
        str(row.get("author") or ""),
        str(row.get("title") or ""),
        str(row.get("work_id") or ""),
    )


def _work_sort_key_popularity(row: dict[str, Any]) -> tuple[bool, int, str, str, str, str]:
    score = row.get("classification_popularity_score")
    return (
        score is None,
        -int(score) if score is not None else 0,
        str(row.get("language") or ""),
        str(row.get("author") or ""),
        str(row.get("title") or ""),
        str(row.get("work_id") or ""),
    )


def _work_sort_key_global_popularity(
    row: dict[str, Any],
) -> tuple[bool, int, str, str, str, str]:
    score = row.get("classification_global_popularity_score")
    return (
        score is None,
        -int(score) if score is not None else 0,
        str(row.get("language") or ""),
        str(row.get("author") or ""),
        str(row.get("title") or ""),
        str(row.get("work_id") or ""),
    )


def _work_sort_key_group_popularity(
    row: dict[str, Any],
) -> tuple[bool, int, str, str, str, str]:
    score = row.get("classification_group_popularity_score")
    return (
        score is None,
        -int(score) if score is not None else 0,
        str(row.get("language") or ""),
        str(row.get("author") or ""),
        str(row.get("title") or ""),
        str(row.get("work_id") or ""),
    )


def _work_sort_key_scope_popularity(row: dict[str, Any]) -> tuple[bool, int, str, str, str, str]:
    score = row.get("classification_scope_popularity_score")
    return (
        score is None,
        -int(score) if score is not None else 0,
        str(row.get("language") or ""),
        str(row.get("author") or ""),
        str(row.get("title") or ""),
        str(row.get("work_id") or ""),
    )


def _list_contained_work_rows(  # noqa: C901, PLR0911, PLR0912, PLR0913
    catalog_path: Path,
    *,
    language: str | None = None,
    author: str | None = None,
    author_id: str | None = None,
    classification_scope: str | None = None,
    classification_group: str | None = None,
    classification_tag: str | None = None,
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
        if _table_exists(conn, "work_classifications"):
            classification_table_columns = _table_columns(conn, "work_classifications")
            if classification_group:
                group_key = classification_group.lower()
                if "discovery_group_id" in classification_table_columns:
                    conditions.append("lower(coalesce(wc.discovery_group_id, '')) = ?")
                    params.append(group_key)
                elif "scope" in classification_table_columns:
                    conditions.append(
                        """
                        (
                            lower(coalesce(wc.scope, '')) LIKE ?
                            OR lower(coalesce(wc.category, '')) LIKE ?
                        )
                        """
                    )
                    group_like = f"%{group_key}%"
                    params.extend([group_like, group_like])
                else:
                    return []
            if classification_tag:
                if not _table_exists(conn, "work_classification_tags"):
                    return []
                conditions.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM work_classification_tags wct
                        WHERE wct.work_id = contained_works.contained_work_id
                          AND lower(wct.tag_id) = ?
                    )
                    """
                )
                params.append(classification_tag.lower())
            if classification_scope:
                if "scope" not in classification_table_columns:
                    return []
                scope_like = f"%{classification_scope.lower()}%"
                conditions.append(
                    """
                    (
                        lower(coalesce(wc.scope, '')) LIKE ?
                        OR lower(coalesce(wc.category, '')) LIKE ?
                    )
                    """
                )
                params.extend([scope_like, scope_like])
            classification_columns = _work_classification_select_columns(
                classification_table_columns
            )
            classification_join = """
                LEFT JOIN work_classifications wc
                  ON wc.work_id = contained_works.contained_work_id
            """
        else:
            if classification_scope or classification_group or classification_tag:
                return []
            classification_columns = _null_work_classification_select_columns()
            classification_join = ""
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
                end_citation,
                {classification_columns}
            FROM contained_works
            {classification_join}
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
    for row in rows:
        row["word_count"] = _word_count_for_citation_range(
            catalog_path,
            str(row["parent_work_id"]),
            str(row["start_citation"]),
            str(row["end_citation"]),
        )
        row["word_count_method"] = "whitespace_tokens"
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
                    _attach_segments_canonical_addresses(catalog_path, rows)
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
            _attach_segments_canonical_addresses(catalog_path, rows)
            return rows[:limit]
    _attach_segments_canonical_addresses(catalog_path, rows)
    return rows


def _attach_segments_canonical_addresses(
    catalog_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    for row in rows:
        _attach_segment_canonical_address(catalog_path, row)


def work_map_for_work(catalog_path: Path, work_ref: str) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    work = get_work(catalog_path, work_ref)
    candidates = [work_ref]
    if work:
        for value in (
            work.get("work_id"),
            work.get("cts_work_urn"),
            work.get("parent_work_id"),
        ):
            if value:
                candidates.append(str(value))
    resolved = resolve_work_ref(catalog_path, work_ref)
    if resolved:
        candidates.append(resolved)
    candidates = list(dict.fromkeys(candidates))
    placeholders = ", ".join("?" for _ in candidates)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "work_map_nodes"):
            return []
        rows = _dict_rows(
            conn,
            f"""
            SELECT DISTINCT
                work_id, node_id, parent_node_id, level, kind, label, native_label,
                ordinal, start_citation, end_citation, provenance, confidence,
                status, note, source_file
            FROM work_map_nodes
            WHERE status = 'accepted'
              AND work_id IN ({placeholders})
            ORDER BY level, ordinal, node_id
            """,
            candidates,
        )
    return [_decorate_work_map_node(catalog_path, row) for row in rows]


def division_metadata_for_work(catalog_path: Path, work_ref: str) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    work = get_work(catalog_path, work_ref)
    candidates = [work_ref]
    if work:
        for value in (
            work.get("work_id"),
            work.get("cts_work_urn"),
            work.get("parent_work_id"),
        ):
            if value:
                candidates.append(str(value))
    resolved = resolve_work_ref(catalog_path, work_ref)
    if resolved:
        candidates.append(resolved)
    candidates = list(dict.fromkeys(candidates))
    placeholders = ", ".join("?" for _ in candidates)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "division_metadata"):
            return []
        return _dict_rows(
            conn,
            f"""
            SELECT
                work_id, node_id, summary, short_label, traditional_reference,
                status, confidence, generator_model, review_status, note, source_file,
                count(*) AS evidence_count
            FROM division_metadata
            WHERE work_id IN ({placeholders})
              AND status = 'accepted'
            GROUP BY
                work_id, node_id, summary, short_label, traditional_reference,
                status, confidence, generator_model, review_status, note, source_file
            ORDER BY work_id, node_id
            """,
            candidates,
        )


def structure_for_work(catalog_path: Path, work_ref: str) -> list[dict[str, Any]]:
    nodes = work_map_for_work(catalog_path, work_ref)
    metadata = {
        (str(row["work_id"]), str(row["node_id"])): row
        for row in division_metadata_for_work(catalog_path, work_ref)
    }
    items: list[dict[str, Any]] = []
    for node in nodes:
        meta = metadata.get((str(node["work_id"]), str(node["node_id"])), {})
        items.append(
            {
                **node,
                "object_type": str(node.get("kind") or "division"),
                "summary": meta.get("summary"),
                "short_label": meta.get("short_label"),
                "traditional_reference": meta.get("traditional_reference"),
                "division_metadata_status": meta.get("status"),
                "division_review_status": meta.get("review_status"),
                "division_confidence": meta.get("confidence"),
                "division_evidence_count": meta.get("evidence_count"),
                "provenance_chips": _structure_provenance_chips(node, meta),
            }
        )
    return items


def current_divisions_for_segment(
    catalog_path: Path,
    work_ref: str,
    citation_path: str,
) -> list[dict[str, Any]]:
    items = structure_for_work(catalog_path, work_ref)
    current_sort = _citation_sort_value(citation_path)
    matches = [
        item
        for item in items
        if _citation_sort_value(str(item.get("start_citation") or ""))
        <= current_sort
        <= _citation_sort_value(str(item.get("end_citation") or ""))
    ]
    return sorted(
        matches,
        key=lambda item: (int(item.get("level") or 0), int(item.get("ordinal") or 0)),
    )


def resolve_structure_reference(
    catalog_path: Path,
    address: str,
    *,
    work_ref: str | None = None,
    citation_ref: str | None = None,
) -> dict[str, Any] | None:
    if not catalog_path.exists():
        return None
    reference = citation_ref or address
    if work_ref:
        resolved_work = resolve_work_ref(catalog_path, work_ref)
        if resolved_work:
            return _match_structure_reference(
                structure_for_work(catalog_path, resolved_work),
                reference,
            )
    return _match_global_traditional_reference(catalog_path, address)


def _match_global_traditional_reference(
    catalog_path: Path,
    address: str,
) -> dict[str, Any] | None:
    address_key = _structure_reference_key(address)
    if not address_key:
        return None
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "division_metadata"):
            return None
        rows = _dict_rows(
            conn,
            """
            SELECT DISTINCT work_id, node_id, traditional_reference
            FROM division_metadata
            WHERE status = 'accepted'
              AND traditional_reference IS NOT NULL
            ORDER BY work_id, node_id
            """,
        )
    for row in rows:
        if _structure_reference_key(str(row.get("traditional_reference") or "")) != address_key:
            continue
        for item in structure_for_work(catalog_path, str(row["work_id"])):
            if str(item.get("node_id") or "") == str(row["node_id"]):
                return item
    return None


def _match_structure_reference(
    items: list[dict[str, Any]],
    reference: str,
) -> dict[str, Any] | None:
    reference_key = _structure_reference_key(reference)
    if not reference_key:
        return None
    for item in items:
        if reference_key in _structure_reference_keys_for_item(item):
            return item
    return None


def _structure_reference_keys_for_item(item: Mapping[str, Any]) -> set[str]:
    keys = {
        _structure_reference_key(str(item.get("traditional_reference") or "")),
        _structure_reference_key(str(item.get("label") or "")),
        _structure_reference_key(str(item.get("short_label") or "")),
        _structure_reference_key(str(item.get("start_citation") or "")),
    }
    kind = str(item.get("kind") or "").strip().lower()
    ordinal = item.get("ordinal")
    if kind and ordinal is not None:
        ordinal_text = str(ordinal)
        keys.add(_structure_reference_key(f"{kind} {ordinal_text}"))
        keys.add(_structure_reference_key(ordinal_text))
        if kind == "book":
            keys.add(_structure_reference_key(f"bk {ordinal_text}"))
        elif kind == "chapter":
            keys.add(_structure_reference_key(f"ch {ordinal_text}"))
    return {key for key in keys if key}


def _structure_reference_key(value: str) -> str:
    return re.sub(r"[\s._,;:]+", " ", value.casefold()).strip()


def citation_maps_for_work(
    catalog_path: Path,
    work_ref: str,
    *,
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    work = get_work(catalog_path, work_ref)
    candidates = [work_ref]
    if work:
        for value in (
            work.get("work_id"),
            work.get("cts_work_urn"),
            work.get("parent_work_id"),
        ):
            if value:
                candidates.append(str(value))
    resolved = resolve_work_ref(catalog_path, work_ref)
    if resolved:
        candidates.append(resolved)
    candidates = list(dict.fromkeys(candidates))
    placeholders = ", ".join("?" for _ in candidates)
    where = [f"work_id IN ({placeholders})"]
    params: list[object] = [*candidates]
    if source_id:
        where.append("source_id = ?")
        params.append(source_id)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "citation_maps"):
            return []
        rows = _dict_rows(
            conn,
            f"""
            SELECT
                citation_map_id, source_id, work_id, source_pattern, machine_pattern,
                projection_rule, example_source_reference, example_machine_citation,
                status, confidence, note, source_file,
                count(*) AS evidence_count
            FROM citation_maps
            WHERE {" AND ".join(where)}
            GROUP BY
                citation_map_id, source_id, work_id, source_pattern, machine_pattern,
                projection_rule, example_source_reference, example_machine_citation,
                status, confidence, note, source_file
            ORDER BY source_id, work_id, citation_map_id
            """,
            params,
        )
    return rows


def _citation_sort_value(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value)
    return tuple(int(part) for part in parts) if parts else (0,)


def _structure_provenance_chips(
    node: Mapping[str, Any],
    meta: Mapping[str, Any],
) -> list[str]:
    chips: list[str] = []
    provenance = str(node.get("provenance") or "")
    if provenance == "curated":
        chips.append("Curated")
    elif provenance == "native":
        chips.append("Source")
    elif provenance == "inferred":
        chips.append("Inferred")
    review_status = str(meta.get("review_status") or "")
    if review_status == "reviewed":
        chips.append("Reviewed")
    elif review_status == "llm_draft":
        chips.append("LLM draft")
    elif review_status == "needs_review":
        chips.append("Needs review")
    return chips


def _decorate_work_map_node(catalog_path: Path, row: dict[str, Any]) -> dict[str, Any]:
    work_id = str(row["work_id"])
    word_count = _word_count_for_citation_range(
        catalog_path,
        work_id,
        str(row["start_citation"]),
        str(row["end_citation"]),
    )
    work = get_work(catalog_path, work_id)
    canonical_text_id = str(work.get("canonical_text_id") or "") if work else ""
    return {
        **row,
        "canonical_text_id": canonical_text_id or None,
        "canonical_address": (
            ctsv2_segment_address(canonical_text_id, str(row["start_citation"]))
            if canonical_text_id
            else None
        ),
        "word_count": word_count,
        "word_count_method": "whitespace_tokens",
    }


def _word_count_for_citation_range(
    catalog_path: Path,
    work_ref: str,
    start_citation: str,
    end_citation: str,
) -> int:
    resolved_work_id = resolve_text_work_ref(catalog_path, work_ref) or work_ref
    total = 0
    for artifact in _catalog_artifacts(catalog_path):
        if artifact["work_id"] != resolved_work_id:
            continue
        book_path = Path(str(artifact["artifact_path"]))
        if not book_path.exists():
            continue
        with duckdb.connect(str(book_path), read_only=True) as conn:
            start_sort_key = _segment_sort_key(conn, resolved_work_id, start_citation)
            end_sort_key = _segment_sort_key(conn, resolved_work_id, end_citation)
            if start_sort_key is None or end_sort_key is None:
                continue
            low = min(start_sort_key, end_sort_key)
            high = max(start_sort_key, end_sort_key)
            texts = conn.execute(
                """
                SELECT text
                FROM segments
                WHERE work_id = ? AND sort_key BETWEEN ? AND ?
                """,
                [resolved_work_id, low, high],
            ).fetchall()
        total += sum(len(str(row[0]).split()) for row in texts)
    return total


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


def list_source_witnesses(
    catalog_path: Path,
    *,
    canonical_text_id: str | None = None,
    collection_id: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if canonical_text_id:
        conditions.append("canonical_text_id = ?")
        params.append(canonical_text_id)
    if collection_id:
        conditions.append("collection_id = ?")
        params.append(collection_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "source_witnesses"):
            return []
        return _dict_rows(
            conn,
            f"""
            SELECT canonical_text_id, work_id, collection_id, language, witness_id,
                   source_id, source_urn, source_path, status, confidence, note
            FROM source_witnesses
            {where}
            ORDER BY canonical_text_id, collection_id, witness_id
            LIMIT ?
            """,
            params,
        )


def list_work_relations(
    catalog_path: Path,
    *,
    source_id: str | None = None,
    target_id: str | None = None,
    relation_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    conditions = []
    params: list[object] = []
    if source_id:
        conditions.append("source_id = ?")
        params.append(source_id)
    if target_id:
        conditions.append("target_id = ?")
        params.append(target_id)
    if relation_type:
        conditions.append("relation_type = ?")
        params.append(relation_type)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "work_relations"):
            return []
        return _dict_rows(
            conn,
            f"""
            SELECT source_id, target_id, relation_type, status, confidence, note, source_file
            FROM work_relations
            {where}
            ORDER BY source_id, relation_type, target_id
            LIMIT ?
            """,
            params,
        )


def reader_summary(catalog_path: Path) -> dict[str, object]:
    if not catalog_path.exists():
        return {
            "collection_count": 0,
            "work_count": 0,
            "artifact_count": 0,
            "segment_count": 0,
            "word_count": 0,
            "word_count_method": "whitespace_tokens",
            "alias_count": 0,
            "source_file_count": 0,
            "metadata_count": 0,
        }
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        collection_count = _scalar_int(conn, "SELECT COUNT(DISTINCT collection_id) FROM works")
        work_count = _scalar_int(conn, "SELECT COUNT(*) FROM works")
        artifact_count = _scalar_int(conn, "SELECT COUNT(*) FROM artifacts")
        segment_count = _scalar_int(conn, "SELECT COALESCE(SUM(segment_count), 0) FROM artifacts")
        word_count = _scalar_int(conn, "SELECT COALESCE(SUM(token_count), 0) FROM artifacts")
        alias_count = _scalar_int(conn, "SELECT COUNT(*) FROM aliases")
        source_file_count = _scalar_int(conn, "SELECT COUNT(*) FROM source_files")
        metadata_count = _scalar_int(conn, "SELECT COUNT(*) FROM source_metadata")
    return {
        "collection_count": int(collection_count),
        "work_count": int(work_count),
        "artifact_count": int(artifact_count),
        "segment_count": int(segment_count),
        "word_count": int(word_count),
        "word_count_method": "whitespace_tokens",
        "alias_count": int(alias_count),
        "source_file_count": int(source_file_count),
        "metadata_count": int(metadata_count),
    }


def _scalar_int(conn: duckdb.DuckDBPyConnection, query: str) -> int:
    row = conn.execute(query).fetchone()
    return int(row[0]) if row else 0
