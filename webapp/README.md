# LangNet Web UI

LangNet Web UI is a SvelteKit reader interface for live one-word dictionary
encounters in Sanskrit, Greek, and Latin.

The application is intentionally reader-first: the main column groups returned
dictionary evidence by source and lexeme, presents contiguous entries in source
order, and keeps metadata in the card chrome so the dictionary text remains the
center of attention.

The current stack is Bun, SvelteKit, Tailwind CSS v4, DaisyUI v5, lucide icons,
Fontsource Noto Serif fonts, and `svelte-adapter-bun`.

## Quick Start

```sh
bun install
just dev
```

The development server binds to `0.0.0.0:43210` by default.

Useful URLs:

- Local: `http://127.0.0.1:43210`
- Configured remote host: `http://langnet.computerdream.club:43210`

Override the default bind address when needed:

```sh
PORT=5173 HOST=127.0.0.1 just dev
```

## Daily Commands

```sh
just install         # install/update Bun dependencies
just                 # list recipes
just doctor          # verify bun, just, jq, and langnet-cli availability
just dev             # start Vite on 0.0.0.0:43210
just dev-open        # start Vite and ask Vite to open a browser
sudo just caddy-proxy # proxy :80 to the dev server on 127.0.0.1:43210
just test            # run fast unit/regression tests
just check           # run svelte-check
just check-watch     # run svelte checks in watch mode
just format          # format source and docs with Prettier
just format-check    # verify formatting without writing changes
just build           # build the production bundle
just verify          # run test + format-check + check + build
just preview         # preview the built app with Vite
just preview-logs    # preview the built app with request logs
just start           # run the Bun adapter production server after build
just api             # probe the live API; requires just dev
just api-summary     # summarize a live API response with jq
just search          # alias for the live /api/search probe
just search-live     # alias for the live /api/search probe
just motd            # probe the MOTD endpoint; requires just dev
just motd-refresh    # probe the LLM-backed MOTD refresh path
just motd-summary    # summarize a live MOTD response with jq
just cli-tools lat   # list CLI tools for a language
just cli-encounter   # run a live CLI encounter directly
just smoke-api       # run current API regression probes; requires just dev
just smoke-cli       # run current direct CLI regression probes
```

`just cli ...`, `just cli-tools`, `just cli-encounter`, and `just smoke-cli`
use `LANGNET_CLI_DIR` when it is set. API and CLI probe recipes also honor
`MAX_BUCKETS`, `MAX_GLOSS_CHARS`, and `TIMEOUT_MS`.

`just caddy-proxy` honors `PORT` and `CADDY_FROM`; for example,
`CADDY_FROM=:8080 PORT=5173 just caddy-proxy` proxies port 8080 to a dev server
on port 5173.

Latin grammar depends on Whitaker's Words being visible to the CLI process. The
web adapter appends `$HOME/.local/bin` to the subprocess `PATH` so server
launches from narrower shells can still find user-local tools such as
`whitakers-words`.

## Project Shape

Important paths:

- `src/routes/+page.svelte`: main search UI, live filters, result grouping, reader
  presentation, and theme switching.
- `src/routes/reader/+page.svelte`: read-only Reader Desk for browsing cataloged
  works, opening contents, reading exact segments, and sending selected words
  back into the dictionary encounter flow.
- `src/routes/learn/+page.svelte`: standalone Foster-first learning workflow for
  morphology concepts, native grammar terms, and source-backed practice links.
- `src/app.css`: Tailwind v4, DaisyUI theme tokens, and project-specific reader
  styling.
- `src/lib/reader.ts`: shared reader catalog, work, and segment types.
- `src/lib/learn.ts`: reusable learning concept map for Foster gateways,
  Sanskrit/Greek/Latin terms, reader questions, and practice words.
- `src/lib/headword-display.ts`: script-aware display model for Sanskrit, Greek,
  and Latin result titles.
- `src/lib/word-index.ts`: native index response model, section lookup targets,
  browse homograph helpers, and source-order labels.
- `src/lib/word-index-fallbacks.ts`: ordered nearby-index query candidates for
  keeping source neighborhoods centered on the encounter result.
- `src/lib/motd-cache.ts`: shared MOTD TTL, recent-key, and browser cache
  helpers.
