from __future__ import annotations

import csv
import re
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

import duckdb
from query_spec import LanguageHint

from langnet.normalizer.core import _hash_query
from langnet.reader.author_classification import (
    author_agent_kind_allowed_values,
    author_historicity_status_allowed_values,
    load_author_classifications,
)
from langnet.reader.citation_map import load_citation_maps
from langnet.reader.classification import load_work_classifications
from langnet.reader.discovery_taxonomy import (
    discovery_group_allowed_values,
    discovery_tag_allowed_values,
)
from langnet.reader.display import decorate_segment_display
from langnet.reader.division_metadata import (
    accepted_division_metadata,
    load_division_metadata,
)
from langnet.reader.metadata_attribution import load_metadata_attributions
from langnet.reader.metadata_overlay import load_metadata_overlays
from langnet.reader.models import ReaderMetadataOverlay, ReaderWorkMapNode
from langnet.reader.search_index import (
    build_reader_search_index,
    inspect_reader_search_query,
    reader_search_index_status,
    search_reader_segments,
    validate_reader_search_index,
)
from langnet.reader.search_normalization import (
    normalize_query_for_search,
    normalize_segment_for_search,
)
from langnet.reader.source_enrichment import (
    dcs_chapter_info_work_map_candidates,
    parse_dcs_chapter_info_metadata,
    parse_perseus_catalog_results,
    perseus_candidate_metadata_overlays,
    sync_dcs_corpus_metadata,
)
from langnet.reader.storage import (
    apply_metadata_overlays_to_catalog,
    citation_maps_for_work,
    current_divisions_for_segment,
    get_work,
    list_alias_conflicts,
    list_aliases,
    list_author_index,
    list_author_sections,
    list_collections,
    list_discovery_group_summaries,
    list_discovery_shelves,
    list_discovery_tag_summaries,
    list_duplicate_audit,
    list_metadata_attributions,
    list_metadata_overlays,
    list_segments_for_work,
    list_source_files,
    list_source_index,
    list_source_metadata,
    list_works,
    lookup_segment_by_address,
    lookup_segment_by_work_and_citation,
    lookup_segments_by_citation_reference,
    prune_stale_work_classifications,
    reader_discovery_coverage,
    reader_summary,
    register_author_classifications,
    register_citation_maps,
    register_division_metadata,
    register_metadata_attributions,
    register_metadata_overlays,
    register_source_metadata,
    register_work_classifications,
    register_work_map_nodes,
    repair_work_languages,
    resolve_structure_reference,
    resolve_work_ref,
    segment_navigation,
    structure_for_work,
    work_map_for_work,
)
from langnet.reader.validation import validate_reader_catalog
from langnet.reader.work_map import accepted_work_map_nodes, load_work_map_nodes
from langnet.storage.normalization_index import NormalizationIndex
from langnet.storage.paths import normalization_db_path

