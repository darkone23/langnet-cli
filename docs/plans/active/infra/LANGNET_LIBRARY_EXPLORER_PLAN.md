# LangNet Library Explorer Plan

> **For agentic workers:** REQUIRED WORKFLOW: use a design-first pass before implementation. Keep the reader catalog as the source of truth; do not create a second library database unless this plan is explicitly revised.

**Goal:** Build a simple but serious Library experience that lets a reader inspect what LangNet actually has, ask collection/provenance questions, and browse works along meaningful axes such as source collection, language, author, period, region, genre/shelf, and provenance.

**User questions this must answer:**

- "What did we import from this source collection?"
- "Do we have any Thomas Aquinas?"
- "Do we have Axiochus?"
- "Do we have Marsilio Ficino, Francis Bacon, Thomas More, Anselm, Duns Scotus, Descartes, Spinoza, or other later Latin authors?"
- "Do we have Pseudo-Dionysius in Greek?"
- "Do we have John Scotus Eriugena's Latin translations?"
- "Which works are present only as source files, which are indexed, and which are visible in the learner UI?"
- "Which titles are duplicated across sources or editions?"

## Current Baseline

Existing surfaces:

- CLI `reader works` can search visible catalog works.
- CLI `reader source-index` can inspect work/edition/source provenance rows.
- API `/api/reader?mode=works` exposes visible works.
- API `/api/reader?mode=source-index` exposes source-index rows.
- Flat TSV snapshots live in `data/reference/reader_source_index/`.
- Reader discovery already has shelves, groups, tags, author indexes, work dossiers, source labels, and collection filters.

Probe results from the current catalog:

- `dionysius` returns results in `works` and `source-index`.
- `thomas aquinas`, `axiochus`, `marsilio ficino`, `francis bacon`, `thomas more`, `pseudo dionysius`, `john scotus`, `eriugena`, `anselm`, `duns scotus`, `descartes`, and `spinoza` currently return no direct `works` or `source-index` hits.
- This does not prove those authors are impossible to import; it means the current reader catalog cannot answer those queries as present works.

Known gap:

- `data/reference/reader_source_index/duplicate_canonical_text_ids.tsv` currently reports one visible duplicate canonical text id: `De situ terrae sanctae`, present through both `digiliblt` and `opengreekandlatin_csel`.

## Product Shape

Add a learner/researcher-facing `/library` page.

Primary page regions:

- Search: one query box for author, title, source id, CTS urn, canonical id, and source path fragments.
- Axis filters: language, collection, shelf/group, tag, period, region, authorship status, source status, and duplicate status.
- Collection explorer: a left rail or top panel listing source collections with counts and health/provenance summaries.
- Results table/cards: work title, author, language, collection, period, shelf/group, token count, source label, duplicate/provenance chips.
- Work drilldown: reuse existing reader work dossier/source details where possible.
- Empty-state intelligence: when a query misses, show "not found in current catalog" and optionally a known acquisition/watchlist note if available.

Design principle:

- The Library is an audit and discovery surface over the reader catalog, not a separate reading surface. Selecting a work should route into the existing Reader experience.
- Corpus acquisition is tracked separately in `docs/plans/active/infra/LANGNET_CORPUS_BUILDING_AND_ACQUISITION_PLAN.md`; the Library should expose acquisition/provenance status but should not perform acquisition work at request time.

## Data Model Additions

### 0. Electronic text acquisition policy

The import pipeline should prefer any stable electronic text over a perfect scholarly format.

Acquisition priority:

- Machine-prepared flat text, HTML, or EPUB.
- XML/TEI when available, but only as a convenience.
- Well-structured site mirrors with stable internal links.
- OCR'd PDFs when the source is valuable and no cleaner electronic text exists.
- Raw image PDFs only as a last resort.

For every acquisition source, record:

- Source homepage.
- Source license or terms note when available.
- Retrieval date.
- Retrieval method: mirror, scrape, direct download, PDF parse, or manual flatfile.
- Raw source path.
- Extracted normalized path.
- Importer/parser version.
- Known exclusions.

### 0.1 Latin Library mirror candidate

The Latin Library is a practical high-value candidate for Anselm, Descartes, and many Neo-Latin/Christian Latin texts. Treat it as a site-mirror source, not as an ad-hoc scraper embedded in request-time product code.

