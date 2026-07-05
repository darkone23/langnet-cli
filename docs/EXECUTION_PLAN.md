# Project Execution Plan

**Mode:** evidence-first stabilization, then measured reader expansion.

This is the compact operating queue. Use `docs/ROADMAP.md` for the milestone
sequence and `docs/plans/README.md` for plan ownership and lifecycle. Dated
handoffs and close-out notes belong in `docs/archive/`, not in this file or
`docs/plans/active/`.

Current closeout target: drive `docs/plans/active/` to zero files. Do that from
the `Active Plan Zero Closeout Queue` in `docs/plans/README.md`; do not create a
new meta-plan under `active/` to manage the active plans.

## Current Thesis

LangNet has enough runtime foundation to be useful. The current task is to make
the existing surfaces trustworthy: word-level `encounter`, reader catalog and
source-index browsing, `/library`, word-index, paradigms, translation-cache
operations, and the SvelteKit adapter.

Do not expand into passage interpretation, embeddings, or broad semantic
inference until the active queue below is stable.

## What Is In A Good Place

- CLI JSON is the product contract, and the webapp is still an adapter over that
  contract rather than a separate semantic runtime.
- Reader catalog/source-index export exists, checked-in TSV snapshots exist,
  canonical reader bundles can be exported and validated, and `/library` can
  expose catalog and acquisition-watchlist data.
- PL122/Eriugena is imported as a source-index-visible pilot slice, and current
  reader expansion now has explicit quality gates instead of raw-count goals.
- Translation cache behavior is disciplined: cache-only lookup is network-free,
  population is explicit, and DICO/Gaffiot/Bailly translated witnesses remain
  derived evidence.
- Word-level evidence architecture is coherent: tool output becomes claims and
  triples, Witness Sense Units, exact buckets, learner-facing summaries, and a
  selected-word reader context payload with lexical/morphology evidence and
  Foster bridge overlays from morphology analysis.
- Foster TOC summary pipeline is complete: 105-entry full run with experience
  rollups, essentials carry `experience:*` refs, `--retry-only` CLI option for
  targeted regeneration of invalid rows, and `foster_bridge` field in the
  reader word-context payload.
- Public/static pages, crawler boundaries, and SvelteKit route policy now have a
  documented product boundary.
- Public traffic controls are observe-mode ready: anonymous sessions, scoped
  client attestation, request-cost headers, crawler API policy, rate-limit
  decision metadata, and rollup storage exist. Soft/enforced limits and
  Cloudflare rule tuning are deferred to `docs/plans/todo/infra/`.

## Main Risks

- Active reader work should stay focused. Use the Reader And Library section
  below as the reader coordination layer.
- Source acquisition is easy to overrun. The framework is documented in
  `docs/technical/reader-source-acquisition.md`; do not import broad series until a
  manifest, staged sample, source role, boundary policy, and known-issues row
  exist.
- Learner copy and compact glosses can sound fluent before they are sufficiently
  source-backed. Keep provenance visible and caveats explicit.
- Reader selected-word context now has a shared CLI/API/UI payload; the ongoing
  risk is keeping generated summaries visually subordinate to deterministic
  lexical, morphology, reader-hit, and caveat fields.
- Search-index rebuilds and long-running reader operations need deliberate
  checkpoints, not incidental rebuilds during unrelated work.

## Active Queue

Work the active-plan closeout queue in this order unless a blocker forces a
short detour:

1. Finish corpus acquisition gates before expanding the reader collection.
   Source-backed enrichment, citation-reference resolution, and the OGL audit
   surface/direct-comparison slice are closed for the current deterministic
   slices. The source-acquisition framework is also closed for the current
   manifest/staging/source-role/quality-gate slice; optional or broader
   follow-ups are tracked under `docs/plans/todo/infra/`.
2. Close or demote public operations, UI/design policy, Foster summaries, and
   dated tracker/coordination records once their durable instructions live in
   the execution plan, roadmap, or scoped todo plans.

Canonical catalog export is closed for the directory-bundle implementation:
`reader export work`, `reader export bundle`, and `reader export validate` now
write/validate LangNet canonical bundles. Presentation exports and portability
packaging are tracked separately under `docs/plans/todo/infra/`.

