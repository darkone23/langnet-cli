# Foster Ossa Didactic Synthesis

This document is a human review surface derived from validated generated
artifacts:

- `examples/debug/foster-ossa-toc-all-summaries-v2.jsonl`
- `examples/debug/foster-ossa-experience-summaries-v2.jsonl`
- `docs/reference/foster-ossa/generated/`

The generated artifacts are secondary aids. The source-backed anchors remain the
local page rows, TOC entries, and `toc:*` / `page:*` references carried by each
summary row.

## Didactic North Pole

LangNet should teach classical-language reading by joining three things:

- source-backed form evidence from dictionaries and morphology analyzers;
- Foster-style functional reading labels that explain what a form is doing;
- conventional grammatical terminology that lets students continue into native
  grammars, commentaries, and reference works.

The platform should not replace traditional grammar with Foster terminology.
It should use Foster terminology as a gateway into exact predicates such as
case, number, gender, tense, voice, mood, person, and syntactic role.

## Method Implications

The validated summaries repeatedly point to several platform principles:

- Treat endings and function as primary reading evidence.
- Keep traditional terms visible, but pair them with functional labels.
- Prefer dictionary-centered vocabulary work over isolated vocabulary lists.
- Prefer real literature and source examples over invented sentences.
- Encourage whole-sentence analysis instead of left-to-right word guessing.
- Preserve ambiguity when one form admits multiple functions.
- Make uncertainty explicit when the generated summary or source span is
  incomplete.

## Platform Shape

This suggests a Foster learning experience with these layers:

- **Reader layer:** page- or passage-backed Latin examples with source refs.
- **Form layer:** observed form, lemma, morphology, and dictionary source.
- **Function layer:** Foster label beside traditional grammar.
- **Exercise layer:** reversing, agreement, time-number, and function drills.
- **Audit layer:** every generated claim links back to `toc:*` and `page:*`.

## Taxonomy Work

The generated summaries identify recurring bridge concepts that should inform
the grammar taxonomy:

- subject / naming;
- object / receiving;
- of-possession;
- to-for-from;
- by-with-from-in;
- direct address;
- place / where;
- verb time numbers;
- active/passive/deponent voice;
- relative and subordinate clause functions;
- indirect discourse and infinitive time relationships.

These should become mapped taxonomy nodes rather than loose display strings.
Each node should carry:

- Foster-facing label;
- conventional grammar names;
- exact morphology predicates where applicable;
- examples from reader/library texts;
- dictionary or analyzer evidence;
- Foster Ossa source refs.

## Review Gates

Before using these summaries as product-facing instruction:

- Regenerate or inspect any row that is not `generated_valid`.
- Spot-check generated claims against page refs before promoting them into
  stable taxonomy.
- Avoid long quotation in app-facing content; use paraphrase plus citation.
- Keep source rows and generated summaries separate in storage.
- Prefer small, inspectable rollups over one large book-level summary.

## Next Product Slice

The next implementation target should be a Foster concept registry audit:

1. Extract candidate taxonomy nodes from the validated TOC and experience
   summaries.
2. Match those nodes to existing LangNet grammar concepts.
3. Mark each node as directly supported, method-supported, or platform overlay.
4. Add reader examples and dictionary evidence for the first small set:
   subject, object, of-possession, to-for-from, and by-with-from-in.
