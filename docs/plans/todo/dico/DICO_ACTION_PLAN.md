# DICO Action Plan

**Goal:** deliver a usable Sanskrit→French/English DICO lookup that plugs into the existing Heritage and DuckDB tooling without adding new model dependencies until data quality is verified.

## Workstream checkpoints
- **Index import (P0):** extract DICO entries via Heritage (`lex=DICO`) into DuckDB with normalized encodings (Devanagari, IAST, SLP1) and stable IDs. Verify with a 50–100 entry spot check.
- **Lookup API (P0):** expose a `dico` tool in the adapter registry that mirrors other backends (`lookup`, `search`) and returns consistent schema (headword, senses, references, source_language).
- **Quality gates (P1):** add fuzz snapshots for 10 representative entries (verbs, compounds, sandhi cases) under `examples/debug/fuzz_results` and a regression test that asserts the schema shape (no optional fields missing).
- **Translation path (P2):** add an offline pipeline to translate `french_definition` → English using an allowed model (see `.opencode/opencode.json`), with manual review before shipping.
- **Pedagogy surfacing (P2):** enrich entries with Foster-style functional labels where the DICO metadata allows it; otherwise keep the raw grammatical hints in `metadata.notes`.

## Done criteria
- `langnet-cli query san <word> --backend dico` returns structured definitions with source info and passes the schema regression test.
- DuckDB index load documented (inputs, commands, expected row count).
- Fuzz snapshots added and reviewed.

## Owners / mentions
- @coder for adapter + schema work
- @sleuth for regression tests + fuzz harness expansion
- @scribe for the DuckDB load/usage documentation
