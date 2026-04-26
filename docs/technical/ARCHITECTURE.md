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
lookup output / evidence inspection / future semantic reduction
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

Not implemented yet:

- Runtime semantic reduction into sense buckets.
- Final learner-facing semantic output.
- First-class ASGI/API surface as a product contract.
- Passage-level interpretation.

## Design Direction

The next architectural step is:

```text
claims/triples → Witness Sense Units → deterministic sense buckets → learner output
```

Do this before embeddings, broad hydration, or passage analysis.
