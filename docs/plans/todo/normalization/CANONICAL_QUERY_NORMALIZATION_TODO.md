# Canonical Query Normalization – Feature (Todo)

*(Copied from the previous active plan – retained for reference)*

---

## Current Status
The core normalization system is implemented and all tests pass, but **bare‑ASCII query enrichment** across languages is still missing.

## Missing Capability
- Detect language of ambiguous ASCII queries (Sanskrit, Greek, Latin).
- Enrich these queries using external resources (Heritage Platform for Sanskrit, CLTK for Latin/Greek) to generate proper encoded forms.
- Integrate enrichment into the `NormalizationPipeline` so that queries with no direct matches can be resolved.

## Tasks (see also `ASCII_ENRICHMENT_TODO.md`)
- ❌ Extend `detect_encoding()` or create a new language‑detector for Greek and Latin ASCII.
- ❌ Implement enrichment pipelines for each language.
- ❌ Update pipeline to fallback to enriched forms.
- ❌ Add comprehensive tests for ambiguous ASCII inputs.

*The rest of the original plan (completed components) is omitted for brevity.*
