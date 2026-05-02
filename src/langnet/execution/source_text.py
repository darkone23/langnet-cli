from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

from langnet.parsing.source_entry_analysis import parse_source_entry

_SEGMENT_SPLIT_RE = re.compile(r"\s+\|\|+\s+|[;\n¶]+")
_COMPACT_ENTRY_BREAK_RE = re.compile(r"\s+\|+\s+|\s+—\s+")
_COMPACT_HEADWORD_NUMBER_RE = re.compile(r"\b1\s+([^:;|]{2,120})(?=[:;|])")
_COMPACT_INFLECTION_TAG_RE = re.compile(r"\b(?:sg|pl|nom|acc|gen|dat|abl)\.")
_COMPACT_LEXICAL_PREAMBLE_RE = re.compile(
    r"^(?:[A-Za-zĀ-ž./_-]{1,64}(?:\s+\[[^\]]+\])?,\s*|"
    r"[A-Za-zĀ-ž./_-]{1,64}\s+\[[^\]]+\]\s*)?"
    r"(?:(?:mfn|m|f|n|a|adj|v|adv|pn|pron|part)\.,?\s*)+",
    re.IGNORECASE,
)
_COMPACT_SECTION_PREFIX_RE = re.compile(r"^(?:[IVX]+|[A-Z])\.\s")
COMPACT_GLOSS_DEFAULT_MAX_CHARS = 120
COMPACT_GLOSS_DEFAULT_MAX_ITEMS = 4
COMPACT_GLOSS_MAX_PREFIX_CHARS = 100
COMPACT_GLOSS_MAX_ITEM_WORDS = 5
COMPACT_GLOSS_MIN_ITEMS = 2
_ANALYSIS_PREVIEW_MAX_CHARS = 180
_ANALYSIS_MAX_ITEMS = 12
_EXAMPLE_TEXT_MIN_WORDS = 4
_DEFINITION_SEGMENT_MAX_WORDS = 16
_CLASSICAL_CITATION_RE = re.compile(
    r"\b(?:"
    r"Cic|Verg|Virg|Hor|Liv|Tac|Caes|Cæs|Ov|Ovid|Plin|Ter|Plaut|Sen|Sall|"
    r"Hom|Hdt|Soph|Eur|Arist|Pl|Xen"
    r")\.\s*(?:[A-Z][A-Za-z.]*\s*)?\d+(?:,\s*\d+)*"
)
_BRACKET_REFERENCE_RE = re.compile(r"\[([^\]]{1,64})\]")
_CROSS_REFERENCE_RE = re.compile(r"\b(?:cf|see)\.\s*([^|:\n]+)", re.IGNORECASE)
_SOURCE_ABBREVIATION_RE = re.compile(r"^[A-Za-zĀ-ž][A-Za-zĀ-ž0-9]*\.$")
_EXAMPLE_SPLIT_RE = re.compile(r"\s+\|\|+\s+|:\s+")


def display_text(raw_text: str) -> str:
    """Return a display-safe text form without treating it as a data reduction."""
    return re.sub(r"\s+", " ", raw_text).strip()


def compact_source_gloss(
    raw_text: str,
    *,
    max_chars: int = COMPACT_GLOSS_DEFAULT_MAX_CHARS,
    max_items: int = COMPACT_GLOSS_DEFAULT_MAX_ITEMS,
) -> str:
    """
    Return a compact learner gloss from a dictionary source string.

    This is a conservative display helper: it does not replace source evidence
    and it only uses repeated dictionary-entry structure such as numbered first
    senses, short pre-colon summaries, lexical grammar preambles, and common
    item separators.
    """
    text = display_text(raw_text)
    if not text:
        return ""
    text = re.sub(r"^\d+\.\s+", "", text)
    numbered = _COMPACT_HEADWORD_NUMBER_RE.search(text)
    if numbered and numbered.start() <= COMPACT_GLOSS_MAX_PREFIX_CHARS:
        text = numbered.group(1).strip()
    elif ":" in text and text.index(":") <= COMPACT_GLOSS_MAX_PREFIX_CHARS:
        prefix = text[: text.index(":")].strip()
        suffix = text[text.index(":") + 1 :].strip()
        if _COMPACT_SECTION_PREFIX_RE.match(prefix):
            return _shorten_display(text, max_chars)
        if _looks_like_lexical_header(prefix) and suffix:
            text = _COMPACT_ENTRY_BREAK_RE.split(suffix, maxsplit=1)[0].strip()
        else:
            text = prefix
    else:
        text = _COMPACT_ENTRY_BREAK_RE.split(text, maxsplit=1)[0].strip()
    text = _trim_lexical_preamble(text)
    text = _limit_gloss_items(text, max_items=max_items)
    return _shorten_display(text, max_chars)