Source posture from the Latin Library notice:

- Texts come from mixed sources: public-domain scans, disappeared Internet sources, and contributor submissions.
- The site attempts to indicate edition/conversion credits where known, but some texts have uncertain edition provenance.
- The site states the texts are not intended as substitutes for critical editions.
- Scanner artifacts and typographical errors may remain.
- The site presents texts for online reading or downloading for personal or educational use.
- The site attempts to avoid copyright-protected texts and asks to be notified if a copyright claim exists.

LangNet treatment:

- Treat Latin Library imports as electronic reading editions/source witnesses, consistent with the rest of the reader corpus.
- Preserve page-level credit/edition notes where available.
- Add a source quality flag such as `mixed_provenance_needs_spot_check`.
- Prefer it for reader availability, vocabulary/morphology practice, and discovery coverage.
- Add a takedown/removal path at the source-manifest level.

Candidate acquisition command shape:

```bash
mkdir -p data/sources_external/latin_library/raw
wget \
  --mirror \
  --convert-links \
  --adjust-extension \
  --page-requisites \
  --no-parent \
  --wait=1 \
  --random-wait \
  --directory-prefix=data/sources_external/latin_library/raw \
  https://www.thelatinlibrary.com/
```

Implementation constraints:

- Run this only as an explicit acquisition step, never during normal databuild.
- Keep raw mirror files separate from generated reader artifacts.
- Add a manifest file that records command, timestamp, source URL, and local root.
- Build an extractor that turns selected HTML pages into normalized plain text segments.
- Start with targeted authors/pages before importing the whole mirror into the catalog.
- Add skip rules for navigation/index pages, non-text pages, and pages with unclear source status.
- Preserve source URLs and local raw paths in `source_files`.

Initial Latin Library target set:

- Anselm: `anselm.html`, `anselmproslogion.html`, `anselmepistula.html`.
- Descartes: `des.html` and `descartes/des.*.shtml`.
- Broader Christian/Neo-Latin indexes after the parser is proven.

Risk controls:

- Check `robots.txt` and terms before mirroring.
- Use polite wait/random-wait settings.
- Make the mirror reproducible but do not require it to be committed if it is too large.
- Commit importer code and small manifests/indexes; decide separately whether raw mirror files belong in Git or external storage.

### 1. Source index export command

Make the generated flat files reproducible.

CLI target:

```bash
just cli reader source-index-export --output-dir data/reference/reader_source_index --output json
```

Requirements:

- Regenerate `all_collections.tsv`.
- Regenerate one `<collection_id>.tsv` per collection.
- Regenerate `duplicate_canonical_text_ids.tsv`.
- Regenerate `README.md` with collection counts.
- Use read-only DuckDB access for the catalog.
- Preserve stable column order.
- Include a JSON summary payload with file paths and row counts.

Files likely touched:

- `src/langnet/reader/storage.py`
- `src/langnet/reader/service.py`
- `src/langnet/cli.py`
- `tests/test_reader_cli.py`
- `data/reference/reader_source_index/README.md`

### 2. Library search payload

Add a catalog-level search shape that can merge visible works and source-index rows.

Candidate CLI:

```bash
just cli reader library-search --query aquinas --limit 50 --output json
```

Candidate API:

```text
/api/reader?mode=library-search&q=aquinas&limit=50
```

Payload fields:

- `query`
- `items`
- `facets`
- `collections`
- `total_estimate`
- `miss`
- `suggested_watchlist_matches`

Item fields:

- `result_kind`: `work`, `source_index`, `author`, `duplicate`, or `watchlist`
- `work_id`
- `title`
- `author`
- `language`
- `collection_id`
- `source_id`
- `canonical_text_id`
- `period`
- `region`
- `shelf`
- `tags`
- `token_count`
- `segment_count`
- `source_path`
- `route`

### 3. Enrichment axes

The current catalog has some classification fields, but the Library needs stronger browsing axes.

Axis fields:

- `period`: Ancient, Late Antique, Medieval, Renaissance, Early Modern, Modern, Unknown.
- `date_range`: normalized display string, e.g. `c. 1225-1274`.
- `region`: Greece, Rome, North Africa, Byzantium, Gaul, Iberia, Britain/Ireland, German lands, Italy, India, Unknown.
- `tradition`: Classical, Christian, Jewish, Neoplatonic, Scholastic, Humanist, Scientific, Legal, Philosophical, Poetic, Historical, Grammatical.
- `language_phase`: Classical Latin, Late Latin, Medieval Latin, Renaissance Latin, Early Modern Latin, Classical Greek, Koine Greek, Byzantine Greek, Vedic Sanskrit, Classical Sanskrit.
- `availability`: readable, indexed_only, source_only, metadata_only, wanted.

Implementation rule:

- Store curated/enriched values in YAML overlays first. Do not infer high-confidence period/region labels from title strings at request time.

Possible directories:

- `data/curated/reader_library_axes/authors/*.yaml`
- `data/curated/reader_library_axes/works/*.yaml`
- `data/curated/reader_library_axes/watchlist/*.yaml`

### 4. Wanted authors and acquisition gaps

Create a small watchlist so the Library can answer important misses honestly.

Initial watchlist names:

- Thomas Aquinas
- Marsilio Ficino
- Francis Bacon
- Thomas More
- Pseudo-Dionysius the Areopagite
- John Scotus Eriugena
- Anselm of Canterbury
- John Duns Scotus
- Rene Descartes
- Baruch Spinoza
- Axiochus

Watchlist payload fields:

- `display_name`
- `aliases`
- `languages`
- `period`
- `region`
- `tradition`
- `desired_works`
- `known_public_domain_sources`
- `current_status`: missing, partial, candidate_source_found, imported, verified.
- `notes`

This turns "do we have Aquinas?" into a clear answer:

- If present: show works.
- If missing but watchlisted: show "not currently imported" with planned/candidate source notes.
- If unknown: show normal empty state.

## UI Increment Plan

### Phase 1: Minimal collection explorer

Build `/library` using existing APIs.

Scope:

- Add route `webapp/src/routes/library/+page.svelte`.
- Add library API helpers around `source-index`, `collections`, and `works`.
- Show collection list with counts.
- Show source-index table.
- Add search box using `mode=source-index&q=...`.
- Add optional collection filter.
- Add "Open in Reader" link when a row has a visible `work_id`.

Acceptance:

- User can click a collection and see contained works.
- User can search `dionysius` and see current matches.
- User can search `thomas aquinas` and get an honest empty state.
- Page works on mobile as stacked filter/result cards.

### Phase 2: Unified library search

Add backend `library-search`.

Scope:

- Search visible works, authors, aliases, and source-index rows in one request.
- Return result kinds and facets.
- Add query examples and empty-state messaging.
- Wire `/library` to use `library-search` by default.

Acceptance:

- `dionysius` shows work and source-index matches together.
- `source_path` and `source_id` fragments are searchable.
- Duplicate canonical ids can be filtered.
- Empty results are distinguished from backend errors.

### Phase 3: Axis filters

Add period/region/tradition/language-phase axes from curated overlays.

Scope:

- Define overlay schema.
- Add storage registration and catalog join.
- Backfill high-value known authors/works.
- Add filters to CLI/API/UI.

Acceptance:

- User can browse "Latin / Medieval / Scholastic".
- User can browse "Greek / Late Antique / Christian / Neoplatonic".
- Unknown values are visible as unknown, not silently hidden.

### Phase 4: Watchlist and acquisition gap layer

Add wanted-author data.

Scope:

- Create curated watchlist YAML.
- Add CLI/API payload for watchlist search.
- Merge watchlist suggestions into `library-search` misses.
- Add UI empty-state cards.

Acceptance:

- Searching `thomas aquinas` reports missing from current catalog but known as a wanted Medieval Latin Scholastic author.
- Searching `pseudo dionysius` can distinguish Greek corpus expectations from Latin translation expectations.
- Searching `eriugena` or `john scotus` reports the planned `PL122` acquisition target until it becomes an imported reader work.

### Phase 5: Source quality and duplicate management

Make provenance/audit useful for catalog maintenance.

Scope:

- Add duplicate filter to source-index/library-search.
- Add "preferred source" concept for duplicate canonical ids.
- Add source witness display for suppressed/alternate editions.
- Resolve the current `De situ terrae sanctae` duplicate.

Acceptance:

- Duplicate works are explainable as editions/sources, not confusing duplicate titles.
- The Library can show all witnesses for a canonical text id.

### Phase 6: Acquisition target visibility

Expose acquisition scorecards and target status through Library-adjacent data.

Scope:

- Keep scorecard TSV/JSON files under `data/reference/ogl_import_audit/`.
- Add curated watchlist rows for high-value absent targets such as Eriugena, Pseudo-Dionysius, Aquinas, and PG pilot authors.
- Add a lightweight source status vocabulary: `present`, `missing_local_source`, `staged`, `imported`, `needs_rights_review`, `needs_ocr`, `needs_segmentation`, `needs_identity_review`.
- Show acquisition targets in empty states without confusing them for imported works.

Acceptance:

- Searching `eriugena` before import shows a wanted/acquisition card pointing to PL122 rather than a generic miss.
- After PL122 import, searching `eriugena` shows catalog results first and acquisition history/provenance second.
- Searching a PG pilot author can state whether the current blocker is no local PG checkout, OCR staging, or import review.

## Implementation Tasks For Spark Agent

### Task A: Source index export command

@coder implement `reader source-index-export`.

Constraints:

- Use read-only catalog access.
- Do not change catalog schema.
- Preserve existing generated TSV columns.
- Add targeted CLI tests.
- Regenerate `data/reference/reader_source_index/`.

Validation:

```bash
just test test_reader_cli
just cli reader source-index-export --output-dir data/reference/reader_source_index --output json
```

### Task B: Minimal `/library` route

@coder implement the first UI slice.

Constraints:

- Reuse `/api/reader?mode=source-index`.
- Reuse existing reader types where practical.
- Do not build a separate database.
- Keep the UI simple: collection selector, search input, result cards/table.
- Make empty states explicit and non-weird.

Validation:

```bash
cd webapp && bun run check
cd webapp && bun run build
```

Manual QA:

- Visit `/library`.
- Select `opengreekandlatin_church_fathers`.
- Confirm three contained works are visible.
- Search `dionysius`.
- Search `thomas aquinas` and confirm clear empty state.

### Task C: Library search design spike

@architect design `reader library-search` after Phase 1 is working.

Deliverable:

- Proposed storage query shape.
- Payload contract.
- Facet contract.
- How watchlist matches merge with real catalog matches.
- Testing plan.

Do not implement Phase 2 until Phase 1 has been validated in browser.

### Task D: Latin Library acquisition spike

@coder create a safe acquisition/import spike for The Latin Library.

Scope:

- Add a documented mirror command or `just` recipe for a polite site mirror.
- Add a manifest format for mirrored electronic text sources.
- Add a small extractor for two Anselm pages and Descartes `Meditationes`.
- Produce normalized plain text or segmented JSON under `data/build/reader_import_staging/latin_library/`.
- Do not import the entire site into the reader catalog in the first pass.

Validation:

```bash
just cli reader source-index --query anselm --limit 5 --output json
just cli reader source-index --query descartes --limit 5 --output json
```

Manual QA:

- Confirm extracted text is actual Latin content, not navigation boilerplate.
- Confirm source URL and local raw source path are preserved.
- Confirm the extractor can skip index/navigation pages.

### 0.2 Archive.org acquisition lane

Archive.org is a strong fallback and sometimes a primary source when it exposes machine-derived files. Prefer Archive metadata and derivative files over scraping page text.

Acquisition priority for an Archive item:

- `_djvu.txt` or other derived plain text.
- EPUB.
- HTML if present and clean.
- PDF with OCR text layer.
- PDF image extraction only when no text derivative exists.

Candidate command shape:

```bash
mkdir -p data/sources_external/archive_org/raw/<identifier>
wget \
  --directory-prefix=data/sources_external/archive_org/raw/<identifier> \
  "https://archive.org/metadata/<identifier>" \
  "https://archive.org/download/<identifier>/<identifier>_djvu.txt"
```

Implementation constraints:

- Use the Archive metadata endpoint to discover files instead of guessing names where possible.
- Record Archive identifier, item URL, file URL, file name, file size, sha/hash when available, and retrieval date.
- Keep original derived text separate from normalized extracted text.
- Add source quality flags: `archive_derived_text`, `archive_epub`, `archive_pdf_text_layer`, `archive_pdf_ocr_needed`.
- Treat Archive texts as candidates requiring spot-checks; derived OCR can be noisy.

