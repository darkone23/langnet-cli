# Unified Tool Integration into `/api/q`

## Objective
- Ensure all stabilized tool endpoints (diogenes, whitakers, heritage, cdsl, cltk) flow consistently into the unified `/api/q` aggregator used by `langnet-cli query`.

## Personas & Phases
- @architect: Align adapter design and data contracts for all sources.
- @coder: Implement adapter wiring and endpoint changes.
- @auditor: Validate data integrity, edge cases, and security.

## Scope
- In scope: Adapter wiring, source presence in unified results, CLI query behavior, regression tests around `/api/q`.
- Out of scope: Backend tool behavior (already validated), new sources.

## Milestones
1) **Adapter design** (@architect): Document expected source keys and required fields per tool in unified entries.
2) **Implementation** (@coder):
   - Wire missing sources into `/api/q` (ensure diogenes/whitakers/heritage/cdsl/cltk all appear when available).
   - Normalize metadata and strip non-pedagogical/noisy fields.
3) **Validation** (@coder/@auditor):
   - Run `just fuzz-compare` and confirm `source_present=true` for canonical sources.
   - Spot-check pedagogical usefulness on sample words (lat lupus, grc logos, san agni).
4) **Tests** (@coder):
   - Add regression tests around `/api/q` to assert source presence and basic field shapes.
5) **Review** (@auditor): Verify no fabricated fields (e.g., confidence) and no leakage of raw HTML.

## Deliverables
- Updated adapters/unified query to include all tool sources.
- Test coverage for `/api/q` source presence.
- Validation artifacts (fresh fuzz-compare summary).

## Risks & Mitigations
- Startup latency / warmup: keep CLTK/spaCy warmup in place; document readiness expectations.
- Payload drift: keep optional fields guarded and avoid fabricated values.

## Validation Checklist
- `just fuzz-compare` clean run with `source_present` for all primary tools.
- Manual `/api/q` spot-checks match pedagogical expectations.
