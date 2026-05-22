# Foster Ossa Core Function Bridge

This document records the first conservative mappings from generated Foster
Ossa terms into the existing LangNet grammar concept registry.

The mappings are generated from validated summary artifacts and source refs,
but they are still a review surface. The stable registry remains
`src/langnet/learning/grammar_concepts.py`.

The machine-readable starter pack built from these mappings lives at
`data/build/foster_essentials.json`, with a readable view in
[`FOSTER_ESSENTIALS.md`](FOSTER_ESSENTIALS.md).

## Promoted Matches

| Foster/Ossa summary term | LangNet concept | Rationale |
| --- | --- | --- |
| `function of-possession`, `of-possession`, related variants | `case.genitive` | The registry already has `case.genitive` with the Foster-facing gateway `Possessing Function`; the summaries repeatedly use the `of-possession` label for this function. |
| `function to-for-from`, `form to-for-from`, related variants | `case.dative` | The registry already has `case.dative` with the Foster-facing gateway `To-For Function`; the summaries use the longer Foster phrase for this function. |
| `object form`, `object forms` | `case.accusative` | In these Foster/Ossa summaries, object form is the learner-facing gateway for the receiving/object case function. |
| `function of address` | `case.vocative` | The registry already defines vocative as direct address, and the summaries use the address function in the same role. |
| `location function` | `case.locative` | The registry already carries a location-oriented case concept with the Foster-facing gateway `In-At Function`. |
| `subject form`, `subject forms` | `case.nominative` | The summaries use subject form for the naming/subject case function; this is mapped only for the phrase with `form`, not for bare `subject`. |

## Deliberately Unpromoted

`by-with-from-in` remains a direct source candidate rather than an automatic
match. It overlaps with multiple existing concepts: `case.ablative`,
`case.instrumental`, and `case.locative`. Treating it as only one of those
would erase a Foster/Ossa bundle that is pedagogically important.

## Current Audit Result

After adding the conservative bridge aliases, the audit reports:

- Total candidates: 862
- Existing concepts: 34
- Direct source candidates: 727
- Method-supported candidates: 67
- Platform overlay candidates: 34

The generated review queue is
[`TAXONOMY_AUDIT.md`](TAXONOMY_AUDIT.md), with full machine-readable output at
`examples/debug/foster-ossa-taxonomy-audit.json`.

## Next Review Targets

- Decide whether `by-with-from-in` should become a Foster-specific aggregate
  concept that links to ablative, instrumental, and locative.
- Review high-frequency direct candidates such as sequence of tenses,
  subjunctive, indirect question, ablative absolute, relative pronoun, and
  reflexive pronoun.
- Add product examples only after each promoted concept has reader examples,
  dictionary evidence, morphology predicates, and Foster/Ossa source refs.
