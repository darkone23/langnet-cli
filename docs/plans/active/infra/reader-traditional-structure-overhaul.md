# Reader Traditional Structure Overhaul

## Status

Active implementation handoff. The detailed design spec is
`docs/superpowers/specs/2026-06-02-orion-reader-structure-design.md`.

Implemented slices:

- Orion UI vocabulary, Object Card, provenance chips, Canon Table, Work Desk,
  and mobile Apparatus Sheet foundations.
- `reader structure` and `/api/reader?mode=structure`.
- Division metadata overlay storage, sync, builder integration, and a reviewed
  Bhagavadgītā chapter 9 fixture.
- Structure-aware `resolve-address`, including exact `traditional_reference`
  lookups such as `BhG 9` and work-qualified labels such as `Republic Book 10`.
- `reader about` and `/api/reader?mode=about` Work Dossier payloads for
  deterministic "tell me about this book" summaries.

Remaining high-value slices:

- More curated aliases and work maps for Greek/Latin canonical examples such as
  Plato's Republic.
- A richer dossier route or drawer for full author/work/chapter biography and
  evidence inspection.
- Generated, review-gated work and chapter bios after source-backed evidence
  coverage expands.

## Goal

Drive the Project Orion UI overhaul, using traditional text structure as the
first concrete proving ground.

The overhaul should make Word, Library, Work, Leaf, Learn, Oracle, and Dossier
surfaces feel like one computable manuscript workspace. Within that system,
conventional text divisions such as books, chapters, sections, verses, and
sutras become indexable, addressable, displayable, researchable, and visible in
the Reader UI as first-class Project Orion objects.

## Scope

This is one Orion UI overhaul implemented incrementally. The first concrete
feature slice is the traditional-division layer:

- standardize reusable UI primitives such as Object Card, Canon Table,
  Marginalium, Dossier, Wheel, Oracle Panel, Provenance Chip Row, and Apparatus
  Sheet;
- improve mobile and tablet apparatus behavior;
- map machine citation paths to traditional division ranges;
- expose a Work Desk and Canon Table for one selected work;
- show current book/chapter context while reading a Leaf;
- support chapter/work bios and provenance-bearing metadata overlays;
- support Firecrawl-backed research batches that enhance curated reader
  metadata and generated study metadata.

## Key Decisions

- Use the Project Orion World and Oracle model.
- Treat Word, Work, Author, Chapter, and Passage as first-class study objects.
- Keep `work_map_nodes`, `citation_references`, and `citation_maps` distinct.
- Prefer a companion division metadata overlay keyed by `work_id + node_id` for
  bios, alternate labels, generated status, and evidence.
- Use flat provenance chips for all claim-bearing UI blocks.
- Standardize async states: skeletons for new content, one loading badge or
  strip with elapsed seconds for replacing existing content.
- Move new user-facing terms into `webapp/src/lib/ui-copy.ts`.
- Treat Firecrawl artifacts as audit evidence for curated metadata, not runtime
  data.

## Persona Handoffs

- @architect: refine the `reader map` versus `reader structure` service
  contract and confirm the division metadata table boundary.
- @coder: implement the first Work Desk and Canon Table slice with tests once
  the detailed implementation plan is approved.
- @artisan: keep UI primitives reusable and avoid one-off reader-only styling.
- @auditor: review provenance, generated-text labeling, old-catalog
  compatibility, and citation mismatch handling.
- @scribe: update web UI docs and reader contract docs after implementation.

## Immediate Next Step

Continue expanding Work Dossier and structure-address coverage from
source-backed curated data. Keep `reader about`, `reader structure`, and
`resolve-address` as the backend contracts for the UI overhaul.
