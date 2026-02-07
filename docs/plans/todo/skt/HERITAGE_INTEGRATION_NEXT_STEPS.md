# Sanskrit Heritage Integration – Next Steps

## Objective
- Fold insights from `docs/upstream-docs/skt-heritage/` (ABBR list, manual) into our Sanskrit pipeline so Heritage outputs are more pedagogical and normalized.

## Source Notes
- `ABBR.md`: rich French grammar/pos abbreviations (e.g., *acc.*, *bén.*, *dés.*, *c.-à-d.*) that can be mapped to English equivalents and/or Foster functions.
- `manual.txt`: highlights segmentation UI, sandhi handling, conjugation/declension generators, homonym disambiguation, and corpus tools; emphasizes IAST/Devanagari/ASCII inputs and sandhi-aware parsing.

## Next Steps (@coder / @scribe)
- **Abbreviation normalization**
  - Parse `docs/upstream-docs/skt-heritage/ABBR.md` to build a mapping table; expose in Heritage adapter metadata so dictionary entries carry human-readable tags (English + original).
  - Where abbreviations imply morphology (e.g., *acc.*, *fut.*, *dés.*), map to Foster codes; keep raw abbreviations for audit.
- **Heritage morphology/dictionary enrichment**
  - Surface homonym indices and class (gaṇa) info in adapter metadata to mirror the manual’s conjugation/declension links.
  - Add sandhi-aware hints (e.g., avagraha, mandatory pauses) to warnings/metadata for learner clarity.
  - Ensure `canonical_form` and transliterations are attached to every Heritage dictionary/morph entry; prefer IAST + Devanagari.
- **Segmentation and examples**
  - Add example payloads (sentence parsing, compound segmentation) showing how we present ambiguous analyses; align with manual’s “First/All/Best” notions in docs.
  - Capture best-practice guidance for user input (IAST vs Devanagari vs ASCII) and sandhi spacing in `docs/PEDAGOGICAL_PHILOSOPHY.md` or a Sanskrit-focused appendix.
- **Testing/validation**
  - Add targeted fixtures for abbrev → Foster/English mapping and for Heritage homonym/class metadata.
  - Fuzz spot-check Sanskrit queries that stress sandhi/compound parsing (e.g., `yogena`, `prāptavyamarthaṃ`, `pravaranrpamukuṭamaṇimarīcimañjarīcayacarcitacaraṇayugalaḥ` with and without hyphens/avagraha).

## Deliverables
- Abbreviation → English (+ Foster where possible) mapping wired into Heritage adapter output.
- Canonical/transliteration consistently present on Heritage entries; homonym/gaṇa metadata surfaced.
- Docs updated with input guidance and example payloads that reflect sandhi-aware parsing and ambiguity handling.

## Risks / Mitigations
- Ambiguous abbrev meanings → keep raw abbrev alongside normalized tags; log unmapped cases.
- Over-aggressive mapping → gate Foster derivations behind confident matches; fall back to raw tags.
- Sandhi/display regressions → cover with fixtures for avagraha, hyphenated compounds, and mixed scripts.
