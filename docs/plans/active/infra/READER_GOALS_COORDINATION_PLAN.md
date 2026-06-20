# Reader Goals Coordination Plan

> **For agentic workers:** Use this as the coordination layer. The detailed plans remain the source of truth for implementation details, but this file defines the current reader work order, acceptance gates, and handoff boundaries.

**Goal:** Keep LangNet's reader work moving toward a coherent library: trustworthy imports, visible provenance, useful discovery, reproducible acquisition, and learner-facing access to Latin, Greek, and Sanskrit texts.

## Current Parity Target

The active target is not raw corpus-count parity. It is **provenance-and-reader-quality parity** across every expansion lane before broad import.

For each new corpus family or source family, LangNet should reach this minimum bar before scaling:

- A source manifest exists before text enters the reader catalog.
- The source-index can answer what was imported, from where, with language, author/title, source path, segment count, token count, and quality status.
- One representative staged/imported sample has been inspected for readable text, work boundaries, and front-matter/OCR noise.
- Known defects are tracked in `data/reference/reader_quality_audit/current_known_issues.tsv`.
- Expansion queues distinguish external source gaps, local checkout gaps, importer gaps, and UI/discovery gaps.
- `/library`, CLI `reader works`, and CLI/API source-index views expose the import without making wanted/acquisition targets look like already-readable works.

Current concrete parity gates:

- PL122/Eriugena: pilot-slice parity met for fourteen works; keep segmentation as a watch item, not a blocker to choosing the next source family.
- Popular classical Latin: parity is not met until the reader has a source-reviewed open/mirrorable path for the highest-demand classroom works, starting with Caesar or Sallust.
- Humanist/mystical source library: Agrippa now has a manifest-backed source candidate and candidate Book I DjVu OCR sample, but import is deferred because cleanup likely needs lexeme-level correction; Ficino and Cusanus now have manifest-backed candidates for cleaner-source comparison; parity is not met until one pilot passes readability/boundary review and the Suda/Orion reference lane has an explicit inventory path.
- Patrologia Graeca: sample-import parity met, but reader-quality parity is not met until OCR noise and segmentation are calibrated against a second witness such as Calfa overlap.
- CSEL: CSEL61 now has a verified source candidate and manifest-backed decision; acquisition parity is not met until one PDF/OCR witness is parsed and a readable sample is staged with work-boundary metadata.
- Library: CLI/API/server-rendered parity exists; browser interaction, work/author portals, and source/acquisition badges are complete for the current Library surface.
- Search: reader catalog/source-index parity exists; `search.lance` rebuild remains deferred until the next approved expansion or reader-quality gate.

## Related Plans And Artifacts

