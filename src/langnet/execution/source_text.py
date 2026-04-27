from __future__ import annotations

import re
from collections.abc import Mapping

_SEGMENT_SPLIT_RE = re.compile(r"[;\n¶]+")


def display_text(raw_text: str) -> str:
    """Return a display-safe text form without treating it as a data reduction."""
    return re.sub(r"\s+", " ", raw_text).strip()


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
        segments.append(
            {
                "index": len(segments),
                "raw_text": segment,
                "display_text": display_text(segment),
                "segment_type": segment_type,
                "labels": list(labels or []),
            }
        )
    if segments:
        return segments
    stripped = raw_text.strip()
    if not stripped:
        return []
    return [
        {
            "index": 0,
            "raw_text": stripped,
            "display_text": display_text(stripped),
            "segment_type": segment_type,
            "labels": list(labels or []),
        }
    ]


def trim_empty(mapping: Mapping[str, object]) -> dict[str, object]:
    """Drop only absent metadata values, not source content."""
    return {key: value for key, value in mapping.items() if value not in (None, "", [], {})}
