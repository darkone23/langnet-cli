from __future__ import annotations

import importlib
from typing import Any


def decorate_segment_display(
    segment: dict[str, Any],
    *,
    language: str | None,
) -> dict[str, Any]:
    decorated = dict(segment)
    if language:
        decorated["language"] = language
    text = str(decorated.get("text") or "")
    display = _segment_display(language, text)
    if display:
        decorated["display"] = display
        decorated["available_layers"] = list(display["available_layers"])
        if language == "san":
            decorated["script"] = display["transliteration_script"]
            decorated["transliteration"] = display["transliteration"]
            if display.get("native_script"):
                decorated["native_script"] = display["native_script"]
    return decorated


def _segment_display(language: str | None, text: str) -> dict[str, Any] | None:
    if not text:
        return None
    if language == "san":
        devanagari = _sanskrit_iast_to_devanagari(text)
        layers = ["transliteration"]
        display: dict[str, Any] = {
            "primary": text,
            "transliteration": text,
            "script": "IAST",
            "transliteration_script": "IAST",
            "available_layers": layers,
        }
        if devanagari and devanagari != text:
            display["primary"] = devanagari
            display["script"] = "Devanagari"
            display["native_script"] = devanagari
            layers.append("devanagari")
        return display
    if language == "grc":
        return {
            "primary": text,
            "script": "Greek",
            "available_layers": ["source"],
        }
    if language == "lat":
        return {
            "primary": text,
            "script": "Latin",
            "available_layers": ["source"],
        }
    return {
        "primary": text,
        "script": "source",
        "available_layers": ["source"],
    }


def _sanskrit_iast_to_devanagari(text: str) -> str | None:
    try:
        sanscript = importlib.import_module("indic_transliteration.sanscript")
        rendered = sanscript.transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
    except Exception:
        return None
    return rendered if isinstance(rendered, str) and rendered.strip() else None
