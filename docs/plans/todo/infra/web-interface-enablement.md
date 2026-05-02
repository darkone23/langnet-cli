# Web Interface Enablement Plan

**Status:** todo  
**Date:** 2026-05-01  
**Feature Area:** infra / learner interface

## Purpose

Prepare LangNet for a small web interface without prematurely rewriting the
runtime. The near-term web service can call `langnet-cli` as a subprocess and
render structured JSON, roughly like CGI. That keeps the CLI contract central
while the learner-facing shape stabilizes.

## Target Architecture

Initial web path:

```text
browser
  -> thin web server endpoint
  -> langnet-cli encounter <lang> <term> <tool-filter> --output json
  -> structured JSON response
  -> client-side render
```

This path is acceptable if the subprocess boundary is explicit, timed out, and
returns stable machine-readable data. The web server should not scrape pretty
output.

## Phase 1: JSON Contract Hardening

**Owner persona:** @architect for contract shape, @auditor for edge cases,
@coder for tests.

Acceptance:

- `encounter --output json` includes:
  - schema version and request metadata;
  - sorted buckets and witnesses;
  - display-ready header, analysis rows, and meaning rows;
  - ranking explanations;
  - source refs and source-detail summaries;
  - translation-cache diagnostics;
  - warnings/errors as structured fields.
- Pretty output remains a rendering convenience, not a web/API contract.
- JSON snapshots cover at least one Latin, Greek, and Sanskrit query. Latin
  contract coverage currently asserts schema, request, analysis, meaning, and
  source-detail display fields.

## Phase 2: CLI JSON Reliability Before Gateway

**Owner persona:** @coder for implementation, @sleuth for timeout/error review.

Acceptance:

- Keep `langnet-cli encounter ... --output json` as the public boundary.
- Success payloads include schema/request/display/ranking/translation fields.
- Display meaning rows include per-entry witness summaries for common metadata
  so callers do not need backend-specific evidence parsing for the first screen.
- Success and error payloads are covered by JSON Schema documents under
  `docs/schemas/`.
- Runtime failures after command dispatch return structured JSON on stdout and
  a nonzero exit code.
- Document recommended subprocess caller behavior: pass argv as a list, enforce
  timeout and max output size outside the CLI, parse stdout for JSON even on
  nonzero exit, and default to `--translation-mode cache` or `off`.
- Do not add a separate gateway executable until the CLI JSON contract has
  broader Latin, Greek, and Sanskrit snapshot coverage.

## Phase 2B: Subprocess Wrapper

Only after the CLI JSON contract is boringly reliable, add a tiny wrapper or web
service layer that executes `langnet-cli` with an argument whitelist, timeout,
and max output size. The wrapper should not own semantic behavior.

## Phase 3: Minimal Web UI

**Owner persona:** @scribe for labels, @coder for UI, @auditor for provenance.

Acceptance:

- First screen shows forms, morphology, top meanings, sources, and ranking
  reasons.
- Source details can expand/collapse without losing evidence.
- Translation provenance is labeled as derived evidence.
- UI can render degraded states: no buckets, no morphology, cache miss, backend
  unavailable, timeout.

## Phase 4: Service-Native API

**Owner persona:** @architect for API boundary, @coder for runtime integration.

Only after the JSON CLI contract is stable, consider a native Python service
entrypoint that reuses the same internal functions as the CLI. The service
should not fork a separate semantic path.

Acceptance:

- Shared display, ranking, and translation-cache helper modules remain the
  policy boundary below the CLI/web rendering layer.
- Shared encounter application function feeds both CLI and web/API.
- CLI JSON and API JSON remain contract-compatible.
- Process-manager restart requirements are documented for deployed servers.

## Risks

- Subprocess calls can be slow if they trigger cold caches or live translation.
- Pretty-output changes must not affect web rendering.
- Translation population must stay explicit to avoid surprising latency/cost.
- Backend environment differences need structured error reporting.
