from __future__ import annotations

import re
import shutil
from collections import Counter
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from langnet.normalizer.greek_transliterator import transliterate_variants
from langnet.normalizer.utils import contains_greek, unique
from langnet.reader.search_concepts import ReaderSearchConcept, load_search_concepts
from langnet.reader.search_normalization import (
    NORMALIZER_VERSION,
    normalize_query_for_search,
    normalize_segment_for_search,
)

SEARCH_INDEX_SCHEMA_VERSION = "langnet.reader_search_index.v1"
SEARCH_RESULT_SCHEMA_VERSION = "langnet.reader_search.v1"
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
LANCE_DATASET_SUFFIX = ".lance"
LANCE_SEARCH_FIELDS = {"search_text", "search_text_folded", "token_text", "display_text"}
READER_SEARCH_CONCEPT_ROOT = Path("data/curated/reader_search")
TOKEN_RE = re.compile(r"\S+")
SEARCH_INDEX_POLARS_SCHEMA = {
    "search_id": pl.String,
    "catalog_path": pl.String,
    "artifact_id": pl.String,
    "segment_id": pl.String,
    "work_id": pl.String,
    "edition_id": pl.String,
    "collection_id": pl.String,
    "language": pl.String,
    "title": pl.String,
    "author": pl.String,
    "source_author": pl.String,
    "source_author_id": pl.String,
    "canonical_author_id": pl.String,
    "canonical_author_name": pl.String,
    "cts_work_urn": pl.String,
    "canonical_text_id": pl.String,
    "canonical_address": pl.String,
    "citation_path": pl.String,
    "sort_key": pl.Int64,
    "work_kind": pl.String,
    "display_text": pl.String,
    "source_text": pl.String,
    "normalized_text": pl.String,
    "search_text": pl.String,
    "search_text_folded": pl.String,
    "token_text": pl.String,
    "classification_discovery_group_id": pl.String,
    "classification_discovery_tags": pl.String,
    "classification_global_popularity_score": pl.Int64,
    "classification_group_popularity_score": pl.Int64,
    "index_schema_version": pl.String,
    "normalizer_version": pl.String,
    "indexed_at": pl.String,
    "source_artifact_hash": pl.String,
}


def build_reader_search_index(  # noqa: PLR0913
    catalog_path: Path,
    index_path: Path,
    *,
    language: str | None = None,
    collection_id: str | None = None,
    replace: bool = False,
    batch_size: int = 50000,
    limit: int | None = None,
) -> dict[str, Any]:
    dataset_path = _lance_dataset_path(index_path)
    if replace and dataset_path.exists():
        shutil.rmtree(dataset_path)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    indexed_at = datetime.now(UTC).isoformat()
    summary: dict[str, Any] = {
        "backend": "duckdb-lance",
        "dataset_path": str(dataset_path),
        "segment_count": 0,
        "work_count": 0,
        "language_counts": {},
        "normalizer_version": NORMALIZER_VERSION,
        "replaced": replace,
        "fts_indexed": False,
    }
    seen_works: set[str] = set()
    language_counts: Counter[str] = Counter()
    with duckdb.connect(":memory:") as conn:
        _load_lance(conn)
        segment_rows: list[dict[str, Any]] = []
        wrote_dataset = dataset_path.exists()
        wrote_rows = False
        for artifact in _catalog_artifact_rows(
            catalog_path,
            language=language,
            collection_id=collection_id,
        ):
            if limit is not None and summary["segment_count"] >= limit:
                break
            book_path = Path(str(artifact["artifact_path"]))
            if not book_path.exists():
                continue
            for segment in _book_segment_rows(book_path, work_id=str(artifact["work_id"])):
                if limit is not None and summary["segment_count"] >= limit:
                    break
                search_row = _search_row(catalog_path, artifact, segment, indexed_at=indexed_at)
                segment_rows.append(search_row)
                summary["segment_count"] += 1
                seen_works.add(str(search_row["work_id"]))
                language_counts.update([str(search_row["language"])])
                if len(segment_rows) >= batch_size:
                    _write_lance_rows(conn, dataset_path, segment_rows, append=wrote_dataset)
                    wrote_dataset = True
                    wrote_rows = True
                    segment_rows.clear()
        if segment_rows:
            _write_lance_rows(conn, dataset_path, segment_rows, append=wrote_dataset)
            wrote_dataset = True
            wrote_rows = True
        if not wrote_dataset and not wrote_rows:
            _write_empty_lance_dataset(conn, dataset_path)
        _create_lance_fts_indexes(conn, dataset_path)
        summary["fts_indexed"] = True
    summary["work_count"] = len(seen_works)
    summary["language_counts"] = dict(sorted(language_counts.items()))
    return summary


