# Semantic Reduction Readiness

**Status:** ready for MVP extension, not ready for learner-quality semantic generalization.

LangNet now has a small runtime semantic path: claim triples become Witness Sense Units, exact gloss buckets, and `encounter` output. That is enough to extend the MVP carefully, but not enough to claim broad semantic reduction or learner-quality encounters.

## What Is Ready

- Core handlers emit claim triples.
- Fixture-backed claim contract tests exist for Whitaker, CDSL, Diogenes, CLTK, Heritage, DICO, and Gaffiot.
- Predicate drift is guarded by a test.
- A hand-written `lupus` WSU fixture exists under `tests/fixtures/`.
- DICO/Gaffiot local raw response IDs are content-addressed and regression-tested.
- Docs now describe the intended WSU → bucket path.
- Runtime WSU extraction exists over `has_sense + gloss + evidence`.
- Exact-match bucket grouping exists.
- `langnet-cli encounter` displays reduced buckets and shows Heritage morphology analysis rows for Sanskrit.
- Cached DICO/Gaffiot translations can be projected as derived evidence before reduction.
- `triples-dump --output json` exposes structured claims and triples for reducer debugging.
- A 50-word diagnostic audit now distinguishes gloss hits from Heritage morphology/evidence hits.
- Accepted `encounter` snapshots now cover translated DICO/Gaffiot cache hits and multi-witness ranking.
- A dedicated learner encounter roadmap now tracks current failures and validation
  tasks for Sanskrit, Latin, and Greek:
  `docs/plans/active/pedagogy/learner-encounter-roadmap.md`.

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

The fuzz harness is useful for parser diagnostics, and the current 50-word audit shows strong evidence coverage. It still should not be used as proof that semantic reduction is ready: hit rates show that evidence exists, not that the top learner-facing answer is the best one.

### 6. Exact Buckets Are Not Semantic Buckets

The current reducer groups exact normalized gloss strings. It is deterministic and inspectable, but it does not yet merge synonyms, reorder source entries by learner value, or split large dictionary entries into clean individual senses.

### 7. Translation Is Cache-Bearing But Selectively Populated

DICO and Gaffiot source entries are French. The cache schema, cache-hit projection, and Gaffiot/DICO golden rows exist, but representative cache rows are not yet broadly populated, and network translation must remain explicit opt-in.

### 8. CDSL Entries Are Still Flat

CDSL display now exposes IAST forms and source keys, and `encounter` performs conservative source-complete display transforms. The underlying CDSL glosses are still large flat strings that mix entry headwords, grammar, citations, abbreviations, compounds, and actual gloss text.

### 9. Learner Encounter Ranking Is Not Trustworthy Yet

Current examples show that evidence existence is not the same as learner quality.
`nirudha` can rank obscure CDSL material first, `dharma` still exposes flat
source strings, `lupus` can show unrelated normalized Latin candidates, and
`logos` can expose large LSJ sections without a concise sense summary.

## Recommended Next Steps

1. Add accepted-output fixtures for hard encounter terms before changing display logic.
2. Split source glosses into structured display fields before attempting semantic similarity.
3. Fix candidate/form hygiene so unrelated analyzer candidates do not pollute learner output.
4. Expand cache-backed translation examples beyond the current golden rows and snapshots.
5. Extend accepted-output examples for harder multi-source disagreements, not just happy-path matches.
6. Delay embeddings and LLM similarity until exact buckets plus source display are boring.

## Readiness Bar

Semantic reduction can advance beyond the exact-bucket MVP when:

- WSU extraction and exact buckets remain fixture-stable.
- Each WSU carries claim/evidence IDs and display metadata.
- No live backend is required for reducer tests.
- `triples-dump` can inspect the same facts the reducer consumes.
- DICO/Gaffiot translated glosses are cache-backed and evidence-bearing before they influence buckets.
- CDSL flat entry strings are structured enough that ranking does not privilege undifferentiated source notation.
- The representative encounter set (`san nirudha`, `san dharma`, `lat lupus`,
  `grc logos`) has accepted learner-facing output and JSON evidence fixtures.
