# Type-Checking Cleanup

**Status:** ⏳ TODO  
**Feature Area:** infra  
**Owner Roles:** @artisan for cleanup, @auditor for review

## Goal

Keep `ty` clean as the claim/evidence and semantic-reduction layers evolve.

## Current Baseline

`just lint-all` currently passes. This file is reserved for future type-checking regressions, not active known failures.

## Rules

- Fix root types, not symptoms.
- Prefer explicit `Mapping[str, object]`, `Sequence[...]`, and `TypedDict` where payloads cross handler boundaries.
- Avoid broad `Any` unless a third-party boundary requires it.
- Keep tests type-clean too.

## Validation

```bash
just typecheck
just lint-all
```
