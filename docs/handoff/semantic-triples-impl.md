# Semantic Triples Implementation Handoff

Use this as the starting point to emit scoped triples from each tool. It points to the canonical rules, current state, and what to build next.

## Canonical Rules & Constants
- Anchors/predicates/evidence: `docs/technical/predicates_evidence.md` (JSON export: `docs/technical/predicates_evidence.json`).
- Scoped anchors & flat facts: `docs/technical/triples_txt.md`.
- Triple projection model: `docs/technical/semantic_triples.md`.
- Pipeline stages (fetch→extract→derive→claim): `docs/technical/design/tool-response-pipeline.md`.

## Current State (Executor/Handlers)
- Status and gaps: `docs/handoff/tool-execution-and-triples.md`.
- Executor/registry/stubs: `src/langnet/execution/*`, `registry.py`, `handlers_stub.py`.
- CLI sanity: `just cli plan-exec <lang> <word> [--use-stub-handlers|--no-stub-handlers] [--no-cache]`; clear caches with `just clean-cache`.
- Triples dump helper: `just triples-dump lat lupus` now logs normalize/execute timings; CLTK is currently disabled there to avoid cold-start overhead (re-enable by toggling `include_cltk` in `.justscripts/triples_dump.py`).
- Parse-only helpers (pre-triples): `just parse diogenes|whitakers|cltk <lang> <word> [opt]` for raw parsed JSON; `just diogenes-parse <lang> <word>` is kept for convenience. Use these to inspect full dictionary hierarchy/morphology (Diogenes), Whitaker wordlists, or CLTK IPA/Lewis payloads.

## Work Plan (follow this)
- Active plan: `docs/plans/active/tool-fact-indexing.md` (Q1 tasks: predicates/evidence alignment, per-tool projections, memoization, CLI inspect).

## What to Implement per Tool
- **Whitaker** (highest priority): form→interp→lex→sense anchors; `has_interpretation/realizes_lexeme` plus `inflection_of` form→lex; morph qualifiers; code-to-label decoding for freq/age/area/geo/source and tense/voice/mood/number/case/gender/degree; pronoun/numeral subtypes; `variant_form` for secondary lemmas; `has_sense/gloss` on lex/sense; keep `raw_text` + evidence.
- **Diogenes**: morph entries → form nodes + morph qualifiers; dictionary blocks → lex/sense `has_sense/gloss`; citations → `has_citation` with evidence; keep `raw_html` + chunk map. (Implemented in `execution/handlers/diogenes.py`, wired in registry; jump refs now mapped to CTS URNs where possible, with original citation text stored in metadata.)
- **CLTK**: form→lemma via `realizes_lexeme`; `has_pronunciation`; Lewis lines as `has_sense/gloss`; keep raw payload. (Triples implemented in `execution/handlers/cltk.py`, but disabled in the triples-dump helper to avoid CLTK cold-start latency.)
- CLTK IPA extraction: single-string IPA payloads are no longer truncated (str was treated as a Sequence); Latin now emits the full IPA string (e.g., `['lʊ.pʊs]` for `lupus`).
- **Heritage/CDSL**: reuse parsers (see `@codesketch/langnet` heritage/cdsl modules); normalize VH/SLP1 encodings; emit morph + sense facts with domains/register/root/compound/sandhi + `source_ref` (`analysis_id` or `mw:<lnum>`), keep `raw_html`/`raw_text`; fall back to stubs when DBs absent; abbreviations in `docs/upstream-docs/skt-heritage` and `docs/upstream-docs/cdsl`. **Current (Mar 2026)**: heritage handler now fires semicolon sktreader requests (best_mode/fmode) and records the full request URL; parses morphology with abbreviation map (iic/ifc), color normalization/meaning, and groups compound solutions with per-variant features. CDSL DuckDB handler live with accent/IAST→SLP1 matching and MW hits for Śiva/Agni/Deva/Kṛṣṇa; dictionary parsing still needs structured sense/domains/root extraction.

