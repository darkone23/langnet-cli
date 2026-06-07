from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, cast

from langnet.execution.source_text import display_text, source_segments_from_text
from langnet.parsing.english_gloss_parser import parse_english_glosses
from langnet.translation.cache import (
    TranslationCache,
    TranslationCacheKey,
    TranslationRecord,
    build_translation_key,
)
from langnet.translation.prompts import BASE_SYSTEM, default_hints_for_language
from langnet.translation.structured import (
    StructuredTranslationError,
    decode_cached_translation_text,
    merge_cached_translation_texts,
    normalize_translation_response,
    requires_structured_translation,
    source_text_from_blocks,
    structured_translation_source_batches,
    translated_segments_from_blocks,
)

_DICO_SOURCE_RE = re.compile(r"#(?P<entry>[^:]+):(?P<occurrence>\d+)$")
STRUCTURED_TRANSLATION_MAX_ATTEMPTS = 3
UNSTRUCTURED_SEGMENT_BATCH_MAX_CHARS = 900
UNSTRUCTURED_SEGMENT_BATCH_MAX_SEGMENTS = 8
UNSTRUCTURED_SEGMENTED_MIN_CHARS = 360
STRUCTURED_TRANSLATION_REPAIR_HINT = (
    "The previous Bailly translation response failed validation. Retry from the same source "
    "blocks, return only the requested JSON object, preserve every requested block path, "
    "and translate all ordinary French prose into English. Do not echo French labels or "
    "definitions unless they are source-language tokens that must be preserved."
)


@dataclass(frozen=True, slots=True)
class TranslationSource:
    source_lexicon: str
    entry_id: str
    occurrence: int
    source_ref: str
    source_tool: str
    source_lang: str


@dataclass(frozen=True, slots=True)
class TranslationProjection:
    key: TranslationCacheKey
    source: TranslationSource
    lexeme_anchor: str
    sense_anchor: str
    source_text: str
    hint: str
    source_blocks: list[Mapping[str, Any]]
    source_segments: list[Mapping[str, Any]]


