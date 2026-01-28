"""
Ruff automation commands for the autobot tool.
"""

import os
from pathlib import Path

import click
import sh
from rich.console import Console

console = Console()


def _get_python_files(src_only):
    """Get list of Python files to check."""
    py_files = []

    if not src_only:
        py_files.extend(Path("tests").glob("**/*.py"))

    py_files.extend(Path("src").glob("**/*.py"))

    return py_files


def _strip_ansi_codes(text):
    """Remove ANSI color codes from text using basic string replacement."""
    # Common ANSI escape sequences
    ansi_codes = [
        "\x1b[1m",
        "\x1b[0m",
        "\x1b[91m",
        "\x1b[94m",
        "\x1b[96m",
        "\x1b[32m",
        "\x1b[33m",
        "\x1b[31m",
        "\x1b[36m",
    ]

    clean_text = text
    for code in ansi_codes:
        clean_text = clean_text.replace(code, "")

    return clean_text


def _process_file_for_ruff(py_file, todo_dir):
    """Process a single Python file for ruff checking."""
    # Create output filename
    safe_name = str(py_file).replace("/", "_").replace("\\", "_").replace(".py", ".txt")
    output_file = todo_dir / safe_name
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        env = os.environ.copy()
        env["NO_COLOR"] = "1"
        result = sh.Command("just")(
            "ruff-check",
            str(py_file),
            _ok_code=[0, 1, 127],
            _err_to_out=True,
            _env=env,
        )

        # Strip color codes from output (just in case)
        clean_output = _strip_ansi_codes(str(result))

        # Check if output indicates actual issues (not environment errors)
        has_issues = False
        message = f"✓ {py_file} - No issues"

        # Look for actual ruff violations, not environment errors
        lines = clean_output.strip().split("\n")
        violations_found = False
        environment_error = False

        for line_text in lines:
            line = line_text.strip()

            # Check for environment errors (ruff not found, etc.)
            if (
                "ruff: command not found" in line
                or "sh:" in line
                and "not found" in line
                or "error: Recipe" in line
            ):
                environment_error = True
                break

            # Skip empty lines, command headers, and success messages
            if (
                line
                and not line.startswith("ruff check")
                and line != "No issues found"
                and not line.startswith("Found")
                and not line.startswith("All checks passed")
            ):
                violations_found = True
                break

        if environment_error:
            has_issues = True
            message = f"✗ {py_file} - Environment error"
        elif violations_found:
            has_issues = True
            message = f"✗ {py_file} - Issues found"
            with open(output_file, "w") as f:
                f.write(clean_output)
        elif not output_file.exists():
            pass

        return has_issues, message

    except sh.ErrorReturnCode as e:
        # If exit code is 0, no issues found
        if e.exit_code == 0:
            return False, f"✓ {py_file} - No issues"
        else:
            # Other error - write error info
            clean_error = _strip_ansi_codes(str(e))
            with open(output_file, "w") as f:
                f.write(f"Error running ruff-check: {clean_error}\n")
            return True, f"✗ {py_file} - Error: {clean_error}"
    except Exception as e:
        clean_error = _strip_ansi_codes(str(e))
        with open(output_file, "w") as f:
            f.write(f"Error running ruff-check: {clean_error}\n")
        return True, f"Error checking {py_file}: {clean_error}"


def _cleanup_clean_files(py_files, files_with_issues, todo_dir):
    """Clean up output files for files that had no issues."""
    console.print("\n[cyan]Cleaning up files with no issues...[/cyan]")
    for py_file in py_files:
        if py_file not in files_with_issues:
            safe_name = str(py_file).replace("/", "_").replace("\\", "_").replace(".py", ".txt")
            output_file = todo_dir / safe_name
            if output_file.exists():
                output_file.unlink()
                console.print(f"  [green]Removed clean file: {output_file}[/green]")

    # Remove ruff-todo directory if it's empty
    if len(files_with_issues) == 0 and todo_dir.exists():
        todo_dir.rmdir()
        console.print("  [green]Removed empty ruff-todo directory[/green]")


