from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from langnet.reader.bulk_classification import load_classification_input_rows

RESEARCH_NEEDS_FIELDS = [
    "priority",
    "research_status",
    "research_need_type",
    "recommended_layer",
    "work_id",
    "language",
    "title",
    "author",
    "source_id",
    "classification_global_popularity_score",
    "classification_confidence",
    "classification_authorship_status",
    "research_reason",
    "existing_curated_coverage",
    "suggested_queries",
    "classification_notes",
]
UNCERTAIN_AUTHORSHIP_STATUSES = {
    "traditional",
    "attributed",
    "uncertain",
    "disputed",
    "composite",
    "pseudepigraphic",
}
UNKNOWN_AUTHOR_VALUES = {"", "unknown", "anonymous", "anon.", "anon"}
LONG_WORK_MAP_WORD_COUNT = 10000
HIGH_IMPACT_SCORE = 70
CANONICAL_SCORE = 90
BIO_CONTEXT_TERMS = ("life", "biography", "suda", "lexicon", "vita")
CONTAINED_CONTEXT_TERMS = (
    "within",
    "inside",
    "embedded",
    "part of",
    "contained",
    "mahābhārata",
    "mahabharata",
)


@dataclass(frozen=True)
class ResearchNeedsConfig:
    catalog_path: Path
    classification_csv: Path
    output_csv: Path | None = None
    language: str | None = None
    limit: int | None = None
    per_need_type_limit: int | None = None
    include_covered: bool = False
    include_unresolved: bool = False


@dataclass(frozen=True)
class _NeedSpec:
    need_type: str
    recommended_layer: str
    reason: str
    base_priority: int


def research_needs_for_classification_csv(
    *,
    config: ResearchNeedsConfig,
) -> list[dict[str, str]]:
    rows = load_classification_input_rows(config.classification_csv)
    if config.language:
        rows = [
            row
            for row in rows
            if str(row.get("language") or "").casefold() == config.language.casefold()
        ]
    coverage = _load_research_coverage(config.catalog_path)
    needs: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        work = _resolve_catalog_work(row, coverage)
        if work is None:
            if config.include_unresolved:
                needs.append(_unresolved_identity_need(row, index))
            continue
        merged = {**row, **_identity_fields(work)}
        work_needs = _research_needs_for_row(merged, coverage)
        if not config.include_covered:
            work_needs = [
                need for need in work_needs if need["research_status"] != "already_curated"
            ]
        for need in work_needs:
            need["_input_index"] = str(index)
        needs.extend(work_needs)
    needs.sort(key=lambda need: (-int(need["priority"]), int(need["_input_index"])))
    if config.per_need_type_limit is not None:
        needs = _limit_needs_per_type(needs, config.per_need_type_limit)
    for need in needs:
        need.pop("_input_index", None)
    if config.limit is not None:
        needs = needs[: config.limit]
    return needs


def export_research_needs_csv(*, config: ResearchNeedsConfig) -> dict[str, Any]:
    needs = research_needs_for_classification_csv(config=config)
    if config.output_csv is None:
        raise ValueError("output_csv is required to export research needs")
    expanded_path = config.output_csv.expanduser()
    expanded_path.parent.mkdir(parents=True, exist_ok=True)
    with expanded_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESEARCH_NEEDS_FIELDS)
        writer.writeheader()
        for need in needs:
            writer.writerow({field: need.get(field, "") for field in RESEARCH_NEEDS_FIELDS})
    input_count = len(load_classification_input_rows(config.classification_csv))
    return {
        "input_count": input_count,
        "catalog_resolved_count": _catalog_resolved_count(
            config.catalog_path,
            config.classification_csv,
            language=config.language,
        ),
        "unresolved_input_count": _unresolved_input_count(
            config.catalog_path,
            config.classification_csv,
            language=config.language,
        ),
        "research_need_count": len(needs),
        "output_csv": str(config.output_csv),
        "language": config.language,
        "limit": config.limit,
        "per_need_type_limit": config.per_need_type_limit,
        "include_covered": config.include_covered,
        "include_unresolved": config.include_unresolved,
        "need_type_counts": _need_type_counts(needs),
    }


@dataclass(frozen=True)
class _ResearchCoverage:
    works: dict[str, dict[str, str]]
    work_lookup: dict[str, str]
    accepted_attributions: set[str]
    accepted_contained_parent_ids: set[str]
    accepted_contained_work_ids: set[str]
    accepted_work_maps: set[str]
    aliases: set[str]
    source_metadata: set[str]
    display_overlays: set[str]


