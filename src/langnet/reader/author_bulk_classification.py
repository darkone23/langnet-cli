from __future__ import annotations

import csv
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from langnet.reader.author_classification import (
    AUTHOR_AGENT_KIND_VALUES,
    AUTHOR_CLASSIFICATION_OUTPUT_FIELDS,
    AUTHOR_CONFIDENCE_VALUES,
    AUTHOR_HISTORICITY_STATUS_VALUES,
    author_agent_kind_allowed_values,
    author_historicity_status_allowed_values,
)
from langnet.reader.bulk_classification import (
    POPULARITY_TIER_VALUES,
    _batch_ordered_rows,
    _batches,
    _response_rows_from_cache_or_model,
)

AUTHOR_CLASSIFICATION_INPUT_FIELDS = [
    "author_id",
    "author_language",
    "author_source_id",
    "author_display_name",
    "work_count",
    "word_count",
    "representative_titles",
]
AUTHOR_GENERATED_FIELDS = [
    field
    for field in AUTHOR_CLASSIFICATION_OUTPUT_FIELDS
    if field not in AUTHOR_CLASSIFICATION_INPUT_FIELDS
]
AUTHOR_FIELD_ALIASES = {
    "author_canonical_name": ("canonical_name", "name"),
    "author_agent_kind": ("agent_kind", "kind"),
    "author_historicity_status": ("historicity_status", "historicity"),
    "author_period": ("period",),
    "author_date_range": ("date_range", "date"),
    "author_region": ("region", "place"),
    "author_cultural_context": ("cultural_context", "context"),
    "author_bio": ("bio", "biography"),
    "author_prominence_score": ("prominence_score", "score"),
    "author_prominence_tier": ("prominence_tier", "tier"),
    "author_confidence": ("confidence",),
    "author_notes": ("notes", "note"),
}
AuthorClassifierCallback = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class AuthorClassificationRunConfig:
    input_csv: Path
    output_csv: Path
    model: str
    run_id: str
    batch_size: int
    raw_response_dir: Path | None = None
    shuffle_seed: str | None = None
    concurrency: int = 1


