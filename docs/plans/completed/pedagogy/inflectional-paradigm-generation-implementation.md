# Inflectional Paradigm Generation Implementation Plan

Status: ✅ DONE - source-backed V1 completed 2026-05-11
Owner: LangNet maintainers
Primary consumers: students and scholars using lookup/encounter workflows for Latin, Greek, and Sanskrit
Roadmap: docs/plans/todo/pedagogy/inflectional-paradigm-generation.md

## Goal

Make paradigm generation real in LangNet by first wrapping the source-backed tools already running locally:

- Sanskrit Heritage `sktdeclin` and `sktconjug`
- Diogenes `do=inflect` for Latin and Greek

The first production milestone is not a full in-house morphology engine. It is a stable LangNet contract that can fetch, parse, normalize, test, document, and expose complete paradigm tables from those authoritative services.

## Session Closure Note - 2026-05-11

The source-backed V1 paradigm slice is stable enough to hand off for review or
continued product work. LangNet now has schema-backed `paradigm` and
`paradigm-resolve` outputs, source-backed Heritage and Diogenes table fetchers,
native/functional grammar resolution, and encounter integration that can expose
a lazy `paradigm_request` without fetching a full table in the main lookup path.

Sanskrit support is intentionally source-backed:

- `paradigm san putra --kind declension --gender Mas` fetches and parses a
  Heritage declension table.
- `paradigm san gam --kind conjugation --class 1` fetches and parses Heritage
  conjugation blocks.
- `paradigm-resolve` can resolve Heritage evidence for forms such as
  `putrāṇām` and `devebhyaḥ` into fetchable declension requests when lemma,
  gender, and analyses are present.
- When gender, class, lemma, or analysis evidence is missing, the resolver should
  degrade with an unresolved reason rather than guessing a paradigm class from a
  bare string.

Verified closure checks from this session:

```bash
just test test_word_index_sections test_word_index_ordering test_paradigm_resolver test_paradigm_service test_cli_paradigm test_cli_paradigm_resolve
just cli paradigm san putra --kind declension --gender Mas --output json
just cli paradigm san gam --kind conjugation --class 1 --output json
just cli paradigm-resolve san putraa.naam --record-json '{"normalized_form":"putrāṇām","lemma":"putra","part_of_speech":"noun","gender":"masculine","source":"heritage:sktreader","analyses":[{"case":"genitive","number":"plural"}]}' --output json
just cli paradigm-resolve san devebhyaḥ --record-json '{"normalized_form":"devebhyaḥ","lemma":"deva","part_of_speech":"noun","gender":"masculine","source":"heritage:sktreader","analyses":[{"case":"dative","number":"plural"},{"case":"ablative","number":"plural"}]}' --output json
just lint-all
just test-fast
```

Remaining follow-up work should be treated as new scope:

- arbitrary reverse morphological analysis for forms not already analyzed by a
  source;
- local paradigm template generation independent of Heritage/Diogenes;
- Sanskrit compound decomposition and component-level paradigm linking;
- cross-language aligned paradigm comparison UI;
- highlight-in-paradigm rendering from originating form features.

## Non-Goals For This Plan

- Building a full reverse morphological analyzer for arbitrary unseen forms.
- Pre-generating all variants for every dictionary entry.
- Implementing a complete local paradigm template registry before source-backed extraction works.
- Solving Sanskrit compound decomposition.
- Producing fully accented local Greek forms independent of Diogenes.

## Success Definition

The project is in a solid forward-moving state when:

- `langnet` has a versioned paradigm JSON contract with schema validation.
- `langnet` has a versioned paradigm resolution contract that separates native grammar features from language-independent functional grammar features.
- Dictionary and analyzer outputs are mined for grammar metadata before any paradigm source is called.
- Sanskrit noun and verb paradigms can be fetched from Heritage and parsed into that contract.
- Latin and Greek paradigms can be fetched from Diogenes and parsed into that contract.
- A CLI command exposes the feature for direct verification.
- Lookup/encounter results can advertise when a paradigm is available and provide enough metadata to request it.
- Documentation explains what is source-backed, what is supported, how to verify it, and what remains out of scope.
- `just lint-all`, focused tests, and `just test-fast` pass without requiring parallel `devenv shell` invocation.

## Concrete Task Queue

These are the first implementation tasks to work through. Each task has a narrow success mark and can be verified independently.

Progress as of current implementation:

