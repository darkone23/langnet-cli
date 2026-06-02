from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

BRIEFING_FLOW_SCHEMA_VERSION = "langnet.encounter_briefing.flow.v1"
BRIEFING_BATCH_SCHEMA_VERSION = "langnet.encounter_briefing.batch.v1"
BRIEFING_SUMMARY_SCHEMA_VERSION = "langnet.encounter_briefing.summary.v1"
BRIEFING_PROMPT_VERSION = "encounter-briefing-v1"
DEFAULT_ENCOUNTER_BRIEFING_MODEL = "openai:qwen/qwen3.7-max"
BRIEFING_SHORT_MAX_CHARS = 220
BRIEFING_REQUIRED_FIELDS = (
    "schema_version",
    "short",
    "forms",
    "meanings",
    "grammar_functions",
    "word_decomposition",
    "reader_usages",
    "phrase_pairs",
    "dictionary_sources",
    "caveats",
)
BRIEFING_LIST_FIELDS = (
    "forms",
    "meanings",
    "grammar_functions",
    "word_decomposition",
    "reader_usages",
    "phrase_pairs",
    "dictionary_sources",
    "caveats",
)
BRIEFING_OBJECT_LIST_FIELDS = (
    "meanings",
    "grammar_functions",
    "word_decomposition",
    "reader_usages",
    "phrase_pairs",
)
BRIEFING_MEANING_REQUIRED_FIELDS = (
    "summary",
    "source_glosses",
    "source_gloss_language",
    "translation_status",
    "sources",
    "translation_sources",
    "source_refs",
)
BRIEFING_DECOMPOSITION_REQUIRED_FIELDS = ("form", "lemma", "analysis", "source")
TRANSLATION_PIPELINE_POLICY = {
    "output_language": "en",
    "source_gloss_policy": "copy-exact",
    "summary_policy": "english-paraphrase-from-evidence",
}
_CITATION_ONLY_RE = re.compile(
    r"^[A-ZΑ-ΩŚṢṚṄÑ][\w.'’/-]*\.\s+.*\b(?:\d+|[ivxlcdm]+)\b",
    re.IGNORECASE,
)
_GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
_CITATION_TAIL_RE = re.compile(r",\s*(?:LXX|Act\.|Ev\.|Ep\.|Cic\.|Od\.|Il\.|Hdt\.|IG|ib\.).*$")
_MORPH_GLOSS_FRAGMENT_RE = re.compile(
    r"^(?:with\s+)?(?:dat|gen|acc|nom|voc|neut|masc|fem)\.?\b", re.IGNORECASE
)


def build_encounter_briefing_flow(
    encounter_payload: Mapping[str, Any],
    *,
    model: str = DEFAULT_ENCOUNTER_BRIEFING_MODEL,
    max_meanings: int = 6,
    max_reader_usages: int = 4,
    max_source_refs: int = 12,
) -> dict[str, Any]:
    """Build the input -> prompt -> constrained-output contract for one encounter."""
    digest = build_encounter_briefing_digest(
        encounter_payload,
        max_meanings=max_meanings,
        max_reader_usages=max_reader_usages,
        max_source_refs=max_source_refs,
    )
    return {
        "schema_version": BRIEFING_FLOW_SCHEMA_VERSION,
        "digest": digest,
        "generation": {
            "status": "not_requested",
            "model": model,
            "prompt_version": BRIEFING_PROMPT_VERSION,
            "summary_schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
        },
        "prompt": briefing_prompt(digest),
        "output_contract": briefing_output_contract(),
        "draft_output": deterministic_briefing_summary(digest),
    }


def build_encounter_briefing_batch(
    encounter_payloads: Sequence[Mapping[str, Any]],
    *,
    model: str = DEFAULT_ENCOUNTER_BRIEFING_MODEL,
    max_meanings: int = 6,
    max_reader_usages: int = 4,
    max_source_refs: int = 12,
) -> dict[str, Any]:
    """Build a compact quality report over multiple encounter briefing flows."""
    items = []
    for index, payload in enumerate(encounter_payloads):
        flow = build_encounter_briefing_flow(
            payload,
            model=model,
            max_meanings=max_meanings,
            max_reader_usages=max_reader_usages,
            max_source_refs=max_source_refs,
        )
        digest = _mapping(flow.get("digest"))
        draft = _mapping(flow.get("draft_output"))
        items.append(
            {
                "index": index,
                "query": _string(digest.get("query")),
                "language": _string(digest.get("language")),
                "encounter_hash": _string(digest.get("encounter_hash")),
                "meaning_count": len(_mapping_list(digest.get("meanings"))),
                "morphology_count": len(_mapping_list(digest.get("morphology"))),
                "reader_usage_count": len(_mapping_list(digest.get("reader_usages"))),
                "phrase_pair_count": len(_mapping_list(digest.get("phrase_pairs"))),
                "word_decomposition_count": len(_mapping_list(digest.get("word_decomposition"))),
                "quality_flags": _quality_flags(digest, draft),
                "draft_short": _string(draft.get("short")),
            }
        )
    return {
        "schema_version": BRIEFING_BATCH_SCHEMA_VERSION,
        "summary": _batch_summary(items),
        "items": items,
    }