def reader_search_index_status(index_path: Path) -> dict[str, Any]:
    dataset_path = _lance_dataset_path(index_path)
    if not dataset_path.exists():
        return {
            "exists": False,
            "backend": "duckdb-lance",
            "dataset_path": str(dataset_path),
            "segment_count": 0,
            "language_counts": {},
            "schema_version": None,
            "normalizer_version": None,
            "fts_indexes": [],
        }
    with duckdb.connect(":memory:") as conn:
        _load_lance(conn)
        dataset = _sql_literal(dataset_path)
        language_counts = {
            str(language): int(count)
            for language, count in conn.execute(
                f"""
                SELECT language, count(*)
                FROM {dataset}
                GROUP BY language
                ORDER BY language
                """
            ).fetchall()
        }
        row = conn.execute(
            f"""
            SELECT
                any_value(index_schema_version),
                any_value(normalizer_version),
                any_value(catalog_path),
                max(indexed_at)
            FROM {dataset}
            """
        ).fetchone()
        assert row is not None
        count_row = conn.execute(f"SELECT count(*) FROM {dataset}").fetchone()
        assert count_row is not None
        indexes = _lance_index_names(conn, dataset_path)
        return {
            "exists": True,
            "backend": "duckdb-lance",
            "dataset_path": str(dataset_path),
            "segment_count": int(count_row[0]),
            "language_counts": language_counts,
            "schema_version": row[0],
            "normalizer_version": row[1],
            "catalog_path": row[2],
            "indexed_at": row[3],
            "fts_indexes": indexes,
        }


def validate_reader_search_index(catalog_path: Path, index_path: Path) -> dict[str, Any]:
    status = reader_search_index_status(index_path)
    issues: list[dict[str, str]] = []
    if not status["exists"]:
        issues.append({"code": "index_missing", "message": f"Search index missing: {index_path}"})
        return {"status": status, "issues": issues}
    if status.get("schema_version") != SEARCH_INDEX_SCHEMA_VERSION:
        issues.append(
            {
                "code": "schema_version",
                "message": "Reader search index schema version is not supported.",
            }
        )
    if status.get("normalizer_version") != NORMALIZER_VERSION:
        issues.append(
            {
                "code": "normalizer_version",
                "message": "Reader search index normalizer version is not supported.",
            }
        )
    indexed_catalog = status.get("catalog_path")
    if indexed_catalog and Path(str(indexed_catalog)) != catalog_path:
        issues.append(
            {
                "code": "catalog_path",
                "message": "Reader search index was built from a different catalog path.",
            }
        )
    index_names = set(status.get("fts_indexes") or [])
    for required_index in ("search_text_idx", "search_text_folded_idx", "token_text_idx"):
        if required_index not in index_names:
            issues.append(
                {
                    "code": "fts_index_missing",
                    "message": f"Reader search index missing Lance FTS index: {required_index}",
                }
            )
    return {"status": status, "issues": issues}