- Task 1 is implemented in `docs/schemas/paradigm_resolution.v1.schema.json`, `src/langnet/paradigm/grammar.py`, and `tests/test_paradigm_resolution_contract.py`.
- Task 2 is implemented in `src/langnet/paradigm/extractors.py` and `tests/test_paradigm_extractors.py`.
- Task 3 is implemented in `src/langnet/paradigm/resolver.py` and `tests/test_paradigm_resolver.py`.
- Task 4 is implemented in `src/langnet/cli.py`, `tests/test_cli_paradigm_resolve.py`, and `tests/test_cli_help.py`.
- Source-backed paradigm payloads are implemented in `docs/schemas/paradigm.v1.schema.json`, `src/langnet/paradigm/models.py`, `src/langnet/paradigm/heritage.py`, `src/langnet/paradigm/diogenes.py`, `src/langnet/paradigm/service.py`, and the `paradigm` CLI command.
- Source-backed tests are implemented in `tests/test_paradigm_contract.py`, `tests/test_paradigm_parsers.py`, `tests/test_paradigm_service.py`, and `tests/test_cli_paradigm.py`.
- Live localhost smoke checks have passed for Sanskrit `putra` declension, Sanskrit `gam` conjugation, Latin `amo` conjugation, and Greek `lo/gos` declension.
- Sanskrit resolver smoke checks cover `putrāṇām`/`putraa.naam` and
  `devebhyaḥ` resolving to fetchable Heritage declension requests when Heritage
  evidence includes lemma, gender, and analyses.
- Current limitations and graceful degradation policy are captured in `docs/technical/backend/paradigm-generation-limitations.md`.
- Verified with focused paradigm tests, `just lint-all`, live CLI smoke checks, and `just test-fast`.

### Task 1: Functional Grammar Contract

Files:

- Create `docs/schemas/paradigm_resolution.v1.schema.json`
- Create `src/langnet/paradigm/grammar.py`
- Create `tests/test_paradigm_resolution_contract.py`

Build:

- A shared functional relation vocabulary:
  - `subject`
  - `direct_object`
  - `recipient_or_goal`
  - `source_or_separation`
  - `possession_or_association`
  - `location`
  - `instrument_or_means`
  - `address`
  - `predicate_relation`
  - `unknown`
- Native grammar feature containers for Sanskrit, Latin, and Greek.
- A resolution payload with:
  - `searched_form`
  - `normalized_form`
  - `language`
  - `lemma`
  - `entry_type`
  - `paradigm_kind`
  - `native_analyses`
  - `functional_analyses`
  - `paradigm_request`
  - `confidence`
  - `provenance`
  - `unresolved_reason`

Verification:

```bash
just test test_paradigm_resolution_contract
```

Success marks:

- Sanskrit `devebhyaḥ` fixture can represent both dative plural and ablative plural.
- Latin `puellae` fixture can represent genitive singular, dative singular, and nominative plural.
- Greek `λόγοις` fixture can represent native dative plural and a functional relation set that includes recipient/location/instrument possibilities.
- An unresolved fixture can explain `missing_gender_or_declension` without guessing.

### Task 2: Dictionary Grammar Extraction

Files:

- Create `src/langnet/paradigm/extractors.py`
- Create `tests/test_paradigm_extractors.py`

Build:

- Extraction helpers that convert existing dictionary/analyzer records into grammar evidence:
  - `extract_sanskrit_grammar_evidence(record)`
  - `extract_latin_grammar_evidence(record)`
  - `extract_greek_grammar_evidence(record)`
- Evidence fields:
  - `lemma`
  - `part_of_speech`
  - `gender`
  - `case`
  - `number`
  - `person`
  - `tense`
  - `mood`
  - `voice`
  - `declension`
  - `conjugation`
  - `principal_parts`
  - `source`
  - `confidence`

Source priority:

- Sanskrit:
  - Heritage reader/parser analyses for inflected forms.
  - CDSL or Heritage dictionary metadata for lemma, gender, and stem hints.
- Latin:
  - Whitaker/Diogenes parse evidence for inflected forms.
  - Dictionary lemma metadata, especially nominative/genitive/gender, for declension inference.
- Greek:
  - Diogenes parse evidence for inflected forms.
  - Dictionary lemma metadata, especially nominative/genitive/article/gender, for declension inference.

Verification:

```bash
just test test_paradigm_extractors
```

Success marks:

- Latin `puella, puellae, f.` evidence derives first declension.
- Latin `rex, regis, m.` evidence derives third declension.
- Sanskrit `putra` with masculine evidence produces a Heritage declension request.
- Greek `λόγος, λόγου, ὁ` evidence produces second-declension masculine evidence when metadata is present.
- Missing evidence stays missing and lowers confidence instead of inventing a class.

### Task 3: Paradigm Resolver

Files:

