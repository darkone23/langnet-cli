"""
AI model routing commands for the autobot tool.
Provides commands to help select appropriate AI personas for different tasks.
"""

from __future__ import annotations

import json
import os
from typing import Any

import click
from rich.console import Console
from rich.table import Table

console = Console()

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

PersonaConfig = dict[str, Any]
PersonaMatrix = dict[str, PersonaConfig]

PERSONA_MATRIX: PersonaMatrix = {
    "architect": {
        "model": "deepseek/deepseek-v3.2",
        "openrouter_id": "deepseek/deepseek-v3.2",
        "description": "System Design, Planning - High reasoning for complex logic",
        "temperature": None,
        "reasoningEffort": "high",
        "task_types": [
            "architecture design",
            "system planning",
            "schema design",
            "complex logic",
            "data model design",
        ],
    },
    "sleuth": {
        "model": "z-ai/glm-4.7",
        "openrouter_id": "z-ai/glm-4.7",
        "description": "Debugging, Root Cause - Conservative, less hallucination",
        "temperature": 0.1,
        "task_types": [
            "debugging",
            "troubleshooting",
            "root cause analysis",
            "performance investigation",
            "bug fixing",
        ],
    },
    "artisan": {
        "model": "minimax/minimax-m2.1",
        "openrouter_id": "minimax/minimax-m2.1",
        "description": "Optimization, Style - High throughput, 200K+ context for rewriting",
        "temperature": 0.2,
        "task_types": [
            "code refactoring",
            "performance optimization",
            "code style improvements",
            "large-scale changes",
            "memory optimization",
        ],
    },
    "coder": {
        "model": "z-ai/glm-4.5-air",
        "openrouter_id": "z-ai/glm-4.5-air",
        "description": "Feature Build, Tests - Fast execution with reliable tool-use",
        "temperature": 0.3,
        "task_types": [
            "implementation",
            "feature development",
            "testing",
            "API development",
            "CLI development",
        ],
    },
    "scribe": {
        "model": "xiaomi/mimo-v2-flash",
        "openrouter_id": "xiaomi/mimo-v2-flash",
        "description": "Docs, Comments - Ultra-low cost for high-volume English prose",
        "temperature": 0.4,
        "task_types": [
            "documentation",
            "code comments",
            "user guides",
            "API documentation",
            "prose writing",
        ],
    },
    "auditor": {
        "model": "openai/gpt-oss-120b",
        "openrouter_id": "openai/gpt-oss-120b",
        "description": "Code Review, Security - Peak instruction following for edge cases",
        "temperature": 0.1,
        "task_types": [
            "code review",
            "security analysis",
            "edge case testing",
            "quality assurance",
            "vulnerability checking",
        ],
    },
}

SKILL_PERSONA_MAP: dict[str, str] = {
    "backend-integration": "architect",
    "data-models": "architect",
    "api-development": "coder",
    "testing": "coder",
    "debugging": "sleuth",
    "code-style": "artisan",
    "cache-management": "artisan",
    "cli-development": "coder",
    "multi-model-ai": "coder",
    "persona-routing": "coder",
}


def get_openrouter_config() -> bool:
    """Get OpenRouter configuration from environment or provide guidance.

    Note: This is for the autobot tooling (external Python scripts).
    Opencode AI access uses separate credentials via `/connect`.
    """
    api_base = os.environ.get("OPENAI_API_BASE")
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_base or OPENROUTER_API_BASE not in api_base:
        console.print("[yellow]OpenRouter not configured in environment[/yellow]")
        console.print(
            "[dim]Note: This is for autobot tooling. "
            "Opencode uses separate /connect credentials.[/dim]"
        )
        console.print("Add to your shell config (.bashrc/.zshrc):")
        console.print(f"  export OPENAI_API_BASE={OPENROUTER_API_BASE}")
        console.print("  export OPENAI_API_KEY=your_openrouter_key")
        return False

    if not api_key:
        console.print("[yellow]OpenRouter API key not set[/yellow]")
        console.print(
            "[dim]Note: This is for autobot tooling. "
            "Opencode uses separate /connect credentials.[/dim]"
        )
        console.print("Add to your shell config:")
        console.print("  export OPENAI_API_KEY=your_openrouter_key")
        return False

    return True


@click.group()
def model():
    """AI model routing and persona management."""
    pass


