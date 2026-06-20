# Reader Traditional Structure Overhaul

## Status

Active implementation handoff. The detailed design spec is
`docs/superpowers/specs/2026-06-02-orion-reader-structure-design.md`.

Current state audit, 2026-06-03:

- Reader traditional-structure foundations are in place: `reader structure`,
  `/api/reader?mode=structure`, structure-aware address resolution, `reader
about`, Work Dossier payloads, current-division marginalia, Canon Table
  rendering, and mobile Apparatus panels.
- Reader UI decomposition is substantially improved, and the reader route is now
  a thin wrapper at `webapp/src/routes/reader/+page.svelte` over
  `webapp/src/lib/reader/ReaderRoutePage.svelte`. The extracted route page
  implementation is still above the preferred 1000-line ceiling; remaining work
  is route state orchestration, URL synchronization, and selected-work/page
  loading actions.
- The Lexicon Word Desk route is now below the active-refactor threshold but
  still above the preferred route ceiling. `webapp/src/routes/+page.svelte` is
  down to roughly 1680 lines. Lookup execution remains route-owned while
  enrichment refresh and group translation retry orchestration now live in
  `webapp/src/lib/desk/desk-workflows.ts`.
- The Lexicon Word Desk now has a vertical file cluster at
  `webapp/src/lib/desk/` for its `Desk*.svelte` components, `desk-*.ts`
  helpers/tests, shared `desk-entry.css`, and pure entry-display helper module
  `desk-entry.ts`. Source-level guards prevent new Word Desk files from
  returning to the flat root `src/lib` directory, and now also guard the
  extracted status/cache display policy.
- Reader-specific API URL builders and payload fetch helpers now have a first
  vertical cluster at `webapp/src/lib/reader/reader-api.ts`, with focused tests
  and source-level guards preventing `/api/reader` and encounter-briefing URL
  construction from returning to the Reader route.
- Reader TypeScript domain helpers and tests now live under
  `webapp/src/lib/reader/`: `index.ts`, `page-formatting.ts`,
  `page-authors.ts`, `page-routing.ts`, `page-navigation.ts`,
  `index-stats.ts`, `index-storage.ts`, `loading-timers.ts`, `text.ts`, and
  `reader-api.ts`. Source-level guards prevent these files from returning to
  the flat root `src/lib` directory.
- Reader source-level UI guards are now split by concern:
  `src/lib/reader/page-loading.test.ts` covers discovery, forms, async panels,
  and loading composition, while `src/lib/reader/reading-surface-guards.test.ts`
  covers apparatus, reading layout, Work Dossier, current-division, page
  navigation, Leaf, source details, and reader state persistence contracts.
- Reader page loading contracts are now split into a fixture module and two
  focused guards (`src/lib/reader/page-loading-fixtures.ts`,
  `src/lib/reader/page-loading.test.ts`,
  `src/lib/reader/page-loading-components.test.ts`) to keep source guard files
  comfortably below the 1000-line operational ceiling.
- `webapp/src/app.css` is down below 750 lines after the latest Word Desk
  extractions. Remaining component-specific blocks are mostly legacy
  entry-card, gloss/list, memory-routine, study-panel, marginalia, source-beast,
  and MOTD styles. Font/theme tokens and truly shared primitives can stay
  global. Legacy dead blocks have now been removed and `orion-motd-warning`
  moved into `DeskMotdFolio.svelte`.
- New extracted Svelte components are following the project guidelines: typed
  Svelte 5 `$props`, focused file sizes under 500 lines, scoped component
  styles, DaisyUI/Tailwind controls where appropriate, and source-level guards
  in `webapp/src/lib/sveltekit-guidelines.test.ts`.
- Word desk encounter reliability now has an explicit Oracle trace slice: `DeskOracleTrace.svelte`,
  `desk-oracle.ts`, and `desk-oracle.test.ts`.
- Async guidelines are partially met. Reader loading surfaces and the Word Desk
  now share elapsed-second activity surfaces for lookup, translation
  enrichment, MOTD refresh, word-index lookup, word-index section browse, and
  paradigm loading. Remaining work is visual QA and eliminating any older
  competing spinners or badges that duplicate those waits.