- `src/lib/paradigm.ts` and `src/lib/paradigm-resolution.ts`: grammar/paradigm
  response normalization.
- `src/routes/api/search/+server.ts`: `/api/search` endpoint and request
  validation.
- `src/routes/api/word-index/+server.ts`: `/api/word-index` endpoint for native
  sections, nearby neighborhoods, and grouped browse rows.
- `src/routes/api/motd/+server.ts`: `/api/motd` endpoint for the Marginal word
  panel.
- `src/routes/api/paradigm/+server.ts`: `/api/paradigm` endpoint for lazy form
  tables.
- `src/routes/api/reader/+server.ts`: `/api/reader` endpoint for reader catalog,
  work, contents, segment, and address-resolution calls.
- `src/lib/server/langnet-cli.ts`: live CLI adapter and normalization layer.
- `src/lib/server/reader-cli.ts`: read-only reader CLI adapter with explicit
  catalog selection.
- `src/lib/search-data.ts`: shared types, language/tool metadata, and sample
  fallback data.
- `vite.config.ts`: Vite host, port, and allowed host settings.
- `svelte.config.js`: Bun adapter and Svelte runes configuration.
- `justfile`: development, verification, and API probe recipes.

Web design docs:

- `docs/UI.md`: current page layout, reader principles, result grouping, Forms,
  and visual direction.
- `docs/SVELTEKIT_GUIDELINES.md`: SvelteKit and Svelte 5 implementation
  boundaries for route shape, component extraction, state, async UI, and tests.
- `docs/LEARNING_UI.md`: Foster-first "Learn this form" north star and first
  integration slice.
- `docs/BACKEND.md`: SvelteKit API adapter contracts.
- `docs/REGRESSION_CASES.md`: live CLI/API cases that should keep working.

## Live Backend

The default backend is the live LangNet CLI. The web app expects to live inside
the CLI tree:

```txt
langnet-tools/
  langnet-cli/
    webapp/
```

If the CLI lives elsewhere, set:

```sh
LANGNET_CLI_DIR=/path/to/other/langnet-cli just dev
```

The API calls:

```sh
cd ..
just cli encounter <language> <word> <tool-filter> \
  --translation-mode <mode> \
  --output json \
  --max-buckets <n> \
  --max-gloss-chars <n>
```

Current UI requests use `max_buckets=54321` and `max_gloss_chars=54321` so the
web layer is not the limiting factor for long dictionary entries. Some upstream
fields may still arrive as short preview text; the adapter promotes fuller
same-entry source evidence when the CLI provides it.

## API

Search endpoint:

```txt
GET /api/search
```

Common parameters:

- `backend=cli|sample`
- `language=san|grc|lat`
- `q=<single-word>`
- `dictionary=all` or one or more `dictionary=<tool>` values
- `translation=off|cache|populate|auto|do-it-all`
- `max_buckets=<number>`
- `max_gloss_chars=<number>`
- `timeout_ms=<number>`

Examples:

```sh
curl 'http://127.0.0.1:43210/api/search?backend=cli&language=lat&q=nox&dictionary=diogenes&translation=off&max_buckets=54321&max_gloss_chars=54321'
curl 'http://127.0.0.1:43210/api/search?backend=cli&language=lat&q=nox&dictionary=lewis_1890&translation=off&max_buckets=54321&max_gloss_chars=54321'
curl 'http://127.0.0.1:43210/api/search?backend=cli&language=grc&q=logos&dictionary=bailly&translation=cache&max_buckets=54321&max_gloss_chars=54321'
curl 'http://127.0.0.1:43210/api/search?backend=cli&language=san&q=dharma&dictionary=all&translation=cache'
```

Search currently accepts one word at a time.

MOTD endpoint:

```txt
GET /api/motd
```

Normal page load requests all three supported languages, uses `candidate_source=llm`, and
keeps translation cache-friendly. The API asks the LLM for candidate words, then
builds a source-backed card through the CLI using a language-appropriate fast
verification source instead of probing every dictionary on first paint. The web
route skips the second LLM card-finalization call for reliability and uses a
bounded 12-second budget for the live LLM path. The browser
also stores successful MOTD payloads in `localStorage` using the returned TTL, so
a recent MOTD can render immediately while the page still asks the endpoint for a
current cache-friendly recommendation.

