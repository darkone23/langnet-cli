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
HEALTHY_STREAK_TARGET = 2


@click.group()
def server():
    """Server management commands."""
    pass


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


def _wait_for_port_to_close() -> None:
    console.print("[cyan]Waiting for port to close...[/cyan]")
    for _ in range(PORT_WAIT_SECONDS):
        if not _port_listening():
            return
        time.sleep(1)
    console.print("[yellow]Port never closed; continuing anyway[/yellow]")


def _wait_for_port_active() -> None:
    console.print("[cyan]Waiting for port to become available...[/cyan]")
    for _ in range(PORT_WAIT_SECONDS):
        if _port_listening():
            console.print(f"[green]Port {UVICORN_PORT} is now active[/green]")
            return
        time.sleep(1)
    console.print(
        f"[yellow]Port {UVICORN_PORT} did not become active within "
        f"{PORT_WAIT_SECONDS} seconds[/yellow]"
    )


def _wait_for_health() -> None:
    console.print("[cyan]Waiting for server startup and health...[/cyan]")
    healthy_streak = 0
    for _ in range(HEALTH_WAIT_SECONDS):
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
                if healthy_streak >= HEALTHY_STREAK_TARGET:
                    console.print("[green]Server is healthy (HTTP 200)[/green]")
                    return
            if http_code and http_code != "000":
                console.print(
                    f"[yellow]Health check returned HTTP {http_code}, retrying...[/yellow]"
                )
        except sh.ErrorReturnCode:
            pass
        time.sleep(1)
    console.print(
        "[yellow]Server health endpoint not reachable within "
        f"{HEALTH_WAIT_SECONDS} seconds[/yellow]"
    )


@server.command()
def restart():
    """Kill uvicorn and wait for port to be active again."""
    console.print("[cyan]Restarting uvicorn server...[/cyan]")

    sh.Command("pkill")("-f", "uvicorn", _ok_code=[0, 1], _tty=False, _tty_out=False, _tty_in=False)
    console.print("[yellow]Sent pkill to uvicorn processes[/yellow]")

    _wait_for_port_to_close()
    _wait_for_port_active()
    _wait_for_health()

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
            console.print(f"[yellow]Attempt {i + 1}: failed to connect ({e}), retrying...[/yellow]")
        time.sleep(1)

    console.print("[red]Server health check failed after retries[/red]")