Implemented slices:

- Orion UI vocabulary, Object Card, provenance chips, Canon Table, Work Desk,
  and mobile Apparatus Sheet foundations.
- Reader Address Lookup now lives in `ReaderAddressLookup.svelte`, keeping the
  reference-entry control local while the route remains responsible for address
  state and navigation.
- Writing SvelteKit guidelines in `webapp/docs/SVELTEKIT_GUIDELINES.md`,
  grounded in official SvelteKit/Svelte docs and Project Orion UI rules.
- Shared Svelte primitives for Orion Object Cards, Provenance Chip Rows, and
  Reader Canon Tables, replacing duplicate snippets in the Reader route and
  mobile apparatus panels.
- First scoped-style extraction from `webapp/src/app.css`: Object Card,
  Provenance Chip Row, Reader Canon Table, and Work Dossier styles now live in
  their Svelte components.
- Mobile apparatus sheet and panel styles now live with their focused Svelte
  components.
- Reader current-division marginalium now lives in `ReaderCurrentDivision.svelte`
  with scoped styles and provenance chips.
- Reader page navigation now lives in `ReaderPageNav.svelte` with scoped styles
  and DaisyUI button controls.
- Reader Leaf now lives in `ReaderLeaf.svelte`, keeping passage lines, citation
  buttons, selected token states, and optional interlinear transliteration out
  of the route and out of global CSS.
- Reader source/transliteration details now live in `ReaderSourceDetails.svelte`
  so passage evidence display stays component-scoped.
- Reader Desk Header now lives in `ReaderDeskHeader.svelte`, with title,
  author jump, transliteration toggle, library return, and page citation controls
  scoped out of the route.
- Reader Discovery Chooser now lives in `ReaderDiscoveryChooser.svelte`, moving
  the library entry cards and their scoped shelf-card styles out of the Reader
  route and global stylesheet.
- Reader Discovery Shelves now lives in `ReaderDiscoveryShelves.svelte`, so
  dynamic shelf cards share the same route extraction direction without relying
  on global shelf-card CSS.
- Reader Discovery Header now lives in `ReaderDiscoveryHeader.svelte`, while the
  route keeps discovery title derivation and view-selection state.
- Reader Text Search Form now lives in `ReaderTextSearchForm.svelte`, moving
  the text-search control layout into scoped component CSS while the route keeps
  query state and search execution.
- Reader Shelf Work Search Form and Reader Author Search Form now live in
  focused Svelte components, removing the remaining discovery-search form
  dependency from global CSS.
- Reader Discovery Summary now lives in `ReaderDiscoverySummary.svelte`, with an
  optional element callback preserving the work-results scroll target.
- Reader Discovery Pager now lives in `ReaderDiscoveryPager.svelte`, sharing the
  cursor button layout across text, work, and author result pages.
- Reader Author TOC now lives in `ReaderAuthorToc.svelte`, keeping author
  section navigation and native/roman section styling scoped to the component.
- Reader Author List now lives in `ReaderAuthorList.svelte`, moving author group
  display and selected-author work expansion out of the route while preserving
  route-owned open handlers and loading snippets.
- Reader Active Filter now lives in `ReaderActiveFilter.svelte`, keeping the
  shelf author-filter badge and clear action out of global CSS.
- Reader Text Search Results now lives in `ReaderTextSearchResults.svelte`,
  moving text-match result rows and query-candidate chips out of the route while
  preserving route-owned navigation callbacks.
- Reader Shelf Work Results now lives in `ReaderShelfWorkResults.svelte`,
  moving shelf-result rows, selected-work state, facet chips, and the author
  filter badge into a scoped component.
- Reader work-row styles are now component-local across text search results,
  shelf work results, and author-expanded work lists instead of global
  `app.css` rules.
- Reader async surfaces now use `ReaderLoadingRows.svelte`,
  `ReaderLoadingStrip.svelte`, and `ReaderErrorPanel.svelte`, preserving the
  elapsed-second loading contract while moving skeleton and error styles out of
  the route and global CSS.