@model.command()
def list():
    """List all available AI personas and their configurations."""
    table = Table(title="AI Persona Matrix", show_header=True, header_style="bold magenta")
    table.add_column("Persona", style="cyan", width=15)
    table.add_column("Model", style="green", width=40)
    table.add_column("Description", style="white", width=50)
    table.add_column("Temp", style="yellow", width=6)

    for persona_name, config in PERSONA_MATRIX.items():
        temp_str = str(config.get("temperature", "")) if config.get("temperature") else ""
        table.add_row(persona_name, config["model"], config["description"], temp_str)

    console.print(table)

    console.print("\n[yellow]Configuration Status:[/yellow]")
    if get_openrouter_config():
        console.print("  [green]✓ OpenRouter configured[/green]")
    else:
        console.print("  [red]✗ OpenRouter not configured[/red]")


@model.command()
@click.argument("persona")
def select(persona: str):
    """Select a specific AI persona and show configuration command."""
    if persona not in PERSONA_MATRIX:
        console.print(f"[red]Persona '{persona}' not found.[/red]")
        console.print(f"Available personas: {', '.join(PERSONA_MATRIX.keys())}")
        return

    config = PERSONA_MATRIX[persona]

    console.print(f"[cyan]Selected Persona:[/cyan] [bold]{persona}[/bold]")
    console.print(f"[cyan]Model:[/cyan] {config['model']}")
    console.print(f"[cyan]Description:[/cyan] {config['description']}")

    if config.get("temperature"):
        console.print(f"[cyan]Temperature:[/cyan] {config['temperature']}")
    if config.get("reasoningEffort"):
        console.print(f"[cyan]Reasoning Effort:[/cyan] {config['reasoningEffort']}")

    console.print("\n[green]Task Types:[/green]")
    for task_type in config["task_types"]:
        console.print(f"  • {task_type}")

    console.print("\n[yellow]OpenRouter Model ID:[/yellow]")
    console.print(f"  {config['model']}")

    console.print("\n[yellow]Example Usage:[/yellow]")
    if persona == "architect":
        console.print('  @architect "Design a new caching system for the Sanskrit dictionary"')
    elif persona == "sleuth":
        console.print('  @sleuth "Debug the deadlock issue in the Diogenes scraper"')
    else:
        console.print(f'  @{persona} "Write comprehensive tests for the new backend module"')


@model.command()
@click.argument("task_type", nargs=-1, required=True)
def suggest(task_type: tuple):
    """Suggest the best AI persona for a given task type."""
    task_type_str = " ".join(task_type)
    task_type_lower = task_type_str.lower()
    matched_personas = []

    for persona_name, config in PERSONA_MATRIX.items():
        for keyword in config["task_types"]:
            if task_type_lower in keyword.lower() or keyword.lower() in task_type_lower:
                matched_personas.append(persona_name)
                break

    if not matched_personas:
        for persona_name, config in PERSONA_MATRIX.items():
            if any(
                persona_name not in matched_personas
                and any(word in task_type_lower for word in keyword.split())
                for keyword in config["task_types"]
            ):
                matched_personas.append(persona_name)

    if not matched_personas:
        console.print(f"[yellow]No specific persona found for task type: {task_type_str}[/yellow]")
        console.print("[cyan]Defaulting to 'coder' for general implementation tasks[/cyan]")
        matched_personas = ["coder"]

    console.print(f"[cyan]Task Type:[/cyan] [bold]{task_type_str}[/bold]")
    console.print(f"[cyan]Suggested Persona(s):[/cyan] [bold]{', '.join(matched_personas)}[/bold]")

    for persona_name in matched_personas:
        config = PERSONA_MATRIX[persona_name]
        console.print(f"\n[yellow]{persona_name.title()}:[/yellow] {config['description']}")
        console.print(f"  [green]Model:[/green] {config['model']}")


@model.command()
@click.argument("skill_name")
def skill(skill_name: str):
    """Get the recommended AI persona for a specific development skill."""
    skill_name = skill_name.lower().replace(".md", "")

    if skill_name not in SKILL_PERSONA_MAP:
        console.print(f"[red]Skill '{skill_name}' not found.[/red]")
        console.print(f"Available skills: {', '.join(SKILL_PERSONA_MAP.keys())}")
        return

    persona_name = SKILL_PERSONA_MAP[skill_name]
    config = PERSONA_MATRIX[persona_name]

    console.print(f"[cyan]Skill:[/cyan] [bold]{skill_name}[/bold]")
    console.print(f"[cyan]Recommended Persona:[/cyan] [bold]{persona_name}[/bold]")
    console.print(f"[cyan]Model:[/cyan] {config['model']}")
    console.print(f"[cyan]Description:[/cyan] {config['description']}")

    console.print("\n[yellow]Example Usage:[/yellow]")
    console.print(f"  @{persona_name}")

    if skill_name == "backend-integration":
        console.print('  @architect "Design a new Old Norse dictionary backend integration"')
    elif skill_name == "testing":
        console.print('  @coder "Write comprehensive unit tests for the CDSL lookup module"')
    elif skill_name == "debugging":
        console.print('  @sleuth "Investigate the performance bottleneck in the cache system"')
    elif skill_name == "code-style":
        console.print('  @artisan "Refactor the diogenes module to improve code readability"')
    else:
        console.print(f'  @{persona_name} "Implement improvements based on this skill guide"')


