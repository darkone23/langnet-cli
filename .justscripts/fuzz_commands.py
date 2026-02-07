"""Fuzz commands for the autobot tool."""

from __future__ import annotations

import click
from fuzz_tool_outputs import run_from_args
from rich.console import Console

console = Console()


@click.group()
def fuzz():
    """Fuzz backend tool outputs and/or unified queries."""
    pass


@fuzz.command("list")
def list_targets():
    """List supported tool/action/lang combinations."""
    console.print("[cyan]Supported fuzz targets:[/cyan]")
    exit_code = run_from_args(["--list"])
    raise SystemExit(exit_code)


@fuzz.command("run")
@click.option("--tool", help="Tool to fuzz (diogenes, whitakers, heritage, cdsl, cltk)")
@click.option("--action", help="Action/verb to use (search, parse, morphology, etc.)")
@click.option("--lang", help="Language code (lat, grc, san)")
@click.option("--words", help="Comma-separated words to test")
@click.option("--validate", is_flag=True, help="Fail on empty/error raw outputs")
@click.option(
    "--mode",
    type=click.Choice(["tool", "query", "compare"]),
    default="tool",
    help="tool: /api/tool only; query: /api/q only; compare: both",
)
@click.option(
    "--save",
    is_flag=False,
    flag_value=True,
    default=None,
    help="Save JSON summary (optional path, defaults to examples/debug/fuzz_results.json)",
)
def run(tool, action, lang, words, validate, mode, save):
    """Run fuzzing for selected targets."""
    args: list[str] = []
    if tool:
        args.extend(["--tool", tool])
    if action:
        args.extend(["--action", action])
    if lang:
        args.extend(["--lang", lang])
    if words:
        args.extend(["--words", words])
    if validate:
        args.append("--validate")
    if mode:
        args.extend(["--mode", mode])
    if save is not None:
        if save is True:
            args.append("--save")
        else:
            args.extend(["--save", save])

    console.print(f"[cyan]Running fuzz harness[/cyan]: {' '.join(args) or '(defaults)'}")
    exit_code = run_from_args(args)
    raise SystemExit(exit_code)
