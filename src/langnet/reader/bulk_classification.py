from __future__ import annotations

import csv
import random
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Protocol, cast

import orjson

from langnet.reader.discovery_taxonomy import (
    DISCOVERY_GROUPS,
    DISCOVERY_TAGS,
    discovery_group_allowed_values,
    discovery_group_label,
    discovery_tag_allowed_values,
    discovery_tags_to_csv,
    normalize_discovery_tags,
    validate_discovery_group_id,
    validate_discovery_tag_csv,
)

CLASSIFICATION_INPUT_FIELDS = [
    "work_id",
    "language",
    "title",
    "author",
    "author_id",
    "source_id",
    "cts_work_urn",
    "work_kind",
    "parent_work_id",
    "start_citation",
    "end_citation",
    "word_count",
    "word_count_method",
    "source_metadata_summary",
]
GENERATED_CLASSIFICATION_FIELDS = [
    "classification_discovery_group_id",
    "classification_discovery_tags",
    "classification_global_popularity_score",
    "classification_global_popularity_tier",
    "classification_group_popularity_score",
    "classification_group_popularity_tier",
    "classification_category",
    "classification_period",
    "classification_date_range",
    "classification_authorship_status",
    "classification_popularity_score",
    "classification_popularity_tier",
    "classification_scope",
    "classification_scope_popularity_score",
    "classification_scope_popularity_tier",
    "classification_confidence",
    "classification_notes",
    "classification_generator_models",
    "classification_generator_run_id",
]
CLASSIFICATION_OUTPUT_FIELDS = CLASSIFICATION_INPUT_FIELDS + GENERATED_CLASSIFICATION_FIELDS
CLASSIFICATION_FIELD_ALIASES = {
    "classification_discovery_group_id": ("discovery_group_id", "group_id", "group"),
    "classification_discovery_tags": ("discovery_tags", "tags"),
    "classification_global_popularity_score": (
        "global_popularity_score",
        "popularity_score",
        "score",
    ),
    "classification_global_popularity_tier": (
        "global_popularity_tier",
        "popularity_tier",
        "tier",
    ),
    "classification_group_popularity_score": (
        "group_popularity_score",
        "scope_popularity_score",
        "topic_popularity_score",
    ),
    "classification_group_popularity_tier": (
        "group_popularity_tier",
        "scope_popularity_tier",
        "topic_popularity_tier",
    ),
    "classification_category": ("category",),
    "classification_period": ("period",),
    "classification_date_range": ("date_range", "date"),
    "classification_authorship_status": ("authorship_status", "authorship"),
    "classification_popularity_score": ("popularity_score", "score"),
    "classification_popularity_tier": ("popularity_tier", "tier"),
    "classification_scope": ("scope", "topic", "subfield", "domain"),
    "classification_scope_popularity_score": (
        "scope_popularity_score",
        "topic_popularity_score",
        "subfield_popularity_score",
        "domain_popularity_score",
    ),
    "classification_scope_popularity_tier": (
        "scope_popularity_tier",
        "topic_popularity_tier",
        "subfield_popularity_tier",
        "domain_popularity_tier",
    ),
    "classification_confidence": ("confidence",),
    "classification_notes": ("notes", "note"),
    "classification_generator_models": ("generator_models", "models"),
    "classification_generator_run_id": ("generator_run_id", "run_id"),
}
COMMON_CLASSIFICATION_CATEGORIES = [
    "Epic",
    "Poetry",
    "Drama",
    "Novel",
    "History",
    "Biography",
    "Philosophy",
    "Grammar",
    "Lexicography",
    "Rhetoric",
    "Technical Treatise",
    "Religious Text",
    "Commentary",
    "Fragmentary Text",
    "Inscription",
    "Letter",
    "Legal Text",
    "Medical Text",
    "Astronomical Text",
    "Mathematical Text",
    "Hymn",
    "Narrative Prose",
    "Other",
]
LANGUAGE_CLASSIFICATION_GUIDANCE = {
    "grc": {
        "period_values": [
            "Archaic",
            "Classical",
            "Hellenistic",
            "Roman Imperial",
            "Late Antique",
            "Byzantine",
            "Medieval",
            "Early Modern",
            "Modern",
            "Uncertain",
        ],
        "category_additions": [
            "Patristic Text",
            "Apocryphal Acts",
            "Martyr Act",
            "Hagiography",
            "Scholia",
        ],
    },
    "lat": {
        "period_values": [
            "Archaic",
            "Republican",
            "Late Republic",
            "Augustan",
            "Early Imperial",
            "Imperial",
            "Late Antique",
            "Medieval",
            "Renaissance",
            "Early Modern",
            "Uncertain",
        ],
        "category_additions": [
            "Satire",
            "Elegy",
            "Didactic Poetry",
            "Patristic Text",
            "Scholarly Commentary",
        ],
    },
    "san": {
        "period_values": [
            "Vedic",
            "Epic",
            "Classical",
            "Early Medieval",
            "Medieval",
            "Early Modern",
            "Modern",
            "Uncertain",
        ],
        "category_additions": [
            "Vedic Text",
            "Itihasa",
            "Purana",
            "Sutra",
            "Kavya",
            "Buddhist Scripture",
            "Jain Text",
            "Dharmashastra",
            "Tantra",
            "Stotra",
        ],
    },
}
LANGUAGE_SCOPE_VALUES = {
    "grc": [
        "Greek Epic Poetry",
        "Greek Lyric Poetry",
        "Greek Drama",
        "Greek Novel",
        "Greek History",
        "Greek Biography",
        "Greek Philosophy",
        "Greek Grammar",
        "Greek Lexicography",
        "Greek Rhetoric",
        "Greek Medicine",
        "Greek Science and Natural History",
        "Greek Mathematics and Astronomy",
        "Greek Religious Literature",
        "Greek Patristic Literature",
        "Greek Hagiography and Martyr Acts",
        "Greek Apocrypha",
        "Greek Commentary and Scholia",
        "Greek Fragmentary Literature",
        "Greek Inscriptions",
        "Greek Letters",
        "Greek Law",
        "Greek Technical Literature",
        "Greek Mythography",
        "Other Greek Literature",
    ],
    "lat": [
        "Latin Epic Poetry",
        "Latin Lyric and Elegiac Poetry",
        "Latin Drama",
        "Latin Satire",
        "Latin History",
        "Latin Biography",
        "Latin Philosophy",
        "Latin Rhetoric",
        "Latin Grammar",
        "Latin Lexicography",
        "Latin Commentary and Scholia",
        "Latin Medicine",
        "Latin Science and Natural History",
        "Latin Mathematics and Astronomy",
        "Latin Law",
        "Latin Letters",
        "Latin Religious Literature",
        "Latin Patristic Literature",
        "Latin Fragmentary Literature",
        "Latin Inscriptions",
        "Latin Technical Literature",
        "Other Latin Literature",
    ],
    "san": [
        "Sanskrit Epic Literature",
        "Sanskrit Kavya",
        "Sanskrit Drama",
        "Sanskrit Grammar",
        "Sanskrit Lexicography",
        "Sanskrit Philosophy",
        "Vedanta",
        "Nyaya",
        "Buddhist Philosophy",
        "Jain Literature",
        "Buddhist Scripture",
        "Buddhist Tantra",
        "Śaiva Tantra",
        "Vedic Texts",
        "Vedic Ritual and Exegesis",
        "Dharmashastra",
        "Purana",
        "Ayurveda",
        "Sanskrit Astronomy and Mathematics",
        "Sanskrit Commentary",
        "Stotra",
        "Sanskrit Narrative Literature",
        "Other Sanskrit Literature",
    ],
}
AUTHORSHIP_STATUS_VALUES = [
    "single_attributed",
    "traditional",
    "anonymous",
    "attributed",
    "uncertain",
    "disputed",
    "composite",
    "pseudepigraphic",
]
POPULARITY_TIER_VALUES = ["canonical", "major", "common", "specialist", "obscure"]
CONFIDENCE_VALUES = ["high", "medium", "low"]
POPULARITY_RUBRIC = [
    {
        "tier": "canonical",
        "score_range": "90-100",
        "meaning": "Central across the language corpus and broad curricula.",
    },
    {
        "tier": "major",
        "score_range": "70-89",
        "meaning": "Widely studied across the language tradition.",
    },
    {
        "tier": "common",
        "score_range": "40-69",
        "meaning": "Often read or cited beyond a narrow specialty.",
    },
    {
        "tier": "specialist",
        "score_range": "10-39",
        "meaning": "Important mainly within a specialty or research subfield.",
    },
    {
        "tier": "obscure",
        "score_range": "0-9",
        "meaning": "Rarely read, fragmentary, marginal, or minimally attested.",
    },
]
GENERIC_FRAGMENT_TITLE_MARKERS = (
    "fragment",
    "fragments",
    "fragmenta",
    "fragmentum",
    "fragmentum in",
    "fragmenta in",
    "frr.",
    "frr",
)
ScopeRule = tuple[tuple[str, ...], str]
GREEK_SCOPE_RULES: tuple[ScopeRule, ...] = (
    (("medicine", "medical"), "Greek Medicine"),
    (("lexicograph",), "Greek Lexicography"),
    (("grammar", "grammatical"), "Greek Grammar"),
    (("martyr", "hagiograph"), "Greek Hagiography and Martyr Acts"),
    (("apocryph",), "Greek Apocrypha"),
    (("papyrolog",), "Greek Fragmentary Literature"),
    (("patristic", "early christian", "exegesis"), "Greek Patristic Literature"),
    (("fragment",), "Greek Fragmentary Literature"),
    (("rhetoric",), "Greek Rhetoric"),
    (("mythograph", "mythography"), "Greek Mythography"),
    (("history", "historiograph"), "Greek History"),
    (("science", "natural"), "Greek Science and Natural History"),
)
LATIN_SCOPE_RULES: tuple[ScopeRule, ...] = (
    (("medicine", "medical"), "Latin Medicine"),
    (("grammar", "grammatical"), "Latin Grammar"),
    (("lexicograph",), "Latin Lexicography"),
    (("appendix vergiliana", "vergilian pseudepigrapha"), "Latin Epic Poetry"),
    (("fragment",), "Latin Fragmentary Literature"),
    (("inscription", "epigraph"), "Latin Inscriptions"),
    (("history", "historiograph"), "Latin History"),
    (("rhetoric",), "Latin Rhetoric"),
    (("commentary", "scholia"), "Latin Commentary and Scholia"),
    (("law", "legal"), "Latin Law"),
    (("popular verse", "political verse", "satire"), "Latin Satire"),
    (("didactic", "technical"), "Latin Technical Literature"),
)
SANSKRIT_SCOPE_RULES: tuple[ScopeRule, ...] = (
    (("śrauta", "srauta", "vedic ritual"), "Vedic Ritual and Exegesis"),
    (("śaiva", "saiva", "shaiva"), "Śaiva Tantra"),
    (("yogācāra", "yogacara"), "Buddhist Philosophy"),
    (("prajñāpāramitā", "prajnaparamita"), "Buddhist Scripture"),
    (("buddhist tantra", "vajray"), "Buddhist Tantra"),
    (("drama",), "Sanskrit Drama"),
    (("śataka", "satak", "kavya", "kāvya", "mahakavya"), "Sanskrit Kavya"),
    (("commentary", "bhāṣya", "bhasya"), "Sanskrit Commentary"),
    (("stotra", "hymn"), "Stotra"),
    (("vedanta", "vedānta"), "Vedanta"),
    (("nyaya", "nyāya"), "Nyaya"),
    (("ayurveda", "āyurveda", "medicine", "medical"), "Ayurveda"),
)

