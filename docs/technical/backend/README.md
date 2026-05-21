# Backend Notes

Backend documents describe external tools, local DuckDB-backed dictionaries,
reader/index stores, and the adapter paths that expose them. They are
operational references, not standalone product contracts.

## Current Backends And Stores

| Area | Current role | Notes |
| --- | --- | --- |
| Diogenes | Greek/Latin dictionary, morphology, citations, and inflection tables | `diogenes-README.md` |
| Whitaker's Words | Latin morphology and compact lexical facts | `whitakers-words-README.md` |
| CDSL | Sanskrit MW/AP90 dictionary entries | `cologne-README.md` |
| DICO | Sanskrit-French dictionary entries | Built by `just cli-databuild dico ...`; translation-cache capable |
| Gaffiot | Latin-French dictionary entries | Built by `just cli-databuild gaffiot ...`; translation-cache capable |
| Bailly | Greek-French dictionary entries from PDF/XML extraction | Inspect with `bailly-*` CLI commands; translation-cache capable |
| Lewis 1890 | Latin-English dictionary entries | Inspect with `lewis-1890-db-lookup` |
| CTS index | citation and reader metadata hydration | Built/consumed as local DuckDB data |
| Reader stores | catalog, works, passages, metadata overlays, search index | Exposed by `reader` and `/api/reader` |
| Word-index stores | dictionary headword sections and entries | Exposed by `word-index` and `/api/word-index` |
| Translation cache | cached English projections for French-source lexica | Exposed by `translation-cache` and `/api/translation-cache` |

## Companion Docs

- `engine-README.md` — runtime wiring and SvelteKit adapter note.
- `tool-capabilities.md` — current `just cli tools --output json` catalog
  summary.
- `paradigm-generation-limitations.md` — source-backed paradigm behavior.
- `abbr-latin.md` — source/reference-only Latin abbreviation list.

## Runtime Boundary

Backends feed the staged pipeline:

```text
fetch → extract → derive → claim
```

CLI JSON is the stable backend contract for the SvelteKit adapter. Do not build
new feature logic directly against backend payloads if it can consume
claims/triples, reader catalog/search JSON, word-index JSON, paradigm JSON, or
translation-cache JSON instead.
