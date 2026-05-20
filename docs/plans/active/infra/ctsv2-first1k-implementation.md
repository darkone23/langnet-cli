# CTSv2, First1KGreek, And Subtext Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CTSv2 the preferred reader addressing layer, import First1KGreek as source-witness data, and model subtexts/ToC relationships as first-class reader metadata rather than source-ID accidents.

**Architecture:** Keep existing `work_id` storage stable during this changeset, add `canonical_text_id` and preferred CTSv2 addresses as public identity, preserve legacy CTS/TLG/PHI/First1K IDs as aliases/source witnesses, and make the builder resolve source candidates into one visible logical text per canonical ID. First1KGreek enters through the Perseus TEI parser with collection-specific provenance and source-preference suppression of lower-priority legacy duplicates.

**Tech Stack:** Python dataclasses, DuckDB catalog/book artifacts, strict project-local YAML readers, Click CLI, existing reader service/API contracts, `just` verification commands.

---

## Scope

This is one large changeset, but it is implemented additively:

- CTSv2 canonical IDs are added to catalog rows and responses.
- Existing `work_id`, CTS1 URNs, TLG/PHI IDs, and aliases keep resolving.
- First1KGreek is imported as `collection_id = first1kgreek`, not as generic Perseus.
- Exact same-language logical duplicates are suppressed at build time.
- Source witnesses and AKA names are retained as metadata/aliases.
- Contained texts and ToC nodes continue to work and gain CTSv2 preferred addresses.

Changing `works.work_id` itself to CTSv2 is deliberately deferred. This changeset makes CTSv2 the default public address while leaving storage migration optional.

## Files

- Modify: `src/langnet/reader/models.py`
  - Add `canonical_text_id` to `ReaderWork`.
  - Add source-witness and relation dataclasses.
- Create: `src/langnet/reader/ctsv2.py`
  - Mint stable CTSv2 IDs from language, title, and cleaned incipit.
  - Parse CTSv2 resource addresses with query parameters.
  - Build preferred segment addresses.
- Modify: `src/langnet/reader/adapters.py`
  - Allow Perseus-style TEI parsing with caller-provided `collection_id`.
  - Populate canonical IDs after builder-level incipit extraction.
- Modify: `src/langnet/reader/builder.py`
  - Add `first1k_greek_dir`.
  - Import First1KGreek XML text files.
  - Register source witnesses/AKA aliases.
  - Suppress lower-priority legacy duplicates by canonical text ID and CTS work URN.
- Modify: `src/langnet/reader/storage.py`
  - Add `canonical_text_id`, `source_witnesses`, and `work_relations`.
  - Resolve by CTSv2 ID and CTSv2 resource URI.
  - Emit preferred CTSv2 addresses in works, segments, contents, show, maps, and search context helpers.
  - Validate duplicate visible canonical IDs.
- Modify: `src/langnet/reader/service.py`
  - Accept `?ref=` CTSv2 resource addresses in `show`.
  - Keep old address behavior as compatibility.
- Modify: `src/langnet/cli_databuild.py`
  - Add `--first1k-greek-dir`.
- Add/modify tests:
  - `tests/test_reader_ctsv2.py`
  - `tests/test_reader_storage.py`
  - `tests/test_reader_builder_cli.py`
  - `tests/test_reader_cli.py`
- Modify docs:
  - `docs/READER_DATA_BUILD.md`
  - `docs/READER_WEB_CONTRACT.md`
  - `docs/READER_CLI_HANDOFF.md`
  - `docs/plans/active/infra/ctsv2-reader-addressing.md`

## Task 1: CTSv2 Utilities And Address Parser

- [ ] Add tests for slug/incipit ID minting:
  - `Aeneid` + `arma virumque cano` -> `urn:ctsv2:lat:aeneid-arma-virumque-cano`
  - `Bhagavadgītā` + `dhṛtarāṣṭra uvāca` -> `urn:ctsv2:san:bhagavadgita-dhrtarastra-uvaca`
- [ ] Add tests for parsing:
  - `urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23`
  - `ctsv2://lat/aeneid-arma-virumque-cano?ref=1.23&witness=phi0690.phi003`
- [x] Implement `src/langnet/reader/ctsv2.py`.

## Task 2: Catalog Schema And Storage Resolution

- [x] Add `canonical_text_id` to `ReaderWork` and `works`.
- [x] Add schema migration for existing catalogs.
- [x] Register canonical text IDs in `register_books`.
- [x] Resolve `work_ref` by alias, `work_id`, `cts_work_urn`, or `canonical_text_id`.
- [x] Add preferred address fields to returned work and segment dictionaries.
- [x] Add duplicate canonical ID validation.

## Task 3: Builder Canonicalization

- [x] Compute canonical IDs from parsed title plus first meaningful segment.
- [x] Keep current work IDs internally.
- [x] Add generated aliases from source IDs, CTS work URNs, and canonical CTSv2 IDs.
- [x] Preserve compatibility aliases from curated YAML.

## Task 4: First1KGreek Import

- [x] Add `first1k_greek_dir` config and CLI option.
- [x] Import only First1KGreek `data/**/*.xml` text files, skipping `__cts__.xml`.
- [x] Parse using the Perseus TEI adapter with `collection_id = first1kgreek`.
- [x] Filter to Greek editions by edition/source language.
- [x] Record First1K source files and source witness metadata.
- [x] Prefer First1KGreek over legacy TLG when exact logical/CTS work identity overlaps.

## Task 5: Subtext And Relation Layer

- [x] Add source-witness and relation tables.
- [x] Register contained works as graph relations.
- [x] Keep `contained_works` and `work_map_nodes` working for current consumers.
- [x] Add preferred CTSv2 IDs/addresses to contained work rows.
- [x] Audit and adjust Bhagavadgita start range if current source starts after `dhrtarastra uvaca`.

## Task 6: API, CLI, UI Contract

- [x] Make reader outputs prefer `canonical_text_id` and `canonical_address`.
- [x] Keep `work_id` and `cts_work_urn` as compatibility fields.
- [x] Update web reader types to consume preferred addresses without requiring a server restart from this agent.
- [x] Document downstream compatibility: old links still resolve, new links should prefer CTSv2.

## Task 7: Verification

- [x] Run focused CTSv2 tests.
- [x] Run reader storage/builder/CLI tests.
- [x] Run fast project test suite.
- [x] Run lint/format checks.
- [x] If feasible within disk constraints, run a small First1KGreek fixture/slice build.
- [x] Do not claim the full local corpus has been rebuilt unless the full build actually completes.
