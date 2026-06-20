from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langnet.reader.storage import (
    get_work,
    list_segments_for_work,
    list_source_index,
    list_source_metadata,
    list_works,
)

BUNDLE_SCHEMA_VERSION = "langnet.catalog_export.bundle.v1"
WORK_SCHEMA_VERSION = "langnet.catalog_export.work.v1"
PROVENANCE_SCHEMA_VERSION = "langnet.catalog_export.provenance.v1"
SEGMENT_SCHEMA_VERSION = "langnet.catalog_export.segment.v1"
VALIDATION_SCHEMA_VERSION = "langnet.catalog_export.validation.v1"
DEFAULT_SEGMENT_LIMIT = 10_000_000
SEGMENT_EXPORT_CHUNK_SIZE = 10_000


@dataclass(frozen=True)
class _ExportBundleConfig:
    replace: bool
    mode: str
    filters: Mapping[str, str | None]


def export_work_bundle(
    catalog_path: Path,
    work_ref: str,
    output_path: Path,
    *,
    replace: bool = True,
) -> dict[str, Any]:
    work = get_work(catalog_path, work_ref)
    if work is None:
        raise ValueError(f"reader work not found: {work_ref}")
    return _export_bundle(
        catalog_path,
        [work],
        output_path,
        _ExportBundleConfig(
            replace=replace,
            mode="reader-export-work",
            filters={"work_ref": work_ref},
        ),
    )


def export_catalog_bundle(
    catalog_path: Path,
    output_path: Path,
    *,
    collection_id: str | None = None,
    language: str | None = None,
    replace: bool = True,
) -> dict[str, Any]:
    works = list_works(
        catalog_path,
        collection_id=collection_id,
        language=language,
        limit=DEFAULT_SEGMENT_LIMIT,
    )
    return _export_bundle(
        catalog_path,
        works,
        output_path,
        _ExportBundleConfig(
            replace=replace,
            mode="reader-export-bundle",
            filters={"collection_id": collection_id, "language": language},
        ),
    )