def _research_needs_for_row(
    row: dict[str, str],
    coverage: _ResearchCoverage,
) -> list[dict[str, str]]:
    needs = []
    if _needs_attribution_research(row):
        needs.append(
            _need_row(
                row,
                coverage,
                spec=_NeedSpec(
                    need_type="attribution_needed",
                    recommended_layer="data/curated/reader_attributions",
                    reason="generated attribution is not curated as source-backed metadata",
                    base_priority=75,
                ),
            )
        )
    if _needs_work_map_research(row):
        needs.append(
            _need_row(
                row,
                coverage,
                spec=_NeedSpec(
                    need_type="work_map_needed",
                    recommended_layer="data/curated/reader_work_maps",
                    reason="long or structured work has no accepted curated table of contents",
                    base_priority=55,
                ),
            )
        )
    if _needs_contained_work_research(row):
        needs.append(
            _need_row(
                row,
                coverage,
                spec=_NeedSpec(
                    need_type="contained_work_needed",
                    recommended_layer="data/curated/reader_contained_works",
                    reason="generated notes suggest embedded or contained work structure",
                    base_priority=65,
                ),
            )
        )
    if not needs and _needs_source_context_research(row):
        needs.append(
            _need_row(
                row,
                coverage,
                spec=_NeedSpec(
                    need_type="source_context_needed",
                    recommended_layer="source_metadata / source enrichment path",
                    reason=(
                        "classification has low confidence or high impact without source context"
                    ),
                    base_priority=45,
                ),
            )
        )
    return [
        need
        for need in needs
        if need["research_status"] != "already_curated"
        or need["research_need_type"] == "source_context_needed"
    ]


def _unresolved_identity_need(row: dict[str, str], index: int) -> dict[str, str]:
    title = _value(row, "title")
    language = _language_label(_value(row, "language"))
    source_id = _value(row, "source_id")
    return {
        "priority": "40",
        "research_status": "identity_unresolved",
        "research_need_type": "catalog_identity_needed",
        "recommended_layer": "generated classification CSV / catalog restore",
        "work_id": _value(row, "work_id"),
        "language": _value(row, "language"),
        "title": title,
        "author": _value(row, "author"),
        "source_id": source_id,
        "classification_global_popularity_score": _value(
            row, "classification_global_popularity_score"
        ),
        "classification_confidence": _value(row, "classification_confidence"),
        "classification_authorship_status": _value(row, "classification_authorship_status"),
        "research_reason": ("generated classification row does not resolve to the current catalog"),
        "existing_curated_coverage": "",
        "suggested_queries": (
            f"{title} {language} catalog identity; {source_id} {language} source id"
        ).strip(),
        "classification_notes": _value(row, "classification_notes"),
        "_input_index": str(index),
    }


def _need_row(
    row: dict[str, str],
    coverage: _ResearchCoverage,
    *,
    spec: _NeedSpec,
) -> dict[str, str]:
    coverage_label = _coverage_label(row, coverage, spec.need_type)
    research_status = "already_curated" if coverage_label else "new"
    priority = _priority(row, spec.base_priority)
    if research_status == "already_curated":
        priority = max(0, priority - 60)
    return {
        "priority": str(priority),
        "research_status": research_status,
        "research_need_type": spec.need_type,
        "recommended_layer": spec.recommended_layer,
        "work_id": _value(row, "work_id"),
        "language": _value(row, "language"),
        "title": _value(row, "title"),
        "author": _value(row, "author"),
        "source_id": _value(row, "source_id"),
        "classification_global_popularity_score": _value(
            row, "classification_global_popularity_score"
        ),
        "classification_confidence": _value(row, "classification_confidence"),
        "classification_authorship_status": _value(row, "classification_authorship_status"),
        "research_reason": spec.reason,
        "existing_curated_coverage": coverage_label,
        "suggested_queries": _suggested_queries(row, spec.need_type),
        "classification_notes": _value(row, "classification_notes"),
    }


def _needs_attribution_research(row: dict[str, str]) -> bool:
    authorship_status = _value(row, "classification_authorship_status").casefold()
    author = _value(row, "author").casefold()
    notes = _value(row, "classification_notes").casefold()
    return (
        author in UNKNOWN_AUTHOR_VALUES
        and authorship_status in UNCERTAIN_AUTHORSHIP_STATUSES
        or "attributed to" in notes
        or "traditionally attributed" in notes
    )


def _needs_work_map_research(row: dict[str, str]) -> bool:
    return _word_count(row) >= LONG_WORK_MAP_WORD_COUNT