def apply_briefing_model_response(
    flow: Mapping[str, Any],
    response_text: str,
) -> dict[str, Any]:
    """Attach a model response to a briefing flow after JSON parsing and validation."""
    output = dict(flow)
    generation = dict(_mapping(flow.get("generation")))
    generation["raw_response"] = response_text
    parsed = _parse_model_response_json(response_text)
    if parsed is None:
        generation["status"] = "invalid_json"
        generation["validation_issues"] = [
            _issue("invalid_json", "model_response", "Model response was not valid JSON")
        ]
        output["generation"] = generation
        output["model_output"] = None
        output["final_output"] = flow.get("draft_output")
        return output

    digest = _mapping(flow.get("digest"))
    issues = validate_briefing_summary(parsed, digest)
    generation["validation_issues"] = issues
    generation["validation_issue_count"] = len(issues)
    output["model_output"] = parsed
    if issues:
        generation["status"] = "rejected"
        output["final_output"] = flow.get("draft_output")
    else:
        generation["status"] = "accepted"
        output["final_output"] = parsed
    output["generation"] = generation
    return output


def briefing_cache_key(flow: Mapping[str, Any]) -> str:
    digest = _mapping(flow.get("digest"))
    prompt = _mapping(flow.get("prompt"))
    generation = _mapping(flow.get("generation"))
    material = {
        "encounter_hash": _string(digest.get("encounter_hash")),
        "model": _string(generation.get("model")),
        "prompt_version": _string(generation.get("prompt_version")),
        "summary_schema_version": _string(generation.get("summary_schema_version")),
        "prompt_hash": _stable_hash(prompt),
    }
    digest_value = _stable_hash(material)[:32]
    return f"eb:{digest_value}"


def load_cached_briefing_flow(
    cache_dir: Path | str, flow: Mapping[str, Any]
) -> dict[str, Any] | None:
    path = _briefing_cache_path(cache_dir, flow)
    if not path.exists():
        return None
    try:
        cached = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    if not isinstance(cached, Mapping):
        return None
    output = dict(cast(Mapping[str, Any], cached))
    generation = dict(_mapping(output.get("generation")))
    generation["cached_status"] = _string(generation.get("status"))
    generation["status"] = "cache_hit"
    generation["cache_key"] = briefing_cache_key(flow)
    output["generation"] = generation
    return output


def store_cached_briefing_flow(cache_dir: Path | str, flow: Mapping[str, Any]) -> Path:
    path = _briefing_cache_path(cache_dir, flow)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(flow, ensure_ascii=False, sort_keys=True, indent=2))
    return path


def _briefing_cache_path(cache_dir: Path | str, flow: Mapping[str, Any]) -> Path:
    cache_key = briefing_cache_key(flow).replace(":", "_")
    return Path(cache_dir) / f"{cache_key}.json"


def build_encounter_briefing_digest(
    encounter_payload: Mapping[str, Any],
    *,
    max_meanings: int = 6,
    max_reader_usages: int = 4,
    max_source_refs: int = 12,
) -> dict[str, Any]:
    display = _mapping(encounter_payload.get("display"))
    request = _mapping(encounter_payload.get("request"))
    meanings = _display_meanings(display) or _bucket_meanings(encounter_payload)
    reader_usages = _reader_usages(encounter_payload, max_items=max_reader_usages)
    source_refs = _source_refs(meanings, max_items=max_source_refs)
    forms = _forms(display, encounter_payload)
    morphology_rows = _morphology(display)
    return {
        "schema_version": "langnet.encounter_briefing.digest.v1",
        "translation_pipeline": TRANSLATION_PIPELINE_POLICY,
        "encounter_schema_version": _string(encounter_payload.get("schema_version")),
        "encounter_hash": _stable_hash(encounter_payload),
        "query": _string(encounter_payload.get("query")),
        "language": _string(encounter_payload.get("language")),
        "tool_filter": _string(request.get("tool_filter")),
        "forms": forms,
        "lexeme_anchors": _string_list(encounter_payload.get("lexeme_anchors")),
        "morphology": _morphology_for_forms(morphology_rows, forms),
        "word_decomposition": _word_decomposition(morphology_rows, forms),
        "meanings": meanings[:max_meanings],
        "reader_usages": reader_usages,
        "phrase_pairs": _phrase_pairs(meanings[:max_meanings]),
        "source_refs": source_refs,
        "warnings": _string_list(encounter_payload.get("warnings")),
        "limits": {
            "max_meanings": max_meanings,
            "max_reader_usages": max_reader_usages,
            "max_source_refs": max_source_refs,
        },
    }


