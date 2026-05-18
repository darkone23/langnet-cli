from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import orjson

from langnet.execution.source_text import display_text, trim_empty

TRANSLATION_BLOCKS_SCHEMA_VERSION = "langnet.translation.blocks.v1"
TRANSLATION_BLOCKS_REQUEST_SCHEMA_VERSION = "langnet.translation.blocks.request.v1"
ABBREVIATION_FUZZY_PREFIX_DELTA = 2
STRUCTURED_TRANSLATION_MAX_BLOCKS_PER_REQUEST = 3
STRUCTURED_TRANSLATION_MAX_CHARS_PER_REQUEST = 900
_GREEK_TOKEN_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]+")
_ABBREVIATION_RE = re.compile(r"\b[^\W\d_][^\W_]*\.", re.UNICODE)
_FRENCH_RESIDUE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE | re.UNICODE)
    for pattern in (
        r"\bparole\b",
        r"\braison\b",
        r"\braisonner\b",
        r"\bfacult[ée]\s+de\b",
        r"\bd[’']o[uù]\b",
        r"\bce\s+qu[’']on\b",
        r"\bdans\s+l[’']",
        r"\bprendre\s+la\b",
        r"\bavec\s+rai-\s*son\b",
        r"\bselon\s+la\b",
        r"\b[eê]tre\s+conforme\b",
        r"\bcomme\s+cela\b",
        r"\bsans\s+aucune\b",
        r"\bd[’']apr[eè]s\b",
        r"\bbonne\s+opinion\b",
        r"\bestime\b",
        r"\bfaire\s+cas\b",
        r"\bne\s+faire\s+aucun\s+cas\b",
        r"\bcompte\s+qu[’']on\b",
        r"\bqqn\b",
        r"\bqqe\s+ch\b",
        r"\ben\s+g[ée]n\b",
        r"\bp\.\s+suite\b",
        r"\bp\.\s+ext\b",
        r"\bparticul\b",
        r"\bpropr\b",
        r"\bau\s+sens\b",
        r"\btra-?\s*ditions\s+historiques\b",
    )
]


class StructuredTranslationError(ValueError):
    """Raised when a structured translation cannot be aligned to source blocks."""


@dataclass(frozen=True, slots=True)
class CachedTranslationContent:
    text: str
    translated_blocks: list[dict[str, Any]]


def requires_structured_translation(projection: object) -> bool:
    source = getattr(projection, "source", None)
    source_lexicon = getattr(source, "source_lexicon", "")
    source_blocks = getattr(projection, "source_blocks", [])
    return source_lexicon == "bailly" and bool(_body_blocks(source_blocks))


def structured_translation_user_content(projection: object) -> str:
    """Build the JSON request body sent to the model for block-preserving translation."""
    source = getattr(projection, "source", None)
    payload = {
        "schema_version": TRANSLATION_BLOCKS_REQUEST_SCHEMA_VERSION,
        "source_lexicon": getattr(source, "source_lexicon", ""),
        "entry_id": getattr(source, "entry_id", ""),
        "source_ref": getattr(source, "source_ref", ""),
        "target_lang": "en",
        "blocks": [
            {
                "path": str(block["path"]),
                "text": str(block["text"]),
            }
            for block in _body_blocks(getattr(projection, "source_blocks", []))
        ],
    }
    return orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def structured_translation_system_hint() -> str:
    return (
        "Return a JSON object with schema_version langnet.translation.blocks.v1 and "
        "a blocks array. Each block has the same path as the request block and a text "
        "field containing the English translation for that block. Preserve block order, "
        "sense boundaries, casing, punctuation, source-language tokens, abbreviations, "
        "spacing inside each block, and line-level structure. Translate French prose "
        "in each block into English using only meanings present in the source entry. "
        "Copy Greek text, Latin citations, author abbreviations, work abbreviations, "
        "book numbers, section numbers, and punctuation exactly as they appear. Render "
        "compact French labels and abbreviations into compact English labels: Postér. "
        "=> Later; c. => with; c. à d. => i.e.; comme => as; synon. => syn.; "
        "dureté => hardness; insensibilité => insensibility; rocher => rock; "
        "rhéteur => rhetorician; apôtre => apostle; particul. => in particular; "
        "propr. => properly; en gén. => in general; p. suite => by extension; "
        "p. ext. => by extension; p. opp. à => opposed to."
    )


