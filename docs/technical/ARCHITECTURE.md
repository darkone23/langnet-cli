# Architecture

LangNet is currently a CLI-first staged runtime for classical-language lookup.

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

## Active CLI Commands

| Command | Role |
| --- | --- |
| `lookup` | quick backend-keyed lookup |
| `parse` | direct backend parser/debug command |
| `normalize` | query normalization inspection |
| `plan` | show planned tool calls |
| `plan-exec` | execute the full staged pipeline |
| `triples-dump` | inspect claim triples and evidence |
| `encounter` | show the current learner-facing reduced output |
| `databuild` | build offline data/indexes |
| `index` | inspect/manage storage indexes |

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
- Translation-cache projection for cached DICO/Gaffiot English gloss evidence.

Not implemented yet:

- Final learner-facing semantic output.
- First-class ASGI/API surface as a product contract.
- Passage-level interpretation.
- Broad semantic merging beyond exact buckets.

## Design Direction

The next architectural step is:

```text
claims/triples → Witness Sense Units → deterministic sense buckets → accepted learner-output examples
```

Do this before embeddings, broad hydration, or passage analysis.

Target design map: `docs/technical/design/TECHNICAL_VISION.md`.
