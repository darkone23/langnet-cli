# Reader Attribution Claims Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve ambiguous or competing authorship traditions as queryable metadata without polluting canonical display authors.

**Architecture:** Add a separate curated attribution-claims layer alongside display metadata overlays. Claims are loaded from YAML, registered into the reader catalog, exposed through `ReaderService`, and listed with a `reader attributions` CLI command. Accepted claims do not mutate `works.author`; only accepted metadata overlays do that.

**Tech Stack:** Python dataclasses, strict local YAML-line parser matching the existing overlay parser style, DuckDB catalog tables, Click CLI, `just test`, `nu` for command-output inspection.

---

### Task 1: Attribution Claim Models And Loader

**Files:**
- Modify: `src/langnet/reader/models.py`
- Create: `src/langnet/reader/metadata_attribution.py`
- Test: `tests/test_reader_metadata_attribution.py`

- [x] Add `ReaderMetadataAttribution` using existing `ReaderMetadataOverlayEvidence` for evidence.
- [x] Add a strict YAML loader for files shaped like:

```yaml
attributions:
  - collection_id: "sanskrit_dcs"
    match_field: "source_id"
    match_value: "dcs_example"
    relation_type: "possible_author"
    agent: "Aristotle"
    status: "accepted"
    confidence: "medium"
    note: "Accepted as a recorded attribution claim, not as display metadata."
    evidence:
      - source_type: "web_source"
        citation: "https://example.org/source"
        label: "Source records the attribution."
        retrieved_at: "2026-05-13"
```

- [x] Supported match fields: `source_id`, `work_id`, `cts_work_urn`.
- [x] Supported relation types: `attributed_author`, `possible_author`, `traditional_author`, `misattributed_author`, `translator`, `commentator`, `editor`, `redactor`, `compiler`.
- [x] Supported statuses: `candidate`, `accepted`, `rejected`, `needs_review`.
- [x] Supported confidence values: `high`, `medium`, `low`.
- [x] Run `just test test_reader_metadata_attribution` and verify the loader tests pass.

### Task 2: Catalog Storage And Builder Registration

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/reader/builder.py`
- Modify: `src/langnet/cli_databuild.py`
- Test: `tests/test_reader_storage.py`
- Test: `tests/test_reader_builder_cli.py`

- [x] Add a `metadata_attributions` catalog table with one row per evidence item.
- [x] Add `register_metadata_attributions()`.
- [x] Add `list_metadata_attributions()` with filters for collection, status, relation type, agent, and match value.
- [x] Load attributions in `ReaderBuilder` from `ReaderBuildConfig.metadata_attribution_dir`.
- [x] Register attributions during catalog creation.
- [x] Add `--metadata-attribution-dir`, defaulting to `data/curated/reader_attributions`.
- [x] Prove old catalogs without the table return an empty attribution list.
- [x] Prove a build registers accepted attribution claims while leaving `works.author` unchanged.

### Task 3: CLI Discovery

**Files:**
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_reader_builder_cli.py`

- [x] Add `ReaderService.attributions()`.
- [x] Add `reader attributions` command.
- [x] Support filters: `--collection`, `--status`, `--relation-type`, `--agent`, `--match-value`, `--limit`, `--output`.
- [x] Pretty output should show collection, status, match target, relation type, agent, and confidence.
- [x] JSON output should include evidence fields for source and review workflows.

### Task 4: Curated Seed And Documentation

**Files:**
- Create: `data/curated/reader_attributions/sanskrit/traditional_authorship.yaml`
- Modify: `docs/READER_CLI_BEGINNER_GUIDE.md`
- Modify: `examples/debug/reader-audit/NOTES.md`

- [ ] Add one seed attribution pair that demonstrates the Aristotle-or-Avicenna pattern only if a real local work and evidence have been verified.
- [x] If no verified Aristotle-or-Avicenna local work is available yet, document the pattern without adding fabricated claims.
- [x] Add real Sanskrit DCS claims for traditional/probable/name-ambiguous authorship where the work and evidence are already verified.
- [x] Add beginner-guide examples for `reader attributions`.
- [x] Add audit notes explaining when to use display overlays vs attribution claims.

### Task 5: Verification

**Files:**
- Test-only and generated audit outputs under `examples/debug/reader-audit`.

- [x] Run focused tests:

```bash
just test test_reader_metadata_attribution test_reader_storage test_reader_builder_cli
```

- [x] Run related reader tests:

```bash
just test test_reader_metadata_overlay test_reader_author_normalization test_reader_validation test_reader_cli
```

- [x] Validate a tiny fixture build with attribution claims:

```bash
just cli reader --catalog <fixture-catalog> attributions --output json
```

- [x] Validate a tiny real DCS subset with attribution claims enabled and display overlays disabled:

```bash
just cli-databuild reader --sanskrit-dir examples/debug/reader_attributions_seed_source --metadata-overlay-dir examples/debug/empty_reader_metadata --metadata-attribution-dir data/curated/reader_attributions --output-root examples/debug/reader_attributions_seed_verify
just cli reader --catalog examples/debug/reader_attributions_seed_verify/catalog.duckdb works --output json
just cli reader --catalog examples/debug/reader_attributions_seed_verify/catalog.duckdb attributions --match-value dcs_354 --output json
```

- [ ] After full catalog rebuilds finish, validate that attribution claims are queryable without changing canonical author/title output.

### Completed Verification So Far

- `just test test_reader_metadata_attribution test_reader_storage test_reader_builder_cli`
  - 31 tests OK.
- `just test test_reader_metadata_attribution test_reader_storage test_reader_builder_cli test_reader_validation test_reader_metadata_overlay test_reader_author_normalization test_reader_cli test_cli_help`
  - 66 tests OK after validator regex refinements and curated-attribution schema coverage.
- `just cli reader --catalog examples/debug/reader_perseus_full_curated_current/catalog.duckdb validate --output json > examples/debug/reader-audit/perseus_full_curated_validate_strict_final.json`
  - Strict Perseus validation issue count is 0.
- Real DCS attribution proof build:
  - 6 works, 6 artifacts, 1,201 segments, source error count 0.
  - Display overlays disabled; all six proof works remain `author = Unknown`.
  - `reader attributions --match-value dcs_354` returns separate Kauṭilya and Chanakya claims.
  - Validation issue count is 0.
- `just ruff-format --check`
  - 243 files already formatted.
- `just ruff-check`
  - All checks passed.
