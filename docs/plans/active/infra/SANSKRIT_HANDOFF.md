# Sanskrit Encoding & Hit-Rate Handoff

Audience: backend devs QA’ing recent Sanskrit normalization/hit-rate fixes.

## What changed
- Heritage inputs are coerced to Velthuis before `sktreader`, avoiding encoding misfires (IAST/Deva/ASCII all routed to VH).
- Heritage parser now captures inline `latin12` segments between solution markers, so compounds (e.g., `yogaanuzaasanam`) retain decomposition instead of being dropped.
- CDSL lookup builds a clean SLP1 candidate list (filters mangled forms with quotes/digits), retries candidates, and attaches canonical metadata.
- Normalizer uses sktsearch canonical first; generates alternates in SLP1/IAST/Deva; guardrails keep `sktlemmatizer` out.
- CDSL adapter now emits a single entry per dictionary with canonical/input forms attached; metadata carries canonical hints instead of duplicating payloads.
- Sanskrit canonicalization handles multi-token queries by canonicalizing each token via sktsearch before hitting tools; SLP1 fallback mapping now keeps vocalic ṛ/ḷ vowels.
- Diogenes citation metadata attempts betacode → Unicode cleanup for Greek abbreviations/citations.

## Quick verification commands
1) Compound parsing (Heritage):
   - `just cli tool heritage morphology --query yogaanuzaasanam`
   - Expect solutions present with segments showing `yoga a | a → ā anuśāsanam`; no “unknown” error.

2) Diacritic lookup (CDSL hit-rate):
   - `just cli tool cdsl lookup --query "anuśāsana" --output json`
   - Expect MW entry with transliteration `anuzAsana` (no stray quotes/digits), `canonical_form` populated.

3) Canonicalization sanity:
   - `just cli tool heritage canonical --query agni` → canonical_text `agnii`
   - `just cli tool heritage canonical --query vrika` → canonical_text `v.rka`

4) Regression smoke (tests):
   - `just test tests.test_sanskrit_canonicalization tests.test_forbidden_terms`
   - `just test tests.test_normalization tests.test_normalization_standalone`

## Recent edge cases to spot-check
- `just cli query san agni` should return one CDSL entry (with `canonical_hint`) rather than repeated copies.
- `just cli query san "atha yogaanuzaasanam"` should not crash; canonical tokens should appear and the first token should still resolve.
- `just cli query grc ousia` should show Greek citation text (Zosimus) in Unicode rather than raw betacode.

## Known gaps to watch
- Multi-word phrases still need tokenization; sktsearch returns empty for full phrases.
- CDSL long-vowel fidelity not fixture-tested; SLP1 lowercasing risk unverified for edge cases.
- Canonical hints not yet surfaced to end users in CLI/API.
- Heritage abbreviation/CTS enrichment still pending.

## Logs/metadata to inspect
- Heritage morphology responses now include `metadata.segments` per solution (compound decomposition).
- CDSL raw includes `canonical_form`, `canonical_form_candidates`, `input_form` for debugging lookup path.
