## Cleanup Guide and Test Hardening Plan

### Current State
- `just test` passes (425 tests, 0 skipped).
- Heritage dictionary/live integration suites removed; stable coverage via fixtures/mocks in:
  - `tests/test_heritage_integration_unittest.py`
  - `tests/test_heritage_platform_integration.py`
  - `tests/test_real_heritage_fixtures.py`
  - `tests/test_heritage_connectivity.py`
- Normalization tests assert structure and encoding, not confidence scoring.
- Diogenes/Whitaker/CDSL tests rely on curated fixtures and golden masters.

### Gaps (Not Covered)
- Heritage dictionary service (no implementation; no tests).
- Live Heritage backend shape changes (CI relies on fixtures/mocks, not live HTML).
- Normalization exact canonical outputs are lightly asserted.
- CLTK Greek/Latin morphology correctness largely untested.
- Limited performance guardrails (only a relaxed check in `test_universal_schema_integration`).

### Recommended Enhancements
1) **Heritage Robustness**
   - Add a fixture-refresh script to pull current `sktsearch`/`sktreader` HTML and regenerate fixtures under `tests/fixtures/heritage/` with a version tag. Gate behind a manual flag.
   - Expand `test_real_heritage_fixtures.py` to validate richer patterns (table counts, key spans) against fixtures, not live endpoints.

2) **Normalization Precision**
   - Add exact canonical expectations per language/encoding (Sanskrit ASCII → velthuis/slp1 form; Latin macron stripping; Greek betacode → unicode).
   - Assert alternates contain expected variants (Latin i/j, u/v; Greek betacode+unicode) instead of only type checks.

3) **Adapter/Schema Fidelity**
   - In `test_universal_schema_integration`, assert minimal required fields per source (non-empty definitions/morphology features when present) using fixtures to avoid live drift.
   - Add a small JSON-schema-style validation for universal entries (word, language, source required; optional blocks must have non-empty core fields).

4) **CLTK Coverage**
   - Add fixture-based assertions for CLTK Greek/Latin morphology outputs (mock when CLTK unavailable) to verify shape and basic fields (lemma, pos).

5) **Performance Guardrails**
   - Replace loose perf checks with fixture-driven timing budgets (cached inputs) and skip when environment is noisy.

6) **Test Hygiene**
   - Periodic audit to remove low-value `isinstance`-only assertions; pair type checks with at least one content check.
   - Document any live/manual suites in `tests/README.md` under a “Manual/Live” section with run instructions and expected variability.

### What to Delete vs. Keep
- Keep fixture/mocked suites as the stable default.
- Do not reintroduce deleted Heritage dictionary/live tests until a new dictionary service or stable sandbox exists.
- If adding live tests, gate with an explicit env flag and prefer fixture fallbacks.

### Quick Start for Next Pass
1. Run `just test` to confirm baseline.
2. Harden normalization expectations in `tests/test_normalization.py` and `tests/test_normalization_standalone.py` (exact canonical forms + alternates).
3. Refresh Heritage fixtures (if you have access), then rerun `test_real_heritage_fixtures.py`.
4. Update `tests/README.md` for any new manual/live sections and fixture-refresh steps.
