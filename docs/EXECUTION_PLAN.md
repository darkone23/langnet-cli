# Project Execution Plan

**Mode:** stabilization before feature expansion

This is the compact operating queue. Use `docs/ROADMAP.md` for the milestone
sequence and `docs/plans/README.md` for plan ownership and lifecycle.

## Current Thesis

LangNet has enough runtime foundation to be useful. The current task is to make
word-level `encounter`, reader corpus discovery, word-index browsing, paradigms,
and the SvelteKit adapter reliable without hiding source evidence.

Do not expand into passage interpretation, embeddings, or broad semantic
inference until the active queue below is stable.

## Active Queue

| Rank | Task | Why Now | Validation |
| --- | --- | --- | --- |
| 1 | Preserve reader-eval gates | Keep classic and corpus fixtures useful while adding real reader forms | `reader-eval` fixtures + encounter tests |
| 2 | Source structuring | Split source blobs only where fixtures justify typed fields | source-specific parser/display tests |
| 3 | Compact gloss coverage | Extend short learner glosses above full source entries without hiding provenance | translation projection + encounter snapshots |
| 4 | Translation cache operations | Keep lookup network-free by default while supporting explicit DICO/Gaffiot/Bailly population | no-network tests + cache diagnostics |
| 5 | Reader/web readiness | Keep CLI JSON, reader catalog/search, word-index, paradigm, and translation-cache contracts stable for SvelteKit routes | CLI contract tests + web route tests |
| 6 | Evidence walkthroughs | Make provenance traceable from display to triples/source refs | docs examples + existing CLI tests |

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
