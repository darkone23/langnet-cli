# Writing SvelteKit Guidelines

These rules govern Project Orion UI implementation in `webapp/`. Use this
document with `webapp/docs/UI.md`: `UI.md` defines the product design language;
this file defines how to write SvelteKit code that can sustain it.

Reference sources:

- SvelteKit project structure: <https://svelte.dev/docs/kit/project-structure>
- SvelteKit routing: <https://svelte.dev/docs/kit/routing>
- SvelteKit loading data: <https://svelte.dev/docs/kit/load>
- SvelteKit state management: <https://svelte.dev/docs/kit/state-management>
- Svelte `.svelte` files: <https://svelte.dev/docs/svelte/svelte-files>
- Svelte `$props`: <https://svelte.dev/docs/svelte/$props>
- Svelte scoped styles: <https://svelte.dev/docs/svelte/scoped-styles>
- Svelte global styles: <https://svelte.dev/docs/svelte/global-styles>

Firecrawl research artifacts for these pages are stored under
`.firecrawl/sveltekit-ui-overhaul/`.

## Core Direction

Build the app as SvelteKit and Svelte 5. Do not add Alpine.js or htmx for UI
behavior unless a specific integration need is documented first. Those tools
solve problems Svelte already owns here: component state, reactive rendering,
event handling, and route-aware navigation.

SvelteKit routes should orchestrate. Components should render. Helpers should
transform. Server adapters should fetch. When a file starts doing all four, it
needs to be split.

## File Boundaries

Official SvelteKit structure puts reusable library code in `src/lib` and route
files in `src/routes`. Follow that split:

- `src/routes/**/+page.svelte`: route shell, URL state, high-level page
  orchestration, and composition of components.
- `src/routes/**/+server.ts`: HTTP endpoint adapters.
- `src/lib/*.svelte`: shared primitives and broadly reusable components.
- `src/lib/*.ts`: shared pure helpers, payload normalization, route-state
  parsing, and type-oriented utilities.
- `src/lib/<surface>/*`: vertically clustered components, helpers, styles, and
  focused tests for one product surface once extraction would otherwise leave a
  flat directory full of similarly named files. The Lexicon Word Desk lives in
  `src/lib/desk/*`; Reader-specific domain helpers and tests live in
  `src/lib/reader/*`.
- `src/lib/server/*.ts`: server-only helpers.

Do not solve a giant file by creating a giant horizontal directory. If a route
family gains a clear concept label, give it a folder and keep navigation by
surface: `desk`, `reader`, `learn`, or another product object name.

Size guidance:

- Prefer components under 500 lines.
- Treat 500-1000 lines as a warning zone.
- Do not grow route files beyond 1000 lines without an explicit extraction plan.
- A file over 2000 lines is an active refactor target, not a place for new UI
  markup.
- Source-level guard tests should follow the same pressure: split large guard
  files by product concern instead of letting one test file become a new
  monolith.

Indentation guidance:

- Avoid templates nested more than 4-5 levels deep.
- If markup reaches 6+ levels, extract a component or snippet.
- If a branch contains multiple independent panels, extract each panel.
- Do not hide deep nesting by moving it wholesale into another file. Split by
  purpose.

## Component Design

Use Svelte 5 `$props` with typed props for component inputs.

Good component shape:

```svelte
<script lang="ts">
	import type { ReaderStructureNode } from './reader';

	type Props = {
		structure: ReaderStructureNode[];
		onOpenDivision: (workId: string, citation: string) => void;
	};

	let { structure, onOpenDivision }: Props = $props();
</script>
```

Component rules:

- Pass data down and callbacks up.
- Keep data loading outside presentational components unless the component is
  explicitly a data boundary.
- Keep callbacks specific: `onOpenDivision(workId, citation)` is better than
  passing a whole route object.
- Use local snippets for small repeated markup inside one component.
- Extract a new component when a snippet becomes a separate concept or carries
  its own branching.

## Route Design

Routes should remain readable as page orchestration:

- parse URL state;
- load or refresh payloads;
- maintain route-level `$state`;
- compose components;
- synchronize URL and session storage when needed.

Do not keep large repeated UI regions in a route. The Reader route has moved
below the active-refactor threshold, but it is still over the preferred route
ceiling; new work should continue reducing route-owned orchestration. The
Lexicon route is also over the preferred size and should be split as the
overhaul reaches the Word Desk.

SvelteKit reuses page and layout components during navigation. Do not assume a
route component is destroyed and recreated on every URL change. Reset state
explicitly when route state changes, or key a subtree deliberately.

## Data Loading

Prefer SvelteKit `load` when data is needed for initial page rendering and can
be derived from URL state. Keep `load` functions pure; do not mutate shared
stores or module-level state inside them.

Use component-side fetches when the interaction is explicitly client-driven:

- selected-word briefing generation;
- reader page-window navigation after an already selected work;
- cache population or translation refresh;
- optional panels that should not block the initial route.

Use URL search params for shareable state. This matches SvelteKit guidance and
Project Orion behavior:

- language;
- selected work or segment;
- address lookup;
- search filters;
- selected word when it should restore on reload.

Use session storage only for ephemeral performance state that should not define
the canonical page identity.

## State Management

Do not put request-specific state in shared server modules. SvelteKit servers
are long-lived and shared. Use request data, cookies, database storage, or API
payloads instead.

For client state:

- use `$state` for route-local interactive state;
- use `$derived` for values computed from route state;
- pass values into components through props;
- prefer universal reactivity over Svelte stores unless a store-like contract is
  genuinely needed.

Avoid side effects in derived helpers. If a helper changes URL, storage, or
network state, name it as an action and keep it out of `$derived`.

## Styling

