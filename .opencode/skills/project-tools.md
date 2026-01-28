# Project Tools and Automation

## Overview

This project uses an **autobot** automation tool for managing development tasks. All project-specific automation should be encoded through the autobot tool rather than scattered across various scripts or commands.

## Autobot Tool Structure

The autobot tool is located at `.justscripts/autobot.py` and follows these conventions:

### Command Structure
- Use **Click groups** for organizing related functionality
- Use **Click subcommands** for specific operations
- Maintain **backward compatibility** for existing commands during transitions

### Current Structure
```bash
just autobot                    # Main autobot commands
just autobot ruff               # Ruff-related commands (group)
just autobot ruff check-all     # Check all Python files
just autobot ruff todo          # Show files with issues
just autobot ruff cleanup       # Clean up issue files
```

### Migration Path
Old commands remain available during transitions but show deprecation notices:
```bash
just autobot ruff-check-all     # Deprecated - use autobot ruff check-all
just autobot ruff-todo         # Deprecated - use autobot ruff todo  
just autobot ruff-cleanup      # Deprecated - use autobot ruff cleanup
```

## Adding New Tools

### Requirements
1. **Encode through autobot**: All project automation should be accessible via `just autobot`
2. **Use Click**: Prefer Click library for CLI interfaces over manual argument parsing
3. **Organize in groups**: Group related functionality under logical subcommands
4. **Use subprocess/sh for external tools**: For external command execution, prefer the `sh` library or `subprocess`
5. **Maintain compatibility**: Provide backward compatibility during transitions

### Template for New Tools

```python
@autobot.group()
def mytool():
    """My tool description and functionality."""
    pass

@mytool.command()
@click.option("--option", help="Description of option")
def mycommand(option):
    """Description of what this command does."""
    # Implementation here
    pass
```

### Example: Adding a Test Tool

```python
@autobot.group()
def test():
    """Testing and quality assurance commands."""
    pass

@test.command()
def coverage():
    """Run test coverage report."""
    subprocess.run(["coverage", "report"])
    pass

@test.command()
def lint():
    """Run all linting checks."""
    subprocess.run(["just", "ruff-check", "src/"])
    subprocess.run(["just", "typecheck"])
    pass
```

## External Tool Integration

### Using `sh` Library
For simple external command execution:

```python
import sh

@autobot.command()
def docker_build():
    """Build Docker image."""
    sh.docker.build("-t", "myapp", ".")
```

### Using `subprocess`
For more complex scenarios:

```python
import subprocess

@autobot.command()
def deploy():
    """Deploy application."""
    result = subprocess.run(
        ["deploy-script", "--env", "production"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        click.echo(f"Deploy failed: {result.stderr}")
        return
    click.echo("Deploy successful!")
```

## Best Practices

### 1. Error Handling
- Provide clear error messages
- Use appropriate exit codes
- Handle external command failures gracefully

### 2. User Experience
- Use Click's help system (`--help`)
- Provide progress indicators for long-running operations
- Use colors and formatting appropriately

### 3. Code Organization
- Keep functions small and focused
- Extract reusable logic into helper functions
- Use type hints where appropriate
- Follow the existing styleguide

### 4. Documentation
- Write clear docstrings for all commands
- Include usage examples in help text
- Document command options and their purposes

## Migration Strategy

When adding new functionality:

1. **Add to autobot**: Implement new commands in the autobot tool
2. **Use groups**: Organize related commands under logical groups
3. **Maintain compatibility**: Keep old commands working during transition
4. **Update documentation**: Update project documentation and skills
5. **Gradual deprecation**: Remove old commands after migration period

## Examples of Future Tools

The autobot tool could expand to include:

```bash
just autobot test coverage      # Run coverage
just autobot test unit         # Run unit tests
just autobot build docker      # Build Docker images
just autobot deploy staging    # Deploy to staging
just autobot docs build        # Build documentation
just autobot cache clear       # Clear application caches
```

This structure provides a centralized, extensible automation system that scales with the project while maintaining consistency and usability.