- Reader Contents List now lives in `ReaderContentsList.svelte`, moving sidebar
  page-segment navigation and its scroll-list styles out of the route and
  global stylesheet.
- Reader Selected Word Panel now lives in `ReaderSelectedWordPanel.svelte`,
  keeping desktop word/oracle briefing display, generation controls, and
  selected-word typography component-local.
- Reader Apparatus Tabs now lives in `ReaderApparatusTabs.svelte`, moving the
  mobile Structure, Word, Oracle, and Evidence tab bar and its fixed-position
  styles out of the route and global stylesheet.
- Reader Desk Empty now lives in `ReaderDeskEmpty.svelte`, giving discovery
  searches and author sections a shared, component-local empty-state primitive.
- Reader Text Search View now lives in `ReaderTextSearchView.svelte`, composing
  the text-search form, async states, result summary, result rows, pager, and
  empty state while leaving query state and navigation callbacks in the route.
- Reader Shelf Work View now lives in `ReaderShelfWorkView.svelte`, composing
  shelf cards, work filters, work async states, result rows, pager, and empty
  state while leaving filter state and API calls in the route.
- Reader Author Discovery View now lives in `ReaderAuthorDiscoveryView.svelte`,
  composing author filters, author sections, async states, author groups, pager,
  and empty state while leaving author/filter state and API calls in the route.
- Reader Context Sidebar now lives in `ReaderContextSidebar.svelte`, composing
  structure, contents, and selected-word briefing panels while leaving data
  refresh and navigation callbacks in the route.
- Reader Passage View now lives in `ReaderPassageView.svelte`, composing
  passage error/loading states, page navigation, current division, text leaves,
  and source details while leaving route state and navigation callbacks in the
  route.
- Reader Discovery View now lives in `ReaderDiscoveryView.svelte`, composing
  discovery header, mode chooser, text search, shelf/work discovery, and author
  discovery while leaving URL state, timers, and API calls in the route.
- Reader page formatting helpers now live in `src/lib/reader/page-formatting.ts`,
  moving pure candidate, shelf, author-section, pagination, and discovery-title
  logic out of the route.
- Reader index storage helpers now live in `src/lib/reader/index-storage.ts`, moving
  session storage validation, TTL construction, and write error handling out of
  the route while the route applies restored values to Svelte state.
- Reader Desk Chrome now lives in `ReaderDeskChrome.svelte`, composing the top
  navigation, theme controls, language selector, index summary, catalog error,
  and address lookup while leaving state changes in the route.
- Reader Selected Work Desk now lives in `ReaderSelectedWorkDesk.svelte`,
  composing the selected work Object Card and work dossier while leaving
  loading, retry, and division navigation callbacks in the route.
- Reader loading timer bookkeeping now lives in `src/lib/reader/loading-timers.ts`,
  moving interval start, reset, elapsed-second calculation, and stop-all cleanup
  out of the route while elapsed Svelte state remains route-owned.
- Reader Shell now lives in `ReaderShell.svelte`, moving the reader grid,
  sidebar frame, and remaining reader layout selectors out of the route and
  global stylesheet. Selected-work, discovery, desk-kicker, and page-segment
  styles now live with their owning components.
- Reader author, facet, synthetic-author, and selected-work display helpers now
  live in `src/lib/reader/page-authors.ts`, keeping route logic focused on state
  changes and API orchestration instead of pure display derivation.
- Reader route-state helpers now live in `src/lib/reader/page-routing.ts`,
  covering default reader addresses, canonical reference detection, work
  metadata readiness, address formatting, and current route-state derivation
  outside the Svelte route.
- Reader route orchestration now uses a shared workspace-state binding layer:
  `reader-route-workspace-state.ts`, with content and discovery loading flows moved
  to dedicated loader modules (`reader-route-content-loaders.ts` and
  `reader-route-discovery-loaders.ts`).
