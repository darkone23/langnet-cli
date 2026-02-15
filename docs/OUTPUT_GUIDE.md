# Output Guide

This guide shows how to read the JSON returned by `langnet-cli query` and the `/api/q` endpoint. Outputs follow the dataclasses in `src/langnet/schema.py` and are designed to stay stable as we harden the Schema v1 contract.

## Top-Level Shape

- CLI/API responses are **lists of dictionary entries** (one per backend that responded).
- Each entry is a `DictionaryEntry` object with the fields below.
- Some backends (e.g., Diogenes) also include raw dictionary blocks for transparency.

```json
[
  {
    "word": "lupus",
    "language": "lat",
    "source": "whitakers",
    "definitions": [
      {
        "definition": "wolf",
        "pos": "noun",
        "gender": "m",
        "examples": [],
        "citations": [],
        "metadata": {
          "decl": "2nd",
          "variant": null
        },
        "source_ref": null,
        "domains": [],
        "register": [],
        "confidence": null
      }
    ],
    "morphology": {
      "lemma": "lupus",
      "pos": "noun",
      "features": {
        "case": "nom",
        "number": "sing",
        "gender": "m"
      },
      "foster_codes": ["NAM"],
      "declension": "2nd",
      "conjugation": null,
      "stem_type": null,
      "tense": null,
      "mood": null,
      "voice": null,
      "person": null
    },
    "dictionary_blocks": [],
    "metadata": {}
  }
]
```

Field notes:
- `definitions[]` list dictionary senses. `source_ref` holds a stable entry ID when available (e.g., `mw:217497`).
- `morphology` summarizes POS and features; `foster_codes` contain functional grammar labels when present.
- `dictionary_blocks[]` appears for Diogenes responses and mirrors the raw entry text and citation metadata.
- `metadata` is backend-specific and may include timings or extra flags; avoid depending on its keys without checking.

## Interpreting Multiple Backends

Queries may return several entries for the same word (e.g., Heritage + CDSL for Sanskrit, Diogenes + Whitaker’s for Latin). Present them separately to learners unless you deliberately merge them in a reduction pipeline.

## Sample Outputs (trimmed)

These are representative examples to illustrate shape and ordering; values will differ by environment and backend availability.

### Latin (`whitakers`, `diogenes`)
```json
[
  {
    "word": "lupus",
    "language": "lat",
    "source": "whitakers",
    "definitions": [{"definition": "wolf", "pos": "noun", "gender": "m", "citations": [], "source_ref": null}],
    "morphology": {"lemma": "lupus", "pos": "noun", "features": {"case": "nom", "number": "sing", "gender": "m"}, "foster_codes": ["NAM"]},
    "dictionary_blocks": []
  },
  {
    "word": "lupus",
    "language": "lat",
    "source": "diogenes",
    "definitions": [],
    "dictionary_blocks": [{"entryid": "00", "entry": "lupus, i, m. a wolf ..."}]
  }
]
```

### Greek (`diogenes`, CLTK morphology)
```json
[
  {
    "word": "λογος",
    "language": "grc",
    "source": "diogenes",
    "definitions": [],
    "dictionary_blocks": [{"entryid": "00", "entry": "λογος, ου, ὁ, computation, reckoning; ..."}]
  },
  {
    "word": "λογος",
    "language": "grc",
    "source": "cltk",
    "morphology": {"lemma": "λογος", "pos": "noun", "features": {"case": "nom", "number": "sing", "gender": "m"}}
  }
]
```

### Sanskrit (`heritage`, `cdsl`)
```json
[
  {
    "word": "agni",
    "language": "san",
    "source": "heritage",
    "definitions": [{"definition": "fire; Agni (deity)", "pos": "noun", "citations": [], "source_ref": null}],
    "morphology": {"lemma": "agni", "pos": "noun", "features": {"case": "nom", "number": "sing", "gender": "m"}}
  },
  {
    "word": "agni",
    "language": "san",
    "source": "cdsl",
    "definitions": [{"definition": "fire; sacrificial fire", "pos": "noun", "source_ref": "mw:217497"}],
    "dictionary_blocks": []
  }
]
```

## Display Rules (recommended)
- Keep entries separate per `source`; do not silently merge fields from different backends.
- Show `definitions` first, then `morphology`, then any `dictionary_blocks`/citations.
- If `foster_codes` exist, render them alongside morphology with human-friendly labels.
- Preserve `source_ref` when present; treat it as a stable reference for sense-level provenance.
- Do not assume `metadata` keys; guard access or surface them only for debugging.

## Inspecting Raw Evidence

To see backend output before adaptation:
- `devenv shell just -- cli tool diogenes search --lang lat --query lupus --output pretty`
- `devenv shell just -- cli tool heritage morphology --query agni --output pretty`

Use these when debugging schema mismatches or adapter changes.

## Future Additions

Semantic reduction (sense clustering and constants) and explicit epistemic modes (`open`, `skeptic`) are still in planning. When they land, this guide will add:
- Stable IDs for sense buckets/constants
- Expected ordering for learner-facing displays
- Links/citations surface rules