def _print_summary(py_files, files_with_issues, environment_errors=None):
    """Print summary of ruff checking results."""
    if environment_errors is None:
        environment_errors = []

    console.print("\n[cyan]Summary:[/cyan]")
    console.print(f"  [cyan]Files checked:[/cyan] [bold]{len(py_files)}[/bold]")

    if environment_errors:
        console.print(
            f"  [yellow]Environment errors:[/yellow] [bold]{len(environment_errors)}[/bold]"
        )
        console.print("    [dim]ruff command not available in environment[/dim]")

    actual_issues = len(files_with_issues) - len(environment_errors)
    if actual_issues > 0:
        console.print(f"  [red]Files with actual issues:[/red] [bold]{actual_issues}[/bold]")

    files_remaining = len([f for f in files_with_issues if f not in environment_errors])
    console.print(
        f"  [yellow]Files remaining in ruff-todo:[/yellow] [bold]{files_remaining}[/bold]"
    )

    if environment_errors:
        error_files = ", ".join(str(f) for f in environment_errors)
        console.print(f"\n[yellow]Environment errors:[/yellow] {error_files}")

    if files_with_issues and actual_issues > 0:
        actual_issue_files = [f for f in files_with_issues if f not in environment_errors]
        issue_files_str = ", ".join(str(f) for f in actual_issue_files)
        console.print(f"\n[red]Files with actual issues:[/red] {issue_files_str}")


@click.group()
def ruff():
    """Ruff linting and code quality management."""
    pass


@ruff.command()
@click.option("--src-only", is_flag=True, help="Only check src/ directory, not tests/")
def check_all(src_only):
    """Run ruff-check on all Python files and save results to ruff-todo/."""

    # Find all Python files
    py_files = _get_python_files(src_only)

    if not py_files:
        console.print("[yellow]No Python files found to check.[/yellow]")
        return

    console.print(f"[cyan]Found {len(py_files)} Python files to check[/cyan]")
    console.print()

    # Create ruff-todo directory
    todo_dir = Path("ruff-todo")
    todo_dir.mkdir(exist_ok=True)

    files_with_issues = []
    environment_errors = []

    for py_file in py_files:
        has_issues, message = _process_file_for_ruff(py_file, todo_dir)
        if has_issues:
            if "Environment error" in message:
                environment_errors.append(py_file)
            else:
                files_with_issues.append(py_file)

        # Color coding based on issue type
        if "Environment error" in message:
            console.print(f"[yellow]{message}[/yellow]")
        elif has_issues:
            console.print(f"[red]{message}[/red]")
        else:
            console.print(f"[green]{message}[/green]")

    console.print()


@ruff.command()
def todo():
    """Show files that have ruff issues (files in ruff-todo/)."""
    todo_dir = Path("ruff-todo")

    if not todo_dir.exists():
        console.print("[yellow]No ruff-todo directory found.[/yellow]")
        return

    txt_files = list(todo_dir.glob("*.txt"))

    if not txt_files:
        console.print("[yellow]No files with issues found.[/yellow]")
        return

    console.print(f"[cyan]Files with ruff issues ({len(txt_files)}):[/cyan]")
    for txt_file in sorted(txt_files):
        console.print(f"  [cyan]{txt_file}[/cyan]")


@ruff.command()
@click.option("--force", is_flag=True, help="Force cleanup without confirmation")
def cleanup(force):
    """Clean up ruff-todo directory and related files."""
    todo_dir = Path("ruff-todo")

    if not todo_dir.exists():
        console.print("[yellow]No ruff-todo directory found.[/yellow]")
        return

    txt_files = list(todo_dir.glob("*.txt"))

    if not txt_files:
        todo_dir.rmdir()
        console.print("[green]Removed empty ruff-todo directory.[/green]")
        return

    if not force:
        console.print(f"[yellow]Found {len(txt_files)} files with issues in ruff-todo/:[/yellow]")
        for txt_file in sorted(txt_files):
            console.print(f"  [cyan]{txt_file}[/cyan]")

        if click.confirm("Remove all these files and the ruff-todo directory?"):
            for txt_file in txt_files:
                txt_file.unlink()
            todo_dir.rmdir()
            console.print(f"[green]Removed {len(txt_files)} files and ruff-todo directory.[/green]")
    else:
        for txt_file in txt_files:
            txt_file.unlink()
        todo_dir.rmdir()
        console.print(
            f"[green]Force removed {len(txt_files)} files and ruff-todo directory.[/green]"
        )