@model.command()
def workflow():
    """Show example workflows using multiple AI personas."""
    console.print("[bold cyan]Example: New Feature Development Workflow[/bold cyan]")
    console.print("\n[yellow]Phase 1: Design (Architect)[/yellow]")
    console.print('  @architect "Design new Sanskrit morphology analyzer with caching"')

    console.print("\n[yellow]Phase 2: Implementation (coder)[/yellow]")
    console.print('  @coder "Implement the morphology analyzer following the design"')

    console.print("\n[yellow]Phase 3: Testing (coder)[/yellow]")
    console.print('  @coder "Write comprehensive tests for the new analyzer"')

    console.print("\n[yellow]Phase 4: Documentation (Scribe)[/yellow]")
    console.print('  @scribe "Document the new analyzer API and usage examples"')

    console.print("\n[yellow]Phase 5: Review (Auditor)[/yellow]")
    console.print('  @auditor "Check the implementation for security and edge cases"')

    console.print("\n[bold cyan]Example: Bug Fix Workflow[/bold cyan]")
    console.print("\n[yellow]Phase 1: Investigation (sleuth)[/yellow]")
    console.print('  @sleuth "Debug the memory leak in the DuckDB cache"')

    console.print("\n[yellow]Phase 2: Fix (coder)[/yellow]")
    console.print('  @coder "Implement the memory leak fix"')

    console.print("\n[yellow]Phase 3: Review (Auditor)[/yellow]")
    console.print('  @auditor "Check if the fix introduces any regressions"')


@model.command()
def config():
    """Show current OpenRouter configuration and provide setup guidance."""
    console.print("[bold cyan]OpenRouter Configuration[/bold cyan]")

    api_base = os.environ.get("OPENAI_API_BASE", "")
    api_key_set = bool(os.environ.get("OPENAI_API_KEY", ""))

    if api_base and OPENROUTER_API_BASE in api_base:
        console.print(f"  [green]✓ OPENAI_API_BASE:[/green] {api_base}")
    else:
        console.print("  [red]✗ OPENAI_API_BASE not set correctly[/red]")
        console.print(f"    Expected to contain: {OPENROUTER_API_BASE}")

    if api_key_set:
        console.print("  [green]✓ OPENAI_API_KEY:[/green] [dim](set)[/dim]")
    else:
        console.print("  [red]✗ OPENAI_API_KEY not set[/red]")

    console.print("\n[yellow]Setup Instructions:[/yellow]")
    console.print("Add to your shell config (.bashrc/.zshrc):")
    console.print(f"  export OPENAI_API_BASE={OPENROUTER_API_BASE}")
    console.print("  export OPENAI_API_KEY=your_openrouter_key_here")

    console.print("\n[yellow]Get an API key from:[/yellow] https://openrouter.ai/keys")


@model.command()
@click.option("--output", type=click.Choice(["json", "table"]), default="table")
def export(output: str):
    """Export persona configurations in different formats."""
    if output == "json":
        export_data = {
            "personas": PERSONA_MATRIX,
            "skill_mapping": SKILL_PERSONA_MAP,
            "openrouter": {"api_base": OPENROUTER_API_BASE, "configured": get_openrouter_config()},
        }
        console.print(json.dumps(export_data, indent=2))
    else:
        table = Table(
            title="Skill to Persona Mapping", show_header=True, header_style="bold magenta"
        )
        table.add_column("Skill", style="cyan", width=20)
        table.add_column("Persona", style="green", width=15)
        table.add_column("Model", style="yellow", width=40)

        for skill_name, persona_name in SKILL_PERSONA_MAP.items():
            config = PERSONA_MATRIX[persona_name]
            table.add_row(skill_name, persona_name, config["model"])

        console.print(table)