- Create `src/langnet/paradigm/resolver.py`
- Create `tests/test_paradigm_resolver.py`

Build:

- `resolve_paradigm_request(language, searched_form, lookup_records)` that:
  - normalizes the searched form
  - extracts grammar evidence from each lookup/analyzer record
  - groups evidence by candidate lemma
  - maps native analyses to functional analyses
  - emits one or more paradigm resolution candidates
  - refuses to produce a fetchable request when required metadata is missing
- Required metadata by request type:
  - Sanskrit declension: lemma plus gender
  - Sanskrit conjugation: root plus present class when Heritage requires it
  - Latin Diogenes inflection: lemma
  - Greek Diogenes inflection: Diogenes-compatible lemma key or convertible Greek lemma

Verification:

```bash
just test test_paradigm_resolver
```

Success marks:

- `putraa.naam` resolves to `putra`, genitive plural, Sanskrit declension request, high confidence when Heritage evidence is present.
- `devebhyaḥ` resolves to `deva`, dative and ablative plural, Sanskrit declension request, high confidence when Heritage evidence is present.
- `puellārum` resolves to `puella`, genitive plural, Latin inflection request.
- `puellae` returns multiple native analyses under one lemma.
- `λόγοις` resolves to `λόγος` or `lo/gos`, Greek inflection request, preserving Unicode and source key when present.
- Unknown or underspecified records return `unresolved_reason` rather than a guessed request.

### Task 4: Resolver CLI Probe

Files:

- Modify `src/langnet/cli.py`
- Create `tests/test_cli_paradigm_resolve.py`

Command:

```bash
just cli paradigm-resolve san putraa.naam --output json
just cli paradigm-resolve san devebhyaḥ --output json
just cli paradigm-resolve lat puellae --output json
just cli paradigm-resolve grc λόγοις --output json
```

Verification:

```bash
just test test_cli_paradigm_resolve test_cli_help
```

Success marks:

- The command shows what LangNet believes before fetching a paradigm.
- Ambiguous forms return multiple analyses.
- Missing metadata is visible to maintainers and users.
- This command can be used to debug resolver behavior without calling Heritage declension, Heritage conjugation, or Diogenes inflection endpoints.

## Phase 0: Baseline And Service Contract Check

Purpose: preserve the working integration points before adding the new layer.

Tasks:

- Confirm the current process-compose services are running and reachable.
- Record a small set of live probe examples in `examples/debug/` only if a saved sample is needed.
- Avoid parallel `devenv shell` or parallel `just` recipes when probing services.

Verification:

```bash
just cli lookup san putra --output json --no-cache
just diogenes-parse lat amo
just diogenes-parse grc λόγος
just test-fast
```

Success marks:

- Sanskrit lookup returns Heritage and CDSL-backed data.
- Latin `amo` and Greek `λόγος` Diogenes parse commands return analyses.
- Existing fast tests pass before paradigm work begins.

## Phase 1: Paradigm Data Contract

Purpose: define the public shape before parsers and CLI grow around it.

Files:

- `docs/schemas/paradigm.v1.schema.json`
- `src/langnet/paradigm/__init__.py`
- `src/langnet/paradigm/models.py`
- `tests/test_paradigm_contract.py`

Contract shape:

- Top-level fields:
  - `schema_version`
  - `language`
  - `lemma`
  - `kind`: `declension` or `conjugation`
  - `source`
  - `source_request`
  - `paradigms`
  - `warnings`
- Each paradigm block:
  - `label`
  - `dimensions`
  - `slots`
- Each slot:
  - `features`
  - `forms`
  - `source_label`
  - `is_ambiguous`
- Each form:
  - `text`
  - `normalized`
  - `source_key`

Implementation notes:

- Use dataclasses and `cattrs`, matching existing serialization patterns.
- Keep source-specific details in `source_request` and `source_key`; keep normalized grammatical features in `features`.
- Preserve raw labels when parsing is uncertain rather than dropping information.

Verification:

```bash
just test test_paradigm_contract
```

Success marks:

- Minimal Sanskrit, Latin, and Greek fixture payloads validate against `docs/schemas/paradigm.v1.schema.json`.
- Serialization round-trips through `cattrs`.
- Invalid payloads fail schema validation in tests.

## Phase 2: Sanskrit Heritage Parsers

Purpose: transform Heritage declension and conjugation HTML into the LangNet paradigm contract.

Files:

- `src/langnet/paradigm/heritage.py`
- `tests/test_paradigm_heritage.py`

Parser entry points:

- `parse_heritage_declension_html(html, *, lemma, gender, request_url=None)`
- `parse_heritage_conjugation_html(html, *, root, present_class, request_url=None)`