def search_reader_segments(  # noqa: PLR0913
    catalog_path: Path,
    index_path: Path,
    query: str,
    *,
    language: str | None = None,
    collection_id: str | None = None,
    work_id: str | None = None,
    author_id: str | None = None,
    group: str | None = None,
    tag: str | None = None,
    mode: str = "keyword",
    field: str = "auto",
    context: int = 0,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    dataset_path = _lance_dataset_path(index_path)
    query_language = language or ""
    normalized = normalize_query_for_search(query_language, query)
    if not dataset_path.exists():
        items: list[dict[str, Any]] = []
    else:
        with duckdb.connect(":memory:") as conn:
            _load_lance(conn)
            search_field = _search_field(field)
            if mode == "fuzzy":
                items = _fuzzy_lance_search(
                    conn,
                    dataset_path,
                    query,
                    language=query_language,
                    requested_language=language,
                    collection_id=collection_id,
                    work_id=work_id,
                    author_id=author_id,
                    group=group,
                    tag=tag,
                    field=field,
                    limit=limit,
                    offset=offset,
                )
            else:
                search_query = _search_query(normalized, search_field, mode)
                items = _lance_fts_search(
                    conn,
                    dataset_path,
                    search_field,
                    search_query,
                    language=language,
                    collection_id=collection_id,
                    work_id=work_id,
                    author_id=author_id,
                    group=group,
                    tag=tag,
                    limit=limit,
                    offset=offset,
                )
            if context > 0:
                _attach_context_windows(catalog_path, conn, dataset_path, items, context=context)
    return {
        "schema_version": SEARCH_RESULT_SCHEMA_VERSION,
        "mode": "search",
        "catalog_path": str(catalog_path),
        "index_path": str(dataset_path),
        "request": {
            "query": query,
            "language": language,
            "collection_id": collection_id,
            "search_mode": mode,
            "field": field,
            "query_candidates": (
                _reader_search_query_candidates(
                    query_language,
                    query,
                    mode=mode,
                    field=field,
                )
                if mode == "fuzzy"
                else []
            ),
        },
        "items": items,
        "pagination": {
            "next_cursor": str(offset + limit) if len(items) == limit else None,
            "prev_cursor": str(max(0, offset - limit)) if offset > 0 else None,
            "limit": limit,
        },
    }


def inspect_reader_search_query(
    language: str,
    query: str,
    *,
    mode: str = "keyword",
    field: str = "auto",
) -> dict[str, Any]:
    return {
        "language": language,
        "input": query,
        "mode": mode,
        "field": field,
        "candidates": _reader_search_query_candidates(
            language,
            query,
            mode=mode,
            field=field,
        ),
    }


def _load_lance(conn: duckdb.DuckDBPyConnection) -> None:
    try:
        conn.execute("LOAD lance")
    except duckdb.Error:
        conn.execute("INSTALL lance FROM community")
        conn.execute("LOAD lance")


def _lance_dataset_path(index_path: Path) -> Path:
    return (
        index_path
        if index_path.suffix == LANCE_DATASET_SUFFIX
        else index_path.with_suffix(LANCE_DATASET_SUFFIX)
    )


def _write_lance_rows(
    conn: duckdb.DuckDBPyConnection,
    dataset_path: Path,
    rows: list[dict[str, Any]],
    *,
    append: bool,
) -> None:
    frame = pl.DataFrame(rows, schema=SEARCH_INDEX_POLARS_SCHEMA)
    conn.register("reader_search_rows", frame)
    mode = "append" if append else "overwrite"
    conn.execute(
        f"""
        COPY (
            SELECT *
            FROM reader_search_rows
        ) TO {_sql_literal(dataset_path)} (
            FORMAT lance,
            MODE '{mode}'
        )
        """
    )
    conn.unregister("reader_search_rows")


def _write_empty_lance_dataset(conn: duckdb.DuckDBPyConnection, dataset_path: Path) -> None:
    conn.execute(
        f"""
        COPY (
            SELECT
                ''::VARCHAR AS search_id,
                ''::VARCHAR AS catalog_path,
                ''::VARCHAR AS artifact_id,
                ''::VARCHAR AS segment_id,
                ''::VARCHAR AS work_id,
                ''::VARCHAR AS edition_id,
                ''::VARCHAR AS collection_id,
                ''::VARCHAR AS language,
                ''::VARCHAR AS title,
                ''::VARCHAR AS author,
                ''::VARCHAR AS source_author,
                NULL::VARCHAR AS source_author_id,
                NULL::VARCHAR AS canonical_author_id,
                NULL::VARCHAR AS canonical_author_name,
                NULL::VARCHAR AS cts_work_urn,
                ''::VARCHAR AS citation_path,
                0::INTEGER AS sort_key,
                ''::VARCHAR AS work_kind,
                ''::VARCHAR AS display_text,
                NULL::VARCHAR AS source_text,
                ''::VARCHAR AS normalized_text,
                ''::VARCHAR AS search_text,
                ''::VARCHAR AS search_text_folded,
                ''::VARCHAR AS token_text,
                ''::VARCHAR AS classification_discovery_group_id,
                ''::VARCHAR AS classification_discovery_tags,
                NULL::BIGINT AS classification_global_popularity_score,
                NULL::BIGINT AS classification_group_popularity_score,
                {_sql_literal(SEARCH_INDEX_SCHEMA_VERSION)} AS index_schema_version,
                {_sql_literal(NORMALIZER_VERSION)} AS normalizer_version,
                ''::VARCHAR AS indexed_at,
                ''::VARCHAR AS source_artifact_hash
            LIMIT 0
        ) TO {_sql_literal(dataset_path)} (
            FORMAT lance,
            MODE 'overwrite',
            WRITE_EMPTY_FILE true
        )
        """
    )


def _create_lance_fts_indexes(conn: duckdb.DuckDBPyConnection, dataset_path: Path) -> None:
    for index_name, column_name in (
        ("search_text_idx", "search_text"),
        ("search_text_folded_idx", "search_text_folded"),
        ("token_text_idx", "token_text"),
    ):
        conn.execute(
            f"""
            CREATE INDEX {index_name}
            ON {_sql_literal(dataset_path)} ({column_name})
            USING INVERTED WITH ({LANCE_FTS_INDEX_OPTIONS})
            """
        )


def _catalog_artifact_rows(
    catalog_path: Path,
    *,
    language: str | None,
    collection_id: str | None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[object] = []
    if language:
        conditions.append("w.language = ?")
        params.append(language)
    if collection_id:
        conditions.append("w.collection_id = ?")
        params.append(collection_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        works_columns = _table_columns(conn, "works")
        canonical_select = (
            "w.canonical_text_id"
            if "canonical_text_id" in works_columns
            else "NULL::VARCHAR AS canonical_text_id"
        )
        return _dict_rows(
            conn,
            f"""
            SELECT
                a.artifact_id, a.work_id, a.edition_id, a.artifact_path,
                a.source_hash, w.collection_id, w.language, w.title, w.author,
                w.author_id, w.cts_work_urn, {canonical_select},
                coalesce(wc.discovery_group_id, '') AS group_id,
                coalesce(wc.discovery_tags, '') AS tags,
                wc.global_popularity_score, wc.group_popularity_score
            FROM artifacts a
            JOIN works w ON w.work_id = a.work_id
            LEFT JOIN work_classifications wc ON wc.work_id = w.work_id
            {where}
            ORDER BY w.language, w.collection_id, w.source_id, a.artifact_id
            """,
            params,
        )


def _book_segment_rows(book_path: Path, *, work_id: str) -> list[dict[str, Any]]:
    with duckdb.connect(str(book_path), read_only=True) as conn:
        return _dict_rows(
            conn,
            """
            SELECT segment_id, work_id, edition_id, segment_kind, citation_path,
                   text, source_text, normalized_text, sort_key
            FROM segments
            WHERE work_id = ?
            ORDER BY sort_key, citation_path
            """,
            [work_id],
        )


def _search_row(
    catalog_path: Path,
    artifact: dict[str, Any],
    segment: dict[str, Any],
    *,
    indexed_at: str,
) -> dict[str, Any]:
    language = str(artifact["language"])
    search_text = normalize_segment_for_search(language, str(segment["text"]))
    search_id = f"{artifact['artifact_id']}:{segment['segment_id']}"
    return {
        "search_id": search_id,
        "catalog_path": str(catalog_path),
        "artifact_id": str(artifact["artifact_id"]),
        "segment_id": str(segment["segment_id"]),
        "work_id": str(artifact["work_id"]),
        "edition_id": str(artifact["edition_id"]),
        "collection_id": str(artifact["collection_id"]),
        "language": language,
        "title": str(artifact["title"]),
        "author": str(artifact["author"]),
        "source_author": str(artifact["author"]),
        "source_author_id": artifact.get("author_id"),
        "canonical_author_id": artifact.get("author_id"),
        "canonical_author_name": str(artifact["author"]),
        "cts_work_urn": artifact.get("cts_work_urn"),
        "canonical_text_id": artifact.get("canonical_text_id"),
        "canonical_address": _search_result_address(
            artifact.get("canonical_text_id"),
            str(segment["citation_path"]),
        ),
        "citation_path": str(segment["citation_path"]),
        "sort_key": int(segment["sort_key"]),
        "work_kind": "work",
        "display_text": search_text.display_text,
        "source_text": segment.get("source_text"),
        "normalized_text": str(segment["normalized_text"]),
        "search_text": search_text.search_text,
        "search_text_folded": search_text.search_text_folded,
        "token_text": search_text.token_text,
        "classification_discovery_group_id": str(artifact.get("group_id") or ""),
        "classification_discovery_tags": str(artifact.get("tags") or ""),
        "classification_global_popularity_score": artifact.get("global_popularity_score"),
        "classification_group_popularity_score": artifact.get("group_popularity_score"),
        "index_schema_version": SEARCH_INDEX_SCHEMA_VERSION,
        "normalizer_version": search_text.normalizer_version,
        "indexed_at": indexed_at,
        "source_artifact_hash": str(artifact.get("source_hash") or ""),
    }


def _lance_fts_search(  # noqa: PLR0913
    conn: duckdb.DuckDBPyConnection,
    dataset_path: Path,
    search_field: str,
    search_query: str,
    *,
    language: str | None,
    collection_id: str | None,
    work_id: str | None,
    author_id: str | None,
    group: str | None,
    tag: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    if not search_query:
        return []
    conditions, params = _search_filters(
        language=language,
        collection_id=collection_id,
        work_id=work_id,
        author_id=author_id,
        group=group,
        tag=tag,
    )
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    prefilter = bool(conditions)
    rows = _lance_fts_rows(
        conn,
        dataset_path,
        search_field,
        search_query,
        where=where,
        params=params,
        k=max(limit + offset, limit * 5, 50),
        limit=limit,
        offset=offset,
        prefilter=prefilter,
    )
    if prefilter and not rows:
        rows = _lance_fts_rows(
            conn,
            dataset_path,
            search_field,
            search_query,
            where=where,
            params=params,
            k=_dataset_row_count(conn, dataset_path),
            limit=limit,
            offset=offset,
            prefilter=False,
        )
    return [_result_item(row) for row in rows]


def _lance_fts_rows(  # noqa: PLR0913
    conn: duckdb.DuckDBPyConnection,
    dataset_path: Path,
    search_field: str,
    search_query: str,
    *,
    where: str,
    params: list[object],
    k: int,
    limit: int,
    offset: int,
    prefilter: bool,
) -> list[dict[str, Any]]:
    try:
        return _dict_rows(
            conn,
            f"""
            SELECT s.*, s._score AS score
            FROM lance_fts(
                {_sql_literal(dataset_path)},
                {_sql_literal(search_field)},
                ?,
                k = ?,
                prefilter = {str(prefilter).lower()}
            ) s
            {where}
            ORDER BY s._score DESC, s.language, s.title, s.sort_key
            LIMIT ? OFFSET ?
            """,
            [search_query, k, *params, limit, offset],
        )
    except duckdb.Error:
        if prefilter:
            return _lance_fts_rows(
                conn,
                dataset_path,
                search_field,
                search_query,
                where=where,
                params=params,
                k=_dataset_row_count(conn, dataset_path),
                limit=limit,
                offset=offset,
                prefilter=False,
            )
        raise


def _dataset_row_count(conn: duckdb.DuckDBPyConnection, dataset_path: Path) -> int:
    row = conn.execute(
        f"""
        SELECT count(*)
        FROM {_sql_literal(dataset_path)}
        """
    ).fetchone()
    assert row is not None
    return int(row[0])


def _fuzzy_lance_search(  # noqa: PLR0913
    conn: duckdb.DuckDBPyConnection,
    dataset_path: Path,
    query: str,
    *,
    language: str,
    requested_language: str | None,
    collection_id: str | None,
    work_id: str | None,
    author_id: str | None,
    group: str | None,
    tag: str | None,
    field: str,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    candidates = _reader_search_query_candidates(language, query, mode="fuzzy", field=field)
    target_count = limit + offset
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        candidate_items = _lance_fts_search(
            conn,
            dataset_path,
            str(candidate["field"]),
            str(candidate["query"]),
            language=requested_language,
            collection_id=collection_id,
            work_id=work_id,
            author_id=author_id,
            group=group,
            tag=tag,
            limit=target_count,
            offset=0,
        )
        for item in candidate_items:
            dedupe_key = _result_dedupe_key(item)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            item["matched_query"] = candidate["query"]
            item["input_query"] = query
            item["match_type"] = candidate["kind"]
            item["candidate_rank"] = candidate["rank"]
            item["matched_field"] = candidate["field"]
            items.append(item)
            if len(items) >= target_count:
                break
        if len(items) >= target_count:
            break
    return items[offset : offset + limit]


def _result_dedupe_key(item: dict[str, Any]) -> tuple[str, str]:
    segment_id = str(item.get("segment_id") or "")
    if segment_id:
        return ("segment_id", segment_id)
    return ("work_citation", f"{item.get('work_id')}:{item.get('citation_path')}")


def _reader_search_query_candidates(
    language: str,
    query: str,
    *,
    mode: str,
    field: str,
) -> list[dict[str, Any]]:
    search_field = _search_field(field)
    normalized = normalize_query_for_search(language, query)
    raw_candidates: list[dict[str, Any]] = [
        {
            "query": _candidate_query(normalized, search_field),
            "kind": "input",
            "field": search_field,
        }
    ]
    if mode == "fuzzy":
        raw_candidates.extend(
            {
                "query": variant,
                "kind": "normalized_surface",
                "field": "search_text_folded",
            }
            for variant in normalized.query_variants
        )
        if language == "grc" and not contains_greek(query):
            raw_candidates.extend(
                {
                    "query": normalize_query_for_search(
                        language, variant.search_key
                    ).search_text_folded,
                    "kind": "transliteration_expansion",
                    "field": "search_text_folded",
                }
                for variant in transliterate_variants(query)
                if variant.search_key
            )
        raw_candidates.extend(_concept_alias_query_candidates(language, query))
    candidates = []
    for rank, raw_candidate in enumerate(_unique_candidate_dicts(raw_candidates)):
        candidate_query = str(raw_candidate.get("query") or "")
        if not candidate_query:
            continue
        candidate = dict(raw_candidate)
        candidate["query"] = candidate_query
        candidate["kind"] = str(raw_candidate.get("kind") or "input")
        candidate["field"] = str(raw_candidate.get("field") or search_field)
        candidate["rank"] = rank
        candidates.append(candidate)
    return candidates


def _candidate_query(normalized: Any, search_field: str) -> str:
    if search_field == "search_text":
        return str(normalized.search_text)
    if search_field == "token_text":
        return str(normalized.token_text)
    return str(normalized.search_text_folded)


def _concept_alias_query_candidates(language: str, query: str) -> list[dict[str, Any]]:
    query_key = normalize_query_for_search(language, query).search_text_folded
    candidates: list[dict[str, Any]] = []
    for concept in _search_concepts_for_language(language):
        label_keys = {
            normalize_query_for_search(language, label).search_text_folded
            for label in concept.labels
        }
        if query_key not in label_keys:
            continue
        for source_query in concept.source_queries:
            candidate_query = normalize_query_for_search(language, source_query).search_text_folded
            if not candidate_query:
                continue
            candidates.append(
                {
                    "query": candidate_query,
                    "kind": "concept_alias",
                    "field": "search_text_folded",
                    "concept_id": concept.concept_id,
                    "concept_label": concept.labels[0],
                    "explanation": concept.explanation,
                    "source_file": concept.source_file,
                }
            )
    return candidates


@lru_cache(maxsize=1)
def _search_concepts() -> tuple[ReaderSearchConcept, ...]:
    return tuple(load_search_concepts(READER_SEARCH_CONCEPT_ROOT))


def _search_concepts_for_language(language: str) -> tuple[ReaderSearchConcept, ...]:
    return tuple(concept for concept in _search_concepts() if concept.language == language)


def _unique_candidate_dicts(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = unique(
        [
            f"{candidate.get('query')}\0{candidate.get('field')}"
            for candidate in candidates
            if candidate.get("query")
        ]
    )
    ordered: list[dict[str, Any]] = []
    for key in keys:
        query, field = key.split("\0", 1)
        matches = [
            candidate
            for candidate in candidates
            if candidate.get("query") == query and candidate.get("field") == field
        ]
        if matches:
            ordered.append(max(matches, key=_candidate_kind_priority))
    return ordered


def _candidate_kind_priority(candidate: dict[str, Any]) -> int:
    kind = str(candidate.get("kind") or "")
    if kind == "concept_alias":
        return 3
    if kind == "inflection_variant":
        return 2
    if kind == "transliteration_expansion":
        return 1
    return 0


def _search_filters(  # noqa: PLR0913
    *,
    language: str | None,
    collection_id: str | None,
    work_id: str | None,
    author_id: str | None,
    group: str | None,
    tag: str | None,
) -> tuple[list[str], list[object]]:
    conditions: list[str] = []
    params: list[object] = []
    for column, value in (
        ("s.language", language),
        ("s.collection_id", collection_id),
        ("s.work_id", work_id),
        ("s.canonical_author_id", author_id),
        ("s.classification_discovery_group_id", group),
    ):
        if value:
            conditions.append(f"{column} = ?")
            params.append(value)
    if tag:
        conditions.append("list_contains(string_split(s.classification_discovery_tags, '|'), ?)")
        params.append(tag)
    return conditions, params


def _search_field(field: str) -> str:
    if field == "display":
        return "display_text"
    if field == "search":
        return "search_text"
    if field in {"auto", "folded"}:
        return "search_text_folded"
    if field not in LANCE_SEARCH_FIELDS:
        return "search_text_folded"
    return field


def _search_query(normalized: Any, search_field: str, mode: str) -> str:
    query = (
        normalized.search_text if search_field == "search_text" else normalized.search_text_folded
    )
    if mode == "exact":
        return f'"{query}"'
    if mode == "phrase":
        return f'"{query}"'
    return query


def _attach_context(
    conn: duckdb.DuckDBPyConnection,
    dataset_path: Path,
    item: dict[str, Any],
    *,
    context: int,
) -> None:
    dataset = _sql_literal(dataset_path)
    params = [item["work_id"], item["sort_key"], context]
    item["context_before"] = [
        _context_item(row)
        for row in reversed(
            _dict_rows(
                conn,
                f"""
                SELECT citation_path, display_text AS text, sort_key
                FROM {dataset}
                WHERE work_id = ? AND sort_key < ?
                ORDER BY sort_key DESC
                LIMIT ?
                """,
                params,
            )
        )
    ]
    item["context_after"] = [
        _context_item(row)
        for row in _dict_rows(
            conn,
            f"""
            SELECT citation_path, display_text AS text, sort_key
            FROM {dataset}
            WHERE work_id = ? AND sort_key > ?
            ORDER BY sort_key
            LIMIT ?
            """,
            params,
        )
    ]


def _attach_context_windows(
    catalog_path: Path,
    conn: duckdb.DuckDBPyConnection,
    dataset_path: Path,
    items: list[dict[str, Any]],
    *,
    context: int,
) -> None:
    artifact_paths = _context_artifact_paths(catalog_path, items)
    for item in items:
        artifact_path = artifact_paths.get(_context_artifact_key(item))
        if artifact_path is None:
            _attach_context(conn, dataset_path, item, context=context)
            continue
        _attach_book_context(artifact_path, item, context=context)


def _context_artifact_paths(
    catalog_path: Path,
    items: list[dict[str, Any]],
) -> dict[tuple[str, str], Path]:
    artifact_ids = sorted(
        {str(item.get("artifact_id") or "") for item in items if item.get("artifact_id")}
    )
    work_ids = sorted({str(item.get("work_id") or "") for item in items if item.get("work_id")})
    if not artifact_ids and not work_ids:
        return {}
    conditions: list[str] = []
    params: list[object] = []
    if artifact_ids:
        conditions.append(f"artifact_id IN ({', '.join('?' for _ in artifact_ids)})")
        params.extend(artifact_ids)
    if work_ids:
        conditions.append(f"work_id IN ({', '.join('?' for _ in work_ids)})")
        params.extend(work_ids)
    with duckdb.connect(str(catalog_path), read_only=True) as catalog_conn:
        rows = _dict_rows(
            catalog_conn,
            f"""
            SELECT artifact_id, work_id, artifact_path
            FROM artifacts
            WHERE {" OR ".join(conditions)}
            ORDER BY artifact_id
            """,
            params,
        )
    paths: dict[tuple[str, str], Path] = {}
    for row in rows:
        artifact_path = _resolve_artifact_path(catalog_path, str(row["artifact_path"]))
        paths.setdefault(("artifact_id", str(row["artifact_id"])), artifact_path)
        paths.setdefault(("work_id", str(row["work_id"])), artifact_path)
    return paths


def _context_artifact_key(item: dict[str, Any]) -> tuple[str, str]:
    artifact_id = str(item.get("artifact_id") or "")
    if artifact_id:
        return ("artifact_id", artifact_id)
    return ("work_id", str(item.get("work_id") or ""))


def _resolve_artifact_path(catalog_path: Path, artifact_path: str) -> Path:
    path = Path(artifact_path)
    if path.is_absolute():
        return path
    if path.exists():
        return path
    return catalog_path.parent / path


def _attach_book_context(
    book_path: Path,
    item: dict[str, Any],
    *,
    context: int,
) -> None:
    if not book_path.exists():
        item["context_before"] = []
        item["context_after"] = []
        return
    params = [item["work_id"], item["sort_key"], context]
    with duckdb.connect(str(book_path), read_only=True) as book_conn:
        item["context_before"] = [
            _context_item(row)
            for row in reversed(
                _dict_rows(
                    book_conn,
                    """
                    SELECT citation_path, text, sort_key
                    FROM segments
                    WHERE work_id = ? AND sort_key < ?
                    ORDER BY sort_key DESC
                    LIMIT ?
                    """,
                    params,
                )
            )
        ]
        item["context_after"] = [
            _context_item(row)
            for row in _dict_rows(
                book_conn,
                """
                SELECT citation_path, text, sort_key
                FROM segments
                WHERE work_id = ? AND sort_key > ?
                ORDER BY sort_key
                LIMIT ?
                """,
                params,
            )
        ]


def _result_item(row: dict[str, Any]) -> dict[str, Any]:
    text = str(row["display_text"])
    return {
        "score": float(row.get("score") or row.get("_score") or 0.0),
        "artifact_id": str(row["artifact_id"]),
        "work_id": str(row["work_id"]),
        "collection_id": str(row["collection_id"]),
        "language": str(row["language"]),
        "title": str(row["title"]),
        "author": str(row["author"]),
        "canonical_author_id": row.get("canonical_author_id"),
        "canonical_author_name": row.get("canonical_author_name"),
        "cts_work_urn": row.get("cts_work_urn"),
        "canonical_text_id": row.get("canonical_text_id"),
        "canonical_address": row.get("canonical_address"),
        "citation_path": str(row["citation_path"]),
        "segment_id": str(row["segment_id"]),
        "sort_key": int(row["sort_key"]),
        "text": text,
        "snippet": text,
        "context_before": [],
        "context_after": [],
        "target": {
            "reader_command": "reader show",
            "work_ref": str(row.get("canonical_text_id") or row["work_id"]),
            "segment": str(row["citation_path"]),
        },
    }


def _search_result_address(canonical_text_id: object, citation_path: str) -> str:
    text_id = str(canonical_text_id or "").strip()
    if not text_id:
        return ""
    return f"{text_id}?ref={citation_path}"


def _context_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation_path": str(row["citation_path"]),
        "text": str(row["text"]),
        "sort_key": int(row["sort_key"]),
    }


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


def _table_columns(conn: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()}


def _sql_literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"
