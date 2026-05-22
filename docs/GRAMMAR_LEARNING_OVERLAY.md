# Grammar Learning Overlay

LangNet should help people read, understand, learn, and eventually write
classical languages. The grammar learning overlay is the teaching layer that
turns source-backed morphology into a bridge from Foster functional grammar to
traditional Greek, Latin, and Sanskrit grammar.

## Purpose

The learner should be able to start with a simple functional question:

> What is this form doing?

Then LangNet should connect that answer to traditional grammar:

> Grammarians call this the genitive. In Greek this is γενική; in Latin,
> genetivus; in Sanskrit, ṣaṣṭhī vibhakti.

The overlay should also teach process-level rules:

- nouns, adjectives, and pronouns decline;
- verbs conjugate;
- stems take endings;
- sandhi can change sounds at boundaries;
- compounds combine lexical units;
- principal parts and stems help predict forms.

## Layering

### 1. Evidence Layer

The overlay does not invent morphology. It starts from source-backed evidence:

- Heritage Sanskrit morphology;
- Whitaker Latin morphology;
- Diogenes/Morpheus Greek and Latin morphology;
- optional spaCy Greek fallback when available;
- future dictionary-entry parsing.

The evidence layer emits exact facts such as `case=genitive`,
`number=singular`, `voice=active`, or `paradigm_kind=declension`.

### 2. Concept Mapping Layer

Exact morphology facts map to stable grammar concepts:

- `case=genitive` -> `case.genitive`
- `case=dative` -> `case.dative`
- `case=ablative` -> `case.ablative`
- `case=instrumental` -> `case.instrumental`
- `number=dual` -> `number.dual`
- `gender=neuter` -> `gender.neuter`
- `voice=passive` -> `voice.passive`
- `part_of_speech=noun` plus `paradigm_kind=declension` -> `process.declension`
- `part_of_speech=verb` plus person/number/tense/mood/voice -> `process.conjugation`
- future Sanskrit sandhi evidence -> `process.sandhi`
- future compound evidence -> `process.compound`

This mapping is language-aware but source-agnostic.

### 3. Teaching Layer

The teaching layer presents:

- Foster gateway label;
- traditional English label;
- Greek, Latin, and Sanskrit grammar names where known;
- plain-language explanation;
- structured grammar-source evidence, beginning with work-level reader anchors;
- source-backed examples;
- reading guidance;
- eventually writing/practice guidance.

## Example

For Greek `λόγου`, the overlay should be able to present:

- observed form: `λόγου`
- source-backed parse: masculine genitive singular
- Foster gateway: Possessing Function
- traditional English: genitive singular
- Greek term: γενική
- Latin comparison: genetivus
- Sanskrit comparison: ṣaṣṭhī vibhakti
- process: declension
- rule: nouns decline for case, number, and gender

## Annotation-Inspired Reading Goals

The Latin sentence markup reference at `~/latin-lang-markup.png` gives the
right product target for passage reading: annotate the structure of the text
without burying the reader in a grammar lecture.

Actionable goals:

- mark observed words with stable roles: subject, object, verb, modifier,
  connective, and clause boundary;
- make distant connections visible, especially separated subjects/verbs,
  adjective/noun agreement, genitive relationships, and coordinated forms;
- distinguish large clauses from smaller embedded clauses;
- expose conjunctions and enclitics such as Latin `et`/`-que` as sentence
  structure, not just dictionary headwords;
- let a learner toggle the annotation layers rather than forcing every mark to
  appear at once;
- connect every visual mark back to source-backed morphology, a parser claim, a
  reader segment, or an explicit "not yet source-backed" caveat;
- use the same concept IDs in CLI JSON, web annotation payloads, and future
  practice/writing prompts.

This creates three linked learning modes:

1. **Word mode:** What is this form? Show morphology, Foster gateway, and
   traditional terms.
2. **Sentence mode:** What is this form doing here? Show subject/object/verb,
   agreement, connective, and clause relations.
3. **Grammar-source mode:** Why do grammarians describe it this way? Link to
   grammar works and source-backed examples where available.

## Product Surfaces

### CLI

The first implementation surface is the CLI, because it is the fastest place to
audit the teaching contract before the web UI hardens around it:

```bash
just cli learn concepts --output json
just cli learn concepts --kind case --output json
just cli learn concept case.genitive --output json
just cli learn evidence-report --output json
just cli learn map \
  --pos noun \
  --paradigm-kind declension \
  --feature case=genitive \
  --feature number=plural \
  --feature gender=masculine \
  --output json
just cli encounter san putraa.naam heritage --include-learning --output json
```

The CLI should remain endpoint-free for concept exploration. It reads the local
registry and mapper only. `encounter --include-learning` is the first
source-backed integration point: it derives candidate-local learning overlays
from morphology-driven paradigm resolution, without fetching full paradigm
tables. Learning concepts include `source_evidence` records, so CLI JSON can
point to classical grammar source works before individual segment citations are
available.

Use `learn evidence-report` as the stabilization gate before expanding into
segment-level grammar-source research or web UI wiring. It should show every
exposed concept with work-level evidence. Concepts without exact passage
citations should list `reader_segment_links` as the expected remaining gap.
The current segment-backed slice covers 23 of 24 exposed concepts with exact
Greek, Latin, or Sanskrit reader passages. `process.declension` remains the
known gap because the available local lines are not yet strong enough to carry
a precise teaching claim. Sanskrit sound-change examples include
`sound_change.guna`, `sound_change.vrddhi`, and `sound_relation.savarna`.

Local source texts are explored through the reader works tool. The current
local Aṣṭādhyāyī record is:

```bash
just cli reader works --language san --query Aṣṭādhyāyī --limit 10 --output json
just cli reader work langnet:reader:sanskrit_dcs:dcs_413 --output json
just cli reader contents langnet:reader:sanskrit_dcs:dcs_413 --limit 12 --output json
just cli reader show langnet:reader:sanskrit_dcs:dcs_413 --segment 550729 --output json
just cli reader show langnet:reader:sanskrit_dcs:dcs_413 --segment 551238 --output json
just cli reader show langnet:reader:tlg:tlg0063.001 --segment 1.1.31.7 --output json
just cli reader show langnet:reader:digiliblt:dlt000157 --segment 76 --output json
```

Use these reader addresses as evidence links only when the specific segment
actually supports the concept being taught.

Useful local grammar-work discovery commands:

```bash
just cli reader works --language lat --group grammar --sort group-popularity --limit 20 --output json
just cli reader works --language grc --group grammar --sort group-popularity --limit 20 --output json
just cli reader works --language san --group grammar --sort group-popularity --limit 20 --output json
```

Current high-value source anchors include:

| Language | Work | Reader selector |
| --- | --- | --- |
| Latin | Varro, `De Lingua Latina` | `langnet:reader:phi:lat0684.001` |
| Greek | Dionysius Thrax, `Ars grammatica` | `langnet:reader:tlg:tlg0063.001` |
| Greek | Apollonius Dyscolus, `Περὶ συντάξεως` | `urn:cts:greekLit:tlg0082.tlg004` |
| Sanskrit | Pāṇini, `Aṣṭādhyāyī` | `langnet:reader:sanskrit_dcs:dcs_413` |
| Sanskrit | Yāska, `Nirukta` | `langnet:reader:sanskrit_dcs:dcs_367` |

See [`docs/technical/grammar-source-anchors.md`](technical/grammar-source-anchors.md)
for the maintained source map, including CTS/CTSv2 reader addresses and
external research grounding.

### Web

The web app should add a compact "Learn this form" panel near Forms:

- Foster label as the gateway;
- native morphology;
- traditional names;
- one short rule;
- examples across languages when helpful;
- source/evidence link.

This should not become a textbook page. It should help a reader understand the
form in front of them, then offer deeper links.

## Design Rules

- Foster labels are gateways, not replacements.
- Traditional grammar terms remain visible.
- Sanskrit grammatical labels are Sanskrit traditional terms in the same
  `traditional` map as Greek and Latin labels. They are not the name of the
  universal layer.
- Every teaching claim should be backed by source morphology or an explicit
  registry concept.
- Work-level source evidence is a bibliography/discovery link; segment-level
  source evidence is required before claiming a specific classical passage
  proves a concept explanation.
- The system should say when evidence is missing.
- Concepts should be reusable across CLI, web, docs, and future practice modes.
