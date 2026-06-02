from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from langnet.reader.models import (
    ReaderDivisionMetadata,
    ReaderMetadataOverlayEvidence,
)

_REQUIRED_KEYS = {
    "work_id",
    "node_id",
    "summary",
    "short_label",
    "traditional_reference",
    "status",
    "confidence",
    "generator_model",
    "review_status",
    "note",
    "evidence",
}
_SUPPORTED_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}
_SUPPORTED_CONFIDENCE = {"high", "medium", "low"}
_SUPPORTED_REVIEW_STATUSES = {"reviewed", "llm_draft", "needs_review", "source_backed"}
_REQUIRED_EVIDENCE_KEYS = {"source_type", "citation", "label"}


def load_division_metadata(root: Path) -> list[ReaderDivisionMetadata]:
    if not root.exists():
        return []
    rows: list[ReaderDivisionMetadata] = []
    for path in sorted(root.rglob("*.yaml")):
        rows.extend(_load_division_metadata_file(path))
    return rows


def accepted_division_metadata(
    rows: list[ReaderDivisionMetadata],
) -> list[ReaderDivisionMetadata]:
    return [row for row in rows if row.status == "accepted"]


def _load_division_metadata_file(path: Path) -> list[ReaderDivisionMetadata]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        msg = f"{path}: division metadata file must be a mapping"
        raise ValueError(msg)
    raw_rows = raw.get("division_metadata")
    if raw_rows is None:
        return []
    if not isinstance(raw_rows, list):
        msg = f"{path}: division_metadata must be a list"
        raise ValueError(msg)
    rows: list[ReaderDivisionMetadata] = []
    for record in raw_rows:
        if not isinstance(record, dict):
            msg = f"{path}: division metadata item must be a mapping"
            raise ValueError(msg)
        rows.append(_row_from_record(path, cast(dict[str, Any], record)))
    return rows


def _row_from_record(path: Path, record: dict[str, Any]) -> ReaderDivisionMetadata:
    missing = sorted(_REQUIRED_KEYS - record.keys())
    if missing:
        if "evidence" in missing:
            msg = f"{path}: division metadata requires at least one evidence item"
            raise ValueError(msg)
        msg = f"{path}: division metadata missing required keys: {', '.join(missing)}"
        raise ValueError(msg)
    status = _record_str(path, record, "status")
    confidence = _record_str(path, record, "confidence")
    review_status = _record_str(path, record, "review_status")
    if status not in _SUPPORTED_STATUSES:
        msg = f"{path}: unsupported division metadata status {status!r}"
        raise ValueError(msg)
    if confidence not in _SUPPORTED_CONFIDENCE:
        msg = f"{path}: unsupported division metadata confidence {confidence!r}"
        raise ValueError(msg)
    if review_status not in _SUPPORTED_REVIEW_STATUSES:
        msg = f"{path}: unsupported division metadata review_status {review_status!r}"
        raise ValueError(msg)
    return ReaderDivisionMetadata(
        work_id=_record_str(path, record, "work_id"),
        node_id=_record_str(path, record, "node_id"),
        summary=_record_str(path, record, "summary"),
        short_label=_record_str(path, record, "short_label"),
        traditional_reference=_record_str(path, record, "traditional_reference"),
        status=status,
        confidence=confidence,
        generator_model=_record_str(path, record, "generator_model"),
        review_status=review_status,
        note=_record_str(path, record, "note"),
        source_file=str(path),
        evidence=_evidence_from_record(path, record),
    )


def _evidence_from_record(
    path: Path,
    record: dict[str, Any],
) -> tuple[ReaderMetadataOverlayEvidence, ...]:
    raw_evidence = record["evidence"]
    if not isinstance(raw_evidence, list) or not raw_evidence:
        msg = f"{path}: division metadata requires at least one evidence item"
        raise ValueError(msg)
    evidence: list[ReaderMetadataOverlayEvidence] = []
    for raw_item in raw_evidence:
        if not isinstance(raw_item, dict):
            msg = f"{path}: division metadata evidence item must be a mapping"
            raise ValueError(msg)
        item = cast(dict[str, Any], raw_item)
        missing = sorted(_REQUIRED_EVIDENCE_KEYS - item.keys())
        if missing:
            msg = f"{path}: division metadata evidence missing required keys: {', '.join(missing)}"
            raise ValueError(msg)
        evidence.append(
            ReaderMetadataOverlayEvidence(
                source_type=_evidence_str(path, item, "source_type"),
                citation=_evidence_str(path, item, "citation"),
                label=_evidence_str(path, item, "label"),
                retrieved_at=_optional_record_str(item, "retrieved_at"),
            )
        )
    return tuple(evidence)


def _record_str(path: Path, record: dict[str, Any], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: division metadata key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _evidence_str(path: Path, record: dict[str, Any], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: division metadata evidence key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _optional_record_str(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    return value if isinstance(value, str) and value else None
