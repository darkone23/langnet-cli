"""
Smoke tests for CLI help text availability.

Verifies that all documented commands expose help successfully without
requiring backend services.
"""

from __future__ import annotations

from collections.abc import Sequence
from unittest.mock import patch

from click.testing import CliRunner

from langnet.cli import main


def _assert_help(args: Sequence[str], expected: str | None = None) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [*args, "--help"])
    assert result.exit_code == 0
    if expected:
        assert expected in result.output


def test_main_help() -> None:
    _assert_help([], "langnet-cli")


def test_documented_command_help() -> None:
    commands = [
        "lookup",
        "parse",
        "paradigm",
        "paradigm-resolve",
        "plan",
        "plan-exec",
        "triples-dump",
        "databuild",
        "doctor",
        "index",
        "langs",
        "normalize",
        "translation-cache",
        "tools",
        "word-index",
        "word-of-day",
        "recommend-words",
        "reader",
    ]
    for command in commands:
        _assert_help([command])


def test_index_subcommand_help() -> None:
    for command in ["status", "clear", "rebuild"]:
        _assert_help(["index", command])


def test_translation_cache_subcommand_help() -> None:
    for command in ["status", "clear"]:
        _assert_help(["translation-cache", command])


def test_translation_cli_defaults_use_deepseek_flash() -> None:
    expected_model = "openai:deepseek/deepseek-v4-flash"
    for command in ["encounter", "translation-warm", "reader-eval"]:
        runner = CliRunner()
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0, result.output
        assert expected_model in result.output
        assert "gemini-3.1-pro-preview" not in result.output


def test_word_index_subcommand_help() -> None:
    for command in ["sources", "sections", "list", "browse", "neighborhood", "nearby", "wheel"]:
        _assert_help(["word-index", command])


def test_word_index_browse_help_mentions_homograph_mode() -> None:
    _assert_help(["word-index", "browse"], "--homographs")


def test_word_index_wheel_accepts_language_option() -> None:
    result = CliRunner().invoke(
        main,
        [
            "word-index",
            "wheel",
            "--language",
            "grc",
            "--source",
            "diogenes",
            "--count",
            "1",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"language": "grc"' in result.output


def test_word_index_nearby_pretty_uses_integrated_neighborhood() -> None:
    payload = {
        "schema_version": "langnet.word_index.v1",
        "request": {"language": "san", "source": "all", "mode": "neighborhood"},
        "sources": [],
        "items": [],
        "neighborhood": {
            "policy": "integrated_language_native",
            "language": "san",
            "source": "all",
            "dictionary": "integrated",
            "items": [
                _word_index_item("before", "ḹ", "ळॡ"),
                _word_index_item("anchor", "e", "ए"),
                _word_index_item("after", "eka", "एक"),
            ],
            "groups": [
                {
                    "language": "san",
                    "source": "cdsl",
                    "anchor": _word_index_item("anchor", "e", "ए"),
                }
            ],
            "order": {"collation": "sa-varga"},
        },
        "pagination": {"next_cursor": None, "prev_cursor": None},
        "warnings": [],
    }
    with patch("langnet.cli.word_index_neighborhood_payload", return_value=payload):
        result = CliRunner().invoke(main, ["word-index", "nearby", "san", "e"])

    assert result.exit_code == 0, result.output
    assert "integrated_language_native" in result.output
    assert "anchor: san:all e (ए)" in result.output
    assert "san:cdsl" not in result.output


def _word_index_item(position: str, transliteration: str, native: str) -> dict[str, object]:
    return {
        "language": "san",
        "source": "all",
        "position": position,
        "canonical_name": native,
        "display": {"transliteration": transliteration},
    }


def test_databuild_subcommand_help() -> None:
    for command in [
        "cts",
        "cdsl",
        "gaffiot",
        "dico",
        "diogenes-index",
        "whitakers-index",
        "reader",
    ]:
        _assert_help(["databuild", command])
