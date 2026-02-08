# CTS Indexer Rebuild (Perseus-Based)

Owners: @architect for design, @coder for implementation, @sleuth for validation, @scribe for docs, @auditor for review

## Context
- Current CTS indexer depends on legacy `authtab`/PHI/TLG `.idt` parsing and produces `lat`-prefixed URNs that miss PHI ids and mislabel works (e.g., Horace, Cicero “Orator”).
- We have the Perseus CTS corpus locally at `~/perseus` with canonical metadata:
  - Latin: `~/perseus/canonical-latinLit/data/**/__cts__.xml` (382 files sampled)
  - Greek: `~/perseus/canonical-greekLit/data/**/__cts__.xml` (structure mirrors Latin; needs full pass)
  - Each textgroup directory has `__cts__.xml` with `urn="urn:cts:{latinLit|greekLit}:...` + `<ti:groupname>` (author).
  - Each work subdirectory has `__cts__.xml` with `urn="urn:cts:{latinLit|greekLit}:...` + `<ti:title>`; editions list `*.perseus-*.xml`.
- Goal: rebuild the CTS indexer to source authoritative author/work data from Perseus CTS XML, drop the `.idt`/`authtab` path, and fix URN→metadata resolution.

## Non-Goals
- Do not change upstream Perseus data.
- Do not alter Diogenes scraping; only the indexer + mapper + tests.

## Plan (actionable)
1. **Schema & Data Model (@architect)**
   - Normalize DuckDB tables keyed by `cts_urn`: `authors (author_urn, author_name, language)`, `works (work_urn, work_title, author_urn, language)`, `editions (edition_urn, edition_label, work_urn, source_path)`.
   - Alias table for abbreviated display labels (e.g., `or` → `Orator`) with soft matching; avoid phi/lat rewrite hacks.
   - Indexes on `cts_urn`, `author_name`, `work_title` for fast resolution; document the intended query shapes for the mapper.

2. **Perseus Parser Prototype (@coder)**
   - Walk both corpora: `~/perseus/canonical-latinLit/data/**/__cts__.xml` and `~/perseus/canonical-greekLit/data/**/__cts__.xml`.
   - Extract: textgroup URN, `<ti:groupname>`; work URN, `<ti:title>`; edition URNs, `<ti:label>` and file path; language tag inferred from corpus root.
   - Emit preview artifacts (CSV/JSON) with a few Latin and Greek samples for unit fixtures; include at least one multi-work author and one multi-edition work.

3. **Indexer Rebuild & CLI (@coder)**
   - Replace `.idt` ingestion with Perseus parser output; parameterize corpus root (default `~/perseus`), keep path override via env/CLI flag.
   - Recreate DuckDB schema and indexes; add explicit wipe step to delete existing `~/.local/share/langnet/cts_urn.duckdb` before rebuild.
   - Extend `just` recipe (and `langnet-cli index cts`) to perform: remove old DB → parse Perseus → load tables → verify counts → report summary.
   - Remove legacy `.idt`/`authtab` parsing modules and references once the new path is wired.

4. **Mapper Improvements (@architect @coder)**
   - Switch `CTSUrnMapper` to query the new schema using native URNs; drop phi→lat fallbacks.
   - Use `citation_text` tokens to select the correct work when an author has multiple works; prefer exact title/label matches and fall back to aliases.
   - Provide graceful “unknown” responses instead of mismatched titles; surface edition label when available.

5. **Validation (@sleuth @auditor)**
   - Golden checks (real DB): Horace `urn:cts:latinLit:phi0893.phi004` → Sermones; Cicero `phi0474.phi035` → Orator; Homer `urn:cts:greekLit:tlg0012.tlg001` → Iliad; one multi-edition Latin work.
   - Unit tests: parser fixture for Latin + Greek `__cts__.xml` samples; mapper regression tests using a small temp DB built from the preview fixtures.
   - Integration test: `just cli query lat ...` with a CTS URN and citation hint to confirm end-to-end resolution.

6. **Docs & Cleanup (@scribe)**
   - Update `docs/DEVELOPER.md` and tests/README with the new rebuild workflow and required corpus path.
   - Document the `just`/CLI commands, wipe requirement, and sample outputs.
   - Remove stale `.idt`/`authtab` mentions from code comments and docs.

## Risks / Open Questions
- Corpus completeness: confirm Greek corpus present and consistent; handle missing `groupname`/`title` gracefully.
- Edition selection: decide whether to surface edition labels or just canonical work titles.
- Performance: ensure DuckDB load stays reasonable; consider batching and indexes on `cts_urn` and `author_name`.

## Next Actions (handoff checklist)
- [ ] Confirm corpus presence at `~/perseus` (both latinLit and greekLit) and count of `__cts__.xml` files.
- [ ] Finalize DuckDB schema + alias strategy and write a short ER diagram/table spec.
- [ ] Build parser prototype over a small subset and capture preview CSV/JSON fixtures.
- [ ] Implement CLI/`just` rebuild that wipes and rebuilds `~/.local/share/langnet/cts_urn.duckdb`.
- [ ] Swap mapper to the new schema and add hint-driven disambiguation tests.
- [ ] Update docs and remove `.idt`/`authtab` references.

## Deliverables
- New DuckDB index built from Perseus CTS metadata.
- Updated `CTSUrnMapper` and tests using real DB.
- Developer docs describing rebuild steps and data source.
