"""
langnet - CLI for querying classical language lexicons and morphological tools.

This tool provides a unified interface to:
  - Latin: Diogenes (lexicon), Whitakers (morphology), CLTK (Lewis lexicon)
  - Greek: Diogenes (lexicon + morphology), spaCy (morphology)
  - Sanskrit: CDSL (Monier-Williams/AP90)

Usage:
    langnet <command> [options]

Commands:
    query       Query a word in a given language
    verify      Check backend connectivity and health
    langs       List supported languages
    health      Alias for verify

For detailed help on a command:
    langnet <command> --help
"""

import dataclasses
import socket
import sys
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import click
import orjson
import requests
from rich.console import Console
from rich.pretty import pprint
from rich.table import Table

from langnet.cologne.core import CdslIndex, CdslIndexBuilder, batch_build
from langnet.config import config
from langnet.foster.render import render_foster_codes
from langnet.indexer.core import IndexType
from langnet.indexer.cts_urn_indexer import CtsUrnIndexer
from langnet.indexer.utils import get_index_manager
from langnet.logging import setup_logging

BODY_PREVIEW_LENGTH = 100


@dataclasses.dataclass
class ToolQueryParams:
    """Parameters for tool queries."""

    tool: str
    action: str
    lang: str | None = None
    query: str | None = None
    dict_name: str | None = None
    output: str = "json"
    save: str | None = None


@dataclasses.dataclass
class ToolQueryContext:
    """Context for tool queries combining click parameters."""

    tool: str
    action: str
    lang: str | None = None
    query: str | None = None
    dict_name: str | None = None
    output: str = "json"
    save: str | None = None


console = Console()
DEFAULT_API_URL = "http://localhost:8000"


def _format_morph_with_foster(morph: dict) -> str:
    tags = morph.get("tags", [])
    foster_codes_raw = morph.get("foster_codes")
    foster_codes: list[str] = foster_codes_raw if isinstance(foster_codes_raw, list) else []
    stem = ", ".join(morph.get("stem", []))
    defs = morph.get("defs")

    parts = []
    if stem:
        parts.append(f"[bold]{stem}[/bold]")

    for i, tag in enumerate(tags):
        tag_display = tag
        if i < len(foster_codes) and foster_codes[i]:
            rendered = cast(list[str], render_foster_codes([foster_codes[i]]))
            foster_display = rendered[0]
            tag_display = f"{tag} ([italic]{foster_display}[/italic])"
        parts.append(tag_display)

    result = " ".join(parts)
    if defs:
        result += f" → {', '.join(defs)}"
    return result


def _format_diogenes_with_foster(result: dict | list) -> None:
    if isinstance(result, list):
        return

    diogenes = result.get("diogenes")
    if not diogenes or "chunks" not in diogenes:
        return

    for chunk in diogenes["chunks"]:
        morph_data = chunk.get("morphology")
        if not morph_data or "morphs" not in morph_data:
            continue

        morphs = morph_data["morphs"]
        formatted_morphs = [_format_morph_with_foster(m) for m in morphs]
        morph_data["formatted"] = formatted_morphs


def _format_cltk_with_foster(result: dict | list) -> None:
    if isinstance(result, list):
        return

    cltk = result.get("cltk")
    if not cltk or "greek_morphology" not in cltk:
        return

    greek_morph = cltk["greek_morphology"]
    if "foster_codes" not in greek_morph:
        return

    greek_morph["formatted_foster"] = render_foster_codes(greek_morph["foster_codes"])


def _format_sanskrit_with_foster(result: dict | list) -> None:
    if isinstance(result, list):
        return

    dictionaries = result.get("dictionaries")
    if not dictionaries:
        return

    for entries in dictionaries.values():
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if isinstance(entry, dict) and "foster_codes" in entry:
                entry["formatted_foster"] = render_foster_codes(entry["foster_codes"])


def _show_sanskrit_warning(result: dict | list) -> None:
    if isinstance(result, list):
        if result and isinstance(result[0], dict) and result[0].get("_warning"):
            console.print(f"[yellow]Warning: {result[0]['_warning']}[/]")
        return

    if result.get("_warning"):
        console.print(f"[yellow]Warning: {result['_warning']}[/]")


def _format_result_with_foster(result: dict | list) -> dict | list:
    if isinstance(result, list):
        return result

    _format_diogenes_with_foster(result)
    _format_cltk_with_foster(result)
    _format_sanskrit_with_foster(result)
    _show_sanskrit_warning(result)
    return result


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False


