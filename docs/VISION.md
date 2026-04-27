# LangNet Vision

LangNet exists to help a reader move from a word in a classical text to an accountable explanation of what that word can mean, what form it is, and which sources support that answer.

The project is not trying to replace dictionaries, grammars, or scholarly judgement. It is building a transparent learning layer over them: a local tool that gathers evidence from trusted sources, preserves provenance, and turns scattered backend output into explanations that students and scholars can inspect.

## Product Promise

For a Latin, Greek, or Sanskrit word, LangNet should answer five questions:

1. What headword or lexeme might this form belong to?
2. What grammatical form or forms can it be?
3. What meanings are supported by dictionary or analyzer evidence?
4. Where did each claim come from?
5. Where do sources agree, disagree, or remain incomplete?

The answer should be useful first and auditable second. A beginner should see a clear reading path; an advanced user should be able to drill down into claims, triples, raw source references, and cache provenance.

## Who It Serves

- Students reading classical texts who need help connecting forms to meanings.
- Teachers preparing concise lexical and grammatical explanations.
- Researchers checking source evidence across tools quickly.
- Developers building structured classical-language datasets.

## Strategic Bet

The core bet is that word-level evidence must become reliable before LangNet can responsibly support broader interpretation.

That means the project should stabilize in this order:

1. Local lookup and normalization.
2. Tool planning and staged execution.
3. Evidence-backed claims and triples.
4. Witness Sense Units extracted from claims.
5. Deterministic sense buckets.
6. Learner-facing semantic output.
7. Optional hydration, compounds, and passage-level support.

This order protects the educational experience. It prevents fluent-looking output from outrunning the sources that justify it.

## Product Principles

### Evidence Before Fluency

Every displayed lexical, morphological, or semantic fact should trace back to a tool response, dictionary entry, citation, or explicit derivation. Generated prose is acceptable only when the underlying evidence remains visible.

### Clarity Before Completeness

Learner-facing output should lead with the most helpful explanation, not every internal detail. Detailed provenance remains available through inspection commands.

### Determinism Before Inference

Stable rules, repeatable IDs, fixture-backed tests, and exact reductions come before embeddings, fuzzy matching, or broad language-model interpretation.

### Tradition With Function

LangNet should preserve traditional grammatical terms while explaining what they do in context. A learner can keep the word "dative" while also seeing its common "to/for" function.

### Local First

The reliable product surface is the local CLI. External services can be required for live lookup, but fixture-backed behavior and evidence inspection should not depend on network access.

## Current North Star

Build a reliable word-level evidence engine first. Then reduce that evidence into grouped meanings that make classical texts easier to read without hiding the sources.

