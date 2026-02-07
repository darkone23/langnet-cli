"""
Server management commands for the autobot tool.
"""

import time

import click
import sh
from rich.console import Console

console = Console()

UVICORN_PORT = 8000


@click.group()
def server():
    """Server management commands."""
    pass


@server.command()
def restart():
    """Kill uvicorn and wait for port to be active again."""
    console.print("[cyan]Restarting uvicorn server...[/cyan]")

    # Avoid PTY exhaustion in limited environments by disabling TTY allocation
    sh.Command("pkill")("-f", "uvicorn", _ok_code=[0, 1], _tty=False, _tty_out=False, _tty_in=False)
    console.print("[yellow]Sent pkill to uvicorn processes[/yellow]")

    time.sleep(5)
    console.print("[cyan]Waiting for port to become available...[/cyan]")
    for i in range(30):
        try:
            check_result = sh.Command("ss")(
                "-tlnp",
                f"sport = :{UVICORN_PORT}",
                _tty=False,
                _tty_out=False,
                _tty_in=False,
            )
            if f":{UVICORN_PORT}" in str(check_result) and "LISTEN" in str(check_result):
                console.print(f"[green]Port {UVICORN_PORT} is now active[/green]")
                break
        except sh.ErrorReturnCode:
            pass
        time.sleep(1)
    else:
        console.print(
            f"[yellow]Port {UVICORN_PORT} did not become active within 30 seconds[/yellow]"
        )

    console.print("[cyan]Waiting for server startup...[/cyan]")
    time.sleep(2)

    console.print("[cyan]Restart complete[/cyan]")


@server.command()
def verify():
    """Verify the server is running by querying the health endpoint."""
    console.print("[cyan]Verifying server is running...[/cyan]")

    try:
        result = sh.Command("curl")(
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            f"http://127.0.0.1:{UVICORN_PORT}/api/health",
            _tty=False,
            _tty_out=False,
            _tty_in=False,
        )
        http_code = str(result).strip()

        if http_code == "200":
            console.print("[green]Server is healthy (HTTP 200)[/green]")
        else:
            console.print(f"[yellow]Server returned: {http_code}[/yellow]")
    except sh.ErrorReturnCode as e:
        console.print(f"[red]Failed to connect to server: {e}[/red]")
