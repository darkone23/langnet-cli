# Technical Documentation

Use this directory for implementation-facing references. The current product
surface is the Click CLI plus SvelteKit API adapter routes; local DuckDB stores
support dictionaries, reader corpora, word indexes, CTS metadata, and the
translation cache.

## Current Maps

- `ARCHITECTURE.md` — current CLI/runtime architecture, SvelteKit adapter
  routes, storage boundary, and implemented/future surfaces.
- `backend/README.md` — backend and local data-source map for Diogenes,
  Whitaker's Words, CDSL, DICO, Gaffiot, Bailly, Lewis 1890, CTS indexes,
  reader stores, word-index stores, and the translation cache.
- `design/README.md` — design notes, clearly separated into implemented
  runtime contracts and future design constraints.

## Claims And Data Contracts

- `predicates_evidence.md` — canonical claim/triple predicates, current source
  tools, and evidence fields.
- `predicates_evidence.json` — machine-readable companion vocabulary.
- `semantic_triples.md` — graph-model notes for claims and downstream
  reduction.
- `grammar-concept-registry.md` — planned data contract for mapping
  source-backed morphology to Foster and traditional grammar concepts.
- `grammar-source-anchors.md` — canonical grammar works, local CTS/CTSv2 reader
  anchors, and external research grounding for Greek, Latin, and Sanskrit
  grammar-source evidence.
- `morphology-projection-audit.md` — current coverage matrix for morphology
  projectors feeding the learner candidate path.
- `../storage-schema.md` — staged-effect, source-index, reader, word-index, CTS,
  and translation-cache DuckDB storage guide.
- `../handler-development-guide.md` — handler stage/versioning guide.

## Runtime And Source Notes

- `backend/tool-capabilities.md` — current `tools` catalog summary.
- `backend/engine-README.md` — runtime wiring and SvelteKit bridge note.
- `backend/diogenes-README.md` — Diogenes dictionary/paradigm backend.
- `backend/whitakers-words-README.md` — Whitaker's Words backend.
- `backend/cologne-README.md` — CDSL/Sanskrit backend.
- `backend/paradigm-generation-limitations.md` — paradigm resolver/fetch
  limitations and graceful degradation.
- `backend/abbr-latin.md` — historical/source reference only; not a live code
  API.
- `opencode/` — OpenCode/OpenRouter persona workflow notes.

## Maintenance Rules

- Keep `ARCHITECTURE.md` aligned with code that exists now.
- Keep speculative designs under `design/`.
- Keep historical implementation reports in `docs/archive/`, not here.
- When predicates or evidence fields change, update `predicates_evidence.md` and the related tests.
