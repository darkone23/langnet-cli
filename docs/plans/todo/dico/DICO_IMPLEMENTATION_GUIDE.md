# DICO Implementation Guide (concise)

Goal: integrate the DICO French↔Sanskrit dictionary into langnet-cli.

## Steps
- Discovery: confirm search/query parameters (`lex=DICO`, encodings, max results) via Heritage CGI.
- Parser: add a DICO parser that extracts headword, Devanagari, and French definitions; ignore page refs/noise.
- Wiring: expose DICO as a backend option in the Sanskrit pipeline (query + tool path), behind a feature flag if needed.
- Tests: add fixtures for a few real entries (e.g., agni, yoga) and unit tests for the parser.
- Pedagogy: surface French glosses alongside Sanskrit transliteration; ensure encodings are normalized.