ClassifierCallback = Callable[[dict[str, Any]], str]


class _ResponseCacheConfig(Protocol):
    raw_response_dir: Path | None


@dataclass(frozen=True)
class ClassificationRunConfig:
    input_csv: Path
    output_csv: Path
    model: str
    run_id: str
    batch_size: int
    raw_response_dir: Path | None = None
    shuffle_seed: str | None = None
    concurrency: int = 1


def load_classification_input_rows(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.expanduser().open("r", encoding="utf-8", newline="") as handle:
        return [
            {str(key): str(value or "").strip() for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
            if str(row.get("work_id") or "").strip()
        ]


def classify_work_csv(
    *,
    config: ClassificationRunConfig,
    classify: ClassifierCallback,
) -> dict[str, Any]:
    input_rows = load_classification_input_rows(config.input_csv)
    batch_input_rows = _batch_ordered_rows(input_rows, config.shuffle_seed)
    generated_by_work_id: dict[str, dict[str, str]] = {}
    generated_without_work_id: list[dict[str, str]] = []
    batches = _batches(batch_input_rows, config.batch_size)
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
        payload = classification_batch_payload(
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
        return _merged_response_rows(batch, response_rows)

    def _merged_response_rows(
        batch: Sequence[dict[str, str]],
        response_rows: list[Mapping[str, Any]],
    ) -> list[dict[str, str]]:
        merged_rows = _merge_generated_rows(
            input_rows=batch,
            response_rows=response_rows,
            model=config.model,
            run_id=config.run_id,
        )
        if len(batch) > 1 and _complete_generated_metadata_count(merged_rows) < len(batch):
            midpoint = max(1, len(batch) // 2)
            return classify_batch(
                batch[:midpoint],
                next_split_batch_index(),
            ) + classify_batch(
                batch[midpoint:],
                next_split_batch_index(),
            )
        return merged_rows

    batch_results: list[list[dict[str, str]]] = []
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

    for result_rows in batch_results:
        for generated_row in result_rows:
            work_id = str(generated_row.get("work_id") or "").strip()
            if work_id:
                generated_by_work_id[work_id] = generated_row
            else:
                generated_without_work_id.append(generated_row)
    generated_rows = [
        generated_by_work_id[str(input_row.get("work_id") or "").strip()]
        for input_row in input_rows
        if str(input_row.get("work_id") or "").strip() in generated_by_work_id
    ]
    generated_rows.extend(generated_without_work_id)
    write_generated_classification_csv(config.output_csv, generated_rows)
    return {
        "input_count": len(input_rows),
        "generated_count": _generated_metadata_count(generated_rows),
        "batch_count": batch_count,
        "shuffle_seed": config.shuffle_seed,
        "output_csv": str(config.output_csv),
        "model": config.model,
        "run_id": config.run_id,
        "concurrency": config.concurrency,
    }


def classification_batch_payload(
    *,
    rows: Sequence[Mapping[str, str]],
    model: str,
    run_id: str,
    batch_index: int,
) -> dict[str, Any]:
    languages = _payload_languages(rows)
    return {
        "schema_version": "langnet.reader.work_classification.request.v1",
        "task": "Generate scholarly reader work metadata for classical literature.",
        "row_count": len(rows),
        "instructions": [
            "Return one JSON object with a rows array.",
            "Return exactly one generated metadata row for every input work_id.",
            "Copy each input work_id exactly into its generated row.",
            "Use the exact output field names.",
            (
                "Use generated scholarly judgment. Treat output as final generated "
                "metadata for direct catalog import."
            ),
            (
                "Choose classification_discovery_group_id from its allowed values. "
                "This one group is the work's peer bucket for group popularity."
            ),
            (
                "Choose classification_discovery_tags from its allowed values only. "
                "Use zero or more tags; tags are discovery facets, not freeform labels."
            ),
            (
                "Use classification_period as a concise historical period label "
                "from the period values for the row's language."
            ),
            (
                "Use classification_global_popularity_score from 0 to 100 within "
                "the whole language corpus for the row's language."
            ),
            (
                "Calibrate popularity against all works in that language, not within "
                "a specialty or subfield."
            ),
            (
                "A leading work on a niche topic can still receive a specialist or "
                "obscure score when the whole language corpus is the comparison set."
            ),
            "Use one classification_global_popularity_tier from its allowed values.",
            (
                "Use classification_group_popularity_score from 0 to 100 within "
                "classification_discovery_group_id."
            ),
            (
                "Use one classification_group_popularity_tier from its allowed values "
                "within that discovery group."
            ),
            (
                "The compatibility fields classification_category, classification_scope, "
                "classification_popularity_score, classification_popularity_tier, "
                "classification_scope_popularity_score, and "
                "classification_scope_popularity_tier may be omitted; the importer "
                "derives them from the discovery fields."
            ),
            "Use one classification_popularity_tier from its allowed values if provided.",
            "Use one classification_authorship_status from its allowed values.",
            "Use one classification_confidence from its allowed values.",
            "Include classification_notes in every row.",
            (
                "Use standalone scholarly prose in classification_notes for a "
                "reader-facing scholarly catalog."
            ),
            (
                "Base classification_notes on the named work, author, language, "
                "identifiers, and word_count."
            ),
            "Use source_id and work_id for row matching and edition awareness.",
            "Use source_metadata_summary as source-backed catalog evidence.",
            "Synthesize final labels from the whole row.",
            (
                "Write classification_notes around title, author, tradition, genre, "
                "and scholarly role."
            ),
            "Keep source collection names in identifiers and provenance fields.",
            (
                "When rows represent alternate editions or source copies, use the "
                "same work-level scholarly judgment and describe the work's scholarly role."
            ),
            (
                "Generic titles such as Fragmenta, fragmentum, fragments, frr., "
                "carmina, or excerpta are not enough by themselves to identify a work."
            ),
            (
                "Use author, author_id, source_id, cts_work_urn, word_count, "
                "parent_work_id, and citation bounds to disambiguate generic titles."
            ),
            (
                "For generic fragment titles, classify the author's known work context "
                "when available; otherwise use Fragmentary Text, lower confidence, and "
                "state the ambiguity in classification_notes."
            ),
            (
                "For fragmentary works, classification_category can be Fragmentary Text, "
                "but classification_scope should prefer the recoverable topical or genre "
                "domain such as Greek Lexicography, Latin Law, Latin Grammar, or Greek "
                "Patristic Literature."
            ),
            (
                "Use or reserve Fragmentary Literature for indeterminate fragments whose "
                "topical or genre domain cannot be recovered from the row context."
            ),
        ],
        "allowed_values": {
            "classification_category_common": COMMON_CLASSIFICATION_CATEGORIES,
            "classification_discovery_group_id": discovery_group_allowed_values(),
            "classification_discovery_tags": discovery_tag_allowed_values(),
            "classification_period": {
                language: LANGUAGE_CLASSIFICATION_GUIDANCE[language]["period_values"]
                for language in languages
                if language in LANGUAGE_CLASSIFICATION_GUIDANCE
            },
            "classification_scope": {
                language: LANGUAGE_SCOPE_VALUES[language]
                for language in languages
                if language in LANGUAGE_SCOPE_VALUES
            },
            "classification_authorship_status": AUTHORSHIP_STATUS_VALUES,
            "classification_popularity_tier": POPULARITY_TIER_VALUES,
            "classification_global_popularity_tier": POPULARITY_TIER_VALUES,
            "classification_scope_popularity_tier": POPULARITY_TIER_VALUES,
            "classification_group_popularity_tier": POPULARITY_TIER_VALUES,
            "classification_confidence": CONFIDENCE_VALUES,
        },
        "language_guidance": {
            language: LANGUAGE_CLASSIFICATION_GUIDANCE[language]
            for language in languages
            if language in LANGUAGE_CLASSIFICATION_GUIDANCE
        },
        "popularity_rubric": POPULARITY_RUBRIC,
        "output_fields": GENERATED_CLASSIFICATION_FIELDS,
        "model": model,
        "run_id": run_id,
        "batch_index": batch_index,
        "rows": [
            {
                **{field: row.get(field, "") for field in CLASSIFICATION_INPUT_FIELDS},
                "classifier_context": _classifier_context(row),
            }
            for row in rows
        ],
    }


def _payload_languages(rows: Sequence[Mapping[str, str]]) -> list[str]:
    return sorted({str(row.get("language") or "").strip() for row in rows if row.get("language")})


def _classifier_context(row: Mapping[str, str]) -> dict[str, Any]:
    title = str(row.get("title") or "").strip()
    title_specificity = _title_specificity(title)
    disambiguation_fields = {
        field: str(row.get(field) or "").strip()
        for field in (
            "author",
            "author_id",
            "source_id",
            "cts_work_urn",
            "word_count",
            "parent_work_id",
            "start_citation",
            "end_citation",
        )
        if str(row.get(field) or "").strip()
    }
    note = (
        "Title is a generic fragmentary title; disambiguate from author, identifiers, "
        "word_count, and citation context."
        if title_specificity == "generic_fragmentary"
        else "Title appears specific enough for ordinary work-level classification."
    )
    return {
        "title_specificity": title_specificity,
        "disambiguation_fields": disambiguation_fields,
        "source_metadata_summary": str(row.get("source_metadata_summary") or "").strip(),
        "note": note,
    }


def _title_specificity(title: str) -> str:
    title_key = _scope_key(title).strip()
    if not title_key:
        return "missing"
    title_terms = set(title_key.split())
    if any(
        _generic_fragment_marker_matches(title_key, title_terms, marker)
        for marker in GENERIC_FRAGMENT_TITLE_MARKERS
    ):
        return "generic_fragmentary"
    return "specific"


def _generic_fragment_marker_matches(title_key: str, title_terms: set[str], marker: str) -> bool:
    marker_key = _scope_key(marker).strip()
    marker_terms = marker_key.split()
    return (
        title_key == marker_key
        or title_key.startswith(f"{marker_key} ")
        or (len(marker_terms) == 1 and marker_key in title_terms)
    )


def _batch_ordered_rows(
    rows: Sequence[dict[str, str]],
    shuffle_seed: str | None,
) -> list[dict[str, str]]:
    ordered_rows = list(rows)
    if shuffle_seed:
        random.Random(shuffle_seed).shuffle(ordered_rows)
    return ordered_rows


def write_generated_classification_csv(output_csv: Path, rows: Sequence[Mapping[str, str]]) -> None:
    expanded_path = output_csv.expanduser()
    expanded_path.parent.mkdir(parents=True, exist_ok=True)
    with expanded_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLASSIFICATION_OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CLASSIFICATION_OUTPUT_FIELDS})


def _write_raw_response(
    raw_response_dir: Path | None,
    batch_index: int,
    response_text: str,
) -> None:
    if raw_response_dir is None:
        return
    expanded_dir = raw_response_dir.expanduser()
    expanded_dir.mkdir(parents=True, exist_ok=True)
    (expanded_dir / f"batch-{batch_index:04d}.json").write_text(response_text, encoding="utf-8")


def _response_rows_from_cache_or_model(
    *,
    config: _ResponseCacheConfig,
    classify: ClassifierCallback,
    payload: dict[str, Any],
    batch_index: int,
) -> list[Mapping[str, Any]]:
    cached_response_text = _read_raw_response(config.raw_response_dir, batch_index)
    if cached_response_text is not None:
        try:
            return _response_rows(cached_response_text)
        except (ValueError, orjson.JSONDecodeError):
            pass
    response_text = classify(payload)
    response_rows = _response_rows(response_text)
    _write_raw_response(config.raw_response_dir, batch_index, response_text)
    return response_rows


def _read_raw_response(raw_response_dir: Path | None, batch_index: int) -> str | None:
    if raw_response_dir is None:
        return None
    response_path = raw_response_dir.expanduser() / f"batch-{batch_index:04d}.json"
    if not response_path.exists():
        return None
    return response_path.read_text(encoding="utf-8")


def _response_rows(response_text: str) -> list[Mapping[str, Any]]:
    payload = orjson.loads(response_text)
    raw_rows = payload.get("rows") if isinstance(payload, Mapping) else payload
    if raw_rows is None and isinstance(payload, Mapping):
        return [payload]
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        raise ValueError("work classification response must contain a rows array")
    return [cast(Mapping[str, Any], row) for row in raw_rows if isinstance(row, Mapping)]


def _merge_generated_rows(
    *,
    input_rows: Sequence[Mapping[str, str]],
    response_rows: Sequence[Mapping[str, Any]],
    model: str,
    run_id: str,
) -> list[dict[str, str]]:
    response_by_work_id = {
        str(row.get("work_id") or "").strip(): row
        for row in response_rows
        if str(row.get("work_id") or "").strip()
    }
    merged_rows: list[dict[str, str]] = []
    for index, input_row in enumerate(input_rows):
        work_id = str(input_row.get("work_id") or "").strip()
        response_row = response_by_work_id.get(work_id, {})
        if not response_row and len(input_rows) == len(response_rows):
            response_row = response_rows[index]
        merged = {
            field: str(input_row.get(field, "") or "") for field in CLASSIFICATION_INPUT_FIELDS
        }
        for field in GENERATED_CLASSIFICATION_FIELDS:
            merged[field] = _generated_field_value(response_row, field)
        _normalize_discovery_fields(merged)
        _derive_legacy_classification_fields(merged)
        merged["classification_scope"] = _normalize_scope(
            language=str(input_row.get("language") or ""),
            scope=merged["classification_scope"],
            category=merged["classification_category"],
        )
        merged["classification_generator_models"] = model
        merged["classification_generator_run_id"] = run_id
        merged_rows.append(merged)
    return merged_rows


def _generated_value(row: Mapping[str, Any], field: str) -> Any:
    if field in row:
        return row.get(field)
    nested = row.get("classification")
    if isinstance(nested, Mapping):
        nested_value = _generated_value(cast(Mapping[str, Any], nested), field)
        if nested_value != "":
            return nested_value
    for alias in CLASSIFICATION_FIELD_ALIASES.get(field, ()):
        if alias in row:
            return row.get(alias)
    return ""


def _generated_field_value(row: Mapping[str, Any], field: str) -> str:
    value = _generated_value(row, field)
    if field == "classification_discovery_tags":
        return discovery_tags_to_csv(value)
    return str(value if value is not None else "").strip()


def _normalize_discovery_fields(row: dict[str, str]) -> None:
    group_id = row.get("classification_discovery_group_id", "").strip()
    if group_id:
        try:
            row["classification_discovery_group_id"] = validate_discovery_group_id(group_id)
        except ValueError:
            row["classification_discovery_group_id"] = _fallback_discovery_group(row)
    tags = row.get("classification_discovery_tags", "").strip()
    if tags:
        try:
            row["classification_discovery_tags"] = validate_discovery_tag_csv(tags)
        except ValueError:
            row["classification_discovery_tags"] = _coerce_discovery_tag_csv(tags)


def _fallback_discovery_group(row: Mapping[str, str]) -> str:
    for tag in normalize_discovery_tags(row.get("classification_discovery_tags", "")):
        if tag in DISCOVERY_GROUPS:
            return tag
    return "other"


def _coerce_discovery_tag_csv(value: object) -> str:
    return "|".join(tag for tag in normalize_discovery_tags(value) if tag in DISCOVERY_TAGS)


def _derive_legacy_classification_fields(row: dict[str, str]) -> None:
    group_id = row.get("classification_discovery_group_id", "").strip()
    group_label = discovery_group_label(group_id)
    if group_label:
        if not row.get("classification_category", "").strip():
            row["classification_category"] = group_label
        if not row.get("classification_scope", "").strip():
            row["classification_scope"] = group_label
    _sync_legacy_field(
        row,
        legacy_field="classification_popularity_score",
        discovery_field="classification_global_popularity_score",
    )
    _sync_legacy_field(
        row,
        legacy_field="classification_popularity_tier",
        discovery_field="classification_global_popularity_tier",
    )
    _sync_legacy_field(
        row,
        legacy_field="classification_scope_popularity_score",
        discovery_field="classification_group_popularity_score",
    )
    _sync_legacy_field(
        row,
        legacy_field="classification_scope_popularity_tier",
        discovery_field="classification_group_popularity_tier",
    )


def _sync_legacy_field(
    row: dict[str, str],
    *,
    legacy_field: str,
    discovery_field: str,
) -> None:
    discovery_value = row.get(discovery_field, "").strip()
    if discovery_value or not row.get(legacy_field, "").strip():
        row[legacy_field] = discovery_value


def _normalize_scope(*, language: str, scope: str, category: str) -> str:
    clean_scope = scope.strip()
    if not clean_scope:
        return ""
    values = LANGUAGE_SCOPE_VALUES.get(language, ())
    if clean_scope in values:
        return clean_scope
    lowered = _scope_key(clean_scope)
    category_key = _scope_key(category)
    haystack = f"{lowered} {category_key}"
    if language == "grc":
        return _controlled_scope(language, _normalize_greek_scope(clean_scope, haystack))
    if language == "lat":
        return _controlled_scope(language, _normalize_latin_scope(clean_scope, haystack))
    if language == "san":
        return _controlled_scope(language, _normalize_sanskrit_scope(clean_scope, haystack))
    return clean_scope


def _controlled_scope(language: str, scope: str) -> str:
    if scope in LANGUAGE_SCOPE_VALUES.get(language, ()):
        return scope
    if language == "grc":
        return "Other Greek Literature"
    if language == "lat":
        return "Other Latin Literature"
    if language == "san":
        return "Other Sanskrit Literature"
    return scope


def _scope_key(value: str) -> str:
    return (
        value.casefold()
        .replace("&", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace("-", " ")
        .replace(",", " ")
        .replace(".", " ")
    )


def _normalize_greek_scope(original: str, haystack: str) -> str:
    return _first_matching_scope(original, haystack, GREEK_SCOPE_RULES)


def _normalize_latin_scope(original: str, haystack: str) -> str:
    return _first_matching_scope(original, haystack, LATIN_SCOPE_RULES)


def _normalize_sanskrit_scope(original: str, haystack: str) -> str:
    return _first_matching_scope(original, haystack, SANSKRIT_SCOPE_RULES)


def _first_matching_scope(original: str, haystack: str, rules: Sequence[ScopeRule]) -> str:
    for needles, scope in rules:
        if any(needle in haystack for needle in needles):
            return scope
    return original


def _has_generated_metadata(row: Mapping[str, str]) -> bool:
    return any(str(row.get(field) or "").strip() for field in GENERATED_CLASSIFICATION_FIELDS[:-2])


def _generated_metadata_count(rows: Sequence[Mapping[str, str]]) -> int:
    return sum(_has_generated_metadata(row) for row in rows)


def _complete_generated_metadata_count(rows: Sequence[Mapping[str, str]]) -> int:
    return sum(_has_complete_generated_metadata(row) for row in rows)


def _has_complete_generated_metadata(row: Mapping[str, str]) -> bool:
    return _has_generated_metadata(row) and bool(str(row.get("classification_notes") or "").strip())


def _batches(rows: Sequence[dict[str, str]], batch_size: int) -> list[list[dict[str, str]]]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    return [list(rows[index : index + batch_size]) for index in range(0, len(rows), batch_size)]