- Reader index summary helpers now live in `src/lib/reader/index-stats.ts`,
  moving author-section totals, stats lookup/upsert behavior, default catalog
  selection, and stats target construction out of the route.
- Reader page navigation helpers now live in `src/lib/reader/page-navigation.ts`,
  covering shelf active-state checks, selected-segment checks, current reading
  work references, and search-result work references outside the route.
- Learn page styles now live in `routes/learn/+page.svelte`, removing the
  `orion-learn-*` page-specific block from global `app.css` while keeping the
  Learn route below the preferred 1000-line ceiling.
- Word Desk async activity now has a focused `DeskActivityLedger.svelte`
  component and `desk-activity.ts` timer helper, so lookup, translation,
  word-index, section-browse, MOTD, and paradigm waits can surface elapsed
  seconds through one stable visualization.
- Word Desk lookup waiting markup now lives in `DeskLookupLoadingPanel.svelte`,
  with the elapsed timer visible in the large lookup panel instead of hidden in
  route-local state.
- Word Desk word-index orchestration for nearby/browse loading, request state
  transitions, and earmark toggles now lives in
  `webapp/src/lib/desk/desk-word-index.ts`, reducing `DeskRouteController.svelte`
  to orchestration boundaries.
- Word Desk Forms/paradigm display now lives in `DeskParadigmPanel.svelte`,
  with pure display helpers in `desk-paradigm.ts` and component-local
  `orion-paradigm-*` / `orion-learning-*` styles instead of route-local markup
  or global `app.css` rules.
- Word Desk enrichment/retry sequencing is now extracted into
  `webapp/src/lib/desk/desk-workflows.ts` and covered by
  `webapp/src/lib/desk/desk-workflows.test.ts`.
- Word Desk URL-state parsing now lives in `desk-route.ts`, covering route
  list params, load/prefill flags, language/tool params, clear-route checks,
  and stable desk route keys outside the Svelte route.
- Word Desk browser storage helpers now live in `desk-storage.ts`, covering
  MOTD local cache, word-index earmarks, desk session state, and versioned
  storage cleanup with focused tests.
- Word Desk MOTD request orchestration now lives in
  `webapp/src/lib/desk/desk-motd-controller.ts`, covering initial/stale loads,
  refresh avoids, abort/reset lifecycle, normalization, errors, and cache writes
  outside `DeskRouteController.svelte`.
- `reader structure` and `/api/reader?mode=structure`.
- Division metadata overlay storage, sync, builder integration, and reviewed
  traditional mappings across all targeted texts (Bhagavadgītā chapters 1-18 and
  Republic Books 1-10), with regression tests in
  `tests/test_reader_division_metadata.py` preventing chapter/book coverage
  regressions.
- Structure-aware `resolve-address`, including exact `traditional_reference`
  lookups such as `BhG 9` and work-qualified labels such as `Republic Book 10`.
- `reader about` and `/api/reader?mode=about` Work Dossier payloads for
  deterministic "tell me about this book" summaries.
- Reader Work Dossier now presents structure counts, current-division context,
  and multiple reviewed division-note cards as provenance-bearing Orion
  objects, with the dossier surface extracted into a typed Svelte component
  instead of inline route markup.
- Mobile Apparatus Sheet now has concrete Structure, Word, Oracle, and Evidence
  panel contents instead of placeholders, using the same Object Card,
  provenance, selected-word, and current-division state as the desktop Reader.
- Greek canonical mapping baseline is now curated for Plato's Republic in
  `data/curated/reader_aliases/greek/republic.yaml` and a 10-book chapter
  scaffold is now curated in `data/curated/reader_work_maps/greek/republic.yaml`.
- Greek encounter normalization now feeds dictionary candidates into fuzzy
  lookup surfaces, so text forms such as `τελευταίαις` can reach both Diogenes
  and Bailly while the word-index sidebar matches non-Latin encounter anchors.
- The Word Desk now exposes an inspectable encounter reliability Oracle trace so
  reader-invoked forms, dictionary buckets, normalized candidates, and word-index
  anchors are surfaced in one provenance-bearing slice.

Remaining high-value slices:

- Complete the Reader Work Desk polish: visual QA across desktop, tablet, and
  mobile; then tune spacing, typography, and panel density from screenshots.
- Bring the Lexicon Word Desk into the same component system: Object Card,
  source-group Dossier sections, Oracle trace, provenance chips, and stable
  async indicators.
- Continue decomposing reader-specific route scaffolds and controls:
  (`webapp/src/lib/reader/ReaderRoutePage.svelte` and
  `webapp/src/routes/reader/+page.svelte`) and then reduce
  `webapp/src/lib/reader/ReaderRouteController.svelte` under the 1000-line ceiling
  by extracting further non-render orchestration.
  into focused orchestration plus component-owned concerns so the main route
  scripts stay under the 1000-line envelope.
- Decompose `webapp/src/lib/desk/DeskRouteController.svelte` similarly; it
  remains above the preferred line-ceiling and should move orchestration into
  focused helper modules.
- A richer dossier route or drawer for full author/work/chapter biography and
  evidence inspection.
- Generated, review-gated work and chapter bios after source-backed evidence
  coverage expands.

## UI Overhaul Execution Roadmap

Treat this as one overhaul, delivered in small verifiable slices.

1. **Foundation:** keep Orion vocabulary, localized copy, Object Card,
   Provenance Chip Row, Canon Table, loading strip, skeleton, and Apparatus
   Sheet primitives stable and covered by source-level web tests.
2. **Reader Work Desk:** make selected works, structure maps, current
   divisions, Work Dossiers, and Leaf reading feel like one manuscript desk.
   Use `reader structure`, `reader about`, and `resolve-address` without adding
   new browser-only contracts.
3. **Storage Hygiene:** complete migration of Word Desk storage orchestration
   (MOTD, word-index earmarks, desk session state) out of `routes/+page.svelte`
   into workspace helpers.
4. **Mobile Apparatus:** fill the bottom Apparatus Sheet with real Structure,
   Word, Oracle, and Evidence content rather than placeholders. Preserve one
   loading indicator per async operation with elapsed seconds.
5. **Lexicon Word Desk:** refactor the dictionary encounter page toward the
   same primitives: word Object Card, source Dossier sections, word-index Wheel,
   provenance chips, and Oracle trace for lookup/normalization/retrieval.
6. **Oracle Trace:** expose reader-invoked lookup reliability as a flat,
   inspectable chain: selected token, normalized candidates, dictionary buckets,
   word-index anchors, reader-search candidates, cache policy, and warnings.
7. **Library And Author Indices:** make shelves, author sections, and work
   lists use Canon Table/Object Card conventions where they carry structure or
   identity metadata.
8. **Research Metadata Loop:** expand Firecrawl-backed evidence artifacts and
   reviewed YAML overlays for work/chapter bios, aliases, and canonical work
   maps. Generated prose stays review-gated and provenance-marked.
9. **Visual QA:** verify desktop, tablet, and mobile screenshots for text
   overlap, cramped buttons, blank panels, one-note palettes, and broken async
   states before considering a slice complete.

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
- Treat oversized Svelte route files as active refactor targets. Routes should
  orchestrate URL state, data refresh, and component composition; new UI markup
  should be extracted into typed Svelte 5 components under `webapp/src/lib`.
  Once a surface has several related files, cluster it vertically under a clear
  product label such as `webapp/src/lib/desk/` instead of widening the root
  library directory.

## Persona Handoffs

- @architect: refine the `reader map` versus `reader structure` service
  contract and confirm the division metadata table boundary.
- @coder: implement the first Work Desk and Canon Table slice with tests once
  the detailed implementation plan is approved.
- @artisan: keep UI primitives reusable and avoid one-off reader-only styling.
- @auditor: review provenance, generated-text labeling, old-catalog
  compatibility, and citation mismatch handling.
- @scribe: update web UI docs and reader contract docs after implementation.

## Recent Work

- Extracted `DeskToolChip.svelte` from the oversized lookup desk route so
  source-selector chips use a typed Svelte 5 component with scoped CSS.