The Refresh button is intentionally different: it requests `candidate_source=llm`
with `refresh=1`, so the API asks the CLI for fresh LLM-generated candidates with
recent keys in the avoid list. Refresh results update the browser cache and the
server's normal MOTD cache slot so a successful refresh sticks.

Examples:

```sh
curl 'http://127.0.0.1:43210/api/motd?language=all&count=1&translation=cache&candidate_source=llm&timeout_ms=12000'
curl 'http://127.0.0.1:43210/api/motd?language=all&count=1&translation=cache&candidate_source=llm&refresh=1&timeout_ms=12000'
```

Word index endpoint:

```txt
GET /api/word-index
```

Common modes:

- `mode=sections`: native alphabet/varnamala sections for one language
- `mode=nearby`: source-neighborhood rows around one query
- `mode=browse`: grouped source-native rows for a section prefix

Browse mode uses the CLI's learner-facing top-level `items[]` when present.
Source/dictionary detail windows remain available in `browse.groups[].items[]`,
but the UI should not repeat those rows as the primary learner list.

Examples:

```sh
curl 'http://127.0.0.1:43210/api/word-index?mode=sections&language=san&source=all'
curl 'http://127.0.0.1:43210/api/word-index?mode=browse&language=san&source=all&prefix=ha&count=12'
curl 'http://127.0.0.1:43210/api/word-index?mode=nearby&language=grc&source=all&q=logos&radius=5'
```

Current endpoints:

- `GET /api/search`
- `GET /api/reader`
- `GET /api/word-index`
- `GET /api/paradigm`
- `GET /api/motd`
- `POST /api/translation-cache`

Reader endpoint:

```txt
GET /api/reader
```

Common modes:

- `mode=catalogs`: list learner-facing reader catalogs
- `mode=facets`, `mode=groups`, `mode=tags`, `mode=author-facets`: list
  discovery affordances
- `mode=shelves`: list discovery shelves for a language
- `mode=search`: search indexed reader text
- `mode=works`: search/list works for a catalog and language
- `mode=work`: resolve exact work metadata
- `mode=contents`: list a first, cursor, from, or around segment window for a work
- `mode=show`: read one exact segment
- `mode=resolve-address`: resolve a friendly address such as `Od. 3.74`

Examples:

```sh
curl 'http://127.0.0.1:43210/api/reader?mode=catalogs'
curl 'http://127.0.0.1:43210/api/reader?mode=works&catalog=development&language=grc&q=Odyssey&limit=5'
curl 'http://127.0.0.1:43210/api/reader?mode=shelves&catalog=development&language=san&sample_limit=2'
curl 'http://127.0.0.1:43210/api/reader?mode=search&catalog=development&language=grc&q=logos&search_mode=fuzzy&group=epic&limit=5'
curl 'http://127.0.0.1:43210/api/reader?mode=work&catalog=development&work=urn:cts:greekLit:tlg0012.tlg002'
curl 'http://127.0.0.1:43210/api/reader?mode=contents&catalog=development&work=urn:cts:greekLit:tlg0012.tlg002&around=3.74&radius=2'
curl 'http://127.0.0.1:43210/api/reader?mode=show&catalog=development&work=urn:cts:greekLit:tlg0012.tlg002&segment=3.74'
```

The reader adapter delegates catalog discovery to `reader catalogs --output json`
and filters audit artifacts out of the learner-facing catalog list. On this
machine the Reader Desk prefers the verified unified `development` catalog until
`default` is intentionally promoted. Source-split catalogs such as `classics`,
`sanskrit`, `perseus`, and `digiliblt` are still resolvable for explicit
operator/debug requests when the CLI reports them, but they are not normal
product choices. Author discovery uses `author-sections`, `authors --section`,
and `works --author-id`, so the Reader Desk can show one native source-language
index per language. The Reader Desk renders a page as a chunk of source segments
and uses contents cursor pagination for next/previous page flow. Opening an
exact citation still uses `show` to locate the active segment, then loads a
surrounding page.

