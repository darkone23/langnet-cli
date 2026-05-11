# Inflectional Paradigm Generation Roadmap

**Status:** ⏳ TODO  
**Feature Area:** pedagogy  
**Owner Roles:** @architect for source contract and scope, @sleuth for endpoint/parser research, @coder for implementation, @auditor for morphology correctness and ambiguity review, @scribe for learner-facing docs

## Summary

Extend dictionary lookup and learner encounters so a user can move from a
surface form or dictionary entry to a full inflectional paradigm.

The target workflow is:

1. User searches an inflected form or lemma.
2. LangNet identifies the likely root/lemma and any morphology for the surface.
3. LangNet offers a source-backed paradigm view for that lemma.
4. If the original surface appears in the paradigm, the matching cell or cells
   are highlighted.

Examples:

- Sanskrit `devebhyaḥ` -> dat./abl. plural of `deva` -> full `deva`
  declension with both plural cells highlighted.
- Latin `puellārum` -> genitive plural of `puella` -> full `puella`
  declension.
- Greek `λόγοις` -> dative plural of `λόγος` -> full `λόγος` paradigm.
- Sanskrit `abravīt` -> 3rd singular verbal form resolving to a root such as
  `√brū`, then a conjugation table when source metadata supports it.

This is foundational for reading assistance, drill mode, grammar exercises, and
future cross-language comparison.

## Source Discovery

Recent local probing confirms that the upstream services already provide much
of the needed paradigm data.

### Sanskrit Heritage

The local Heritage service is running at `http://localhost:48080` and exposes:

- `/cgi-bin/skt/sktreader` for current reader morphology.
- `/cgi-bin/skt/sktdeclin` for nominal declension tables.
- `/cgi-bin/skt/sktconjug` for verbal conjugation tables.
- `/cgi-bin/skt/sktparser`, `/cgi-bin/skt/sktgraph`, and
  `/cgi-bin/skt/sktgraph2` for parser/solution views.

Confirmed examples:

```text
http://localhost:48080/cgi-bin/skt/sktdeclin?q=putra;g=Mas;font=roma;t=VH;lex=SH
http://localhost:48080/cgi-bin/skt/sktconjug?q=gam;c=1;font=roma;t=VH;lex=SH
```

`sktdeclin` returns a table with cases as rows, numbers as columns, and one or
more forms in each cell. `sktconjug` returns nested inflection tables grouped by
conjugation, tense/mood, voice, person, and number, plus participle links that
cascade back to `sktdeclin`.

### Diogenes / Perseus

The local Diogenes service is running at `http://localhost:8888`. Direct curl
probes need `curl --http0.9` because of the server response style.

Confirmed routes:

```text
http://localhost:8888/Perseus.cgi?do=parse&lang=lat&q=amo
http://localhost:8888/Perseus.cgi?do=lemma&lang=lat&q=amo&noheader=1
http://localhost:8888/Perseus.cgi?do=inflect&lang=lat&q=amo&noheader=1
http://localhost:8888/Perseus.cgi?do=inflect&lang=grk&q=lo/gos&noheader=1
```

`do=inflect` returns repeated `span.form_span_visible` nodes. Each row carries
the generated form and an `infl` attribute such as `(pres ind act 1st sg)` or
`(masc dat sg)`. Greek display text is Unicode while checkbox values remain in
beta code.

## Product Scope

### V1: Source-Backed Paradigm Views

V1 should not start by writing a full local morphology generator. It should
adapt existing source-backed engines:

- Heritage `sktdeclin` for Sanskrit noun/adjective/pronoun declensions.
- Heritage `sktconjug` for Sanskrit root conjugations when root and class are
  known.
- Diogenes `do=inflect` for Greek and Latin inflected-form inventories.
- Existing Heritage reader and Diogenes parse output for surface-form analysis
  and highlight resolution.

This gives users useful paradigm tables while preserving source provenance and
avoiding premature local grammar-engine complexity.

### Later: Local Template Registry

The longer-term feature request calls for a local paradigm template registry
keyed by `(language, part_of_speech, paradigm_class, paradigm_subclass)`. That
should remain a later phase after the source-backed contract and UI behavior are
stable.

## Entry Classification

Paradigm-aware lookup results should classify entries with:

- `root`: canonical lemma/root form capable of a paradigm.
- `variant`: inflected form resolving to a root plus one or more analyses.
- `indeclinable`: particle, adverb, preposition, or other no-paradigm form.
- `compound_member`: primarily Sanskrit, for forms usable only in compounds.