- `docs/technical/rebuilding-reader-sources.md`: reader rebuild model, source-index exports, generated/curated metadata loop, server migration notes.
- `docs/plans/completed/infra/LANGNET_CORPUS_BUILDING_AND_ACQUISITION_PLAN.md`: completed acquisition framework, lanes, source manifests, corpus-building policy, and target author/work register.
- `docs/technical/reader-source-acquisition.md`: current source-acquisition operating guide for manifests, staging, source roles, quality status, and verification.
- `docs/plans/active/infra/READER_COLLECTION_EXPANSION_MASTER_TRACKER_2026-06-07.md`: expansion-lane register, status, cost tiers, and target order.
- `docs/plans/completed/infra/LANGNET_LIBRARY_EXPLORER_PLAN.md`: completed `/library`, search, watchlist, provenance, work/author portal, and acquisition-gap UX surface.
- `docs/plans/completed/infra/LANGNET_CANONICAL_CATALOG_EXPORT_PLAN.md`: completed canonical directory bundle export, work/catalog export CLI, validation command, deterministic checksum rows, and Bruno smoke bundle.
- `docs/plans/todo/infra/canonical-catalog-presentation-exports.md`: future EPUB/static presentation exports from canonical bundles.
- `docs/plans/todo/infra/canonical-catalog-portability-and-archive-packaging.md`: future archive packaging, restore docs, and retention policy.
- `docs/plans/active/infra/READER_EXPERIENCE_MODALITY_AND_TYPOGRAPHY_PLAN.md`: reader modality, typography, tone, ornament, and keyed-work experience policy.
- `docs/plans/completed/infra/READER_WORD_CONTEXT_RETRIEVAL_QUALITY_PLAN.md`: completed selected-word sidebar, CLI/API word-context payload, retrieval correctness, index health, and performance gates.
- `docs/plans/completed/infra/OPEN_GREEK_LATIN_IMPORTER_AUDIT_AND_FIX_PLAN.md`: completed OGL importer audit surfaces and direct source-view comparison slice.
- `docs/plans/completed/infra/BRUNO_LLULL_ELECTRONIC_TEXT_ACQUISITION.md`: completed bounded Bruno HTML acquisition slice and Llull research handoff.
- `docs/plans/todo/infra/llull-latin-source-research-continuation.md`: future Llull source-witness research before staging/import.
- `docs/plans/todo/infra/ogl-patrologia-source-view-mapping-and-attribution-review.md`: future PL filename/volume mapping, broader source-view samples, and attribution review.
- `data/reference/reader_source_index/`: checked-in source-index snapshots.
- `data/reference/ogl_import_audit/`: OGL, CSEL, Patrologia, PL/PG acquisition scorecards.
- `data/reference/reader_quality_audit/current_known_issues.tsv`: current corpus-quality blockers found in the live reader catalog.
- `data/sources_external/patrologia_latina/pl122/manifest.yaml`: imported PL122/Eriugena pilot acquisition manifest.
- `data/sources_external/patrologia_graeca/pilot/manifest.yaml`: PG pilot acquisition manifest.
- `data/curated/reader_library_watchlist/high_value_targets.yaml`: high-value absent or staged acquisition targets for Library empty states.
- `docs/archive/2026-06-reader-expansion/READER_CURRENT_STATUS_HANDOFF_2026-06-07.md`: dated verified state, command outcomes, running-service notes, and safe handoff prompt from the 2026-06-07 reader pass.

## Current Reader Workstreams

### 1. Provenance and audit visibility

Status:

- Source-index export exists and writes checked-in flatfiles.
- OGL audit artifacts exist under `data/reference/ogl_import_audit/`.
- PL/PG acquisition scorecards and next-step queue exist.
- Current live-catalog corpus quality defects are tracked under `data/reference/reader_quality_audit/current_known_issues.tsv`.

Next actions:

- Keep high-priority corpus defects fixed before broadening imports. Sanskrit translations imported as Sanskrit works and PHI Coptic/Sahidic rows visible in primary classical surfaces were fixed in importer guards and current catalog on 2026-06-07.
- Keep source-index TSVs regenerated after each catalog import/rebuild.
- Latest post-cleanup source-index export on 2026-06-07 reported `10592` rows, with `patrologia_graeca_pilot.tsv` at `1`, `sanskrit_texts.tsv` at `320`, and `phi.tsv` at `784` rows.
- Keep `current_ogl_audit.json` regenerated after OGL importer changes.
- Make every skipped OGL file explainable as alternate view, duplicate, zero-segment, missing source, or parse/import issue.

Acceptance:

- A human can answer "what did we import from this source?" from TSVs or `/library`.
- A human can distinguish external corpus gaps from local checkout gaps and importer gaps.
- Every future acquisition target has a manifest before raw text enters the reader catalog.
- Translation-only or unsupported-language rows are not silently presented as primary Greek, Latin, or Sanskrit reader works.

### 2. Patrologia Latina PL122 / Eriugena

Status:

- PL122 is externally attested and now imported as a pilot slice; local OGL coverage remains partial for Patrologia.
- A PL122 source manifest exists.
- Raw Latin Wikisource markdown and staged samples exist for the fourteen imported PL122 works:
  - `De divisione naturae`
  - `De praedestinatione`
  - `Expositiones super Ierarchiam caelestem S. Dionysii`
  - `Versio operum S. Dionysii`
  - `Homilia in prologum Evangelii secundum Joannem`
  - `Commentarius in Evangelium secundum Joannem`
  - `De egressu et regressu animae ad Deum`
  - `Expositiones super Ierarchiam ecclesiasticam S. Dionysii`
  - `Expositiones in Mysticam theologiam S. Dionysii`
  - `Versio Ambiguorum S. Maximi`
  - `Versus`
  - `Epistola et Decreta`
