from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langnet.reader.display import decorate_segment_display
from langnet.reader.storage import (
    get_work,
    list_alias_conflicts,
    list_aliases,
    list_author_index,
    list_author_sections,
    list_collections,
    list_duplicate_audit,
    list_metadata_attributions,
    list_metadata_overlays,
    list_segments_for_work,
    list_source_files,
    list_source_metadata,
    list_works,
    lookup_segment_by_address,
    lookup_segment_by_work_and_citation,
    reader_summary,
    resolve_work_ref,
    segment_navigation,
)
from langnet.reader.validation import validate_reader_catalog

READER_SCHEMA_VERSION = "langnet.reader.v1"
_DOTTED_CITATION_RE = re.compile(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+")
_CITATION_LABEL_RE = re.compile(r"\b(?:book|bk|line|ln|l)\.?\b", re.IGNORECASE)
_CITATION_PART_RE = re.compile(r"[0-9]+[A-Za-z]?")
MIN_CITATION_PARTS = 2


class ReaderService:
    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = catalog_path

    def collections_payload(self) -> dict[str, Any]:
        return self._payload("collections", list_collections(self.catalog_path))

    def collections(self) -> dict[str, Any]:
        return self.collections_payload()

    def authors_payload(
        self,
        *,
        language: str | None = None,
        section: str | None = None,
        query: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
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
            pagination=_pagination(limit=limit, offset=offset, has_more=has_more),
        )

    def author_sections_payload(self, *, language: str) -> dict[str, Any]:
        return self._payload(
            "author-sections",
            list_author_sections(self.catalog_path, language=language),
            language=language,
        )

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

    def authors(
        self,
        *,
        language: str | None = None,
        section: str | None = None,
        query: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self.authors_payload(
            language=language,
            section=section,
            query=query,
            limit=limit,
            cursor=cursor,
        )

    def works_payload(  # noqa: PLR0913
        self,
        *,
        language: str | None = None,
        collection_id: str | None = None,
        author: str | None = None,
        attributed_to: str | None = None,
        author_id: str | None = None,
        query: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
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
            query=query,
            limit=fetch_limit,
            offset=offset,
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
            query=query,
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
        query: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self.works_payload(
            language=language,
            collection_id=collection_id,
            author=author,
            attributed_to=attributed_to,
            author_id=author_id,
            query=query,
            limit=limit,
            cursor=cursor,
        )

    def contents_payload(  # noqa: PLR0913
        self,
        work_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        from_citation: str | None = None,
        around: str | None = None,
        radius: int = 20,
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
        has_more = around is None and len(items) > limit
        if around is None:
            items = items[:limit]
        work = get_work(self.catalog_path, work_id)
        language = _work_language(work)
        items = [decorate_segment_display(item, language=language) for item in items]
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
            pagination=_pagination(limit=limit, offset=offset, has_more=has_more),
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
            "navigation": segment_navigation(self.catalog_path, segment) if segment else None,
        }

    def work_payload(self, work_ref: str) -> dict[str, Any]:
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "work",
            "catalog_path": str(self.catalog_path),
            "work_ref": work_ref,
            "item": get_work(self.catalog_path, work_ref),
        }

    def resolve_address(self, address: str) -> dict[str, Any]:
        resolved_address = address
        segment = None
        if " " in address.strip():
            work_ref, citation_path = self._split_reference(address.strip())
            citation_path = _normalize_citation_path(citation_path)
            work_id = resolve_work_ref(self.catalog_path, work_ref)
            if work_id and citation_path:
                resolved_address = f"{work_id}:{citation_path.strip()}"
                segment = lookup_segment_by_address(self.catalog_path, resolved_address)
        if segment is None and resolved_address == address:
            segment = lookup_segment_by_address(self.catalog_path, address)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "resolve-address",
            "catalog_path": str(self.catalog_path),
            "address": address,
            "resolved_address": resolved_address,
            "segment": segment,
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
        return ".".join(parts)
    return citation


def _cursor_offset(cursor: str | None) -> int:
    if cursor is None or cursor == "":
        return 0
    try:
        return max(0, int(cursor))
    except ValueError:
        return 0


def _pagination(*, limit: int | None, offset: int, has_more: bool) -> dict[str, Any] | None:
    if limit is None:
        return None
    previous_offset = max(0, offset - limit)
    return {
        "next_cursor": str(offset + limit) if has_more else None,
        "prev_cursor": str(previous_offset) if offset > 0 else None,
        "limit": limit,
    }


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
