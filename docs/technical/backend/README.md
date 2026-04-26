# Backend Notes

Backend documents describe external tools and local adapters. They are operational references, not product contracts.

## Current Backends

- `diogenes-README.md` — Greek/Latin dictionary HTML from Diogenes.
- `whitakers-words-README.md` — Latin morphology and senses.
- `cologne-README.md` — CDSL/Sanskrit dictionary data.
- `engine-README.md` — current runtime wiring notes.
- `tool-capabilities.md` — rough capability matrix.

## Runtime Boundary

Backends feed the staged pipeline:

```text
fetch → extract → derive → claim
```

Do not build new feature logic directly against backend payloads if it can consume claims/triples instead.