For V1 this classification can be computed per result from source evidence
rather than pre-populated for every dictionary row.

Example variant shape:

```json
{
  "form": "devebhyaḥ",
  "entry_type": "variant",
  "resolves_to": "deva",
  "analyses": [
    { "case": "dative", "number": "plural" },
    { "case": "ablative", "number": "plural" }
  ],
  "ambiguous": true
}
```

Syncretic forms must keep all valid analyses. The UI should highlight all
matching cells, not pick one silently.

## Unified Data Contract

Add a schema version such as `langnet.paradigm.v1`.

Top-level shape:

```json
{
  "schema_version": "langnet.paradigm.v1",
  "request": {
    "language": "san",
    "surface": "devebhyaḥ",
    "lemma": "deva",
    "source": "heritage"
  },
  "entry": {
    "id": "heritage:SH:deva",
    "language": "san",
    "part_of_speech": "noun",
    "entry_type": "root",
    "lemma_form": "deva",
    "source_dictionary": "SH",
    "source_entry_id": "/skt/DICO/..."
  },
  "origin": {
    "form": "devebhyaḥ",
    "entry_type": "variant",
    "resolves_to": "heritage:SH:deva",
    "analyses": [
      { "case": "dative", "number": "plural" },
      { "case": "ablative", "number": "plural" }
    ]
  },
  "paradigm": {
    "kind": "declension",
    "layout": {
      "rows": ["nominative", "vocative", "accusative"],
      "columns": ["singular", "dual", "plural"]
    },
    "cells": [
      {
        "features": { "case": "dative", "number": "plural" },
        "forms": ["devebhyaḥ"],
        "highlighted": true,
        "source": "heritage:sktdeclin"
      }
    ]
  },
  "warnings": []
}
```

The same cell model should support Latin/Greek Diogenes rows even when the
source output is a flat list rather than a rectangular table.

## Required Behaviors

### Search Result Enhancement

Lookup and encounter output should:

- preserve the user surface form;
- show the selected lemma/root;
- include possible analyses for variants;
- indicate whether a paradigm is available;
- expose a stable action target for the paradigm request;
- avoid hiding ambiguity.

### Highlighting

When the user arrives from an inflected form, the paradigm response should mark
all cells whose forms match the originating surface after normalized comparison.

Examples:

- Sanskrit `devebhyaḥ` highlights dative plural and ablative plural.
- Latin `puellae` may highlight genitive singular, dative singular, and
  nominative plural.
- Greek `λόγοις` highlights dative plural.

### Disambiguation

If a surface has multiple root analyses, the response should carry multiple
candidate roots. The UI should let the user choose which paradigm to view rather
than collapsing them into one.

Example:

```json
{
  "surface": "amās",
  "candidates": [
    {
      "lemma": "amō",
      "entry_type": "variant",
      "analyses": [{ "person": "2", "number": "singular", "tense": "present" }]
    },
    {
      "lemma": "ama",
      "entry_type": "variant",
      "analyses": [{ "case": "accusative", "number": "plural" }]
    }
  ]
}
```

## Per-Language Notes

### Sanskrit

V1 should prefer Heritage as the authoritative source:

- Use `sktreader` to resolve surface forms to lemmas and analyses.
- Use `sktdeclin` when a nominal stem and gender are known.
- Use `sktconjug` when a verbal root and present class are known.
- Parse participle declension links from `sktconjug` as follow-up paradigm
  targets.

Important fields for later local generation:

- `stem`, `gender`, `stem_final`, `paradigm_class`;
- `strong_stem`, `middle_stem`, `weak_stem` for alternating stems;
- `present_class`, `pada`, `set_aniṭ`, and derived stems for verbs;
- `irregular`, `pronoun`, `compound_only`, `vedic_only`, `classical_only`.

V1 should scope to Classical Sanskrit source output and defer compound
decomposition and Vedic-specific generation.

### Latin

V1 should prefer Diogenes/Perseus for inflection inventories and existing
Whitaker/CLTK/Diogenes parse output for surface analysis.

Later local metadata should include:

- noun lemma, genitive singular, gender, stem, declension;
- verb principal parts, conjugation, present/perfect/participial stems;
- irregular flags such as `deponent`, `semi_deponent`, `defective`, and
  `impersonal`.

### Greek

V1 should prefer Diogenes/Perseus `do=inflect` for generated forms and existing
Diogenes parse output for surface analysis.

Later local metadata should include:

- noun lemma, article, gender, genitive singular, stem, declension/subclass;
- verb principal parts, thematic/athematic class, contraction type;
- irregular flags such as `contract`, `deponent`, `defective`, `suppletive`;
- accent-class metadata if local generation becomes a target.

Correct Greek accent generation should remain out of scope for local generation
until a reliable source or rule implementation is available.

## Proposed CLI/API Surface

CLI examples:

```bash
just cli paradigm san deva --source heritage --kind declension --gender Mas --output json
just cli paradigm san gam --source heritage --kind conjugation --class 1 --output json
just cli paradigm lat amo --source diogenes --output json
just cli paradigm grc logos --source diogenes --output json
just cli encounter san devebhyaḥ --show-paradigm --output json
```

The first implementation can expose a CLI command before adding a web endpoint.
The web UI can then call the CLI/API surface used by `langnet-web2`.

## Implementation Phases

### Phase 1: Endpoint Adapters And Fixtures

- Add fixture HTML for `sktdeclin`, `sktconjug`, and Diogenes `do=inflect`.
- Add parser tests for table rows, forms, and feature labels.
- Add a small service boundary that fetches from source endpoints and returns
  raw HTML plus parsed rows.

### Phase 2: Unified Paradigm Model

- Add `ParadigmResponse`, `ParadigmEntry`, `ParadigmCell`, and
  `ParadigmAnalysis` models.
- Preserve source references and request URLs.
- Normalize feature names across languages without dropping source labels.

### Phase 3: CLI Command

- Add `langnet-cli paradigm`.
- Support Sanskrit Heritage declension/conjugation.
- Support Latin/Greek Diogenes `do=inflect`.
- Add JSON-first output and a compact pretty view.

### Phase 4: Lookup And Encounter Integration

- Add `paradigm_available` and `paradigm_request` metadata to lookup and
  encounter results.
- When the surface form has analyses, highlight matching paradigm cells.
- Preserve ambiguous analyses and expose multiple candidate roots when needed.

### Phase 5: Documentation And UX

- Document source-backed coverage, limitations, and example commands.
- Update learner-facing docs to explain ambiguity and highlighting.
- Add web integration notes for `langnet-web2`.

### Phase 6: Local Generation Research

- Revisit the full template registry only after source-backed views work.
- Decide whether to pre-generate variants or generate on demand.
- If local generation is pursued, start with the narrowest high-value subset:
  Sanskrit a-stem nouns, Latin first declension nouns, and Greek second
  declension nouns.

## Acceptance Criteria

V1 is complete when:

- `sktdeclin` output for a known Sanskrit noun parses into structured rows.
- `sktconjug` output for a known Sanskrit root parses at least finite-form
  tables and participle links.
- Diogenes `do=inflect` output for Latin and Greek parses into structured form
  rows with source morphology labels.
- A CLI user can request a paradigm for at least:
  - Sanskrit `putra` or `deva`;
  - Sanskrit `gam` class 1;
  - Latin `amo`;
  - Greek `λόγος` or beta-code `lo/gos`.
- A lookup/encounter result can advertise an available paradigm target.
- Variant-origin highlighting works for at least one Sanskrit, one Latin, and
  one Greek fixture.
- Ambiguous analyses remain represented as arrays.
- Docs describe source-backed limitations clearly.

Full long-term completion additionally requires:

- complete entry classification for dictionary rows;
- variant-to-root resolution for generated or indexed variants;
- local root metadata for supported paradigms;
- a local template registry for the agreed subset;
- UI navigation from search results to paradigm views.

## Out Of Scope For V1

- Full local morphology generation for arbitrary entries.
- Pre-generating all variants for all lexemes.
- Sanskrit compound decomposition.
- Vedic Sanskrit forms.
- Greek accent generation independent of source output.
- Cross-language paradigm comparison.
- Drill/quiz mode.
- Pāṇinian derivational explanations.

## Open Questions

1. Should the first user-facing surface be CLI-only, or should we add the web
   view in the same milestone?
2. Should Sanskrit paradigm requests require explicit gender/class from the
   caller, or should LangNet infer them from Heritage reader/dictionary links
   before asking the user?
3. Should Diogenes Greek input accept Unicode and internally convert to beta
   code for `do=inflect`, or should v1 document beta-code input for that command?
4. How much of the source HTML should be preserved in JSON for audit/debug?
5. Should this feature live under `encounter` first, or as an independent
   `paradigm` command that `encounter` later links to?
