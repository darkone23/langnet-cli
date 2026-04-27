# Output Guide

LangNet currently exposes three useful output layers:

1. **Backend lookup output** from `lookup`.
2. **Evidence-backed claim/triple output** from `plan-exec` and `triples-dump`.
3. **First learner-facing reduced output** from `encounter`.

The learner-facing layer is still an MVP: it groups exact Witness Sense Units into buckets and preserves source evidence, but it is not yet the final semantic schema.

## High-Fidelity Display Rule

Display transforms may transliterate, normalize whitespace, expand abbreviations, label source notes, or add explanations. They must not silently discard source content. If a source segment is hard to interpret, keep it visible or move it into an explicit structured field that remains inspectable.

## `lookup`

`lookup` is useful for quick inspection. Its JSON is backend-keyed.

```bash
just cli lookup lat lupus --output json
```

Typical shape:

```json
{
  "whitakers": [...],
  "diogenes": {...},
  "cltk": {...}
}
```

`lookup --output pretty` is a terminal summary. It is intentionally compact and should not be treated as the final semantic schema.

## `plan-exec`

`plan-exec` runs the staged runtime:

```text
normalize → plan → fetch → extract → derive → claim
```

Use it when you need to know which tools were selected and what claim effects were produced.

```bash
just cli plan-exec lat lupus --output json
```

The JSON summary is intended for inspection and regression tests. It reports:

- cache status and response-ref count
- planned versus produced counts for fetch, extract, derive, and claim stages
- skipped optional calls with reasons and source-call IDs
- handler versions observed in produced effects
- compact claim rows

## `triples-dump`

`triples-dump` is the best current evidence-inspection command.

```bash
just triples-dump lat lupus whitakers
just triples-dump san agni cdsl
```

Use the third argument to narrow the tool family. Examples:

- `whitakers`
- `diogenes`
- `cdsl`
- `all`

Current output is text by default. Use `--output json` for structured inspection.

Current `triples-dump --output json` shape:

```json
{
  "query": {
    "language": "san",
    "text": "agni",
    "normalized_candidates": ["agni"]
  },
  "tool_filter": "cdsl",
  "filters": {
    "predicate": "gloss",
    "subject_prefix": null,
    "max_triples": 10
  },
  "claims": [
    {
      "claim_id": "clm-example",
      "tool": "claim.cdsl.sense",
      "subject": "drv-example",
      "predicate": "has_sense",
      "derivation_id": "drv-example"
    }
  ],
  "triples": [
    {
      "claim_id": "clm-example",
      "subject": "lex:agni",
      "predicate": "has_sense",
      "object": "sense:lex:agni#example",
      "metadata": {
        "evidence": {
          "source_tool": "cdsl",
          "claim_id": "clm-example",
          "response_id": "resp-example",
          "source_ref": "mw:123",
          "raw_blob_ref": "raw_json"
        }
      },
      "display_iast": "agni",
      "display_slp1": "agni",
      "source_encoding": "slp1"
    },
    {
      "claim_id": "clm-example",
      "subject": "sense:lex:agni#example",
      "predicate": "gloss",
      "object": "fire; sacrificial fire",
      "metadata": {
        "source_ref": "mw:123",
        "evidence": {
          "source_tool": "cdsl",
          "claim_id": "clm-example",
          "response_id": "resp-example",
          "source_ref": "mw:123",
          "raw_blob_ref": "raw_json"
        }
      }
    }
  ],
  "warnings": []
}
```

The JSON shape keeps claim metadata separate from triple metadata so tools can inspect claims without scraping the text renderer. Text output remains supported.

## `encounter`

`encounter` is the current learner-facing path. It runs staged evidence, projects cache-backed translations when requested, reduces source glosses into exact buckets, and prints a compact word encounter.

```bash
devenv shell langnet-cli -- encounter san dharma cdsl --max-buckets 5
devenv shell langnet-cli -- encounter san agni heritage --no-cache
devenv shell langnet-cli -- encounter lat lupus gaffiot --use-translation-cache
```

This output should be treated as a prototype learner interface. It is the right surface for examples and snapshots, but not yet a stable product schema.

The accepted-output gallery currently covers representative Sanskrit, Latin, and Greek snapshots in `tests/test_cli_encounter_output.py`. Add new examples there when display ranking or source transforms change.

For Sanskrit, Heritage is the preferred analysis/morphology source. A Heritage-only encounter may show an `Analysis` section without meaning buckets:

```text
agni [san]
==========

Analysis
- agn -> agn: loc. sg. m. (heritage)
- agn -> agn: loc. sg. n. (heritage)
```

