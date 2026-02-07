# Pedagogical Mapping Phase Alignment

## Objective
- Align the unified `/api/q` mapping phase with the pedagogical goals in `docs/PEDAGOGICAL_PHILOSOPHY.md`, ensuring backends emit learner-friendly data (functions over forms) without post-processing hacks.

## Personas & Phases
- @architect: finalize mapping rules and schema targets.
- @coder: implement backend adapter changes and canonical wiring.
- @auditor: sanity-check payloads against pedagogy and TODO items.

## Current Gaps (from fuzz sanity check + docs/TODO.md)
- Functional grammar mapping absent (cases/voice/tense/person not translated to Foster functions).
- Diogenes: senses sometimes broken; citations not normalized to CTS URNs; dictionary blocks not pedagogy-filtered.
- Heritage: canonical/lemmatize results not surfaced in unified entries; sktsearch not always applied; no DICO integration.
- CDSL: definitions often contain raw SLP1; transliteration not normalized; schema metadata noisy.
- Universal schema: grouping/hierarchy weak; citations minimal; canonical forms not consistently present.

## Status
- Lifecycle: Active (pedagogy).
- Stage: Mapping rules + adapter scoping.
- Owners: @architect (rules), @coder (adapters), @auditor (validation).

## Plan / Next Steps
1) **Mapping rules** (@architect)
   - Define Foster function mappings for case/number/person/tense/voice/mood across lat/grc/san (see draft below).
   - Decide canonical fields to carry per source (lemma, canonical_form, transliterations, roots).
   - Specify citation normalization (CTS URN targets; what stays in metadata vs surfaced).
2) **Adapter updates** (@coder)
   - Diogenes: clean sense extraction; map morphology tags → Foster functions; normalize citations to CTS URN where present.
   - Whitaker’s/CLTK: map morphology to functions; ensure Lewis & Short lines are tagged with POS where possible.
   - Heritage: surface canonical + lemmatize outputs in entries; preflight canonical (sktsearch) and feed that into morphology/dictionary lookups when available; keep raw_html out.
   - CDSL: apply transliteration cleanup for definitions where safe; attach roots/etymology; trim noisy metadata.
3) **Canonical consistency** (@coder)
   - Ensure all Sanskrit tools use canonical (sktsearch) forms for lookups (e.g., agni→agnii) before morphology/dictionary; carry canonical_form in metadata.
   - Normalize Greek betacode→Unicode and Latin macrons consistently before mapping.
4) **Validation pass** (@auditor/@coder)
   - Run `just fuzz-compare` and manually spot-check: lat lupus, grc logos, san agni/yogena (include morphology → function labels, canonical presence, citations).
   - Record examples of “good” pedagogical payloads for docs.
5) **Docs alignment** (@scribe)
   - Update `docs/PEDAGOGICAL_PHILOSOPHY.md` examples to mirror current outputs once mappings land.
   - Add a short “what learners see first” note to developer docs to keep mappings from regressing.

## Deliverables
- Updated adapters emitting Foster function fields (no downstream post-processor required).
- Canonical/lemmatize data surfaced in unified entries for Sanskrit; consistent canonical handling for lat/grc.
- Citation normalization + sample payloads demonstrating “see in the wild”.
- Fresh fuzz comparison artifacts showing sources present and mapped pedagogy-first fields.

## Risks & Mitigations
- Over-mapping noisy tags → keep raw metadata alongside functional labels for fallback.
- Citation loss → retain original refs in metadata while adding normalized CTS where possible.
- Transliteration corruption → restrict auto-clean to confidently detected SLP1 segments; log when skipped.

## Moving Forward / Handoff
- Finish CTS normalization for Diogenes:
  - Use local CTS URN mapping database (`src/langnet/citation/cts_urn.py` + index) to convert Perseus refs; keep `original_citations` alongside normalized.
  - Attach normalized citations to both dictionary blocks and morphology chunks; expose in unified entries.
- Canonical consistency:
  - Latin/Greek: apply betacode→Unicode (Greek) and macron-preserving canonical forms; surface `canonical_form` at adapter level.
  - Sanskrit: ensure `canonical_form` from sktsearch is propagated through aggregated entries (dictionary + morphology).
- Foster exposure in dictionaries:
  - Whitaker/CLTK: tag dictionary senses/lines with POS and foster_codes where derivable (from codeline or features).
  - Diogenes dictionary blocks: add POS/foster where recoverable from morphology tags in the same chunk.
