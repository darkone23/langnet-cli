from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from langnet.reader.models import ReaderCitationMap, ReaderMetadataOverlayEvidence

_REQUIRED_KEYS = {
    "citation_map_id",
    "source_id",
    "work_id",
    "source_pattern",
    "machine_pattern",
    "projection_rule",
    "example_source_reference",
    "example_machine_citation",
    "status",
    "confidence",
    "note",
    "evidence",
}
_SUPPORTED_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}
_SUPPORTED_CONFIDENCE = {"high", "medium", "low"}
_REQUIRED_EVIDENCE_KEYS = {"source_type", "citation", "label"}


def load_citation_maps(root: Path) -> list[ReaderCitationMap]:
    if not root.exists():
        return []
    maps: list[ReaderCitationMap] = []
    for path in sorted(root.rglob("*.yaml")):
        maps.extend(_load_citation_map_file(path))
    return maps


def accepted_citation_maps(maps: list[ReaderCitationMap]) -> list[ReaderCitationMap]:
    return [citation_map for citation_map in maps if citation_map.status == "accepted"]


def _load_citation_map_file(path: Path) -> list[ReaderCitationMap]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        msg = f"{path}: citation map file must be a mapping"
        raise ValueError(msg)
    raw_maps = raw.get("citation_maps")
    if raw_maps is None:
        return []
    if not isinstance(raw_maps, list):
        msg = f"{path}: citation_maps must be a list"
        raise ValueError(msg)
    maps: list[ReaderCitationMap] = []
    for record in raw_maps:
        if not isinstance(record, dict):
            msg = f"{path}: citation map item must be a mapping"
            raise ValueError(msg)
        maps.append(_citation_map_from_record(path, cast(dict[str, Any], record)))
    return maps


def _citation_map_from_record(path: Path, record: dict[str, Any]) -> ReaderCitationMap:
    missing = sorted(_REQUIRED_KEYS - record.keys())
    if missing:
        if "evidence" in missing:
            msg = f"{path}: citation map requires at least one evidence item"
            raise ValueError(msg)
        msg = f"{path}: citation map missing required keys: {', '.join(missing)}"
        raise ValueError(msg)
    status = _record_str(path, record, "status")
    confidence = _record_str(path, record, "confidence")
    if status not in _SUPPORTED_STATUSES:
        msg = f"{path}: unsupported citation map status {status!r}"
        raise ValueError(msg)
    if confidence not in _SUPPORTED_CONFIDENCE:
        msg = f"{path}: unsupported citation map confidence {confidence!r}"
        raise ValueError(msg)
    evidence = _evidence_from_record(path, record)
    return ReaderCitationMap(
        citation_map_id=_record_str(path, record, "citation_map_id"),
        source_id=_record_str(path, record, "source_id"),
        work_id=_record_str(path, record, "work_id"),
        source_pattern=_record_str(path, record, "source_pattern"),
        machine_pattern=_record_str(path, record, "machine_pattern"),
        projection_rule=_record_str(path, record, "projection_rule"),
        example_source_reference=_record_str(path, record, "example_source_reference"),
        example_machine_citation=_record_str(path, record, "example_machine_citation"),
        status=status,
        confidence=confidence,
        note=_record_str(path, record, "note"),
        source_file=str(path),
        evidence=evidence,
    )


def _evidence_from_record(
    path: Path,
    record: dict[str, Any],
) -> tuple[ReaderMetadataOverlayEvidence, ...]:
    raw_evidence = record["evidence"]
    if not isinstance(raw_evidence, list) or not raw_evidence:
        msg = f"{path}: citation map requires at least one evidence item"
        raise ValueError(msg)
    evidence: list[ReaderMetadataOverlayEvidence] = []
    for raw_item in raw_evidence:
        if not isinstance(raw_item, dict):
            msg = f"{path}: citation map evidence item must be a mapping"
            raise ValueError(msg)
        item = cast(dict[str, Any], raw_item)
        missing = sorted(_REQUIRED_EVIDENCE_KEYS - item.keys())
        if missing:
            msg = f"{path}: citation map evidence missing required keys: {', '.join(missing)}"
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
        msg = f"{path}: citation map key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _evidence_str(path: Path, record: dict[str, Any], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: citation map evidence key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _optional_record_str(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    return value if isinstance(value, str) and value else None