def briefing_prompt(digest: Mapping[str, Any]) -> dict[str, str]:
    digest_json = json.dumps(digest, ensure_ascii=False, sort_keys=True, indent=2)
    contract_json = json.dumps(briefing_output_contract(), ensure_ascii=False, sort_keys=True)
    return {
        "prompt_version": BRIEFING_PROMPT_VERSION,
        "system": (
            "You write concise classical-language word briefings for a reader sidebar. "
            "All generated prose must be English. Use only the provided encounter digest. "
            "Do not invent references, works, "
            "dictionary sources, morphology, or meanings. If evidence is thin or ambiguous, "
            "say so in caveats. Do not infer definitions from lemma names or morphology rows. "
            "Paraphrase only in summary, short, note, and caveat fields; copy evidence fields "
            "exactly from the digest. Treat source-language dictionary text as evidence to "
            "translate or explain in English, not as final reader prose. "
            "Return only JSON matching the requested schema."
        ),
        "user": (
            "Summarize this clicked reader word for a learner. Keep it compact enough for "
            "an inline sidebar.\n\nEncounter digest:\n"
            f"{digest_json}\n\n"
            "Output contract:\n"
            f"{contract_json}\n\n"
            f"Use schema_version exactly {BRIEFING_SUMMARY_SCHEMA_VERSION}. "
            "Write short, summary, note, and caveat text in English. Use source_glosses only "
            "for exact values copied from digest.meanings[].gloss; you may paraphrase those "
            "glosses only in meaning.summary. Translate source-language glosses into English "
            "only in meaning.summary, and preserve source_gloss_language plus translation_status. "
            "If a morphology row lacks a corresponding meaning, mention that in caveats instead "
            "of supplying a gloss. Use word_decomposition only for possible segmentation or "
            "sub-word analysis; do not treat decomposition rows as the clicked word's meaning. "
            "grammar_functions items must be JSON objects copied from digest.morphology with "
            "summary, form, lemma, analysis, foster_display, and source; never return strings "
            "there. "
            "word_decomposition items must be JSON objects copied from digest.word_decomposition "
            "with form, lemma, analysis, source, and an English note; never return strings there. "
            "Each meaning must include summary, source_glosses, source_gloss_language, "
            "translation_status, sources, translation_sources, and source_refs. "
            "Use phrase_pairs for source-backed example phrases; gloss may be empty when the "
            "digest only has an untranslated phrase. Use dictionary_sources from "
            "digest.meanings[].sources "
            "and digest.morphology[].source; do not derive dictionary names from source_ref "
            "prefixes unless that source id is also present in those fields."
        ),
    }


def briefing_output_contract() -> dict[str, Any]:
    return {
        "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
        "required_fields": list(BRIEFING_REQUIRED_FIELDS),
        "rules": [
            "Generated prose must be English.",
            "summary, short, note, and caveat fields may paraphrase.",
            "Do not use free-form string arrays for meanings, grammar_functions, "
            "word_decomposition, reader_usages, or phrase_pairs.",
            "Evidence fields must be copied exactly from the digest.",
            "Evidence fields include source_glosses, source_refs, forms, grammar analysis, "
            "reader labels/snippets, phrase text, and source ids.",
            "Every reader, phrase, or dictionary reference must come from digest fields.",
            "Use compact learner prose; keep short under 220 characters.",
            "Do not choose one morphology analysis as certain when several remain possible.",
            "Use schema_version exactly langnet.encounter_briefing.summary.v1.",
            "Do not infer meanings from lemma names or morphology rows.",
            "Use word_decomposition only to explain possible segmentation, not lexical meaning.",
            "Prefer source-backed glosses, with reliable English paraphrase in summaries.",
        ],
        "field_shapes": {
            "meanings[]": {
                "summary": "English paraphrase",
                "source_glosses": ["exact digest.meanings[].gloss values"],
                "source_gloss_language": "exact digest.meanings[].source_gloss_language",
                "translation_status": "exact digest.meanings[].translation_status",
                "sources": ["exact digest.meanings[].sources values"],
                "translation_sources": ["exact digest.meanings[].translation_sources values"],
                "source_refs": ["exact digest.meanings[].source_refs values"],
            },
            "grammar_functions[]": {
                "summary": "English paraphrase of the analysis",
                "form": "exact digest.morphology[].form",
                "lemma": "exact digest.morphology[].lemma",
                "analysis": "exact digest.morphology[].analysis",
                "foster_display": "exact digest.morphology[].foster_display",
                "source": "exact digest.morphology[].source",
            },
            "word_decomposition[]": {
                "form": "exact digest.word_decomposition[].form",
                "lemma": "exact digest.word_decomposition[].lemma",
                "analysis": "exact digest.word_decomposition[].analysis",
                "source": "exact digest.word_decomposition[].source",
                "note": "English note; do not treat as the clicked word meaning",
            },
            "reader_usages[]": {
                "label": "exact digest.reader_usages[].label",
                "snippet": "exact digest.reader_usages[].snippet",
                "note": "English note",
            },
            "phrase_pairs[]": {
                "phrase": "exact digest.phrase_pairs[].phrase",
                "gloss": "exact digest.phrase_pairs[].gloss",
                "source": "exact digest.phrase_pairs[].source",
                "source_ref": "exact digest.phrase_pairs[].source_ref",
                "note": "English note",
            },
        },
    }


