from __future__ import annotations

import ast
from pathlib import Path
from typing import NoReturn, cast

from langnet.reader.models import ReaderMetadataOverlay, ReaderMetadataOverlayEvidence

_REQUIRED_OVERLAY_KEYS = {
    "collection_id",
    "match_field",
    "match_value",
    "field",
    "value",
    "status",
    "confidence",
    "note",
    "evidence",
}
_SUPPORTED_OVERLAY_KEYS = _REQUIRED_OVERLAY_KEYS
_REQUIRED_EVIDENCE_KEYS = {"source_type", "citation", "label"}
_OPTIONAL_EVIDENCE_KEYS = {"retrieved_at"}
_SUPPORTED_EVIDENCE_KEYS = _REQUIRED_EVIDENCE_KEYS | _OPTIONAL_EVIDENCE_KEYS
_SUPPORTED_MATCH_FIELDS = {"source_id", "work_id", "cts_work_urn", "author_id"}
_SUPPORTED_FIELDS = {"author", "author_id", "title", "language", "cts_work_urn"}
_SUPPORTED_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}
_SUPPORTED_CONFIDENCE = {"high", "medium", "low"}


def load_metadata_overlays(root: Path) -> list[ReaderMetadataOverlay]:
    if not root.exists():
        return []

    overlays: list[ReaderMetadataOverlay] = []
    for path in sorted(root.rglob("*.yaml")):
        overlays.extend(_load_overlay_file(path))
    return overlays


def accepted_metadata_overlays(
    overlays: list[ReaderMetadataOverlay],
) -> list[ReaderMetadataOverlay]:
    return [overlay for overlay in overlays if overlay.status == "accepted"]


def _load_overlay_file(path: Path) -> list[ReaderMetadataOverlay]:  # noqa: C901, PLR0912
    current: dict[str, object] | None = None
    current_evidence: list[dict[str, str]] | None = None
    overlays: list[ReaderMetadataOverlay] = []
    saw_header = False

    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line:
            continue
        if line == "overlays:" and not saw_header:
            saw_header = True
            continue
        if not saw_header:
            _raise_unsupported(path, line_number)
        if line.startswith("  - collection_id: "):
            if current is not None:
                overlays.append(_overlay_from_record(path, current))
            current = {
                "collection_id": _parse_quoted_scalar(
                    path,
                    line_number,
                    line.removeprefix("  - collection_id: "),
                )
            }
            current_evidence = None
            continue
        if line == "    evidence:":
            if current is None:
                _raise_unsupported(path, line_number)
            current_evidence = []
            current["evidence"] = current_evidence
            continue
        if line.startswith("      - source_type: "):
            if current_evidence is None:
                _raise_unsupported(path, line_number)
            current_evidence.append(
                {
                    "source_type": _parse_quoted_scalar(
                        path,
                        line_number,
                        line.removeprefix("      - source_type: "),
                    )
                }
            )
            continue
        if line.startswith("        "):
            if current_evidence is None or not current_evidence:
                _raise_unsupported(path, line_number)
            key, value = _parse_evidence_key_value(
                path,
                line_number,
                line.removeprefix("        "),
            )
            current_evidence[-1][key] = value
            continue
        if line.startswith("    "):
            if current is None:
                _raise_unsupported(path, line_number)
            key, value = _parse_overlay_key_value(
                path,
                line_number,
                line.removeprefix("    "),
            )
            current[key] = value
            continue
        _raise_unsupported(path, line_number)

    if current is not None:
        overlays.append(_overlay_from_record(path, current))
    return overlays


def _parse_overlay_key_value(path: Path, line_number: int, body: str) -> tuple[str, str]:
    if ": " not in body:
        _raise_unsupported(path, line_number)
    key, value_text = body.split(": ", 1)
    if key not in _SUPPORTED_OVERLAY_KEYS - {"collection_id", "evidence"}:
        _raise_unsupported(path, line_number)
    return key, _parse_quoted_scalar(path, line_number, value_text)