Initial Archive.org targets from current research:

- Francis Bacon: Archive has editions of *The Works of Francis Bacon*.
- Thomas More: Archive has volumes of *The Complete Works of St. Thomas More*.
- Duns Scotus: Archive has some editions/secondary collections; use cautiously.
- Spinoza: Archive has *The Chief Works of Benedict de Spinoza*.
- Axiochus: Archive has printed/OCR material, but a Greek electronic source may be better if available.

Task E: Archive.org acquisition spike

@coder implement a small Archive metadata downloader and derivative-text extractor.

Scope:

- Add a script or CLI subcommand that accepts one Archive identifier and writes a manifest.
- Download metadata JSON and the best available text derivative.
- Normalize the derivative into staging text.
- Preserve all provenance.
- Start with one Descartes/Gutenberg-style direct text source and one Archive item to prove the abstraction handles both direct text and Archive metadata.

Validation:

```bash
python -m py_compile src/langnet/reader/source_acquisition.py
just test test_reader_cli
```

Manual QA:

- Inspect the first 100 lines of staged text.
- Confirm OCR headers/footers are either stripped or marked as needing cleanup.
- Confirm source manifest can explain exactly where the text came from.

### Task F: Patrologia Latina PL122 acquisition spike

@coder implement the first Patrologia-specific acquisition spike around Joannes Scotus Eriugena.

Scope:

- Create a source manifest for `PL122` under the planned external source layout.
- Use Latin Wikisource `Patrologia_Latina/122` as the first table-of-contents and work-boundary source.
- Use Archive.org PL122 or PL 1-221 as a fallback/cross-check source.
- Stage at least one work-level text sample for `De divisione naturae` or `De praedestinatione`.
- Preserve PL volume id, source URL, retrieval date, text quality status, and work-boundary confidence.
- Do not bulk-import all of PL122 until the staged sample has been inspected.

Validation:

```bash
just cli reader source-index --query eriugena --limit 10 --output json
just cli reader source-index-export --output-dir data/reference/reader_source_index --output json
```

Manual QA:

- Confirm staged text is Latin content, not Wikisource navigation.
- Confirm source provenance identifies `PL122`.
- Confirm `/library` can eventually surface Eriugena after import.

### Task G: Patrologia Graeca pilot manifest and sample

@coder create a PG pilot acquisition manifest and one staged sample before broad PG import.

Scope:

- Evaluate Open Patrologia Graeca / OGL-PatrologiaGraecaDev availability for one volume.
- Compare one overlapping Calfa PG volume when possible.
- Record whether the source offers raw text, hOCR, page images, column labels, author/work metadata, and rights notes.
- Stage one small Greek text sample from the chosen source.
- Record OCR quality and segmentation risk explicitly.
- Do not import broad PG until the pilot path is proven.

Validation:

```bash
just cli reader source-index --query "patrologia graeca" --limit 10 --output json
```

Manual QA:

- Confirm the sample is Greek text with acceptable Unicode handling.
- Confirm source manifest can identify the PG volume and source witness.
- Confirm scorecard notes are updated if the pilot contradicts the current ranking.

## Open Questions

- Should `/library` be public navigation, or initially hidden behind `/reader`/internal links?
- Should English Bible translations appear in the same Library surface, or remain hidden from primary Latin/Greek/Sanskrit reader UX?
- How aggressive should the watchlist be: only authors we intend to import soon, or a broader "classical/medieval/early modern desiderata" list?
- Should period/region/tradition axes be author-level, work-level, or both? Recommendation: both, with work-level overriding author-level when known.

## Recommended Next Move

Current next move:

- Implement Task F first: PL122 / Eriugena acquisition spike.
- In parallel or immediately after, implement Task G: Patrologia Graeca pilot manifest and sample.
- Keep Phase 4 watchlist work close behind so `/library` can explain important misses before each target is fully imported.

Reason:

- Source-index exports and the minimal Library surface already exist.
- Eriugena is a confirmed high-value miss caused by absent local PL122 source material.
- PG is a major corpus gap, and a pilot prevents us from designing a broad importer around untested OCR assumptions.
- The Library should make missing-known targets visible instead of silently returning empty search results.
