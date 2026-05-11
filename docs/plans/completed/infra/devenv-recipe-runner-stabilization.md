# Devenv Recipe Runner Stabilization Record

**Date:** 2026-05-05
**Status:** done
**Feature Area:** infra
**Owner Roles:** @architect for recipe boundary, @coder for runner wiring, @auditor for regression checks

## Goal

Make routine Just recipes safe to run as isolated client commands while external services remain owned by the user's process-compose session.

## Scope

- Add `.justscripts/run-dev-tool` for non-CLI tools such as `nose2`, `ruff`, `ty`, and `python`.
- Keep `.justscripts/run-langnet-cli` as the CLI entrypoint wrapper.
- Update non-destructive recipes to avoid variadic `devenv shell -- ... "$@"`.
- Keep destructive/service recipes clearly marked; do not take over process-compose service lifecycle.
- Add text-level regression tests that catch reintroduction of fragile variadic forwarding.

## Steps

1. Add failing tests in `tests/test_cli_concurrency_contract.py`: **done**
   - assert routine variadic recipes do not contain `devenv shell -- ... "$@"`;
   - assert parse/triples helper recipes route through `.justscripts/run-langnet-cli`;
   - assert the new runner prefers `.devenv/state/venv/bin`.
2. Add `.justscripts/run-dev-tool`: **done**
   - set repo `PYTHONPATH`;
   - bootstrap `devenv shell -- true` only when the requested venv executable is missing;
   - execute the venv executable directly when present;
   - fall back to `devenv shell -- <tool> ...` only after direct lookup fails.
3. Update `justfile`: **done**
   - tests, lint, typecheck, benchmark, autobot, and translate-lex use `run-dev-tool`;
   - parse, diogenes-parse, and triples-dump use `run-langnet-cli`.
4. Update docs that describe recipe health if wording changes: **done**
5. Verify sequentially:
   - targeted contract tests;
   - representative recipe smoke tests;
   - `just validate-stabilization`.

## Outcome

Routine test, lint, typecheck, benchmark, helper, parse, and triples inspection
recipes now avoid variadic `devenv shell -- ... "$@"` forwarding. Services
remain outside recipe ownership and should stay running in the user's
process-compose session. Health audits should run Just/devenv recipes
sequentially.

## Verification

- `just test test_cli_concurrency_contract test_cli_help test_cli_doctor`
- `just ruff-format --check`
- `just ruff-check`
- `just typecheck`
- `just benchmark`
- `just parse cdsl san agni mw`
- `just triples-dump san agni cdsl`
- `just diogenes-parse --help lupus`
- `just validate-stabilization`
- `just cli doctor --output json`
- `just test tests.integration.test_live_services tests.integration.test_canonical_pipeline tests.integration.test_diogenes_canonical`