@click.group()
def main():
    """Query classical language lexicons and morphological tools.

    Provides unified access to Latin, Greek, and Sanskrit resources
    including Diogenes, Whitakers, CLTK, and spaCy backends.
    """
    setup_logging()


def _verify_impl(api_url: str, socket_timeout: float = 1.0, http_timeout: float = 30.0):
    """Core verification logic shared by verify and health commands."""
    parsed = urlparse(api_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80

    if not is_port_open(host, port, timeout=socket_timeout):
        console.print(f"[red]Error: Cannot connect to {host}:{port} - port closed[/]")
        sys.exit(1)

    health_url = f"{api_url}/api/health"
    try:
        response = requests.get(health_url, timeout=http_timeout)
        response.raise_for_status()
        health_data = orjson.loads(response.text)

        status = health_data.get("status", "unknown")
        components = health_data.get("components", {})

        table = Table(title="Backend Status")
        table.add_column("Backend", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")

        for name, info in components.items():
            comp_status = info.get("status", "unknown")
            message = info.get("message", "")
            status_style = "green" if comp_status == "healthy" else "red"
            table.add_row(name.title(), f"[{status_style}]{comp_status}[/]", message)

        console.print(table)
        console.print(f"\nOverall: [bold]{status}[/]")

        if status != "healthy":
            sys.exit(1)
    except requests.RequestException as e:
        console.print(f"[red]Error: Could not connect to API at {health_url}[/]")
        console.print(f"[red]Details: {e}[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


@main.command(name="verify")
@click.option(
    "--api-url",
    default=DEFAULT_API_URL,
    help="Base URL of the langnet API server",
)
@click.option(
    "--socket-timeout",
    default=1.0,
    help="Timeout for socket connectivity check (seconds)",
)
@click.option(
    "--timeout",
    default=30.0,
    help="Timeout for HTTP health check (seconds)",
)
@click.option(
    "--output",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format: json for raw output, table for formatted display",
)
def verify(api_url: str, socket_timeout: float, timeout: float, output: str):
    """Verify backend connectivity and health status.

    Performs a two-stage check:
    1. Quick TCP socket check to detect closed ports
    2. Full HTTP health check against /api/health endpoint

    Returns non-zero exit code if any backend is unhealthy.

    Examples:
        langnet verify                           # check local server
        langnet verify --api-url http://host:8000
        langnet verify --timeout 60              # longer timeout
    """
    _verify_impl(api_url, socket_timeout, timeout)


@main.command(name="query")
@click.argument("lang")
@click.argument("word")
@click.option(
    "--api-url",
    default=DEFAULT_API_URL,
    help="Base URL of the langnet API server",
)
@click.option(
    "--output",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format: json (raw JSON) or table (rich formatted)",
)
def query(lang: str, word: str, api_url: str, output: str):
    """Query a word in a classical language.

    Queries the langnet API for lexicon entries and morphological analysis.
    Supports Latin (lat), Greek (grc), and Sanskrit (san).

    Arguments:
        lang: Language code (lat, grc, san, or grk as alias for grc)
        word: Word to look up (ASCII or UTF-8, sent via POST)

    Options:
        --output json   Output raw JSON from server (pipable)
        --output table  Rich formatted output (default)

    Examples:
        langnet-cli query lat lupus
        langnet-cli query grc Nike
        langnet-cli query grc '*ou/sia'      # Greek: Betacode encoding
        langnet-cli query san '.agni'        # Sanskrit: Velthuis encoding
        langnet-cli query lat lupus --output json | jq '.diogenes'
    """
    valid_languages = {"lat", "grc", "san", "grk"}
    if lang not in valid_languages:
        console.print(
            f"[red]Error: Invalid language '{lang}'. Must be one of: "
            f"{', '.join(sorted(valid_languages))}[/]"
        )
        sys.exit(1)

    if lang == "grk":
        lang = "grc"

    url = f"{api_url}/api/q"

    try:
        response = requests.post(url, data={"l": lang, "s": word}, timeout=30)
        response.raise_for_status()

        if output == "json":
            sys.stdout.write(response.text)
            sys.stdout.flush()
        else:
            result = orjson.loads(response.text)
            result = _format_result_with_foster(result)

            pprint(result)
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


@main.command(name="langs")
@click.option(
    "--api-url",
    default=DEFAULT_API_URL,
    help="Base URL of the langnet API server",
)
def list_languages(api_url: str):
    """List supported languages and their codes.

    Displays a table of available language codes and full names.
    """
    table = Table(title="Supported Languages")
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="green")
    table.add_row("lat", "Latin")
    table.add_row("grc", "Greek")
    table.add_row("san", "Sanskrit")
    console.print(table)


@main.command(name="health")
@click.option(
    "--api-url",
    default=DEFAULT_API_URL,
    help="Base URL of the langnet API server",
)
@click.option(
    "--timeout",
    default=30.0,
    help="Timeout for HTTP health check (seconds)",
)
def health(api_url: str, timeout: float):
    """Check API health (alias for verify).

    Deprecated: Use 'langnet verify' instead.
    """
    _verify_impl(api_url, http_timeout=timeout)


def get_cdsl_db_dir() -> Path:
    return config.cdsl_db_dir


def get_cdsl_dict_dir() -> Path:
    return config.cdsl_dict_dir


@main.group()
def cdsl():
    """CDSL Sanskrit dictionary tools (Cologne Digital Sanskrit Lexicon)."""


@cdsl.command(name="build")
@click.argument("dict_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("output_db", type=click.Path(file_okay=True, dir_okay=False))
@click.option("--dict-id", default=None, help="Explicit dict ID (from dir name if not provided)")
@click.option("--limit", default=None, type=int, help="Limit to N entries (for testing)")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing database")
@click.option(
    "--batch-size",
    default=None,
    type=int,
    help="Batch size for processing (default: auto)",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help="Number of parallel workers (default: CPU count)",
)
def build(  # noqa: PLR0913 - 7 params is reasonable for CLI builder with 4 optional options
    dict_dir: str,
    output_db: str,
    dict_id: str | None,
    limit: int | None,
    force: bool,
    batch_size: int | None,
    workers: int | None,
):
    """Build DuckDB index from CDSL source SQLite.

    Example: langnet-cli cdsl build ~/cdsl_data/dict/MW ~/cdsl_data/db/mw.db --limit 1000
    """
    dict_path = Path(dict_dir)
    output_path = Path(output_db)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if dict_id is None:
        dict_id = dict_path.name.upper()

    if output_path.exists() and not force:
        console.print(f"[red]Error: Database already exists: {output_path}[/]")
        console.print("Use --force to overwrite.")
        sys.exit(1)

    console.print(f"Building {dict_id} from {dict_path}...")

    count = CdslIndexBuilder.build(
        dict_path,
        output_path,
        dict_id.upper(),
        limit=limit,
        batch_size=batch_size,
        num_workers=workers,
    )

    console.print(f"[green]Indexed {count} entries into {output_path}[/]")


@cdsl.command(name="build-all")
@click.argument("dict_root", type=click.Path(exists=True, file_okay=False), default=None)
@click.argument("output_dir", type=click.Path(file_okay=False, dir_okay=True), default=None)
@click.option("--limit", default=None, type=int, help="Limit each dictionary to N entries")
def build_all(dict_root: str | None, output_dir: str | None, limit: int | None):
    """Build all dictionaries in a directory.

    Example: langnet-cli cdsl build-all ~/cdsl_data/dict ~/cdsl_data/db --limit 1000
    """
    dict_path = Path(dict_root) if dict_root else get_cdsl_dict_dir()
    output_path = Path(output_dir) if output_dir else get_cdsl_db_dir()

    console.print(f"Building all dictionaries from {dict_path}...")

    results = batch_build(dict_path, output_path, limit=limit)

    for dict_id, count in sorted(results.items()):
        if count >= 0:
            console.print(f"  [green]{dict_id}: {count} entries[/]")
        else:
            console.print(f"  [red]{dict_id}: FAILED[/]")


@cdsl.command(name="lookup")
@click.argument("dict_id")
@click.argument("key")
@click.option("--output", type=click.Choice(["json", "table"]), default="table")
def lookup(dict_id: str, key: str, output: str):
    """Lookup headword (Devanagari or SLP1 accepted).

    Example: langnet-cli cdsl lookup mw "अग्नि"
             langnet-cli cdsl lookup mw agni
    """

    db_path = get_cdsl_db_dir() / f"{dict_id.lower()}.db"
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/]")
        console.print("Run 'langnet-cli cdsl build' first to create the index.")
        sys.exit(1)

    with CdslIndex(db_path) as index:
        results = index.lookup(dict_id.upper(), key)

    if not results:
        console.print(f"[yellow]No entries found for '{key}'[/]")
        return

    if output == "json":
        json_output = [
            {
                "dict_id": r.dict_id,
                "key": r.key,
                "lnum": r.lnum,
                "body": r.body,
                "page_ref": r.page_ref,
            }
            for r in results
        ]
        console.print(orjson.dumps(json_output, option=orjson.OPT_INDENT_2).decode("utf-8"))
    else:
        table = Table(title=f"Results for '{key}' in {dict_id.upper()}")
        table.add_column("Key", style="cyan")
        table.add_column("L#", justify="right")
        table.add_column("Body", style="green")
        table.add_column("Page", style="yellow")
        for r in results:
            body_preview = (
                (r.body[:BODY_PREVIEW_LENGTH] + "...")
                if r.body and len(r.body) > BODY_PREVIEW_LENGTH
                else r.body or ""
            )
            table.add_row(r.key, str(r.lnum), body_preview, r.page_ref or "")
        console.print(table)


@cdsl.command(name="prefix")
@click.argument("dict_id")
@click.argument("prefix")
@click.option("--limit", default=20, type=int, help="Max results")
def prefix(dict_id: str, prefix: str, limit: int):
    """Autocomplete: find headwords starting with prefix.

    Example: langnet-cli cdsl prefix mw "अग्न"
    """
    db_path = get_cdsl_db_dir() / f"{dict_id.lower()}.db"
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/]")
        sys.exit(1)

    with CdslIndex(db_path) as index:
        results = index.prefix_search(dict_id.upper(), prefix, limit=limit)

    if not results:
        console.print(f"[yellow]No matches found for '{prefix}'[/]")
        return

    console.print(f"[cyan]Matches for '{prefix}' in {dict_id.upper()}:[/]")
    for key, lnum in results[:limit]:
        console.print(f"  {key} [{lnum}]")


@cdsl.command(name="list")
def list_dicts():
    """List indexed dictionaries.

    Example: langnet-cli cdsl list
    """
    db_dir = get_cdsl_db_dir()
    if not db_dir.exists():
        console.print("[yellow]No indexed dictionaries found.[/]")
        console.print("Run 'langnet-cli cdsl build' to create indexes.")
        return

    dbs = sorted(db_dir.glob("*.db"))
    if not dbs:
        console.print("[yellow]No .db files found.[/]")
        return

    table = Table(title="Indexed Dictionaries")
    table.add_column("Dictionary", style="cyan")
    table.add_column("Entries", justify="right", style="green")
    table.add_column("Size", style="yellow")

    for db_file in dbs:
        dict_id = db_file.stem.upper()
        with CdslIndex(db_file) as index:
            info = index.get_info(dict_id)
        size_kb = info["db_size_bytes"] // 1024
        table.add_row(dict_id, str(info["entry_count"]), f"{size_kb} KB")

    console.print(table)


@cdsl.command(name="info")
@click.argument("dict_id")
def info(dict_id: str):
    """Show dictionary metadata and statistics.

    Example: langnet-cli cdsl info MW
    """
    db_path = get_cdsl_db_dir() / f"{dict_id.lower()}.db"
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/]")
        sys.exit(1)

    with CdslIndex(db_path) as index:
        info = index.get_info(dict_id.upper())

    table = Table(title=f"Dictionary: {info['dict_id']}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Database", info["db_path"])
    table.add_row("Entries", str(info["entry_count"]))
    table.add_row("Headwords", str(info["headword_count"]))
    table.add_row("Size", f"{info['db_size_bytes']} bytes")

    console.print(table)