def learner_segments_from_text(
    raw_text: str,
    *,
    max_chars: int = COMPACT_GLOSS_DEFAULT_MAX_CHARS,
) -> list[dict[str, object]]:
    """Build typed learner-summary segments while preserving full source text elsewhere."""
    learner_gloss = compact_source_gloss(raw_text, max_chars=max_chars)
    if not learner_gloss:
        return []
    return [
        {
            "index": 0,
            "raw_text": learner_gloss,
            "display_text": learner_gloss,
            "segment_type": "learner_gloss",
            "labels": ["definition", "learner_summary"],
        }
    ]


def source_segments_from_text(
    raw_text: str,
    *,
    segment_type: str = "source_text",
    labels: list[str] | None = None,
) -> list[dict[str, object]]:
    """Conservatively segment source text while preserving the full raw text elsewhere."""
    segments: list[dict[str, object]] = []
    for raw_segment in _SEGMENT_SPLIT_RE.split(raw_text):
        segment = raw_segment.strip()
        if not segment:
            continue
        display = display_text(segment)
        classified_type, classified_labels = _classify_source_segment(
            display,
            default_segment_type=segment_type,
            default_labels=labels or [],
        )
        segments.append(
            {
                "index": len(segments),
                "raw_text": segment,
                "display_text": display,
                "segment_type": classified_type,
                "labels": classified_labels,
            }
        )
    if segments:
        return segments
    stripped = raw_text.strip()
    if not stripped:
        return []
    display = display_text(stripped)
    classified_type, classified_labels = _classify_source_segment(
        display,
        default_segment_type=segment_type,
        default_labels=labels or [],
    )
    return [
        {
            "index": 0,
            "raw_text": stripped,
            "display_text": display,
            "segment_type": classified_type,
            "labels": classified_labels,
        }
    ]


def _classify_source_segment(
    text: str,
    *,
    default_segment_type: str,
    default_labels: list[str],
) -> tuple[str, list[str]]:
    segment_type = default_segment_type
    labels = list(default_labels)
    if "translation" in default_labels:
        return segment_type, labels
    clean = display_text(text).strip(" ;,")
    if re.match(r"^(?:cf|see)\.\s+", clean, re.IGNORECASE):
        segment_type = _classified_segment_type(default_segment_type, "cross_reference_segment")
        labels = _merge_labels(
            default_labels,
            ["cross_reference", "source_reference"],
            replace_definition=True,
        )
    elif _SOURCE_ABBREVIATION_RE.match(clean) or _is_bracket_source_reference_segment(clean):
        segment_type = _classified_segment_type(default_segment_type, "source_reference_segment")
        labels = _merge_labels(
            default_labels,
            ["source_reference"],
            replace_definition=True,
        )
    elif _CLASSICAL_CITATION_RE.search(clean) and _looks_like_example_text(clean):
        segment_type = _classified_segment_type(default_segment_type, "example_segment")
        labels = _merge_labels(
            default_labels,
            ["example", "citation", "source_reference"],
            replace_definition=True,
        )
    elif clean and _is_probable_definition_segment(clean):
        segment_type = _classified_segment_type(default_segment_type, "definition_segment")
        labels = _merge_labels(default_labels, ["definition"])
    return segment_type, labels


def _classified_segment_type(default_segment_type: str, classified_segment_type: str) -> str:
    if default_segment_type in {"dictionary_entry", "dictionary_line"}:
        return default_segment_type
    return classified_segment_type


def _is_bracket_source_reference_segment(text: str) -> bool:
    match = re.fullmatch(r"\[([^\]]{1,64})\]", text)
    return bool(match and _looks_like_source_reference(display_text(match.group(1))))


def _merge_labels(
    base: list[str],
    additions: list[str],
    *,
    replace_definition: bool = False,
) -> list[str]:
    labels = [label for label in base if not (replace_definition and label == "definition")]
    for label in additions:
        if label not in labels:
            labels.append(label)
    return labels


