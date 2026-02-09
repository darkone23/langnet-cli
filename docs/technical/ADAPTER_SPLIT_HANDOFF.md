# Adapter Split Handoff (in-progress)

Context: Split `src/langnet/backend_adapter.py` into per-backend modules under `src/langnet/adapters/`. Refactor is now landed and the full test suite is green.

## Current state
- New adapter modules: `src/langnet/adapters/{base,diogenes,whitakers,cltk,cdsl,heritage,registry}.py`.
- Shim kept for legacy imports: `src/langnet/backend_adapter.py` re-exports adapters and registry.
- Engine now imports `LanguageAdapterRegistry` from `langnet.adapters.registry`.
- Universal schema adapters now emit full `DictionaryEntry` objects (definitions, morphology, dictionary blocks) for all backends.
- Registry composes sources per language (`diogenes`/`spacy|cltk` for Greek, `diogenes|whitakers|cltk` for Latin, `heritage|cdsl|cltk` for Sanskrit).
- Test status: `just test` and `just test-fast` both pass (444 and 418 tests respectively). Fuzz harness should be rerun with a running server to refresh artifacts.

## What changed
- Diogenes adapter now builds `DictionaryBlock` objects from matching reference blocks and surfaces morphology from Perseus headers as `MorphologyInfo`.
- Whitaker’s adapter parses `wordlist`/`results` to populate definitions from senses and morphology from codeline/term facts, carrying Foster codes.
- CLTK adapter handles morphology-only spaCy payloads, Lewis & Short lookup, and generic CLTK results; all emit `DictionaryDefinition`/`MorphologyInfo`.
- CDSL adapter builds definitions from `meaning`/`data` and populates morphology features when present.
- Heritage adapter combines morphology + dictionary analyses into definitions and `MorphologyInfo`, retaining lemma/pos and grammar tags in metadata.
- Registry now also consumes Greek `spacy` key (mapped through CLTK adapter) to keep spaCy morphology in results.

## Follow-ups / nice-to-have
- Citations: Diogenes blocks currently preserve raw citation maps but not normalized `Citation` objects; consider enriching from CTS URNs for downstream rendering.
- Fuzz harness: rerun `just fuzz-query` with server running and refresh `examples/debug/fuzz_results_query/` snapshots.
- Performance: spaCy/CLTK results are passed through the CLTK adapter; if adding new morphology sources, reuse that path or add a small wrapper.
- Observability: adapters now embed minimal metadata; extend with backend timing/error hints if needed for logs.

## Quick commands
- Fast tests: `just test-fast` (skips integration-tagged tests).
- Full suite: `just test`.
- Fuzz: `just fuzz-query` (server must be running; restart server after backend changes via `just restart-server`).
