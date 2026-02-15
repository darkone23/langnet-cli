# Full Implementation Roadmap (Proto + Claims + Reduction + Views)

**Scope**: Make the design docs real—proto-first contract, claim/witness layer, clean parsing, semantic reduction with embeddings, indexed facts, and learner/research views with citations.

## Goals
- Single authoritative schema (proto) used everywhere.
- Claims/Witness layer (subject/predicate/object/provenance) emitted by adapters.
- Clean parsing of dictionary entries before WSU extraction.
- Semantic reduction with embeddings (gensim) and mode-aware clustering (open/skeptic).
- Indexed facts to avoid re-querying backends.
- Dual view modes: didactic (short) vs research (full), with citation display and linkouts.
- Evidence-respecting CLI/API with consistent commands.

## Current State (summary)
- Adapters output `DictionaryEntry` dataclasses; proto is export-only via `semantic_converter.py`.
- Entry parsing layer is designed (`docs/technical/design/04-entry-parsing.md`) but not implemented.
- Semantic reducer exists (tests present) but works on noisy definitions; no claims, no embeddings.
- Modes exist in docs (open/skeptic) but not wired through API/CLI.
- No claim index; everything is live per request.

## Prerequisites
- Align proto (`vendor/langnet-spec/schema/langnet_spec.proto`) with required fields:
  - Definitions, morphology, provenance, **claims/witnesses**, sense refs, citations.
  - Mode/zoom flags (didactic/research; open/skeptic).
- Ensure `just codegen` regenerates Python from proto (already wired).

## Phases and Tasks

### Phase 1: Proto-First Consolidation
- [ ] Review/update proto to include claims/witnesses, mode flags, citations.
- [ ] Run `just codegen`; commit generated Python.
- [ ] Update cattrs/serialization to use generated types (retire dataclass schema after migration).
- [ ] Add CI check: `just codegen` + diff must be clean.

### Phase 2: Entry Parsing Layer (prereq for clean WSUs)
- [ ] Implement parsers per `docs/technical/design/04-entry-parsing.md` and `docs/plans/active/dictionary-entry-parsing.md`.
  - CDSL, Diogenes, CLTK Lewis, Heritage (if needed).
  - Produce structured `ParsedEntry` objects (headword, gender, sense lines, citations, etymology).
- [ ] Wire parsers into adapters before claim emission.
- [ ] Tests: golden fixtures for a few lemmas (lupus/logos/agni); assert split of sense vs citation vs etymology.

### Phase 3: Claim/Witness Emission
- [ ] Define Claim/Provenance types in proto (subject, predicate, value, provenance, citations, sense_ref).
- [ ] Update adapters to emit claims from parsed entries:
  - Diogenes: senses + CTS citations → claims per `sense_ref`.
  - CDSL/Heritage: definitions + `source_ref` → sense claims.
  - Whitaker’s/CLTK: morphology claims with provenance.
- [ ] Tests: per-adapter mini fixtures asserting claims present and provenance populated.
- [ ] Ambiguity handling: retain multiple lemma/analysis claims (e.g., `lat ea`) with distinct provenance; downstream modes/views decide how to display/merge, but claims are never discarded.

### Phase 4: Semantic Reduction Upgrade
- [ ] Switch reducer input to claims (not raw definitions).
- [ ] Add gensim embedding similarity (e.g., `glove-wiki-gigaword-100`) per `semantic-reduction-current-status.md`.
- [ ] Mode wiring: open/skeptic thresholds; didactic/research zoom selection.
- [ ] Output buckets/constants + bucket-level claims.
- [ ] Tests: snapshot small fixture outputs; verify mode-dependent clustering.

### Phase 5: Indexing Layer
- [ ] Implement claim index (DuckDB/SQLite) keyed by lemma, source_ref, predicate.
- [ ] `just` tasks: build/update index from live backends or fixtures.
- [ ] API/CLI: check index first; refresh on miss or with `--refresh`.
- [ ] Tests: index build/read round-trip for sample lemmas.

