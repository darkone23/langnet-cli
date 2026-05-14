from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb

from langnet.reader.storage import list_alias_conflicts

REQUIRED_CATALOG_TABLES = {
    "works",
    "editions",
    "artifacts",
    "aliases",
    "source_files",
    "source_metadata",
}
REQUIRED_BOOK_TABLES = {"segments", "addresses"}
LEGACY_MARKUP_PATTERN = r"&\d*|\$(?:\d+(?![\d,])|[A-Za-z])"
LEGACY_MARKUP_RE = re.compile(LEGACY_MARKUP_PATTERN)
XML_LIKE_TAG_PATTERN = (
    r"</[A-Za-z][A-Za-z0-9:_-]*\s*>|"
    r"<[A-Za-z][A-Za-z0-9:_-]*/>|"
    r"<[A-Za-z][A-Za-z0-9:_-]*"
    r"(?:\s+[A-Za-z_:][A-Za-z0-9:_.-]*=\"[^\"]*\")+\s*/?>"
)
SEGMENT_MARKUP_RE = re.compile(rf"{XML_LIKE_TAG_PATTERN}|&\d+")


def validate_reader_catalog(catalog_path: Path) -> list[dict[str, str]]:  # noqa: C901
    issues: list[dict[str, str]] = []
    if not catalog_path.exists():
        return [
            {
                "code": "catalog_missing",
                "message": f"Reader catalog does not exist: {catalog_path}",
            }
        ]

    catalog_tables = _tables(catalog_path)
    for table in sorted(REQUIRED_CATALOG_TABLES - catalog_tables):
        issues.append(
            {
                "code": "catalog_table_missing",
                "message": f"Reader catalog missing required table: {table}",
            }
        )
    if issues:
        return issues

    for conflict in list_alias_conflicts(catalog_path):
        issues.append(
            {
                "code": "alias_conflict",
                "message": (
                    f"Alias {conflict['language']}:{conflict['alias']} targets "
                    f"{', '.join(str(target) for target in conflict['targets'])}"
                ),
            }
        )
    issues.extend(_alias_target_issues(catalog_path))

    for work in _work_rows(catalog_path):
        work_id = str(work["work_id"])
        for field in ("author", "title"):
            value = str(work[field])
            if LEGACY_MARKUP_RE.search(value):
                issues.append(
                    {
                        "code": "work_metadata_markup",
                        "message": (f"Work {work_id} has legacy markup in {field}: {value}"),
                    }
                )
    issues.extend(_legacy_cts_work_urn_issues(catalog_path))

    checked_artifact_paths: set[Path] = set()
    for artifact in _artifact_rows(catalog_path):
        artifact_path = Path(str(artifact["artifact_path"]))
        artifact_id = str(artifact["artifact_id"])
        if int(artifact["segment_count"]) == 0:
            issues.append(
                {
                    "code": "artifact_zero_segments",
                    "message": f"Book artifact has zero segments: {artifact_id}",
                }
            )
        if artifact_path in checked_artifact_paths:
            continue
        checked_artifact_paths.add(artifact_path)
        if not artifact_path.exists():
            issues.append(
                {
                    "code": "artifact_missing",
                    "message": f"Book artifact is missing: {artifact_id} {artifact_path}",
                }
            )
            continue
        issues.extend(_book_schema_and_quality_issues(artifact_path, artifact_id))
    return issues


def _tables(path: Path) -> set[str]:
    with duckdb.connect(str(path), read_only=True) as conn:
        return {
            str(row[0])
            for row in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }


def _artifact_rows(catalog_path: Path) -> list[dict[str, Any]]:
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        cursor = conn.execute(
            """
            SELECT artifact_id, artifact_path, segment_count
            FROM artifacts
            ORDER BY artifact_id
            """
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _work_rows(catalog_path: Path) -> list[dict[str, Any]]:
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        cursor = conn.execute(
            """
            SELECT work_id, author, title
            FROM works
            ORDER BY work_id
            """
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _alias_target_issues(catalog_path: Path) -> list[dict[str, str]]:
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = conn.execute(
            """
            SELECT a.language, a.alias, a.target
            FROM aliases a
            LEFT JOIN works by_id ON by_id.work_id = a.target
            LEFT JOIN works by_cts ON by_cts.cts_work_urn = a.target
            WHERE by_id.work_id IS NULL
              AND by_cts.work_id IS NULL
            ORDER BY a.language, a.alias, a.target
            LIMIT 20
            """
        ).fetchall()
    return [
        {
            "code": "alias_target_missing",
            "message": f"Alias {language}:{alias} targets missing work {target}",
        }
        for language, alias, target in rows
    ]


def _legacy_cts_work_urn_issues(catalog_path: Path) -> list[dict[str, str]]:
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        rows = conn.execute(
            """
            SELECT work_id, collection_id, author_id, source_id
            FROM works
            WHERE collection_id IN ('phi', 'tlg')
              AND (cts_work_urn IS NULL OR trim(cts_work_urn) = '')
            ORDER BY work_id
            LIMIT 50
            """
        ).fetchall()
    issues: list[dict[str, str]] = []
    for work_id, collection_id, author_id, source_id in rows:
        expected = _expected_legacy_cts_work_urn(
            str(collection_id),
            str(author_id or ""),
            str(source_id or ""),
        )
        if expected is None:
            continue
        issues.append(
            {
                "code": "legacy_cts_work_urn_missing",
                "message": f"Legacy work {work_id} is missing CTS work URN {expected}",
            }
        )
    return issues


def _expected_legacy_cts_work_urn(
    collection_id: str,
    author_id: str,
    source_id: str,
) -> str | None:
    work_number = source_id.rsplit(".", 1)[-1]
    if not work_number.isdigit():
        return None
    if collection_id == "tlg" and re.fullmatch(r"tlg\d{4}", author_id):
        return f"urn:cts:greekLit:{author_id}.tlg{work_number.zfill(3)}"
    if collection_id == "phi" and re.fullmatch(r"phi\d{4}", author_id):
        return f"urn:cts:latinLit:{author_id}.phi{work_number.zfill(3)}"
    return None


def _book_schema_and_quality_issues(
    artifact_path: Path,
    artifact_id: str,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    with duckdb.connect(str(artifact_path), read_only=True) as conn:
        book_tables = _tables_for_connection(conn)
        for table in sorted(REQUIRED_BOOK_TABLES - book_tables):
            issues.append(
                {
                    "code": "book_table_missing",
                    "message": f"Book artifact {artifact_id} missing required table: {table}",
                }
            )
        if not book_tables >= REQUIRED_BOOK_TABLES:
            return issues

        blank_rows = conn.execute(
            """
            SELECT segment_id, citation_path
            FROM segments
            WHERE length(trim(text)) = 0
            LIMIT 5
            """
        ).fetchall()
        for segment_id, citation_path in blank_rows:
            issues.append(
                {
                    "code": "segment_blank_text",
                    "message": (
                        f"Book artifact {artifact_id} has blank segment text: "
                        f"{segment_id} ({citation_path})"
                    ),
                }
            )

        text_rows = conn.execute(
            """
            SELECT segment_id, citation_path, text
            FROM segments
            WHERE regexp_matches(text, '<[^>]+>|&')
            LIMIT 5
            """
        ).fetchall()
        for segment_id, citation_path, text in text_rows:
            if not SEGMENT_MARKUP_RE.search(str(text)):
                continue
            issues.append(
                {
                    "code": "segment_text_markup",
                    "message": (
                        f"Book artifact {artifact_id} has markup-like text in segment "
                        f"{segment_id} ({citation_path})"
                    ),
                }
            )
    return issues


def _tables_for_connection(conn: duckdb.DuckDBPyConnection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    }