- Removed unused `orion-source-row` global styles and moved live
  `orion-tool-chip` styling out of `webapp/src/app.css`.
- Extracted `DeskSourceControls.svelte` so source/returned-tool fieldsets are
  composed in one typed component and `orion-source-grid` styling is scoped.
- Extracted `DeskPulseWidget.svelte` so the lookup loading visual and its
  keyframes are no longer global `app.css` rules.
- Extracted `DeskSearchReading.svelte` so query romanization feedback is scoped
  to a typed lookup-desk component rather than global CSS.
- Extracted `DeskColophonPanel.svelte` so encounter cache/request provenance is
  composed outside the oversized home route.
- Extracted `DeskHeroSearch.svelte` so the home route delegates language tabs,
  lookup input, romanization feedback, and clear/status controls to a typed
  desk component.
- Extracted `DeskMotdFolio.svelte` and `DeskMotdSkeletonList.svelte` so the
  margin recommendation folio, its loading skeleton, and folio-specific styles
  no longer live in the oversized route or global `app.css`.
- Extracted `DeskPageMarksPanel.svelte` so route/API share marks and
  endpoint-code styling live in a focused sidebar component.
- Extracted `DeskWordIndexEarmarks.svelte` so saved word-index links and
  earmark styling are scoped outside the oversized route/global `app.css`.
- Extracted `DeskWordIndexRail.svelte`, `DeskWordIndexSections.svelte`, and
  `DeskWordIndexRows.svelte` so the visible word-index sidebar instrument is
  componentized instead of deeply nested route markup and global CSS.
- Extracted `DeskComponentLedger.svelte` so compound/member evidence is a
  focused Word Desk surface with scoped component styles rather than old route
  markup and global `orion-component-*` rules.
- Extracted `DeskHeadwordBookplate.svelte` so dictionary groups and compound
  members share one illuminated Word object heading with scoped styles instead
  of duplicated route/component markup and global headword CSS.
- Extracted `DeskDictionaryGroupCard.svelte` so dictionary source groups,
  source/reader layer switching, retry controls, nested section expansion, and
  returned-ending notes render in a focused Word Desk component instead of the
  oversized route.
- Extracted Word Desk async activity, lookup loading, paradigm display, route
  parsing, and browser-storage helpers into focused components/modules with
  tests.
- Moved the shared Word Desk entry-frame rules for dictionary groups and
  component ledgers into `webapp/src/lib/desk/desk-entry.css`, keeping
  `webapp/src/app.css` below 900 lines while avoiding duplicated CSS in the two
  entry-rendering components.
- Extracted `DeskTopbar.svelte` so the Word Desk navigation, translation-mode
  selector, status counters, and theme controls live in a focused component
  with scoped topbar styles instead of route-owned markup and global `app.css`
  selectors.
- Extracted `DeskLookupResults.svelte` so lookup alerts, translation-enrichment
  notices, component ledger composition, dictionary witness framing, lookup
  loading, paradigm display, and empty-filter messaging live in one focused
  result surface instead of route-owned markup.
- Extracted `DeskSidebar.svelte` so the word-index rail, source controls,
  colophon, and page marks are composed through one focused sidebar surface, and
  fixed sidebar styles are scoped outside global `app.css`.
- Extracted `DeskPageShell.svelte` so the Word Desk main layout, topbar slot,
  content column, sidebar slot, and shell typography/background rules are scoped
  outside the route and global `app.css`.
- Word Desk endpoint builders now live in `desk-endpoints.ts`, with focused
  tests covering search cache-busting parameters, dictionary selection, and
  word-index nearby/sections/browse URLs.
- Word Desk word-index row merging, display labels, match-key generation, source
  labels, and item keys now live in `word-index.ts`, with focused tests and
  route guards preventing the pure helpers from returning to `routes/+page.svelte`.
- Word Desk MOTD normalization, presentability checks, warning filtering, source
  script cleanup, display labels, lookup hints, and note cleanup now live in
  `desk-motd.ts`, with focused tests and source guards preventing route-local
  helper regressions.