### Phase 6: Views & Citations
- [ ] Didactic view: short/glossy bucketed output with top senses, foster codes, minimal citations.
- [ ] Research view: full claims/witnesses, raw citations, timings.
- [ ] Citation display/linkouts: CTS → Perseus catalog, DCS/DICO links where applicable.
- [ ] CLI/API flags: `--mode open|skeptic`, `--view didactic|research`.
- [ ] Tests: view rendering snapshots per mode/view.
- [ ] Provenance display: show provenance on claims (source, source_ref, sense_ref); keep ambiguous lemmas (e.g., `lat ea`) as multiple claims, surface warnings/filters rather than dropping evidence.

### Phase 7: Cleanup & Docs
- [ ] Remove legacy semantic converter path; single proto-based response shape.
- [ ] Update `docs/technical/backend/tool-capabilities.md` with finalized claims per tool.
- [ ] Update `docs/OUTPUT_GUIDE.md` with didactic/research examples.
- [ ] Add “Data Contracts & Claims” doc (source of truth pointing to proto).

## Verification Checklist
- Proto in repo matches generated code (`just codegen` clean).
- Adapters emit proto types + claims; parsing layer enabled.
- Reducer consumes claims; modes/views produce distinct, tested outputs.
- Index builds reproducible via `just` and used in API/CLI.
- Docs updated: tool capabilities, output guide, commands.
- Mermaid diagrams updated: see `docs/technical/design/mermaid/semantic-pipeline.md` for planned flow (keep in sync as implementation progresses).

## References
- `docs/technical/design/01-semantic-structs.md`
- `docs/technical/design/02-witness-contracts.md`
- `docs/technical/design/03-classifier-and-reducer.md`
- `docs/technical/design/04-entry-parsing.md`
- `docs/plans/active/dictionary-entry-parsing.md`
- `docs/plans/active/semantic-reduction/*`
- `docs/technical/backend/tool-capabilities.md`

## Concrete Example (lat ea: current vs target)
- **Today** (`devenv shell just -- cli query lat ea --output json`):
  - Three Whitaker’s entries (verb “eo/eare…”, pronoun “is/ea/id”, pronoun “idem/eadem/idem”) with flat `definitions[]` and a single morphology block; no structured claims.
  - Diogenes block for “is/ea/id” with raw `dictionary_blocks` and citations; no structured sense IDs or per-analysis claims.
  - CLTK entry with a Lewis gloss; no claims.
  - Ambiguity is implicit: multiple entries, but no per-analysis provenance or lemma claims.
- **Target** (after parsing + claims):
  - Parse Diogenes senses and synthesize `sense_ref`; emit claims (subject=ea, predicate=lemma, value=is; predicate=pos; citation claims).
  - Emit Whitaker’s claims per analysis (surface+lemma+POS+features+provenance) for `eo` vs `is` vs `idem` to support disambiguation like “cur portas portas.”
  - Emit CLTK claims (lemma + gloss + provenance).
  - Index all claims; modes/views:
    - **research**: show all claims with provenance (open/skeptic controls clustering).
    - **didactic**: bucketed/curated senses with ambiguity warnings, never dropping claims.

### Concrete Example (Diogenes parser for disambiguation/navigation)
- **Form disambiguation**: `curl "http://localhost:8888/Perseus.cgi?do=parse&lang=lat&q=portas"` returns two analyses: `portās, porta` (fem acc pl) and `portās, porto` (pres ind act 2nd sg). Parse this to emit per-analysis claims (surface, lemma, POS, features, provenance).
- **Ambiguity example**: `curl "http://localhost:8888/Perseus.cgi?do=parse&lang=lat&q=ea"` returns multiple analyses for “ea” (fem nom sg; neut nom/voc/acc pl; fem abl sg). These must become distinct claims (surface+lemma+POS+features+provenance) to keep ambiguity explicit.
- **Entry navigation / neighborhood**: `curl "http://localhost:8888/Perseus.cgi?do=prev_entry&lang=lat&q=55038347"` (and `next_entry`) returns neighbor entry IDs (e.g., `prevEntrylat(55036652)`). Use these to build ordered lemma neighborhoods and capture navigation metadata as provenance hooks.
