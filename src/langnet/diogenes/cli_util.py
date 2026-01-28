#!/usr/bin/env python3

import asyncio
import os

import click
import structlog
from rich import print as rprint
from rich.panel import Panel
from sh import bash

import langnet.logging  # noqa: F401 - ensures logging is configured before use

logger = structlog.get_logger(__name__)


SLEEP_DURATION = 3600


def find_zombie_pids() -> list[int]:
    """
    Finds all Parent PIDs (PPIDs) of 'perl <defunct>' zombie processes.
    Uses a more robust ps format that works across systems.
    """
    cmd = (
        "ps -eo ppid,stat,cmd --no-headers 2>/dev/null | awk '$2 ~ /^Z/ && $3 ~ /perl/ {print $1}'"
    )
    try:
        output = bash("-c", cmd, _encoding="utf-8").strip()  # type: ignore[call-overload]
        if not output:
            return []
        pids = []
        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.isdigit():
                pids.append(int(line))
        return list(set(pids))  # dedupe
    except Exception as e:
        logger.error("zombie_detection_failed", error=str(e))
        return []


def kill_process(pid: int):
    """
    Sends a SIGTERM signal to the given PID.
    """
    try:
        os.kill(pid, 15)  # 15 = SIGTERM
        rprint(f"[green]Zombie Killer: Sent SIGTERM to PID {pid}.[/green]")
    except ProcessLookupError:
        logger.info("zombie_process_gone", pid=pid)
        rprint(f"[yellow]Zombie Killer: PID {pid} no longer exists.[/yellow]")
    except PermissionError:
        logger.error("zombie_kill_permission_denied", pid=pid)
        rprint(f"[red]Zombie Killer: Permission denied to kill {pid}.[/red]")
    except Exception as e:
        logger.error("zombie_kill_failed", pid=pid, error=str(e))


async def run_one_shot():
    """Run a single check and exit."""
    pids = find_zombie_pids()
    if pids:
        logger.info("zombies_found", count=len(pids), pids=pids)
        rprint(
            f"[bold red]Zombie Killer: Found {len(pids)} perl zombie(s) "
            f"with parent PIDs: {pids}[/bold red]"
        )
        for pid in pids:
            kill_process(pid)
    else:
        logger.info("no_zombies_found")
        rprint("[green]Zombie Killer: No perl zombies found.[/green]")


async def main_loop(interval: int = 3600):
    """
    Main service loop - runs indefinitely with periodic checks.
    """
    logger.info("zombie_killer_started", interval=interval)
    rprint(
        Panel(
            f"[bold]Zombie Killer: Service started.[/bold] Checking every {interval}s.",
            expand=False,
        )
    )
    while True:
        pids = find_zombie_pids()

        if pids:
            logger.info("zombies_found", count=len(pids), pids=pids)
            rprint(
                f"[bold red]Zombie Killer: Found {len(pids)} perl zombie(s)"
                f" with parent PIDs: {pids}[/bold red]"
            )
            for pid in pids:
                kill_process(pid)
        else:
            logger.info("no_zombies_found")
            rprint("[yellow]Zombie Killer: No perl zombies found.[/yellow]")

        await asyncio.sleep(interval)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--interval",
    default=3600,
    type=int,
    help="Seconds between checks (default: 3600)",
)
def cli(ctx, interval):
    """Perl zombie process reaper.

    Scans for zombie perl processes, kills their parent, and waits
    for the next check interval. The parent Diogenes server will be
    terminated and requires an external process manager to restart it.

    Usage:
        langnet-dg-reaper                    # loop mode (default interval: 3600s)
        langnet-dg-reaper --interval 1800    # loop mode (30s interval)
        langnet-dg-reaper reap --once        # one-shot mode
    """
    ctx.ensure_object(dict)
    ctx.obj["interval"] = interval
    if ctx.invoked_subcommand is None:
        asyncio.run(main_loop(interval))


@cli.command()
@click.option(
    "--once",
    is_flag=True,
    help="Run a single check and exit (one-shot mode)",
)
def reap(once):
    """Reap zombie perl processes.

    Finds zombie (defunct) perl processes and kills their parent.
    The Diogenes server will be terminated and requires an external
    process manager to restart it.
    """
    try:
        if once:
            asyncio.run(run_one_shot())
        else:
            asyncio.run(main_loop(3600))
    except KeyboardInterrupt:
        logger.info("zombie_killer_shutting_down")
        rprint("[yellow]\nZombie Killer: Shutting down...[/yellow]")


if __name__ == "__main__":
    cli()
