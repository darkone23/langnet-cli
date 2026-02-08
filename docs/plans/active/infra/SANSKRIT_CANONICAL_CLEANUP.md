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

## Next steps
1) **Assert canonical propagation** (@auditor)
   - Add integration tests: `cli tool heritage lemmatize --query agni/vrika` surface canonical inputs; CDSL lookups recorded with SLP1 (`vfka`).
   - Verify returned entries carry `canonical_form` + `input_form` consistently (heritage + cdsl).

2) **Surface canonical to users** (@coder)
   - Add CLI/API hint when canonical differs (e.g., `agni → agnii / agnI`), keeping output noise minimal.

3) **Fidelity checks for CDSL** (@coder)
   - Audit/lint CDSL lookup path to avoid destructive lowercasing of SLP1 where it harms long vowels; add a fixture if adjustments are needed.

4) **Docs & fixtures** (@scribe)
   - Update README/DEVELOPER and sample fixtures (agni, vrika, vrika → vfka) to describe canonical pipeline and metadata.

## Verification checklist
- `just cli tool heritage morphology --query vrika` returns lemma.
- `just cli tool heritage lemmatize --query vrika` returns lemma/grammar from sktreader.
- `just cli tool heritage lemmatize --query agni` succeeds (canonicalized).
- `just cli tool cdsl lookup --query vrika` hits SLP1 form and returns entries.
- Tests: add/green for normalization + integration as above.
