# Learn CLI Audit

This audit covers the local CLI-first didactic surfaces that currently feed
the grammar learning overlay:

- `learn concepts`
- `learn concept`
- `learn map`
- `learn evidence-report`
- `learn doctor`
- `learn foster-bridge`
- `encounter --include-learning`
- Foster/Ossa reference commands under `foster-ossa`

## Current State

The CLI surface is coherent enough to use as the contract before web UI wiring.
The core `learn` commands now expose the same didactic model from multiple
entry points:

- concept-first: `learn concept case.genitive --output json`
- compact concept list: `learn concepts --kind case --view compact --output json`
- feature-first: `learn map --pos noun --feature case=genitive --view compact --output json`
- Foster-first: `learn foster-bridge of-possession --view compact --output json`
- readiness-first: `learn doctor --output json`
- encounter-first: `encounter san putraa.naam heritage --include-learning --output json`

The current output gives downstream clients:

- stable concept IDs;
- Foster gateway labels;
- traditional Greek, Latin, and Sanskrit terms;
- native gateway rows that explain how those terms map to the Foster learner
  gateway;
- source-basis strings;
- structured grammar-source evidence;
- reviewed Foster/Ossa bridge records;
- Foster essentials learner actions, product-use notes, source refs, summary
  refs, and morphology predicates;
- compact projections for UI planning;
- didactic readiness checks from `learn doctor`;
- diagnostics for unmapped or ignored feature facts;
- evidence gaps when a concept lacks exact reader-segment grounding.
- ambiguity markers such as `ambiguous-analysis` when source morphology exposes
  multiple concrete readings for the same observed form.

## Verified Commands

Representative smoke checks:

```bash
just cli learn --help
just cli learn concepts --kind case --output json
just cli learn concepts --kind case --view compact --output json
just cli learn concept case.genitive --output json
just cli learn map --pos noun --paradigm-kind declension --feature case=genitive --view compact --output json
just cli learn map --pos noun --paradigm-kind declension --feature case=ablative --output json
just cli learn evidence-report --output json
just cli learn doctor --output json
just cli learn foster-bridge --status promoted_match --output json
just cli learn foster-bridge of-possession --view compact --output json
just cli learn foster-bridge by-with-from-in
just cli foster-ossa --help
just cli encounter --help
```

## Findings

### Strong

- `learn` is now the right umbrella for local didactic exploration.
- The Foster/Ossa bridge is bidirectional:
  - Foster term to concept via `learn foster-bridge`;
  - concept to Foster term via `learn concept` and `learn map`;
  - encounter candidate to Foster term via `encounter --include-learning`.
- `learn foster-bridge` is backed by
  `docs/reference/foster-ossa/FOSTER_ESSENTIALS.md`, so page refs, learner
  actions, product-use notes, and morphology predicates share the same source of
  truth as the Foster/Ossa essentials commands.
- `by-with-from-in` is correctly preserved as an aggregate candidate linked to
  ablative, instrumental, and locative rather than flattened into a single case.
- `learn evidence-report` gives a compact stabilization gate:
  25 exposed concepts, 24 with reader-segment evidence, and
  `process.declension` as the known remaining passage-level gap.
- `learn doctor` now gives a single didactic readiness gate. The expected state
  is `ok: true` with warnings for the known `process.declension` segment gap and
  Foster refs that are actionable but not yet embedded snippets.
- `--view compact` is available for concepts, concept detail, map, and bridge
  payloads, giving the web/server layer a smaller projection to consume.
- Help output exists for the didactic commands and is now covered by tests.
- Heritage alternates are preserved as separate candidates. For example, `deva`
  can expose masculine and neuter vocative singular readings instead of
  collapsing to the last parsed gender.

### Weak

- Pretty output is useful for inspection but still not a polished teaching UI.
- Full JSON remains intentionally verbose because it returns source evidence
  arrays for audit/debug workflows.
- `learn foster-bridge` entries contain Foster/Ossa `page:*` references and
  reader example queries, but do not yet resolve those references into embedded
  local page snippets.
- `encounter --include-learning` depends on a candidate carrying concept IDs;
  if morphology projection misses a feature, the overlay cannot repair it.
- Dictionary-entry semantic grammar facts do not yet challenge morphology
  candidates. `sambuddhi` is the current representative case: dictionary
  entries describe vocative/address grammar, while Heritage morphology can still
  produce nominal neuter readings.
- `process.declension` still lacks a verified reader-segment source.

## Hardening Tasks

- Resolve Foster/Ossa `page:*` and `toc:*` source actions into inspectable
  snippets once the web/server layer has a source-reference endpoint.
- Add source-backed example fixtures for the six promoted Foster bridges and the
  `by-with-from-in` aggregate candidate.
- Find or reject a precise reader segment for `process.declension`.
- Add dictionary-entry grammar fact extraction/reranking for source entries
  that explicitly say `vocative`, `genitive`, `declension`, `feminine`, and
  similar grammar facts.
- Expand the bridge registry cautiously into high-value candidates:
  sequence of tenses, subjunctive, indirect question, ablative absolute,
  relative pronoun, reflexive pronoun, deponent verbs, and indirect discourse.

## Web Readiness

The current CLI contract is ready to inform the web UI shape, but not to serve
as final copy. The web should consume the same concept IDs and bridge IDs while
keeping source evidence and bridge status visible. In particular, aggregate
candidates should display as related Foster bundles, not as promoted grammar
facts.