def deterministic_briefing_summary(digest: Mapping[str, Any]) -> dict[str, Any]:
    meanings = [_summary_meaning(item) for item in _mapping_list(digest.get("meanings"))]
    morphology = _mapping_list(digest.get("morphology"))
    reader_usages = [
        {
            "label": _string(item.get("label")),
            "snippet": _string(item.get("snippet")),
            "note": "",
        }
        for item in _mapping_list(digest.get("reader_usages"))
    ]
    dictionary_sources = sorted(
        {
            source
            for meaning in _mapping_list(digest.get("meanings"))
            for source in _string_list(meaning.get("sources"))
        }
    )
    caveats = []
    if any(
        _string(item.get("confidence")) == "single-witness"
        for item in _mapping_list(digest.get("meanings"))
    ):
        caveats.append("Some meanings are supported by a single witness.")
    warnings = _string_list(digest.get("warnings"))
    caveats.extend(warnings[:2])
    return {
        "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
        "short": _draft_short(digest, meanings),
        "forms": _string_list(digest.get("forms")),
        "meanings": meanings,
        "grammar_functions": [
            {
                "summary": _string(item.get("foster_display")) or _string(item.get("analysis")),
                "form": _string(item.get("form")),
                "lemma": _string(item.get("lemma")),
                "analysis": _string(item.get("analysis")),
                "foster_display": _string(item.get("foster_display")),
                "source": _string(item.get("source")),
            }
            for item in morphology
        ],
        "word_decomposition": [
            {
                "form": _string(item.get("form")),
                "lemma": _string(item.get("lemma")),
                "analysis": _string(item.get("analysis")),
                "source": _string(item.get("source")),
                "note": "Possible decomposition or alternate segment from the analyzer.",
            }
            for item in _mapping_list(digest.get("word_decomposition"))
        ],
        "reader_usages": reader_usages,
        "phrase_pairs": [
            {
                "phrase": _string(item.get("phrase")),
                "gloss": _string(item.get("gloss")),
                "source": _string(item.get("source")),
                "source_ref": _string(item.get("source_ref")),
                "note": "",
            }
            for item in _mapping_list(digest.get("phrase_pairs"))
        ],
        "dictionary_sources": dictionary_sources,
        "caveats": caveats,
    }


def _draft_short(digest: Mapping[str, Any], meanings: Sequence[Mapping[str, Any]]) -> str:
    query = _string(digest.get("query")) or "This word"
    glosses = [
        _string(item.get("summary")) for item in meanings[:3] if _string(item.get("summary"))
    ]
    if not glosses:
        return f"{query}: no compact source-backed meaning was available in this encounter."
    return _compact_text(f"{query}: " + "; ".join(glosses), max_chars=BRIEFING_SHORT_MAX_CHARS)


def _compact_text(value: str, *, max_chars: int) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip(" ,;:") + "..."


def _summary_meaning(item: Mapping[str, Any]) -> dict[str, Any]:
    gloss = _string(item.get("gloss"))
    summary = _draft_summary_gloss(gloss)
    return {
        "summary": summary,
        "source_glosses": [gloss] if gloss else [],
        "source_gloss_language": _string(item.get("source_gloss_language")),
        "translation_status": _string(item.get("translation_status")),
        "sources": _string_list(item.get("sources")),
        "translation_sources": _string_list(item.get("translation_sources")),
        "confidence": _string(item.get("confidence")),
        "source_refs": _string_list(item.get("source_refs")),
    }


def _draft_summary_gloss(gloss: str) -> str:
    text = " ".join(gloss.split())
    if not text:
        return ""

    cleaned_parts = [cleaned for part in text.split(";") if (cleaned := _draft_summary_part(part))]
    if not cleaned_parts:
        return _compact_text(text, max_chars=90)
    return _compact_text("; ".join(cleaned_parts), max_chars=120)


def _draft_summary_part(part: str) -> str:
    text = re.sub(r"^\s*[IVXLCDM]+\.\s*", "", part.strip(), flags=re.IGNORECASE)
    if _GREEK_RE.match(text) and "," not in text:
        return ""
    text = _strip_greek_example_tail(text)
    text = _CITATION_TAIL_RE.sub("", text)
    text = re.sub(r",\s*(?:al\.|etc\.)\s*$", "", text)
    pieces = [piece for raw_piece in text.split(",") if (piece := _draft_summary_piece(raw_piece))]
    return ", ".join(pieces)


def _strip_greek_example_tail(text: str) -> str:
    match = re.search(r",\s*[\u0370-\u03ff\u1f00-\u1fff]", text)
    if not match:
        return text
    prefix = text[: match.start()]
    if re.search(r"[A-Za-z]", prefix):
        return prefix
    return text


def _draft_summary_piece(piece: str) -> str:
    text = piece.strip()
    if not text:
        return ""
    if _MORPH_GLOSS_FRAGMENT_RE.search(text):
        return ""
    if _GREEK_RE.search(text) and not re.search(r"[A-Za-z]", text):
        return ""
    return text


def _quality_flags(digest: Mapping[str, Any], draft: Mapping[str, Any]) -> list[str]:
    flags: list[str] = []
    meanings = _mapping_list(digest.get("meanings"))
    if not meanings:
        flags.append("no_meanings")
    if any(_string(item.get("translation_status")) == "translation-derived" for item in meanings):
        flags.append("translation_derived")
    if any(_string(item.get("confidence")) == "single-witness" for item in meanings):
        flags.append("single_witness")
    if _mapping_list(digest.get("word_decomposition")):
        flags.append("has_word_decomposition")
    if not _mapping_list(digest.get("reader_usages")):
        flags.append("no_reader_usages")
    if _mapping_list(digest.get("phrase_pairs")):
        flags.append("has_phrase_pairs")
    if _draft_has_raw_source_noise(draft):
        flags.append("raw_source_noise")
    if _needs_llm_summary(flags, draft):
        flags.append("needs_llm_summary")
    return flags


def _draft_has_raw_source_noise(draft: Mapping[str, Any]) -> bool:
    short = _string(draft.get("short"))
    if len(short) > BRIEFING_SHORT_MAX_CHARS:
        return True
    return bool(re.search(r"\b(?:Cic|Hdt|IG|ib|cf)\.", short))