Required extraction:

- Declension:
  - Parse `table.inflexion`.
  - Map row labels to Sanskrit cases.
  - Map column labels to singular, dual, plural.
  - Preserve multiple forms in a cell.
  - Preserve the originating Heritage labels.
- Conjugation:
  - Parse nested `table.inflexion` blocks.
  - Preserve tense/mood, voice, person, and number when present.
  - Preserve participle declension links as source keys when present.

Fixture examples:

- `putra`, masculine declension:
  - nominative singular includes `putraḥ`
  - genitive plural includes `putrāṇām`
  - locative singular includes `putre`
- `gam`, class 1 conjugation:
  - parser returns at least one finite paradigm block
  - each parsed slot has grammatical features and at least one form

Verification:

```bash
just test test_paradigm_heritage
```

Success marks:

- Heritage declension fixture produces a complete 8 case by 3 number noun table when the source table is complete.
- Heritage conjugation fixture produces structured blocks without losing source labels.
- Parser tests do not require live HTTP services.

## Phase 3: Diogenes Latin And Greek Parser

Purpose: transform Diogenes `do=inflect` output into the LangNet paradigm contract.

Files:

- `src/langnet/paradigm/diogenes.py`
- `tests/test_paradigm_diogenes.py`

Parser entry point:

- `parse_diogenes_inflect_html(html, *, language, lemma, request_url=None)`

Required extraction:

- Parse repeated `span.form_span_visible` blocks.
- Extract visible Unicode form text.
- Extract checkbox `value` as `source_key` when present.
- Extract `infl` attribute as the raw morphology label.
- Normalize common Latin and Greek morphology labels into `features`.
- Preserve the unparsed `infl` string as `source_label`.

Fixture examples:

- Latin `amo`:
  - includes `amo`
  - includes at least one perfect form such as `amavi`
  - features identify person, number, tense, mood, and voice when present
- Greek `lo/gos`:
  - includes Unicode forms such as `λόγος`, `λόγου`, and `λόγῳ`
  - preserves beta-code source keys such as `lo/gw|`
  - identifies nominative, genitive, and dative singular when present

Verification:

```bash
just test test_paradigm_diogenes
```

Success marks:

- Latin and Greek fixtures parse without live services.
- Unknown morphology labels are preserved, not discarded.
- Greek visible Unicode and beta-code source keys are both retained.

## Phase 4: Fetching Service

Purpose: provide one internal API for source-backed paradigm retrieval.

Files:

- `src/langnet/paradigm/service.py`
- `tests/test_paradigm_service.py`

Service shape:

- `ParadigmService.get_paradigm(language, lemma, **options)`
- Sanskrit options:
  - `kind=declension`, `gender=Mas|Fem|Neu`
  - `kind=conjugation`, `present_class=1..10`
- Latin and Greek options:
  - Diogenes `do=inflect`
  - language mapping: `lat` to `lat`, `grc` to `grk`

Implementation notes:

- Use existing HTTP/client conventions where possible.
- Keep network failures explicit in `warnings`.
- Cache only after the parsed contract is stable.
- Do not shell out to `curl`; use Python HTTP clients.

Verification:

```bash
just test test_paradigm_service
```

Success marks:

- Unit tests mock HTTP responses and verify exact URLs/parameters.
- Heritage declension and conjugation calls are routed to `sktdeclin` and `sktconjug`.
- Diogenes Latin and Greek calls are routed to `Perseus.cgi?do=inflect`.
- HTTP failures produce actionable errors or warning payloads.

## Phase 5: CLI Command

Purpose: make the feature directly testable without UI work.

Files:

- `src/langnet/cli.py`
- `tests/test_cli_paradigm.py`
- `tests/test_cli_help.py`

Command:

```bash
just cli paradigm san putra --kind declension --gender Mas --output json
just cli paradigm san gam --kind conjugation --class 1 --output json
just cli paradigm lat amo --output json
just cli paradigm grc lo/gos --output json
```

CLI behavior:

- JSON output should emit the contract from Phase 1.
- Human output should show a compact table or grouped list.
- `--output json` is the required stable interface for tests.
- Invalid option combinations should fail with clear messages.

Verification:

```bash
just test test_cli_paradigm test_cli_help
```

Success marks:

- Help output lists the new command.
- JSON output validates against `paradigm.v1.schema.json`.
- CLI tests use mocked service responses, not live services.

## Phase 6: Live Smoke Verification

Purpose: prove the new command works against the actual local services.

Precondition:

- Process-compose services are already running.
- Code changes have been loaded by the relevant Python process. If verifying through the API later, restart the process manager first.

Verification:

