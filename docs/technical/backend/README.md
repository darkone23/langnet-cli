# Backend Documentation

Backend-specific technical references for langnet-cli. These files cover the language engine and each upstream backend. Status is included to clarify whether they are reference-only or still evolving.

## Files
- **engine-README.md** — Core language processing engine overview (reference).
- **diogenes-README.md** — Diogenes/Perseus integration details (reference; revisit if Diogenes APIs change).
- **cologne-README.md** — Cologne Digital Sanskrit Dictionary interface and tooling (reference).
- **whitakers-words-README.md** — Whitaker's Words parser and helpers (reference).
- **tool-capabilities.md** — What each backend is trusted for and expected to emit as claims/witnesses (planned).
- **abbr-latin.md** — Latin grammar abbreviation map (Cassell-derived) for parsing/normalization.

## Notes
- Adapter split and universal schema are now stable; extend adapters directly in `src/langnet/adapters/` and keep tests/fuzz in sync.
- When altering backend behavior, update the relevant README here and run `just test` (full) plus `just fuzz-query` with the server running.
