# Architecture

LangNet is currently a CLI-first staged runtime for classical-language lookup,
reader exploration, local dictionary indexes, paradigm lookup, and
translation-cache inspection. The web product uses a SvelteKit adapter that
executes CLI JSON commands; there is no current Python ASGI `/api/q` product
contract in this checkout.

## Runtime Shape

```text
CLI
  ↓
normalization
  ↓
tool planning
  ↓
staged execution
  ↓
raw responses → extractions → derivations → claims/triples
  ↓
lookup output / evidence inspection / exact WSU reduction / encounter output
```

## Main Entry Points

- `src/langnet/cli.py` — Click CLI.
- `src/langnet/planner/core.py` — creates language-specific tool plans.
- `src/langnet/execution/executor.py` — executes staged plans.
- `src/langnet/execution/handlers/` — backend-specific extract/derive/claim functions.
- `src/langnet/storage/` — DuckDB-backed indexes and caches.
- `webapp/src/routes/api/` — SvelteKit API adapter routes that call CLI JSON
  commands for the browser UI.

## Active CLI Commands

| Command | Role |
| --- | --- |
| `lookup` | unified dictionary lookup across available sources |
| `encounter` | learner-facing source-backed word encounter output |
| `reader` | explore locally indexed reader corpora, catalog data, passages, and search |
| `word-index` | inspect local dictionary headword indexes and sections |
| `paradigm` | fetch source-backed inflection tables |
| `paradigm-resolve` | explain how a surface form resolves to paradigm requests |
| `translation-cache` | inspect and clear DICO/Gaffiot/Bailly translation-cache rows |
| `translation-warm` | populate French-source lexicon translation cache rows |
| `doctor` | check local CLI assumptions, schemas, cache, translation dependencies, and optional binaries |
| `langs` | list supported language codes and aliases |
| `tools` | list accepted `tool_filter` values and tool metadata |
| `entry-analyze` | inspect one raw dictionary entry for glosses, references, and source segments |
| `bailly-db-lookup` | inspect PDF-derived Bailly DuckDB entries |
| `bailly-xml-audit` | audit generated Bailly per-page Poppler XML |
| `bailly-xml-extract` | extract Bailly Poppler XML pages to structural entries |
| `lewis-1890-db-lookup` | inspect local Lewis 1890 DuckDB entries |
| `parse` | direct backend parser/debug command |
| `normalize` | query normalization inspection |
| `plan` | show tool calls before execution |
| `plan-exec` | execute the full staged pipeline |
| `triples-dump` | inspect claim triples and evidence |
| `word-of-day` | emit learner recommendation cards with optional encounter probe summaries |
| `recommend-words` | request several learner recommendation cards on demand |
| `reader-eval` | score reader fixtures against encounter reductions |
| `databuild` | build offline data/indexes |
| `index` | inspect/manage storage indexes |

Routine examples should use the repository wrapper:

```bash
just cli lookup lat lupus --output json
just cli reader catalogs --output json
just cli word-index sections lat --output json
just cli paradigm san putra --kind declension --gender Mas --output json
just cli translation-cache status --output json
just cli doctor --output json
```

## SvelteKit Adapter Routes

The web adapter lives under `webapp/src/routes/api/`:

| Route | Current role |
| --- | --- |
| `/api/search` | lookup/encounter-style search bridge |
| `/api/reader` | reader catalog, work, passage, and search modes |
| `/api/word-index` | word-index sections and entries |
| `/api/paradigm` | source-backed paradigm lookup |
| `/api/translation-cache` | web clear/retry adapter for translation-cache rows; CLI handles status inspection |
| `/api/motd` | message-of-the-day/recommendation payloads |

These routes are adapter code around CLI JSON and local files. They are not a
separate Python product API surface.

## Staged Effects

The execution model uses dataclass effects:

- `RawResponseEffect`
- `ExtractionEffect`
- `DerivationEffect`
- `ClaimEffect`

Handlers should preserve provenance across stages. Claims and triples are the stable input for semantic reduction.

## Backends