def normalize_translation_response(projection: object, response_text: str) -> str:
    text = response_text.strip()
    if not requires_structured_translation(projection):
        return text
    source_blocks = _body_blocks(getattr(projection, "source_blocks", []))
    try:
        payload = _parse_json_object(text)
    except StructuredTranslationError as exc:
        if len(source_blocks) != 1 or "not JSON" not in str(exc) or not text:
            raise
        payload = {
            "blocks": [
                {
                    "path": str(source_blocks[0]["path"]),
                    "text": text,
                }
            ]
        }
    schema_version = payload.get("schema_version")
    accepted_schema_versions = {
        None,
        TRANSLATION_BLOCKS_SCHEMA_VERSION,
        TRANSLATION_BLOCKS_REQUEST_SCHEMA_VERSION,
    }
    if schema_version not in accepted_schema_versions:
        raise StructuredTranslationError(
            "Bailly translation response used an unexpected schema_version"
        )
    raw_blocks = payload.get("blocks")
    if not isinstance(raw_blocks, Sequence) or isinstance(raw_blocks, (str, bytes)):
        raise StructuredTranslationError("Bailly translation response has no blocks array")
    output_blocks = [
        cast(Mapping[str, Any], block) for block in raw_blocks if isinstance(block, Mapping)
    ]
    expected_paths = [str(block["path"]) for block in source_blocks]
    received_paths = [str(block.get("path") or "") for block in output_blocks]
    if received_paths != expected_paths and not _can_repair_echoed_paths_by_position(
        expected_paths,
        received_paths,
    ):
        raise StructuredTranslationError(
            "Bailly translation block paths changed: "
            f"expected {expected_paths!r}, received {received_paths!r}"
        )

    translated_blocks: list[dict[str, Any]] = []
    for source_block, output_block in zip(source_blocks, output_blocks, strict=True):
        translated_text = output_block.get("text")
        if not isinstance(translated_text, str) or not translated_text.strip():
            raise StructuredTranslationError(
                f"Bailly translation block {source_block['path']} has no translated text"
            )
        restored_text = _restore_source_tokens(
            str(source_block.get("text") or ""),
            translated_text.strip(),
        )
        restored_text = _repair_known_bailly_header(
            source_text=str(source_block.get("text") or ""),
            translated_text=restored_text,
        )
        _validate_translated_french_residue(
            path=str(source_block["path"]),
            source_text=str(source_block.get("text") or ""),
            translated_text=restored_text,
        )
        translated_block = dict(source_block)
        translated_block["source_text"] = str(source_block.get("text") or "")
        translated_block["text"] = restored_text
        translated_blocks.append(trim_empty(translated_block))

    payload = {
        "schema_version": TRANSLATION_BLOCKS_SCHEMA_VERSION,
        "text": "\n".join(str(block["text"]) for block in translated_blocks),
        "blocks": translated_blocks,
    }
    return orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def structured_translation_source_batches(
    source_blocks: object,
    *,
    max_blocks: int = STRUCTURED_TRANSLATION_MAX_BLOCKS_PER_REQUEST,
    max_chars: int = STRUCTURED_TRANSLATION_MAX_CHARS_PER_REQUEST,
) -> list[list[Mapping[str, Any]]]:
    body_blocks = _body_blocks(source_blocks)
    if not body_blocks:
        return []

    batches: list[list[Mapping[str, Any]]] = []
    current: list[Mapping[str, Any]] = []
    current_chars = 0
    for block in body_blocks:
        block_chars = len(str(block.get("text") or ""))
        if current and (len(current) >= max_blocks or current_chars + block_chars > max_chars):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(block)
        current_chars += block_chars
    if current:
        batches.append(current)
    return batches


def source_text_from_blocks(source_blocks: Sequence[Mapping[str, Any]]) -> str:
    return " ".join(
        str(block.get("text") or "").strip()
        for block in source_blocks
        if str(block.get("text") or "").strip()
    )


