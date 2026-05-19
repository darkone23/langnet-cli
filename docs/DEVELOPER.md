# Developer Guide

This guide describes the current development workflow for `langnet-cli`.

## Ground Rules

- Prefer `just` recipes over ad-hoc commands.
- Keep changes small and testable.
- Do not add live-service dependencies to unit tests.
- Put temporary local debugging files under `examples/debug/`.
- Restart long-running server/process-manager jobs after Python code changes.

## Environment

```bash
devenv shell
```

Most recipes enter the environment themselves:

```bash
just cli --help
just lint-all
just test-fast
```

Routine recipes avoid forwarding variadic arguments through `devenv shell`.
`just cli ...` routes through `.justscripts/run-langnet-cli`; tests, linting,
typechecking, benchmarks, and helper scripts route through
`.justscripts/run-dev-tool`. Run Just/devenv recipes sequentially when auditing
recipe health.

External services are managed outside these recipes, typically in the user's
process-compose session. Treat `just cli doctor --output json` and targeted
integration checks as readiness probes; do not assume routine recipes own
service lifecycle.

## Validation

Use the narrowest relevant test first, then broaden.

```bash
# One module
just test tests.test_whitakers_triples

# Fast suite
just test-fast

# Formatting, linting, and type checking
just lint-all
```

`just lint-all` runs:

- `just ruff-format --check`
- `just ruff-check`
- `just typecheck`

Use `just ruff-format` when formatting changes are expected.

## CLI Debugging

```bash
just cli lookup lat lupus --output pretty
just cli lookup lat lupus --output json

just cli parse whitakers lat amarem --format json
just cli parse diogenes lat lupus --format pretty

just cli normalize san agni
just cli plan lat lupus
just cli plan-exec lat lupus
just triples-dump lat lupus whitakers

just cli encounter lat cano gaffiot
just cli encounter san karman dico
just cli word-of-day san --output json
just cli recommend-words grc --count 3 --output json
just cli translation-warm lat examples/debug/latin_words.txt --tool-filter gaffiot --dry-run
just cli translation-cache clear --source-lexicon bailly --status error --headword logos --yes
```

Use `--translation-mode auto` only when you intentionally want to populate
missing DICO/Gaffiot/Bailly translations through OpenRouter. It may be slow on long
entries and requires `OPENAI_API_KEY` on cache misses. The default translation
model is `openai:google/gemini-2.5-flash`, with
`openai:deepseek/deepseek-v4-flash` as the default fallback on provider failures,
empty responses, or slow completed responses. Override with `--translation-model`
when comparing model quality or cost. Cache-only reads do not call the model;
successful cache rows are reusable across compatible models for the same source,
prompt, and hint, while writes remain model-stamped for provenance. If a row is
stuck in `error`, clear that targeted row and run `translation-warm` or
`encounter --translation-mode auto` to rebuild it.
Set `LANGNET_TRANSLATION_FALLBACK_MODELS` to a comma-separated model list when
translation warming should retry a different provider/model after an empty
response, slow completed response, or provider exception from the primary model.
`LANGNET_TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND` sets the minimum accepted
completed-output rate before falling through to the next model; use
`LANGNET_TRANSLATION_MIN_RATE_TOKENS` and `LANGNET_TRANSLATION_MIN_RATE_SECONDS`
to keep very small or very fast responses from tripping that budget. Cache
population validates deterministic transport/shape failures such as empty
responses and Bailly block/schema mismatches. It does not reject translations
with repeated source n-grams; quality review should be handled by explicit cache
invalidation and re-warming.

## Runtime Pipeline

The staged runtime is:

```text
normalize → plan → fetch → extract → derive → claim
```

Important modules:

- `src/langnet/cli.py` — Click command surface.
- `src/langnet/planner/core.py` — language-aware tool-plan construction.
- `src/langnet/execution/executor.py` — staged plan execution.
- `src/langnet/execution/handlers/` — backend handlers.
- `src/langnet/execution/effects.py` — raw/extraction/derivation/claim dataclasses.
- `src/langnet/storage/` — DuckDB-backed indexes and cache tables.

## Handler Development

A real handler usually has three functions:

1. `extract_*`: raw response → structured extraction.
2. `derive_*`: extraction → normalized derivation.
3. `claim_*`: derivation → evidence-backed claims/triples.

Expectations:

- Use `@versioned(...)` when handler output semantics change.
- Preserve raw payload references in extraction/claim values where useful.
- Put provenance in `provenance_chain` and triple `metadata.evidence`, not in anchor IDs.
- Add a service-free fixture test for each handler behavior.

See `docs/handler-development-guide.md` for the detailed pattern.

## Claim Contract Tests

Use `tests/claim_contract.py` for shared assertions:

- claim IDs and source fields are present
- triples contain `subject`, `predicate`, and `object`
- evidence links back to call, derivation, and claim IDs

Examples:

- `tests/test_whitakers_triples.py`
- `tests/test_cdsl_triples.py`
- `tests/test_claim_contracts.py`

## External Services

Live lookup may require:

- Diogenes at `localhost:8888`
- Sanskrit Heritage at `localhost:48080`
- Whitaker's Words at `~/.local/bin/whitakers-words`
- CLTK model data in `CLTK_DATA` or writable `~/cltk_data`; the CLTK fetch client uses `data/cache/cltk_data` only as a fallback
- CDSL DuckDB data built locally

Unit tests should not require these services unless explicitly marked.

## Storage and Cache

Runtime data lives under the project’s configured cache/data paths. Use project recipes and CLI commands to inspect or clear it.

Relevant docs:

- `docs/storage-schema.md`
- `docs/technical/ARCHITECTURE.md`

## Documentation Workflow

- Update `docs/PROJECT_STATUS.md` when the project grade or major gap changes.
- Update `docs/ROADMAP.md` only for milestone-level direction.
- Put implementation task lists under `docs/plans/`.
- Move stale session reports and superseded plans to `docs/archive/`.

## AI Persona Workflow

The repo uses OpenRouter/OpenCode persona conventions documented in `AGENTS.md`:

- `@architect` for design and sequencing.
- `@coder` for implementation.
- `@sleuth` for debugging.
- `@artisan` for style/optimization.
- `@scribe` for docs.
- `@auditor` for review and edge cases.

These are process conventions. They do not replace code review or tests.
