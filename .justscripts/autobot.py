#!/usr/bin/env python3
"""
Autobot - Automation tool for langnet-cli development tasks.
"""

import sys
from pathlib import Path

import click
from rich.console import Console

# Add the .justscripts directory to sys.path so we can import ruff_commands
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

console = Console()

try:
    from ruff_commands import ruff  # type: ignore[assignment,attr-defined]
except ImportError:
    ruff = None  # type: ignore[assignment]

try:
    from server_commands import server  # type: ignore[assignment,attr-defined]
except ImportError:
    server = None  # type: ignore[assignment]


@click.group()
def autobot():
    """Automation tool for langnet-cli development tasks."""
    pass


# Add ruff group to autobot if available
if ruff is not None:
    autobot.add_command(ruff, name="ruff")

# Add server group to autobot if available
if server is not None:
    autobot.add_command(server, name="server")


if __name__ == "__main__":
    autobot()