Use DaisyUI components and Tailwind utility classes for standard web controls,
spacing, layout, responsive behavior, and modern interaction feel. Use
Project Orion CSS only where the design system needs a manuscript-specific
surface that DaisyUI does not provide directly.

Svelte scoped styles are the default home for component-local Orion rules.
The official Svelte docs describe `<style>` CSS as scoped to the component by
default. Use `:global(...)` only when a selector intentionally reaches outside
the component.

This project also has a large shared `app.css`; use it deliberately:

- app shell, theme tokens, font imports, Tailwind/DaisyUI setup, and page-level
  layout rails belong in `app.css`;
- component-specific Orion rules belong in the component `<style>`;
- large new global CSS sections should be grouped by component prefix;
- use stable `orion-*` class names for source-level regression tests.

Current extracted scoped-style primitives:

- `OrionObjectCard.svelte`
- `OrionProvenanceChips.svelte`
- `src/lib/desk/Desk*.svelte`, `src/lib/desk/desk-entry.ts`, and
  `src/lib/desk/desk-entry.css`
- `ReaderActiveFilter.svelte`
- `ReaderAddressLookup.svelte`
- `ReaderAuthorDiscoveryView.svelte`
- `ReaderAuthorList.svelte`
- `ReaderAuthorSearchForm.svelte`
- `ReaderAuthorToc.svelte`
- `ReaderCanonTable.svelte`
- `ReaderContextSidebar.svelte`
- `ReaderContentsList.svelte`
- `ReaderCurrentDivision.svelte`
- `ReaderDeskChrome.svelte`
- `ReaderDeskEmpty.svelte`
- `ReaderDeskHeader.svelte`
- `ReaderDiscoveryChooser.svelte`
- `ReaderDiscoveryHeader.svelte`
- `ReaderDiscoveryPager.svelte`
- `ReaderDiscoverySummary.svelte`
- `ReaderDiscoveryShelves.svelte`
- `ReaderDiscoveryView.svelte`
- `ReaderErrorPanel.svelte`
- `ReaderLeaf.svelte`
- `ReaderLoadingRows.svelte`
- `ReaderLoadingStrip.svelte`
- `ReaderPageNav.svelte`
- `ReaderPassageView.svelte`
- `ReaderSelectedWorkDesk.svelte`
- `ReaderShelfWorkResults.svelte`
- `ReaderShelfWorkSearchForm.svelte`
- `ReaderShelfWorkView.svelte`
- `ReaderSelectedWordPanel.svelte`
- `ReaderSourceDetails.svelte`
- `ReaderTextSearchForm.svelte`
- `ReaderTextSearchResults.svelte`
- `ReaderTextSearchView.svelte`
- `ReaderWorkDossier.svelte`
- `ReaderApparatusSheet.svelte`
- `ReaderApparatusTabs.svelte`
- `ReaderApparatusWordPanel.svelte`
- `ReaderApparatusOraclePanel.svelte`
- `ReaderApparatusEvidencePanel.svelte`

Avoid visual debt:

- no nested cards inside cards;
- no decorative gradients or orbs as default backgrounds;
- text must wrap inside controls on mobile;
- use fixed or constrained dimensions for repeated tool rows, tabs, and panels;
- do not scale font size with viewport width.

## Async UI

Project Orion standard:

- adding new content: skeleton rows;
- replacing existing content: keep the existing content visible and show one
  loading strip, spinner, or badge;
- visible waits should expose elapsed seconds when the route already tracks a
  timer;
- do not stack several loading indicators for the same operation.

## Project Orion Components

Current primitives:

- Object Card: first-class object summary. Use `OrionObjectCard.svelte`.
- Provenance Chip Row: visible provenance for curated, source-backed, reviewed,
  generated, or uncertain material. Use `OrionProvenanceChips.svelte`.
- Canon Table: hierarchical structure ranges and traditional references. Use
  `ReaderCanonTable.svelte`.
- Work Dossier: deterministic "tell me about this work" view.
- Leaf: passage reading surface.
- Apparatus Sheet: mobile Structure, Word, Oracle, and Evidence panels.

Implementation rule: when adding a new Orion primitive, create or extract a
focused component before adding a second large copy of the same pattern.
Do not keep local snippets for Object Card, Provenance Chip Row, or Canon Table
inside route files or apparatus panels.

## Testing

Use the existing lightweight source-level tests to protect structural contracts:

- component exists;
- route imports component rather than inlining large markup;
- CSS class exists;
- localization key exists;
- async timer or loading strip is wired.

Then run:

```bash
cd webapp
just test
just build
```

After frontend changes, rebuild production and restart the process listening on
`43210` so the process manager reloads the app.

## Refactor Checklist

Before adding UI to an existing Svelte file:

1. Check `wc -l`.
2. If the file is already over 1000 lines, extract first.
3. If the new markup creates 6+ indentation levels, extract a component.
4. If the component would need more than 12 props, consider grouping data into a
   typed view model helper.
5. Keep route-level data and component-level display separate.
6. Add or update source-level tests for the boundary.
7. Run `just test` and `just build`.

## Current Cleanup Targets

- `webapp/src/routes/+page.svelte`: split Lexicon Word Desk into object card,
  source dossier, word-index wheel, oracle trace, lookup execution, and loading
  components. Keep Word Desk-specific files clustered under
  `webapp/src/lib/desk/`; status, reader-layer, and cache-display policies
  belong in `desk-status.ts`, not in the route.
- `webapp/src/routes/reader/+page.svelte`: continue extracting Reader
  discovery, Work Desk, Leaf, and route-state helpers.
- `webapp/src/app.css`: move component-only rules into component styles where
  possible; keep shared Orion primitive styles global.
