# Foster Display Vocabulary

**Status:** ACTIVE  
**Date:** 2026-04-28  
**Feature Area:** pedagogy  
**Owner Roles:** @architect for display contract, @coder for implementation, @auditor for grammar-label correctness

## Purpose

Provide optional Foster-style functional labels for morphology without replacing
the exact grammatical facts carried by source claims. The learner should be able
to see both:

- exact grammar: `accusative`, `dual`, `neuter`;
- optional functional labels: `RECEIVING`, `PAIR`, `NEUTER`.

## Current Slice

Implemented:

- `src/langnet/pedagogy/foster.py`
- `tests/test_foster_pedagogy.py`

Captured from `codesketch/src/langnet/foster/`:

- Latin case, tense, gender, number, voice, mood, and participle labels.
- Greek case, tense, gender, number, voice, mood, and participle labels.
- Sanskrit case, gender, and number labels.

Intentional correction:

- Sanskrit case numbering now follows the standard order:
  `1 nominative`, `2 accusative`, `3 instrumental`, `4 dative`,
  `5 ablative`, `6 genitive`, `7 locative`, `8 vocative`.
- The old sketch mapped Sanskrit `2` to `CALLING`; the maintained module maps
  it to `RECEIVING` and maps `8` to `CALLING`.

## Next Steps

1. Decide where Foster labels belong in runtime output.
   - Preferred: metadata on morphology feature objects and/or terminal
     rendering, not new semantic predicates.
   - Exact grammatical triples must remain unchanged.

2. Add display rendering.
   - Full labels: `Naming Function`, `Receiving Function`, etc.
   - Short labels: stable abbreviations where they help compact terminal
     output.
   - Keep rendering as presentation logic, separate from claim extraction.

3. Wire into learner encounter output behind an explicit option.
   - Suggested CLI option: `--foster-labels`.
   - Default output should remain exact grammatical labels until the display is
     reviewed with real examples.

4. Add real-output snapshots.
   - Latin: one Whitaker/Diogenes noun and one verb.
   - Greek: one Diogenes noun and one finite verb/participle.
   - Sanskrit: one Heritage nominal analysis and one CDSL body-derived feature.

## Acceptance

```bash
just test tests.test_foster_pedagogy tests.test_cli_encounter_output
just lint-all
```

The feature is complete when Foster labels are available in learner display
without reducing evidence fidelity or hiding source grammar.
