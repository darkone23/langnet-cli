# Grammar Concept Registry

The grammar concept registry is the data contract for the grammar learning
overlay. It maps source-backed morphology facts to stable teachable concepts.

## Concept Shape

```yaml
id: case.genitive
kind: case
foster_gateway: Possessing Function
plain_english: Marks belonging, association, source, description, or relation.
traditional:
  en: genitive
  grc: γενική
  lat: genetivus
  san: ṣaṣṭhī vibhakti
  san_role: sambandha
applies_to:
  - noun
  - adjective
  - pronoun
processes:
  - process.declension
source_basis:
  - Smyth Greek Grammar
  - Allen and Greenough Latin Grammar
  - Whitney Sanskrit Grammar
evidence:
  - evidence_level: reader_work
    source_anchor_id: grammar.source.dionysius_thrax.ars_grammatica
    work_id: langnet:reader:tlg:tlg0063.001
    canonical_text_id: urn:ctsv2:grc:ars-grammatica-peri-grammatike-s
    cts_work_urn: urn:cts:greekLit:tlg0063.tlg001
    citation_path:
    canonical_address: urn:ctsv2:grc:ars-grammatica-peri-grammatike-s
    label: "Dionysius Thrax, Ars grammatica"
examples:
  grc: λόγου
  lat: puellae
  san: putrāṇām
skills:
  read: Recognize possession, association, or relation.
  understand: Connect the form to its sentence role.
  learn: Map Foster language to traditional case terminology.
  write: Choose the appropriate genitive form in controlled practice.
```

## Required Fields

- `id`: stable dotted identifier.
- `kind`: concept category such as `case`, `number`, `gender`, `tense`,
  `mood`, `voice`, `process`, `form_part`, `sound_change`, or
  `sound_relation`.
- `foster_gateway`: learner-facing functional label when applicable.
- `plain_english`: short teaching explanation.
- `traditional`: language-specific traditional names.
- `applies_to`: relevant parts of speech or contexts.
- `processes`: related process concepts.
- `source_basis`: grammar references or project source notes supporting the
  concept text.
- `evidence`: structured reader-work or reader-segment links that ground the
  concept in classical grammar source traditions.
- `examples`: source-backed examples by language.
- `skills`: read/understand/learn/write guidance.

Sanskrit grammatical labels belong in `traditional` beside Greek and Latin
labels. Do not create a separate universal layer named after one grammar text
or school. Use additional keys such as `san_role` or `san_process` when a
Sanskrit role/process term is useful for teaching.

## Source Evidence

The registry keeps compact `source_basis` strings for readable provenance, but
it now also carries structured evidence links that point into the reader
catalog:

```yaml
evidence:
  - evidence_level: reader_segment
    source_anchor_id: grammar.source.panini.astadhyayi
    work_id: langnet:reader:sanskrit_dcs:dcs_413
    canonical_text_id: urn:ctsv2:san:astadhyayi-vrddhir-adaic
    citation_path: "550729"
    canonical_address: urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550729
    label: "Pāṇini, Aṣṭādhyāyī: adeṅ guṇaḥ"
```

Only attach a reader segment when that specific passage supports the concept.
The reader work record alone is useful as a bibliography/source anchor, but it
is not proof for a specific teaching claim.

The maintained work-level anchor list is
[`grammar-source-anchors.md`](grammar-source-anchors.md). It includes local
reader selectors, CTS/CTSv2 addresses, and external bibliography checks for
Varro, Dionysius Thrax, Apollonius Dyscolus, Pāṇini, Yāska, Kāśikāvṛtti, and
supporting grammar works.

Discovery commands:

```bash
just cli reader works --language lat --group grammar --sort group-popularity --limit 20 --output json
just cli reader works --language grc --group grammar --sort group-popularity --limit 20 --output json
just cli reader works --language san --group grammar --sort group-popularity --limit 20 --output json
```

## Initial Concept Families

Phase 1 should cover:

- cases: nominative, vocative, accusative, genitive, dative, ablative,
  instrumental, locative;
- numbers: singular, dual, plural;
- genders: masculine, feminine, neuter;
- verb features: person, tense, mood, voice;
- processes: declension, conjugation, inflection, stem, ending;
- source-grounded Greek, Latin, and Sanskrit anchors for the current core
  concept slice. As of this pass, 23 of 24 exposed concepts have exact
  `reader_segment` evidence; `process.declension` intentionally remains
  work-level only until a clean passage-level definition is verified.

Phase 2 should add:

- Sanskrit sandhi;
- compounds;
- principal parts;
- Sanskrit vibhakti, tiṅ, lakāra;
- Greek augment and reduplication;
- Latin declension and conjugation classes.

## Mapping Contract

The mapper consumes the morphology candidate fields already produced by
`langnet.morphology.candidates` and `langnet.paradigm.resolver`.

Examples:

| Evidence | Concept |
| --- | --- |
| `case=genitive` | `case.genitive` |
| `case=dative` | `case.dative` |
| `case=vocative` | `case.vocative` |
| `case=ablative` | `case.ablative` |
| `case=instrumental` | `case.instrumental` |
| `case=locative` | `case.locative` |
| `number=dual` | `number.dual` |
| `gender=neuter` | `gender.neuter` |
| `voice=passive` | `voice.passive` |
| `voice=middle` | `voice.middle` |
| `paradigm_kind=declension` | `process.declension` |
| `paradigm_kind=conjugation` | `process.conjugation` |
| verified guṇa source segment | `sound_change.guna` |
| verified vṛddhi source segment | `sound_change.vrddhi` |
| verified savarṇa source segment | `sound_relation.savarna` |
| future sandhi evidence | `process.sandhi` |
| future compound evidence | `process.compound` |

The mapper should preserve uncertainty. If a source emits ambiguous analyses,
the concept list should keep those alternatives rather than collapse them into
one answer.
