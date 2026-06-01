from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class ReaderSearchConcept:
    concept_id: str
    language: str
    labels: tuple[str, ...]
    source_queries: tuple[str, ...]
    source_file: str
    explanation: str = ""


def load_search_concepts(root: Path) -> list[ReaderSearchConcept]:
    if not root.exists():
        return []

    concepts: list[ReaderSearchConcept] = []
    for path in sorted(root.rglob("*.yaml")):
        concepts.extend(_load_concept_file(path))
    return concepts


def _load_concept_file(path: Path) -> list[ReaderSearchConcept]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        msg = f"{path}: concept file must contain a mapping"
        raise ValueError(msg)
    records = raw.get("concepts")
    if not isinstance(records, list):
        msg = f"{path}: concept file must contain a concepts list"
        raise ValueError(msg)
    return [_concept_from_record(path, record) for record in records]


def _concept_from_record(path: Path, record: Any) -> ReaderSearchConcept:
    if not isinstance(record, dict):
        msg = f"{path}: concept record must be a mapping"
        raise ValueError(msg)
    concept_id = _required_str(path, record, "id")
    language = _required_str(path, record, "language")
    labels = _required_string_list(path, record, "labels")
    source_queries = _required_string_list(path, record, "source_queries")
    explanation = record.get("explanation") or record.get("notes") or ""
    if not isinstance(explanation, str):
        msg = f"{path}: concept {concept_id!r} explanation must be a string"
        raise ValueError(msg)
    return ReaderSearchConcept(
        concept_id=concept_id,
        language=language,
        labels=tuple(labels),
        source_queries=tuple(source_queries),
        source_file=str(path),
        explanation=explanation,
    )


def _required_str(path: Path, record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"{path}: concept record missing string key {key!r}"
        raise ValueError(msg)
    return value.strip()


def _required_string_list(path: Path, record: dict[str, Any], key: str) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list) or not value:
        msg = f"{path}: concept record missing list key {key!r}"
        raise ValueError(msg)
    if not all(isinstance(item, str) and item.strip() for item in value):
        msg = f"{path}: concept record key {key!r} must contain strings"
        raise ValueError(msg)
    return [item.strip() for item in value]