- `reader stage-pl-wikisource` now emits segmented JSONL for staged PL122 works.
- `reader import-pl-wikisource` imported all fourteen above works into the reader catalog.
- Source-index snapshots now include collection `patrologia_latina_wikisource`.
- Reviewed generated work classifications and author classification have been synced for the selected PL122 import.
- This is acquisition work, not currently an importer bug.

Next actions:

- Spot-check imported PL122 works in `/reader` and `/library` was completed for representative samples.
- Segmentation/front-matter handling for PL122 is implemented in code; full selected-slice re-stage/import verification is now complete and shows text-first first segments.
- Add curated aliases and metadata for Eriugena where useful.
- PL122 is now fully staged and imported across the 14-toC works; next priority is the next planned volume from the PL scorecards after reader QA.
- Generate/import metadata for newly imported works only when they enter the reader catalog.
- Full reader search-index rebuild was attempted on 2026-06-07 but was stopped after running too long for the synchronous pass; this is deferred until after segmentation is signed off.
- Inspect Archive.org PL122 or PL 1-221 derivatives for OCR fallback.
- Use the University of Chicago Patrologia Latina Database bibliography as a PL worklist/identity-control source when selecting future PL gaps; classify it as bibliographic knowledgebase evidence rather than clean reader text unless a separate text witness is identified.
- Preserve PL column markers as address/provenance metadata.
- Import additional PL122 works only after the selected-work reader experience is acceptable.

Acceptance:

- Multiple staged Latin samples exist with explicit PL122 provenance. Completed for fourteen samples.
- The staged samples are actual Latin content, not navigation or index boilerplate. Completed for fourteen samples.
- Segmented JSONL exists for fourteen selected PL122 works. Completed.
- PL122 is one of Patrologia Latina’s 217-volume series baseline and is a pilot, not a series-complete acquisition.
- After import, Eriugena appears in `reader works`, `reader source-index`, `/library`, and source-index TSVs. CLI/source-index TSV portion completed.
- The Library acquisition watchlist is served from `data/curated/reader_library_watchlist/high_value_targets.yaml` through `reader library-watchlist` and `/api/reader?mode=library-watchlist`, avoiding duplicated frontend-only acquisition target data.
- Verified on 2026-06-07: `reader works --query eriugena`, `reader source-index --collection patrologia_latina_wikisource`, `/api/reader?mode=source-index&q=eriugena`, and server-rendered `/library` all expose all fourteen imported Eriugena works.

### 3. Patrologia Graeca pilot

Status:

- A pilot checkout was selected from OGL-PatrologiaGraecaDev Vol.-1 and raw OCR pages were staged locally.
- A one-work Patrologia Graeca sample has been staged and imported (Clement to the Corinthians).
- A PG pilot manifest exists and now includes this staged sample context.

Next actions:

- Calibrate the Vol.-1 pilot against Calfa overlap where available.
- Compare OCR quality, coverage, and metadata fidelity of pilot rows before any broad PG expansion.
- Update `data/reference/reader_quality_audit/current_known_issues.tsv` with pilot OCR and segmentation risks.
- Record a scale-up/rejection decision and only then schedule PG-series expansion work.

Acceptance:

- One PG pilot sample is staged and imported (and appears in `reader source-index --collection patrologia_graeca_pilot`).
- Unicode Greek text quality and segmentation risks are documented in the audit table.
- A clear recommendation for scale-up exists before broad PG acquisition/import.

### 4. CSEL and Patrologia completeness

Status:

- CSEL external scorecard exists.
- Patrologia local/source/catalog scorecards exist.
- Current CSEL appears more internally consistent than PL, but external coverage remains incomplete.

Next actions:

- Pick missing CSEL base volume ids from `csel_external_scorecard.tsv`.
- Search for reliable electronic/OCR sources for the first missing range.
- Continue open-web legitimacy checks for weak or suspicious OGL rows.
- Compare Patrologia `data`, `corrected`, `split`, and `volumes` source views before changing importer precedence.
- Treat `data/reference/ogl_import_audit/pl_pg_acquisition_next_steps.tsv` row 8 as source-candidate-verified; keep CSEL:volume-61 provenance-first until a local PDF/OCR witness is parsed and sampled.

Acceptance:

- Missing CSEL ranges have source-acquisition status, not just "absent" notes.
- Patrologia source-view precedence is evidence-based.
- High-value questionable rows either have curated overlays, importer fixes, or acquisition targets.

### 4a. Popular classical Latin coverage

Status:

- Current watchlist coverage was biased toward patristic, scholastic, and early-modern philosophical Latin.
- A popular Latin acquisition scorecard now tracks common classroom/self-study targets under `data/reference/ogl_import_audit/popular_latin_acquisition_scorecard.tsv`.
- Initial catalog probing for common Latin queries did not expose visible matches for Vergil, Aeneid, Ovid, Metamorphoses, Caesar, Cicero, Horace, Livy, Tacitus, Sallust, Plautus, Terence, or Catullus.

Next actions:

- Verify existing local/OGL/Perseus coverage before importing duplicates.
- Pick one prose-first measured import target, preferably Caesar `De bello Gallico` or Sallust `Bellum Catilinae`.
- Use only open/mirrorable witnesses: public source trees, Latin Library-style mirrors, Wikisource, Project Gutenberg, Archive derivatives, or reproducible local checkouts.
- Preserve canonical citation shapes before broad import: book/chapter for Caesar and Sallust, speech/section for Cicero, poem number for Catullus, and book/line for Vergil/Ovid.

Acceptance:

- `/library` and `reader works` surface the first imported popular Latin target by common English and Latin aliases.
- Source-index rows show source path, witness role, segment count, token count, and quality status.
- The popular Latin lane remains distinct from PL/PG/CSEL specialist expansion.

### 4b. Humanist, scholastic, mystical, and reference coverage

Status:

- The project direction now distinguishes bulk ecclesiastical series expansion from a curated humanist library lane.
- A seeded scorecard exists at `data/reference/ogl_import_audit/orion_humanist_mystical_acquisition_scorecard.tsv`.
- The watchlist now includes Agrippa, Albertus Magnus, Paracelsus, Pico, Plethon, Suda reference bios, and Orion/etymologica targets alongside existing Ficino, Bruno, Llull, Aquinas, and Duns Scotus rows.
- Suda is already imported as a First1KGreek reader work, but it is not yet structured as an author-bio/person/reference lookup layer.
- The reusable reader-work ingestion skill now lives at `/home/nixos/.agents/skills/langnet-reader-work-ingestion/SKILL.md` and should guide future manifest-backed source acquisition, staging, and scorecard updates.

Next actions:

- Pause broad expansion until current staged/source-decision quality gates are closed in `data/reference/reader_quality_audit/current_known_issues.tsv`; the dated close-out record is archived at `docs/archive/2026-06-reader-expansion/READER_EXPANSION_QUALITY_CLOSEOUT_2026-06-07.md`.
- QA the `/library` source-index truncation fix after web restart; PHI should no longer appear to stop early under the audit-sized source-index limit.
- QA Cusanus reader and Library provenance after its import into `cusanus_latin_wikisource`.
- Continue the reusable manifest-backed ingestion path rather than an author-specific pipeline; current candidates are Cusanus, Ficino, and deferred Agrippa.
- Bruno now proves the direct Latin HTML ingestion path for Project Orion:
  `De Umbris Idearum`, `De Magia`, and `De vinculis in genere` are imported in
  `bruno_esotericarchives` with source-index export.
- Canonical bundle export now proves the normalized runtime contract for
  imported reader works: `reader export work bruno:esotericarchives:de-magia`
  writes a validated directory bundle with manifest, work metadata, segments,
  provenance, catalog summary, and checksums.