@main.group()
def citation():
    """Citation utilities for classical language texts."""
    pass


@citation.command(name="explain")
@click.argument("abbreviation")
@click.option(
    "--api-url",
    default=DEFAULT_API_URL,
    help="Base URL of the langnet API server",
)
def explain_citation(abbreviation: str, api_url: str):
    """Explain a citation abbreviation or reference.

    Provides detailed information about classical text citations,
    including abbreviations, cross-references, and source details.

    Examples:
        langnet-cli citation explain "Hom. Il. 1.1"
        langnet-cli citation explain "L&S"
        langnet-cli citation explain "M-W 127"
    """
    # Simple lookup for common citation abbreviations
    citation_db = {
        # Diogenes/Perseus style - include both short and full forms
        "hom": {"full_name": "Homer", "work": "epic poet", "type": "author"},
        "hom.": {"full_name": "Homer", "work": "epic poet", "type": "author"},
        "il": {"full_name": "Iliad", "work": "epic poem", "type": "work"},
        "il.": {"full_name": "Iliad", "work": "epic poem", "type": "work"},
        "od": {"full_name": "Odyssey", "work": "epic poem", "type": "work"},
        "od.": {"full_name": "Odyssey", "work": "epic poem", "type": "work"},
        "verg": {"full_name": "Vergil", "work": "Roman poet", "type": "author"},
        "verg.": {"full_name": "Vergil", "work": "Roman poet", "type": "author"},
        "aen": {"full_name": "Aeneid", "work": "epic poem", "type": "work"},
        "aen.": {"full_name": "Aeneid", "work": "epic poem", "type": "work"},
        "georg": {"full_name": "Georgics", "work": "didactic poem", "type": "work"},
        "georg.": {"full_name": "Georgics", "work": "didactic poem", "type": "work"},
        "ecl": {"full_name": "Eclogues", "work": "pastoral poems", "type": "work"},
        "ecl.": {"full_name": "Eclogues", "work": "pastoral poems", "type": "work"},
        "cic": {"full_name": "Cicero", "work": "Roman statesman", "type": "author"},
        "cic.": {"full_name": "Cicero", "work": "Roman statesman", "type": "author"},
        "fin": {"full_name": "Tusculan Disputations", "work": "philosophical work", "type": "work"},
        "fin.": {
            "full_name": "Tusculan Disputations",
            "work": "philosophical work",
            "type": "work",
        },
        "plaut": {"full_name": "Plautus", "work": "Roman playwright", "type": "author"},
        "plaut.": {"full_name": "Plautus", "work": "Roman playwright", "type": "author"},
        "cas": {"full_name": "Casina", "work": "comedy", "type": "work"},
        "cas.": {"full_name": "Casina", "work": "comedy", "type": "work"},
        # Dictionary abbreviations
        "l&s": {
            "full_name": "Lewis and Short Latin Dictionary",
            "work": "Latin lexicon",
            "type": "dictionary",
        },
        "lsj": {
            "full_name": "Liddell-Scott-Jones Greek Lexicon",
            "work": "Greek lexicon",
            "type": "dictionary",
        },
        "mw": {
            "full_name": "Monier-Williams Sanskrit-English Dictionary",
            "work": "Sanskrit lexicon",
            "type": "dictionary",
        },
        "m-w": {
            "full_name": "Monier-Williams Sanskrit-English Dictionary",
            "work": "Sanskrit lexicon",
            "type": "dictionary",
        },
        "apte": {
            "full_name": "The Practical Sanskrit-English Dictionary",
            "work": "Sanskrit lexicon",
            "type": "dictionary",
        },
    }

    # Normalize the abbreviation - try multiple approaches
    variations = [
        abbreviation,
        abbreviation.lower(),
        abbreviation.replace(".", ""),
        abbreviation.replace(" ", ""),
        abbreviation.lower().replace(".", ""),
        abbreviation.lower().replace(" ", ""),
    ]

    found = False
    for variation in variations:
        if variation in citation_db:
            info = citation_db[variation]
            table = Table(title="Citation Explanation")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Abbreviation", abbreviation)
            table.add_row("Full Name", info["full_name"])
            table.add_row("Work/Type", info["work"])
            table.add_row("Category", info["type"].title())

            console.print(table)
            found = True
            break

    if not found:
        console.print(f"[yellow]No detailed information found for '{abbreviation}'[/]")
        console.print("[yellow]Try querying the word directly to see associated citations.[/]")


