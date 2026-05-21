# Just Recipe Health

LangNet uses `just` as the maintained entry point for local development,
verification, and CLI probes. Prefer these wrappers over calling tool binaries
directly, because the wrappers activate the project environment consistently.

## Routine Commands

```bash
just test test_foster_pedagogy
just test-fast
just lint-all
just typecheck
```

## CLI Probes

Use `just cli` for ordinary CLI checks:

```bash
just cli encounter san putraa.naam heritage --include-paradigm-resolution --output json --translation-mode off
just cli encounter lat puellae whitakers --include-paradigm-resolution --output json --translation-mode off
just cli paradigm grc lo/gos --kind declension --output json
```

## Parser And Triple Helpers

Use the maintained helper recipes when inspecting backend parser or triple
output:

```bash
just parse diogenes grc logos
just triples-dump grc logos diogenes
```

These commands keep documentation examples aligned with the current `justfile`
and avoid stale shell-wrapper patterns.
