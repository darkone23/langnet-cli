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

import click
import orjson
import requests
import socket
import sys
from urllib.parse import urlparse
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
    except (socket.timeout, ConnectionRefusedError, OSError):
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
        health_data = response.json()

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
def verify(api_url: str, socket_timeout: float, timeout: float):
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
            result = response.json()
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


if __name__ == "__main__":
    main()
