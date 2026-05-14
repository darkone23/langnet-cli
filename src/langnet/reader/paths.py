from __future__ import annotations

import re
from pathlib import Path

from langnet.databuild.paths import build_dir
from langnet.reader.models import ReaderBookPathParts

_SAFE_PART_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_part(value: str) -> str:
    cleaned = _SAFE_PART_RE.sub("_", value.strip())
    return cleaned.strip("._") or "unknown"


def reader_root(data_root: Path | None = None) -> Path:
    base = data_root / "build" if data_root is not None else build_dir()
    return base / "reader"


def reader_catalog_path(data_root: Path | None = None) -> Path:
    return reader_root(data_root) / "catalog.duckdb"


def reader_books_dir(data_root: Path | None = None) -> Path:
    return reader_root(data_root) / "books"


def reader_book_path(
    parts: ReaderBookPathParts,
    *,
    data_root: Path | None = None,
) -> Path:
    return (
        reader_books_dir(data_root)
        / _safe_part(parts.collection)
        / _safe_part(parts.namespace)
        / _safe_part(parts.author_id)
        / _safe_part(parts.work_id)
        / f"{_safe_part(parts.edition_id)}.duckdb"
    )