def _needs_contained_work_research(row: dict[str, str]) -> bool:
    if _value(row, "work_kind") == "contained":
        return False
    haystack = f"{_value(row, 'title')} {_value(row, 'classification_notes')}".casefold()
    return any(term in haystack for term in CONTAINED_CONTEXT_TERMS)


def _needs_source_context_research(row: dict[str, str]) -> bool:
    if _value(row, "source_metadata_summary"):
        return False
    low_confidence = _value(row, "classification_confidence").casefold() == "low"
    return low_confidence or _score(row) >= CANONICAL_SCORE


def _coverage_label(row: dict[str, str], coverage: _ResearchCoverage, need_type: str) -> str:
    work_id = _value(row, "work_id")
    candidates = _coverage_candidates(row, coverage)
    labels = {
        "attribution_needed": (
            "accepted_attribution",
            bool(candidates & coverage.accepted_attributions),
        ),
        "contained_work_needed": (
            "accepted_contained_work",
            work_id in coverage.accepted_contained_parent_ids
            or work_id in coverage.accepted_contained_work_ids,
        ),
        "work_map_needed": ("accepted_work_map", work_id in coverage.accepted_work_maps),
        "source_context_needed": ("source_metadata", bool(candidates & coverage.source_metadata)),
        "display_metadata_needed": (
            "accepted_display_overlay",
            bool(candidates & coverage.display_overlays),
        ),
        "alias_needed": ("alias", work_id in coverage.aliases),
    }
    label, covered = labels.get(need_type, ("", False))
    if covered:
        return label
    return ""


def _coverage_candidates(row: dict[str, str], coverage: _ResearchCoverage) -> set[str]:
    work_id = _value(row, "work_id")
    work = coverage.works.get(work_id, {})
    values = {
        work_id,
        _value(row, "source_id"),
        _value(row, "cts_work_urn"),
        _value(work, "source_id"),
        _value(work, "cts_work_urn"),
    }
    return {value for value in values if value}


def _resolve_catalog_work(
    row: dict[str, str],
    coverage: _ResearchCoverage,
) -> dict[str, str] | None:
    exact_work = coverage.works.get(_value(row, "work_id"))
    if exact_work is not None:
        return exact_work
    for key in _catalog_identity_lookup_keys(
        _value(row, "work_id"),
        _value(row, "source_id"),
        _value(row, "cts_work_urn"),
    ):
        work_id = coverage.work_lookup.get(key)
        if work_id:
            return coverage.works.get(work_id)
    return None


def _identity_fields(work: dict[str, str]) -> dict[str, str]:
    return {
        "work_id": _value(work, "work_id"),
        "language": _value(work, "language"),
        "title": _value(work, "title"),
        "author": _value(work, "author"),
        "source_id": _value(work, "source_id"),
        "cts_work_urn": _value(work, "cts_work_urn"),
        "author_id": _value(work, "author_id"),
    }


def _priority(row: dict[str, str], base_priority: int) -> int:
    priority = base_priority
    score = _score(row)
    if score >= CANONICAL_SCORE:
        priority += 20
    elif score >= HIGH_IMPACT_SCORE:
        priority += 10
    if _value(row, "classification_confidence").casefold() == "low":
        priority += 15
    return priority


def _suggested_queries(row: dict[str, str], need_type: str) -> str:
    title = _value(row, "title")
    language = _language_label(_value(row, "language"))
    author = _value(row, "author")
    if need_type == "attribution_needed":
        return f"{title} {language} attribution; {title} {language} author"
    if need_type == "work_map_needed":
        return f"{title} {language} table of contents; {title} {language} chapters"
    if need_type == "contained_work_needed":
        return f"{title} {language} contained work; {title} {language} citation range"
    if need_type == "source_context_needed":
        return f"{title} {language} genre source; {title} {author} {language}".strip()
    return f"{title} {language}"


def _language_label(language: str) -> str:
    return {"grc": "Greek", "lat": "Latin", "san": "Sanskrit"}.get(language, language)


def _score(row: dict[str, str]) -> int:
    for field in ("classification_global_popularity_score", "classification_popularity_score"):
        raw_value = _value(row, field)
        if not raw_value:
            continue
        try:
            return int(float(raw_value))
        except ValueError:
            continue
    return 0


def _word_count(row: dict[str, str]) -> int:
    raw_value = _value(row, "word_count")
    if not raw_value:
        return 0
    try:
        return int(float(raw_value))
    except ValueError:
        return 0