For a combined Sanskrit lookup, `encounter` should show Heritage analysis alongside CDSL/DICO meaning evidence. CDSL source keys remain inspectable separately from learner-facing IAST display forms.

### Evidence Walkthrough: Sanskrit `dharma`

Use `encounter` first to see the learner-facing result:

```bash
devenv shell -- bash -c 'langnet-cli encounter san dharma all --no-cache --max-buckets 3'
```

For CDSL-backed meanings, the displayed bucket text may use a display gloss. This must not omit source content by default. Today `metadata.display_gloss` only applies display-safe Sanskrit transliteration transforms; the raw CDSL gloss remains in the evidence triple object.

To inspect where a displayed CDSL meaning came from, dump the source triples:

```bash
devenv shell -- bash -c 'langnet-cli triples-dump san dharma cdsl --no-cache --output json --predicate gloss --max-triples 3'
```

In the JSON, inspect the matching `gloss` triple:

- `object` is the raw CDSL source-near gloss.
- `metadata.display_gloss` is the conservative learner-display string used by `encounter` when present. It should preserve source content unless a future parser separates notes into explicit fields.
- `metadata.source_entry` identifies the CDSL row and source keys, including dictionary id, line number, `source_ref`, SLP1 key, and IAST key.
- `metadata.source_segments` is an ordered, source-complete split of the raw gloss text. Each segment has `raw_text` and `display_text`; unrecognized segments remain unclassified.
- `metadata.source_notes`, when present, summarizes confidently typed cross-reference/source-reference segments. It does not replace or remove the original segments.
- `metadata.source_ref` identifies the dictionary row, such as `mw:<line>`.
- `metadata.evidence.response_id`, `extraction_id`, `derivation_id`, and `claim_id` show the runtime path that produced the triple.
- `metadata.display_iast` and `metadata.display_slp1` show the learner form and source key separately.

That separation is the current evidence contract: learner output can be cleaner than source text, but source text remains inspectable.

### Evidence Walkthrough: DICO/Gaffiot Translation Cache

DICO and Gaffiot now follow the same evidence shape for French dictionary-entry
glosses. Their source text remains French and is marked with `source_lang: fr`;
cached English translations are separate derived witnesses.

For translated DICO/Gaffiot glosses:

- `metadata.parsed_glosses` contains individual English gloss candidates parsed from the translated text.
- `metadata.translated_segments` keeps the translated output in ordered display segments.
- `metadata.evidence.derived_from_tool` and `metadata.evidence.derived_from_sense` point back to the French source witness.

In `encounter`, cache-backed translation buckets are displayed before untranslated
French source buckets, and the output includes `translated from: dico` or
`translated from: gaffiot` when that provenance is available. Multi-witness
non-translated buckets are ranked ahead of single-witness buckets.

DICO and Gaffiot source entries are French source evidence. Cached English text is derived evidence, not a replacement for the French source.

First inspect the source French gloss:

```bash
devenv shell -- bash -c 'langnet-cli triples-dump lat lupus gaffiot --no-cache --output json --predicate gloss --max-triples 3'
devenv shell -- bash -c 'langnet-cli triples-dump san dharma dico --no-cache --output json --predicate gloss --max-triples 3'
```

In those source triples:

- `object` is the original French source gloss.
- `metadata.source_lang` should be `fr` when the source handler marks it.
- `metadata.evidence.source_tool` is `gaffiot` or `dico`.
- `metadata.evidence.source_ref` identifies the source entry, such as `gaffiot:<entry>` or `dico:<page>.html#<anchor>:<occurrence>`.

After a matching cache row exists, inspect the derived English evidence through `encounter`:

```bash
devenv shell -- bash -c 'langnet-cli encounter lat lupus gaffiot --use-translation-cache --translation-cache-db data/cache/langnet.duckdb --output json'
devenv shell -- bash -c 'langnet-cli encounter san dharma dico --use-translation-cache --translation-cache-db data/cache/langnet.duckdb --output json'
```

In the JSON, look for a witness whose `source_tool` is `translation`. Its evidence should include:

- `source_lexicon`: `gaffiot` or `dico`
- `source_ref`: the original French entry reference
- `source_text_hash`: the hash of the exact French source text that was translated
- `source_text_lang`: the language of the source text used for the cache key, currently `fr`
- `gloss_lang`: the language of the derived gloss object, currently `en`
- `translation_id`: the cache identity
- `model`, `prompt_hash`, and `hint_hash`
- `derived_from_tool`: the source tool, such as `gaffiot` or `dico`
- `derived_from_sense`: the source French sense anchor

The high-fidelity rule applies here too: the English gloss expands the source evidence for learners, but the source French triple remains the evidence-bearing input and must stay inspectable.

