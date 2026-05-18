"""Structural parsing helpers for Bailly dictionary entries."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict


class BaillySource(TypedDict, total=False):
    kind: Literal["bailly_app_markdown"]
    url: str


class BaillyBlock(TypedDict):
    path: str
    marker: str
    text: str


class BaillyStructuralEntry(TypedDict):
    lemma: str
    source: BaillySource
    blocks: list[BaillyBlock]


class BaillyStructureComparison(TypedDict):
    matched: bool
    missing: list[str]
    mismatched: list[dict[str, str]]


_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_LINK_ONLY_RE = re.compile(r"^\[[^\]]+\]\([^)]+\)$")
_NUMBERED_RE = re.compile(r"^(\d+)\s+(.+)$")
_NUMBERED_COMPACT_RE = re.compile(r"^(\d)(\D.+)$")
_ROMAN_RE = re.compile(r"^(I|II|III|IV|V)\s+(.+)$")
_ROMAN_COMPACT_RE = re.compile(r"^(II|III|IV|V)(\D.+)$")
_LETTER_RE = re.compile(r"^([A-E])\s+(.+)$")
_LETTER_COMPACT_RE = re.compile(r"^([A-E])(?=(?:propr\.|p\.|Syntaxe))(.+)$")
_ETYMOLOGY_RE = re.compile(r"^(Étym\.)\s*(.*)$")
_ROMAN_MARKERS = {"I", "II", "III", "IV", "V"}
_LETTER_MARKERS = {"A", "B", "C", "D", "E"}


def parse_bailly_app_markdown(
    markdown: str,
    *,
    source_url: str = "",
) -> BaillyStructuralEntry:
    """Parse Bailly.app markdown into ordered structural blocks.

    This parser intentionally avoids semantic interpretation. It preserves the visible
    entry flow exposed by Bailly.app: head text, top-level markers, child numbered
    markers, and note-like markers such as ``Étym.``.
    """
    lemma, body_lines = _entry_body(markdown)
    blocks = _structural_blocks(body_lines)
    return _trim_empty_entry(
        {
            "lemma": lemma,
            "source": _trim_empty_source(
                {
                    "kind": "bailly_app_markdown",
                    "url": source_url,
                }
            ),
            "blocks": blocks,
        }
    )


def compare_bailly_structure(
    gold_blocks: Sequence[Mapping[str, object]],
    extracted_blocks: Sequence[Mapping[str, object]],
) -> BaillyStructureComparison:
    """Compare gold fixture blocks against PDF-derived structural blocks.

    The check is deliberately structural. It does not interpret definitions or citations; it
    verifies that the extracted blocks preserve expected path keys, markers, and text anchors.
    """
    extracted_by_path = {
        str(block.get("path") or ""): block for block in extracted_blocks if block.get("path")
    }
    missing: list[str] = []
    mismatched: list[dict[str, str]] = []

    for gold in gold_blocks:
        path = str(gold.get("path") or "")
        extracted = extracted_by_path.get(path)
        if extracted is None:
            missing.append(path)
            continue

        gold_marker = str(gold.get("marker") or "")
        extracted_marker = str(extracted.get("marker") or "")
        if extracted_marker != gold_marker:
            mismatched.append(
                {
                    "path": path,
                    "field": "marker",
                    "expected": gold_marker,
                    "actual": extracted_marker,
                }
            )

        gold_text = str(gold.get("text") or "")
        extracted_text = str(extracted.get("text") or "")
        if not _contains_text_anchor(extracted_text, gold_text):
            mismatched.append(
                {
                    "path": path,
                    "field": "text",
                    "expected": gold_text,
                    "actual": extracted_text,
                }
            )

    return {
        "matched": not missing and not mismatched,
        "missing": missing,
        "mismatched": mismatched,
    }


def _entry_body(markdown: str) -> tuple[str, list[str]]:
    lemma = ""
    body_lines: list[str] = []
    in_entry = False
    for raw_line in markdown.splitlines():
        line = _clean_line(raw_line)
        if not in_entry:
            h1_match = _H1_RE.match(line)
            if h1_match:
                lemma = h1_match.group(1).strip()
                in_entry = True
            continue
        if line == "Assigner des étiquettes":
            break
        if not line or _LINK_ONLY_RE.match(line):
            continue
        body_lines.append(line)
    return lemma, body_lines


def _structural_blocks(lines: list[str]) -> list[BaillyBlock]:
    blocks: list[BaillyBlock] = []
    current_marker = "head"
    current_path = "00"
    current_parts: list[str] = []
    path_state = _MarkerPathState()

    def flush() -> None:
        if current_parts:
            blocks.append(
                {
                    "path": current_path,
                    "marker": current_marker,
                    "text": _join_parts(current_parts),
                }
            )

    for line in lines:
        marker = _line_marker(line, has_parent=path_state.has_parent)
        if marker is None:
            current_parts.append(line)
            continue

        marker_text, text = marker
        flush()
        current_path = path_state.path_for(marker_text)
        current_marker = marker_text
        current_parts = [text] if text else []

    flush()
    return blocks


class _MarkerPathState:
    def __init__(self) -> None:
        self._active_paths: dict[int, str] = {}
        self._active_markers: dict[int, str] = {}
        self._next_indexes: dict[int, int] = {1: 1}

    @property
    def has_parent(self) -> bool:
        return bool(self._active_paths)

    def path_for(self, marker: str) -> str:
        depth = self._depth_for(marker)
        index = self._next_indexes.get(depth, 1 if depth == 1 else 0)
        path = f"{index:02d}" if depth == 1 else f"{self._active_paths[depth - 1]}:{index:02d}"
        self._next_indexes[depth] = index + 1
        for stale_depth in [key for key in self._active_paths if key > depth]:
            del self._active_paths[stale_depth]
            del self._active_markers[stale_depth]
            self._next_indexes.pop(stale_depth, None)
        self._active_paths[depth] = path
        self._active_markers[depth] = marker
        self._next_indexes[depth + 1] = 0
        return path

    def _depth_for(self, marker: str) -> int:
        if marker in _LETTER_MARKERS or marker == "Étym.":
            return 1
        if marker in _ROMAN_MARKERS:
            return 2 if self._active_markers.get(1) in _LETTER_MARKERS else 1
        if marker.isdigit():
            for depth in sorted(self._active_markers, reverse=True):
                if self._active_markers[depth] in _ROMAN_MARKERS:
                    return depth + 1
            if self._active_markers.get(1) in _LETTER_MARKERS:
                return 2
            if self._active_paths:
                return max(self._active_paths) + 1
        return 1


def _line_marker(line: str, *, has_parent: bool = False) -> tuple[str, str] | None:
    etymology_match = _ETYMOLOGY_RE.match(line)
    if etymology_match:
        return (etymology_match.group(1), etymology_match.group(2).strip())
    letter_match = _LETTER_RE.match(line) or _LETTER_COMPACT_RE.match(line)
    if letter_match:
        return (letter_match.group(1), letter_match.group(2).strip())
    numbered_match = _NUMBERED_RE.match(line)
    if numbered_match is None and has_parent:
        numbered_match = _NUMBERED_COMPACT_RE.match(line)
    if numbered_match:
        return (numbered_match.group(1), numbered_match.group(2).strip())
    roman_match = _ROMAN_RE.match(line) or _ROMAN_COMPACT_RE.match(line)
    if roman_match:
        return (roman_match.group(1), roman_match.group(2).strip())
    return None


def _clean_line(line: str) -> str:
    stripped = line.strip()
    return re.sub(r"\\([\[\]|])", r"\1", stripped)


def _join_parts(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part.strip())


def _contains_text_anchor(text: str, anchor: str) -> bool:
    normalized_text = _normalize_comparison_text(text)
    normalized_anchor = _normalize_comparison_text(anchor)
    return normalized_anchor in normalized_text or normalized_text in normalized_anchor


def _normalize_comparison_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _trim_empty_source(source: BaillySource) -> BaillySource:
    return BaillySource({key: value for key, value in source.items() if value})


def _trim_empty_entry(entry: BaillyStructuralEntry) -> BaillyStructuralEntry:
    if not entry["source"]:
        return BaillyStructuralEntry(
            {
                "lemma": entry["lemma"],
                "source": {"kind": "bailly_app_markdown"},
                "blocks": entry["blocks"],
            }
        )
    return entry
