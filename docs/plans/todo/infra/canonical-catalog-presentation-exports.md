# Canonical Catalog Presentation Exports

Status: todo
Owner: @coder, @scribe
Created: 2026-06-20
Supersedes follow-up phases from: `docs/plans/completed/infra/LANGNET_CANONICAL_CATALOG_EXPORT_PLAN.md`

## Goal

Generate human-facing and interchange exports from the canonical reader catalog
bundle, without making those exports the source of truth.

## Scope

- Add EPUB export from a canonical bundle or single exported work.
- Map reader segments to stable XHTML sections.
- Include Dublin Core metadata and LangNet canonical text ids.
- Include a source/provenance page that preserves upstream CTS/source URNs as
  evidence rather than primary UI identifiers.
- Decide whether static HTML and JSONL slices need separate commands or should
  be generated from the same presentation-export layer.

## Acceptance

- `reader export epub <work-id>` or equivalent operates from canonical bundle
  data rather than directly from irregular upstream source files.
- EPUB output validates with a local smoke check and preserves title, author,
  language, canonical id, segment order, and provenance.
- Learner-facing presentation omits noisy apparatus only by explicit mode or
  documented policy; no source evidence is silently discarded.