def merge_cached_translation_texts(translated_texts: Sequence[str]) -> str:
    translated_blocks: list[dict[str, Any]] = []
    for translated_text in translated_texts:
        content = decode_cached_translation_text(translated_text)
        translated_blocks.extend(content.translated_blocks)
    payload = {
        "schema_version": TRANSLATION_BLOCKS_SCHEMA_VERSION,
        "text": "\n".join(str(block["text"]) for block in translated_blocks),
        "blocks": translated_blocks,
    }
    return orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def decode_cached_translation_text(translated_text: str) -> CachedTranslationContent:
    text = translated_text.strip()
    if not text.startswith("{"):
        return CachedTranslationContent(text=text, translated_blocks=[])
    try:
        payload = orjson.loads(text)
    except orjson.JSONDecodeError:
        return CachedTranslationContent(text=text, translated_blocks=[])
    if not isinstance(payload, Mapping):
        return CachedTranslationContent(text=text, translated_blocks=[])
    if payload.get("schema_version") != TRANSLATION_BLOCKS_SCHEMA_VERSION:
        return CachedTranslationContent(text=text, translated_blocks=[])
    display = payload.get("text")
    raw_blocks = payload.get("blocks")
    translated_blocks = (
        [dict(cast(Mapping[str, Any], block)) for block in raw_blocks if isinstance(block, Mapping)]
        if isinstance(raw_blocks, Sequence) and not isinstance(raw_blocks, (str, bytes))
        else []
    )
    if not isinstance(display, str):
        display = "\n".join(
            str(block.get("text") or "").strip()
            for block in translated_blocks
            if str(block.get("text") or "").strip()
        )
    return CachedTranslationContent(text=display.strip(), translated_blocks=translated_blocks)


