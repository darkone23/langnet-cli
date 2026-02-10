# Roadmap / Next Steps

Short, actionable priorities to keep pedagogy and maintainability moving.

## Near-term (P0–P1)
- **Pedagogy surfacing:** tighten output ordering (head → senses → references → foster features) and verify via regression snapshots. Add a small UI recipe to `docs/OUTPUT_GUIDE.md` consumers.
- **Diogenes stability:** expand fuzz/unified harness to cover Perseus citations and ensure sense extraction stays deduplicated.
- **Heritage normalization:** add guardrails for mangled SLP1 detection and document the normalization contract for downstream clients.
- **Whitaker’s availability checks:** surface a clear error when the binary is missing and add a CLI `verify` hook.

## Mid-term (P2)
- **DICO integration:** implement the DuckDB-backed DICO adapter per `docs/plans/todo/dico/DICO_ACTION_PLAN.md` and add fuzz snapshots.
- **Universal schema:** converge morphology/lexicon outputs so clients can render the same structure for Latin/Greek/Sanskrit with minimal branching.
- **Foster enrichment coverage:** extend functional labels to Heritage and Diogenes where metadata allows; document fallbacks.

## Long-term (P3)
- **Fuzzy search:** add tolerant lookup for common encoding and accent errors across all three languages.
- **Enhanced citations:** stabilize CTS URN mapping and add learner-friendly citation formatting.
- **Performance/UX:** cache hot paths (e.g., Monier-Williams headwords, Whitaker’s inflection tables) and track latency regressions via `timing_ms`.
