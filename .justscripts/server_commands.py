"""
Server management commands for the autobot tool.
"""

import time

import click
import sh
from rich.console import Console

console = Console()

UVICORN_PORT = 8000
PORT_WAIT_SECONDS = 120
HEALTH_WAIT_SECONDS = 60


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

    def _port_listening() -> bool:
        try:
            check_result = sh.Command("ss")(
                "-tlnp",
                f"sport = :{UVICORN_PORT}",
                _tty=False,
                _tty_out=False,
                _tty_in=False,
            )
            return f":{UVICORN_PORT}" in str(check_result) and "LISTEN" in str(check_result)
        except sh.ErrorReturnCode:
            return False

    # Wait for the old process to drop the port before waiting for the restart.
    console.print("[cyan]Waiting for port to close...[/cyan]")
    for _ in range(PORT_WAIT_SECONDS):
        if not _port_listening():
            break
        time.sleep(1)
    else:
        console.print("[yellow]Port never closed; continuing anyway[/yellow]")

    console.print("[cyan]Waiting for port to become available...[/cyan]")
    for _ in range(PORT_WAIT_SECONDS):
        if _port_listening():
            console.print(f"[green]Port {UVICORN_PORT} is now active[/green]")
            break
        time.sleep(1)
    else:
        console.print(
            f"[yellow]Port {UVICORN_PORT} did not become active within {PORT_WAIT_SECONDS} seconds[/yellow]"
        )

    console.print("[cyan]Waiting for server startup and health...[/cyan]")
    healthy_streak = 0
    for i in range(HEALTH_WAIT_SECONDS):
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
                healthy_streak += 1
                if healthy_streak >= 2:
                    console.print("[green]Server is healthy (HTTP 200)[/green]")
                    break
            if http_code and http_code != "000":
                console.print(f"[yellow]Health check returned HTTP {http_code}, retrying...[/yellow]")
        except sh.ErrorReturnCode:
            pass
        time.sleep(1)
    else:
        console.print(
            f"[yellow]Server health endpoint not reachable within {HEALTH_WAIT_SECONDS} seconds[/yellow]"
        )

    console.print("[cyan]Restart complete[/cyan]")


@server.command()
def verify():
    """Verify the server is running by querying the health endpoint."""
    console.print("[cyan]Verifying server is running...[/cyan]")

    for i in range(10):
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
                return
            console.print(f"[yellow]Server returned: {http_code}, retrying...[/yellow]")
        except sh.ErrorReturnCode as e:
            console.print(f"[yellow]Attempt {i+1}: failed to connect ({e}), retrying...[/yellow]")
        time.sleep(1)

    console.print("[red]Server health check failed after retries[/red]")
