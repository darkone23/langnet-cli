"""
Fixture tests for CLI pretty-output formatter behavior.

Tests _display_pretty() with small in-memory payloads to protect output
format and ordering without requiring backend services.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from typing import Any

from langnet.cli import _display_pretty


def _render_pretty(language: str, text: str, results: dict[str, Any]) -> str:
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        _display_pretty(language, text, results)
    return output_buffer.getvalue()


def test_display_pretty_latin_whitakers() -> None:
    results = {
        "whitakers": [
            {
                "terms": [{"term": "lupus"}],
                "codeline": {"term": "lupus", "pos_code": "N"},
                "senses": ["wolf", "pike"],
            }
        ]
    }

    output = _render_pretty("lat", "lupus", results)

    assert "LUPUS [Latin]" in output
    assert "━" * 60 in output
    assert "Whitaker's Words" in output
    assert "Sources: 1/1 successful" in output


def test_display_pretty_sanskrit_heritage() -> None:
    results = {
        "heritage": {
            "morphology": [
                {"form": "agniḥ", "analysis": "nominative singular"},
                {"form": "agnim", "analysis": "accusative singular"},
            ]
        }
    }

    output = _render_pretty("san", "agni", results)

    assert "AGNI [Sanskrit]" in output
    assert "━" * 60 in output
    assert "Sanskrit Heritage Platform" in output
    assert "Sources: 1/1 successful" in output


def test_display_pretty_with_error() -> None:
    results = {
        "whitakers": [
            {
                "terms": [{"term": "lupus"}],
                "codeline": {"term": "lupus", "pos_code": "N"},
                "senses": ["wolf"],
            }
        ],
        "diogenes": {"error": "Service unavailable"},
    }

    output = _render_pretty("lat", "lupus", results)

    assert "LUPUS [Latin]" in output
    assert "Whitaker's Words" in output
    assert "DIOGENES" in output
    assert "Service unavailable" in output
    assert "Sources: 1/2 successful" in output


def test_display_pretty_ordering() -> None:
    results = {
        "whitakers": [{"terms": [{"term": "lupus"}], "senses": ["wolf"]}],
        "diogenes": {"entries": [{"headword": "lupus", "definition": "wolf definition"}]},
    }

    output = _render_pretty("lat", "lupus", results)
    output_lines = output.split("\n")
    whitakers_idx = next(i for i, line in enumerate(output_lines) if "Whitaker's Words" in line)
    diogenes_idx = next(i for i, line in enumerate(output_lines) if "Lewis & Short" in line)

    assert whitakers_idx < diogenes_idx
