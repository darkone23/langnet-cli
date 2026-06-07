from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

READER_LIBRARY_WATCHLIST_SCHEMA_VERSION = "langnet.reader.library_watchlist.v1"
DEFAULT_READER_LIBRARY_WATCHLIST_PATH = Path(
    "data/curated/reader_library_watchlist/high_value_targets.yaml"
)


def library_watchlist_payload(
    *,
    watchlist_path: Path = DEFAULT_READER_LIBRARY_WATCHLIST_PATH,
    query: str | None = None,
    language: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    items = load_library_watchlist_targets(watchlist_path)
    normalized_query = _normalize(query or "")
    normalized_language = _normalize(language or "")
    normalized_status = _normalize(status or "")
    if normalized_language:
        items = [
            item
            for item in items
            if normalized_language in {_normalize(value) for value in item.get("languages", [])}
        ]
    if normalized_status:
        items = [
            item for item in items if _normalize(str(item.get("status") or "")) == normalized_status
        ]
    if normalized_query:
        query_parts = normalized_query.split()
        items = [
            item
            for item in items
            if _target_matches_query(item, normalized_query=normalized_query, query_parts=query_parts)
        ]
    if limit is not None:
        items = items[:limit]
    return {
        "schema_version": READER_LIBRARY_WATCHLIST_SCHEMA_VERSION,
        "mode": "library-watchlist",
        "request": {
            "watchlist_path": str(watchlist_path),
            "query": query,
            "language": language,
            "status": status,
            "limit": limit,
        },
        "summary": {
            "target_count": len(items),
        },
        "items": items,
    }


def load_library_watchlist_targets(path: Path) -> list[dict[str, Any]]:
    source = path.expanduser()
    raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    targets = raw.get("targets") if isinstance(raw, dict) else []
    if not isinstance(targets, list):
        return []
    return [_normalize_target(target) for target in targets if isinstance(target, dict)]


def _normalize_target(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("id") or "").strip(),
        "display_name": str(raw.get("display_name") or "").strip(),
        "aliases": _string_list(raw.get("aliases")),
        "languages": _string_list(raw.get("languages")),
        "period": str(raw.get("period") or "").strip(),
        "tradition": str(raw.get("tradition") or "").strip(),
        "status": str(raw.get("status") or "").strip(),
        "source_plan": str(raw.get("source_plan") or "").strip(),
        "note": str(raw.get("note") or "").strip(),
        "evidence": raw.get("evidence") if isinstance(raw.get("evidence"), list) else [],
        "local_artifacts": _string_list(raw.get("local_artifacts")),
    }


def _target_matches_query(
    item: dict[str, Any],
    *,
    normalized_query: str,
    query_parts: list[str],
) -> bool:
    haystack = _normalize(
        " ".join(
            [
                str(item.get("id") or ""),
                str(item.get("display_name") or ""),
                " ".join(str(value) for value in item.get("aliases", [])),
                " ".join(str(value) for value in item.get("languages", [])),
                str(item.get("period") or ""),
                str(item.get("tradition") or ""),
                str(item.get("status") or ""),
                str(item.get("source_plan") or ""),
                str(item.get("note") or ""),
            ]
        )
    )
    return normalized_query in haystack or all(part in haystack for part in query_parts)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())