## Greek Path: Status + Next Steps
- Scope: Greek currently relies on Diogenes (LSJ + Perseus morph) and CLTK morphology; Whitaker has no Greek path, so expect fewer sources than Latin.
- Anchor normalization fixed: Diogenes/CLTK now share `normalize_greekish_token` (accent stripping, final-sigma folding, betacode collapse), so Greek lemmas/forms mint anchors like `lex:logos`/`form:logos` instead of `None`. Tests cover `λόγος`.
- Query normalization: keep UTF-8 input for CLTK, but convert to betacode for Diogenes fetch; strip accents when hashing anchors so `λόγος`/`λογος`/`*logos` converge.
- Normalization cache: Greek candidates are re-ranked on read (ω/ο folded, frequency tie-break) so stale cache rows no longer surface lower-frequency variants; `just cli normalize grc phos` now prefers `φῶς` even with cached results.
- LSJ projection: keep `entryid`/indent map from Diogenes blocks so Greek senses (e.g., `logos` 65 blocks) can be clustered; citations already carry CTS URNs in metadata—preserve `citation_ref` + text for LSJ abbreviations.
- CLTK Greek status: endpoint reachable but currently returns lemma-only payloads (empty IPA/blank Lewis lines) in this environment; spaCy fallback is now wired (optional) for Greek morphology, emitting `has_pos`/case/number/gender features when the `grc_odycy_joint_sm` model is available.
- Tests/fixtures: add `triples-dump grc logos diogenes` golden (anchors not `None`), and a CLTK Greek morph fixture that at least exercises `has_pronunciation`/`inflection_of` without Lewis lines.
- Quick checks once normalization is fixed: `just cli plan-exec grc logos --no-cache --no-stub-handlers` (Diogenes + CLTK), `just triples-dump grc logos diogenes` (fast) and `just triples-dump grc logos cltk` (CLTK warmup).
- Helper flags: `python ./.justscripts/tool_parse.py diogenes grc logos --normalize` uses the normalizer’s best candidate (betacode/Greek) for Diogenes; `python ./.justscripts/triples_dump.py grc logos diogenes --normalize` defaults to normalized queries (use `--no-normalize` to bypass). `just parse ...` now passes `--no-normalize` by default; add `--normalize` explicitly when you want the normalizer to pick the query form.

