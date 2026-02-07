# Heritage ABBR Follow-Ups (Next Steps)

## Context
- ABBR.md is now parsed into a cached data file (`src/langnet/heritage/abbr_data.json`).
- Sanskrit references in CDSL/Heritage expose `citation_details` with display/long_name from the shared map.
- Pedagogical goal: learners see readable source names (not opaque abbreviations) while retaining raw strings.

## Next Steps (achievable)
1) Frontend exposure (@coder/@scribe)
   - Surface `citation_details` in rendered dictionary views (API/CLI/UI) so display/long_name are visible without digging in metadata.
   - Keep raw ids alongside displays to avoid lossy transformations.
2) Coverage audit (@auditor)
   - Spot-check high-volume Sanskrit entries (MW/Apte/Boehtlingk-Roth) to confirm ABBR matches; add any missing source-like labels to `abbr_data.json`.
   - Ensure grammar-only ABBRs stay tagged as `kind: "grammar"` and are not over-expanded in source contexts.
3) Pipeline consistency (@coder)
   - Apply the same ABBR map to any other Heritage outputs that emit references (combined/reader paths) before serialization.
4) Verification (@sleuth)
   - After changes, run `just cli query san agni`, `agnii`, `veda` (post `just restart-server`) to confirm displays + raw refs.
   - Optionally extend fuzz fixtures to assert `citation_details` presence for a Sanskrit term.

## Notes
- `src/langnet/heritage/abbr_data.json` is the single source; regenerate from ABBR.md if upstream changes.
- CTS DB remains Perseus-only; ABBR mapping is the near-term solution for Sanskrit sources.
