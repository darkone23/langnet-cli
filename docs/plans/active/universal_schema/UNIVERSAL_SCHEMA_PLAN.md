# Universal Schema Plan

## Goal
Create a single, language‑agnostic JSON‑compatible data model that all back‑ends (Heritage, CDSL, Whitaker’s, etc.) must return. The model will include:
- `DictionaryEntry` – the top‑level container for a queried term.
- `Sense` – a specific meaning, with part‑of‑speech, definition, example sentences, and **sense‑level citations**.
- `Citation` – source reference (URL, title, author, page, optional excerpt).
- `MorphologyInfo` – optional field for morphological parsing results (lemmas, stems, grammar tags).

## Tasks
1. **Define dataclasses** in `src/langnet/schema.py` mirroring the spec.
2. **Document the schema** in `docs/UNIVERSAL_SCHEMA.md` with examples for each language.
3. **Update BaseBackendAdapter** (`src/langnet/backend_adapter.py`) to return the new dataclasses.
4. **Write unit tests** ensuring adapters correctly produce `DictionaryEntry` objects.
5. **Add JSON serialization** utilities (using `cattrs` or `orjson`).
6. **Integrate with existing pipelines** – modify normalization and heritage modules to emit the new model.
7. **Review and move to completed** once all back‑ends conform.

## Acceptance Criteria
- All existing tests pass after migration.
- New tests confirm presence of `sense.citations` for every sense.
- The API `/api/q` returns objects that can be `orjson.dumps` without custom encoders.
- Documentation clearly shows how to extend the schema for future back‑ends.