- Keep Agrippa deferred in `data/sources_external/agrippa/de-occulta-philosophia/manifest.yaml` until lexeme-level OCR cleanup policy is ready.
- Continue Ficino from `data/sources_external/ficino/de-vita-libri-tres/manifest.yaml`: compare 1489, 1529, and 1549 OCR/text derivatives and pick the cleanest opening sample for staging.
- Cusanus now proves the reusable clean-electronic-text plus control-witness ingestion path: full De docta ignorantia staging imported as 104 paragraph-level segments in `cusanus_latin_wikisource`, with source-index export generated. Next work is post-import reader/Library provenance QA.
- Aquinas Archive.org derivative inspection found a Leonine Prima Pars q.50-q.119 volume; a bounded q.50 paragraph-level OCR candidate is now staged, but it needs OCR review and article substructure separation before reader import.
- Duns Scotus Archive.org derivative inspection found usable non-Ordinatio volumes; locate an open Ordinatio primary witness or deliberately pivot the first Scotus sample to a bounded logical/Sentences work before staging.
- Track Newton, Kepler, and Euler as scientific Latin expansion targets; defer staging until a diagram/formula/proposition-aware source policy is defined.
- Inventory current Greek lexicographic coverage for Suda, Orion of Thebes, Etymologicum-style works, Pseudo-Zonaras, Stephanus Byzantius, and related sources.
- Create source-backed relationship metadata for the Ficino/Plethon/Cosimo/Pico/Plotinus transmission cluster only where evidence is explicit.
- Ensure every UI cast-of-characters figure resolves to reader works, Suda/reference entries, or an acquisition watchlist target.

Acceptance:

- At least one humanist/mystical Latin pilot has a source manifest, staged sample, source-index row, and quality status. Agrippa manifest and candidate sample are complete; import/source-index remains pending readability review.
- Suda/reference entries can be used for author/person context without treating generated summaries as evidence.
- Orion of Thebes and Greek etymologica have explicit inventory status and next actions.
- Cast-of-characters coverage is auditable from curated data or acquisition scorecards.

### 5. Library experience

Status:

- `/library` exists and server-renders initial source-index rows, collections, and acquisition watchlist data.
- Source-index API support exists.
- The Library plan includes acquisition target visibility and watchlist behavior.
- `/library` uses CLI/API-backed curated watchlist data from `data/curated/reader_library_watchlist/high_value_targets.yaml`, not frontend-only constants.
- `/library` now uses compact expandable rows for source-index results instead of a large card for every work.
- Curated watchlist targets include Eriugena, Pseudo-Dionysius, Aquinas, Anselm, Descartes, Bruno, Llull, Duns Scotus, Ficino, Bacon, More, Spinoza, John of Damascus, and Axiochus.
- Verified on 2026-06-07: server-rendered `/library` contains catalog row content (`Ars maior`) and acquisition/provenance content (`Joannes Scotus Eriugena`).
- Verified on 2026-06-07: the compact expandable row layout is deployed in the live `/library` HTML.
- Reader experience policy now has a dedicated modality/typography plan: the UI should feel like a keyed humanist memory theatre, not a generic lexicon.

Next actions:

- Add acquisition status labels such as `missing_local_source`, `planned`, `staged`, `imported`, `needs_ocr`, `needs_segmentation`, and `needs_source_role_review`.
- Keep imported works visually distinct from wanted/acquisition targets.
- Add browser QA coverage for `/library` filters and searches.
- Improve how imported watchlist targets are shown as acquisition history/context instead of "wanted" items.
- Continue typography/tone work according to the reader modality plan: primary text, citation gutter, apparatus, witness labels, and memory-key affordances should all reinforce the scholarly reader-desk experience.

Acceptance:

- Searching `eriugena` after import shows catalog results first and provenance/acquisition context second. Verified via CLI/API and server-rendered Library content on 2026-06-07; browser interaction QA remains.
- Searching planned targets such as `ficino` returns curated acquisition context through `reader library-watchlist` and `/api/reader?mode=library-watchlist`. Verified on 2026-06-07.
- Searching source names or collection ids makes it clear what is present, staged, or still wanted. Partially complete; browser QA remains.

### 6. Metadata enrichment loop

Status:

- Curated and generated metadata roles are documented.
- Source-backed research artifacts and generated classifications are separated by policy.

Next actions:

- Use source-backed curated records for identity, attribution, aliases, work maps, contained works, and citation boundaries.
- Use generated metadata for shelves, tags, periods, popularity, and discovery notes.
- After importing new works, run classification only for new/changed rows where practical.
- Rebuild or update the search index after source text changes.

Acceptance:

### 7. Word-context retrieval quality

Status:

- Selected-word marginalia exists in the reader UI, and encounter briefing can provide learner-facing generated summaries.
- Reader text search, source-index provenance, work contents, work dossiers, and API response caching exist as separate primitives.
- A dedicated implementation plan now exists for unifying those primitives into a CLI/API/UI word-context payload.

Next actions:

- Implement `reader word-context` in the CLI and reader service.
- Expose `/api/reader?mode=word-context` through the web adapter.
- Make the selected-word sidebar render deterministic evidence before generated prose.
- Add golden-query fixtures for common Latin forms such as `corpore`, `arma`, and `virum`.
- Surface search-index availability and timing so no-hit, unavailable-index, and slow-retrieval cases are distinguishable.
- Track retrieval-quality defects in `data/reference/reader_quality_audit/current_known_issues.tsv` before broad corpus expansion resumes.

Acceptance:

- A reader can click a word such as `corpore` and receive a fast, evidence-backed sidebar with form normalization, lexical/morphological evidence where available, reader hits, passage context, provenance, caveats, and timing/index status.
- The same word-context payload is available through CLI JSON and `/api/reader`.
- Generated interpretation remains secondary and does not block deterministic evidence rendering.
- Project quality gates remain explicit: correctness fixtures, source/index status, and retrieval-performance telemetry must be present before this stack is marked complete.

- Generated model output never becomes evidence for authorship or work identity.
- Curated overlays survive rebuilds.
- New reader imports are discoverable by source, author, title, shelf, period, and acquisition provenance.

## Current Priority Order

1. Completed: PL122 reader-quality gate is verified with full selected-slice re-stage/import and sampled content output; keep segmentation quality as a watch point on future PL imports.
2. Continue corpus-quality audit; the known Sanskrit translation and PHI Coptic/Sahidic primary-surface bugs are fixed, but new source-family defects should be added to `data/reference/reader_quality_audit/current_known_issues.tsv`.
3. Plan and execute the next high-value series expansion sequence (PL122 is now complete as a 14-text slice) and sync source-index artifacts.
4. Plan PL122+next PL expansion sequence from scorecards after quality signoff.
5. Compare PG pilot row quality against Calfa overlap and finalize the PG expansion recommendation.
6. Browser-QA the now CLI/API-backed Library watchlist and compact source-index explorer.
7. Continue OGL source-view quality audit.
8. Pick first missing CSEL acquisition target.
9. Refresh source-index and audit scorecards after any import/rebuild.

## Agent Handoff Template

Use this when assigning implementation work:

```text
Work from docs/plans/active/infra/READER_GOALS_COORDINATION_PLAN.md.

Target workstream: <PL122 / PG pilot / Library watchlist / OGL audit / CSEL acquisition>

Do:
- Create or update source manifests before importing source text.
- Keep raw source, staged text, curated metadata, generated metadata, and catalog output separate.
- Preserve provenance: URL, retrieval date, source witness, source path, quality status, and work-boundary confidence.
- Regenerate source-index/audit artifacts only after a catalog import or importer change.

Do not:
- Treat missing local volumes as importer bugs.
- Bulk-import a whole series before staging and inspecting one representative sample.
- Use generated classifications as evidence for authorship or identity.
- Mix wanted/acquisition targets with imported reader works in UI payloads.

Acceptance:
- <specific command or UI flow>
- <specific staged file or manifest>
- <specific source-index/library expectation>
```

## Stop Conditions

Pause and ask for review if:

- A source role is unclear: for example, it may be a bibliography, scan locator, database UI, OCR witness, or clean text witness.
- A staged text is mostly OCR noise.
- Work boundaries cannot be inferred without human judgment.
- A proposed importer change would change source-view precedence for many existing Patrologia/CSEL rows.
- A UI change would make wanted/acquisition targets look like imported works.