def validate_catalog_export(export_path: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    manifest_path = export_path / "manifest.json"
    manifest = _read_json(manifest_path, errors)
    if manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        errors.append(
            {
                "path": "manifest.json",
                "message": f"missing schema_version {BUNDLE_SCHEMA_VERSION}",
            }
        )
    checksums_path = export_path / "checksums" / "SHA256SUMS"
    expected_checksums = _read_checksums(checksums_path, errors)
    _validate_checksums(export_path, expected_checksums, errors)

    work_items = manifest.get("works")
    if not isinstance(work_items, list):
        errors.append({"path": "manifest.json", "message": "works must be a list"})
        work_items = []
    for work_item in work_items:
        if not isinstance(work_item, Mapping):
            errors.append({"path": "manifest.json", "message": "work entry must be an object"})
            continue
        work_key = str(work_item.get("work_key") or "")
        if not work_key:
            errors.append({"path": "manifest.json", "message": "work entry missing work_key"})
            continue
        _validate_work_export(export_path, work_key, errors, warnings)

    return {
        "mode": "reader-export-validate",
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "path": str(export_path),
        "ok": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def _export_bundle(
    catalog_path: Path,
    works: Iterable[Mapping[str, Any]],
    output_path: Path,
    config: _ExportBundleConfig,
) -> dict[str, Any]:
    output_path = output_path.expanduser()
    if output_path.exists():
        if not config.replace:
            raise FileExistsError(f"export path already exists: {output_path}")
        shutil.rmtree(output_path)
    (output_path / "works").mkdir(parents=True, exist_ok=True)
    (output_path / "indexes").mkdir(parents=True, exist_ok=True)
    (output_path / "checksums").mkdir(parents=True, exist_ok=True)

    exported_works: list[dict[str, Any]] = []
    total_segments = 0
    for work in sorted(works, key=lambda item: str(item.get("work_id") or "")):
        work_payload = _work_payload(work)
        work_key = _safe_export_key(str(work_payload["langnet_work_id"]))
        work_dir = output_path / "works" / work_key
        work_dir.mkdir(parents=True, exist_ok=True)
        provenance = _provenance_payload(catalog_path, work_payload)
        _write_json(work_dir / "work.json", work_payload)
        segment_count = _write_jsonl(
            work_dir / "segments.jsonl",
            _segment_payloads(
                work_payload,
                _iter_segments_for_work(catalog_path, str(work_payload["langnet_work_id"])),
            ),
        )
        _write_json(work_dir / "provenance.json", provenance)
        exported_works.append(
            {
                "work_key": work_key,
                "langnet_work_id": work_payload["langnet_work_id"],
                "canonical_text_id": work_payload["canonical_text_id"],
                "language": work_payload["language"],
                "title": work_payload["title"],
                "segment_count": segment_count,
                "paths": {
                    "work": f"works/{work_key}/work.json",
                    "segments": f"works/{work_key}/segments.jsonl",
                    "provenance": f"works/{work_key}/provenance.json",
                },
            }
        )
        total_segments += segment_count

    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "created_at": _export_timestamp(catalog_path),
        "catalog_path": str(catalog_path),
        "format": "directory",
        "filters": dict(config.filters),
        "work_count": len(exported_works),
        "segment_count": total_segments,
        "works": exported_works,
    }
    _write_json(output_path / "manifest.json", manifest)
    _write_json(
        output_path / "indexes" / "catalog-summary.json",
        {
            "schema_version": "langnet.catalog_export.catalog_summary.v1",
            "work_count": len(exported_works),
            "segment_count": total_segments,
            "works": exported_works,
        },
    )
    checksum_rows = _write_checksums(output_path)
    validation = validate_catalog_export(output_path)
    return {
        "mode": config.mode,
        "path": str(output_path),
        "summary": {
            "work_count": len(exported_works),
            "segment_count": total_segments,
            "checksum_count": len(checksum_rows),
            "validation_ok": validation["ok"],
        },
        "works": exported_works,
        "validation": validation,
    }


def _work_payload(work: Mapping[str, Any]) -> dict[str, Any]:
    work_id = str(work.get("work_id") or "")
    canonical_text_id = str(work.get("canonical_text_id") or work.get("cts_work_urn") or work_id)
    author = str(work.get("display_author") or work.get("author") or "")
    source_id = str(work.get("source_id") or "")
    cts_work_urn = work.get("cts_work_urn")
    return {
        "schema_version": WORK_SCHEMA_VERSION,
        "langnet_work_id": work_id,
        "canonical_text_id": canonical_text_id,
        "collection_id": str(work.get("collection_id") or ""),
        "language": str(work.get("language") or ""),
        "title": str(work.get("display_title") or work.get("title") or ""),
        "authors": [
            {
                "name": author,
                "role": "source_author",
                "authority_id": work.get("author_id"),
                "confidence": "source" if author else "unresolved",
            }
        ],
        "source_ids": {
            "source_id": source_id,
            "cts_work_urn": str(cts_work_urn) if cts_work_urn else None,
        },
        "canonical_address": canonical_text_id,
        "quality_flags": _quality_flags(work),
    }


def _segment_payloads(
    work: Mapping[str, Any],
    segments: Iterable[Mapping[str, Any]],
) -> Iterable[dict[str, Any]]:
    for segment in segments:
        yield {
            "schema_version": SEGMENT_SCHEMA_VERSION,
            "segment_id": segment.get("segment_id"),
            "langnet_work_id": work["langnet_work_id"],
            "canonical_address": segment.get("canonical_address"),
            "citation_path": segment.get("citation_path"),
            "sort_key": segment.get("sort_key"),
            "language": work["language"],
            "text": segment.get("text"),
            "normalized_text": segment.get("normalized_text"),
            "display_layers": {
                "source_text": bool(segment.get("source_text")),
                "translation": False,
                "commentary": False,
            },
            "source_ref": {
                "edition_id": segment.get("edition_id"),
                "segment_kind": segment.get("segment_kind"),
                "source_citation": segment.get("citation_path"),
            },
        }


def _iter_segments_for_work(
    catalog_path: Path,
    work_id: str,
) -> Iterable[Mapping[str, Any]]:
    offset = 0
    while True:
        rows = list_segments_for_work(
            catalog_path,
            work_id,
            limit=SEGMENT_EXPORT_CHUNK_SIZE,
            offset=offset,
        )
        if not rows:
            return
        yield from rows
        if len(rows) < SEGMENT_EXPORT_CHUNK_SIZE:
            return
        offset += len(rows)


def _provenance_payload(
    catalog_path: Path,
    work: Mapping[str, Any],
) -> dict[str, Any]:
    work_id = str(work["langnet_work_id"])
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "langnet_work_id": work_id,
        "source_index": list_source_index(
            catalog_path,
            work_id=work_id,
            limit=DEFAULT_SEGMENT_LIMIT,
        ),
        "source_metadata": list_source_metadata(
            catalog_path,
            subject_kind="work",
            subject_id=work_id,
            limit=DEFAULT_SEGMENT_LIMIT,
        ),
    }


def _quality_flags(work: Mapping[str, Any]) -> list[str]:
    flags: list[str] = []
    if str(work.get("canonical_text_id") or "").startswith("urn:ctsv2:"):
        return flags
    if not work.get("canonical_text_id"):
        flags.append("synthetic_source_identity")
    return flags