## Sanskrit Path (Heritage + CDSL)
- Assets: `data/build/cdsl_mw.duckdb` and `data/build/cdsl_ap90.duckdb` are present; planner already schedules `heritage` + `cdsl` (MW by default). Upstream references live in `docs/upstream-docs/skt-heritage/*` and `docs/upstream-docs/cdsl/*`; use `@codesketch/langnet`’s `heritage/*` and `cologne/*` modules for parser patterns.
- Heritage projection: handler now hits `sktreader` with full semicolon params (best_mode/fmode/rcpts) and records the full request URL; parses morphology with abbreviations, color normalization/meaning, and groups solutions into compound members with variant features. Still TODO: sandhi/segment reconstruction and dictionary sense extraction. Add tests/fixtures (agni/yoga/śiva/zmazruvardhana) covering VH→SLP1 conversion and compound grouping.
- CDSL projection: **current** handler queries DuckDB read-only with accent/IAST→SLP1 matching and emits `has_sense` glosses with `source_ref` (`mw:<lnum>`). TODO: parse `sense_lines`/domains/register/root/grammar_refs` via `codesketch/cologne/parser.py` and emit structured triples; expand dict selection (mw/ap90) and add fixtures.
- Encoding/normalization: lean on `langnet.normalizer.sanskrit`; bridge VH↔SLP1 with the Heritage converter and CDSL `to_slp1` helpers (codesketch). Hash anchors on unaccented SLP1 tokens so Heritage VH and CDSL SLP1 converge.
- Fixtures/verification: start with `agni`/`agnim` plus AP90 contrasts (`bhakti`, `śiva`/`śiva`); target goldens in `tests/fixtures` + snapshots; run `just triples-dump san agni heritage` / `just triples-dump san agni cdsl` and `just cli plan-exec san agni --no-cache --no-stub-handlers` (use `--use-stub-handlers` if Heritage is offline). Add `just cli parse heritage|cdsl san <term>` smoke tests.

## Provenance & Schema
- Use predicate/evidence constants for claim payloads and memo hashes.
- Evidence block per triple: `source_tool`, `call_id`, `response_id`, `extraction_id`, `derivation_id`, `claim_id`, optional `raw_ref/raw_blob_ref/source_ref`.
- Do not bake provenance into IDs; anchors are scoped per `predicates_evidence.md`.

## Tests & Fixtures
- Fixture-backed executor/triple tests per tool (no network); assert deterministic anchors/claim IDs and cache hits.
- Golden snapshots for agni/lupus/logos once projections are in place.
- Needs: add deterministic fixtures for Diogenes/Whitaker/CLTK triples; add regression to check timing (e.g., client build skips CLTK unless enabled).

## Current Readiness (Latin/Greek/Sanskrit) — Mar 2026
- CLI sanity: `just triples-dump grc anthropos spacy` now works (planner receives NormalizedQuery); Diogenes/Whitaker/CLTK parses succeed via `langnet-cli parse` and in triples-dump.
- Fuzz harness: updated to call `langnet-cli parse …` for diogenes/whitakers/cltk. Sample runs saved under `examples/debug/fuzz_diogenes_lat|grc`, `fuzz_whitakers_lat`, `fuzz_cltk_lat|grc` with tool=ok for lupus/amo/logos/anthropos.
- Provenance: claims carry `raw_blob_ref` + call/extraction/derivation/claim IDs; raw payloads remain in the effects index (no need to inline).
- Coverage gaps: CLTK still disabled by default in triples-dump for latency; spaCy path optional for Greek. No semantic reduction yet—keep all witness claims.
- Ready for Sanskrit: planner/handlers now live (heritage basic morph anchor + CDSL glosses); CDSL DBs are local. Next work: richer Heritage parsing + CDSL sense structuring per Sanskrit Path notes; keep WSU-friendly provenance without touching Latin/Greek.

## Quick Commands
- Run plan-exec: `just cli plan-exec lat lupus --no-cache --no-stub-handlers` (or `--use-stub-handlers` if assets missing).
- Clear caches: `just clean-cache`.
- Triples dump (fast, Diogenes+Whitaker): `just triples-dump lat lupus` (CLTK disabled; flip `include_cltk` in `.justscripts/triples_dump.py` to re-enable, expect ~15s CLTK warmup).
- Parse only: `just parse diogenes lat lupus` (full entry hierarchy), `just parse whitakers lat lupus` (wordlist), `just parse cltk lat lupus` (IPA + Lewis lines).
- Sanskrit bring-up: `just cli plan-exec san agni --no-cache --no-stub-handlers` then `just triples-dump san agni heritage` / `just triples-dump san agni cdsl` (requires Heritage at `:48080` + `data/build/cdsl_*.duckdb`; add `--use-stub-handlers` if Heritage is offline). Parse-only: `just cli parse heritage san yoga` and `just cli parse cdsl san śiva` (normalizes to SLP1 and hits MW).
- Recent CLI checks:
  - `just triples-dump lat lupus` → Diogenes + Whitaker anchors/senses look good; sense counts stable.
  - `just cli plan-exec lat lupus --no-cache --no-stub-handlers` → end-to-end plan executes; CLTK IPA captured as full string.
  - `just triples-dump grc logos diogenes` / `just cli plan-exec grc logos --no-cache --no-stub-handlers` → Greek anchors stable (`lex:logos`/`form:logos`), LSJ senses+citation refs emitted; CLTK Greek still lemma-only (no IPA/gloss yet), spaCy path adds POS/case/number/gender when the model is present.

### Latest Verification (Mar 2026)
- Latin (19 terms: lupus, amo, puella, rex, res, bellum, homo, lux, miles, corpus, manus, dies, sum, mare, bonus, domus, terra, gloria, deus): `just triples-dump lat <term>` passed (Diogenes + Whitaker).
- Greek (20 terms in Greek script: λόγος, ἄνθρωπος, θεός, φῶς, ἀγαθός, γυνή, ἀνήρ, ψυχή, βίος, χείρ, παιδεία, πόλις, χρόνος, φίλος, σοφία, δίκη, ἔργον, οἶκος, λόγχη): `just triples-dump grc <term>` passed (Diogenes anchors + LSJ senses; spaCy morph claims). CLTK Greek still lemma-only here (no IPA/gloss).
- Sanskrit (20 terms: agni, deva, śiva, kṛṣṇa, arjuna, yoga, dharma, karma, bhakti, guru, putra, nara, satya, rāma, sita, lakṣmaṇa, brahma, ātman, māyā, bhūmi): `just triples-dump san <term>` passed. Fix added to CDSL fetch key variants (SLP1/digraphs/underscore+numbers) so MW glosses resolve for dharma/bhakti/śiva/sita/bhūmi, etc.
- Gaps for next dev: Heritage still lacks sandhi/segment reconstruction and dictionary sense extraction; add tests/goldens for compound grouping. CDSL senses still flat gloss strings—structure domains/register/root via `codesketch/cologne/parser.py` and add fixtures. CLTK Greek still missing IPA/gloss unless environment provides richer payloads; spaCy path optional. No semantic reduction yet (witness-only).

- **Ambiguous form strategy (e.g., mahāśmaśāna)**: sktreader fails on ASCII transliteration like `mahashmashana` but succeeds on VH/SLP1 (`mahaazmazaana`). Proposed plan:
  1) When Heritage returns “not recognized”, attempt ASCII→IAST-ish heuristics: map `sh`→`ś`, long vowels (`aa`→`ā`, `ii`→`ī`, `uu`→`ū`), retroflex (`z`→`ṣ`), and try SLP1 digraph guesses.
  2) Retry sktreader with the candidate VH/SLP1 forms (up to a small bounded set, log attempts).
  3) If still missing, fall back to decomposition hints from sktreader (it already returns segmentation) and try recombining with normalized diacritics.
  4) Record attempted forms + “hit/miss” status in normalization steps/evidence for observability.
- This should raise hit rates for compounds without relying on sktsearch’s segment-based matches.

### Heritage Sanskrit: prior codesketch implementation (mining guide)
- Modules to reuse under `codesketch/src/langnet/heritage`:
  - `client.py`: HeritageHTTPClient builds semicolon CGI URLs, rate-limits, and fetches sktsearch canonical forms (captures `entry_url` when present).
  - `html_extractor.py`: Rich HTML extraction; pulls Solution blocks, latin12 `[word]{analysis}` patterns, navy links, CSS colors, raw_text, segments, and dictionary URLs attached to patterns.
  - `lineparsers/parse_morphology.py`: Lark grammar (`grammars/morphology.ebnf`) → MorphologyReducer + Transformer mapping compact codes to features (pos/case/gender/number/person/tense/voice/mood) and compound roles; parses text descriptions too.
  - `parsers.py`: MorphologyParser ties extractor + Lark reducer; enriches analyses with dictionary URLs and segments/colors metadata; SimpleHeritageParser fallback for tables; abbreviation expansion stubs.
  - `morphology.py`: Builds Foster codes from analyses, extracts sandhi/compound segments from HTML segments (color classes, arrows, “|”), normalizes colors; includes dictionary lookup integration.
  - `abbr.py`: Loader for upstream Heritage ABBR.md → normalized abbreviation map (grammar vs source tags).
  - `velthuis_converter.py` + `encoding_service.py`: Utf82VH port and transliteration helpers (IAST/SLP1/Velthuis detection/conversion).
- Integration asks:
  - Rehydrate Heritage handler with the above: use HTML extractor + Lark reducer to emit structured morphology (features, compound_role, sandhi rules, color hints, dictionary_url) and keep raw_text/segments in evidence.
  - Surface CSS color meanings into qualifiers (noun/pronoun/verb colors) if useful.
  - Feed abbreviation map into sense parsing when adding dictionary extraction later.
  - Capture `entry_url` from sktsearch and per-pattern `dictionary_url` in claims for DICO/LS connections.

### Sanskrit reliability restore (codesketch parity loop)
- Target parity: Heritage emits structured morphology with qualifiers (pos/case/gender/number/person/tense/voice/mood + compound_role/sandhi/colors + dictionary_url/source_ref); CDSL emits structured senses (gloss/domain/register/root/grammar_refs) with `source_ref` and SLP1-normalized anchors; both keep raw_ref/raw_text for provenance.
- Iteration loop (all via `just`, no ad-hoc commands):
  1) Baseline extraction: `just cli parse heritage san agni` and `just cli parse cdsl san śiva` (or `--use-stub-handlers` if Heritage is offline) to confirm payload shape before projection; keep `--no-cache` while iterating.
  2) Wire codesketch extractors: port `heritage/html_extractor.py` + `lineparsers/parse_morphology.py` into the handler, then run `just triples-dump san agni heritage --no-cache` and check for `has_morphology` triples with qualifiers + `compound_role`/sandhi segments; expect SLP1 anchors to match CDSL (`lex:agni`).
  3) Sense structuring: after plugging `codesketch/cologne/parser.py` into CDSL, run `just triples-dump san agni cdsl --no-cache` and look for `has_sense` objects carrying gloss + domain/register/root + `source_ref mw:<lnum>`; verify accent-insensitive hits on `śiva`/`śivaH` and AP90 contrasts (`bhakti`, `agnim`).
  4) Ambiguous forms: exercise the retry heuristics with `just cli plan-exec san mahaazmazaana --no-cache --no-stub-handlers` (Velthuis hit) and `just cli plan-exec san mahāśmaśāna --no-cache` (IAST hit). Record attempted forms in claim metadata; success = Heritage returns analyses instead of “not recognized”.
  5) Snapshots/tests: once triples stabilize, add fixtures under `tests/fixtures/triples/san/` (agni/yoga/śiva + a failing compound) and guard with `just test-fast` (or `just test` when integration tags needed). Ensure deterministic anchors/claim IDs and that memoized runs are cache hits.
  6) Full pipeline: `just cli plan-exec san agni --no-cache --no-stub-handlers` should produce merged Heritage + CDSL claims with aligned anchors; rerun with cache warmed to confirm memoization. If Heritage is flaky, use `--use-stub-handlers` to validate CDSL path while keeping Sanskrit planner wiring intact.

### Heritage parity gaps (after URL alignment)
- Sandhi/segment reconstruction from HTML segments and emission alongside compounds.
- Dictionary sense extraction (heritage dictionaries) with `source_ref` and abbreviation expansion.
- Segment merging: keep spans grouped per pattern to avoid over-splitting multi-word solutions; reuse the codesketch segment collector logic.
- Verification target: `just triples-dump san zmazruvardhana heritage` and `yogānuśāsanam` should emit correctly grouped segments and parsed features with color hints; rerun `mahashmashana` to confirm compound parsing survives.

## Verification Guide
1) Parse layer (pre-triples)
   - Diogenes: `just parse diogenes lat is` → expect `PerseusAnalysisHeader` + dictionary entries (e.g., ĕo, is) with block counts.
   - Whitaker: `just parse whitakers lat is` → expect wordlist with codeline terms (e.g., `is, ea, id`).
   - CLTK: `just parse cltk lat lupus` → expect IPA and Lewis lines in the parsed JSON.
   - Greek sanity: `just parse diogenes grc logos --normalize` (LSJ blocks + Perseus morph for λόγος); `just parse diogenes grc logos` exercises ASCII path; `just parse cltk grc logos --normalize` currently returns lemma-only payloads.
   - Sanskrit: `just cli parse heritage san agni` (VH conversion + analyses with raw_ref only) and `just cli parse cdsl san śiva` (SLP1/accent-insensitive MW hit with `source_ref` `mw:<lnum>`).
   These confirm full extraction before projection.
2) Triples layer
   - `just triples-dump lat is diogenes` → sense counts per lexeme and triples for morphology/citations.
   - `just triples-dump lat is whitakers` → look for decoded features (frequency “very frequent”, mapped tense/case/gender, pronoun/numeral subtypes when applicable) and `inflection_of` form→lex links.
   - `just triples-dump grc logos diogenes --normalize` → expect anchors `lex:logos`/`form:logos` (no `None`), sense/gloss triples, citations preserved.
   - Sanskrit (current): `just triples-dump san agni heritage` / `just triples-dump san agni cdsl` → anchors in SLP1 (`lex:agni`/`form:agni`), Heritage morph triple (anchors + analyses) with `raw_ref`, and `has_sense/gloss` with `source_ref` like `mw:<lnum>`; expect MW hits for śiva/kṛṣṇa/deva once normalized.
   - If needed, enable CLTK in `.justscripts/triples_dump.py` (set `include_cltk=True`) and run `just triples-dump lat lupus cltk` to confirm IPA/gloss triples.

## Navigation Shortcuts
- Rules/constants: `docs/technical/predicates_evidence.md`, `docs/technical/triples_txt.md`, `docs/technical/semantic_triples.md`.
- Status/gaps: `docs/handoff/tool-execution-and-triples.md`.
- Work tracker: `docs/plans/active/tool-fact-indexing.md`.
