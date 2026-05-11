# Project Execution Plan

**Date:** 2026-05-05  
**Mode:** stabilization before feature expansion

This is the compact operating queue. Use `docs/BASELINE_AND_ROADMAP.md` for the
current checkpoint and `docs/ROADMAP.md` for the milestone sequence.

## Current Thesis

LangNet has enough runtime foundation to be useful. The current task is to make
word-level `encounter` output reliable for readers while preserving source
evidence and inspectability.

Do not expand into passage interpretation, embeddings, or broad semantic
inference until the active queue below is stable.

## Active Queue

| Rank | Task | Why Now | Validation |
| --- | --- | --- | --- |
| 1 | Preserve reader-eval gates | Keep classic-opening and corpus-expansion fixtures green while adding real forms | `reader-eval` fixtures + encounter tests |
| 2 | Source structuring | Split source blobs only where fixtures justify typed fields | source-specific parser/display tests |
| 3 | Compact gloss coverage | Extend short learner glosses above full source entries without hiding provenance | translation projection + encounter snapshots |
| 4 | Translation cache operations | Make cache warming practical and keep lookup network-free by default | no-network tests + docs examples |
| 5 | CLI/web readiness | Keep JSON contracts, `doctor`, `langs`, `tools`, and read-only cache profiles usable for subprocess callers | CLI contract tests + `doctor` |
| 6 | Evidence walkthroughs | Make provenance traceable from display to triples/source refs | docs examples + existing CLI tests |

## Immediate Concrete Targets

### Reader Eval Fixtures

Maintain tolerant assertions for:

- classic-opening reader forms in `tests/fixtures/reader_eval_classics.json`
- corpus-expansion forms in `tests/fixtures/reader_eval_corpus_expansion.json`

Check:

- expected lemma top-1/top-3;
- expected gloss tokens;
- known bad lemma not top-ranked;
- morphology/analysis availability;
- compound/enclitic split visibility.

### Headword And Form Gates

Keep these reader-form cases covered:

- `virumque` should resolve to `vir + -que`, not lead with `virus`;
- `μῆνιν` should prefer `μῆνις` and keep surface morphology visible;
- `θεὰ` should prefer `θεά`;
- `karma` should route to `karman` when the DICO/MW concept entry is intended.

### Compact Glosses

Use translated or source-backed entries to derive short display helpers:

- `arma`: arms; weapons; war; troops
- `cano`: sing; sing of; celebrate
- `dharma`: law; duty; virtue; proper nature
- `karman`: act; action; rite; duty; karma

The compact gloss is display metadata. It must not replace the source or
translated witness.

Current source-structuring progress:

- CDSL source-note segments are preserved and can be shown below source refs in
  `encounter`.
- Diogenes definition triples carry `learner_gloss` and `learner_segments` so
  LSJ/Lewis-style entries have a compact learner summary available downstream.

### Translation Cache

Keep current behavior:

- `--translation-mode cache`: read exact cache hits only;
- `--translation-mode auto`: explicitly populate missing rows, then display;
- default encounter: no hidden network call.
- `translation-warm`: explicitly populate missing rows for a word list.
- `encounter --output json`: report cache availability, hit/miss counts, and
  writes.

Next additions:

- optional pretty/debug cache diagnostics;
- timeout/chunking policy for long entries.

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

Run these Just/devenv recipes sequentially. Parallel recipe probes can produce
misleading positional-argument failures.

## Deferred Work

These remain out of scope until the active queue is stable:

- embeddings and semantic similarity;
- LLM-generated explanations as primary output;
- passage-level disambiguation;
- first-class API/UI product contract;
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
- compact glosses exist for common DICO/Gaffiot/CDSL/LSJ/Lewis entries;
- provenance remains visible from every learner-facing meaning.
