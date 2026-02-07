# Mapping Phase Handoff

## Objective
- Hand off remaining pedagogy mapping work (Foster exposure, canonical consistency, CTS normalization) so `/api/q` stays learner-first across Latin/Greek/Sanskrit.

## Context
- Foster codes now flow through morphology; dictionary-side exposure and citation normalization remain.
- CTS URN mapper lives in `src/langnet/citation/cts_urn.py` with a local DB for Perseus → CTS conversions.
- Heritage upstream docs (ABBR, manual) reviewed; Sanskrit plan sits at `docs/plans/todo/skt/HERITAGE_INTEGRATION_NEXT_STEPS.md`.

## Gaps To Close (@coder / @auditor / @scribe)
- **CTS normalization**
  - Normalize Diogenes citations via CTS mapper; keep `original_citation` alongside `cts_urn` + display.
  - Attach normalized citations to both morphology chunks and dictionary blocks; ensure aggregation surfaces them.
- **Dictionary Foster + POS**
  - Diogenes dictionary blocks: derive POS/foster from nearby morph tags when available; fall back gracefully.
  - Whitaker/CLTK lines: tag senses with POS + foster_codes where codelines allow; keep raw tags in metadata.
- **Canonical consistency**
  - Latin/Greek: betacode→Unicode and macron-preserving `canonical_form` applied before mapping; carry through aggregation.
  - Sanskrit: ensure `canonical_form` from sktsearch/lemmatize threads through Heritage/CDSL dictionary-only entries.
- **Schema & grouping**
  - Group entries by `canonical_form` + `lemma`; ensure foster_codes appear on dictionary-only entries (metadata if needed).
  - Keep transliterations (IAST/SLP1/Devanagari) + roots where available.
- **Docs & examples**
  - Record “good” payloads (lat `lupus`, grc `logos`, san `agni`, `yogena`) with foster_codes, canonical, CTS citations.
  - Update pedagogy docs once payloads are stable; cite CTS usage and foster exposure rules.
- **Validation**
  - Run `just fuzz-compare` for regression guard; manual spot-check CTS-heavy queries.

## Risks / Mitigations
- Citation loss → always keep `original_citation` in metadata when normalizing.
- Over-eager foster mapping → gate on confident tag parses; retain raw tags for audit.
- Transliteration drift → restrict auto-normalization to clear cases; document skipped cases for follow-up.
