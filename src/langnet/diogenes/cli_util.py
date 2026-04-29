from __future__ import annotations

import asyncio
import os
import subprocess

import click
import structlog
from rich import print as rprint
from rich.panel import Panel

logger = structlog.get_logger(__name__)

DEFAULT_INTERVAL_SECONDS = 3600


def find_zombie_pids() -> list[int]:
    """Return parent PIDs for defunct Perl processes left by Diogenes."""
    command = [
        "bash",
        "-c",
        "ps -eo ppid,stat,cmd --no-headers 2>/dev/null | awk '$2 ~ /^Z/ && $3 ~ /perl/ {print $1}'",
    ]
    try:
        result = subprocess.run(  # noqa: S603
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        logger.error("zombie_detection_failed", error=str(exc))
        return []

    pids: set[int] = set()
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.isdigit():
            pids.add(int(stripped))
    return sorted(pids)


def kill_process(pid: int) -> None:
    """Send SIGTERM to a parent process that owns zombie Perl children."""
    try:
        os.kill(pid, 15)
        rprint(f"[green]Diogenes reaper: sent SIGTERM to PID {pid}.[/green]")
    except ProcessLookupError:
        logger.info("zombie_process_gone", pid=pid)
        rprint(f"[yellow]Diogenes reaper: PID {pid} no longer exists.[/yellow]")
    except PermissionError:
        logger.error("zombie_kill_permission_denied", pid=pid)
        rprint(f"[red]Diogenes reaper: permission denied for PID {pid}.[/red]")
    except OSError as exc:
        logger.error("zombie_kill_failed", pid=pid, error=str(exc))


async def run_one_shot() -> None:
    """Run one zombie-process scan and exit."""
    pids = find_zombie_pids()
    if not pids:
        logger.info("no_zombies_found")
        rprint("[green]Diogenes reaper: no perl zombies found.[/green]")
        return

    logger.info("zombies_found", count=len(pids), pids=pids)
    rprint(
        f"[bold red]Diogenes reaper: found {len(pids)} perl zombie parent PID(s): {pids}[/bold red]"
    )
    for pid in pids:
        kill_process(pid)


async def main_loop(interval: int = DEFAULT_INTERVAL_SECONDS) -> None:
    """Run periodic zombie-process scans until interrupted."""
    logger.info("zombie_reaper_started", interval=interval)
    rprint(
        Panel(
            f"[bold]Diogenes reaper started.[/bold] Checking every {interval}s.",
            expand=False,
        )
    )
    while True:
        await run_one_shot()
        await asyncio.sleep(interval)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--interval",
    default=DEFAULT_INTERVAL_SECONDS,
    type=int,
    help="Seconds between checks.",
)
def cli(ctx: click.Context, interval: int) -> None:
    """Reap zombie Perl processes left by Diogenes."""
    ctx.ensure_object(dict)
    ctx.obj["interval"] = interval
    if ctx.invoked_subcommand is None:
        asyncio.run(main_loop(interval))


@cli.command()
@click.option(
    "--once",
    is_flag=True,
    help="Run a single check and exit.",
)
def reap(once: bool) -> None:
    """Reap zombie Perl processes."""
    try:
        if once:
            asyncio.run(run_one_shot())
        else:
            asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("zombie_reaper_shutting_down")
        rprint("[yellow]\nDiogenes reaper: shutting down...[/yellow]")
