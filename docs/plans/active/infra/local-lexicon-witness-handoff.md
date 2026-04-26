# Local Lexicon Witness Handoff

**Status:** active stabilization handoff  
**Date:** 2026-04-26  
**Feature Area:** infra / dico / semantic-reduction

## What Changed

LangNet now treats local French dictionary sources as evidence-bearing lookup witnesses:

- Latin Gaffiot entries flow through `fetch.gaffiot → extract.gaffiot.json → derive.gaffiot.entries → claim.gaffiot.entries`.
- Sanskrit DICO entries flow through `fetch.dico → extract.dico.json → derive.dico.entries → claim.dico.entries`.
- `triples-dump` can filter output with `--predicate`, `--subject-prefix`, and `--max-triples`.
- DICO lookup expands IAST/Sanskrit input into Heritage/Velthuis-style candidates, so entries such as `kṛṣṇa` can resolve to DICO key `k.r.s.na`.
- Gaffiot lookup accepts multiple candidate forms from the planner, so a surface form and lemma can both be tried.
- Planner call-construction helpers now live outside `planner/core.py` in `planner/calls.py` and `planner/local_lexicons.py`.
- `triples-dump` display helpers now live outside `cli.py` in `cli_triples.py`.
- Offline `databuild` Click commands now live outside `cli.py` in `cli_databuild.py`.
- DICO/Gaffiot local fetch clients now use content-addressed raw response IDs.

These changes intentionally stop before translation. Gaffiot/DICO currently emit original French source evidence only.

## Current Validation

Run before handoff:

```bash
just lint-all
just test-fast
devenv shell -- bash -c 'langnet-cli triples-dump lat lupi gaffiot --no-cache --predicate gloss --max-triples 1'
devenv shell -- bash -c 'langnet-cli triples-dump san kṛṣṇa dico --no-cache --predicate gloss --max-triples 1'
just cli-databuild --help
```

Expected state:

- lint/typecheck clean
- nose2 suite passing
- filtered Gaffiot/DICO source French glosses visible in `triples-dump`

## Known Limits

- Gaffiot may resolve a surface-form entry before a lemma entry when both exist. This is correct source evidence, but the future semantic reducer will need a clear policy for lemma-preferred vs surface-specific witnesses.
- DICO staged lookup is planned from Sanskrit candidate forms. Heritage dictionary URL fallback still exists for exact anchor cases.
- CDSL output can leak Sanskrit Lexicon encodings such as SLP1 into learner-visible triples.
- `triples-dump` filtering is text output only. JSON inspection is still missing.
- `cli.py` and `planner/core.py` are smaller but still large; continue extracting cohesive command/planner areas as behavior stabilizes.
- Translation cache is not implemented. French source evidence must remain distinct from future English translation evidence.

## Recommended Next Steps

1. Add CDSL IAST display fields while preserving raw encoded source forms.
2. Add `triples-dump --output json` or a small structured inspection command.
3. Add a WSU extractor over `has_sense + gloss + evidence`.
4. Add translation cache schema/key helpers for Gaffiot-first French → English.
5. Decide the lemma-vs-surface policy for local lexicon witnesses.

## Junior-Friendly Work

- Add CDSL transliteration fixtures for `Darma → dharma`, `agni → agni`, and one retroflex/vowel-heavy form.
- Add docs examples for `triples-dump --predicate gloss --max-triples 1`.
- Add fixture tests for deterministic DICO/Gaffiot source text hashes.
- Add a small fixture describing a French source gloss and its future translated English gloss with separate evidence IDs.