### Evidence Walkthrough: Latin `lupus`

Use `encounter` for the learner-facing view:

```bash
devenv shell -- bash -c 'langnet-cli encounter lat lupus all --no-cache --max-buckets 3'
```

Then inspect the exact triples that the reducer can consume:

```bash
devenv shell -- bash -c 'langnet-cli triples-dump lat lupus all --no-cache --output json --predicate gloss --max-triples 5'
```

For each displayed meaning, match the bucket text to a `gloss` triple. The
important fields are:

- `subject`: the sense anchor that received the gloss.
- `object`: the source gloss text used by WSU extraction.
- `metadata.evidence.source_tool`: the backend witness, such as `whitaker`, `diogenes`, `gaffiot`, or `translation`.
- `metadata.evidence.source_ref`: the source-local dictionary/reference identifier when available.
- `claim_id` and `claim_tool`: the claim row that emitted the triple.

If a translated Gaffiot bucket is displayed first, the corresponding English
witness should also expose `translated_from`, `translation_id`, and
`metadata.evidence.derived_from_sense`; use those fields to find the original
French source witness in the same claim.

Triples use this shape:

```json
{
  "subject": "lex:lupus#noun",
  "predicate": "has_sense",
  "object": "sense:lex:lupus#noun#...",
  "metadata": {
    "evidence": {
      "source_tool": "whitaker",
      "call_id": "...",
      "response_id": "...",
      "extraction_id": "...",
      "derivation_id": "...",
      "claim_id": "...",
      "raw_blob_ref": "raw_text"
    }
  }
}
```

## Reading Triples

| Anchor | Meaning |
| --- | --- |
| `form:<surface>` | observed input or inflected surface form |
| `interp:...` | one scoped interpretation of a form |
| `lex:<lemma>` | normalized lexical item |
| `sense:<lex>#...` | source-backed sense node |

Common predicates:

- `has_interpretation`
- `realizes_lexeme`
- `has_sense`
- `gloss`
- `has_citation`
- `has_morphology`
- `has_pos`, `has_case`, `has_number`, `has_gender`, `has_tense`, `has_voice`, `has_mood`
- `has_feature` for tool-specific details

The canonical predicate/evidence reference is `docs/technical/predicates_evidence.md`.

## Sanskrit CDSL Display

CDSL source rows are stored and queried in Sanskrit Lexicon/Cologne-style SLP1 keys. For example, `dharma` is backed by the source key `Darma`, `dharmaḥ` by `DarmaH`, and `kṛṣṇa` by `kfzRa`.

Runtime triples preserve those source-near forms as evidence:

- `display_iast` is the learner-facing form.
- `display_slp1` is the CDSL/source key.
- `display_gloss` is a conservative learner-facing gloss string for CDSL entries. It currently preserves source content and applies display-safe transliteration transforms only.
- `source_entry` identifies the dictionary row and CDSL source keys.
- `source_segments` stores ordered raw/display segment pairs without classifying or removing source text.
- `source_encoding` is usually `slp1`.

The `encounter` command uses these fields for display. It shows IAST forms first and source keys separately, and it prefers `display_gloss` when present. The raw CDSL entry text remains available as the `gloss` triple object with source references.

## Evidence Fields

| Field | Meaning |
| --- | --- |
| `source_tool` | backend or source family that produced the assertion |
| `call_id` | planned tool call that led to the claim |
| `response_id` | raw response used by extraction, when available |
| `extraction_id` | structured extraction effect |
| `derivation_id` | normalized derivation effect |
| `claim_id` | claim projection that emitted the triple |
| `source_ref` | stable dictionary/source entry reference, when available |
| `raw_blob_ref` | raw payload field such as `raw_text`, `raw_html`, or `raw_json` |
| `display_iast` | learner-facing Sanskrit display form, especially for CDSL SLP1 entries |
| `display_slp1` | raw or source-near Sanskrit SLP1 form for debugging and round-trip checks |
| `display_gloss` | learner-facing display string for a source gloss; raw source text remains the triple object |
| `source_entry` | structured source-row identity, such as CDSL dictionary id, line number, source ref, and source keys |
| `source_segments` | ordered source-complete segments with raw and display text |
| `source_encoding` | encoding of source-near display fields, for example `slp1` |

## Display Policy

Future learner-facing output should order information this way:

1. Headword/form.
2. Morphology or source-backed analysis when it clarifies the form, especially Sanskrit Heritage.
3. Grouped meanings.
4. Citations and source evidence.
5. Source disagreements or caveats.

Backend-keyed output remains useful for debugging, but learner-facing examples should now prefer `encounter` because it follows the claim-to-WSU reduction path.