| Rank | Task | Why Now | Validation |
| --- | --- | --- | --- |
| 1 | Reader quality gates before expansion | Prevent PL/PG/CSEL/humanist acquisition from adding unreadable or misclassified catalog rows | source-index TSVs, `/library`, `current_known_issues.tsv`, representative `reader contents` checks |
| 2 | Learner encounter quality | Keep word-level answers useful before broader passage interpretation | `reader-eval`, encounter snapshots, translation projection tests |
| 3 | Source structuring | Split source blobs only where fixtures justify typed fields | source-specific parser/display tests |
| 4 | Translation cache operations | Keep lookup network-free by default while supporting explicit DICO/Gaffiot/Bailly population | no-network tests, cache diagnostics, web retry tests |
| 5 | Public/web boundary | Keep crawlable pages cheap and keep `/q`, `/reader`, and `/api/*` bounded | route-policy tests, web build/check, crawler log review |
| 6 | Evidence walkthroughs | Make provenance traceable from display to triples/source refs | docs examples, `plan-exec`, `triples-dump`, CLI tests |

## Immediate Concrete Targets

### Reader Eval Fixtures

Maintain tolerant assertions for:

- classic-opening reader forms in `tests/fixtures/reader_eval_classics.json`;
- corpus-expansion forms in `tests/fixtures/reader_eval_corpus_expansion.json`.

Check:

- expected lemma top-1/top-3;
- expected gloss tokens;
- known bad lemma not top-ranked;
- morphology/analysis availability;
- compound/enclitic split visibility.

### Headword And Form Gates

Keep these reader-form cases covered:

- `virumque` resolves to `vir + -que`, with tackon evidence below the content word;
- `μῆνιν` prefers `μῆνις` and keeps surface morphology visible;
- `θεὰ` prefers `θεά`;
- `Troiae` can reach `Troia` through a general reader-form candidate;
- `Ἀχιλῆος` can reach validated epic `-εύς` headwords;
- `karma` routes to `karman` when source evidence supports the concept entry;
- Sanskrit compound rows preserve segment-level lemmas.

### Compact Glosses

Use translated or source-backed entries to derive short display helpers:

- `arma`: arms; weapons; war; troops
- `cano`: sing; sing of; celebrate
- `dharma`: law; duty; virtue; proper nature
- `karman`: act; action; rite; duty; karma

The compact gloss is display metadata. It must not replace the source or
translated witness.

### Translation Cache

Keep current behavior:

- cache mode reads exact cache hits only;
- auto/population modes are explicit before any provider call;
- default encounter makes no hidden network call;
- `translation-warm` populates missing rows for a word list;
- `translation-cache status` reports cache state.

Next additions:

- Bailly translation-cache fixtures and examples where local Bailly rows exist;
- optional pretty/debug cache diagnostics;
- timeout/chunking policy for long entries;
- passage-vocabulary cache warming.

### SvelteKit Adapter

Keep the webapp as an adapter over existing contracts:

- `/api/search` for search;
- `/api/reader` for reader catalog/text/search modes;
- `/api/word-index` for dictionary browsing;
- `/api/paradigm` for source-backed paradigm data;
- `/api/motd` for message-of-the-day data;
- `/api/translation-cache` for cache inspection and scoped maintenance.

The webapp should render structured fields from CLI/data outputs, not scrape
pretty terminal text or introduce separate semantic behavior.

Public traffic controls should remain observe-first until deployment traffic has
been reviewed. Do not enable route-level 429 enforcement or Cloudflare
challenge/rate-limit rules without updating
`docs/plans/todo/infra/public-traffic-enforcement-and-cloudflare-tuning.md`.

### Reader And Library

Treat reader/library expansion as a quality-controlled acquisition pipeline.

**Parity target:** the goal is not raw corpus-count parity. It is
provenance-and-reader-quality parity across every expansion lane before broad
import. For each new corpus family or source family:

- a source manifest exists before text enters the reader catalog;
- the source-index can answer what was imported, from where, with language,
  author/title, source path, segment count, token count, and quality status;
- one representative staged/imported sample has been inspected for readable
  text, work boundaries, and front-matter/OCR noise;
- known defects are tracked in
  `data/reference/reader_quality_audit/current_known_issues.tsv`;
- expansion queues distinguish external source gaps, local checkout gaps,
  importer gaps, and UI/discovery gaps;
