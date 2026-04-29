# CDSL Entry Grammar And Sanskrit Source Structure

**Status:** ACTIVE  
**Date:** 2026-04-28  
**Feature Area:** skt  
**Owner Roles:** @architect for source model, @coder for parser/tests, @sleuth for real-entry fuzzing, @auditor for Sanskrit grammar correctness

## Purpose

Improve Sanskrit dictionary evidence from CDSL by separating learner glosses,
source notes, Sanskrit forms, grammatical features, citations, and cross
references while preserving the raw source text.

CDSL is one of the most important Sanskrit meaning sources. The project should
not treat long CDSL lines as a single opaque English gloss when a reader is
asking, "what does this word mean?"

## Current Slice

Implemented:

- CDSL claims preserve raw gloss, display gloss, source ref, and source entry
  metadata.
- Source segments are split conservatively on semicolons.
- Recognized citation-only and cross-reference-only segments are typed without
  dropping unclassified text.
- SLP1/IAST display conversion is covered by tests.
- Sanskrit case extraction now uses standard case numbering:
  `1 nominative`, `2 accusative`, `3 instrumental`, `4 dative`, `5 ablative`,
  `6 genitive`, `7 locative`, `8 vocative`.
- Compound `info lex="m:f#n"` gender sets are parsed into ordered gender lists.
- CDSL source-entry metadata now carries `page_ref` when the built index
  provides it.
- Explicit body XML structure now captures `ab` abbreviations, compound hints,
  declension markers from `info lex`, root/etymology markers, `ls` lexicon
  references, and `s1` cross references in grammar metadata.

Captured from `codesketch/src/langnet/cologne/` and `codesketch/tests/test_cdsl.py`:

- Key/key2 preservation matters.
- `lex`, `info`, and body text can contain useful grammatical metadata.
- `ls` and `s1` tags should become source references or cross references.
- Etymology/root markers should be captured when they are explicit.
- Page references should remain visible as source-entry evidence.

## Parser Direction

Use structured XML parsing first, then Lark grammars for ambiguous body strings.
The goal is not to fully parse every historical dictionary convention. The goal
is to classify enough structure to improve learner display and evidence
navigation:

- `gloss`: readable meaning text;
- `grammar`: POS, gender, case, number, Sanskrit form, derivational notes;
- `citation`: source abbreviation and locator;
- `cross_reference`: see/cf. references to other headwords;
- `example`: explicit quoted or example material where detectable;
- `unclassified`: preserved source text that should not be silently discarded.

## Next Steps

1. Add a CDSL source-entry fuzz fixture set.
   - Include `key1`, `key2`, `lex`, `info`, `s`, `ls`, `s1`, root markers,
     page refs, and source abbreviations.
   - Include common Sanskrit terms: `agni`, `dharma`, `karman`, `ātman`,
     `brahman`, `soma`.
   - Status: representative synthetic coverage exists in
     `tests/test_cdsl_triples.py`; the remaining work is real-entry fuzz
     expansion.

2. Introduce a small CDSL body grammar.
   - Keep it tolerant and classifier-oriented.
   - Use Lark for body fragments after XML tags have been converted into
     structured tokens.

3. Add learner-display snapshots.
   - Ensure long CDSL lines do not flood the first few encounter buckets with
     citation-only material.
   - Ensure raw source text remains inspectable.

4. Extend real-input fuzzing.
   - Use corpus Sanskrit examples from Taittiriya material and common Vedic
     terms.
   - Track retrieval hit, meaningful gloss hit, and grammatical feature hit
     separately.

## Acceptance

```bash
just test tests.test_cdsl_triples tests.test_source_text_analysis
LANGNET_DATA_DIR=examples/debug/validation-data just validate-stabilization
```

The feature is ready when CDSL improves Sanskrit learner display without hiding
citations, source abbreviations, or raw dictionary text.