READER_SCHEMA_VERSION = "langnet.reader.v1"
WORD_CONTEXT_SCHEMA_VERSION = "langnet.reader.word_context.v1"
SOURCE_INDEX_EXPORT_COLUMNS = (
    "collection_id",
    "language",
    "work_id",
    "title",
    "author",
    "author_id",
    "source_id",
    "cts_work_urn",
    "canonical_text_id",
    "edition_id",
    "edition_label",
    "source_path",
    "cts_edition_urn",
    "file_role",
    "file_status",
    "source_hash",
    "size_bytes",
    "artifact_count",
    "segment_count",
    "token_count",
    "adapters",
    "artifact_paths",
    "source_witness_count",
    "source_witness_collections",
)
_DOTTED_CITATION_RE = re.compile(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+")
_CITATION_LABEL_RE = re.compile(r"\b(?:book|bk|line|ln|l)\.?\b", re.IGNORECASE)
_CITATION_PART_RE = re.compile(r"[0-9]+[A-Za-z]?|[ivxlcdm]+", re.IGNORECASE)
_ROMAN_CITATION_RE = re.compile(r"[ivxlcdm]+", re.IGNORECASE)
_ROMAN_CITATION_VALUES = {
    "i": 1,
    "v": 5,
    "x": 10,
    "l": 50,
    "c": 100,
    "d": 500,
    "m": 1000,
}
MIN_CITATION_PARTS = 2


class ReaderService:
    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = catalog_path

    def collections_payload(self) -> dict[str, Any]:
        return self._payload("collections", list_collections(self.catalog_path))

    def collections(self) -> dict[str, Any]:
        return self.collections_payload()

    def authors_payload(  # noqa: PLR0913
        self,
        *,
        language: str | None = None,
        section: str | None = None,
        query: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        agent_kind: str | None = None,
        historicity: str | None = None,
        sort: str = "catalog",
    ) -> dict[str, Any]:
        offset = _cursor_offset(cursor)
        fetch_limit = limit + 1 if limit is not None else None
        items = list_author_index(
            self.catalog_path,
            language=language,
            section=section,
            query=query,
            limit=fetch_limit,
            offset=offset,
            agent_kind=agent_kind,
            historicity=historicity,
            sort=sort,
        )
        has_more = limit is not None and len(items) > limit
        if limit is not None:
            items = items[:limit]
        return self._payload(
            "authors",
            items,
            language=language,
            section=section,
            query=query,
            agent_kind=agent_kind,
            historicity=historicity,
            sort=sort,
            pagination=_pagination(limit=limit, offset=offset, has_more=has_more),
        )

    def author_sections_payload(self, *, language: str) -> dict[str, Any]:
        return self._payload(
            "author-sections",
            list_author_sections(self.catalog_path, language=language),
            language=language,
        )

    def author_payload(
        self,
        author_ref: str,
        *,
        language: str | None = None,
        representative_limit: int = 8,
    ) -> dict[str, Any]:
        item = _find_author_detail_item(
            list_author_index(self.catalog_path, language=language),
            author_ref,
        )
        representative_works: list[dict[str, Any]] = []
        query: dict[str, Any] | None = None
        if item is not None:
            author_id = str(item.get("source_author_id") or item.get("author_id") or "")
            item_language = str(item.get("language") or language or "")
            if author_id:
                representative_works = list_works(
                    self.catalog_path,
                    language=item_language or language,
                    author_id=author_id,
                    limit=representative_limit,
                    sort="global-popularity",
                )
                query = {"language": item_language or language, "author_id": author_id}
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "author",
            "catalog_path": str(self.catalog_path),
            "request": {
                "author_ref": author_ref,
                "language": language,
                "representative_limit": representative_limit,
            },
            "item": item,
            "query": query,
            "representative_works": representative_works,
        }

    def duplicate_audit_payload(
        self,
        *,
        kind: str = "authors",
        language: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return self._payload(
            "duplicate-audit",
            list_duplicate_audit(
                self.catalog_path,
                kind=kind,
                language=language,
                limit=limit,
            ),
            kind=kind,
            language=language,
            limit=limit,
        )

    def authors(  # noqa: PLR0913
        self,
        *,
        language: str | None = None,
        section: str | None = None,
        query: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        agent_kind: str | None = None,
        historicity: str | None = None,
        sort: str = "catalog",
    ) -> dict[str, Any]:
        return self.authors_payload(
            language=language,
            section=section,
            query=query,
            limit=limit,
            cursor=cursor,
            agent_kind=agent_kind,
            historicity=historicity,
            sort=sort,
        )

    def works_payload(  # noqa: PLR0913
        self,
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
        cursor: str | None = None,
        sort: str = "catalog",
    ) -> dict[str, Any]:
        offset = _cursor_offset(cursor)
        fetch_limit = limit + 1 if limit is not None else None
        items = list_works(
            self.catalog_path,
            language=language,
            collection_id=collection_id,
            author=author,
            attributed_to=attributed_to,
            author_id=author_id,
            classification_scope=classification_scope,
            classification_group=classification_group,
            classification_tag=classification_tag,
            query=query,
            limit=fetch_limit,
            offset=offset,
            sort=sort,
        )
        has_more = limit is not None and len(items) > limit
        if limit is not None:
            items = items[:limit]
        return self._payload(
            "works",
            items,
            language=language,
            collection_id=collection_id,
            author=author,
            attributed_to=attributed_to,
            author_id=author_id,
            classification_scope=classification_scope,
            classification_group=classification_group,
            classification_tag=classification_tag,
            query=query,
            sort=sort,
            pagination=_pagination(limit=limit, offset=offset, has_more=has_more),
        )

    def works(  # noqa: PLR0913
        self,
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
        cursor: str | None = None,
        sort: str = "catalog",
    ) -> dict[str, Any]:
        return self.works_payload(
            language=language,
            collection_id=collection_id,
            author=author,
            attributed_to=attributed_to,
            author_id=author_id,
            classification_scope=classification_scope,
            classification_group=classification_group,
            classification_tag=classification_tag,
            query=query,
            limit=limit,
            cursor=cursor,
            sort=sort,
        )

    def discovery_groups_payload(self, *, language: str | None = None) -> dict[str, Any]:
        items = (
            list_discovery_group_summaries(self.catalog_path, language=language)
            if language
            else discovery_group_allowed_values()
        )
        return self._payload("groups", items, language=language)

    def discovery_tags_payload(self, *, language: str | None = None) -> dict[str, Any]:
        items = (
            list_discovery_tag_summaries(self.catalog_path, language=language)
            if language
            else discovery_tag_allowed_values()
        )
        return self._payload("tags", items, language=language)

    def author_facets_payload(self) -> dict[str, Any]:
        return self._payload(
            "author-facets",
            [
                {
                    "id": "agent_kind",
                    "label": "Author agent kinds",
                    "description": "Strict values used by reader authors --agent-kind.",
                    "filter": "--agent-kind",
                    "values": author_agent_kind_allowed_values(),
                },
                {
                    "id": "historicity",
                    "label": "Author historicity statuses",
                    "description": "Strict values used by reader authors --historicity.",
                    "filter": "--historicity",
                    "values": author_historicity_status_allowed_values(),
                },
            ],
        )

    def discovery_facets_payload(self, *, language: str | None = None) -> dict[str, Any]:
        group_values = (
            list_discovery_group_summaries(self.catalog_path, language=language)
            if language
            else discovery_group_allowed_values()
        )
        tag_values = (
            list_discovery_tag_summaries(self.catalog_path, language=language)
            if language
            else discovery_tag_allowed_values()
        )
        return self._payload(
            "facets",
            [
                {
                    "id": "discovery_groups",
                    "label": "Discovery groups",
                    "description": (
                        "Primary peer buckets used by --group and --sort group-popularity."
                    ),
                    "command": (
                        f"reader groups --language {language}" if language else "reader groups"
                    ),
                    "filter": "--group",
                    "values": group_values,
                },
                {
                    "id": "discovery_tags",
                    "label": "Discovery tags",
                    "description": "Controlled faceted tags used by --tag.",
                    "command": (
                        f"reader tags --language {language}" if language else "reader tags"
                    ),
                    "filter": "--tag",
                    "values": tag_values,
                },
                {
                    "id": "sorts",
                    "label": "Sort modes",
                    "description": "Supported ordering modes for reader works.",
                    "command": "reader works --sort",
                    "values": [
                        {
                            "id": "catalog",
                            "label": "Catalog order",
                            "description": "Stable source/catalog ordering.",
                        },
                        {
                            "id": "global-popularity",
                            "label": "Global popularity",
                            "description": "Popularity within the selected language corpus.",
                        },
                        {
                            "id": "group-popularity",
                            "label": "Group popularity",
                            "description": (
                                "Popularity within the work's primary discovery group."
                            ),
                        },
                        {
                            "id": "popularity",
                            "label": "Legacy popularity",
                            "description": "Compatibility alias for older generated metadata.",
                        },
                    ],
                },
                {
                    "id": "author_agent_kinds",
                    "label": "Author agent kinds",
                    "description": "Controlled values for generated author classification.",
                    "command": "reader author-facets",
                    "filter": "--agent-kind",
                    "values": author_agent_kind_allowed_values(),
                },
                {
                    "id": "author_historicity_statuses",
                    "label": "Author historicity statuses",
                    "description": "Controlled values for generated author classification.",
                    "command": "reader author-facets",
                    "filter": "--historicity",
                    "values": author_historicity_status_allowed_values(),
                },
                {
                    "id": "examples",
                    "label": "Example discovery questions",
                    "description": "Common CLI query shapes.",
                    "examples": [
                        {
                            "question": "Show me popular Ayurvedic texts.",
                            "command": (
                                "reader works --language san --tag ayurveda --sort group-popularity"
                            ),
                        },
                        {
                            "question": "Show me Latin grammar texts by popularity.",
                            "command": (
                                "reader works --language lat --group grammar "
                                "--sort group-popularity"
                            ),
                        },
                        {
                            "question": "Show me popular Greek medical texts.",
                            "command": (
                                "reader works --language grc --tag medicine --sort group-popularity"
                            ),
                        },
                        {
                            "question": "Show me the most broadly popular Sanskrit works.",
                            "command": ("reader works --language san --sort global-popularity"),
                        },
                        {
                            "question": "Show me source author labels that are work titles.",
                            "command": "reader authors --agent-kind work_title",
                        },
                        {
                            "question": "Show me pseudonymous author labels.",
                            "command": "reader authors --historicity pseudonymous",
                        },
                    ],
                },
            ],
            language=language,
        )

    def discovery_shelves_payload(
        self,
        *,
        language: str | None = None,
        limit: int | None = None,
        sample_limit: int = 3,
    ) -> dict[str, Any]:
        return self._payload(
            "shelves",
            list_discovery_shelves(
                self.catalog_path,
                language=language,
                limit=limit,
                sample_limit=sample_limit,
            ),
            language=language,
            limit=limit,
            sample_limit=sample_limit,
        )

    def coverage_payload(self) -> dict[str, Any]:
        return self._payload("coverage", reader_discovery_coverage(self.catalog_path))

    def search_index_build_payload(  # noqa: PLR0913
        self,
        *,
        index_path: Path,
        language: str | None = None,
        collection_id: str | None = None,
        replace: bool = False,
        batch_size: int = 50000,
        limit: int | None = None,
    ) -> dict[str, Any]:
        summary = build_reader_search_index(
            self.catalog_path,
            index_path,
            language=language,
            collection_id=collection_id,
            replace=replace,
            batch_size=batch_size,
            limit=limit,
        )
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "search-index-build",
            "catalog_path": str(self.catalog_path),
            "index_path": str(index_path),
            "request": {
                "language": language,
                "collection_id": collection_id,
                "replace": replace,
                "batch_size": batch_size,
                "limit": limit,
            },
            "summary": summary,
        }

    def search_index_status_payload(self, *, index_path: Path) -> dict[str, Any]:
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "search-index-status",
            "catalog_path": str(self.catalog_path),
            "index_path": str(index_path),
            "summary": reader_search_index_status(index_path),
        }

    def search_index_validate_payload(self, *, index_path: Path) -> dict[str, Any]:
        validation = validate_reader_search_index(self.catalog_path, index_path)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "search-index-validate",
            "catalog_path": str(self.catalog_path),
            "index_path": str(index_path),
            "summary": validation["status"] | {"issue_count": len(validation["issues"])},
            "items": validation["issues"],
        }

    def search_index_inspect_normalize_payload(
        self,
        *,
        language: str,
        text: str,
    ) -> dict[str, Any]:
        segment = normalize_segment_for_search(language, text)
        query = normalize_query_for_search(language, text)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "search-index-inspect-normalize",
            "catalog_path": str(self.catalog_path),
            "request": {"language": language, "text": text},
            "summary": {
                "segment": segment.__dict__,
                "query": {
                    **query.__dict__,
                    "query_variants": list(query.query_variants),
                },
            },
        }

    def search_index_inspect_query_payload(
        self,
        *,
        language: str,
        text: str,
        mode: str = "keyword",
        field: str = "auto",
    ) -> dict[str, Any]:
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "search-index-inspect-query",
            "catalog_path": str(self.catalog_path),
            "request": {
                "language": language,
                "text": text,
                "mode": mode,
                "field": field,
            },
            "summary": inspect_reader_search_query(
                language,
                text,
                mode=mode,
                field=field,
            ),
        }

    def search_payload(  # noqa: PLR0913
        self,
        *,
        index_path: Path,
        query: str,
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
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return search_reader_segments(
            self.catalog_path,
            index_path,
            query,
            language=language,
            collection_id=collection_id,
            work_id=work_id,
            author_id=author_id,
            group=group,
            tag=tag,
            mode=mode,
            field=field,
            context=context,
            limit=limit,
            offset=_cursor_offset(cursor),
        )

    def word_context_payload(  # noqa: PLR0913, PLR0915
        self,
        *,
        query: str,
        language: str,
        index_path: Path,
        work_ref: str | None = None,
        segment_ref: str | None = None,
        search_limit: int = 8,
        search_context: int = 1,
        lexical_evidence_provider: Callable[..., dict[str, Any]] | None = None,
        morphology_provider: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        steps: list[dict[str, Any]] = []
        caveats: list[str] = []

        def timed_step(name: str, started: float, **extra: Any) -> None:
            steps.append(
                {
                    "name": name,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                    **extra,
                }
            )

        step_started = perf_counter()
        normalized_query = normalize_query_for_search(language, query)
        cached_normalization = _cached_normalization_evidence(query, language)
        normalized_query_text = str(
            getattr(normalized_query, "search_text", "")
            or getattr(normalized_query, "token_text", "")
            or getattr(normalized_query, "search_text_folded", "")
            or ""
        )
        candidates = [
            candidate
            for candidate in [
                query,
                normalized_query_text,
                *[str(item.get("lemma") or "") for item in cached_normalization["items"]],
            ]
            if candidate
        ]
        normalized_candidates = list(dict.fromkeys(candidates))
        normalization = {
            "surface": query,
            "normalized": normalized_query,
            "candidates": normalized_candidates,
        }
        timed_step("normalization", step_started)

        step_started = perf_counter()
        lexical_evidence, lexical_evidence_caveats = _word_context_lexical_evidence(
            query=query,
            language=language,
            candidates=normalized_candidates,
            fallback=cached_normalization,
            lexical_evidence_provider=lexical_evidence_provider,
        )
        caveats.extend(lexical_evidence_caveats)
        timed_step(
            "lexical_evidence",
            step_started,
            status=str(lexical_evidence.get("status") or "unknown"),
            item_count=len(list(lexical_evidence.get("items") or [])),
        )

        step_started = perf_counter()
        morphology, morphology_caveats = _word_context_morphology(
            query=query,
            language=language,
            candidates=normalized_candidates,
            fallback=cached_normalization,
            morphology_provider=morphology_provider,
        )
        caveats.extend(morphology_caveats)
        timed_step(
            "morphology",
            step_started,
            status=str(morphology.get("status") or "unknown"),
            item_count=len(list(morphology.get("items") or [])),
        )

        work: dict[str, Any] | None = None
        segment: dict[str, Any] | None = None
        source_index_rows: list[dict[str, Any]] = []
        resolved_work_id: str | None = None
        step_started = perf_counter()
        if work_ref:
            work = get_work(self.catalog_path, work_ref)
            resolved_work_id = str(work.get("work_id") or "") if work else None
            if segment_ref:
                segment = lookup_segment_by_work_and_citation(
                    self.catalog_path,
                    work_ref,
                    segment_ref,
                )
                if segment is not None:
                    segment = decorate_segment_display(segment, language=language)
                    segment["current_divisions"] = current_divisions_for_segment(
                        self.catalog_path,
                        str(segment.get("work_id") or resolved_work_id or work_ref),
                        str(segment.get("citation_path") or segment_ref),
                    )
                    resolved_work_id = str(segment.get("work_id") or resolved_work_id or "")
            if resolved_work_id:
                source_index_rows = list_source_index(
                    self.catalog_path,
                    work_id=resolved_work_id,
                    limit=3,
                )
        timed_step(
            "passage_context",
            step_started,
            work_found=bool(work),
            segment_found=bool(segment),
            source_index_rows=len(source_index_rows),
        )

        step_started = perf_counter()
        try:
            index_status = reader_search_index_status(index_path)
        except Exception as exc:  # noqa: BLE001
            index_status = {
                "exists": False,
                "backend": "duckdb-lance",
                "dataset_path": str(index_path),
                "error": str(exc),
            }
            caveats.append("Reader search index status could not be inspected.")
        timed_step("search_index_status", step_started, exists=bool(index_status.get("exists")))

        reader_hits_status = "index_unavailable"
        reader_hit_items: list[dict[str, Any]] = []
        language_counts = index_status.get("language_counts")
        index_has_language = not isinstance(language_counts, dict) or language in {
            str(key) for key in language_counts
        }
        if index_status.get("exists") and not index_has_language:
            caveats.append(
                f"Reader search index has no {language} slice; corpus hits are unavailable "
                "for this language."
            )
        elif index_status.get("exists"):
            step_started = perf_counter()
            try:
                search_payload = search_reader_segments(
                    self.catalog_path,
                    index_path,
                    query,
                    language=language,
                    work_id=resolved_work_id,
                    mode="fuzzy",
                    field="auto",
                    context=search_context,
                    limit=search_limit,
                )
                reader_hit_items = list(search_payload.get("items") or [])
                reader_hits_status = "available" if reader_hit_items else "no_hits"
            except Exception as exc:  # noqa: BLE001
                reader_hits_status = "error"
                caveats.append(f"Reader corpus search failed: {exc}")
            timed_step(
                "reader_search",
                step_started,
                status=reader_hits_status,
                hit_count=len(reader_hit_items),
            )
        else:
            caveats.append("Reader search index is unavailable; corpus hits are not zero-proof.")

        source_row = source_index_rows[0] if source_index_rows else {}
        return {
            "schema_version": WORD_CONTEXT_SCHEMA_VERSION,
            "mode": "word-context",
            "catalog_path": str(self.catalog_path),
            "request": {
                "language": language,
                "query": query,
                "work_ref": work_ref,
                "segment_ref": segment_ref,
                "search_limit": search_limit,
                "search_context": search_context,
                "index_path": str(index_path),
            },
            "normalization": normalization,
            "lexical_evidence": {
                "status": lexical_evidence.get("status", "unavailable"),
                "items": list(lexical_evidence.get("items") or []),
                "note": lexical_evidence.get("note", ""),
            },
            "morphology": {
                "status": morphology.get("status", "unavailable"),
                "items": list(morphology.get("items") or []),
                "note": morphology.get("note", ""),
            },
            "reader_hits": {
                "status": reader_hits_status,
                "index_status": index_status,
                "items": reader_hit_items,
            },
            "passage_context": {
                "status": "available" if segment or work else "not_requested",
                "work": work,
                "segment": segment,
                "source_index": source_index_rows,
            },
            "provenance": {
                "work_id": resolved_work_id or source_row.get("work_id"),
                "collection_id": source_row.get("collection_id")
                or (work or {}).get("collection_id"),
                "source_id": source_row.get("source_id") or (work or {}).get("source_id"),
                "source_path": source_row.get("source_path"),
                "file_status": source_row.get("file_status"),
                "quality_status": source_row.get("file_status"),
                "edition_label": source_row.get("edition_label"),
                "canonical_text_id": source_row.get("canonical_text_id")
                or (work or {}).get("canonical_text_id"),
                "cts_work_urn": source_row.get("cts_work_urn") or (work or {}).get("cts_work_urn"),
            },
            "caveats": caveats,
            "timing": {
                "total_ms": round((perf_counter() - started_at) * 1000, 2),
                "steps": steps,
            },
        }

    def contents_payload(  # noqa: PLR0913
        self,
        work_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        from_citation: str | None = None,
        around: str | None = None,
        radius: int = 20,
        char_budget: int | None = None,
    ) -> dict[str, Any]:
        offset = _cursor_offset(cursor)
        fetch_limit = limit + 1 if around is None else limit
        items = list_segments_for_work(
            self.catalog_path,
            work_id,
            limit=fetch_limit,
            offset=offset,
            from_citation=from_citation,
            around=around,
            radius=radius,
        )
        source_count = len(items)
        if around is None:
            items = items[:limit]
        work = get_work(self.catalog_path, work_id)
        language = _work_language(work)
        items = [decorate_segment_display(item, language=language) for item in items]
        items = _budget_reader_segments(
            items,
            char_budget=char_budget,
            anchor=around,
            limit=limit,
        )
        for item in items:
            item["current_divisions"] = current_divisions_for_segment(
                self.catalog_path,
                str(item.get("work_id") or work_id),
                str(item.get("citation_path") or ""),
            )
        has_more = around is None and source_count > len(items)
        return self._payload(
            "contents",
            items,
            work_id=work_id,
            limit=limit,
            cursor=cursor,
            from_citation=from_citation,
            window=(
                {
                    "anchor": around,
                    "before_count": radius,
                    "after_count": radius,
                }
                if around
                else None
            ),
            pagination=_pagination(
                limit=limit,
                offset=offset,
                has_more=has_more,
                next_offset=offset + len(items),
            ),
        )

    def contents(self, work_id: str, *, limit: int = 50) -> dict[str, Any]:
        return self.contents_payload(work_id, limit=limit)

    def segment_payload(self, address: str) -> dict[str, Any]:
        resolved_address = address
        if " " in address.strip():
            resolved = self.resolve_address(address)
            segment = resolved["segment"]
            resolved_address = str(resolved["resolved_address"])
        else:
            segment = lookup_segment_by_address(self.catalog_path, address)
            if segment is None:
                resolved = self.resolve_address(address)
                segment = resolved["segment"]
                resolved_address = str(resolved["resolved_address"])
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "show",
            "catalog_path": str(self.catalog_path),
            "address": address,
            "resolved_address": resolved_address,
            "segment": _decorate_segment(self.catalog_path, segment),
            "current_divisions": (
                current_divisions_for_segment(
                    self.catalog_path,
                    str(segment.get("work_id") or ""),
                    str(segment.get("citation_path") or ""),
                )
                if segment
                else []
            ),
            "navigation": segment_navigation(self.catalog_path, segment) if segment else None,
        }

    def show(self, address: str) -> dict[str, Any]:
        return self.segment_payload(address)

    def show_work_segment(self, work_ref: str, citation_path: str) -> dict[str, Any]:
        segment = lookup_segment_by_work_and_citation(self.catalog_path, work_ref, citation_path)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "show",
            "catalog_path": str(self.catalog_path),
            "address": f"{work_ref} {citation_path}",
            "work_ref": work_ref,
            "citation_path": citation_path,
            "segment": _decorate_segment(self.catalog_path, segment),
            "current_divisions": (
                current_divisions_for_segment(
                    self.catalog_path,
                    str(segment.get("work_id") or work_ref),
                    str(segment.get("citation_path") or citation_path),
                )
                if segment
                else []
            ),
            "navigation": segment_navigation(self.catalog_path, segment) if segment else None,
        }

    def work_payload(self, work_ref: str) -> dict[str, Any]:
        item = get_work(self.catalog_path, work_ref)
        if item is not None and item.get("work_kind") == "work":
            matches = list_works(
                self.catalog_path,
                language=str(item.get("language") or "") or None,
                query=str(item.get("work_id") or ""),
                limit=25,
            )
            item = next(
                (match for match in matches if match.get("work_id") == item.get("work_id")),
                item,
            )
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "work",
            "catalog_path": str(self.catalog_path),
            "work_ref": work_ref,
            "item": item,
        }

    def map_payload(self, work_ref: str) -> dict[str, Any]:
        return self._payload(
            "map",
            work_map_for_work(self.catalog_path, work_ref),
            work_ref=work_ref,
        )

    def structure_payload(self, work_ref: str) -> dict[str, Any]:
        items = structure_for_work(self.catalog_path, work_ref)
        top_level = [item for item in items if int(item.get("level") or 0) == 1]
        kinds = sorted({str(item.get("kind") or "") for item in items if item.get("kind")})
        payload = self._payload("structure", items, work_ref=work_ref)
        payload["summary"] = {
            "node_count": len(items),
            "top_level_count": len(top_level),
            "kinds": kinds,
            "has_division_metadata": any(item.get("summary") for item in items),
        }
        return payload

    def work_dossier_payload(self, work_ref: str) -> dict[str, Any]:
        work = get_work(self.catalog_path, work_ref)
        items = structure_for_work(self.catalog_path, work_ref)
        top_level = [item for item in items if int(item.get("level") or 0) == 1]
        division_bios = [item for item in items if item.get("summary")]
        top_level_kind = _dominant_structure_kind(top_level)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "work-dossier",
            "catalog_path": str(self.catalog_path),
            "request": {"work_ref": work_ref},
            "work": work,
            "summary": {
                "structure_count": len(items),
                "top_level_count": len(top_level),
                "top_level_kind": top_level_kind,
                "structure_label": _structure_count_label(len(top_level), top_level_kind),
                "division_bio_count": len(division_bios),
                "has_division_metadata": bool(division_bios),
            },
            "headings": top_level,
            "division_bios": division_bios,
            "provenance_chips": _merge_provenance_chips(items),
        }

    def citation_maps_payload(
        self,
        work_ref: str,
        *,
        source_id: str | None = None,
    ) -> dict[str, Any]:
        return self._payload(
            "citation-maps",
            citation_maps_for_work(self.catalog_path, work_ref, source_id=source_id),
            work_ref=work_ref,
            source_id=source_id,
        )

    def sync_citation_maps_payload(self, citation_map_dir: Path) -> dict[str, Any]:
        maps = load_citation_maps(citation_map_dir)
        register_citation_maps(self.catalog_path, maps)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-citation-maps",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "citation_map_dir": str(citation_map_dir),
                "synced_count": len(maps),
            },
        }

    def sync_work_maps_payload(self, work_map_dir: Path) -> dict[str, Any]:
        nodes = accepted_work_map_nodes(load_work_map_nodes(work_map_dir))
        register_work_map_nodes(self.catalog_path, nodes)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-work-maps",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "work_map_dir": str(work_map_dir),
                "synced_count": len(nodes),
            },
        }

    def sync_division_metadata_payload(self, division_metadata_dir: Path) -> dict[str, Any]:
        rows = accepted_division_metadata(load_division_metadata(division_metadata_dir))
        register_division_metadata(self.catalog_path, rows)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-division-metadata",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "division_metadata_dir": str(division_metadata_dir),
                "synced_count": len(rows),
            },
        }

    def sync_classifications_payload(
        self,
        classification_csv: Path,
        *,
        merge: bool = False,
    ) -> dict[str, Any]:
        classifications = load_work_classifications(classification_csv)
        register_work_classifications(self.catalog_path, classifications, merge=merge)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-classifications",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "classification_csv": str(classification_csv),
                "synced_count": len(classifications),
                "metadata_status": "generated",
                "sync_mode": "merge" if merge else "replace",
            },
        }

    def sync_author_classifications_payload(
        self,
        classification_csv: Path,
        *,
        merge: bool = False,
    ) -> dict[str, Any]:
        classifications = load_author_classifications(classification_csv)
        register_author_classifications(self.catalog_path, classifications, merge=merge)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-author-classifications",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "classification_csv": str(classification_csv),
                "synced_count": len(classifications),
                "metadata_status": "generated",
                "sync_mode": "merge" if merge else "replace",
            },
        }

    def sync_metadata_overlays_payload(
        self,
        metadata_overlay_dir: Path,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        overlays = load_metadata_overlays(metadata_overlay_dir)
        register_metadata_overlays(self.catalog_path, overlays)
        summary = apply_metadata_overlays_to_catalog(
            self.catalog_path,
            overlays,
            dry_run=dry_run,
        )
        summary["metadata_overlay_dir"] = str(metadata_overlay_dir)
        summary["synced_count"] = len(overlays)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-metadata-overlays",
            "catalog_path": str(self.catalog_path),
            "summary": summary,
        }

    def sync_metadata_attributions_payload(
        self,
        metadata_attribution_dir: Path,
    ) -> dict[str, Any]:
        attributions = load_metadata_attributions(metadata_attribution_dir)
        register_metadata_attributions(self.catalog_path, attributions)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-metadata-attributions",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "metadata_attribution_dir": str(metadata_attribution_dir),
                "synced_count": len(attributions),
            },
        }

    def repair_languages_payload(self, *, dry_run: bool = False) -> dict[str, Any]:
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "repair-languages",
            "catalog_path": str(self.catalog_path),
            "summary": repair_work_languages(self.catalog_path, dry_run=dry_run),
        }

    def prune_stale_classifications_payload(self, *, dry_run: bool = False) -> dict[str, Any]:
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "prune-stale-classifications",
            "catalog_path": str(self.catalog_path),
            "summary": prune_stale_work_classifications(self.catalog_path, dry_run=dry_run),
        }

    def sync_source_enrichment_payload(  # noqa: PLR0913
        self,
        *,
        dcs_corpus_table: Path | None = None,
        dcs_chapter_info: Path | None = None,
        perseus_catalog_results: tuple[Path, ...] = (),
        perseus_collection_id: str = "perseus",
        perseus_subject: str = "",
        perseus_source_url: str = "",
    ) -> dict[str, Any]:
        dcs_chapter_metadata_count = 0
        dcs_corpus_summary: dict[str, Any] | None = None
        candidate_work_map_nodes = []
        perseus_metadata_count = 0
        if dcs_chapter_info is not None:
            dcs_chapter_info_text = dcs_chapter_info.read_text(encoding="utf-8")
            rows = parse_dcs_chapter_info_metadata(
                dcs_chapter_info_text,
                source_path=dcs_chapter_info,
            )
            register_source_metadata(self.catalog_path, rows)
            dcs_chapter_metadata_count = len(rows)
            candidate_work_map_nodes = dcs_chapter_info_work_map_candidates(
                self.catalog_path,
                dcs_chapter_info_text,
                source_path=dcs_chapter_info,
            )
        if dcs_corpus_table is not None:
            dcs_corpus_summary = sync_dcs_corpus_metadata(
                self.catalog_path,
                dcs_corpus_table.read_text(encoding="utf-8"),
                source_path=dcs_corpus_table,
            )
        if perseus_catalog_results:
            for path in perseus_catalog_results:
                rows = parse_perseus_catalog_results(
                    path.read_text(encoding="utf-8"),
                    collection_id=perseus_collection_id,
                    subject=perseus_subject,
                    source_url=perseus_source_url or str(path),
                    source_path=path,
                )
                register_source_metadata(self.catalog_path, rows)
                perseus_metadata_count += len(rows)
        candidate_overlays = perseus_candidate_metadata_overlays(self.catalog_path)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-source-enrichment",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "dcs_chapter_metadata_count": dcs_chapter_metadata_count,
                "dcs_corpus": dcs_corpus_summary,
                "candidate_work_map_node_count": len(candidate_work_map_nodes),
                "perseus_metadata_count": perseus_metadata_count,
                "perseus_catalog_result_count": len(perseus_catalog_results),
                "candidate_metadata_overlay_count": len(candidate_overlays),
                "metadata_status": "source-backed",
            },
            "candidate_work_map_nodes": [
                _work_map_node_payload(node) for node in candidate_work_map_nodes
            ],
            "candidate_metadata_overlays": [
                _metadata_overlay_payload(overlay) for overlay in candidate_overlays
            ],
        }

    def resolve_address(self, address: str) -> dict[str, Any]:  # noqa: C901, PLR0912
        resolved_address = address
        segment = None
        segments: list[dict[str, Any]] = []
        structure_node: dict[str, Any] | None = None
        current_divisions: list[dict[str, Any]] = []
        resolution_kind = "not_found"
        address_text = address.strip()
        spaced_reference = " " in address_text
        split_work_ref: str | None = None
        split_citation_path: str | None = None
        if spaced_reference:
            work_ref, citation_path = self._split_reference(address.strip())
            citation_path = _normalize_citation_path(citation_path)
            split_work_ref = work_ref
            split_citation_path = citation_path
            work_id = resolve_work_ref(self.catalog_path, work_ref)
            if work_id and citation_path:
                resolved_address = f"{work_id}:{citation_path.strip()}"
                segment = lookup_segment_by_address(self.catalog_path, resolved_address)
                if segment is not None:
                    resolution_kind = "segment"
            else:
                segments = lookup_segments_by_citation_reference(self.catalog_path, address)
                if segments:
                    segment = segments[0]
                    resolution_kind = "citation_reference"
        if (
            segment is None
            and not segments
            and resolved_address == address
            and not spaced_reference
        ):
            segment = lookup_segment_by_address(self.catalog_path, address)
            if segment is not None:
                resolution_kind = "segment"
        if segment is not None:
            if not segments:
                segments = [segment]
        else:
            segments = lookup_segments_by_citation_reference(self.catalog_path, address)
            if segments:
                segment = segments[0]
                resolution_kind = "citation_reference"
        if segment is None:
            structure_node = resolve_structure_reference(
                self.catalog_path,
                address,
                work_ref=split_work_ref,
                citation_ref=split_citation_path,
            )
            if structure_node is not None:
                resolved_address = f"{structure_node['work_id']}:{structure_node['start_citation']}"
                segment = lookup_segment_by_work_and_citation(
                    self.catalog_path,
                    str(structure_node["work_id"]),
                    str(structure_node["start_citation"]),
                )
                if segment is not None:
                    segments = [segment]
                    current_divisions = current_divisions_for_segment(
                        self.catalog_path,
                        str(segment["work_id"]),
                        str(segment["citation_path"]),
                    )
                    resolution_kind = "structure"
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "resolve-address",
            "catalog_path": str(self.catalog_path),
            "address": address,
            "resolved_address": resolved_address,
            "resolution_status": "resolved" if segment is not None else "not_found",
            "resolution_kind": resolution_kind,
            "segment": segment,
            "segments": segments,
            "structure_node": structure_node,
            "current_divisions": current_divisions,
        }

    def _split_reference(self, address: str) -> tuple[str, str]:
        parts = address.strip().split()
        for prefix_size in range(len(parts) - 1, 0, -1):
            work_ref = " ".join(parts[:prefix_size])
            if resolve_work_ref(self.catalog_path, work_ref):
                return work_ref, " ".join(parts[prefix_size:])
        work_ref, _sep, citation_path = address.partition(" ")
        return work_ref, citation_path

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "summary",
            "catalog_path": str(self.catalog_path),
            "summary": reader_summary(self.catalog_path),
        }

    def aliases(self) -> dict[str, Any]:
        return self._payload("aliases", list_aliases(self.catalog_path))

    def source_index(  # noqa: PLR0913
        self,
        *,
        collection_id: str | None = None,
        language: str | None = None,
        source_id: str | None = None,
        work_id: str | None = None,
        query: str | None = None,
        limit: int = 500,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        offset = _cursor_offset(cursor)
        fetch_limit = limit + 1
        items = list_source_index(
            self.catalog_path,
            collection_id=collection_id,
            language=language,
            source_id=source_id,
            work_id=work_id,
            query=query,
            limit=fetch_limit,
            offset=offset,
        )
        has_more = len(items) > limit
        items = items[:limit]
        return self._payload(
            "source-index",
            items,
            collection_id=collection_id,
            language=language,
            source_id=source_id,
            work_id=work_id,
            query=query,
            limit=limit,
            cursor=cursor,
            pagination=_pagination(
                limit=limit,
                offset=offset,
                has_more=has_more,
                next_offset=offset + len(items),
            ),
        )

    def source_index_export(self, output_dir: Path) -> dict[str, Any]:
        rows = list_source_index(self.catalog_path, limit=10_000_000)
        output_dir.mkdir(parents=True, exist_ok=True)

        files: list[dict[str, Any]] = []
        all_path = output_dir / "all_collections.tsv"
        _write_source_index_tsv(all_path, rows)
        files.append({"path": str(all_path), "row_count": len(rows), "kind": "all_collections"})

        collection_rows: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            collection_id = str(row.get("collection_id") or "unknown")
            collection_rows.setdefault(collection_id, []).append(row)

        for collection_id in sorted(collection_rows):
            collection_path = output_dir / f"{_safe_source_index_filename(collection_id)}.tsv"
            _write_source_index_tsv(collection_path, collection_rows[collection_id])
            files.append(
                {
                    "path": str(collection_path),
                    "row_count": len(collection_rows[collection_id]),
                    "kind": "collection",
                    "collection_id": collection_id,
                }
            )

        duplicate_rows = _source_index_duplicate_rows(rows)
        duplicate_path = output_dir / "duplicate_canonical_text_ids.tsv"
        _write_dict_tsv(
            duplicate_path,
            duplicate_rows,
            (
                "canonical_text_id",
                "work_count",
                "collections",
                "authors",
                "titles",
                "work_ids",
            ),
        )
        files.append(
            {
                "path": str(duplicate_path),
                "row_count": len(duplicate_rows),
                "kind": "duplicate_canonical_text_ids",
            }
        )

        readme_path = output_dir / "README.md"
        readme_path.write_text(
            _source_index_readme(collection_rows, output_dir=output_dir),
            encoding="utf-8",
        )
        files.append({"path": str(readme_path), "row_count": 0, "kind": "readme"})

        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "source-index-export",
            "catalog_path": str(self.catalog_path),
            "request": {"output_dir": str(output_dir)},
            "summary": {
                "row_count": len(rows),
                "collection_count": len(collection_rows),
                "duplicate_canonical_text_id_count": len(duplicate_rows),
            },
            "items": files,
        }

    def alias_conflicts(self) -> dict[str, Any]:
        return self._payload("alias-check", list_alias_conflicts(self.catalog_path))

    def overlays(
        self,
        *,
        collection_id: str | None = None,
        status: str | None = None,
        field: str | None = None,
        match_value: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        return self._payload(
            "overlays",
            list_metadata_overlays(
                self.catalog_path,
                collection_id=collection_id,
                status=status,
                field=field,
                match_value=match_value,
                limit=limit,
            ),
            collection_id=collection_id,
            status=status,
            field=field,
            match_value=match_value,
            limit=limit,
        )

    def attributions(  # noqa: PLR0913
        self,
        *,
        collection_id: str | None = None,
        status: str | None = None,
        relation_type: str | None = None,
        agent: str | None = None,
        match_value: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        return self._payload(
            "attributions",
            list_metadata_attributions(
                self.catalog_path,
                collection_id=collection_id,
                status=status,
                relation_type=relation_type,
                agent=agent,
                match_value=match_value,
                limit=limit,
            ),
            collection_id=collection_id,
            status=status,
            relation_type=relation_type,
            agent=agent,
            match_value=match_value,
            limit=limit,
        )

    def sources(
        self,
        *,
        collection_id: str | None = None,
        file_status: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        return self._payload(
            "sources",
            list_source_files(
                self.catalog_path,
                collection_id=collection_id,
                file_status=file_status,
                limit=limit,
            ),
            collection_id=collection_id,
            file_status=file_status,
            limit=limit,
        )

    def metadata(
        self,
        *,
        collection_id: str | None = None,
        subject_kind: str | None = None,
        subject_id: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        return self._payload(
            "metadata",
            list_source_metadata(
                self.catalog_path,
                collection_id=collection_id,
                subject_kind=subject_kind,
                subject_id=subject_id,
                limit=limit,
            ),
            collection_id=collection_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            limit=limit,
        )

    def validate(self) -> dict[str, Any]:
        return self._payload("validate", validate_reader_catalog(self.catalog_path))

    def _payload(self, mode: str, items: list[dict[str, Any]], **request: object) -> dict[str, Any]:
        pagination = request.pop("pagination", None)
        window = request.pop("window", None)
        payload: dict[str, Any] = {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": mode,
            "catalog_path": str(self.catalog_path),
            "request": {key: value for key, value in request.items() if value is not None},
            "items": items,
        }
        if pagination is not None:
            payload["pagination"] = pagination
        if window is not None:
            payload["window"] = window
        return payload


def _metadata_overlay_payload(overlay: ReaderMetadataOverlay) -> dict[str, Any]:
    return {
        "collection_id": overlay.collection_id,
        "match_field": overlay.match_field,
        "match_value": overlay.match_value,
        "field": overlay.field,
        "value": overlay.value,
        "status": overlay.status,
        "confidence": overlay.confidence,
        "note": overlay.note,
        "source_file": overlay.source_file,
        "evidence": [
            {
                "source_type": evidence.source_type,
                "citation": evidence.citation,
                "label": evidence.label,
                "retrieved_at": evidence.retrieved_at,
            }
            for evidence in overlay.evidence
        ],
    }


def _work_map_node_payload(node: ReaderWorkMapNode) -> dict[str, Any]:
    return {
        "work_id": node.work_id,
        "node_id": node.node_id,
        "parent_node_id": node.parent_node_id,
        "level": node.level,
        "kind": node.kind,
        "label": node.label,
        "native_label": node.native_label,
        "ordinal": node.ordinal,
        "start_citation": node.start_citation,
        "end_citation": node.end_citation,
        "provenance": node.provenance,
        "confidence": node.confidence,
        "status": node.status,
        "note": node.note,
        "source_file": node.source_file,
        "evidence": [
            {
                "source_type": evidence.source_type,
                "citation": evidence.citation,
                "label": evidence.label,
                "retrieved_at": evidence.retrieved_at,
            }
            for evidence in node.evidence
        ],
    }


def _find_author_detail_item(
    items: list[dict[str, Any]],
    author_ref: str,
) -> dict[str, Any] | None:
    needle = author_ref.strip().casefold()
    if not needle:
        return None
    for item in items:
        values = (
            item.get("author_id"),
            item.get("source_author_id"),
            item.get("canonical_author_id"),
            item.get("display_name"),
            item.get("source_author_name"),
            item.get("canonical_author_name"),
        )
        if any(needle == str(value or "").casefold() for value in values):
            return item
    for item in items:
        names = (
            item.get("display_name"),
            item.get("source_author_name"),
            item.get("canonical_author_name"),
        )
        if any(needle in str(value or "").casefold() for value in names):
            return item
    return None


def _normalize_citation_path(citation_path: str) -> str:
    citation = citation_path.strip().strip(",;:")
    if not citation:
        return citation
    compact = re.sub(r"\s+", "", citation)
    if _DOTTED_CITATION_RE.fullmatch(compact):
        return compact
    unlabeled = _CITATION_LABEL_RE.sub(" ", citation)
    parts = _CITATION_PART_RE.findall(unlabeled)
    if len(parts) >= MIN_CITATION_PARTS:
        return ".".join(_normalize_citation_part(part) for part in parts)
    return citation


def _normalize_citation_part(part: str) -> str:
    value = part.strip()
    if _ROMAN_CITATION_RE.fullmatch(value):
        return str(_roman_citation_to_int(value))
    return value


def _roman_citation_to_int(value: str) -> int:
    total = 0
    previous = 0
    for char in reversed(value.casefold()):
        current = _ROMAN_CITATION_VALUES[char]
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return total


def _cursor_offset(cursor: str | None) -> int:
    if cursor is None or cursor == "":
        return 0
    try:
        return max(0, int(cursor))
    except ValueError:
        return 0


def _word_context_lexical_evidence(
    *,
    query: str,
    language: str,
    candidates: list[str],
    fallback: dict[str, Any],
    lexical_evidence_provider: Callable[..., dict[str, Any]] | None,
) -> tuple[dict[str, Any], list[str]]:
    if lexical_evidence_provider is None:
        return fallback, []
    try:
        return (
            lexical_evidence_provider(
                query=query,
                language=language,
                candidates=candidates,
            ),
            [],
        )
    except Exception as exc:  # noqa: BLE001
        return (
            {
                "status": "error",
                "items": [],
                "note": f"Lexical evidence lookup failed: {exc}",
            },
            ["Lexical evidence lookup failed."],
        )


def _word_context_morphology(
    *,
    query: str,
    language: str,
    candidates: list[str],
    fallback: dict[str, Any],
    morphology_provider: Callable[..., dict[str, Any]] | None,
) -> tuple[dict[str, Any], list[str]]:
    if morphology_provider is None:
        return _word_context_cached_morphology(fallback), []
    try:
        return (
            morphology_provider(
                query=query,
                language=language,
                candidates=candidates,
            ),
            [],
        )
    except Exception as exc:  # noqa: BLE001
        return (
            {
                "status": "error",
                "items": [],
                "note": f"Morphology lookup failed: {exc}",
            },
            ["Morphology lookup failed."],
        )


def _word_context_cached_morphology(fallback: dict[str, Any]) -> dict[str, Any]:
    items = list(fallback.get("items") or [])
    return {
        "status": fallback.get("status", "unavailable"),
        "items": items,
        "note": (
            "Cached normalizer lemma candidates are available; full morphology "
            "features still require the heavier lookup/paradigm path."
            if items
            else fallback.get("note", "")
        ),
    }


def _cached_normalization_evidence(query: str, language: str) -> dict[str, Any]:
    language_hint = _reader_language_hint(language)
    if language_hint is None:
        return {
            "status": "unavailable",
            "items": [],
            "note": f"Unsupported normalization language for word context: {language}",
        }
    db_path = normalization_db_path()
    if not db_path.exists():
        return {
            "status": "unavailable",
            "items": [],
            "note": f"Normalization cache is unavailable: {db_path}",
        }
    try:
        with duckdb.connect(str(db_path), read_only=True) as conn:
            table_exists = conn.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'query_normalization_index'
                """
            ).fetchone()
            if not table_exists or int(table_exists[0]) == 0:
                return {
                    "status": "unavailable",
                    "items": [],
                    "note": "Normalization cache table is unavailable.",
                }
            normalized = NormalizationIndex(conn).get(_hash_query(query, language_hint))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "items": [],
            "note": f"Normalization cache lookup failed: {exc}",
        }
    if normalized is None:
        return {
            "status": "unavailable",
            "items": [],
            "note": "No cached lexical or morphology candidates for this form.",
        }
    items = [
        {
            "lemma": candidate.lemma,
            "sources": list(candidate.sources),
            "encodings": dict(candidate.encodings),
        }
        for candidate in normalized.candidates
        if candidate.lemma
    ]
    return {
        "status": "available" if items else "no_hits",
        "items": items,
        "note": "Cache-only normalizer candidates; no external lookup was performed.",
    }


def _reader_language_hint(language: str) -> LanguageHint.ValueType | None:
    normalized = language.strip().lower()
    if normalized == "lat":
        return LanguageHint.LANGUAGE_HINT_LAT
    if normalized == "grc":
        return LanguageHint.LANGUAGE_HINT_GRC
    if normalized in {"san", "skt"}:
        return LanguageHint.LANGUAGE_HINT_SAN
    return None


def _pagination(
    *,
    limit: int | None,
    offset: int,
    has_more: bool,
    next_offset: int | None = None,
) -> dict[str, Any] | None:
    if limit is None:
        return None
    previous_offset = max(0, offset - limit)
    return {
        "next_cursor": str(next_offset if next_offset is not None else offset + limit)
        if has_more
        else None,
        "prev_cursor": str(previous_offset) if offset > 0 else None,
        "limit": limit,
    }


def _budget_reader_segments(
    items: list[dict[str, Any]],
    *,
    char_budget: int | None,
    anchor: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    count_limit = limit if limit is not None and limit > 0 else len(items)
    if not items or not char_budget or char_budget <= 0:
        return items[:count_limit]
    if anchor:
        return _budget_reader_segments_around_anchor(
            items,
            char_budget=char_budget,
            anchor=anchor,
            limit=count_limit,
        )

    budgeted: list[dict[str, Any]] = []
    total_chars = 0
    for item in items:
        item_chars = _segment_reader_text_length(item)
        if budgeted and (len(budgeted) >= count_limit or total_chars + item_chars > char_budget):
            break
        budgeted.append(item)
        total_chars += item_chars
        if len(budgeted) >= count_limit:
            break
    return budgeted or items[:1]


def _budget_reader_segments_around_anchor(
    items: list[dict[str, Any]],
    *,
    char_budget: int,
    anchor: str,
    limit: int,
) -> list[dict[str, Any]]:
    anchor_index = next(
        (
            index
            for index, item in enumerate(items)
            if str(item.get("citation_path") or "") == anchor
        ),
        0,
    )
    selected = {anchor_index}
    total_chars = _segment_reader_text_length(items[anchor_index])
    before_index = anchor_index - 1
    after_index = anchor_index + 1
    before_open = before_index >= 0
    after_open = after_index < len(items)

    while len(selected) < limit and (before_open or after_open):
        changed = False
        if before_open:
            item_chars = _segment_reader_text_length(items[before_index])
            if total_chars + item_chars <= char_budget:
                selected.add(before_index)
                total_chars += item_chars
                changed = True
                before_index -= 1
                before_open = before_index >= 0
            else:
                before_open = False
        if len(selected) >= limit:
            break
        if after_open:
            item_chars = _segment_reader_text_length(items[after_index])
            if total_chars + item_chars <= char_budget:
                selected.add(after_index)
                total_chars += item_chars
                changed = True
                after_index += 1
                after_open = after_index < len(items)
            else:
                after_open = False
        if not changed and not before_open and not after_open:
            break

    return [items[index] for index in sorted(selected)]


def _segment_reader_text_length(item: dict[str, Any]) -> int:
    display = item.get("display")
    if isinstance(display, dict):
        primary = display.get("primary") or display.get("native_script")
        if primary:
            return len(str(primary))
    return len(str(item.get("text") or ""))


def _dominant_structure_kind(items: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in items:
        kind = str(item.get("kind") or "division")
        counts[kind] = counts.get(kind, 0) + 1
    if not counts:
        return "division"
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]


def _structure_count_label(count: int, kind: str) -> str:
    label = kind or "division"
    if count != 1:
        label = f"{label}s"
    return f"{count} {label}"


def _merge_provenance_chips(items: list[dict[str, Any]]) -> list[str]:
    chips: list[str] = []
    for item in items:
        for chip in item.get("provenance_chips") or []:
            chip_text = str(chip)
            if chip_text and chip_text not in chips:
                chips.append(chip_text)
    return chips


def _decorate_segment(catalog_path: Path, segment: dict[str, Any] | None) -> dict[str, Any] | None:
    if segment is None:
        return None
    work = get_work(catalog_path, str(segment.get("work_id") or ""))
    return decorate_segment_display(segment, language=_work_language(work))


def _work_language(work: dict[str, Any] | None) -> str | None:
    if not work:
        return None
    language = work.get("language")
    return str(language) if language else None


def _write_source_index_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_dict_tsv(path, rows, SOURCE_INDEX_EXPORT_COLUMNS)


def _write_dict_tsv(
    path: Path,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _tsv_value(row.get(column)) for column in columns})


def _tsv_value(value: Any) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _safe_source_index_filename(collection_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", collection_id.strip())
    return safe or "unknown"


def _source_index_duplicate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        canonical = str(row.get("canonical_text_id") or "").strip()
        if canonical:
            grouped.setdefault(canonical, []).append(row)

    duplicates: list[dict[str, Any]] = []
    for canonical, canonical_rows in grouped.items():
        work_ids = sorted({str(row.get("work_id") or "") for row in canonical_rows})
        if len(work_ids) <= 1:
            continue
        duplicates.append(
            {
                "canonical_text_id": canonical,
                "work_count": len(work_ids),
                "collections": ", ".join(
                    sorted({str(row.get("collection_id") or "") for row in canonical_rows})
                ),
                "authors": " | ".join(
                    sorted({str(row.get("author") or "") for row in canonical_rows})
                ),
                "titles": " | ".join(
                    sorted({str(row.get("title") or "") for row in canonical_rows})
                ),
                "work_ids": " | ".join(work_ids),
            }
        )
    return sorted(duplicates, key=lambda row: str(row["canonical_text_id"]))


def _source_index_readme(
    collection_rows: dict[str, list[dict[str, Any]]],
    *,
    output_dir: Path,
) -> str:
    lines = [
        "# Reader Source Index Flat Files",
        "",
        "Generated from `data/build/reader/catalog.duckdb`. These files are flat, "
        "grep-friendly snapshots of imported reader works by source collection.",
        "",
        "## Files",
        "",
        "- `all_collections.tsv`: every imported work/edition/artifact provenance row.",
        "- `<collection_id>.tsv`: the same rows split by source collection.",
        "- `duplicate_canonical_text_ids.tsv`: canonical text ids currently attached "
        "to more than one visible work.",
        "",
        "## Collection summary",
        "",
        "| Collection | Works | Editions | Segments | Words | File |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for collection_id in sorted(collection_rows):
        rows = collection_rows[collection_id]
        works = len({str(row.get("work_id") or "") for row in rows})
        editions = len({str(row.get("edition_id") or "") for row in rows})
        segments = sum(int(row.get("segment_count") or 0) for row in rows)
        words = sum(int(row.get("token_count") or 0) for row in rows)
        filename = f"{_safe_source_index_filename(collection_id)}.tsv"
        lines.append(
            f"| `{collection_id}` | {works} | {editions} | {segments} | {words} | `{filename}` |"
        )
    lines.extend(
        [
            "",
            "## Columns",
            "",
            *[f"- `{column}`" for column in SOURCE_INDEX_EXPORT_COLUMNS],
            "",
            "## Regeneration",
            "",
            "```bash",
            f"just cli reader source-index-export --output-dir {output_dir} --output json",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"
