# Tool Plan DAG (Stage 0 → 1 Bridge)

**Status**: Draft  
**Owner**: Planning/Core team  
**Date**: 2026-02-XX  
**Scope**: How to turn a `NormalizedQuery` into a ToolPlan that covers raw fetch + extraction + derivation (no execution yet).

## Goal

Produce accurate, reproducible ToolPlans that mirror the legacy engine call flows while honoring the new staged pipeline:

```
NormalizedQuery → ToolPlan (calls + parse/derive tasks) → Execute → Effects → Parse → Derive
```

We do **not** re-do normalization. We focus on planning the DAG of tool calls and downstream parse/derive tasks per language.

## Inputs

- **Single canonical candidate** from `NormalizedQuery.candidates`: One precomputed lemma with resolved form (e.g., SLP1 for Sanskrit, betacode for Greek).
- Language hint (SAN | GRC | LAT).
- Tool capabilities (diogenes, heritage, cdsl, whitakers, cltk).
- Parser/deriver inventory (HTML/XML/line parsers from `codesketch`).

**Important**: Planning operates on one specific canonical lemma. Do not plan calls that resolve ambiguity (e.g., diogenes `word_list`, morphology parsers that return multiple candidates). Normalization is complete before planning begins.

## Desired Outputs

- `ToolPlan` that includes:
  - **Fetch nodes**: HTTP/subprocess calls with params derived from canonical candidates.
  - **Parse nodes**: tool-specific extraction tasks (HTML → blocks, XML → entries, text → tagged lines).
  - **Derive nodes**: fact builders (morph facts, sense facts, citation facts).
  - **Claim nodes**: map derivations into semantic claims (stage 5 placeholder).
  - **Dependencies**: explicit edges `fetch → parse → derive`.
  - **Stage tags**: each node labelled fetch|extract|derive|claim for caching/parallelism.
- Stable hashing (excluding volatile fields) for caching.

## Language-Specific Call Graphs (mirror codesketch)

**Critical Clarification**: Each plan is built for ONE precomputed canonical lemma. The input is a single candidate from `NormalizedQuery.candidates` with an already-resolved canonical form (e.g., SLP1 for Sanskrit, betacode for Greek). Do NOT plan calls that resolve ambiguity or perform morphological analysis to find the lemma—normalization is complete before planning begins.

- **Greek (GRC)**  
  Fetch: diogenes `word_list` (lookup canonical form directly—no ambiguity resolution needed), diogenes `parse` (morph + citations for the specific canonical form).  
  Parse: diogenes HTML → entry blocks; parse tables → morph records.  
  Derive: dictionary facts (gloss blocks), morph facts, citation refs (CTS hydration is separate tool call later).

- **Latin (LAT)**  
  Fetch: diogenes `word_list` (lookup canonical form directly), whitakers (text lines for the specific lemma), cltk IPA (optional).  
  Parse: diogenes HTML parse, whitakers line parsers (senses/codes/facts).  
  Derive: morph facts, gloss facts from whitakers, IPA attachment.

- **Sanskrit (SAN)**  
  Fetch: heritage `sktreader` (HTML, keyed on SLP1 canonical form), heritage morphology (if available), cdsl (XML) keyed on SLP1, CLTK optional.  
  Parse: heritage HTML morphology parser, cdsl XML entry splitter.  
  Derive: morph facts (gender/case/number), sense facts from CDSL entries, canonical form confirmation.

## Plan Phases & Tasks

### Phase 1 — DAG shape & metadata (@architect @coder)
- [ ] Enumerate fetch nodes per language with concrete endpoints/params (use normalized candidates; cap breadth).
- [ ] Define parse nodes (virtual tools) per fetch:
  - diogenes_html_parse, diogenes_morph_parse
  - whitakers_line_parse
  - heritage_html_parse (morphology)
  - cdsl_xml_parse
- [ ] Define derive nodes per parse:
  - diogenes_dict_derive, diogenes_morph_derive, diogenes_citation_refs
  - whitakers_fact_derive
  - heritage_morph_derive
  - cdsl_sense_derive
- [ ] Encode dependencies (fetch → parse → derive) in ToolPlan or a companion structure.

### Phase 2 — Planning logic (@coder)
- [ ] Implement planner logic that generates fetch nodes for ONE specific canonical candidate, then auto-attaches parse/derive nodes.
- [ ] Ensure deterministic call_ids and stable plan_hash (exclude volatile fields).
- [ ] Respect per-language tool availability toggles (config-driven).
- [ ] **Clarify**: Planning receives a single pre-resolved lemma—no word_list, parse, or morphology calls needed to resolve the canonical form.

### Phase 3 — Fidelity vs legacy (@auditor @sleuth)
- [ ] Validate planned params against codesketch behaviors (diogenes params, heritage t=VH/max, cdsl SLP1).
- [ ] Confirm parse/derive node coverage matches existing extractors.

### Phase 4 — Tests (@coder)
- [ ] Fixture-based plan tests for SAN/GRC/LAT that assert DAG shape:
  - Presence of fetch + parse + derive nodes
  - Correct params/ordering
  - Dependencies wired
- [ ] Hash stability test (same input → same plan_hash; different plan_id).

### Phase 5 — Docs (@scribe)
- [ ] Update `docs/technical/design/query-planning.md` with DAG examples.
- [ ] Add CLI guidance for inspecting plans (pretty/json) per language.

## Open Questions

- Should parse/derive tasks live in `ToolPlan` proper or a nested `PipelinePlan`? (lean: keep in ToolPlan with `tool` names like `diogenes.parse_html` to reuse executor).
- How to express CTS hydration as a follow-up tool call vs. derive step? (likely separate fetch once citations are extracted).
- How to cap candidate explosion for Greek word_list while preserving top matches?

## Definition of Done

- `ToolPlan` instances include fetch + parse + derive nodes with dependencies per language.
- Plan hash stable; IDs deterministic; tests cover SAN/GRC/LAT plan shapes.
- Docs updated; CLI shows full planned DAG (fetch/parse/derive).