def _needs_llm_summary(flags: Sequence[str], draft: Mapping[str, Any]) -> bool:
    if _string(draft.get("short")).endswith("..."):
        return True
    return bool(
        set(flags)
        & {
            "translation_derived",
            "has_phrase_pairs",
            "has_word_decomposition",
            "raw_source_noise",
        }
    )


def _batch_summary(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_language: dict[str, int] = {}
    flag_counts: dict[str, int] = {}
    for item in items:
        language = _string(item.get("language")) or "unknown"
        by_language[language] = by_language.get(language, 0) + 1
        for flag in _string_list(item.get("quality_flags")):
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
    return {
        "total": len(items),
        "by_language": dict(sorted(by_language.items())),
        "flag_counts": dict(sorted(flag_counts.items())),
    }


def _parse_model_response_json(response_text: str) -> Mapping[str, Any] | None:
    text = response_text.strip()
    if text.startswith("```"):
        text = _strip_markdown_json_fence(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    return cast(Mapping[str, Any], payload)


def _strip_markdown_json_fence(text: str) -> str:
    lines = text.splitlines()
    if not lines or not lines[0].strip().startswith("```"):
        return text
    if lines and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text


@dataclass(frozen=True)
class _BriefingValidationContext:
    forms: set[str]
    meaning_glosses: set[str]
    meaning_sources: set[str]
    morphology_sources: set[str]
    sources: set[str]
    source_refs: set[str]
    grammar: set[tuple[str, str, str]]
    word_decomposition: set[tuple[str, str, str, str]]
    reader_usages: set[tuple[str, str]]
    phrase_pairs: set[tuple[str, str, str, str]]
    source_gloss_languages: set[str]
    translation_statuses: set[str]


def validate_briefing_summary(
    summary: Mapping[str, Any], digest: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Validate that copyable briefing fields are grounded in the encounter digest."""
    issues: list[dict[str, str]] = []
    _validate_summary_shape(issues, summary)
    if _string(summary.get("schema_version")) != BRIEFING_SUMMARY_SCHEMA_VERSION:
        issues.append(
            _issue(
                "invalid_schema_version",
                "schema_version",
                f"schema_version must be {BRIEFING_SUMMARY_SCHEMA_VERSION}",
            )
        )
    context = _briefing_validation_context(digest)
    _validate_summary_forms(issues, summary, context)
    _validate_summary_meanings(issues, summary, context)
    _validate_summary_grammar(issues, summary, context)
    _validate_summary_word_decomposition(issues, summary, context)
    _validate_summary_reader_usages(issues, summary, context)
    _validate_summary_phrase_pairs(issues, summary, context)
    _validate_sources(
        issues,
        _string_list(summary.get("dictionary_sources")),
        context.sources,
        "dictionary_sources",
    )
    return issues


def _validate_summary_shape(issues: list[dict[str, str]], summary: Mapping[str, Any]) -> None:
    for field in BRIEFING_REQUIRED_FIELDS:
        if field not in summary:
            issues.append(_issue("missing_required_field", field, field))
    for field in BRIEFING_LIST_FIELDS:
        if field in summary and not isinstance(summary.get(field), list):
            issues.append(_issue("invalid_field_type", field, f"{field} must be a list"))
    for field in BRIEFING_OBJECT_LIST_FIELDS:
        value = summary.get(field)
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                issues.append(
                    _issue(
                        "invalid_item_type",
                        f"{field}[{index}]",
                        f"{field} items must be objects",
                    )
                )
    _validate_meaning_shape(issues, summary)
    _validate_decomposition_shape(issues, summary)


def _validate_meaning_shape(issues: list[dict[str, str]], summary: Mapping[str, Any]) -> None:
    for index, item in enumerate(_mapping_list(summary.get("meanings"))):
        for field in BRIEFING_MEANING_REQUIRED_FIELDS:
            if field not in item:
                issues.append(
                    _issue(
                        "missing_meaning_field",
                        f"meanings[{index}].{field}",
                        field,
                    )
                )


def _validate_decomposition_shape(issues: list[dict[str, str]], summary: Mapping[str, Any]) -> None:
    for index, item in enumerate(_mapping_list(summary.get("word_decomposition"))):
        for field in BRIEFING_DECOMPOSITION_REQUIRED_FIELDS:
            if field not in item:
                issues.append(
                    _issue(
                        "missing_word_decomposition_field",
                        f"word_decomposition[{index}].{field}",
                        field,
                    )
                )


def _briefing_validation_context(digest: Mapping[str, Any]) -> _BriefingValidationContext:
    meaning_rows = _mapping_list(digest.get("meanings"))
    morphology_rows = _mapping_list(digest.get("morphology"))
    decomposition_rows = _mapping_list(digest.get("word_decomposition"))
    reader_rows = _mapping_list(digest.get("reader_usages"))
    phrase_rows = _mapping_list(digest.get("phrase_pairs"))
    meaning_sources = {
        source for item in meaning_rows for source in _string_list(item.get("sources"))
    }
    morphology_sources = {
        _string(item.get("source")) for item in morphology_rows if _string(item.get("source"))
    }
    source_refs = set(_string_list(digest.get("source_refs")))
    source_refs.update(
        ref for item in meaning_rows for ref in _string_list(item.get("source_refs"))
    )
    source_refs.update(_string(item.get("source_ref")) for item in phrase_rows)
    source_refs.discard("")
    return _BriefingValidationContext(
        forms=set(_string_list(digest.get("forms"))),
        meaning_glosses={_string(item.get("gloss")) for item in meaning_rows},
        meaning_sources=meaning_sources,
        morphology_sources=morphology_sources,
        sources=meaning_sources | morphology_sources,
        source_refs=source_refs,
        grammar={
            (
                _string(item.get("form")),
                _string(item.get("analysis")),
                _string(item.get("source")),
            )
            for item in morphology_rows
        },
        word_decomposition={
            (
                _string(item.get("form")),
                _string(item.get("lemma")),
                _string(item.get("analysis")),
                _string(item.get("source")),
            )
            for item in decomposition_rows
        },
        reader_usages={
            (_string(item.get("label")), _string(item.get("snippet"))) for item in reader_rows
        },
        phrase_pairs={
            (
                _string(item.get("phrase")),
                _string(item.get("gloss")),
                _string(item.get("source")),
                _string(item.get("source_ref")),
            )
            for item in phrase_rows
        },
        source_gloss_languages={
            _string(item.get("source_gloss_language"))
            for item in meaning_rows
            if _string(item.get("source_gloss_language"))
        },
        translation_statuses={
            _string(item.get("translation_status"))
            for item in meaning_rows
            if _string(item.get("translation_status"))
        },
    )


def _validate_summary_forms(
    issues: list[dict[str, str]],
    summary: Mapping[str, Any],
    context: _BriefingValidationContext,
) -> None:
    for index, form in enumerate(_string_list(summary.get("forms"))):
        if context.forms and form not in context.forms:
            issues.append(_issue("unsupported_form", f"forms[{index}]", form))


def _validate_summary_meanings(
    issues: list[dict[str, str]],
    summary: Mapping[str, Any],
    context: _BriefingValidationContext,
) -> None:
    for index, item in enumerate(_mapping_list(summary.get("meanings"))):
        for gloss in _string_list(item.get("source_glosses")):
            if not _evidence_value_in(gloss, context.meaning_glosses):
                path = f"meanings[{index}].source_glosses"
                issues.append(_issue("unsupported_meaning_gloss", path, gloss))
        _validate_sources(
            issues,
            _string_list(item.get("sources")),
            context.meaning_sources,
            f"meanings[{index}].sources",
        )
        _validate_source_refs(
            issues,
            _string_list(item.get("source_refs")),
            context.source_refs,
            f"meanings[{index}].source_refs",
        )
        source_gloss_language = _string(item.get("source_gloss_language"))
        if source_gloss_language and source_gloss_language not in context.source_gloss_languages:
            issues.append(
                _issue(
                    "unsupported_source_gloss_language",
                    f"meanings[{index}].source_gloss_language",
                    source_gloss_language,
                )
            )
        translation_status = _string(item.get("translation_status"))
        if translation_status and translation_status not in context.translation_statuses:
            issues.append(
                _issue(
                    "unsupported_translation_status",
                    f"meanings[{index}].translation_status",
                    translation_status,
                )
            )


def _validate_summary_grammar(
    issues: list[dict[str, str]],
    summary: Mapping[str, Any],
    context: _BriefingValidationContext,
) -> None:
    for index, item in enumerate(_mapping_list(summary.get("grammar_functions"))):
        form = _string(item.get("form"))
        if context.forms and form and form not in context.forms:
            issues.append(_issue("unsupported_form", f"grammar_functions[{index}].form", form))
        grammar_key = (form, _string(item.get("analysis")), _string(item.get("source")))
        if grammar_key not in context.grammar:
            issues.append(
                _issue(
                    "unsupported_grammar_analysis",
                    f"grammar_functions[{index}]",
                    "grammar evidence must match a digest morphology row",
                )
            )
        _validate_sources(
            issues,
            [_string(item.get("source"))],
            context.morphology_sources,
            f"grammar_functions[{index}].source",
        )


def _validate_summary_word_decomposition(
    issues: list[dict[str, str]],
    summary: Mapping[str, Any],
    context: _BriefingValidationContext,
) -> None:
    for index, item in enumerate(_mapping_list(summary.get("word_decomposition"))):
        decomposition_key = (
            _string(item.get("form")),
            _string(item.get("lemma")),
            _string(item.get("analysis")),
            _string(item.get("source")),
        )
        if decomposition_key not in context.word_decomposition:
            issues.append(
                _issue(
                    "unsupported_word_decomposition",
                    f"word_decomposition[{index}]",
                    "decomposition evidence must match a digest word_decomposition row",
                )
            )


def _validate_summary_reader_usages(
    issues: list[dict[str, str]],
    summary: Mapping[str, Any],
    context: _BriefingValidationContext,
) -> None:
    for index, item in enumerate(_mapping_list(summary.get("reader_usages"))):
        usage_key = (_string(item.get("label")), _string(item.get("snippet")))
        if usage_key not in context.reader_usages:
            issues.append(
                _issue(
                    "unsupported_reader_usage",
                    f"reader_usages[{index}]",
                    "reader usage label and snippet must match digest.reader_usages",
                )
            )


def _validate_summary_phrase_pairs(
    issues: list[dict[str, str]],
    summary: Mapping[str, Any],
    context: _BriefingValidationContext,
) -> None:
    for index, item in enumerate(_mapping_list(summary.get("phrase_pairs"))):
        phrase_key = (
            _string(item.get("phrase")),
            _string(item.get("gloss")),
            _string(item.get("source")),
            _string(item.get("source_ref")),
        )
        if phrase_key not in context.phrase_pairs:
            issues.append(
                _issue(
                    "unsupported_phrase_pair",
                    f"phrase_pairs[{index}]",
                    "phrase, gloss, source, and source_ref must match digest.phrase_pairs",
                )
            )
        _validate_source_refs(
            issues,
            [_string(item.get("source_ref"))],
            context.source_refs,
            f"phrase_pairs[{index}].source_ref",
        )


def _forms(display: Mapping[str, Any], payload: Mapping[str, Any]) -> list[str]:
    header = _mapping(display.get("header"))
    forms = [_clean_form(value) for value in _string_list(header.get("forms"))]
    if forms:
        return _dedupe([form for form in forms if form])
    return [_anchor_tail(anchor) for anchor in _string_list(payload.get("lexeme_anchors"))]


def _morphology_for_forms(
    rows: Sequence[Mapping[str, str]], forms: Sequence[str]
) -> list[dict[str, str]]:
    form_set = set(forms)
    if not form_set:
        return [dict(row) for row in rows]
    return [dict(row) for row in rows if _string(row.get("form")) in form_set]


def _word_decomposition(
    rows: Sequence[Mapping[str, str]], forms: Sequence[str]
) -> list[dict[str, str]]:
    form_set = set(forms)
    if not form_set:
        return []
    return [dict(row) for row in rows if _string(row.get("form")) not in form_set]


def _morphology(display: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _mapping_list(display.get("analysis")):
        rows.append(
            {
                "form": _string(item.get("form")),
                "lemma": _string(item.get("lemma")),
                "analysis": _string(item.get("analysis")),
                "source": _string(item.get("source")),
                "foster_display": _string(item.get("foster_display")),
                "display_text": _string(item.get("display_text")),
            }
        )
    return rows


def _display_meanings(display: Mapping[str, Any]) -> list[dict[str, Any]]:
    meanings: list[dict[str, Any]] = []
    for item in _mapping_list(display.get("meanings")):
        source_summary = _mapping(item.get("source_detail_summary"))
        refs = [
            *_string_list(item.get("source_refs")),
            *_string_list(source_summary.get("source_refs")),
        ]
        meanings.append(
            {
                "bucket_id": _string(item.get("bucket_id")),
                "gloss": _string(item.get("display_gloss")),
                "sources": _string_list(item.get("sources")),
                "source_gloss_language": _source_gloss_language(item),
                "witness_count": _int(item.get("witness_count")),
                "confidence": _string(item.get("confidence_label")),
                "translation_status": _translation_status(item),
                "translation_sources": _string_list(item.get("translation_sources")),
                "source_refs": _dedupe(refs),
                "examples": _string_list(source_summary.get("examples")),
                "cross_refs": _string_list(source_summary.get("cross_refs")),
            }
        )
    return meanings


def _bucket_meanings(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    meanings: list[dict[str, Any]] = []
    for item in _mapping_list(payload.get("buckets")):
        meanings.append(
            {
                "bucket_id": _string(item.get("bucket_id")),
                "gloss": _string(item.get("display_gloss") or item.get("normalized_gloss")),
                "sources": _bucket_sources(item),
                "source_gloss_language": _bucket_source_gloss_language(item),
                "witness_count": len(_mapping_list(item.get("witnesses"))),
                "confidence": _string(item.get("confidence_label")),
                "translation_status": _bucket_translation_status(item),
                "translation_sources": _bucket_translation_sources(item),
                "source_refs": _bucket_source_refs(item),
                "examples": [],
                "cross_refs": [],
            }
        )
    return meanings


def _source_gloss_language(item: Mapping[str, Any]) -> str:
    source_langs = _string_list(item.get("source_langs"))
    if source_langs:
        return source_langs[0]
    if _translation_status(item) == "translation-derived":
        return "unknown-source"
    return "en"


def _translation_status(item: Mapping[str, Any]) -> str:
    sources = set(_string_list(item.get("sources")))
    if _string_list(item.get("translation_sources")) or "translation" in sources:
        return "translation-derived"
    source_langs = {value.lower() for value in _string_list(item.get("source_langs"))}
    if source_langs and source_langs != {"en"}:
        return "source-language"
    return "english-or-unknown"


def _bucket_source_gloss_language(bucket: Mapping[str, Any]) -> str:
    languages = []
    for witness in _mapping_list(bucket.get("witnesses")):
        evidence = _mapping(witness.get("evidence"))
        languages.append(_string(evidence.get("source_lang")))
        languages.append(_string(evidence.get("gloss_lang")))
    values = _dedupe([value for value in languages if value])
    if values:
        return values[0]
    if _bucket_translation_status(bucket) == "translation-derived":
        return "unknown-source"
    return "en"


def _bucket_translation_status(bucket: Mapping[str, Any]) -> str:
    if _bucket_translation_sources(bucket):
        return "translation-derived"
    source_lang = _bucket_source_gloss_language_without_translation_check(bucket)
    if source_lang and source_lang.lower() != "en":
        return "source-language"
    return "english-or-unknown"


def _bucket_source_gloss_language_without_translation_check(bucket: Mapping[str, Any]) -> str:
    for witness in _mapping_list(bucket.get("witnesses")):
        evidence = _mapping(witness.get("evidence"))
        language = _string(evidence.get("gloss_lang")) or _string(evidence.get("source_lang"))
        if language:
            return language
    return ""


def _bucket_translation_sources(bucket: Mapping[str, Any]) -> list[str]:
    sources: list[str] = []
    for witness in _mapping_list(bucket.get("witnesses")):
        evidence = _mapping(witness.get("evidence"))
        if _string(witness.get("source_tool")) == "translation":
            sources.append(_string(evidence.get("source_tool")))
        if _string(evidence.get("source_tool")) == "translation":
            sources.append(_string(evidence.get("source_dictionary")))
        if _string(evidence.get("translation_id")):
            sources.append(_string(evidence.get("source_tool")))
    return _dedupe([source for source in sources if source])


def _bucket_sources(bucket: Mapping[str, Any]) -> list[str]:
    return _dedupe(
        [
            _string(witness.get("source_tool"))
            for witness in _mapping_list(bucket.get("witnesses"))
            if _string(witness.get("source_tool"))
        ]
    )


def _bucket_source_refs(bucket: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for witness in _mapping_list(bucket.get("witnesses")):
        evidence = _mapping(witness.get("evidence"))
        refs.append(_string(evidence.get("source_ref")))
    return _dedupe(refs)


def _reader_usages(payload: Mapping[str, Any], *, max_items: int) -> list[dict[str, str]]:
    reader_search = _mapping(payload.get("reader_search"))
    usages: list[dict[str, str]] = []
    for item in _mapping_list(reader_search.get("items"))[:max_items]:
        author = _string(item.get("author"))
        title = _string(item.get("title"))
        citation = _string(item.get("citation_path"))
        label = ", ".join(part for part in (author, title) if part)
        if citation:
            label = f"{label} {citation}".strip()
        usages.append(
            {
                "work_id": _string(item.get("work_id")),
                "label": label,
                "citation_path": citation,
                "snippet": _string(item.get("snippet") or item.get("text")),
            }
        )
    return usages


def _source_refs(meanings: Sequence[Mapping[str, Any]], *, max_items: int) -> list[str]:
    refs: list[str] = []
    for meaning in meanings:
        refs.extend(_string_list(meaning.get("source_refs")))
    return _dedupe(refs)[:max_items]


def _phrase_pairs(meanings: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    for meaning in meanings:
        source = _first(_string_list(meaning.get("sources")))
        source_ref = _first(_string_list(meaning.get("source_refs")))
        for example in _string_list(meaning.get("examples")):
            if _is_citation_only_example(example):
                continue
            phrase, gloss = _split_phrase_pair(example)
            pairs.append(
                {
                    "phrase": phrase,
                    "gloss": gloss,
                    "source": source,
                    "source_ref": source_ref,
                }
            )
    return _dedupe_phrase_pairs(pairs)


def _is_citation_only_example(value: str) -> bool:
    if "=>" in value or "->" in value:
        return False
    return bool(_CITATION_ONLY_RE.search(value.strip()))


def _split_phrase_pair(value: str) -> tuple[str, str]:
    for delimiter in ("=>", "->"):
        if delimiter in value:
            phrase, gloss = value.split(delimiter, 1)
            return phrase.strip(), gloss.strip()
    return value.strip(), ""


def _dedupe_phrase_pairs(values: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str]] = set()
    output: list[dict[str, str]] = []
    for item in values:
        key = (
            _string(item.get("phrase")),
            _string(item.get("gloss")),
            _string(item.get("source")),
            _string(item.get("source_ref")),
        )
        if key[0] and key not in seen:
            seen.add(key)
            output.append(
                {
                    "phrase": key[0],
                    "gloss": key[1],
                    "source": key[2],
                    "source_ref": key[3],
                }
            )
    return output


def _validate_sources(
    issues: list[dict[str, str]],
    values: Sequence[str],
    allowed_sources: set[str],
    path: str,
) -> None:
    for value in values:
        if value and value not in allowed_sources:
            issues.append(_issue("unsupported_dictionary_source", path, value))


def _validate_source_refs(
    issues: list[dict[str, str]],
    values: Sequence[str],
    allowed_refs: set[str],
    path: str,
) -> None:
    for value in values:
        if value and value not in allowed_refs:
            issues.append(_issue("unsupported_source_ref", path, value))


def _evidence_value_in(value: str, allowed_values: set[str]) -> bool:
    if value in allowed_values:
        return True
    normalized = _evidence_normalized(value)
    return any(_evidence_normalized(allowed) == normalized for allowed in allowed_values)


def _evidence_normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", unicodedata.normalize("NFC", value))


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _stable_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [cast(Mapping[str, Any], item) for item in value if isinstance(item, Mapping)]


def _string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_string(item) for item in value if _string(item)]


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return 0


def _first(values: Sequence[str]) -> str:
    return values[0] if values else ""


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _anchor_tail(value: str) -> str:
    tail = value.rsplit(":", 1)[-1]
    return _clean_form(tail)


def _clean_form(value: str) -> str:
    return value.rsplit(":", 1)[-1].split("#", 1)[0].strip()
