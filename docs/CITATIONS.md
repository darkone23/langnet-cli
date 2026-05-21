# Citations and External Sources

LangNet depends on external classical-language tools and datasets. This page records what they are used for and what developers should expect operationally.

## Core Sources

| Source | Use | Operational note |
| --- | --- | --- |
| Sanskrit Heritage Platform | Sanskrit morphology and dictionary-style analysis | run locally at `localhost:48080` |
| Diogenes | Greek/Latin lexica from Perseus data | run locally at `localhost:8888` |
| Whitaker's Words | Latin morphology and dictionary lookup | binary expected at `~/.local/bin/whitakers-words` |
| CLTK | Classical-language utilities and supplemental data | needs model data; uses `CLTK_DATA`, writable `~/cltk_data`, or project cache fallback |
| CDSL | Sanskrit dictionary data, especially Monier-Williams/AP90 | local DuckDB data built by project tooling |
| DICO | Sanskrit-French dictionary entries | local DuckDB source built by project tooling; translation-cache capable |
| Gaffiot | Latin-French dictionary entries | local DuckDB source built by project tooling; translation-cache capable |
| Bailly | Greek-French dictionary entries | local DuckDB source derived from PDF/XML extraction; translation-cache capable |
| Lewis 1890 | Latin-English dictionary entries | local DuckDB source built from CLTK/upstream data |
| CTS/reader corpora | reader works, passages, CTS URNs, metadata overlays, and search indexes | local reader/data builds; source attribution must remain visible |
| Perseus Digital Library | Text/citation source data used by Diogenes and CTS work | external corpus data may be needed for indexing |

## Runtime Dependencies

Key Python/runtime dependencies include:

- Click for CLI commands.
- DuckDB for local indexes and caches.
- cattrs/orjson for effect serialization.
- BeautifulSoup/Lark/parser utilities for backend extraction.
- aisuite/OpenRouter-compatible configuration for optional translation-cache
  population.
- SvelteKit and Bun for the web adapter under `webapp/`.
- Ruff and ty for formatting, linting, and type checking.
- nose2 for tests.

See `pyproject.toml`, `devenv.nix`, and lock files for authoritative dependency versions.

## Provenance Policy

External data should remain traceable. Handler outputs should preserve:

- tool name
- call ID
- response ID
- extraction ID
- derivation ID
- claim ID
- source entry reference where available
- raw blob reference where available
- translation-cache derivation metadata when English glosses are derived from
  DICO, Gaffiot, or Bailly source entries
- reader catalog/search and CTS source attribution when reader passages or
  citations are shown

The canonical evidence schema is `docs/technical/predicates_evidence.md`.

## Licensing Note

This document is not legal advice. Before redistributing bundled datasets or generated indexes, verify each upstream source’s license and attribution requirements.
