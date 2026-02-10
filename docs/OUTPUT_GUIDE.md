# Output Guide (CLI & API)

This guide shows how to read the JSON returned by `langnet-cli query` or `/api/q`, with a focus on learner-first fields and backend-specific quirks.

## Shape at a glance
- Top level: an array of backend results (`diogenes`, `whitakers`, `heritage`, `cdsl`, etc.).
- Each entry has:
  - `head`: the headword or lemma.
  - `senses`: primary glosses/definitions. This is the best place for learners to start reading.
  - `references`: citations related to those senses; kept next to the senses to avoid duplication.
  - `metadata`: source tags (e.g., `dict_name`, `language`, `foster_codes`, `notes`) that describe the entry, not the learner-facing gloss.
  - `morphology` (when present): analysis of the queried form. Pedagogical details live in `morphology.features.foster`; raw backend keys live in `morphology.features.raw`.
  - `timing_ms`: backend latency, useful for debugging only.

## Reading morphology
- **Learner-first:** use `morphology.features.foster` to surface Foster functional grammar (e.g., “Naming Function”, “By-With Function”).
- **Technical:** use `morphology.features.raw` if you need the backend’s exact tags. We intentionally prune non-morphological keys (`tags`, `foster_codes`) from this raw section to avoid duplication.
- `form` carries the inflected form; `lemma` is the normalized headword.

## Sanskrit normalization
- Input is normalized via the Sanskrit Heritage pipeline. The response may include `canonical_slp1` and `canonical_tokens` to show the normalized form that downstream tools used.
- If the query looks like mangled SLP1, we de-prioritize it in candidate lists; prefer the `canonical_slp1` value when building links back to Heritage.

## Citations and references
- `references` are always attached to the entry they explain (no global duplication). Each reference may include `label`, `cts_urn`, and `source` (e.g., `L.` for Lexicographers).
- For Diogenes/Perseus data, citations can appear both in `references` and inside `senses` text; the structured list is the authoritative source.

## Backend specifics
- **Diogenes (Latin/Greek lexica):** `metadata` may include `tags` and `foster_codes` for the entry as a whole; morphology blocks omit those keys to keep structure predictable.
- **Whitaker’s Words (Latin morphology):** look at `morphology.features.foster` for pedagogy; `metadata.lexicon` indicates Whitaker’s source.
- **Heritage (Sanskrit morphology):** `morphology.analysis` carries Heritage’s own labels; we enrich with Foster functions where available.
- **CDSL (Sanskrit lexica):** `references` include Monier-Williams cross-references. We keep them deduplicated and adjacent to `senses`.

## Minimal client recipe
1. Take the first entry in the array matching your target backend.
2. Display `head`, then the `senses` list.
3. Show `references` under each sense (if present).
4. If morphology exists, render `morphology.features.foster` for teaching, and expose `morphology.features.raw` on demand for advanced users.
5. Ignore `timing_ms` unless debugging; it is not pedagogical.
