# Citation Resolution Plan

**Status:** ACTIVE  
**Date:** 2026-04-29  
**Feature Area:** infra  
**Owner Roles:** @architect for resolver scope, @coder for implementation slices, @auditor for provenance review

## Goal

Keep citations useful for readers without making lookup depend on perfect
canonical resolution.

For the current feature set, the invariant is:

- raw source citation strings remain visible;
- known Perseus-style references may be converted to CTS URNs;
- unresolved citations are still emitted as evidence, not dropped;
- future hydration is optional enrichment over preserved evidence.

## Current State

Maintained code now covers the first local-index slice:

- Diogenes Perseus-style references are converted by
  `langnet.execution.handlers.diogenes._to_cts_urn`.
- Diogenes definition triples preserve both `citation_text` and
  `citation_ref` metadata.
- CTS index building lives in `src/langnet/databuild/cts.py`.
- Read-only CTS resolution lives in `src/langnet/citation/resolver.py`.
- Regression coverage lives in `tests/test_citation_preservation.py` and
  `tests/test_cts_citation_resolver.py`.

Observed local indexes on 2026-04-29:

- `data/build/cts_urn.duckdb`: 2,199 authors, 7,786 works, 1,150 editions.
- `~/.local/share/langnet/cts_urn.duckdb`: 2,200 authors, 7,787 works, 1,150
  editions.

The resolver checks `LANGNET_CTS_DB`, then `data/build/cts_urn.duckdb`, then
`~/.local/share/langnet/cts_urn.duckdb`.

Captured from `codesketch/src/langnet/citation/`:

- DB-backed author/work lookup can be useful later, but should not be required
  for learner display.
- Non-CTS abbreviation allowlists are useful design input for Latin and Greek
  source references.
- Betacode-to-Unicode conversion belongs at resolver boundaries, not inside
  display code.
- Failed resolution must preserve the original citation string.

## Next Slices

1. Wire `CtsCitationResolver` into the planned CTS staged calls.
   It already accepts raw citation text/ref plus optional language and returns
   either CTS metadata or an unresolved citation record with the original text.

2. Connect the resolver only where the source already emits citation metadata.
   Do not parse arbitrary dictionary prose as citations in this slice.

3. Add abbreviation fixtures for common Latin and Greek references.
   Keep these as test data, not runtime `if word == ...` cases.

4. Add Sanskrit parity checks.
   CDSL source abbreviations and reference-like tails should be typed and
   preserved even when they do not map to CTS.

## Acceptance

```bash
just test tests.test_cts_citation_resolver tests.test_citation_preservation tests.test_databuild_cts tests.test_claim_contracts
LANGNET_DATA_DIR=examples/debug/validation-data just validate-stabilization
```

The resolver is successful when citations are source-visible first and
canonicalized second.
