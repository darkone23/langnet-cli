# Sanskrit Canonical Cleanup @scribe @coder

## Goal
Finish the Sanskrit canonicalization flow so all Sanskrit tools (Heritage, CDSL, CLI) operate on canonical forms without duplication or legacy endpoints.

## Current state
- Canonicalization: `SanskritNormalizer` now prefers Heritage `sktsearch`, produces Velthuis + SLP1/IAST alternates, and merges enrichment metadata.
- Heritage lemmatize: powered by `sktreader` morphology (legacy lemmatizer removed) with canonical inputs routed via normalization.
- Backend noise trimmed: CLTK/Diogenes/Sanskrit duplication reduced; Sanskrit adapter now injects `canonical_form`/`input_form` metadata.
- Guardrails: unit tests cover agni/vrika canonicalization; failing test prevents `sktlemmatizer` from reappearing.

## Gaps / Risks
- CLI still lacks a user-facing canonical hint when input differs from canonical.
- No integration coverage that tool invocations (heritage/cdsl) actually receive canonical SLP1 and report it back.
- CDSL path still lowercases SLP1 internally; long-vowel fidelity for lookups is unverified.
- Docs/fixtures not updated for the canonical flow.

## Closeout path (to move to completed)
1) **Canonical propagation tests (P0, @auditor/@coder)**
   - Add integration tests: `cli tool heritage lemmatize --query agni/vrika` surface canonical inputs; CDSL lookup records SLP1 (`vfka`).
   - Assert returned entries carry `canonical_form` + `input_form` for heritage + cdsl.

2) **User-facing canonical hint (P1, @coder)**
   - CLI/API outputs show canonical when it differs (`agni → agnii / agnI`) without noisy banners; guarded behind a small toggle if needed.

3) **CDSL fidelity (P1, @coder)**
   - Remove destructive lowercasing of SLP1; add fixture proving long-vowel preservation.

4) **Docs/fixtures refresh (P2, @scribe)**
   - README/DEVELOPER + sample fixtures (agni, vrika, vrika→vfka) describe the canonical pipeline/metadata.

## Definition of done
- Above items landed with tests/fixtures and docs updated.
- `just cli tool heritage morphology --query vrika` + `heritage lemmatize --query agni/vrika` pass with canonical metadata.
- `just cli tool cdsl lookup --query vrika` uses SLP1 form and returns entries with canonical hints.
- `just test tests.test_sanskrit_canonicalization tests.test_forbidden_terms` green; regression fuzz spot-checks recorded in pickup notes.
