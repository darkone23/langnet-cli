# How to Pick Up This Work

## Read First
- `docs/plans/todo/pedagogy/DICTIONARY_FOSTER_AND_ABBREVS.md`
- `docs/plans/todo/pedagogy/CITATION_ENRICHMENT_NEXT.md`

## Code Touchpoints
- `src/langnet/backend_adapter.py`: Whitaker/Diogenes/CLTK dictionary handling, foster propagation, POS heuristics.
- `src/langnet/citation/cts_urn.py`: CTS helper; add abbrev map and fallback displays for non-CTS citations.
- `src/langnet/schema.py`: already carries `citation_details` and `original_citations`.

## Implement Steps (achievable)
1) Whitaker: copy `foster_codes` from morphology/first-term into each sense’s metadata; add `foster_codes` in entry metadata for dictionary-only cases.
2) Diogenes dictionary blocks:
   - Heuristic POS from headings/entry text.
   - If morphology chunk exists, propagate its `foster_codes` into block metadata.
3) CLTK dictionary: keep POS inference; attach foster only when features allow (otherwise leave absent).
4) Abbreviation map:
   - Build an allowlist (LSJ, OLD, L&S, DGE, LfgrE, MW, Apte, Böhtlingk-Roth, Suśr., Uṇ., ĀpŚr., Kātantra, L., etc.; pull source-like items from `docs/upstream-docs/skt-heritage/ABBR.md`).
   - For non-CTS citations, set `display`/`long_name` in `citation_details`; always keep raw ids/text.
5) Aggregation: ensure entry metadata bubbles up `foster_codes` when dictionary-only, and `citation_details` is exposed for all citations (URN or not).

## Verify
- `just fuzz-compare`
- After restart: `just cli query lat lupus`, `grc logos`, `san agni` → dictionary senses show POS + foster where applicable; every citation has a readable display or raw fallback.
- `curl http://127.0.0.1:8000/api/health` post-restart.

## Notes
- CTS DB is Perseus-only today; abbrev map is the near-term path for non-CTS refs.
- Keep originals in metadata to avoid lossy mapping; gate abbrev expansion to the allowlist.
