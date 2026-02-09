# fixing-types

Checkpoint for ongoing typing cleanup across langnet-cli. Pick up from here.

## Requirements / guardrails
- Do **not** introduce `Any`; prefer concrete types, TypedDicts, Protocols, or casts.
- It is OK for tests to add explicit type assertions/casts to narrow unions and enforce expected shapes.
- Avoid behavior changes; keep runtime flow the same while tightening types.

## Progress (current)
- `just typecheck` now passes cleanly.
- CLTK tool typing tightened: `classics_toolkit/core.py` uses TYPE_CHECKING imports for CLTK classes, keeps guards for Latin resources.
- Heritage typing cleanups:
  - `heritage/morphology.py` adds sktreader normalization helper, fixes dictionary lookup TypedDict keys, narrows morphology analysis handling, and ensures fetch param types match client expectations.
  - `heritage/parameters.py` ParamDict now accepts None/bool and transliterate calls guarded when schemes are missing.
  - `heritage/html_extractor.py`/`heritage/parsers.py` pattern extraction and metadata now use concrete Morphology* TypedDicts with casts.
  - Encoding bridge tests updated with dict assertions/casts; `heritage_cdsl_integration` no longer subscripts Unknowns.
- Normalization:
  - `normalization/models.py` adds safe citation typing/conversion without `Any`.
  - `normalization/sanskrit.py` returns JSONMapping consistently, guards canonical token handling, and drops invalid `lexicon` kwarg when calling Heritage client.
- Indexers: config path values coerced to `Path`-friendly strings; stats fetching guards against `fetchone()` returning None.
- Minor test hygiene: CTS URN/health tests now assert dict types before `.get()`/`.values()`.

## Notes / handoff
- No behavior changes intended; only type tightening and safer casts/guards.
- If further runtime regressions are suspected, rerun `just typecheck` first, then spot-check Heritage/CTS flows after restarting any long-lived processes per AGENTS restart note.
