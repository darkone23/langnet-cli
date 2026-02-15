#!/usr/bin/env python3
"""
Diogenes maintenance commands for langnet-cli.
"""

import asyncio
import os

import click
import structlog
from rich import print as rprint
from rich.panel import Panel
from sh import bash

logger = structlog.get_logger(__name__)


def find_zombie_pids() -> list[int]:
    """
    Finds all Parent PIDs (PPIDs) of 'perl <defunct>' zombie processes.
    Uses a more robust ps format that works across systems.
    """
    cmd = (
        "ps -eo ppid,stat,cmd --no-headers 2>/dev/null | awk '$2 ~ /^Z/ && $3 ~ /perl/ {print $1}'"
    )
    try:
        output = bash(
            "-c", cmd, _encoding="utf-8", _tty=False, _tty_out=False, _tty_in=False
        ).strip()
        if not output:
            return []
        pids = []
        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.isdigit():
                pids.append(int(line))
        return list(set(pids))
    except Exception as e:
        logger.error("zombie_detection_failed", error=str(e))
        return []


def kill_process(pid: int):
    """
    Sends a SIGTERM signal to the given PID.
    """
    try:
        os.kill(pid, 15)
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


@click.group()
def diogenes():
    """Diogenes backend maintenance commands."""
    pass


@diogenes.command()
@click.option(
    "--interval",
    default=3600,
    type=int,
    help="Seconds between checks (default: 3600)",
)
@click.option(
    "--once",
    is_flag=True,
    help="Run a single check and exit (one-shot mode)",
)
def reap(interval: int, once: bool):
    """Reap zombie perl processes.

    Finds zombie (defunct) perl processes and kills their parent.
    The Diogenes server will be terminated and requires an external
    process manager to restart it.

    Usage:
        just autobot diogenes reap              # loop mode (default interval: 3600s)
        just autobot diogenes reap --interval 1800  # loop mode (30min interval)
        just autobot diogenes reap --once       # one-shot mode
    """
    try:
        if once:
            asyncio.run(run_one_shot())
        else:
            asyncio.run(main_loop(interval))
    except KeyboardInterrupt:
        logger.info("zombie_killer_shutting_down")
        rprint("[yellow]\nZombie Killer: Shutting down...[/yellow]")
