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

import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
import orjson
import requests
from rich.console import Console
from rich.table import Table

from langnet.logging import setup_logging

console = Console()
DEFAULT_API_URL = "http://localhost:8000"


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

        all_healthy = True
        for name, info in components.items():
            comp_status = info.get("status", "unknown")
            message = info.get("message", "")
            status_style = "green" if comp_status == "healthy" else "red"
            if comp_status != "healthy":
                all_healthy = False
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
            f"[red]Error: Invalid language '{lang}'. Must be one of: {', '.join(sorted(valid_languages))}[/]"
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
            from rich.pretty import pprint

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


@main.command(name="cache-stats")
@click.option(
    "--api-url",
    default=DEFAULT_API_URL,
    help="Base URL of the langnet API server",
)
def cache_stats(api_url: str):
    """Show cache statistics including size and entry counts by language.

    Displays cache database size, total entries, and breakdown by language.
    """
    cache_url = f"{api_url}/api/cache/stats"
    try:
        response = requests.get(cache_url, timeout=30)
        response.raise_for_status()
        stats = orjson.loads(response.text)

        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Entries", str(stats.get("total_entries", 0)))
        table.add_row("Database Size", stats.get("total_size_human", "0.0B"))

        console.print(table)

        if stats.get("languages"):
            lang_table = Table(title="By Language")
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Entries", style="green")
            lang_table.add_column("Size", style="yellow")
            for lang_info in sorted(stats["languages"], key=lambda x: -x["entries"]):
                lang_table.add_row(
                    lang_info["lang"],
                    str(lang_info["entries"]),
                    lang_info["size_human"],
                )
            console.print(lang_table)
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


@main.command(name="cache-clear")
@click.option("--lang", default=None, type=str, help="Specific language to clear (lat, grc, san)")
def cache_clear(lang: str | None):
    """Clear the response cache.

    Clears cached query results to ensure fresh data is fetched.

    Options:
        --lang    Clear only specific language cache (lat, grc, san)

    Examples:
        langnet-cli cache-clear           # Clear all caches
        langnet-cli cache-clear --lang san  # Clear only Sanskrit cache
    """
    from langnet.cache.core import QueryCache, get_cache_path

    try:
        cache = QueryCache(get_cache_path())

        if lang:
            count = cache.clear_by_lang(lang)
            console.print(f"[green]Cleared {count} entries from {lang} cache[/]")
        else:
            cache.clear()
            console.print("[green]Cache cleared successfully[/]")
    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/]")
        sys.exit(1)


def get_cdsl_db_dir() -> Path:
    from langnet.config import config

    return config.cdsl_db_dir


def get_cdsl_dict_dir() -> Path:
    from langnet.config import config

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
def build(
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
    from langnet.cologne.core import CdslIndexBuilder

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
    from langnet.cologne.core import batch_build

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

    from langnet.cologne.core import CdslIndex

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
        from rich.table import Table

        table = Table(title=f"Results for '{key}' in {dict_id.upper()}")
        table.add_column("Key", style="cyan")
        table.add_column("L#", justify="right")
        table.add_column("Body", style="green")
        table.add_column("Page", style="yellow")
        for r in results:
            body_preview = (r.body[:100] + "...") if r.body and len(r.body) > 100 else r.body or ""
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
    from langnet.cologne.core import CdslIndex

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
    from langnet.cologne.core import CdslIndex

    db_dir = get_cdsl_db_dir()
    if not db_dir.exists():
        console.print("[yellow]No indexed dictionaries found.[/]")
        console.print("Run 'langnet-cli cdsl build' to create indexes.")
        return

    dbs = sorted(db_dir.glob("*.db"))
    if not dbs:
        console.print("[yellow]No .db files found.[/]")
        return

    from rich.table import Table

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
    from langnet.cologne.core import CdslIndex

    db_path = get_cdsl_db_dir() / f"{dict_id.lower()}.db"
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/]")
        sys.exit(1)

    with CdslIndex(db_path) as index:
        info = index.get_info(dict_id.upper())

    from rich.table import Table

    table = Table(title=f"Dictionary: {info['dict_id']}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Database", info["db_path"])
    table.add_row("Entries", str(info["entry_count"]))
    table.add_row("Headwords", str(info["headword_count"]))
    table.add_row("Size", f"{info['db_size_bytes']} bytes")

    console.print(table)


if __name__ == "__main__":
    main()
