from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from langnet.reader.discovery_taxonomy import (
    discovery_group_label,
    validate_discovery_group_id,
    validate_discovery_tag_csv,
)
from langnet.reader.models import ReaderWorkClassification


def load_work_classifications(path: Path) -> list[ReaderWorkClassification]:
    expanded_path = path.expanduser()
    if expanded_path.is_dir():
        rows: list[ReaderWorkClassification] = []
        for csv_path in sorted(expanded_path.rglob("*.csv")):
            rows.extend(_load_classification_csv(csv_path))
        return rows
    if not expanded_path.exists():
        return []
    return _load_classification_csv(expanded_path)


def _load_classification_csv(path: Path) -> list[ReaderWorkClassification]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            _classification_from_row(path, index, row)
            for index, row in enumerate(reader, start=2)
            if _field(row, "work_id")
        ]


def _classification_from_row(
    path: Path,
    row_number: int,
    row: dict[str, Any],
) -> ReaderWorkClassification:
    discovery_group_id = _optional_discovery_group(path, row_number, row)
    discovery_tags = _optional_discovery_tags(path, row_number, row)
    global_score = _integer_field(
        path,
        row_number,
        row,
        "classification_global_popularity_score",
    )
    group_score = _integer_field(
        path,
        row_number,
        row,
        "classification_group_popularity_score",
    )
    global_tier = _field(row, "classification_global_popularity_tier")
    group_tier = _field(row, "classification_group_popularity_tier")
    legacy_popularity_score = _integer_field(
        path,
        row_number,
        row,
        "classification_popularity_score",
    )
    legacy_scope_popularity_score = _integer_field(
        path,
        row_number,
        row,
        "classification_scope_popularity_score",
    )
    category = _field(row, "classification_category")
    scope = _field(row, "classification_scope")
    group_label = discovery_group_label(discovery_group_id)
    return ReaderWorkClassification(
        work_id=_field(row, "work_id"),
        category=category or group_label,
        period=_field(row, "classification_period"),
        date_range=_field(row, "classification_date_range"),
        authorship_status=_field(row, "classification_authorship_status"),
        popularity_score=global_score if global_score is not None else legacy_popularity_score,
        popularity_tier=global_tier or _field(row, "classification_popularity_tier"),
        scope=scope or group_label,
        scope_popularity_score=group_score
        if group_score is not None
        else legacy_scope_popularity_score,
        scope_popularity_tier=group_tier or _field(row, "classification_scope_popularity_tier"),
        confidence=_field(row, "classification_confidence"),
        note=_field(row, "classification_notes"),
        generator_models=_field(row, "classification_generator_models"),
        generator_run_id=_field(row, "classification_generator_run_id"),
        source_file=str(path),
        discovery_group_id=discovery_group_id,
        discovery_tags=discovery_tags,
        global_popularity_score=global_score,
        global_popularity_tier=global_tier,
        group_popularity_score=group_score,
        group_popularity_tier=group_tier,
    )


def _field(row: dict[str, Any], name: str) -> str:
    value = row.get(name)
    return str(value).strip() if value is not None else ""


def _integer_field(
    path: Path,
    row_number: int,
    row: dict[str, Any],
    field_name: str,
) -> int | None:
    raw_value = _field(row, field_name)
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        msg = f"{path}:{row_number}: {field_name} must be an integer, got {raw_value!r}"
        raise ValueError(msg) from exc


def _optional_discovery_group(
    path: Path,
    row_number: int,
    row: dict[str, Any],
) -> str:
    raw_value = _field(row, "classification_discovery_group_id")
    if not raw_value:
        return ""
    try:
        return validate_discovery_group_id(raw_value)
    except ValueError as exc:
        msg = f"{path}:{row_number}: classification_discovery_group_id has {exc}"
        raise ValueError(msg) from exc


def _optional_discovery_tags(
    path: Path,
    row_number: int,
    row: dict[str, Any],
) -> str:
    raw_value = _field(row, "classification_discovery_tags")
    if not raw_value:
        return ""
    try:
        return validate_discovery_tag_csv(raw_value)
    except ValueError as exc:
        msg = f"{path}:{row_number}: classification_discovery_tags has {exc}"
        raise ValueError(msg) from exc