def _int_value(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return default


def translation_source_from_evidence(
    evidence: Mapping[str, Any],
) -> TranslationSource | None:
    """Recover the translation-cache source identity from French lexicon evidence."""
    source_tool = evidence.get("source_tool")
    source_ref = evidence.get("source_ref")
    if not isinstance(source_tool, str) or not isinstance(source_ref, str):
        return None

    source: TranslationSource | None = None
    if source_tool == "gaffiot":
        _, _, entry_id = source_ref.partition(":")
        if entry_id:
            source = TranslationSource(
                source_lexicon="gaffiot",
                entry_id=entry_id,
                occurrence=_int_value(evidence.get("variant_num")),
                source_ref=source_ref,
                source_tool=source_tool,
                source_lang=str(evidence.get("source_lang") or "fr"),
            )

    elif source_tool == "dico":
        match = _DICO_SOURCE_RE.search(source_ref)
        if match:
            source = TranslationSource(
                source_lexicon="dico",
                entry_id=match.group("entry"),
                occurrence=int(match.group("occurrence")),
                source_ref=source_ref,
                source_tool=source_tool,
                source_lang=str(evidence.get("source_lang") or "fr"),
            )

    elif source_tool == "bailly":
        _, _, entry_id = source_ref.partition(":")
        if entry_id:
            source = TranslationSource(
                source_lexicon="bailly",
                entry_id=entry_id,
                occurrence=_int_value(evidence.get("occurrence")),
                source_ref=source_ref,
                source_tool=source_tool,
                source_lang=str(evidence.get("source_lang") or "fr"),
            )

    elif source_tool == "georges_1913":
        _, _, rest = source_ref.partition(":")
        entry_id = rest.split("#", 1)[-1].rsplit(":", 1)[0] if rest else ""
        if entry_id:
            source = TranslationSource(
                source_lexicon="georges_1913",
                entry_id=entry_id,
                occurrence=_int_value(evidence.get("occurrence")),
                source_ref=source_ref,
                source_tool=source_tool,
                source_lang=str(evidence.get("source_lang") or "de"),
            )

    return source


def _evidence_from(triple: Mapping[str, Any]) -> dict[str, Any]:
    metadata = triple.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    evidence = metadata.get("evidence")
    payload = dict(evidence) if isinstance(evidence, Mapping) else {}
    for key in ("source_lang", "source_ref", "translation_id"):
        value = metadata.get(key)
        if value and key not in payload:
            payload[key] = value
    return payload


def _triples_from_claim(claim: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = claim.get("value")
    if not isinstance(value, Mapping):
        return []
    triples = value.get("triples")
    if not isinstance(triples, Sequence) or isinstance(triples, (str, bytes)):
        return []
    return [cast(Mapping[str, Any], triple) for triple in triples if isinstance(triple, Mapping)]


def _mutable_triples_from_claim(claim: dict[str, Any]) -> list[Any] | None:
    value = claim.get("value")
    if not isinstance(value, dict):
        return None
    triples = value.get("triples")
    return triples if isinstance(triples, list) else None


def _translation_sense_anchor(lexeme_anchor: str, translation_id: str, translated_text: str) -> str:
    material = f"{translation_id}\x1f{translated_text}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"sense:{lexeme_anchor}#tr-{digest}"


def _existing_translation_ids(triples: Sequence[Mapping[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for triple in triples:
        evidence = _evidence_from(triple)
        translation_id = evidence.get("translation_id")
        if isinstance(translation_id, str):
            ids.add(translation_id)
    return ids


def _sense_links(triples: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    links: dict[str, str] = {}
    for triple in triples:
        if triple.get("predicate") != "has_sense":
            continue
        subject = triple.get("subject")
        obj = triple.get("object")
        if isinstance(subject, str) and isinstance(obj, str):
            links[obj] = subject
    return links


def _projection_for_gloss(
    *,
    triple: Mapping[str, Any],
    sense_links: Mapping[str, str],
    model: str,
    hint: str,
) -> TranslationProjection | None:
    if triple.get("predicate") != "gloss":
        return None
    sense_anchor = triple.get("subject")
    source_text = triple.get("object")
    if not isinstance(sense_anchor, str) or not isinstance(source_text, str):
        return None
    lexeme_anchor = sense_links.get(sense_anchor)
    if lexeme_anchor is None:
        return None

    evidence = _evidence_from(triple)
    if evidence.get("source_lang") not in {"fr", "de"}:
        return None
    source = translation_source_from_evidence(evidence)
    if source is None:
        return None
    metadata = triple.get("metadata")
    metadata_map = metadata if isinstance(metadata, Mapping) else {}
    source_blocks_value = metadata_map.get("source_blocks")
    source_segments_value = metadata_map.get("source_segments")

    key = build_translation_key(
        source_lexicon=source.source_lexicon,
        entry_id=source.entry_id,
        occurrence=source.occurrence,
        headword_norm=lexeme_anchor.removeprefix("lex:"),
        source_text=source_text,
        source_lang=source.source_lang,
        model=model,
        prompt=BASE_SYSTEM,
        hint=hint,
    )
    return TranslationProjection(
        key=key,
        source=source,
        lexeme_anchor=lexeme_anchor,
        sense_anchor=sense_anchor,
        source_text=source_text,
        hint=hint,
        source_blocks=[
            cast(Mapping[str, Any], item)
            for item in source_blocks_value
            if isinstance(item, Mapping)
        ]
        if isinstance(source_blocks_value, Sequence)
        and not isinstance(source_blocks_value, (str, bytes))
        else [],
        source_segments=[
            cast(Mapping[str, Any], item)
            for item in source_segments_value
            if isinstance(item, Mapping)
        ]
        if isinstance(source_segments_value, Sequence)
        and not isinstance(source_segments_value, (str, bytes))
        else [],
    )


def _translation_projections(
    *,
    claims: Sequence[Mapping[str, Any]],
    language: str,
    model: str,
) -> list[TranslationProjection]:
    hint = "\n".join(default_hints_for_language(language))
    projections: list[TranslationProjection] = []
    seen_ids: set[str] = set()

    for claim in claims:
        triples = _triples_from_claim(claim)
        existing_ids = _existing_translation_ids(triples)
        sense_links = _sense_links(triples)

        for triple in triples:
            projection = _projection_for_gloss(
                triple=triple,
                sense_links=sense_links,
                model=model,
                hint=hint,
            )
            if projection is None:
                continue
            translation_id = projection.key.translation_id
            if translation_id in existing_ids or translation_id in seen_ids:
                continue
            projections.append(projection)
            seen_ids.add(translation_id)

    return projections


def populate_missing_translations(  # noqa: PLR0913
    *,
    claims: Sequence[Mapping[str, Any]],
    language: str,
    model: str,
    cache: TranslationCache,
    translate: Callable[[TranslationProjection], str],
    raise_on_error: bool = True,
) -> int:
    """Translate French glosses that are missing from the cache."""
    written = 0
    for projection in _translation_projections(claims=claims, language=language, model=model):
        existing = cache.get(projection.key)
        if _is_usable_translation_record(projection, existing):
            continue

        start = time.perf_counter()
        try:
            translated_text = _translate_projection(projection, translate)
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - start) * 1000)
            cache.upsert(
                TranslationRecord(
                    key=projection.key,
                    translated_text=None,
                    status="error",
                    error=str(exc),
                    duration_ms=duration_ms,
                )
            )
            if raise_on_error:
                raise
            continue

        duration_ms = int((time.perf_counter() - start) * 1000)
        if not translated_text:
            cache.upsert(
                TranslationRecord(
                    key=projection.key,
                    translated_text=None,
                    status="empty",
                    duration_ms=duration_ms,
                )
            )
            continue

        cache.upsert(
            TranslationRecord(
                key=projection.key,
                translated_text=translated_text,
                status="ok",
                duration_ms=duration_ms,
            )
        )
        written += 1
    return written


def _is_usable_translation_record(
    projection: TranslationProjection,
    record: TranslationRecord | None,
) -> bool:
    return (
        record is not None
        and record.status == "ok"
        and bool(record.translated_text)
        and _cached_translation_validation_error(projection, record) is None
    )


def _cached_translation_validation_error(
    projection: TranslationProjection,
    record: TranslationRecord,
) -> str | None:
    if record.status != "ok" or not record.translated_text:
        return None
    if requires_structured_translation(projection):
        return None
    return None


def _translate_projection(
    projection: TranslationProjection,
    translate: Callable[[TranslationProjection], str],
) -> str:
    if not requires_structured_translation(projection):
        if _should_segment_unstructured_projection(projection):
            return _translate_segmented_unstructured_projection(projection, translate)
        return _translate_unstructured_projection_with_retries(projection, translate)

    batches = structured_translation_source_batches(projection.source_blocks)
    if len(batches) <= 1:
        return _translate_structured_projection_with_retries(projection, translate)

    translated_batches = []
    for batch in batches:
        batch_projection = replace(
            projection,
            source_blocks=list(batch),
            source_text=source_text_from_blocks(batch),
        )
        translated_batches.append(
            _translate_structured_projection_with_retries(batch_projection, translate)
        )
    return merge_cached_translation_texts(translated_batches)


def _should_segment_unstructured_projection(projection: TranslationProjection) -> bool:
    if projection.source.source_lexicon not in {"dico", "gaffiot", "georges_1913"}:
        return False
    if len(projection.source_text) < UNSTRUCTURED_SEGMENTED_MIN_CHARS:
        return False
    return len(_translation_source_segment_texts(projection.source_segments)) > 1


def _translate_segmented_unstructured_projection(
    projection: TranslationProjection,
    translate: Callable[[TranslationProjection], str],
) -> str:
    translated_batches: list[str] = []
    for batch in _unstructured_translation_segment_batches(projection.source_segments):
        batch_text = "\n".join(batch)
        batch_projection = replace(projection, source_text=batch_text)
        translated_batches.append(
            _translate_unstructured_projection_with_retries(batch_projection, translate)
        )
    return "\n".join(text for text in translated_batches if text.strip()).strip()


def _unstructured_translation_segment_batches(
    source_segments: Sequence[Mapping[str, Any]],
) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    current_chars = 0
    for text in _translation_source_segment_texts(source_segments):
        projected_chars = current_chars + len(text)
        if current and (
            len(current) >= UNSTRUCTURED_SEGMENT_BATCH_MAX_SEGMENTS
            or projected_chars > UNSTRUCTURED_SEGMENT_BATCH_MAX_CHARS
        ):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(text)
        current_chars += len(text)
    if current:
        batches.append(current)
    return batches


def _translation_source_segment_texts(
    source_segments: Sequence[Mapping[str, Any]],
) -> list[str]:
    texts: list[str] = []
    for segment in source_segments:
        raw_text = segment.get("raw_text")
        display = segment.get("display_text")
        text = raw_text if isinstance(raw_text, str) and raw_text.strip() else display
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
    return texts


def _translate_unstructured_projection_with_retries(
    projection: TranslationProjection,
    translate: Callable[[TranslationProjection], str],
) -> str:
    return normalize_translation_response(projection, translate(projection))


def _translate_structured_projection_with_retries(
    projection: TranslationProjection,
    translate: Callable[[TranslationProjection], str],
) -> str:
    last_error: Exception | None = None
    for attempt in range(STRUCTURED_TRANSLATION_MAX_ATTEMPTS):
        try:
            active_projection = (
                projection
                if attempt == 0
                else replace(
                    projection,
                    hint=(
                        f"{projection.hint}\n\n{STRUCTURED_TRANSLATION_REPAIR_HINT}\n"
                        f"Validation failure to repair: {last_error}"
                    ),
                )
            )
            return normalize_translation_response(
                active_projection,
                translate(active_projection),
            )
        except (StructuredTranslationError, ValueError) as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def translation_cache_status_counts(
    *,
    claims: Sequence[Mapping[str, Any]],
    language: str,
    model: str,
    cache: TranslationCache,
) -> dict[str, int]:
    """Count cache status for translatable French gloss projections."""
    counts = {"total": 0, "hits": 0, "missing": 0, "errors": 0, "empty": 0}
    for projection in _translation_projections(claims=claims, language=language, model=model):
        counts["total"] += 1
        record = cache.get(projection.key)
        if record is None:
            counts["missing"] += 1
        elif record.status == "ok" and record.translated_text:
            if _cached_translation_validation_error(projection, record):
                counts["errors"] += 1
            else:
                counts["hits"] += 1
        elif record.status == "empty":
            counts["empty"] += 1
        else:
            counts["errors"] += 1
    return counts


def _translated_triples(
    *,
    projection: TranslationProjection,
    translated_text: str,
    model: str,
) -> list[dict[str, Any]]:
    key = projection.key
    source = projection.source
    cached_translation = decode_cached_translation_text(translated_text)
    display_translation = cached_translation.text
    translated_sense_anchor = _translation_sense_anchor(
        projection.lexeme_anchor,
        key.translation_id,
        display_translation,
    )
    parsed_glosses = parse_english_glosses(display_translation)
    translated_segments = translated_segments_from_blocks(cached_translation.translated_blocks)
    if not translated_segments:
        translated_segments = source_segments_from_text(
            display_translation,
            segment_type="translated_gloss_segment",
            labels=["translation", "parsed_gloss"],
        )
    translated_evidence = {
        "source_tool": "translation",
        "source_lexicon": source.source_lexicon,
        "source_ref": source.source_ref,
        "source_text_hash": key.source_text_hash,
        "source_lang": key.target_lang,
        "source_text_lang": key.source_lang,
        "gloss_lang": key.target_lang,
        "target_lang": key.target_lang,
        "translation_id": key.translation_id,
        "model": model,
        "prompt_hash": key.prompt_hash,
        "hint_hash": key.hint_hash,
        "derived_from_tool": source.source_tool,
        "derived_from_sense": projection.sense_anchor,
        "parsed_glosses": parsed_glosses,
        "translated_segments": translated_segments,
        "translated_blocks": cached_translation.translated_blocks,
        "source_blocks": projection.source_blocks,
        "source_segments": projection.source_segments,
        "raw_blob_ref": "entry_translations",
    }
    return [
        {
            "subject": projection.lexeme_anchor,
            "predicate": "has_sense",
            "object": translated_sense_anchor,
            "metadata": {
                "evidence": translated_evidence,
                "translation_id": key.translation_id,
            },
        },
        {
            "subject": translated_sense_anchor,
            "predicate": "gloss",
            "object": display_translation,
            "metadata": {
                "evidence": translated_evidence,
                "source_lang": "en",
                "source_ref": source.source_ref,
                "display_gloss": display_text(display_translation),
                "parsed_glosses": parsed_glosses,
                "translated_segments": translated_segments,
                "translated_blocks": cached_translation.translated_blocks,
                "translation_id": key.translation_id,
                "translated_from": projection.sense_anchor,
            },
        },
    ]


def _translation_state(
    *,
    projection: TranslationProjection,
    record: TranslationRecord | None,
    model: str,
) -> dict[str, Any]:
    key = projection.key
    if record is None:
        status = "missing"
        error = ""
    elif record.status == "empty":
        status = "empty"
        error = record.error or ""
    else:
        status = "error"
        error = record.error or ""
    state: dict[str, Any] = {
        "available": False,
        "status": status,
        "translation_id": key.translation_id,
        "source_lexicon": projection.source.source_lexicon,
        "source_text_lang": key.source_lang,
        "target_lang": key.target_lang,
        "model": model,
        "source_text_hash": key.source_text_hash,
        "derived_from_tool": projection.source.source_tool,
        "derived_from_sense": projection.sense_anchor,
        "raw_blob_ref": "entry_translations",
    }
    if error:
        state["error"] = error
    return state


def _annotate_source_translation_state(
    *,
    triples: list[Any],
    projection: TranslationProjection,
    record: TranslationRecord | None,
    model: str,
) -> None:
    for triple in triples:
        if not isinstance(triple, dict):
            continue
        if triple.get("predicate") != "gloss":
            continue
        if triple.get("subject") != projection.sense_anchor:
            continue
        if triple.get("object") != projection.source_text:
            continue
        metadata = triple.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            continue
        evidence = metadata.setdefault("evidence", {})
        if not isinstance(evidence, dict):
            continue
        evidence["translation_state"] = _translation_state(
            projection=projection,
            record=record,
            model=model,
        )
        return


def project_cached_translations(
    *,
    claims: Sequence[Mapping[str, Any]],
    language: str,
    model: str,
    cache: TranslationCache,
) -> list[Mapping[str, Any]]:
    """Add cached English translation triples for French gloss triples."""
    projected = cast(list[dict[str, Any]], deepcopy([dict(claim) for claim in claims]))
    for claim in projected:
        mutable_triples = _mutable_triples_from_claim(claim)
        if mutable_triples is None:
            continue
        triples = _triples_from_claim(claim)
        existing_ids = _existing_translation_ids(triples)

        claim_projections = _translation_projections(
            claims=[claim],
            language=language,
            model=model,
        )
        for projection in claim_projections:
            if projection is None or projection.key.translation_id in existing_ids:
                continue
            record = cache.get(projection.key)
            validation_error = (
                _cached_translation_validation_error(projection, record)
                if record is not None
                else None
            )
            if (
                record is None
                or record.status != "ok"
                or not record.translated_text
                or validation_error
            ):
                state_record = record
                if validation_error and record is not None:
                    state_record = TranslationRecord(
                        key=record.key,
                        translated_text=None,
                        status="error",
                        error=validation_error,
                        duration_ms=record.duration_ms,
                    )
                _annotate_source_translation_state(
                    triples=mutable_triples,
                    projection=projection,
                    record=state_record,
                    model=model,
                )
                continue

            mutable_triples.extend(
                _translated_triples(
                    projection=projection,
                    translated_text=record.translated_text,
                    model=model,
                )
            )
            existing_ids.add(projection.key.translation_id)

    return [cast(Mapping[str, Any], claim) for claim in projected]
