# Opencode Skills

This directory contains opencode skills for langnet-cli development.

## Available Skills

### Core Development
- [testing.md](testing.md) - Running tests, debugging test failures
- [data-models.md](data-models.md) - Creating dataclass models with cattrs
- [code-style.md](code-style.md) - Formatting, linting, type checking

### Backend Development
- [backend-integration.md](backend-integration.md) - Adding new language data providers
- [api-development.md](api-development.md) - Starlette ASGI API development

### Operations
- [cache-management.md](cache-management.md) - Managing DuckDB response cache
- [debugging.md](debugging.md) - Troubleshooting common issues

### User Interface
- [cli-development.md](cli-development.md) - Click CLI command development

## Using Opencode with This Project

To ask opencode to perform a specific task, reference the skill directly:

```
Using the testing.md skill, run the test suite and report any failures.
```

```
Following the backend-integration.md skill, create a new backend for Old Norse.
```

```
Using the debugging.md skill, help me troubleshoot why the Diogenes backend is not responding.
```

## Quick Reference

For new contributors:
1. Read [code-style.md](code-style.md) - Understand coding conventions
2. Read [testing.md](testing.md) - Learn how to run tests
3. Read [debugging.md](debugging.md) - Common troubleshooting

For adding features:
1. Read [backend-integration.md](backend-integration.md) - Add a new backend
2. Read [data-models.md](data-models.md) - Create proper data models
3. Read [api-development.md](api-development.md) - Wire into the API

For maintenance:
1. Read [cache-management.md](cache-management.md) - Manage the cache
2. Read [debugging.md](debugging.md) - Troubleshoot issues
3. Read [cli-development.md](cli-development.md) - Add CLI commands