- Word Desk session/freshness helpers now live in `desk-session.ts`, covering
  stored-route matching, stale translated source layers, missing reader
  translations, valid stored tool filtering, returned-tool derivation, and the
  translated-source-tool predicate with focused tests.
- Clustered the Word Desk files under `webapp/src/lib/desk/`, including
  `Desk*.svelte` components, `desk-*.ts` helpers/tests, and `desk-entry.css`,
  so the earlier line-count extraction now has a surface-level navigation label
  instead of a flat pile of desk files in root `src/lib`.
- Extracted Word Desk entry grouping, section rendering, source-layer labels,
  component meaning display, source-reference sorting, and dictionary tool
  presentation helpers into `webapp/src/lib/desk/desk-entry.ts` with focused
  tests, reducing `routes/+page.svelte` below 2000 lines while leaving only
  route-state mutation wrappers in the route.
- Extracted Word Desk shareable URL construction into
  `webapp/src/lib/desk/desk-route.ts`, covering canonical desk URLs, MOTD
  recommendation links, word-index item links, and word-index section links
  with focused tests and guards preventing `visible`, `source`, and
  `dictionary` route-param assembly from returning to the Svelte route.
- Extracted Word Desk URL hydration parsing into
  `webapp/src/lib/desk/desk-route.ts` as a pure route-intent helper, covering
  language/query/tool parsing, load/prefill decisions, preserve/reset
  decisions, pending layer lists, and validated theme/backend/translation params
  while leaving Svelte `$state` assignment in the route.
- Extracted Word Desk lookup policy helpers into
  `webapp/src/lib/desk/desk-lookup.ts`, covering one-word validation,
  progressive enrichment first-pass mode selection, pending route-query
  comparison, and encounter-result view-state derivation for visible tools,
  source layers, expanded sections, and collapsed branches.
- Extracted Word Desk async lookup mechanics into
  `webapp/src/lib/desk/desk-lookup.ts`, covering encounter fetches with the
  minimum visible lookup delay and translation-cache retry POST construction,
  while keeping Svelte state flags, refresh sequencing, and result application
  explicit in the route.
- Extracted Word Desk current-status labels, status details, reader-layer
  colophon status, and translation-cache summary copy into
  `webapp/src/lib/desk/desk-status.ts`, with focused tests and guideline guards
  preventing route-local status/cache display policy from returning to
  `routes/+page.svelte`.
- Extracted Word Desk persistence orchestration into
  `webapp/src/lib/desk/desk-route-workspace.ts`, moving MOTD, word-index
  earmark, and desk session storage reads/writes behind browser-aware workspace
  helpers.
- Extracted Reader API URL construction and payload fetch helpers into
  `webapp/src/lib/reader/reader-api.ts`, covering catalog, facets, shelves,
  author sections, author/work search, text search, structure, dossier,
  contents/page-window, show, resolve-address, work metadata, and selected-word
  encounter briefing requests. The Reader route now delegates endpoint IO while
  retaining Svelte state, abort-controller, timer, and navigation ownership.
- Removed low-value Reader route passthrough wrappers for loading timers and
  selected-work display labels, replacing them with direct timer-helper calls
  and derived selected-work label state.
- Added SvelteKit guideline guards requiring extracted Word Desk components and
  styles to stay focused and preventing their selectors from returning to global
  CSS.
- Added SvelteKit guideline guards keeping both oversized routes listed in the
  active overhaul plan while they remain above the preferred 1000-line ceiling,
  and preserving the current `app.css` budget below 750 lines.
- Added SvelteKit guideline guards requiring Reader endpoint construction and
  encounter briefing fetches to remain under the `src/lib/reader/` surface
  cluster instead of returning to `routes/reader/+page.svelte`.
- Clustered Reader TypeScript domain helpers and tests under
  `webapp/src/lib/reader/`, including the Reader domain index, page formatting,
  page authors, page routing, page navigation, index stats, index storage,
  loading timers, API helpers, and the source-level loading guard.