def translated_segments_from_blocks(
    translated_blocks: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for block in translated_blocks:
        text = block.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        segment = {
            "index": len(segments),
            "raw_text": text.strip(),
            "display_text": display_text(text),
            "segment_type": "translated_gloss_segment",
            "labels": ["translation", "parsed_gloss"],
            "source_ref": block.get("source_ref"),
            "source_path": block.get("path"),
            "source_marker": block.get("marker"),
            "source_level": block.get("level"),
            "parent_path": block.get("parent_path"),
        }
        segments.append(trim_empty(segment))
    return segments


def _parse_json_object(text: str) -> Mapping[str, Any]:
    json_text = _extract_json_object_text(text)
    try:
        payload = orjson.loads(json_text)
    except orjson.JSONDecodeError as exc:
        raise StructuredTranslationError("Bailly translation response is not JSON") from exc
    if not isinstance(payload, Mapping):
        raise StructuredTranslationError("Bailly translation response is not a JSON object")
    return cast(Mapping[str, Any], payload)


def _can_repair_echoed_paths_by_position(
    expected_paths: Sequence[str],
    received_paths: Sequence[str],
) -> bool:
    if len(expected_paths) != len(received_paths):
        return False
    path_pairs = zip(expected_paths, received_paths, strict=True)
    mismatches = [
        index for index, (expected, received) in enumerate(path_pairs) if expected != received
    ]
    if len(mismatches) != 1:
        return False
    mismatch = mismatches[0]
    expected_root = expected_paths[mismatch].split(":", 1)[0]
    received = received_paths[mismatch].strip()
    return bool(received) and received.split(":", 1)[0] == expected_root


def _extract_json_object_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped
    start = stripped.find("{")
    if start < 0:
        return stripped
    end = _json_object_end(stripped, start)
    return stripped[start:end] if end is not None else stripped[start:]


def _json_object_end(text: str, start: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = in_string
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def _restore_source_tokens(source_text: str, translated_text: str) -> str:
    return _restore_source_citation_abbreviations(
        source_text,
        _restore_source_greek_tokens(source_text, translated_text),
    )


def _validate_translated_french_residue(
    *,
    path: str,
    source_text: str,
    translated_text: str,
) -> None:
    source_probe = _french_residue_probe(source_text)
    translated_probe = _french_residue_probe(translated_text)
    if not source_probe or not translated_probe:
        return
    if _compact_probe(source_probe) == _compact_probe(translated_probe) and _has_french_residue_cue(
        source_probe
    ):
        raise StructuredTranslationError(f"Bailly translation block {path} appears untranslated")
    for pattern in _FRENCH_RESIDUE_PATTERNS:
        if pattern.search(source_probe) and pattern.search(translated_probe):
            raise StructuredTranslationError(
                f"Bailly translation block {path} kept French dictionary prose"
            )


def _has_french_residue_cue(text: str) -> bool:
    return any(pattern.search(text) for pattern in _FRENCH_RESIDUE_PATTERNS)


def _repair_known_bailly_header(*, source_text: str, translated_text: str) -> str:
    if _compact_probe(_french_residue_probe(source_text)) != _compact_probe(
        _french_residue_probe(translated_text)
    ):
        return translated_text
    match = re.fullmatch(r"(\s*)parole(\s*:\s*)", translated_text, re.IGNORECASE)
    if match is None:
        return translated_text
    return f"{match.group(1)}speech{match.group(2)}"


def _french_residue_probe(text: str) -> str:
    return text.replace("’", "'").replace("œ", "oe").replace("Œ", "oe").lower()


def _compact_probe(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _restore_source_greek_tokens(source_text: str, translated_text: str) -> str:
    source_tokens = _GREEK_TOKEN_RE.findall(source_text)
    translated_matches = list(_GREEK_TOKEN_RE.finditer(translated_text))
    if not source_tokens or not translated_matches:
        return translated_text

    translated_chars = list(translated_text)
    search_from = 0
    for source_token in source_tokens:
        source_key = _greek_token_key(source_token)
        for match_index in range(search_from, len(translated_matches)):
            translated_token = translated_matches[match_index].group(0)
            if _greek_token_key(translated_token) != source_key:
                continue
            start, end = translated_matches[match_index].span()
            translated_chars[start:end] = list(source_token)
            search_from = match_index + 1
            break
    return "".join(translated_chars)


def _restore_source_citation_abbreviations(source_text: str, translated_text: str) -> str:
    source_tokens = _ABBREVIATION_RE.findall(source_text)
    if not source_tokens:
        return translated_text
    used: set[int] = set()

    def replace(match: re.Match[str]) -> str:
        translated_token = match.group(0)
        for index, source_token in enumerate(source_tokens):
            if index in used:
                continue
            if _abbreviation_keys_match(source_token, translated_token):
                used.add(index)
                return source_token
        return translated_token

    return _ABBREVIATION_RE.sub(replace, translated_text)


def _abbreviation_keys_match(source_token: str, translated_token: str) -> bool:
    source_key = _abbreviation_key(source_token)
    translated_key = _abbreviation_key(translated_token)
    if not source_key or not translated_key:
        return False
    if source_key == translated_key:
        return True
    if (
        source_key.startswith(translated_key)
        and len(source_key) - len(translated_key) <= ABBREVIATION_FUZZY_PREFIX_DELTA
    ):
        return True
    return (
        translated_key.startswith(source_key)
        and len(translated_key) - len(source_key) <= ABBREVIATION_FUZZY_PREFIX_DELTA
    )


def _abbreviation_key(token: str) -> str:
    key = _strip_combining_marks(token.casefold()).replace(".", "")
    if key.startswith("ae"):
        key = key[1:]
    return key


def _greek_token_key(token: str) -> str:
    return _strip_combining_marks(token.casefold())


def _strip_combining_marks(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _body_blocks(source_blocks: object) -> list[Mapping[str, Any]]:
    if not isinstance(source_blocks, Sequence) or isinstance(source_blocks, (str, bytes)):
        return []
    blocks = [
        cast(Mapping[str, Any], block) for block in source_blocks if isinstance(block, Mapping)
    ]
    return [
        block
        for block in blocks
        if block.get("kind") != "head"
        and isinstance(block.get("path"), str)
        and isinstance(block.get("text"), str)
        and str(block.get("text")).strip()
    ]
