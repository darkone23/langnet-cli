# Local Lexicon Witness Handoff

**Status:** active stabilization handoff  
**Date:** 2026-04-27  
**Feature Area:** infra / dico / semantic-reduction

## What Changed

LangNet now treats local French dictionary sources as evidence-bearing lookup witnesses:

- Latin Gaffiot entries flow through `fetch.gaffiot → extract.gaffiot.json → derive.gaffiot.entries → claim.gaffiot.entries`.
- Sanskrit DICO entries flow through `fetch.dico → extract.dico.json → derive.dico.entries → claim.dico.entries`.
- `triples-dump` can filter output with `--predicate`, `--subject-prefix`, and `--max-triples`, and can emit structured JSON with `--output json`.
- DICO lookup expands IAST/Sanskrit input into Heritage/Velthuis-style candidates, so entries such as `kṛṣṇa` can resolve to DICO key `k.r.s.na`.
- Gaffiot lookup accepts multiple candidate forms from the planner, so a surface form and lemma can both be tried.
- Planner call-construction helpers now live outside `planner/core.py` in `planner/calls.py` and `planner/local_lexicons.py`.
- `triples-dump` display helpers now live outside `cli.py` in `cli_triples.py`.
- Offline `databuild` Click commands now live outside `cli.py` in `cli_databuild.py`.
- DICO/Gaffiot local fetch clients now use content-addressed raw response IDs.
- Translation-cache schema/key helpers exist, and cache-hit projection can add derived English evidence for `encounter` when `--use-translation-cache` is provided.

Gaffiot/DICO still emit original French source evidence by default. Cached English translations are derived evidence and must remain distinguishable from the source French.

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
- structured claim/triple inspection visible with `triples-dump --output json`

## Known Limits

- Gaffiot may resolve a surface-form entry before a lemma entry when both exist. This is correct source evidence, but the future semantic reducer will need a clear policy for lemma-preferred vs surface-specific witnesses.
- DICO staged lookup is planned from Sanskrit candidate forms. Heritage dictionary URL fallback still exists for exact anchor cases.
- CDSL output is better at showing IAST display forms, but the underlying source strings are still flat and can mix grammar, citations, abbreviations, compounds, and gloss text.
- `cli.py` and `planner/core.py` are smaller but still large; continue extracting cohesive command/planner areas as behavior stabilizes.
- Translation cache population remains explicit and network-backed; normal lookup should use resolved cache hits where possible and should not call the translation provider implicitly.

## Recommended Next Steps

1. Strengthen CDSL source/gloss/source-note separation while preserving raw encoded source forms.
2. Add evidence-inspection examples that trace `encounter` meanings through `triples-dump --output json`.
3. Expand no-network DICO/Gaffiot translation cache examples beyond the first golden rows.
4. Decide the lemma-vs-surface policy for local lexicon witnesses.
5. Keep broader semantic grouping behind exact-bucket tests and accepted-output examples.

## Junior-Friendly Work

- Add CDSL source-structure fixtures for `dharma`, `agni`, and one citation-heavy entry.
- Add fixture tests for deterministic DICO/Gaffiot source text hashes.
- Add docs examples for `triples-dump --output json --predicate gloss --max-triples 1`.
