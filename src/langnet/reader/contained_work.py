from __future__ import annotations

import ast
from pathlib import Path
from typing import cast

from langnet.reader.models import ReaderContainedWork, ReaderMetadataOverlayEvidence

_REQUIRED_KEYS = {
    "contained_work_id",
    "parent_work_id",
    "collection_id",
    "language",
    "title",
    "author",
    "source_id",
    "start_citation",
    "end_citation",
    "status",
    "confidence",
    "note",
    "evidence",
}
_OPTIONAL_KEYS = {"cts_work_urn"}
_SUPPORTED_KEYS = _REQUIRED_KEYS | _OPTIONAL_KEYS
_REQUIRED_EVIDENCE_KEYS = {"source_type", "citation", "label"}
_OPTIONAL_EVIDENCE_KEYS = {"retrieved_at"}
_SUPPORTED_EVIDENCE_KEYS = _REQUIRED_EVIDENCE_KEYS | _OPTIONAL_EVIDENCE_KEYS
_SUPPORTED_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}
_SUPPORTED_CONFIDENCE = {"high", "medium", "low"}


def load_contained_works(root: Path) -> list[ReaderContainedWork]:
    if not root.exists():
        return []
    works: list[ReaderContainedWork] = []
    for path in sorted(root.rglob("*.yaml")):
        works.extend(_load_contained_work_file(path))
    return works


def accepted_contained_works(works: list[ReaderContainedWork]) -> list[ReaderContainedWork]:
    return [work for work in works if work.status == "accepted"]


def _load_contained_work_file(path: Path) -> list[ReaderContainedWork]:  # noqa: C901, PLR0912
    current: dict[str, object] | None = None
    current_evidence: list[dict[str, str]] | None = None
    works: list[ReaderContainedWork] = []
    saw_header = False

    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line:
            continue
        if line == "contained_works:" and not saw_header:
            saw_header = True
            continue
        if not saw_header:
            _raise_unsupported(path, line_number)
        if line.startswith("  - contained_work_id: "):
            if current is not None:
                works.append(_contained_work_from_record(path, current))
            current = {
                "contained_work_id": _parse_quoted_scalar(
                    path,
                    line_number,
                    line.removeprefix("  - contained_work_id: "),
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
            key, value = _parse_key_value(path, line_number, line.removeprefix("    "))
            current[key] = value
            continue
        _raise_unsupported(path, line_number)

    if current is not None:
        works.append(_contained_work_from_record(path, current))
    return works


def _parse_key_value(path: Path, line_number: int, body: str) -> tuple[str, str]:
    if ": " not in body:
        _raise_unsupported(path, line_number)
    key, value_text = body.split(": ", 1)
    if key not in _SUPPORTED_KEYS - {"contained_work_id", "evidence"}:
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


def _contained_work_from_record(path: Path, record: dict[str, object]) -> ReaderContainedWork:
    if "evidence" not in record:
        msg = f"{path}: contained work record requires at least one evidence item"
        raise ValueError(msg)
    missing = sorted(_REQUIRED_KEYS - record.keys())
    if missing:
        msg = f"{path}: contained work record missing required keys: {', '.join(missing)}"
        raise ValueError(msg)
    status = _record_str(path, record, "status")
    confidence = _record_str(path, record, "confidence")
    if status not in _SUPPORTED_STATUSES:
        msg = f"{path}: unsupported contained work status {status!r}"
        raise ValueError(msg)
    if confidence not in _SUPPORTED_CONFIDENCE:
        msg = f"{path}: unsupported contained work confidence {confidence!r}"
        raise ValueError(msg)
    return ReaderContainedWork(
        contained_work_id=_record_str(path, record, "contained_work_id"),
        parent_work_id=_record_str(path, record, "parent_work_id"),
        collection_id=_record_str(path, record, "collection_id"),
        language=_record_str(path, record, "language"),
        title=_record_str(path, record, "title"),
        author=_record_str(path, record, "author"),
        source_id=_record_str(path, record, "source_id"),
        cts_work_urn=_optional_record_str(record, "cts_work_urn"),
        start_citation=_record_str(path, record, "start_citation"),
        end_citation=_record_str(path, record, "end_citation"),
        status=status,
        confidence=confidence,
        note=_record_str(path, record, "note"),
        source_file=str(path),
        evidence=_evidence_from_record(path, record),
    )


def _evidence_from_record(
    path: Path,
    record: dict[str, object],
) -> tuple[ReaderMetadataOverlayEvidence, ...]:
    raw_evidence = record["evidence"]
    if not isinstance(raw_evidence, list) or not raw_evidence:
        msg = f"{path}: contained work record requires at least one evidence item"
        raise ValueError(msg)
    evidence: list[ReaderMetadataOverlayEvidence] = []
    for raw_item in raw_evidence:
        if not isinstance(raw_item, dict):
            msg = f"{path}: contained work evidence item must be a mapping"
            raise ValueError(msg)
        item = cast(dict[str, str], raw_item)
        missing = sorted(_REQUIRED_EVIDENCE_KEYS - item.keys())
        if missing:
            msg = f"{path}: contained work evidence missing required keys: {', '.join(missing)}"
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
        msg = f"{path}: contained work record key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _optional_record_str(record: dict[str, object], key: str) -> str | None:
    value = record.get(key)
    return value if isinstance(value, str) and value else None


def _raise_unsupported(path: Path, line_number: int) -> None:
    msg = f"{path}:{line_number}: unsupported contained work YAML line"
    raise ValueError(msg)
