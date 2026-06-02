# Reader Traditional Structure Overhaul

## Status

Active design handoff. The detailed design spec is
`docs/superpowers/specs/2026-06-02-orion-reader-structure-design.md`.

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

Review and approve the design spec. After approval, create a detailed
implementation plan with small, test-driven tasks.
