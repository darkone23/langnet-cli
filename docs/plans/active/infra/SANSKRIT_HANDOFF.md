# Sanskrit Encoding & Hit-Rate Handoff

Audience: backend devs QA’ing recent Sanskrit normalization/hit-rate fixes.

## What changed (concise)
- Heritage inputs coerced to Velthuis; compounds preserved.
- CDSL lookup cleans SLP1 candidates and attaches canonical metadata.
- Normalizer prefers sktsearch canonical; multi-token canonicalization keeps vocalic ṛ/ḷ.
- CDSL adapter emits one entry per dictionary with canonical hints.

## Quick verification (minimal)
- `just cli tool heritage morphology --query yogaanuzaasanam` (compounds preserved).
- `just cli tool cdsl lookup --query "anuśāsana" --output json` (clean transliteration, canonical_form set).
- `just cli tool heritage canonical --query agni` / `vrika` (canonical_text populated).
- `just test tests.test_sanskrit_canonicalization tests.test_forbidden_terms`.

## Edge cases
- `just cli query san agni` → one CDSL entry with canonical hint; no duplicates.
- `just cli query san "atha yogaanuzaasanam"` → no crash; canonical tokens present.
- `just cli query grc ousia` → Greek citation text in Unicode (not betacode).

## Closeout checklist (to move to completed)
- Multi-word Sanskrit tokenization: add fixture for phrases where sktsearch returns empty but we still pass through safely.
- CDSL long-vowel fidelity: fixture proving SLP1 is preserved (no lowercasing loss).
- Canonical hints: surfaced to CLI/API users when canonical != input.
- Heritage enrichment: abbreviations/CTS applied or explicitly deferred with doc note.
- Spot fuzz: record outputs for `san agni`, `san yogaanuzaasanam`, `grc ousia` after changes.

## Definition of done
- All checklist items landed with tests/fixtures and short doc note.
- `just cli tool heritage morphology --query yogaanuzaasanam` and `cdsl lookup --query "anuśāsana"` succeed with canonical metadata.
- Regression guard: fuzz/spot outputs attached to pickup notes; server restarted (`just restart-server`) after backend changes.
