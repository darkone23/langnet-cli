from __future__ import annotations

import ast
from pathlib import Path
from typing import NoReturn, cast

from langnet.reader.models import (
    ReaderMetadataAttribution,
    ReaderMetadataOverlayEvidence,
)

_REQUIRED_ATTRIBUTION_KEYS = {
    "collection_id",
    "match_field",
    "match_value",
    "relation_type",
    "agent",
    "status",
    "confidence",
    "note",
    "evidence",
}
_SUPPORTED_ATTRIBUTION_KEYS = _REQUIRED_ATTRIBUTION_KEYS
_REQUIRED_EVIDENCE_KEYS = {"source_type", "citation", "label"}
_OPTIONAL_EVIDENCE_KEYS = {"retrieved_at"}
_SUPPORTED_EVIDENCE_KEYS = _REQUIRED_EVIDENCE_KEYS | _OPTIONAL_EVIDENCE_KEYS
_SUPPORTED_MATCH_FIELDS = {"source_id", "work_id", "cts_work_urn", "author_id"}
_SUPPORTED_RELATION_TYPES = {
    "attributed_author",
    "possible_author",
    "traditional_author",
    "misattributed_author",
    "translator",
    "commentator",
    "editor",
    "redactor",
    "compiler",
}
_SUPPORTED_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}
_SUPPORTED_CONFIDENCE = {"high", "medium", "low"}


def load_metadata_attributions(root: Path) -> list[ReaderMetadataAttribution]:
    if not root.exists():
        return []

    attributions: list[ReaderMetadataAttribution] = []
    for path in sorted(root.rglob("*.yaml")):
        attributions.extend(_load_attribution_file(path))
    return attributions


def accepted_metadata_attributions(
    attributions: list[ReaderMetadataAttribution],
) -> list[ReaderMetadataAttribution]:
    return [attribution for attribution in attributions if attribution.status == "accepted"]


def _load_attribution_file(path: Path) -> list[ReaderMetadataAttribution]:  # noqa: C901, PLR0912
    current: dict[str, object] | None = None
    current_evidence: list[dict[str, str]] | None = None
    attributions: list[ReaderMetadataAttribution] = []
    saw_header = False

    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line:
            continue
        if line == "attributions:" and not saw_header:
            saw_header = True
            continue
        if not saw_header:
            _raise_unsupported(path, line_number)
        if line.startswith("  - collection_id: "):
            if current is not None:
                attributions.append(_attribution_from_record(path, current))
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
            key, value = _parse_attribution_key_value(
                path,
                line_number,
                line.removeprefix("    "),
            )
            current[key] = value
            continue
        _raise_unsupported(path, line_number)

    if current is not None:
        attributions.append(_attribution_from_record(path, current))
    return attributions


def _parse_attribution_key_value(
    path: Path,
    line_number: int,
    body: str,
) -> tuple[str, str]:
    if ": " not in body:
        _raise_unsupported(path, line_number)
    key, value_text = body.split(": ", 1)
    if key not in _SUPPORTED_ATTRIBUTION_KEYS - {"collection_id", "evidence"}:
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


def _attribution_from_record(
    path: Path,
    record: dict[str, object],
) -> ReaderMetadataAttribution:
    if "evidence" not in record:
        msg = f"{path}: attribution record requires at least one evidence item"
        raise ValueError(msg)
    missing = sorted(_REQUIRED_ATTRIBUTION_KEYS - record.keys())
    if missing:
        msg = f"{path}: attribution record missing required keys: {', '.join(missing)}"
        raise ValueError(msg)

    evidence = _evidence_from_record(path, record)
    match_field = _record_str(path, record, "match_field")
    relation_type = _record_str(path, record, "relation_type")
    status = _record_str(path, record, "status")
    confidence = _record_str(path, record, "confidence")
    if match_field not in _SUPPORTED_MATCH_FIELDS:
        msg = f"{path}: unsupported match_field {match_field!r}"
        raise ValueError(msg)
    if relation_type not in _SUPPORTED_RELATION_TYPES:
        msg = f"{path}: unsupported metadata attribution relation_type {relation_type!r}"
        raise ValueError(msg)
    if status not in _SUPPORTED_STATUSES:
        msg = f"{path}: unsupported metadata attribution status {status!r}"
        raise ValueError(msg)
    if confidence not in _SUPPORTED_CONFIDENCE:
        msg = f"{path}: unsupported metadata attribution confidence {confidence!r}"
        raise ValueError(msg)

    return ReaderMetadataAttribution(
        collection_id=_record_str(path, record, "collection_id"),
        match_field=match_field,
        match_value=_record_str(path, record, "match_value"),
        relation_type=relation_type,
        agent=_record_str(path, record, "agent"),
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
        msg = f"{path}: attribution record requires at least one evidence item"
        raise ValueError(msg)

    evidence: list[ReaderMetadataOverlayEvidence] = []
    for raw_item in raw_evidence:
        if not isinstance(raw_item, dict):
            msg = f"{path}: attribution evidence item must be a mapping"
            raise ValueError(msg)
        item = cast(dict[str, str], raw_item)
        missing = sorted(_REQUIRED_EVIDENCE_KEYS - item.keys())
        if missing:
            msg = f"{path}: attribution evidence missing required keys: {', '.join(missing)}"
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
        msg = f"{path}: attribution record key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _raise_unsupported(path: Path, line_number: int) -> NoReturn:
    msg = f"{path}:{line_number}: unsupported metadata attribution YAML line"
    raise ValueError(msg)
