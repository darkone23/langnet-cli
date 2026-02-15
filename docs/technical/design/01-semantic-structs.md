# LangNet CLI – Unified Output Schema v1 Specification

## Status

Draft – Target for Stabilization

## Purpose

This document defines the stable JSON output schema for `cli word` queries.

The schema:

* Separates surface input from lexical hypotheses
* Preserves source traceability
* Distinguishes semantic identity from gloss description
* Supports epistemic modes (`open`, `skeptic`)
* Allows internal evolution without breaking external consumers

This schema is versioned and must remain backward-compatible once stabilized.

---

# 1. Architectural Overview

The CLI pipeline produces:

```
Surface Query
    ↓
Lemma Hypotheses
    ↓
Witness Sense Units (per source)
    ↓
Sense Buckets (clustered WSUs)
    ↓
Semantic Constants (stable identifiers)
    ↓
Display Gloss (human-readable description)
```

Important distinction:

| Layer             | Stability            | Purpose                 |
| ----------------- | -------------------- | ----------------------- |
| Witness           | Source-defined       | Raw evidence            |
| Bucket            | Algorithm-defined    | Cluster artifact        |
| Semantic Constant | Registry-defined     | Stable concept identity |
| Display Gloss     | Presentation-defined | Description of concept  |

Buckets may change as evidence changes.
Semantic constants must remain stable once curated.

---

# 2. Top-Level Object

```json
{
  "schema_version": "1.0.0",
  "query": { ... },
  "lemmas": [ ... ],
  "analyses": [ ... ],
  "senses": [ ... ],
  "citations": [ ... ],
  "provenance": [ ... ],
  "ui_hints": { ... },
  "warnings": [ ... ]
}
```

---

# 3. Query Object

```json
"query": {
  "surface": "string",
  "language_hint": "lat | grc | san | null",
  "normalized": "string",
  "normalization_steps": []
}
```

Represents user input and normalization pipeline.

---

# 4. Lemmas

```json
"lemmas": [
  {
    "lemma_id": "san:śiva",
    "display": "śiva",
    "language": "san",
    "sources": ["SOURCE_MW", "SOURCE_HERITAGE"]
  }
]
```

Multiple candidates allowed.

**Source Enum Values**:
- `SOURCE_MW`: Monier-Williams Sanskrit-English Dictionary
- `SOURCE_AP90`: Apte Practical Sanskrit-English Dictionary  
- `SOURCE_HERITAGE`: Sanskrit Heritage Platform
- `SOURCE_CDSL`: Cologne Digital Sanskrit Lexicon
- `SOURCE_WHITAKERS`: Whitaker's Words (Latin)
- `SOURCE_DIOGENES`: Diogenes (Latin/Greek)
- `SOURCE_LEWIS_SHORT`: Lewis & Short Latin Dictionary
- `SOURCE_LSJ`: Liddell-Scott-Jones Greek-English Lexicon
- `SOURCE_CLTK`: Classical Language Toolkit

**Source Enum Values**:
- `SOURCE_MW`: Monier-Williams Sanskrit-English Dictionary
- `SOURCE_AP90`: Apte Practical Sanskrit-English Dictionary  
- `SOURCE_HERITAGE`: Sanskrit Heritage Platform
- `SOURCE_CDSL`: Cologne Digital Sanskrit Lexicon
- `SOURCE_WHITAKERS`: Whitaker's Words (Latin)
- `SOURCE_DIOGENES`: Diogenes (Latin/Greek)
- `SOURCE_LEWIS_SHORT`: Lewis & Short Latin Dictionary
- `SOURCE_LSJ`: Liddell-Scott-Jones Greek-English Lexicon
- `SOURCE_CLTK`: Classical Language Toolkit

---

# 5. Analyses (Surface-Level Morphology)

```json
"analyses": [
  {
    "type": "ANALYSIS_TYPE_MORPHOLOGY",
    "features": {
      "pos": "POS_NOUN",
      "case": "CASE_VOCATIVE",
      "number": "NUMBER_SINGULAR",
      "gender": "GENDER_MASCULINE"
    },
    "witnesses": [
      {
        "source": "SOURCE_HERITAGE",
        "ref": "heritage:morph:ziva"
      }
    ]
  }
]
```

Analyses describe the input form, not the lemma ontology.

---

# 6. Senses (Bucketed + Constant-Aligned)

Each element in `senses[]` represents a **bucketed cluster of witness senses** aligned to an optional semantic constant.

```json
"senses": [
  {
    "sense_id": "B1",
    "semantic_constant": "AUSPICIOUSNESS",
    "display_gloss": "auspicious; benign; favorable",
    "domains": ["general"],
    "register": ["epithet"],
    "confidence": 0.91,
    "witnesses": [
      {
        "source": "MW",
        "sense_ref": "217497"
      }
    ]
  }
]
```

---

## 6.1 Field Definitions

| Field             | Required | Description                                  |
| ----------------- | -------- | -------------------------------------------- |
| sense_id          | yes      | Stable bucket identifier (cluster artifact)  |
| semantic_constant | nullable | Stable registry ID for semantic concept      |
| display_gloss     | yes      | Human-readable gloss selected from witnesses |
| domains           | optional | Semantic domains                             |
| register          | optional | Register classification                      |
| confidence        | yes      | Bucket coherence/support metric (0.0-1.0)    |
| witnesses         | yes      | Supporting WSUs (use Source enum values)     |

---

# 7. Semantic Constant Policy

`semantic_constant` represents a stable semantic identity selected from a registry.

Rules:

1. If bucket matches known constant → assign it.
2. If no match → introduce new provisional constant.
3. Provisional constants may later be curated.
4. Constants must not change identity once curated.
5. Constants are language-agnostic identifiers.

Example constant registry entry (not emitted per query):

```json
{
  "constant_id": "AUSPICIOUSNESS",
  "canonical_label": "auspiciousness",
  "description": "state or quality of being favorable or blessed",
  "status": "curated"
}
```

---

# 8. Citations

Canonical citation objects.

```json
{
  "source": "Perseus",
  "type": "cts",
  "ref": "urn:cts:latinLit:phi0119.phi008"
}
```

Citation types include:

* cts
* dictionary
* morph
* etymology
* note

---

# 9. Provenance

```json
"provenance": [
  {
    "tool": "cdsl_indexer",
    "version": "0.3.2",
    "timestamp": "2026-02-12T14:32:10Z"
  }
]
```

All outputs must include provenance metadata.

---

# 10. UI Hints

```json
"ui_hints": {
  "default_mode": "open",
  "primary_lemma": "san:śiva",
  "collapsed_senses": ["B4", "B7"]
}
```

These do not alter evidence — only display defaults.

---

# 11. Stability Rules

1. Field names must not change in v1.x.
2. `semantic_constant` may be null.
3. Bucket IDs must remain stable if evidence unchanged.
4. Mode must not alter schema shape.
5. Witness references must remain resolvable.

---

# 12. Completion Criteria

* [ ] JSON schema validation file created
* [ ] Unit tests enforce required fields
* [ ] Semantic constant nullable support implemented
* [ ] Snapshot tests confirm stability
* [ ] Version string exposed in CLI output
