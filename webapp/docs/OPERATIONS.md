# Operations

This document covers the day-to-day mechanics for running and checking the web
UI during development.

## Development Server

Start the app:

```sh
just dev
```

By default this binds Vite to:

```txt
0.0.0.0:43210
```

The configured allowed hosts are:

```txt
langnet.computerdream.club
project-orion.net
```

Use a different bind address or port when needed:

```sh
HOST=127.0.0.1 PORT=5173 just dev
```

## Who Owns The Dev Server

It is reasonable for a human operator to own the long-running dev server. The web
app can be checked through the existing server with:

```sh
curl -sS -o /tmp/langnet-web-root.html -w '%{http_code} %{content_type}\n' \
  http://127.0.0.1:43210/
```

If another server is already running on `43210`, do not start a competing server
unless you intentionally want a second Vite instance on another port.

## Port 43210 Is Busy

Find the process:

```sh
lsof -iTCP:43210 -sTCP:LISTEN
```

or:

```sh
ss -ltnp 'sport = :43210'
```

Then stop the process that owns the server. Prefer stopping it from the terminal
where it was started. Use `kill <pid>` only when the owner terminal is gone.

## Verification Commands

Fast project verification:

```sh
just verify
```

This runs:

- `just test`
- `just format-check`
- `just check`
- `just build`

Run only the fast unit/regression tests:

```sh
just test
```

These tests cover display-model and nearby-index candidate behavior that is easy
to regress without a browser screenshot or a running server.

Smoke the web API through the live backend while `just dev` is running:

```sh
just smoke-api
```

Smoke the direct CLI path without the web server:

```sh
just smoke-cli
```

## Web API Probes

Reader and search endpoints include `Server-Timing` headers. `reader_cache` and
`search_cache` indicate an in-process exact-request cache hit; restart the
preview/dev process to pick up code changes or clear those in-memory caches.

Summarize a result:

```sh
just api-summary lat nox gaffiot cache
just api-summary lat nox lewis_1890 off
just api-summary grc logos bailly cache
just api-summary san पुराण dico cache
just api-summary lat nexus diogenes off
```

The `just api` recipe URL-encodes query parameters, so non-ASCII words are safe:

```sh
just api san पुराण dico cache
```

## MOTD Probes

Normal cache-friendly MOTD:

```sh
just motd
```

The browser uses localStorage as an immediate MOTD prefill, but normal page load
does not call this endpoint when a stored MOTD card is already present. That
keeps tab restore and browser tab discard from turning an already-rendered page
into a fresh recommendation request.

Refresh path, intentionally LLM-backed:

```sh
just motd-refresh
```

The refresh path may be slow. The web endpoint allows up to 120 seconds by
default. The broader API timeout cap is 300 seconds.

## Resume And Font Stability

The dictionary desk stores the current encounter and word-index section data in
`sessionStorage` for short-lived tab restoration. A URL with `q=` is
prefill-oriented by default; it should only relaunch the lookup when the URL
explicitly includes `load=yes`. Links with `load=no` or `prefill=yes` should not
restore an old rendered encounter over the prefilled form.

The Reader Desk stores durable reader navigation state in the browser URL.
`sessionStorage` is only a cache for the currently visible
language/catalog/author index payload. Returning to the route in the same tab can
reuse that cache when it matches the URL; a fresh tab should still reconstruct
the requested state from query parameters and API calls.

App fonts are declared in `src/app.css` with explicit `unicode-range` values for
Latin, Latin Extended, Greek, Greek Extended, and Devanagari. They use
`font-display: block` so the layout splash and the browser font policy agree:
avoid painting fallback text and then swapping to Noto after the app is visible.

## Word Index Probes

Native section order:

```sh
curl -sS 'http://127.0.0.1:43210/api/word-index?mode=sections&language=grc&source=all' |
  jq '{order, sections: [.sections[] | {label, transliteration, anchor: .anchor.query}]}'
```

Grouped browse rows:

```sh
curl -sS 'http://127.0.0.1:43210/api/word-index?mode=browse&language=san&source=all&prefix=ha&count=12' |
  jq '{request, order, items: [.items[] | {primary: .display.primary, transliteration: .display.transliteration, homograph_count, source_entry_count, source_counts}]}'
```

The learner-facing browse list should come from top-level `items[]` when the CLI
provides it. `browse.groups[].items[]` are source/dictionary detail windows and
are useful for diagnostics, but rendering them as the main list can produce
repeated rows such as `ha ha ha`.

Direct CLI comparison, without touching the web server:

```sh
cd ..
just cli word-index sections san --source all --output json
just cli word-index browse san --source all --prefix ha --limit 12 --output json
```

The expected order policy for section browsing is source-native or grouped
source-native, not generic Latin key ordering.

## Distinguishing Web Bugs From Upstream Bugs

Start with the API:

```sh
just api-summary <lang> <word> <dictionary> <translation>
```

If the API data has the expected fields but the UI renders the wrong layer,
grouping, or expansion state, the bug is likely in `src/routes/+page.svelte`.

If the API already has clipped, missing, or semantically odd text, inspect direct
CLI output:

```sh
just cli-encounter <lang> <word> <dictionary> <translation>
```

If the direct CLI returns the same clipped or odd text, the web layer should not
pretend it can recover missing source data. It should show the returned text and,
when appropriate, a quiet note such as `Returned text ends here.`

If direct CLI fails but the web API succeeds, record the direct CLI failure as an
upstream instability before changing the web adapter. One known example is direct
`lat nox gaffiot cache`, which may fail upstream while the API smoke path remains
healthy.

If Latin grammar disappears only through the web API, check whether the server
process can discover Whitaker's Words. The adapter now appends `$HOME/.local/bin`
to CLI subprocess `PATH`, and `src/lib/server/langnet-cli-env.test.ts` protects
that behavior. A quick symptom probe is:

```sh
just api lat ratio all cache | jq '{source_tools, analysis_sources: [.analysis[].source], candidate: .paradigm_resolution.candidates[0]}'
```

Expected: `source_tools` includes `whitakers`, analysis includes `whitaker`, and
the paradigm candidate has `kind: "declension"` rather than
`unresolved_reason: "no_grammar_evidence"`.

## Formatting

Format everything:

```sh
just format
```

Check formatting only:

```sh
just format-check
```

Prettier is configured in `.prettierrc` and ignores generated output, lockfiles,
and local development directories via `.prettierignore`.