```bash
just cli paradigm san putra --kind declension --gender Mas --output json
just cli paradigm san gam --kind conjugation --class 1 --output json
just cli paradigm lat amo --output json
just cli paradigm grc lo/gos --output json
```

Success marks:

- Sanskrit `putra` output includes `putrāṇām`.
- Sanskrit `gam` output includes finite verbal forms.
- Latin `amo` output includes present and perfect forms.
- Greek `lo/gos` output includes Unicode Greek forms and Diogenes source keys.
- No verification step invokes parallel `devenv shell`.

## Phase 7: Lookup And Encounter Integration

Purpose: connect paradigms to the reader-facing workflows without blocking the parser milestone.

Files:

- `src/langnet/word_index/service.py`
- `src/langnet/cli.py`
- `docs/schemas/encounter.v1.schema.json`
- `tests/test_cli_encounter_output.py`
- `tests/test_word_index.py`

Data additions:

- Add optional `paradigm` metadata to lookup/encounter entries:
  - `available`
  - `language`
  - `lemma`
  - `kind`
  - `source`
  - `request_options`
  - `originating_form`
  - `highlight_features` when known

Scope:

- Root entries can advertise direct paradigm availability.
- Variant entries can advertise a paradigm request if a resolved lemma is known.
- Highlighting should be populated only when analysis is known; otherwise leave it absent instead of guessing.
- `encounter --output json --include-paradigm-resolution` now embeds a
  `langnet.paradigm_resolution.v1` payload for the searched form, using
  morphology triples and the existing resolver. This intentionally produces
  resolution metadata only; full paradigm table fetching remains lazy through
  `paradigm`.
- Greek learner-key bridge support is in place for verified MOTD basics such as
  `logos -> lo/gos`, `sophos -> sofo/s`, and `nomos -> no/mos`, so curated Greek
  recommendations and encounter resolution can expose Diogenes-backed
  `paradigm_request` data instead of stopping at `no_grammar_evidence`.
- Current top-level encounter resolution supports Sanskrit Heritage morphology
  objects and graph-style Latin/Greek morphology triples. Component-level
  paradigm resolution remains a follow-up.

Verification:

```bash
just test test_word_index test_cli_encounter_output
```

Success marks:

- Existing lookup and encounter schemas remain valid.
- Sanskrit hit-rate fixes still work for `sanjay`, `sanjaya`, `putraa.naam`, `putrāṇām`, and `dhimata`.
- Encounter JSON can point from an analyzed form to a paradigm request.

## Phase 8: Documentation Update

Purpose: keep users and maintainers clear on the feature boundary.

Files:

- `README.md`
- `docs/OUTPUT_GUIDE.md`
- `docs/DEVELOPER.md`
- `docs/ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/plans/todo/pedagogy/inflectional-paradigm-generation.md`

Required documentation:

- How to run paradigm commands.
- Which languages and sources are supported in V1.
- Why V1 is source-backed instead of locally generated.
- Known limitations:
  - no arbitrary reverse analyzer yet
  - no Sanskrit compound decomposition
  - no local Greek accent engine
  - no cross-language aligned paradigm UI yet
- Verification commands for maintainers.

Verification:

```bash
rg -n "paradigm|sktdeclin|sktconjug|do=inflect" README.md docs
rg -n "TB[D]|f[i]ll in|coming so[o]n" README.md docs
```

Success marks:

- Docs accurately describe implemented behavior, not the future ideal.
- Roadmap separates completed source-backed V1 work from future local generator work.
- No stub prose is introduced.

## Phase 9: Final Stabilization

Purpose: make sure the branch is ready for continued feature work or review.

Verification:

```bash
just ruff-format
just lint-all
just test-fast
```

Additional live smoke, when services are running:

```bash
just cli paradigm san putra --kind declension --gender Mas --output json
just cli paradigm lat amo --output json
just cli paradigm grc lo/gos --output json
```

Success marks:

- Formatting is stable.
- Linting passes.
- Fast tests pass.
- Live service smoke passes or has a documented service availability reason.
- `docs/plans/todo/pedagogy/inflectional-paradigm-generation.md` is updated with the actual completed scope.

## Review Checkpoints

- @architect after Phase 1: confirm the contract can support source-backed V1 and later local template generation.
- @coder after Phase 5: confirm CLI and service behavior are test-covered.
- @auditor after Phase 7: review schema compatibility, error handling, and user-facing ambiguity.
- @scribe after Phase 8: ensure docs reflect the actual implementation boundary.

## Immediate Next Step

Start with Phase 1. Add the paradigm schema, dataclasses, and contract tests before implementing any parser-specific behavior.
