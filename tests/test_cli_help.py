"""
Smoke tests for CLI help text availability.

Verifies that all documented commands expose help successfully without
requiring backend services.
"""

from __future__ import annotations

from collections.abc import Sequence

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
        "plan",
        "plan-exec",
        "triples-dump",
        "databuild",
        "index",
        "normalize",
    ]
    for command in commands:
        _assert_help([command])


def test_index_subcommand_help() -> None:
    for command in ["status", "clear", "rebuild"]:
        _assert_help(["index", command])