- Universal schema/aggregation:
  - Group entries by canonical_form + lemma; ensure foster_codes are available on morphology and as metadata for dictionary-only entries.
  - Document expected output shape for `/api/q` (pedagogy-first ordering, foster + canonical + citations).
- Validation docs:
  - Capture “good” examples (lat lupus, grc logos, san agni/yogena) with foster codes, canonical forms, and CTS citations for `docs/PEDAGOGICAL_PHILOSOPHY.md`.
## Draft Mapping Rules (@architect)
- Case/number/gender
  - Latin (diogenes/whitaker): nom/voc/acc/gen/dat/abl/loc → NAMING/CALLING/RECEIVING/POSSESSING/TO_FOR/BY_WITH_FROM_IN/IN_WHERE; sg/pl/du → SINGLE/GROUP/PAIR; m/f/n → MALE/FEMALE/NEUTER.
  - Greek (diogenes/cltk): nom/voc/acc/gen/dat → NAMING/CALLING/RECEIVING/POSSESSING/TO_FOR; sg/pl/du → SINGLE/GROUP/PAIR; m/f/n → MALE/FEMALE/NEUTER.
  - Sanskrit (heritage/cdsl): case 1-8 → NAMING/CALLING/RECEIVING/POSSESSING/TO_FOR/BY_WITH_FROM_IN/IN_WHERE/OH; sg/du/pl → SINGLE/PAIR/GROUP; m/f/n → MALE/FEMALE/NEUTER.
- Tense/aspect
  - Latin: pres/imperf/perf/plupf/fut/futperf → TIME_NOW/TIME_WAS_DOING/TIME_PAST/TIME_HAD_DONE/TIME_LATER/ONCE_DONE.
  - Greek: pres/imperf/aor/perf/plupf/fut → TIME_NOW/TIME_WAS_DOING/TIME_PAST/TIME_HAD_DONE/ONCE_DONE/TIME_LATER.
- Voice/mood/misc
  - Voice: act → DOING; pass → BEING_DONE_TO; mid/depon/semi_depon → FOR_SELF.
  - Mood: indic → STATEMENT; subj → WISH_MAY_BE; opt → MAYBE_WILL_DO; imper → COMMAND.
  - Participle: part → PARTICIPLE (preserve alongside finite mood/voice when present).
- Output conventions
  - Attach `foster_codes` as enum values (not display strings) alongside raw tags.
  - Keep raw tags/metadata for auditability; avoid lossy replacements.
  - Surface per-morph (diogenes), per-entry (dictionary grammar_tags), and CLTK greek morphology consistently.

## Canonical & Citation Carriage (@architect)
- Canonical fields to keep per source: `lemma`, `canonical_form` (normalized headword), `transliterations` (iast/slp1/dev/latin as available), `root`/`etymology`, `normalized_query`, `pos`.
- Sanskrit: run `sktsearch` upfront; feed canonical_form into morphology + dictionary; include heritage lemmatize/canonical outputs in unified entries.
- Latin/Greek: preserve macrons/breathing in canonical_form; normalize betacode→Unicode before mapping; carry original orthography in `original_form`.
- Citations: prefer normalized `cts_urn` plus `citation_display`; keep original citation string in `metadata.original_citation` for lossless trace; ensure Diogenes dictionary/morph chunks inherit normalized citations where available.

## Adapter Touchpoints (@coder)
- Diogenes: normalize citations; ensure `morphology.morphs[].foster_codes` populated; clean sense extraction; mark dictionary blocks with POS and foster tags where derivable.
- Whitaker’s/CLTK: add foster mappings to morphology outputs; ensure Lewis & Short lines carry POS and foster tags; avoid stripping macrons.
- Heritage/CDSL: attach `canonical_form`, `root`, `transliterations`, `foster_codes` (from grammar_tags) to entries; strip raw_html; add DICO hook when available.
- Aggregator/universal schema: group entries with canonical_form + lemma; expose citations and foster_codes in top-level mapped payload.

## Validation Checklist (@auditor)
- Run `just fuzz-compare` and manual spot checks: `lat lupus`, `grc logos`, `san agni`, `san yogena`; confirm foster_codes present and aligned with functions and canonical forms.
- Verify citation normalization (CTS URN present + readable display) in Diogenes outputs.
- Ensure dictionary entries keep raw tags while exposing foster_codes; no raw HTML leakage from Heritage/CDSL.