def _need_type_counts(needs: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for need in needs:
        need_type = need["research_need_type"]
        counts[need_type] = counts.get(need_type, 0) + 1
    return counts


def _limit_needs_per_type(
    needs: list[dict[str, str]],
    per_need_type_limit: int,
) -> list[dict[str, str]]:
    counts: dict[str, int] = {}
    limited: list[dict[str, str]] = []
    for need in needs:
        need_type = need["research_need_type"]
        count = counts.get(need_type, 0)
        if count >= per_need_type_limit:
            continue
        counts[need_type] = count + 1
        limited.append(need)
    return limited


def _load_research_coverage(catalog_path: Path) -> _ResearchCoverage:
    if not catalog_path.exists():
        return _ResearchCoverage({}, {}, set(), set(), set(), set(), set(), set(), set())
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        works = _load_work_rows(conn)
        return _ResearchCoverage(
            works=works,
            work_lookup=_catalog_work_lookup(works),
            accepted_attributions=_load_single_column_set(
                conn,
                "metadata_attributions",
                "match_value",
                "WHERE status = 'accepted'",
            ),
            accepted_contained_parent_ids=_load_single_column_set(
                conn,
                "contained_works",
                "parent_work_id",
                "WHERE status = 'accepted'",
            ),
            accepted_contained_work_ids=_load_single_column_set(
                conn,
                "contained_works",
                "contained_work_id",
                "WHERE status = 'accepted'",
            ),
            accepted_work_maps=_load_single_column_set(
                conn,
                "work_map_nodes",
                "work_id",
                "WHERE status = 'accepted'",
            ),
            aliases=_load_single_column_set(conn, "aliases", "target", ""),
            source_metadata=_load_single_column_set(conn, "source_metadata", "subject_id", ""),
            display_overlays=_load_single_column_set(
                conn,
                "metadata_overlays",
                "match_value",
                "WHERE status = 'accepted'",
            ),
        )


def _load_work_rows(conn: duckdb.DuckDBPyConnection) -> dict[str, dict[str, str]]:
    if not _table_exists(conn, "works"):
        return {}
    rows = conn.execute(
        """
        SELECT work_id, collection_id, language, title, author, author_id, source_id,
               cts_work_urn, canonical_text_id
        FROM works
        """
    ).fetchall()
    return {
        str(row[0]): {
            "work_id": str(row[0] or ""),
            "collection_id": str(row[1] or ""),
            "language": str(row[2] or ""),
            "title": str(row[3] or ""),
            "author": str(row[4] or ""),
            "author_id": str(row[5] or ""),
            "source_id": str(row[6] or ""),
            "cts_work_urn": str(row[7] or ""),
            "canonical_text_id": str(row[8] or ""),
        }
        for row in rows
    }


def _catalog_work_lookup(works: dict[str, dict[str, str]]) -> dict[str, str]:
    candidates: dict[str, set[str]] = {}
    for work_id, work in works.items():
        for key in _catalog_identity_lookup_keys(
            work_id,
            _value(work, "source_id"),
            _value(work, "cts_work_urn"),
        ):
            candidates.setdefault(key, set()).add(work_id)
    return {key: next(iter(values)) for key, values in candidates.items() if len(values) == 1}


def _catalog_identity_lookup_keys(*values: str) -> set[str]:
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


def _catalog_resolved_count(
    catalog_path: Path,
    classification_csv: Path,
    *,
    language: str | None,
) -> int:
    rows = load_classification_input_rows(classification_csv)
    if language:
        rows = [
            row for row in rows if str(row.get("language") or "").casefold() == language.casefold()
        ]
    coverage = _load_research_coverage(catalog_path)
    return sum(1 for row in rows if _resolve_catalog_work(row, coverage) is not None)


def _unresolved_input_count(
    catalog_path: Path,
    classification_csv: Path,
    *,
    language: str | None,
) -> int:
    rows = load_classification_input_rows(classification_csv)
    if language:
        rows = [
            row for row in rows if str(row.get("language") or "").casefold() == language.casefold()
        ]
    return len(rows) - _catalog_resolved_count(
        catalog_path,
        classification_csv,
        language=language,
    )


def _load_single_column_set(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    column_name: str,
    where_sql: str,
) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    return {
        str(row[0])
        for row in conn.execute(
            f"SELECT DISTINCT {column_name} FROM {table_name} {where_sql}"
        ).fetchall()
        if row[0]
    }


def _table_exists(conn: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
    )


def _value(row: dict[str, str], field: str) -> str:
    return str(row.get(field) or "").strip()
