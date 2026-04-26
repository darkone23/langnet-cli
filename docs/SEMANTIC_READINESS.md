# Semantic Reduction Readiness

**Status:** not ready for implementation beyond fixtures.

LangNet has enough claim/triple infrastructure to prepare semantic reduction, but not enough stabilized behavior to build the full reducer confidently.

## What Is Ready

- Core handlers emit claim triples.
- Fixture-backed claim contract tests exist for Whitaker, CDSL, Diogenes, CLTK, Heritage, DICO, and Gaffiot.
- Predicate drift is guarded by a test.
- A hand-written `lupus` WSU fixture exists under `tests/fixtures/`.
- DICO/Gaffiot local raw response IDs are content-addressed and regression-tested.
- Docs now describe the intended WSU → bucket path.

## Blocking Gaps

### 1. Claim Shape Still Varies By Handler

Handlers emit useful triples, but claim-level predicates and value shapes are not fully normalized. A reducer can start from triples, but should not depend on backend-specific `claim.value` fields.

### 2. Predicate Constants Are Not Fully Used

The constants module exists, but handlers still emit many predicate strings directly. This is manageable, but it increases drift risk.

### 3. Evidence Inspection Is Still Thin

`triples-dump` exposes triples and now supports predicate/subject/max-count filters. Before semantic reduction, developers should still be able to quickly answer:

- which claims produced this gloss?
- which raw response produced this claim?
- which tool failed or was skipped?

### 4. CLTK Is Environment-Sensitive

CLTK now uses a writable data directory, but model data may be missing. Semantic fixtures must not depend on live CLTK until this is consistently handled.

### 5. Fuzz Harness Is Not A Semantic Gate

The fuzz harness is useful for parser diagnostics, but query/compare modes still reflect older API assumptions. It should not be used as proof that semantic reduction is ready.

### 6. No WSU Extractor Contract Yet

There is a WSU fixture contract, but no runtime extractor. The next safe step is an extractor that consumes only triples:

```text
has_sense + gloss + evidence → WitnessSenseUnit
```

### 7. Translation Is Not Yet Evidence-Bearing

DICO and Gaffiot source entries are French. The ad-hoc translation script can translate sampled rows and is tuned most heavily for Gaffiot, but translated text is not cached, not represented as translation evidence, and not visible to `triples-dump`. Gaffiot and DICO source entries now flow through staged effects, but both remain French source evidence. Semantic reduction should not depend on translated Gaffiot/DICO glosses until the cache path in `docs/TRANSLATION_CACHE_PLAN.md` exists.

## Recommended Next Steps

1. Add a tiny WSU extractor over claim triples.
2. Keep it service-free and fixture-driven.
3. Add exact-match bucket grouping only after extractor tests pass.
4. Add cached translation triples only after cache-hit behavior is testable without network calls.
5. Delay embeddings, semantic constants, and learner display changes.

## Readiness Bar

Semantic reduction is ready to start only when:

- WSU extraction works from fixture claims.
- Each WSU carries claim/evidence IDs.
- No live backend is required for reducer tests.
- `triples-dump` can inspect the same facts the reducer consumes.
- DICO/Gaffiot translated glosses are cache-backed and evidence-bearing before they influence buckets.