def analyze_source_entry(
    raw_text: str,
    *,
    source_tool: str = "unknown",
    max_items: int = _ANALYSIS_MAX_ITEMS,
) -> dict[str, object]:
    """
    Produce a diagnostic, source-backed analysis of a dictionary entry.

    The result is intentionally heuristic. It is useful for inspecting what the
    current generic text routines can see before a source-specific parser earns
    deeper structure.
    """
    display = display_text(raw_text)
    grammar_parse = parse_source_entry(source_tool, raw_text)
    grammar_definition = _grammar_definition_text(grammar_parse)
    learner_gloss = (
        _shorten_display(grammar_definition, COMPACT_GLOSS_DEFAULT_MAX_CHARS)
        if grammar_definition
        else compact_source_gloss(raw_text)
    )
    learner_segments = learner_segments_from_text(raw_text)
    source_segments = source_segments_from_text(raw_text)
    citations = _citation_items(display, max_items=max_items)
    source_references = _source_reference_items(display, source_segments, max_items=max_items)
    examples = _example_items(
        display,
        citations,
        source_segments,
        grammar_parse,
        max_items=max_items,
    )
    gloss_candidates = _gloss_candidate_items(
        learner_gloss,
        learner_segments,
        source_segments,
        grammar_parse,
        max_items=max_items,
    )
    return trim_empty(
        {
            "source_tool": source_tool,
            "grammar_parse": grammar_parse,
            "display_text": display,
            "learner_gloss": learner_gloss,
            "learner_segments": learner_segments,
            "source_segments": source_segments,
            "gloss_candidates": gloss_candidates,
            "citations": citations,
            "source_references": source_references,
            "examples": examples,
            "counts": {
                "gloss_candidates": len(gloss_candidates),
                "citations": len(citations),
                "source_references": len(source_references),
                "examples": len(examples),
                "source_segments": len(source_segments),
            },
        }
    )


def _trim_lexical_preamble(text: str) -> str:
    return _COMPACT_LEXICAL_PREAMBLE_RE.sub("", text, count=1).strip(" ,;")


def _looks_like_lexical_header(text: str) -> bool:
    return "," in text and any(ch.isalpha() for ch in text)


def _limit_gloss_items(
    text: str,
    *,
    max_items: int = COMPACT_GLOSS_DEFAULT_MAX_ITEMS,
) -> str:
    if "," in text and ";" in text:
        return text
    separator = "; " if ";" in text and "," not in text else ", "
    parts = [part.strip() for part in re.split(r"\s*[,;]\s*", text) if part.strip()]
    if len(parts) <= 1:
        return text
    short_parts = [
        part
        for part in parts
        if len(part.split()) <= COMPACT_GLOSS_MAX_ITEM_WORDS
        and not _COMPACT_INFLECTION_TAG_RE.search(part)
    ]
    if len(short_parts) < COMPACT_GLOSS_MIN_ITEMS:
        return text
    return separator.join(short_parts[:max_items])


def _shorten_display(text: str, max_chars: int) -> str:
    normalized = display_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def _citation_items(text: str, *, max_items: int) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    seen: set[str] = set()
    for match in _CLASSICAL_CITATION_RE.finditer(text):
        value = display_text(match.group(0))
        if value in seen:
            continue
        seen.add(value)
        items.append(
            {
                "text": value,
                "kind": "classical_citation",
                "start": match.start(),
                "end": match.end(),
                "labels": ["citation", "source_reference"],
            }
        )
        if len(items) >= max_items:
            break
    return items