| Backend | Languages | Current use |
| --- | --- | --- |
| Whitaker's Words | Latin | morphology, lemmas, senses |
| Diogenes | Latin, Greek | dictionary entries, citations, morphology chunks |
| CLTK | Latin, Greek | supplemental lemma/pronunciation/lexicon data |
| spaCy | Greek where configured | supplemental NLP claims |
| Sanskrit Heritage | Sanskrit | morphology |
| CDSL | Sanskrit | dictionary senses and source references |
| Local DICO | Sanskrit | French source glosses from Heritage DICO entries |
| Local Gaffiot | Latin | French source glosses for Latin entries |
| Local Bailly | Greek | French source glosses from PDF-derived Bailly entries |
| Local Lewis 1890 | Latin | English dictionary entries from local DuckDB |
| CTS index | Greek/Latin reader/citation data | citation and reader metadata hydration |

Live backend access requires local external services. Unit tests should use fixtures.

## Claims and Triples

Claims are normalized assertions from backend derivations. Many claims include triples:

```json
{
  "subject": "lex:lupus",
  "predicate": "has_sense",
  "object": "sense:lex:lupus#...",
  "metadata": {
    "evidence": {
      "source_tool": "diogenes",
      "call_id": "...",
      "response_id": "...",
      "extraction_id": "...",
      "derivation_id": "...",
      "claim_id": "..."
    }
  }
}
```

Rules:

- Do not encode provenance in anchor IDs.
- Attach evidence in metadata.
- Use scoped interpretation anchors for ambiguous forms.
- Treat claims/triples as projections over raw payloads, not replacements.

Canonical reference: `docs/technical/predicates_evidence.md`.

## Storage

DuckDB indexes store normalized queries, tool plans, raw responses, extractions, derivations, claims, and provenance. Handler versions are used to invalidate stale derived/indexed data.

Separate local stores also support source products, including DICO, Gaffiot,
Bailly, Lewis 1890, Whitaker's, Diogenes, CDSL, CTS URN metadata, reader
catalog DuckDB files, reader search Lance indexes, word-index stores, and the
translation cache.

Detailed reference: `docs/storage-schema.md`.

## Current Boundary

Implemented:

- CLI lookup and parser commands.
- Tool planning.
- Staged execution.
- Claim/triple projection.
- Fixture-backed claim contract tests for core handlers.
- Runtime exact Witness Sense Unit reduction into buckets.
- First learner-facing `encounter` output with Sanskrit Heritage analysis rows.
- Reader catalog, passage, discovery/search, and word-index CLI surfaces backed
  by local data stores.
- Source-backed `paradigm` and `paradigm-resolve` CLI surfaces, plus the
  SvelteKit `/api/paradigm` adapter.
- Translation-cache projection for cached DICO/Gaffiot/Bailly English gloss evidence.
- Explicit `encounter --translation-mode auto` cache-miss population for
  DICO/Gaffiot/Bailly translations.
- Word-list DICO/Gaffiot/Bailly translation-cache warming through
  `translation-warm`.
- Compact learner glosses above full source dictionary entries for several
  source families, including DICO-aware handling for long Sanskrit entries.
- Source-headword-aware encounter ranking for exact dictionary hits.
- Schema-backed `word-of-day` / `recommend-words` recommendation output.
- SvelteKit API adapter routes for search, reader, word-index, paradigm,
  MOTD, and translation-cache workflows.

Not implemented yet:

- Release-quality learner-facing semantic output.
- Complete typed source segmentation for all long LSJ/Lewis/Gaffiot/DICO/CDSL
  entries.
- Reader-form/headword ranking for remaining hard cases.
- First-class Python ASGI/API surface as a product contract.
- Passage-level interpretation.
- Broad semantic merging beyond exact buckets.

## Design Direction

The next architectural step is:

```text
claims/triples → Witness Sense Units → deterministic sense buckets → compact learner display
```

Do this before embeddings, broad hydration, or passage analysis.

Target design map: `docs/technical/design/TECHNICAL_VISION.md`.