- `/library`, CLI `reader works`, and CLI/API source-index views expose the
  import without making wanted/acquisition targets look like already-readable
  works.

**Acquisition framework:**

- create or update source manifests before importing text;
- stage and inspect a bounded sample before series-scale import;
- keep raw sources, staged text, curated metadata, generated metadata, and
  catalog/source-index output separate;
- update `data/reference/reader_quality_audit/current_known_issues.tsv` before
  changing a risky target to imported/import-ready;
- make `/library` distinguish imported works from staged, planned, wanted, or
  deferred acquisition targets;
- use `docs/technical/reader-source-acquisition.md` for source roles, quality
  statuses, staging commands, and verification;
- use the reader-work ingestion skill at
  `/home/nixos/.agents/skills/langnet-reader-work-ingestion/SKILL.md` as the
  process guardrail for reusable ingestion across many authors and corpora.

**Current lane status:**

- PL122/Eriugena: pilot-slice parity met for fourteen works; keep segmentation
  as a watch item.
- Popular classical Latin: parity not met until a source-reviewed open/mirrorable
  path exists for the highest-demand classroom works (Caesar or Sallust first).
- Humanist/mystical source library: Cusanus imported; Bruno imported; Agrippa
  deferred (lexeme-level OCR cleanup needed); Ficino has manifest-backed
  candidates; Aquinas q.50 preserved as non-importable evidence; Duns Scotus
  source-decision deferred.
- Patrologia Graeca: sample-import parity met; reader-quality parity not met
  until OCR noise and segmentation are calibrated against a second witness.
- CSEL: CSEL61 has a verified source candidate; acquisition parity not met until
  one PDF/OCR witness is parsed and a readable sample is staged.
- Library: CLI/API/server-rendered parity exists; browser interaction QA remains.
- Search: reader catalog/source-index parity exists; `search.lance` rebuild
  deferred until the next approved expansion or reader-quality gate.

**Acquisition stop conditions.** Pause and ask for review if:

- a source role is unclear (bibliography, scan locator, database UI, OCR
  witness, or clean text witness);
- a staged text is mostly OCR noise;
- work boundaries cannot be inferred without human judgment;
- a proposed importer change would change source-view precedence for many
  existing Patrologia/CSEL rows;
- a UI change would make wanted/acquisition targets look like imported works.

**Immediate reader priority** is QA and targeted follow-through, not another
broad import batch:

- confirm Cusanus reader/Library provenance display;
- keep PL122 segmentation as a watch item for future PL imports;
- calibrate the PG pilot before broad PG expansion;
- select one popular Latin prose target only after source review;
- keep Agrippa, Aquinas q.50, and Duns Scotus deferred until their source
  quality decisions are explicit;
- keep Bruno as a completed bounded acquisition slice:
  `bruno_esotericarchives` has three imported Latin works and source-index rows;
  the canonical export smoke bundle for `De Magia` validates under
  `examples/debug/catalog-export-bruno-de-magia`;
  Llull remains a source-research continuation under `docs/plans/todo/infra/`.

## Validation Loop

Use the narrowest test first, then broaden:

```bash
just test test_cli_encounter_output test_translation_projection
just ruff-check
just typecheck
just validate-stabilization
```

Before a larger checkpoint, run:

```bash
just lint-all
just test-fast
```

Run Just/devenv recipes sequentially. Parallel recipe probes can produce
misleading positional-argument failures.

## Deferred Work

These remain out of scope until the active queue is stable:

- embeddings and semantic similarity;
- LLM-generated explanations as primary output;
- passage-level disambiguation;
- first-class Python product API beyond the current SvelteKit adapter;
- broad hydration beyond optional labels/links.
- broad corpus acquisition without manifest and staged-sample gates.

## Decision Gates

Advance beyond exact buckets only when:

- WSU extraction and exact buckets are fixture-stable;
- each WSU carries evidence IDs and display metadata;
- reducer tests require no live backend;
- `triples-dump` inspects the same facts the reducer consumes;
- representative reader eval fixtures pass.

Advance passage work only when:

- word-level hit quality is reliable for representative classics;
- compact glosses exist for common DICO/Gaffiot/Bailly/CDSL/LSJ/Lewis entries;
- provenance remains visible from every learner-facing meaning.