Reader route state is URL-resumable where upstream cursors and identifiers allow
it. The `/reader` query string can carry `lang`, `catalog`, `view`, `q`,
`text_q`, `search_mode`, `group`, `tag`, `sort`, `page_cursor`,
`author_section`, `author`, `authors_cursor`, `works_cursor`,
`contents_cursor`, `collection`, `work`, `address`, `segment`, `word`, and
`theme`.
Session storage remains a matching-cache optimization, not the canonical reader
state.

Paradigm endpoint:

```txt
GET /api/paradigm
```

The encounter payload may include `paradigm_resolution.candidates[]`. The UI
shows those as compact grammar readings and calls `/api/paradigm` only when the
reader asks to load a table.

Example:

```sh
curl 'http://127.0.0.1:43210/api/paradigm?language=lat&lemma=ratio&kind=declension&gender=feminine'
```

## Page State URLs

The UI state is encoded in the page URL so searches can be linked, reloaded, and
shared. Opening a URL with `q=` restores the form and filter state. It only runs
the lookup automatically when `load=yes` is present.

The address bar is kept prefill-oriented by default: after a manual search, the
browser URL drops `load=yes` so a restored or discarded tab does not eagerly run
the lookup again. The sidebar's Page link includes `load=yes` when it is showing
a result that can be shared as an immediately loading encounter.

Common page parameters:

- `lang=san|grc|lat`
- `q=<single-word>`
- `dictionary=all` or repeated `dictionary=<tool>` values
- `visible=<tool>` for live post-result filtering
- `backend=cli|sample`
- `translation=off|cache|populate|auto|do-it-all`
- `theme=manuscript|vespers`
- `load=yes` to run the lookup on page load
- repeated `source=<bucket-id>`, `expand=<section-key>`, and
  `collapse=<section-key>` for reader-layer and section state

Example:

```txt
/?lang=lat&q=nox&dictionary=all&translation=auto&theme=manuscript&load=yes
```

## Search Workflow

1. Choose a language: Sanskrit, Greek, or Latin.
2. Choose source tools before searching, or use explicit `dictionary=all`.
3. Submit a single word.
4. Translation defaults to `auto`. For `cache` and `off`, the UI waits for one
   lookup. For `auto`, `populate`, and `do-it-all`, the UI first asks for cached
   results, renders them, then only runs the slow translation pass if cached
   DICO/Gaffiot/Bailly results still contain French source text without Reader EN.
5. Results are grouped by dictionary source and lexeme.
6. Returned source tools can be filtered live after results arrive.
7. DICO and Gaffiot groups show Reader EN / Source toggles only when that language
   layer is relevant.
8. Diogenes sections are rendered in source-ref order with indentation based on
   source-ref depth.

Inline expansion controls are reserved for dictionary text itself: long sections,
or clipped sections when fuller same-entry detail is available. For translated
DICO and Gaffiot entries, expansion stays inside the active Reader EN or source
layer rather than switching to mixed evidence text.

This progressive behavior keeps dictionary text readable while cache population or
translation generation continues. Warm-cache results do not trigger the expensive
second pass. If the slow pass fails, the cached result remains on screen and the UI
reports the enrichment error separately.

## Design Direction

The interface follows a "classic manuscript meets Tufte CSS meets DaisyUI"
direction:

- reader-first layout rather than dashboard density
- bookish serif type for dictionary text
- restrained manuscript colors and small source emblems
- compact card chrome for source, section, witness, and layer metadata
- DaisyUI controls for tabs, buttons, selects, badges, alerts, joins, stats, and
  loading states
- custom CSS only where the reader layout needs source-specific presentation

The design goal is not to hide evidence. The goal is to keep the first encounter
calm, then make the path to source detail obvious when detail is needed.

## More Documentation

- [docs/BACKEND.md](docs/BACKEND.md) explains the live CLI integration and data
  normalization.
- [docs/UI.md](docs/UI.md) records the result presentation model and interface
  principles.
- [docs/REGRESSION_CASES.md](docs/REGRESSION_CASES.md) lists the current smoke
  words and what each one is meant to protect.
- [docs/OPERATIONS.md](docs/OPERATIONS.md) covers dev-server ownership,
  verification, MOTD probes, and how to separate web-layer bugs from upstream CLI
  behavior.
