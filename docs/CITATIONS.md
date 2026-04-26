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
| Perseus Digital Library | Text/citation source data used by Diogenes and CTS work | external corpus data may be needed for indexing |

## Runtime Dependencies

Key Python/runtime dependencies include:

- Click for CLI commands.
- DuckDB for local indexes and caches.
- cattrs/orjson for effect serialization.
- BeautifulSoup/Lark/parser utilities for backend extraction.
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

The canonical evidence schema is `docs/technical/predicates_evidence.md`.

## Licensing Note

This document is not legal advice. Before redistributing bundled datasets or generated indexes, verify each upstream source’s license and attribution requirements.