def _validate_work_export(
    export_path: Path,
    work_key: str,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    work_dir = export_path / "works" / work_key
    work = _read_json(work_dir / "work.json", errors)
    _validate_work_file(work, work_key, errors, warnings)
    _validate_segment_file(work_dir / "segments.jsonl", work_key, errors)
    _validate_provenance_file(work_dir / "provenance.json", work_key, errors)


def _validate_work_file(
    work: Mapping[str, Any],
    work_key: str,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    if work.get("schema_version") != WORK_SCHEMA_VERSION:
        errors.append(
            {"path": f"works/{work_key}/work.json", "message": "invalid work schema_version"}
        )
    for field in ("langnet_work_id", "canonical_text_id", "title", "language"):
        if not work.get(field):
            errors.append({"path": f"works/{work_key}/work.json", "message": f"missing {field}"})
    authors = work.get("authors")
    if not isinstance(authors, list) or not authors:
        errors.append({"path": f"works/{work_key}/work.json", "message": "missing authors"})
    elif str(authors[0].get("name") or "").casefold() == "unknown":
        warnings.append(
            {"path": f"works/{work_key}/work.json", "message": "display author is Unknown"}
        )
    if not str(work.get("canonical_text_id") or "").startswith("urn:ctsv2:"):
        warnings.append(
            {
                "path": f"works/{work_key}/work.json",
                "message": "canonical_text_id is not a CTSv2 address",
            }
        )


def _validate_segment_file(
    segment_path: Path,
    work_key: str,
    errors: list[dict[str, str]],
) -> None:
    segment_count = 0
    if not segment_path.exists():
        errors.append({"path": f"works/{work_key}/segments.jsonl", "message": "missing segments"})
        return
    with segment_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            segment_count += 1
            _validate_segment_line(line, work_key, line_number, errors)
    if segment_count == 0:
        errors.append(
            {"path": f"works/{work_key}/segments.jsonl", "message": "work has no segments"}
        )


def _validate_segment_line(
    line: str,
    work_key: str,
    line_number: int,
    errors: list[dict[str, str]],
) -> None:
    try:
        segment = json.loads(line)
    except json.JSONDecodeError as exc:
        errors.append(
            {
                "path": f"works/{work_key}/segments.jsonl:{line_number}",
                "message": str(exc),
            }
        )
        return
    for field in ("segment_id", "langnet_work_id", "citation_path", "sort_key"):
        if segment.get(field) in (None, ""):
            errors.append(
                {
                    "path": f"works/{work_key}/segments.jsonl:{line_number}",
                    "message": f"missing {field}",
                }
            )


def _validate_provenance_file(
    provenance_path: Path,
    work_key: str,
    errors: list[dict[str, str]],
) -> None:
    provenance = _read_json(provenance_path, errors)
    if provenance.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        errors.append(
            {
                "path": f"works/{work_key}/provenance.json",
                "message": "invalid provenance schema_version",
            }
        )
    if not provenance.get("source_index"):
        errors.append(
            {"path": f"works/{work_key}/provenance.json", "message": "missing source provenance"}
        )


def _validate_checksums(
    export_path: Path,
    expected_checksums: Mapping[str, str],
    errors: list[dict[str, str]],
) -> None:
    for relative_path, expected_hash in expected_checksums.items():
        path = export_path / relative_path
        if not path.exists():
            errors.append({"path": relative_path, "message": "checksummed file is missing"})
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            errors.append({"path": relative_path, "message": "checksum mismatch"})


def _read_checksums(path: Path, errors: list[dict[str, str]]) -> dict[str, str]:
    if not path.exists():
        errors.append({"path": "checksums/SHA256SUMS", "message": "missing checksums"})
        return {}
    rows: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            checksum, relative_path = line.split("  ", 1)
        except ValueError:
            errors.append(
                {
                    "path": f"checksums/SHA256SUMS:{line_number}",
                    "message": "invalid checksum row",
                }
            )
            continue
        rows[relative_path] = checksum
    return rows


def _write_checksums(output_path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for path in sorted(output_path.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        relative_path = path.relative_to(output_path).as_posix()
        rows.append((hashlib.sha256(path.read_bytes()).hexdigest(), relative_path))
    checksum_path = output_path / "checksums" / "SHA256SUMS"
    checksum_path.write_text(
        "".join(f"{digest}  {relative_path}\n" for digest, relative_path in rows),
        encoding="utf-8",
    )
    return rows


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    row_count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            row_count += 1
    return row_count


def _read_json(path: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    if not path.exists():
        errors.append({"path": str(path), "message": "missing JSON file"})
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append({"path": str(path), "message": str(exc)})
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _safe_export_key(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    safe = re.sub(r"-+", "-", safe).strip("-._")
    return safe or "work"


def _export_timestamp(catalog_path: Path) -> str:
    if catalog_path.exists():
        timestamp = datetime.fromtimestamp(catalog_path.stat().st_mtime, UTC)
        return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return (
        datetime.fromtimestamp(0, UTC)
        .isoformat(timespec="microseconds")
        .replace(
            "+00:00",
            "Z",
        )
    )
