# Dictionary Foster & Abbreviation Exposure – Next Steps

## Objective
- Surface foster codes and readable citations in dictionary content so `/api/q` shows pedagogy-first data even when morphology is absent.

## Current State
- Foster: mapped for morphology across backends; Whitaker senses do **not** carry foster; Diogenes dictionary blocks untagged for POS/foster; CLTK dictionary lines are POS-tagged heuristically but lack foster.
- Citations: Diogenes CTS URNs normalized with author/work/display; non-Perseus abbreviations (e.g., L., Suśr., LSJ, MW) pass through raw.
- Abbreviations: No shared table; Sanskrit Heritage ABBR.md reviewed but not wired.

## Next Steps (achievable)
1) **Whitaker senses → foster** (@coder)
   - When `foster_codes` exist on morphology/first-term, copy into each sense metadata (already partial), and add a top-level `foster_codes` in entry metadata for dictionary-only cases.
2) **Diogenes dictionary POS/foster** (@coder)
   - Derive POS from headings/entry text heuristics (noun/verb/adj/etc.) for dictionary blocks.
   - When a morphology chunk exists in the same parse, propagate its foster_codes into adjacent dictionary blocks’ metadata.
3) **CLTK dictionary foster/POS** (@coder)
   - Use inferred POS to attach default foster where possible (e.g., none unless features exist). Keep metadata key for future expansion.
4) **Abbreviation expansion** (@scribe/@coder)
   - Build a small mapping for common dictionary abbreviations (LSJ, OLD, L&S, DGE, LfgrE, MW, Apte, Böhtlingk-Roth, Suśr., Uṇ., ĀpŚr., Kātantra, L., Gārhapatya, Āhavanīya, Dakṣiṇa).
   - Apply to non-CTS citations across dictionary sources: add `display` and `long_name` in citation_details while preserving originals.
   - Source Sanskrit labels from `docs/upstream-docs/skt-heritage/ABBR.md` where they name sources (skip pure grammar tags for now).
5) **Aggregation pass** (@coder)
   - Ensure entry metadata bubbles up foster_codes when dictionary-only and exposes citation_details/display for all citations (URN or not).

## Verification
- Manual queries after restart: `just cli query lat lupus`, `grc logos`, `san agni` → confirm dictionary senses show POS and foster metadata, and every citation has a readable display.
- Fuzz: `just fuzz-compare` to guard regressions.

## Risks / Mitigations
- Heuristic POS mis-tags → keep original text in metadata; avoid destructive overwrites.
- Abbrev mis-expansion → use allowlist; keep raw id/text in citation_details.
- Foster overreach → only attach when derived from morphology or clear tags; otherwise leave absent.
