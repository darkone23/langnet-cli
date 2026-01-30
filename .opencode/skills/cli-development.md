# CLI Development

Develop CLI commands using Click.

## Entry Point

`src/langnet/cli.py` - Click-based CLI with subcommands

## Adding New Command

```python
@main.command(name="my-command")
@click.argument("required_arg")
@click.option("--optional", default="default", help="description")
@click.option("--flag", is_flag=True, default=False, help="description")
def my_command(required_arg: str, optional: str, flag: bool):
    """Command description for help.

    More detailed description here.

    Examples:
        langnet-cli my-command foo
        langnet-cli my-command foo --optional bar
    """
    # Implementation
    console.print(f"[green]Success![/]")
```

## Built-in Commands

- `query <lang> <word>` - Query a word
- `verify` - Check backend connectivity
- `health` - Alias for verify
- `langs` - List supported languages
- `cache-stats` - Show cache statistics
- `cache-clear` - Clear cache
- `cdsl build` - Build CDSL dictionary index
- `cdsl lookup` - Lookup in CDSL dictionary
- `cdsl prefix` - Autocomplete search
- `cdsl list` - List indexed dictionaries

## CLI Patterns

### Rich Output
```python
from rich.console import Console
from rich.table import Table

console = Console()
console.print("[green]Success![/]")
console.print(f"[red]Error: {message}[/]")
```

### Error Handling
```python
import sys

def my_command(arg: str):
    try:
        result = do_something(arg)
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)
```

### Table Output
```python
table = Table(title="My Data")
table.add_column("Name", style="cyan")
table.add_column("Value", style="green")
table.add_row("Item 1", "100")
console.print(table)
```

### JSON Output (pipable)
```python
@main.command()
@click.option("--output", type=click.Choice(["json", "table"]), default="table")
def my_command(output: str):
    if output == "json":
        sys.stdout.write(json.dumps(data))
        sys.stdout.flush()
    else:
        pprint(data)
```

## Testing CLI Commands

```bash
# Test query command
langnet-cli query lat lupus

# Test with JSON output
langnet-cli query lat lupus --output json | jq '.diogenes'

# Test cache clear
langnet-cli cache-clear --lang san

# Test CDSL lookup
langnet-cli cdsl lookup mw "अग्नि"
```

## CLI vs API

CLI wraps the API endpoints:
- CLI uses HTTP requests to `http://localhost:8000`
- API must be running for CLI to work
- CLI provides user-friendly formatting (tables, colors)
- API returns raw JSON for programmatic access

## Multi-Model AI Persona

**Recommended Persona**: The Implementer (`openrouter/zhipuai/glm-4.5-air:implementer`)

Use this persona for:
- Implementing new CLI commands
- User interface improvements
- Command-line argument parsing
- Rich console output formatting

Example:
```bash
/model openrouter/zhipuai/glm-4.5-air:implementer
"Add a new CLI command to export query results to Markdown format"
```

## Dependencies

Click is installed via poetry: `click = "^8.1.7"`
Rich is installed for formatting: `rich = "^13.9.4"`
