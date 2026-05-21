> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# Reader Metadata Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible curated metadata overlay layer for reader corpus works, with explicit provenance and review status.

**Architecture:** Source adapters keep importing source-faithful metadata. A new overlay loader reads strict YAML records from `data/curated/reader_metadata/`, validates evidence/status/confidence, applies only `accepted` assertions during `databuild reader`, and registers every overlay assertion in the catalog for audit. Candidate web-research findings can be stored without changing displayed metadata until reviewed.

**Tech Stack:** Python dataclasses, local strict-YAML parsing, DuckDB catalog tables, existing Click reader/databuild commands, `just` test/lint commands.

---

### Task 1: Overlay Models And Loader

**Files:**
- Modify: `src/langnet/reader/models.py`
- Create: `src/langnet/reader/metadata_overlay.py`
- Test: `tests/test_reader_metadata_overlay.py`

- [x] Add dataclasses for overlay evidence and assertions.
- [x] Add a strict YAML loader for files under `data/curated/reader_metadata/`.
- [x] Require `field`, `value`, `status`, `confidence`, `note`, and at least one evidence item.
- [x] Reject unsupported status/confidence values and unsupported target shapes.

### Task 2: Build-Time Overlay Application

**Files:**
- Modify: `src/langnet/reader/builder.py`
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/cli_databuild.py`
- Test: `tests/test_reader_builder_cli.py`

- [x] Add `metadata_overlay_dir` to reader build configuration and CLI.
- [x] Load overlays before iterating sources.
- [x] Apply only `accepted` overlays matching a parsed work by collection/source/work id.
- [x] Preserve source metadata and register overlay provenance in the catalog.
- [x] Support fields: `author`, `author_id`, `title`, `language`, `cts_work_urn`.

### Task 3: CLI Audit Surface

**Files:**
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_reader_builder_cli.py`

- [x] Add `reader overlays` command.
- [x] Filter overlays by collection, subject id, status, and field.
- [x] Emit JSON rows with evidence URL/source path, note, confidence, and status.

### Task 4: First Curated Seed And Research Workflow

**Files:**
- Create: `data/curated/reader_metadata/sanskrit/panini.yaml`
- Modify: `examples/debug/reader-audit/NOTES.md`

- [x] Add one candidate seed showing the ambiguity-safe format.
- [x] Add first researched candidate batch for major Sanskrit works.
- [x] Document that ambiguous titles such as `Śivasūtra` must stay candidate until the exact source text is identified.
- [x] Document the web research loop: search, scrape, write candidate overlay, review, then promote to accepted.

### Task 5: Candidate Review And Promotion CLI

**Files:**
- Create: `src/langnet/reader/metadata_overlay_review.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_reader_metadata_overlay.py`
- Test: `tests/test_reader_builder_cli.py`

- [x] Add review decision/review result models.
- [x] Add local rule recommendations for candidate overlays.
- [x] Add OpenRouter/aisuite LLM reviewer support for structured recommendations.
- [x] Add YAML promotion that rewrites only the matched overlay record.
- [x] Append `rule_review` or `llm_review` evidence when promoting.
- [x] Add `reader overlay-review` with dry-run JSON, interactive `--apply`, and noninteractive `--apply --yes`.
- [x] Keep `candidate` unchanged unless explicit apply approval is given.
- [x] Keep noninteractive `--apply --yes` from promoting `needs_review` recommendations.

### Verification

- [x] `just test test_reader_metadata_overlay test_reader_builder_cli`
- [x] `just test test_reader_metadata_overlay test_reader_builder_cli test_reader_storage test_reader_validation`
- [x] `just ruff-format --check`
- [x] `just ruff-check`
- [x] Build a tiny fixture catalog with overlays and verify `reader overlays`.
- [x] Verify old catalogs without `metadata_overlays` return an empty overlay list instead of failing.
- [x] `just test test_reader_metadata_overlay test_reader_builder_cli`
- [x] `reader overlay-review --metadata-overlay-dir data/curated/reader_metadata --reviewer rule --output json`
- [x] Operator drill against sandbox overlay files: dry-run, decline-all, approve-one, safe `--yes`, LLM dry-run, LLM decline.
- [x] Real gated run against curated overlays: LLM batch gate promoted 0, then source-strengthened Kāmasūtra/Vātsyāyana and promoted it through the rule gate.
- [x] Targeted rebuild verifies `sanskrit_dcs:dcs_347` imports as `Kāmasūtra` by `Vātsyāyana` with validation issue count 0.
- [x] Full curated Sanskrit rebuild verifies 977 works, 3,319,944 segments, source error count 0, validation issue count 0, and accepted Kāmasūtra/Vātsyāyana metadata applied.
- [x] Add accepted research-backed overlays for Perseus Appendix Vergiliana author/title gaps.
- [x] Add accepted research-backed overlays for digilibLT public author authority gaps, reducing verified `Unattributed` rows to 0 in the curated digilibLT rebuild.
- [x] Add accepted medium-confidence traditional display attributions for Sanskrit Kāmasūtra, Nyāyasūtra, Mahābhārata, and Rāmāyaṇa while preserving uncertainty in notes.
- [x] Add accepted research-backed Sanskrit overlays for Abhidharmakośa, Abhidharmakośabhāṣya, Amarakośa, Arthaśāstra, Kirātārjunīya, Meghadūta, Nāṭyaśāstra, Yogasūtra, Aṣṭādhyāyī, Buddhacarita, Bodhicaryāvatāra, Daśakumāracarita, Gītagovinda, Harṣacarita, and Suśrutasaṃhitā.
- [x] Enforce portable overlay citation convention: no host-local prefixes such as `/home/nixos` or local umbrella directories such as `Classics-Data`.

### Task 6: Import-Layer Author Display Normalization

**Files:**
- Create: `src/langnet/reader/author_normalization.py`
- Modify: `src/langnet/reader/builder.py`
- Test: `tests/test_reader_author_normalization.py`
- Test: `tests/test_reader_builder_cli.py`

- [x] Normalize pseudo-author variants into one display form.
- [x] Apply import-layer author normalization before accepted overlays.
- [x] Add builder-level coverage proving imported works use normalized author displays.
- [x] Preserve `Unattributed` as an unresolved metadata gap.
- [x] Canonicalize source authority label `Anonymus` to reader-facing `Anonymous` while retaining source evidence in overlays.
- [x] Normalize comma-form and pseudonymous source labels for display, e.g. `Ulpianus, Domitius` -> `Domitius Ulpianus`, `Bassus, Caesius (Ps.)` -> `Pseudo-Caesius Bassus`.
- [x] Enrich legacy TLG dangling `Pseudo-` author ids from `cd.authors.php` numeric canon labels.
- [x] Targeted rebuild verifies affected TLG pseudo-author families no longer display as `Pseudo-`.

### Task 7: Reader Catalog Text Quality Validation

**Files:**
- Modify: `src/langnet/reader/validation.py`
- Test: `tests/test_reader_validation.py`

- [x] Validate blank segment text inside book artifact DuckDB files.
- [x] Validate legacy/XML-like markup leakage inside segment text.
- [x] Verify stricter validation still passes the curated digilibLT rebuild.