def _source_reference_items(
    text: str,
    source_segments: list[dict[str, object]],
    *,
    max_items: int,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    _append_bracket_references(text, items, seen, max_items=max_items)
    _append_cross_references(text, items, seen, max_items=max_items)
    _append_segment_references(source_segments, items, seen, max_items=max_items)
    return items


def _append_bracket_references(
    text: str,
    items: list[dict[str, object]],
    seen: set[tuple[str, str]],
    *,
    max_items: int,
) -> None:
    for match in _BRACKET_REFERENCE_RE.finditer(text):
        label = display_text(match.group(1)).strip()
        if _looks_like_source_reference(label):
            _append_unique_item((items, seen), label, "bracket_reference", ["source_reference"])
        if len(items) >= max_items:
            return


def _append_cross_references(
    text: str,
    items: list[dict[str, object]],
    seen: set[tuple[str, str]],
    *,
    max_items: int,
) -> None:
    for match in _CROSS_REFERENCE_RE.finditer(text):
        for part in _reference_parts(match.group(1)):
            _append_unique_item(
                (items, seen),
                part,
                "cross_reference",
                ["cross_reference", "source_reference"],
            )
            if len(items) >= max_items:
                return


def _append_segment_references(
    source_segments: list[dict[str, object]],
    items: list[dict[str, object]],
    seen: set[tuple[str, str]],
    *,
    max_items: int,
) -> None:
    for segment in source_segments:
        display = str(segment.get("display_text") or "")
        segment_index = _segment_index(segment, len(items))
        labels = _segment_labels(segment)
        if "source_reference" in labels:
            _append_unique_item(
                (items, seen), display, "typed_source_segment", labels, segment_index
            )
        elif _SOURCE_ABBREVIATION_RE.match(display):
            _append_unique_item(
                (items, seen),
                display,
                "source_abbreviation",
                ["source_reference"],
                segment_index,
            )
        if len(items) >= max_items:
            return


def _append_unique_item(
    state: tuple[list[dict[str, object]], set[tuple[str, str]]],
    value: str,
    kind: str,
    labels: list[str],
    segment_index: int | None = None,
) -> None:
    items, seen = state
    clean = display_text(value).strip(" ;,")
    if not clean:
        return
    key = (kind, clean)
    if key in seen:
        return
    seen.add(key)
    item: dict[str, object] = {"text": clean, "kind": kind, "labels": labels}
    if segment_index is not None:
        item["segment_index"] = segment_index
    items.append(item)


def _example_items(
    text: str,
    citations: list[dict[str, object]],
    source_segments: list[dict[str, object]],
    grammar_parse: Mapping[str, object] | None,
    *,
    max_items: int,
) -> list[dict[str, object]]:
    citation_texts = [str(item["text"]) for item in citations]
    examples: list[dict[str, object]] = []
    seen: set[str] = set()

    _append_grammar_example(examples, seen, citation_texts, grammar_parse)
    _append_split_examples(text, examples, seen, citation_texts, max_items=max_items)
    _append_segment_examples(source_segments, examples, seen, citation_texts, max_items=max_items)
    return examples


def _append_grammar_example(
    examples: list[dict[str, object]],
    seen: set[str],
    citation_texts: list[str],
    grammar_parse: Mapping[str, object] | None,
) -> None:
    grammar_example = _grammar_example_text(grammar_parse)
    if not grammar_example:
        return
    matched_citation = _first_contained(citation_texts, grammar_example)
    examples.append(
        _example_item(
            grammar_example,
            "grammar_example",
            matched_citation,
            labels=["example", "grammar_parse"],
        )
    )
    seen.add(grammar_example)


def _append_split_examples(
    text: str,
    examples: list[dict[str, object]],
    seen: set[str],
    citation_texts: list[str],
    *,
    max_items: int,
) -> None:
    for raw_part in _EXAMPLE_SPLIT_RE.split(text)[1:]:
        example = display_text(raw_part).strip(" ;|")
        matched_citation = _first_contained(citation_texts, example)
        if _should_skip_example(example, seen, matched_citation):
            continue
        seen.add(example)
        examples.append(_example_item(example, "example_candidate", matched_citation))
        if len(examples) >= max_items:
            return


def _append_segment_examples(
    source_segments: list[dict[str, object]],
    examples: list[dict[str, object]],
    seen: set[str],
    citation_texts: list[str],
    *,
    max_items: int,
) -> None:
    for segment in source_segments:
        example = str(segment.get("display_text") or "")
        matched_citation = _first_contained(citation_texts, example)
        if not matched_citation or example in seen:
            continue
        seen.add(example)
        item = _example_item(example, "example_candidate", matched_citation)
        item["segment_index"] = segment.get("index")
        examples.append(item)
        if len(examples) >= max_items:
            return


def _should_skip_example(
    example: str,
    seen: set[str],
    matched_citation: str | None,
) -> bool:
    if not example or example in seen:
        return True
    return matched_citation is None and not _looks_like_example_text(example)


def _example_item(
    text: str,
    kind: str,
    citation: str | None,
    *,
    labels: list[str] | None = None,
) -> dict[str, object]:
    item_labels = list(labels or ["example"])
    item: dict[str, object] = {
        "text": _shorten_display(text, _ANALYSIS_PREVIEW_MAX_CHARS),
        "kind": kind,
        "labels": item_labels,
    }
    if citation:
        item["citation"] = citation
        if "citation" not in item_labels:
            item_labels.insert(1, "citation")
    return item


def _gloss_candidate_items(
    learner_gloss: str,
    learner_segments: list[dict[str, object]],
    source_segments: list[dict[str, object]],
    grammar_parse: Mapping[str, object] | None,
    *,
    max_items: int,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    seen: set[str] = set()

    def add(text: str, kind: str, labels: list[str], segment_index: int | None = None) -> None:
        value = display_text(text)
        if not value or value in seen:
            return
        seen.add(value)
        item: dict[str, object] = {"text": value, "kind": kind, "labels": labels}
        if segment_index is not None:
            item["segment_index"] = segment_index
        items.append(item)

    grammar_definition = _grammar_definition_text(grammar_parse)
    if grammar_definition:
        add(grammar_definition, "grammar_definition", ["definition", "grammar_parse"])
    add(learner_gloss, "learner_gloss", ["definition", "learner_summary"])
    for segment in learner_segments:
        add(
            str(segment.get("display_text") or ""),
            "learner_segment",
            _segment_labels(segment, fallback=["definition"]),
            _segment_index(segment, len(items)),
        )
    for segment in source_segments:
        labels = _segment_labels(segment)
        if "source_reference" in labels or "cross_reference" in labels:
            continue
        display = str(segment.get("display_text") or "")
        if _is_probable_definition_segment(display):
            add(
                _shorten_display(display, _ANALYSIS_PREVIEW_MAX_CHARS),
                "definition_segment",
                ["definition", *labels],
                _segment_index(segment, len(items)),
            )
        if len(items) >= max_items:
            break
    return items[:max_items]


def _grammar_definition_text(grammar_parse: Mapping[str, object] | None) -> str:
    if not grammar_parse or grammar_parse.get("parsed") is not True:
        return ""
    if grammar_parse.get("format") == "gaffiot" and not grammar_parse.get("sense_number"):
        return ""
    value = grammar_parse.get("definition_text")
    return display_text(value) if isinstance(value, str) else ""


def _segment_index(segment: Mapping[str, object], fallback: int) -> int:
    value = segment.get("index")
    if isinstance(value, int):
        return value
    return fallback


def _segment_labels(
    segment: Mapping[str, object],
    *,
    fallback: list[str] | None = None,
) -> list[str]:
    value = segment.get("labels")
    if isinstance(value, list):
        return [str(item) for item in value]
    return cast(list[str], list(fallback or []))


def _grammar_example_text(grammar_parse: Mapping[str, object] | None) -> str:
    if not grammar_parse or grammar_parse.get("parsed") is not True:
        return ""
    value = grammar_parse.get("example_text")
    return display_text(value) if isinstance(value, str) else ""


def _reference_parts(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*;\s*|\s*,\s*", text) if part.strip()]


def _looks_like_source_reference(label: str) -> bool:
    return (
        any(char.isupper() for char in label)
        or any(char.isdigit() for char in label)
        or "." in label
    )


def _looks_like_example_text(text: str) -> bool:
    return (
        any(marker in text for marker in ("«", "»", '"'))
        or len(text.split()) >= _EXAMPLE_TEXT_MIN_WORDS
    )


def _first_contained(needles: list[str], haystack: str) -> str | None:
    for needle in needles:
        if needle and needle in haystack:
            return needle
    return None


def _is_probable_definition_segment(text: str) -> bool:
    if not text:
        return False
    if re.match(r"^(?:cf|see)\.\s+", text, re.IGNORECASE):
        return False
    if _SOURCE_ABBREVIATION_RE.match(text):
        return False
    if len(text.split()) > _DEFINITION_SEGMENT_MAX_WORDS:
        return False
    if _CLASSICAL_CITATION_RE.search(text):
        return False
    return any(char.isalpha() for char in text)


def trim_empty(mapping: Mapping[str, object]) -> dict[str, object]:
    """Drop only absent metadata values, not source content."""
    return {key: value for key, value in mapping.items() if value not in (None, "", [], {})}
