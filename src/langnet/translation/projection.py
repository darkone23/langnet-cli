from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, cast

from langnet.execution.source_text import display_text, source_segments_from_text
from langnet.parsing.english_gloss_parser import parse_english_glosses
from langnet.translation.cache import TranslationCache, TranslationCacheKey, build_translation_key
from langnet.translation.prompts import BASE_SYSTEM, default_hints_for_language

_DICO_SOURCE_RE = re.compile(r"#(?P<entry>[^:]+):(?P<occurrence>\d+)$")


@dataclass(frozen=True, slots=True)
class TranslationSource:
    source_lexicon: str
    entry_id: str
    occurrence: int
    source_ref: str
    source_tool: str


@dataclass(frozen=True, slots=True)
class TranslationProjection:
    key: TranslationCacheKey
    source: TranslationSource
    lexeme_anchor: str
    sense_anchor: str


def _int_value(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return default


def translation_source_from_evidence(
    evidence: Mapping[str, Any],
) -> TranslationSource | None:
    """Recover the translation-cache source identity from DICO/Gaffiot evidence."""
    source_tool = evidence.get("source_tool")
    source_ref = evidence.get("source_ref")
    if not isinstance(source_tool, str) or not isinstance(source_ref, str):
        return None

    if source_tool == "gaffiot":
        _, _, entry_id = source_ref.partition(":")
        if not entry_id:
            return None
        return TranslationSource(
            source_lexicon="gaffiot",
            entry_id=entry_id,
            occurrence=_int_value(evidence.get("variant_num")),
            source_ref=source_ref,
            source_tool=source_tool,
        )

    if source_tool == "dico":
        match = _DICO_SOURCE_RE.search(source_ref)
        if not match:
            return None
        return TranslationSource(
            source_lexicon="dico",
            entry_id=match.group("entry"),
            occurrence=int(match.group("occurrence")),
            source_ref=source_ref,
            source_tool=source_tool,
        )

    return None


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
    if evidence.get("source_lang") != "fr":
        return None
    source = translation_source_from_evidence(evidence)
    if source is None:
        return None

    key = build_translation_key(
        source_lexicon=source.source_lexicon,
        entry_id=source.entry_id,
        occurrence=source.occurrence,
        headword_norm=lexeme_anchor.removeprefix("lex:"),
        source_text=source_text,
        model=model,
        prompt=BASE_SYSTEM,
        hint=hint,
    )
    return TranslationProjection(
        key=key,
        source=source,
        lexeme_anchor=lexeme_anchor,
        sense_anchor=sense_anchor,
    )


def _translated_triples(
    *,
    projection: TranslationProjection,
    translated_text: str,
    model: str,
) -> list[dict[str, Any]]:
    key = projection.key
    source = projection.source
    translated_sense_anchor = _translation_sense_anchor(
        projection.lexeme_anchor,
        key.translation_id,
        translated_text,
    )
    parsed_glosses = parse_english_glosses(translated_text)
    translated_segments = source_segments_from_text(
        translated_text,
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
            "object": translated_text,
            "metadata": {
                "evidence": translated_evidence,
                "source_lang": "en",
                "source_ref": source.source_ref,
                "display_gloss": display_text(translated_text),
                "parsed_glosses": parsed_glosses,
                "translated_segments": translated_segments,
                "translation_id": key.translation_id,
                "translated_from": projection.sense_anchor,
            },
        },
    ]


def project_cached_translations(
    *,
    claims: Sequence[Mapping[str, Any]],
    language: str,
    model: str,
    cache: TranslationCache,
) -> list[Mapping[str, Any]]:
    """Add cached English translation triples for DICO/Gaffiot French gloss triples."""
    projected = cast(list[dict[str, Any]], deepcopy([dict(claim) for claim in claims]))
    hint = "\n".join(default_hints_for_language(language))

    for claim in projected:
        mutable_triples = _mutable_triples_from_claim(claim)
        if mutable_triples is None:
            continue
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
            if projection is None or projection.key.translation_id in existing_ids:
                continue
            record = cache.get(projection.key)
            if record is None or record.status != "ok" or not record.translated_text:
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