@citation.command(name="list")
@click.argument("lang")
@click.argument("word")
@click.option(
    "--api-url",
    default=DEFAULT_API_URL,
    help="Base URL of the langnet API server",
)
@click.option(
    "--output",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format: json for raw output, table for formatted display",
)
def list_citations(lang: str, word: str, api_url: str, output: str):  # noqa: C901, PLR0912
    """List all citations for a word query.

    Shows all citations found when looking up a word in the classical language.
    Helps students understand what references and sources are associated with
    a particular term.

    Arguments:
        lang: Language code (lat, grc, san, or grk as alias for grc)
        word: Word to look up and find citations for

    Examples:
        langnet-cli citation list lat lupus
        langnet-cli citation list grc Nike
        langnet-cli citation list san agni
    """
    valid_languages = {"lat", "grc", "san", "grk"}
    if lang not in valid_languages:
        console.print(
            f"[red]Error: Invalid language '{lang}'. Must be one of: "
            f"{', '.join(sorted(valid_languages))}[/]"
        )
        sys.exit(1)

    if lang == "grk":
        lang = "grc"

    url = f"{api_url}/api/q"

    try:
        response = requests.post(url, data={"l": lang, "s": word}, timeout=30)
        response.raise_for_status()

        result = orjson.loads(response.text)

        # Extract citations from the result
        citations = []

        # Check Diogenes results
        if result.get("diogenes") and result["diogenes"].get("dg_parsed"):
            for chunk in result["diogenes"].get("chunks", []):
                if hasattr(chunk, "definitions") and chunk.definitions:
                    for block in chunk.definitions.blocks:
                        if hasattr(block, "citations") and block.citations:
                            citations.extend(block.citations.citations)

        # Check CDSL results
        if result.get("cdsl"):
            for dict_entries in result["cdsl"].get("dictionaries", {}).values():
                for entry in dict_entries:
                    if hasattr(entry, "references") and entry.references:
                        citations.extend(entry.references.citations)

        if not citations:
            console.print(f"[yellow]No citations found for '{word}' in {lang}[/]")
            return

        if output == "json":
            json_output = [citation.to_dict() for citation in citations]
            console.print(orjson.dumps(json_output, option=orjson.OPT_INDENT_2).decode("utf-8"))
        else:
            table = Table(title=f"Citations for '{word}' ({lang})")
            table.add_column("#", style="cyan")
            table.add_column("Text", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Work", style="blue")
            table.add_column("Author", style="magenta")
            table.add_column("Source", style="cyan")

            for i, citation in enumerate(citations, 1):
                primary_ref = citation.references[0] if citation.references else None
                table.add_row(
                    str(i),
                    primary_ref.text if primary_ref else "N/A",
                    primary_ref.type.value if primary_ref else "N/A",
                    primary_ref.work if primary_ref else "N/A",
                    primary_ref.author if primary_ref else "N/A",
                    citation.abbreviation or "N/A",
                )

            console.print(table)

    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()


@main.group()
def indexer():
    """Indexer tools for building and managing search indexes."""
    pass


@indexer.command("build-cts")
@click.option(
    "--source",
    "-s",
    type=click.Path(exists=True),
    default="/home/nixos/langnet-tools/diogenes/Classics-Data",
    help="Source data directory",
)
@click.option("--output", "-o", type=click.Path(), help="Output database path")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing index file")
@click.option("--force", is_flag=True, help="Force rebuild even if index exists")
@click.option("--config-dir", type=click.Path(), help="Configuration directory")
def build_cts_index(
    source: str, output: str | None, overwrite: bool, force: bool, config_dir: str | None
):
    """Build CTS URN reference index."""
    source_path = Path(source)
    output_path = (
        Path(output) if output else Path.home() / ".local" / "share" / "langnet" / "cts_urn.duckdb"
    )

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Overwrite if requested
    if output_path.exists():
        if overwrite:
            output_path.unlink()
            click.echo(f"Deleted existing index file {output_path}")
        else:
            click.echo(f"Index already exists at {output_path}. Use --overwrite to replace.")
            return 1

    click.echo("Building CTS URN index...")
    click.echo(f"Source: {source_path}")
    click.echo(f"Output: {output_path}")

    # Build indexer
    config = {"source_dir": str(source_path), "force_rebuild": force}

    indexer_obj = CtsUrnIndexer(output_path, config)

    try:
        success = indexer_obj.build()
        if success:
            click.echo("✅ CTS URN index built successfully!")

            # Register the index
            manager = get_index_manager()
            manager.register_index(
                name="cts_urn", index_type=IndexType.CTS_URN, path=output_path, config=config
            )

            # Show stats
            stats = indexer_obj.get_stats()
            work_count = stats.get("work_count", "N/A")
            size_mb = stats.get("size_mb", 0)
            click.echo(f"📊 Stats: {work_count} works, {size_mb:.2f} MB")
        else:
            click.echo("❌ Failed to build CTS URN index")
            return 1
    except Exception as e:
        click.echo(f"❌ Error building index: {e}")
        return 1
    finally:
        indexer_obj.cleanup()

    return 0


@indexer.command("stats-cts")
@click.option("--name", "-n", default="cts_urn", help="Index name")
def stats_cts(name: str):
    """Show CTS URN index statistics."""
    from langnet.indexer.utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    stats = manager.get_index_stats(name)

    if not stats:
        click.echo(f"❌ Index '{name}' not found")
        return 1

    click.echo(f"📊 {name} Index Statistics:")
    click.echo(f"  Type: {stats.index_type.value}")
    click.echo(f"  Status: {stats.status.value}")
    click.echo(f"  Size: {stats.size_mb:.2f} MB")
    click.echo(f"  Entries: {stats.entry_count}")
    click.echo(f"  Built: {stats.build_date}")

    return 0


@indexer.command("list-indexes")
def list_indexes():
    """List all registered indexes."""
    from langnet.indexer.utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    indexes = manager.list_indexes()

    if not indexes:
        click.echo("No indexes registered")
    else:
        for index in indexes:
            click.echo(f"  {index['type']} ({index.get('path', 'unknown')})")

    return 0


@main.group()
def tool():
    """Debug individual backend tools and access raw data."""
    pass


@tool.group()
def diogenes():
    """Diogenes backend tools for Latin and Greek."""
    pass


@diogenes.command("parse")
@click.option("--lang", required=True, help="Language code (lat, grc, grk)")
@click.option("--query", required=True, help="Word to parse")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
def diogenes_parse(lang: str, query: str, output: str, save: str):
    """Parse a word using Diogenes backend."""
    _tool_query("diogenes", "parse", lang=lang, query=query, output=output, save=save)


@tool.group()
def whitakers():
    """Whitaker's Words backend tools for Latin."""
    pass


@whitakers.command("search")
@click.option("--query", required=True, help="Word to analyze")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
def whitakers_search(query: str, output: str, save: str):
    """Analyze a word using Whitaker's Words backend."""
    _tool_query("whitakers", "search", lang="lat", query=query, output=output, save=save)


@tool.group()
def heritage():
    """Heritage Platform backend tools for Sanskrit."""
    pass


@heritage.command("morphology")
@click.option("--query", required=True, help="Word to analyze")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
def heritage_morphology(query: str, output: str, save: str):
    """Get morphological analysis using Heritage Platform backend."""
    _tool_query("heritage", "morphology", query=query, output=output, save=save)


@heritage.command("canonical")
@click.option("--query", required=True, help="Word to canonicalize")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
def heritage_canonical(query: str, output: str, save: str):
    """
    Get canonical Sanskrit form using sktsearch.

    Handles transliteration and encoding normalization.
    Useful for converting user input to standard dictionary form.

    Examples:
        just cli tool heritage canonical --query agnii
        # Returns: {canonical_sanskrit: "agni", canonical_text: "अग्नि"}
    """
    _tool_query("heritage", "canonical", query=query, output=output, save=save)


@heritage.command("lemmatize")
@click.option("--query", required=True, help="Inflected form to lemmatize")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
def heritage_lemmatize(query: str, output: str, save: str):
    """
    Get lemma from inflected form using sktlemmatizer.

    Examples:
        just cli tool heritage lemmatize --query agniis
        # Returns: {lemma: "agni", inflected_form: "agniis"}
    """
    _tool_query("heritage", "lemmatize", query=query, output=output, save=save)


@tool.group(name="cdsl")
def cdsl_tool():
    """CDSL backend tools for Sanskrit."""
    pass


@cdsl_tool.command("lookup")
@click.option("--query", required=True, help="Word to lookup")
@click.option("--dict", "dict_name", help="Dictionary ID (default: mw)")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
def cdsl_lookup(query: str, dict_name: str, output: str, save: str):
    """Lookup a word using CDSL backend."""
    _tool_query("cdsl", "lookup", query=query, dict_name=dict_name, output=output, save=save)


@tool.group()
def cltk():
    """CLTK backend tools for classical languages."""
    pass


@cltk.command("morphology")
@click.option("--lang", required=True, help="Language code (lat, grc, san)")
@click.option("--query", required=True, help="Word to analyze")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
def cltk_morphology(lang: str, query: str, output: str, save: str):
    """Get morphological analysis using CLTK backend."""
    _tool_query("cltk", "morphology", lang=lang, query=query, output=output, save=save)


def _tool_query(  # noqa: PLR0913
    tool: str,
    action: str,
    lang: str | None = None,
    query: str | None = None,
    dict_name: str | None = None,
    output: str = "json",
    save: str | None = None,
):
    """Generic tool query implementation."""
    context = ToolQueryContext(
        tool=tool,
        action=action,
        lang=lang,
        query=query,
        dict_name=dict_name,
        output=output,
        save=save,
    )
    _tool_query_with_context(context)


@tool.command("query")
@click.option(
    "--tool",
    required=True,
    type=click.Choice(["diogenes", "whitakers", "heritage", "cdsl", "cltk"]),
    help="Backend tool to invoke",
)
@click.option(
    "--action",
    required=True,
    type=click.Choice(
        [
            "parse",
            "search",
            "morphology",
            "dictionary",
            "lookup",
            "canonical",
            "lemmatize",
        ]
    ),
    help="Action to perform",
)
@click.option("--lang", help="Language code (required for diogenes/cltk)")
@click.option("--query", required=True, help="Word to query")
@click.option("--dict", "dict_name", help="Dictionary ID (for heritage/cdsl)")
@click.option(
    "--output", type=click.Choice(["json", "pretty", "yaml"]), default="json", help="Output format"
)
@click.option("--save", help="Save output to fixture file")
@click.pass_context
def tool_query(ctx, **kwargs):  # noqa: PLR0913
    """Generic tool query interface for all backend tools."""
    context = ToolQueryContext(
        tool=kwargs["tool"],
        action=kwargs["action"],
        lang=kwargs.get("lang"),
        query=kwargs["query"],
        dict_name=kwargs.get("dict_name"),
        output=kwargs.get("output", "json"),
        save=kwargs.get("save"),
    )
    _tool_query_with_context(context)


def _tool_query_with_context(context: ToolQueryContext):
    """Generic tool query implementation."""
    # import json
    # from pathlib import Path

    url = f"{DEFAULT_API_URL}/api/tool/{context.tool}/{context.action}"
    params = {}

    if context.lang:
        params["lang"] = context.lang
    if context.query:
        params["query"] = context.query
    if context.dict_name:
        params["dict"] = context.dict_name

    # Make the request
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()

        # result = orjson.loads(response.text)

        # Format output
        if context.output in ["pretty", "yaml"]:
            raise NotImplementedError("Only JSON passthrough supported")
        else:  # json
            print(response.text)
            # console.print(response.text)

        # Save to fixture if requested
        if context.save:
            raise NotImplementedError("Only JSON passthrough supported")
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


@indexer.command("query-cts")
@click.argument("abbrev")
@click.option("--language", "-l", default="lat", help="Language code")
def query_cts(abbrev: str, language: str):
    """Query CTS URN index for abbreviation matches."""
    from langnet.indexer.utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    config = manager.get_index_config("cts_urn")

    if not config:
        click.echo("❌ CTS URN index not found. Run 'langnet-cli indexer build-cts' first.")
        return 1

    output_path = Path(config["path"])
    if not output_path.exists():
        click.echo("❌ CTS URN index file not found")
        return 1

    # Query the index
    indexer_obj = CtsUrnIndexer(output_path, config)
    try:
        results = indexer_obj.query_abbreviation(abbrev, language)

        if not results:
            click.echo(f"❌ No matches found for '{abbrev}'")
        else:
            click.echo(f"🔍 Results for '{abbrev}':")
            for result in results:
                click.echo(f"  {result}")

    except Exception as e:
        click.echo(f"❌ Query error: {e}")
        return 1
    finally:
        indexer_obj.cleanup()

    return 0


@indexer.command("validate-cts")
@click.option("--fix", is_flag=True, help="Attempt to fix issues")
def validate_cts(fix: bool):
    """Validate CTS URN index integrity."""
    from langnet.indexer.utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    config = manager.get_index_config("cts-urn")

    if not config:
        click.echo("❌ CTS URN index not found")
        return 1

    output_path = Path(config["path"])
    if not output_path.exists():
        click.echo("❌ CTS URN index file not found")
        return 1

    # Validate the index
    indexer_obj = CtsUrnIndexer(output_path, config)
    try:
        is_valid = indexer_obj.validate()

        if is_valid:
            click.echo("✅ Index validation passed")
        else:
            click.echo("❌ Index validation failed")
            if fix:
                click.echo("💡 Fix mode not implemented yet")
            return 1

    except Exception as e:
        click.echo(f"❌ Validation error: {e}")
        return 1
    finally:
        indexer_obj.cleanup()

    return 0
