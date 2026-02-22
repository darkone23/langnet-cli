# Tool Triples Handoff: Whitaker/Diogenes/CLTK (LAT) — Current State & Next Steps

**Scope**: Latin tool flow (Diogenes, Whitaker, CLTK) producing extraction-derived triples/facts with provenance. This is a checkpoint handoff for the next implementer.

## What’s implemented
- Executor runs Diogenes + Whitaker + CLTK end-to-end for Latin (`just cli plan-exec lat <word> --no-stub-handlers --no-cache`).
- Handlers:
  - **Diogenes**: parses HTML into lemmas/chunks; payload includes `raw_html` + parsed blocks; claims are still `has_lemmas` (no triple projection yet).
  - **Whitaker**: parses output into `wordlist` + `raw_text`; claims include `triples` (POS/morph/senses) but currently mix headword/form subjects without `inflection_of` links; raw payload retained.
  - **CLTK**: fetch client + handler; payload has lemma/IPA/Lewis lines; claims are generic `has_lemmas` (no triple projection yet).
- Semantic triples design doc added: `docs/technical/semantic_triples.md` (clean subjects/objects, evidence alongside).
- Flat-fact/scoped interpretation model captured in `docs/plans/active/tool-fact-indexing.md` (anchors: form/interp/lex/sense; predicates; provenance rules).

## Known gaps / priorities
1) **Whitaker triple projection**: implement scoped facts per the flat-facts doc:
   - Anchors: `form:<surface>`, `interp:form:<surface>→lex:<lemma>#<pos>`, `lex:<lemma>#<pos>`, `sense:<lex>#<sense-key>`.
   - Triples/facts: `form has_interpretation interp`; `interp pos ...` + `realizes_lexeme`; `lex has_sense sense`; `sense gloss ...`; `variant_form`; morphological features in qualifiers.
   - Evidence in metadata (`source_json`/`evidence`), not in IDs. Ensure surface form is exposed (e.g., `has_form` literal) if opaque form ids are used.
   - Add `inflection_of` from forms to headwords; stop mixing headword/form subjects in POS triples.
2) **Diogenes projection**: add triples for morph (forms + tags), dictionary senses, citations, with anchors per above; keep `raw_html`.
3) **CLTK projection**: form→lemma (`inflection_of`), lemma `has_pronunciation`, lemma `has_sense` (Lewis line), anchors per model.
4) **ID/predicate/evidence conventions**: settle a deterministic ID policy, shared predicate constants, and a minimal evidence schema (tool, response_id, call_id, raw_ref/raw_blob_ref).
5) **Deduplication/ordering**: define uniqueness (s,p,o,evidence) and ensure claims carry both `triples` and raw payloads.

## Quick CLI harness for inspection
Use this snippet to run a plan and print triples per tool:

```bash
# Run end-to-end (Diogenes + Whitaker + CLTK), no cache, no stubs
just cli plan-exec lat <word> --no-stub-handlers --no-cache
```

Or, programmatically extract triples for a word:

```bash
python - <<'PY'
from pathlib import Path
import duckdb
from query_spec import LanguageHint
from langnet.cli import _create_normalization_service, _build_exec_clients, NormalizeConfig
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.execution.executor import execute_plan_staged
from langnet.execution.registry import default_registry
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.plan_index import PlanResponseIndex, apply_schema

word = "ea"
norm_cfg = NormalizeConfig(
    diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
    heritage_base="http://localhost:48080",
    db_path=None,
    no_cache=True,
    output="pretty",
)
service = _create_normalization_service(norm_cfg)
normalized = service.normalize(word, LanguageHint.LANGUAGE_HINT_LAT)
planner = ToolPlanner(
    PlannerConfig(
        diogenes_endpoint=norm_cfg.diogenes_endpoint,
        diogenes_parse_endpoint=None,
        heritage_base_url=norm_cfg.heritage_base,
        heritage_max_results=5,
        include_whitakers=True,
        max_candidates=3,
    )
)
candidate = planner.select_candidate(normalized.normalized)
plan = planner.build(normalized.normalized, candidate)

conn = duckdb.connect(database=":memory:")
apply_schema(conn)
raw_index = RawResponseIndex(conn)
extraction_index = ExtractionIndex(conn)
derivation_index = DerivationIndex(conn)
claim_index = ClaimIndex(conn)
plan_response_index = PlanResponseIndex(conn)

registry = default_registry(use_stubs=False)
clients = _build_exec_clients(plan, norm_cfg.diogenes_endpoint, use_stubs=False)

result = execute_plan_staged(
    plan=plan,
    clients=clients,
    registry=registry,
    raw_index=raw_index,
    extraction_index=extraction_index,
    derivation_index=derivation_index,
    claim_index=claim_index,
    plan_response_index=plan_response_index,
    allow_cache=False,
)

for claim in result.claims:
    print(f"TOOL={claim.tool} SUBJECT={claim.subject} PRED={claim.predicate}")
    val = claim.value if isinstance(claim.value, dict) else {}
    triples = val.get("triples") if isinstance(val, dict) else None
    if triples:
        for t in triples[:5]:
            print("  triple", t)
    if "raw_text" in val:
        print("  raw_text_len", len(val["raw_text"]))
    if "raw_html" in val:
        print("  raw_html_len", len(val["raw_html"]))
PY
```

## Files to read first
- `docs/technical/semantic_triples.md` — clean subjects/objects; evidence in metadata; triple+metadata shape.
- `docs/plans/active/tool-fact-indexing.md` — flat-fact/anchor/predicate rules; outstanding ID/predicate/evidence decisions.
- `docs/handoff/tool-execution-integration.md` — executor/registry context.

## Relevant docs map
- Execution + registry
  - `docs/handoff/tool-execution-integration.md`, `docs/handoff/tool-executor.md`, `docs/handoff/tool-plan-exec-handoff.md`
  - `docs/plans/active/infra/tool-plan-execution-to-claims.md`
- Triples/facts design
  - `docs/technical/semantic_triples.md` (triple+metadata model)
  - `docs/plans/active/tool-fact-indexing.md` (flat facts, anchors, predicates, gaps)
  - `docs/technical/design/tool-fact-architecture.md`, `docs/technical/design/tool-response-pipeline.md`, `docs/technical/design/mermaid/tool-fact-flow.md`
  - `docs/technical/triples_txt.md` (additional triples notes)
  - `docs/upstream-docs/semantics/index.html` (RDF primer/reference)
- Tool-specific refs
  - `docs/technical/backend/whitakers-words-README.md`
  - `docs/technical/backend/diogenes-README.md`
- Semantic reduction context
  - `docs/plans/active/semantic-reduction/SEMANTIC_REDUCTION_README.md`
  - `docs/plans/active/semantic-reduction/semantic-reduction-gaps.md`

## Suggested next steps for implementer
1) Implement Whitaker triple/fact emission per anchor/predicate rules; add `inflection_of` and scope senses to headwords; keep raw payload.
2) Mirror the projection for Diogenes and CLTK.
3) Define and publish predicate constants + evidence schema; add a `has_form` literal for forms when using opaque ids.
4) Add a small CLI subcommand (or flag) to dump triples for a word (using the snippet above as the core).
