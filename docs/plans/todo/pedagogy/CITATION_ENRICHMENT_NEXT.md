# Citation Enrichment – Next Steps

## Objective
- Expand citation friendliness beyond raw CTS IDs by attaching human-readable author/work names everywhere we can, and make non-Perseus dictionary citations less opaque.

## Current State
- Diogenes blocks: CTS URNs normalized; author/work pulled from the CTS DuckDB (Perseus-derived). Raw IDs preserved.
- Heritage/CDSL/Whitaker/CLTK: no citation normalization; some entries carry abbreviations or free-text references only.
- CTS index content: Perseus coverage only (latinLit/greekLit). No bespoke mappings for lexicon abbreviations or non-Perseus references.

## Gaps
- Non-Perseus refs (e.g., “LSJ s.v.”, “GEL”, “LS”, “Lid.”, Sanskrit lexica abbreviations) lack display names.
- Diogenes citation_details stop at author/work for URNs; no backfill for URN-less refs.
- No shared abbreviation table to explain dictionary-side citations (Latin/Greek lexica, Sanskrit sources).
- Verification is manual; no targeted fixtures covering citation displays.

## Next Steps (achievable)
1) **Fallback displays for URN-less citations** (@coder)
   - When a citation_id is not a CTS URN, set `display` = `citation_text` and include `kind: "unknown"` in citation_details.
   - Ensure aggregation surfaces these displays without dropping originals.
2) **Abbreviation table** (@scribe/@coder)
   - Build a small static mapping for common lexicon abbreviations we see (LSJ, OLD, Lewis & Short, LfgrE, DGE, MW, Monier-Williams, Apte, Böhtlingk-Roth).
   - For Sanskrit, pull useful labels from `docs/upstream-docs/skt-heritage/ABBR.md` where they correspond to sources (not just grammar tags).
   - Attach `long_name` and `source` in `citation_details` for non-URN ids when matched.
3) **CTS DB enrichment pathway** (@infra)
   - Extend CTS DuckDB to store `author_name`/`work_title` for any future non-Perseus rows (e.g., dictionary abbreviations). Provide importer hook to add custom rows (namespace `lexicon`).
   - Add a config flag so Diogenes adapter can optionally look in a supplemental mapping JSON before falling back to raw text.
4) **Verification**
   - Add focused fuzz fixtures (or manual spot checks) that assert `citation_details.display` exists for: latin `lupus`, greek `logos`, sanskrit `agni`, and a case with unknown abbrev (should echo raw text).
   - Manual sanity after restart: `just cli query lat lupus --output json` and `grc logos` to confirm displays survive aggregation.
5) **Documentation**
   - Document the abbreviation mapping and fallback rules in `docs/PEDAGOGICAL_PHILOSOPHY.md` or a short appendix; note that CTS enrichment is Perseus-scoped today.

## Risks / Mitigations
- Mis-expansion of abbreviations → keep originals in metadata; gate mapping to a curated allowlist.
- Missing CTS data → preserve raw citation_id/text so displays never disappear.
- Drift between languages → keep mapping tables language-tagged and versioned.

## Definition of Done
- All dictionary entries surface a `display` for every citation (URN or not).
- Known abbreviations expand to human-readable names; unknowns remain intact.
- Spot-check queries show author/work for URNs and readable labels for non-URN refs.