def _parse_evidence_key_value(path: Path, line_number: int, body: str) -> tuple[str, str]:
    if ": " not in body:
        _raise_unsupported(path, line_number)
    key, value_text = body.split(": ", 1)
    if key not in _SUPPORTED_EVIDENCE_KEYS - {"source_type"}:
        _raise_unsupported(path, line_number)
    return key, _parse_quoted_scalar(path, line_number, value_text)


def _parse_quoted_scalar(path: Path, line_number: int, value_text: str) -> str:
    if not (value_text.startswith('"') and value_text.endswith('"')):
        _raise_unsupported(path, line_number)
    try:
        value = ast.literal_eval(value_text)
    except (SyntaxError, ValueError) as exc:
        msg = f"{path}:{line_number}: invalid quoted string"
        raise ValueError(msg) from exc
    if not isinstance(value, str):
        _raise_unsupported(path, line_number)
    return value


def _overlay_from_record(path: Path, record: dict[str, object]) -> ReaderMetadataOverlay:
    if "evidence" not in record:
        msg = f"{path}: overlay record requires at least one evidence item"
        raise ValueError(msg)
    missing = sorted(_REQUIRED_OVERLAY_KEYS - record.keys())
    if missing:
        msg = f"{path}: overlay record missing required keys: {', '.join(missing)}"
        raise ValueError(msg)

    evidence = _evidence_from_record(path, record)
    match_field = _record_str(path, record, "match_field")
    field = _record_str(path, record, "field")
    status = _record_str(path, record, "status")
    confidence = _record_str(path, record, "confidence")
    if match_field not in _SUPPORTED_MATCH_FIELDS:
        msg = f"{path}: unsupported match_field {match_field!r}"
        raise ValueError(msg)
    if field not in _SUPPORTED_FIELDS:
        msg = f"{path}: unsupported metadata overlay field {field!r}"
        raise ValueError(msg)
    if status not in _SUPPORTED_STATUSES:
        msg = f"{path}: unsupported metadata overlay status {status!r}"
        raise ValueError(msg)
    if confidence not in _SUPPORTED_CONFIDENCE:
        msg = f"{path}: unsupported metadata overlay confidence {confidence!r}"
        raise ValueError(msg)

    return ReaderMetadataOverlay(
        collection_id=_record_str(path, record, "collection_id"),
        match_field=match_field,
        match_value=_record_str(path, record, "match_value"),
        field=field,
        value=_record_str(path, record, "value"),
        status=status,
        confidence=confidence,
        note=_record_str(path, record, "note"),
        source_file=str(path),
        evidence=evidence,
    )


def _evidence_from_record(
    path: Path,
    record: dict[str, object],
) -> tuple[ReaderMetadataOverlayEvidence, ...]:
    raw_evidence = record["evidence"]
    if not isinstance(raw_evidence, list) or not raw_evidence:
        msg = f"{path}: overlay record requires at least one evidence item"
        raise ValueError(msg)

    evidence: list[ReaderMetadataOverlayEvidence] = []
    for raw_item in raw_evidence:
        if not isinstance(raw_item, dict):
            msg = f"{path}: overlay evidence item must be a mapping"
            raise ValueError(msg)
        item = cast(dict[str, str], raw_item)
        missing = sorted(_REQUIRED_EVIDENCE_KEYS - item.keys())
        if missing:
            msg = f"{path}: overlay evidence missing required keys: {', '.join(missing)}"
            raise ValueError(msg)
        evidence.append(
            ReaderMetadataOverlayEvidence(
                source_type=item["source_type"],
                citation=item["citation"],
                label=item["label"],
                retrieved_at=item.get("retrieved_at"),
            )
        )
    return tuple(evidence)


def _record_str(path: Path, record: dict[str, object], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: overlay record key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _raise_unsupported(path: Path, line_number: int) -> NoReturn:
    msg = f"{path}:{line_number}: unsupported metadata overlay YAML line"
    raise ValueError(msg)
