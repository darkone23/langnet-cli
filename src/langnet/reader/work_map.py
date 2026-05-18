from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from langnet.reader.models import ReaderMetadataOverlayEvidence, ReaderWorkMapNode

_REQUIRED_KEYS = {
    "work_id",
    "node_id",
    "level",
    "kind",
    "label",
    "ordinal",
    "start_citation",
    "end_citation",
    "provenance",
    "confidence",
    "status",
    "note",
    "evidence",
}
_SUPPORTED_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}
_SUPPORTED_PROVENANCE = {"native", "curated", "inferred"}
_SUPPORTED_CONFIDENCE = {"high", "medium", "low"}
_REQUIRED_EVIDENCE_KEYS = {"source_type", "citation", "label"}


def load_work_map_nodes(root: Path) -> list[ReaderWorkMapNode]:
    if not root.exists():
        return []
    nodes: list[ReaderWorkMapNode] = []
    for path in sorted(root.rglob("*.yaml")):
        nodes.extend(_load_work_map_file(path))
    return nodes


def accepted_work_map_nodes(nodes: list[ReaderWorkMapNode]) -> list[ReaderWorkMapNode]:
    return [node for node in nodes if node.status == "accepted"]


def _load_work_map_file(path: Path) -> list[ReaderWorkMapNode]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        msg = f"{path}: work map file must be a mapping"
        raise ValueError(msg)
    raw_nodes = raw.get("work_maps")
    if raw_nodes is None:
        return []
    if not isinstance(raw_nodes, list):
        msg = f"{path}: work_maps must be a list"
        raise ValueError(msg)
    return [_node_from_record(path, cast(dict[str, Any], record)) for record in raw_nodes]


def _node_from_record(path: Path, record: dict[str, Any]) -> ReaderWorkMapNode:
    missing = sorted(_REQUIRED_KEYS - record.keys())
    if missing:
        if "evidence" in missing:
            msg = f"{path}: work map node requires at least one evidence item"
            raise ValueError(msg)
        msg = f"{path}: work map node missing required keys: {', '.join(missing)}"
        raise ValueError(msg)
    status = _record_str(path, record, "status")
    provenance = _record_str(path, record, "provenance")
    confidence = _record_str(path, record, "confidence")
    if status not in _SUPPORTED_STATUSES:
        msg = f"{path}: unsupported work map status {status!r}"
        raise ValueError(msg)
    if provenance not in _SUPPORTED_PROVENANCE:
        msg = f"{path}: unsupported work map provenance {provenance!r}"
        raise ValueError(msg)
    if confidence not in _SUPPORTED_CONFIDENCE:
        msg = f"{path}: unsupported work map confidence {confidence!r}"
        raise ValueError(msg)
    evidence = _evidence_from_record(path, record)
    return ReaderWorkMapNode(
        work_id=_record_str(path, record, "work_id"),
        node_id=_record_str(path, record, "node_id"),
        parent_node_id=_optional_record_str(record, "parent_node_id"),
        level=_record_int(path, record, "level"),
        kind=_record_str(path, record, "kind"),
        label=_record_str(path, record, "label"),
        native_label=_optional_record_str(record, "native_label"),
        ordinal=_record_int(path, record, "ordinal"),
        start_citation=_record_str(path, record, "start_citation"),
        end_citation=_record_str(path, record, "end_citation"),
        provenance=provenance,
        confidence=confidence,
        status=status,
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
        msg = f"{path}: work map node requires at least one evidence item"
        raise ValueError(msg)
    evidence: list[ReaderMetadataOverlayEvidence] = []
    for raw_item in raw_evidence:
        if not isinstance(raw_item, dict):
            msg = f"{path}: work map evidence item must be a mapping"
            raise ValueError(msg)
        item = cast(dict[str, Any], raw_item)
        missing = sorted(_REQUIRED_EVIDENCE_KEYS - item.keys())
        if missing:
            msg = f"{path}: work map evidence missing required keys: {', '.join(missing)}"
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
        msg = f"{path}: work map key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _evidence_str(path: Path, record: dict[str, Any], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: work map evidence key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _record_int(path: Path, record: dict[str, Any], key: str) -> int:
    value = record[key]
    if not isinstance(value, int):
        msg = f"{path}: work map key {key!r} must be an integer"
        raise ValueError(msg)
    return value


def _optional_record_str(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    return value if isinstance(value, str) and value else None
