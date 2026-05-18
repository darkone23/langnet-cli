from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from langnet.reader.models import ReaderAuthorClassification

AUTHOR_AGENT_KIND_VALUES = (
    "person",
    "collective",
    "tradition",
    "work_title",
    "anonymous_label",
    "ambiguous",
)
AUTHOR_HISTORICITY_STATUS_VALUES = (
    "historical",
    "legendary",
    "mythic",
    "pseudonymous",
    "traditional",
    "uncertain",
    "not_applicable",
)
AUTHOR_PROMINENCE_TIER_VALUES = (
    "canonical",
    "major",
    "common",
    "specialist",
    "obscure",
)
AUTHOR_CONFIDENCE_VALUES = ("high", "medium", "low")

AUTHOR_CLASSIFICATION_OUTPUT_FIELDS = [
    "author_id",
    "author_language",
    "author_source_id",
    "author_display_name",
    "author_canonical_name",
    "author_agent_kind",
    "author_historicity_status",
    "author_period",
    "author_date_range",
    "author_region",
    "author_cultural_context",
    "author_bio",
    "author_prominence_score",
    "author_prominence_tier",
    "author_confidence",
    "author_notes",
    "author_generator_models",
    "author_generator_run_id",
    "work_count",
    "word_count",
    "representative_titles",
]


def load_author_classifications(path: Path) -> list[ReaderAuthorClassification]:
    expanded_path = path.expanduser()
    if expanded_path.is_dir():
        rows: list[ReaderAuthorClassification] = []
        for csv_path in sorted(expanded_path.rglob("*.csv")):
            rows.extend(_load_author_classification_csv(csv_path))
        return rows
    if not expanded_path.exists():
        return []
    return _load_author_classification_csv(expanded_path)


def author_agent_kind_allowed_values() -> list[dict[str, str]]:
    return _allowed_values(
        {
            "person": "Identifiable individual person.",
            "collective": "School, group, community, or corporate attribution.",
            "tradition": "Broad tradition or lineage used as attribution.",
            "work_title": "A title or text label occupying the author slot.",
            "anonymous_label": "Anonymous, unknown, or generic author label.",
            "ambiguous": "Insufficient evidence or mixed use.",
        }
    )


def author_historicity_status_allowed_values() -> list[dict[str, str]]:
    return _allowed_values(
        {
            "historical": "Historically attested person.",
            "legendary": "Person with legendary or tradition-shaped biography.",
            "mythic": "Mythic or divine figure.",
            "pseudonymous": "Name used for pseudonymous attribution.",
            "traditional": "Traditional attribution without secure historicity.",
            "uncertain": "Insufficient evidence for a reliable status.",
            "not_applicable": "Not applicable because the agent is not a person.",
        }
    )


def validate_author_agent_kind(value: str) -> str:
    return _validate_controlled_value(
        field_name="author_agent_kind",
        value=value,
        allowed_values=AUTHOR_AGENT_KIND_VALUES,
    )


def validate_author_historicity_status(value: str) -> str:
    return _validate_controlled_value(
        field_name="author_historicity_status",
        value=value,
        allowed_values=AUTHOR_HISTORICITY_STATUS_VALUES,
    )


def _load_author_classification_csv(path: Path) -> list[ReaderAuthorClassification]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            _author_classification_from_row(path, index, row)
            for index, row in enumerate(reader, start=2)
            if _field(row, "author_id")
        ]


def _author_classification_from_row(
    path: Path,
    row_number: int,
    row: dict[str, Any],
) -> ReaderAuthorClassification:
    return ReaderAuthorClassification(
        author_id=_field(row, "author_id"),
        language=_field(row, "author_language") or _field(row, "language"),
        source_author_id=_field(row, "author_source_id") or _field(row, "source_author_id"),
        canonical_name=_field(row, "author_canonical_name"),
        agent_kind=_row_controlled_value(
            path,
            row_number,
            row,
            "author_agent_kind",
            AUTHOR_AGENT_KIND_VALUES,
        ),
        historicity_status=_row_controlled_value(
            path,
            row_number,
            row,
            "author_historicity_status",
            AUTHOR_HISTORICITY_STATUS_VALUES,
        ),
        period=_field(row, "author_period"),
        date_range=_field(row, "author_date_range"),
        region=_field(row, "author_region"),
        cultural_context=_field(row, "author_cultural_context"),
        bio=_field(row, "author_bio"),
        prominence_score=_integer_field(path, row_number, row, "author_prominence_score"),
        prominence_tier=_row_optional_controlled_value(
            path,
            row_number,
            row,
            "author_prominence_tier",
            AUTHOR_PROMINENCE_TIER_VALUES,
        ),
        confidence=_row_optional_controlled_value(
            path,
            row_number,
            row,
            "author_confidence",
            AUTHOR_CONFIDENCE_VALUES,
        ),
        note=_field(row, "author_notes"),
        generator_models=_field(row, "author_generator_models"),
        generator_run_id=_field(row, "author_generator_run_id"),
        source_file=str(path),
    )


def _row_controlled_value(
    path: Path,
    row_number: int,
    row: dict[str, Any],
    field_name: str,
    allowed_values: Iterable[str],
) -> str:
    value = _field(row, field_name)
    if not value:
        msg = f"{path}:{row_number}: {field_name} is required"
        raise ValueError(msg)
    return _validate_row_controlled_value(path, row_number, field_name, value, allowed_values)


def _row_optional_controlled_value(
    path: Path,
    row_number: int,
    row: dict[str, Any],
    field_name: str,
    allowed_values: Iterable[str],
) -> str:
    value = _field(row, field_name)
    if not value:
        return ""
    return _validate_row_controlled_value(path, row_number, field_name, value, allowed_values)


def _validate_row_controlled_value(
    path: Path,
    row_number: int,
    field_name: str,
    value: str,
    allowed_values: Iterable[str],
) -> str:
    try:
        return _validate_controlled_value(
            field_name=field_name,
            value=value,
            allowed_values=allowed_values,
        )
    except ValueError as exc:
        msg = f"{path}:{row_number}: {exc}"
        raise ValueError(msg) from exc


def _validate_controlled_value(
    *,
    field_name: str,
    value: str,
    allowed_values: Iterable[str],
) -> str:
    normalized = value.strip()
    allowed = tuple(allowed_values)
    if normalized not in allowed:
        msg = f"{field_name} must be one of {', '.join(allowed)}, got {value!r}"
        raise ValueError(msg)
    return normalized


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


def _field(row: dict[str, Any], name: str) -> str:
    value = row.get(name)
    return str(value).strip() if value is not None else ""


def _allowed_values(descriptions: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"id": value, "label": value.replace("_", " ").title(), "description": description}
        for value, description in descriptions.items()
    ]