def load_author_classification_input_rows(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.expanduser().open("r", encoding="utf-8", newline="") as handle:
        return [
            {str(key): str(value or "").strip() for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
            if str(row.get("author_id") or "").strip()
        ]


def classify_author_csv(
    *,
    config: AuthorClassificationRunConfig,
    classify: AuthorClassifierCallback,
) -> dict[str, Any]:
    input_rows = load_author_classification_input_rows(config.input_csv)
    ordered_rows = _batch_ordered_rows(input_rows, config.shuffle_seed)
    batches = _batches(ordered_rows, config.batch_size)
    batch_count = len(batches)
    batch_count_lock = Lock()

    def next_split_batch_index() -> int:
        nonlocal batch_count
        with batch_count_lock:
            batch_count += 1
            return batch_count

    def classify_batch(
        batch: Sequence[dict[str, str]],
        batch_index: int,
    ) -> list[dict[str, str]]:
        payload = author_classification_batch_payload(
            rows=batch,
            model=config.model,
            run_id=config.run_id,
            batch_index=batch_index,
        )
        response_rows = _response_rows_from_cache_or_model(
            config=config,
            classify=classify,
            payload=payload,
            batch_index=batch_index,
        )
        merged_rows = _merge_author_rows(
            input_rows=batch,
            response_rows=response_rows,
            model=config.model,
            run_id=config.run_id,
        )
        if len(batch) > 1 and _complete_author_metadata_count(merged_rows) < len(batch):
            midpoint = max(1, len(batch) // 2)
            return classify_batch(
                batch[:midpoint],
                next_split_batch_index(),
            ) + classify_batch(
                batch[midpoint:],
                next_split_batch_index(),
            )
        return merged_rows

    if config.concurrency <= 1 or len(batches) <= 1:
        batch_results = [
            classify_batch(batch, batch_index) for batch_index, batch in enumerate(batches, start=1)
        ]
    else:
        with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            futures = [
                executor.submit(classify_batch, batch, batch_index)
                for batch_index, batch in enumerate(batches, start=1)
            ]
            batch_results = [future.result() for future in futures]

    generated_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for result_rows in batch_results:
        for generated_row in result_rows:
            key = _author_key(generated_row)
            if key[0]:
                generated_by_key[key] = generated_row
    generated_rows = [
        generated_by_key[_author_key(input_row)]
        for input_row in input_rows
        if _author_key(input_row) in generated_by_key
    ]
    write_author_classification_csv(config.output_csv, generated_rows)
    return {
        "input_count": len(input_rows),
        "generated_count": _generated_author_metadata_count(generated_rows),
        "batch_count": batch_count,
        "shuffle_seed": config.shuffle_seed,
        "output_csv": str(config.output_csv),
        "model": config.model,
        "run_id": config.run_id,
        "concurrency": config.concurrency,
    }


def author_classification_batch_payload(
    *,
    rows: Sequence[Mapping[str, str]],
    model: str,
    run_id: str,
    batch_index: int,
) -> dict[str, Any]:
    return {
        "task": "reader_author_classification",
        "instructions": [
            "Return one JSON object with a rows array.",
            "Return one output row for every input row.",
            "Keep author_id and author_language exactly as provided.",
            "Keep author_source_id exactly as provided.",
            "Choose author_agent_kind and author_historicity_status from allowed values.",
            (
                "Use author_agent_kind=work_title when author_display_name is a "
                "named text or textual corpus occupying the author slot."
            ),
            (
                "Use author_agent_kind=anonymous_label for explicit anonymous "
                "or unknown headings such as Anonymous, Anonymi, Adespota, or Incerti."
            ),
            (
                "Use author_agent_kind=collective only for real groups, schools, "
                "communities, or corporate bodies."
            ),
            (
                "For mythic or divine named figures, use author_agent_kind=person "
                "and author_historicity_status=mythic."
            ),
            (
                "Use author_period, author_date_range, author_region, "
                "and author_cultural_context when known."
            ),
            "Write author_bio as concise reader-facing scholarly prose.",
            "Use author_prominence_score from 0 to 100 within the language corpus.",
            "Include author_notes in every row to explain ambiguous source labels.",
        ],
        "allowed_values": {
            "author_agent_kind": author_agent_kind_allowed_values(),
            "author_historicity_status": author_historicity_status_allowed_values(),
            "author_prominence_tier": POPULARITY_TIER_VALUES,
            "author_confidence": ["high", "medium", "low"],
        },
        "output_fields": AUTHOR_CLASSIFICATION_OUTPUT_FIELDS,
        "model": model,
        "run_id": run_id,
        "batch_index": batch_index,
        "row_count": len(rows),
        "rows": [
            {field: row.get(field, "") for field in AUTHOR_CLASSIFICATION_INPUT_FIELDS}
            for row in rows
        ],
    }


def write_author_classification_csv(
    output_csv: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    output_csv = output_csv.expanduser()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUTHOR_CLASSIFICATION_OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {field: row.get(field, "") for field in AUTHOR_CLASSIFICATION_OUTPUT_FIELDS}
            )


def _merge_author_rows(
    *,
    input_rows: Sequence[Mapping[str, str]],
    response_rows: Sequence[Mapping[str, Any]],
    model: str,
    run_id: str,
) -> list[dict[str, str]]:
    response_by_key = {
        (
            str(row.get("author_id") or "").strip(),
            str(row.get("author_language") or row.get("language") or "").strip(),
        ): row
        for row in response_rows
        if str(row.get("author_id") or "").strip()
    }
    merged_rows: list[dict[str, str]] = []
    for index, input_row in enumerate(input_rows):
        response_row = response_by_key.get(_author_key(input_row), {})
        if not response_row and len(input_rows) == len(response_rows):
            response_row = response_rows[index]
        merged = {
            field: str(input_row.get(field, "") or "")
            for field in AUTHOR_CLASSIFICATION_INPUT_FIELDS
        }
        for field in AUTHOR_GENERATED_FIELDS:
            merged[field] = _author_generated_field_value(response_row, field)
        merged["author_generator_models"] = model
        merged["author_generator_run_id"] = run_id
        merged_rows.append(merged)
    return merged_rows


def _author_generated_field_value(row: Mapping[str, Any], field: str) -> str:
    value = _author_generated_value(row, field)
    return _normalize_author_generated_field(field, str(value if value is not None else ""))


def _normalize_author_generated_field(field: str, value: str) -> str:
    normalized = value.strip()
    normalized_key = normalized.casefold().replace("-", "_").replace(" ", "_")
    if field == "author_agent_kind":
        return _normalized_controlled_value(
            normalized_key,
            allowed_values=AUTHOR_AGENT_KIND_VALUES,
            aliases={
                "mythic": "person",
                "mythical": "person",
                "mythological": "person",
                "divine": "person",
                "text": "work_title",
                "title": "work_title",
                "work": "work_title",
                "anonymous": "anonymous_label",
                "unknown": "anonymous_label",
            },
            fallback="ambiguous",
            use_fallback_for_empty=True,
        )
    if field == "author_historicity_status":
        return _normalized_controlled_value(
            normalized_key,
            allowed_values=AUTHOR_HISTORICITY_STATUS_VALUES,
            aliases={
                "mythical": "mythic",
                "mythological": "mythic",
                "divine": "mythic",
                "anonymous": "not_applicable",
                "unknown": "uncertain",
            },
            fallback="uncertain",
            use_fallback_for_empty=True,
        )
    if field == "author_prominence_tier":
        return _normalized_controlled_value(
            normalized_key,
            allowed_values=POPULARITY_TIER_VALUES,
            aliases={},
            fallback="specialist",
        )
    if field == "author_confidence":
        return _normalized_controlled_value(
            normalized_key,
            allowed_values=AUTHOR_CONFIDENCE_VALUES,
            aliases={},
            fallback="medium",
        )
    return normalized


def _normalized_controlled_value(
    normalized_key: str,
    *,
    allowed_values: Sequence[str],
    aliases: Mapping[str, str],
    fallback: str,
    use_fallback_for_empty: bool = False,
) -> str:
    if normalized_key in allowed_values:
        return normalized_key
    alias = aliases.get(normalized_key)
    if alias:
        return alias
    if normalized_key == "":
        return fallback if use_fallback_for_empty else ""
    return fallback


def _author_generated_value(row: Mapping[str, Any], field: str) -> Any:
    if field in row:
        return row.get(field)
    nested = row.get("author")
    if isinstance(nested, Mapping):
        nested_value = _author_generated_value(nested, field)
        if nested_value != "":
            return nested_value
    for alias in AUTHOR_FIELD_ALIASES.get(field, ()):
        if alias in row:
            return row.get(alias)
    return ""


def _author_key(row: Mapping[str, str]) -> tuple[str, str]:
    return (
        str(row.get("author_id") or "").strip(),
        str(row.get("author_language") or row.get("language") or "").strip(),
    )


def _has_generated_author_metadata(row: Mapping[str, str]) -> bool:
    return any(str(row.get(field) or "").strip() for field in AUTHOR_GENERATED_FIELDS[:-2])


def _generated_author_metadata_count(rows: Sequence[Mapping[str, str]]) -> int:
    return sum(_has_generated_author_metadata(row) for row in rows)


def _complete_author_metadata_count(rows: Sequence[Mapping[str, str]]) -> int:
    return sum(
        _has_generated_author_metadata(row) and bool(str(row.get("author_notes") or "").strip())
        for row in rows
    )