- Split the oversized Reader source guard into `page-loading.test.ts` and
  `reading-surface-guards.test.ts`, with a SvelteKit guideline guard keeping
  both files below the 1000-line cap.
- Extracted Reader text/tokenization helpers into `src/lib/reader/text.ts`,
  covering selected-token cleanup, display/transliteration text selection,
  token part generation, and aligned transliteration fallback. The public
  `src/lib/reader` exports remain stable while `index.ts` falls below the
  1000-line ceiling.
- Extracted Reader route URL override application and next-URL construction
  into `src/lib/reader/page-routing.ts`, so the thin `routes/reader/+page.svelte`
  wrapper plus `ReaderRoutePage.svelte` now keeps the browser history side
  effect while delegating query-state assembly.
- Extracted Reader route startup/state orchestration and URL-parsing state hydrate
  application into `src/lib/reader/reader-route-workspace.ts`, including route
  defaults, restoration, URL state hydration, and cursor/statestore persistence
  plumbing. `ReaderRouteController.svelte` now delegates these lifecycle seams to
  the workspace module while preserving in-route data loading and selection actions.
- Extracted Reader selected-word context label helpers into
  `src/lib/reader/reader-word-context.ts`, keeping the public
  `src/lib/reader/index.ts` exports stable while reducing the Reader domain
  index below the 1000-line guard.
- Extracted Reader selected-word fetch/reset orchestration into
  `src/lib/reader/reader-selected-word-controller.ts`, covering word-context
  fetches, encounter briefing fetches, token selection, request aborts, and
  reset behavior with focused tests while reducing `ReaderRouteController.svelte`
  to 1446 lines.
- Extracted Word Desk MOTD request orchestration into
  `src/lib/desk/desk-motd-controller.ts`, covering initial/stale loads, refresh
  avoid lists, abort/reset lifecycle, normalization, errors, and cache writes
  with focused tests while reducing `DeskRouteController.svelte` to 1501 lines.

## Immediate Next Step

Continue the UI overhaul in this order:

1. Continue reducing `routes/+page.svelte` toward the preferred 1000-line route
   ceiling by extracting the remaining stateful lookup orchestration seams:
   first-pass search sequencing remains in-route; enrichment refresh sequencing
   and retry refresh sequencing now flow through `desk-workflows.ts`, and word-index
   orchestration now flows through `desk-word-index.ts`. MOTD request orchestration
   now flows through `desk-motd-controller.ts`, and status/cache copy has already
   moved to `desk-status.ts`.
2. Move the remaining Word Desk orchestration boundaries out of the route:
   storage synchronization and async activity coordination should stay under
   the `src/lib/desk/` surface label when they are desk-specific.
3. Continue reducing `app.css` by moving component-only Word Desk styles into
   the extracted Svelte components. Keep only tokens, app shell, theme, and
   shared primitive rules global.
4. Remaining selected-work/page orchestration is extracted into
   `src/lib/reader/reader-route-content-loaders.ts`; continue reducing
   `routes/reader/+page.svelte` and `ReaderRouteController.svelte` by extracting
   the remaining discovery/search orchestration (author sections, shelves, works,
   and text search loaders) into focused `src/lib/reader/` helpers.
5. Keep `src/lib/reader/index.ts` below the 1000-line guard; continue moving
   focused Reader helpers out only where they form clearer concept modules,
   while keeping the public Reader domain export stable.
6. Normalize async surfaces across the Word Desk so adding content uses
   skeletons, replacing content uses one spinner/badge/loading strip, and
   visible waits expose elapsed seconds.
7. (Done) Add the encounter reliability Oracle trace: selected surface form,
   normalized candidates, dictionary buckets, word-index anchors,
   reader-search candidates, cache policy, warnings, and provenance chips.
8. Expand traditional-structure metadata with curated aliases and work maps for
   Greek/Latin examples such as Plato's Republic, then add review-gated work
   and chapter bios from source-backed research artifacts.
9. Perform visual QA across desktop, tablet, and mobile for Reader Work Desk,
   Lexicon Word Desk, and mobile Apparatus before calling the overhaul stable.
