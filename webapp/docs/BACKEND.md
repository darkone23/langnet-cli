# Backend Integration

The web app is live-CLI first. Sample data remains in `src/lib/search-data.ts`
as a development fixture, but normal searches call the real LangNet CLI through
`/api/search`.

Current SvelteKit endpoints are `/api/search`, `/api/reader`,
`/api/word-index`, `/api/paradigm`, `/api/motd`, and
`/api/translation-cache`.

## Request Flow

The main UI builds an API URL like:

```txt
/api/search?backend=cli&language=lat&q=nox&dictionary=diogenes&translation=off&max_buckets=54321&max_gloss_chars=54321
```

`src/routes/api/search/+server.ts` validates:

- `language`: `san`, `grc`, or `lat`
- `backend`: `cli` or `sample`
- `translation`: `off`, `cache`, `populate`, `auto`, or `do-it-all`
- `dictionary`: `all` or valid tools for the selected language
- `q`: a single word

When `backend=cli` and a query is present, the API delegates to
`src/lib/server/langnet-cli.ts`.

## Reader Corpus API

The Reader Desk at `/reader` uses a separate read-only adapter,
`src/lib/server/reader-cli.ts`, and the `/api/reader` endpoint. This keeps corpus
reading separate from one-word dictionary encounters while still allowing a
selected passage word to continue into the existing dictionary page.

The endpoint follows the app's existing mode-based pattern:

```txt
/api/reader?mode=catalogs
/api/reader?mode=facets&catalog=development&language=grc
/api/reader?mode=groups&catalog=development&language=lat
/api/reader?mode=tags&catalog=development&language=san
/api/reader?mode=author-facets&catalog=development&language=lat
/api/reader?mode=shelves&catalog=development&language=san&sample_limit=2
/api/reader?mode=search&catalog=development&language=grc&q=logos&search_mode=fuzzy&limit=20
/api/reader?mode=works&catalog=development&language=grc&q=Odyssey&limit=40
/api/reader?mode=work&catalog=development&work=urn:cts:greekLit:tlg0012.tlg002
/api/reader?mode=contents&catalog=development&work=urn:cts:greekLit:tlg0012.tlg002&around=3.74&radius=4
/api/reader?mode=show&catalog=development&work=urn:cts:greekLit:tlg0012.tlg002&segment=3.74
/api/reader?mode=resolve-address&catalog=development&address=Od.%203.74
```

Catalog discovery delegates to the upstream CLI's `reader catalogs --output json`
contract. The web adapter keeps source-split audit artifacts resolvable for
explicit operator/debug requests, but filters them out of the learner-facing
`mode=catalogs` list. Product-facing catalog targets are:

- `development`: the verified unified local build
- `default`: the packaged/default build after intentional promotion

Audit artifacts such as `classics`, `sanskrit`, `perseus`, and `digiliblt` are
not shown as normal catalog choices when the CLI marks them with
`readiness: "audit_artifact"`. The Reader Desk defaults to the available
`development` catalog first, then `default`, then any remaining available
product catalog for the active language.

Reading flow:

- `facets`, `groups`, `tags`, `author-facets`, and `shelves` power Reader Desk
  discovery.
- `search` delegates to the CLI reader text-search index and accepts
  `search_mode`, `group`, `tag`, `collection`, `work_id`, `author_id`,
  `context`, `limit`, and `cursor`.
- `author-sections`, `authors`, and `works --author-id` provide native author
  index discovery by source-language section.
- `works` and `authors` pass CLI-native `--query`, `--limit`, and `--cursor`.
- `contents` uses `--limit` and `--cursor` for page chunks, and `--around` /
  `--radius` when opening an exact citation inside a work.
- `show` supplies the exact active segment and upstream next/previous pointers.
- `work` restores exact work metadata for shared URLs that start on a
  `work + segment` pair.
- Sanskrit passage rendering prefers upstream `display.primary`, so Devanagari
  appears where the reader CLI provides it while source transliteration remains
  available in the page detail.

The reader route serializes durable UI state into the browser URL. Supported
route parameters include `lang`, `catalog`, `view`, `q`, `text_q`,
`search_mode`, `group`, `tag`, `sort`, `page_cursor`, `author_section`,
`author`, `authors_cursor`, `works_cursor`, `contents_cursor`, `collection`,
`work`, `address`, `segment`, `word`, and `theme`. Session storage is only a
cache for already loaded index payloads that match the URL.

## Translation Cache API

`POST /api/translation-cache` lets the UI retry or clear rejected generated
translations for DICO, Gaffiot, and Bailly. The body can include either
`translation_id` or source projection fields such as `source_lexicon`,
`entry_id`, `occurrence`, `headword_norm`, and `source_text_hash`, plus optional
`max_retries` and `timeout_ms`. A successful retry clears the in-process search
response cache so the next encounter can show the refreshed translation layer.

The web API uses MessagePack only when the browser sends
`Accept: application/msgpack`; JSON remains the default-compatible format.

## CLI Invocation

The adapter runs the CLI through the parent `langnet-cli` project:

```sh
cd ..
just cli encounter <language> <word> <tool-filter> \
  --translation-mode <mode> \
  --output json \
  --max-buckets <n> \
  --max-gloss-chars <n>
```

The default CLI directory is `..`. Override it with:

```sh
LANGNET_CLI_DIR=/path/to/langnet-cli
```

The `just cli ...` and `just cli-encounter` recipes use the same variable.

The default timeout is five minutes because `translation=auto` or
`translation=populate` can populate caches and may be slow on a cold lookup.

The adapter builds a deterministic subprocess environment for CLI calls. It
preserves the server process environment, sets `NO_COLOR=1`, and appends
`$HOME/.local/bin` to `PATH` if `HOME` is available. This protects Latin grammar
lookups when a dev server was started from an environment that can run Vite but
cannot otherwise discover user-local tools such as `whitakers-words`.

## Progressive Translation

The browser does not block the first readable result on slow translation modes.

The UI defaults to `auto`. When the selected translation mode is `auto`,
`populate`, or `do-it-all`, the UI:

1. sends an initial `translation=cache` request
2. renders the cached result as soon as it returns
3. checks whether cached DICO/Gaffiot buckets still have FR source text without
   Reader EN
4. starts a second request with the selected slow translation mode only when that
   missing translation condition is present
5. replaces the result with the enriched payload if the second request succeeds

If the user starts another search while the slow request is still running, the old
response is ignored. If the slow request fails, the cached result remains visible
and the enrichment error is shown separately.

The API remains synchronous. The progressive behavior currently lives in the
Svelte UI rather than in a backend job queue.

## Tool Filtering

The CLI accepts a single tool filter argument, while the web UI can represent
multiple source-tool choices.

Mapping rules:

- `dictionary=all` -> CLI `all`
- one selected dictionary -> that tool
- multiple selected dictionaries -> CLI `all`, then the adapter filters returned
  buckets back down to requested tools

After a search completes, the UI also provides live returned-tool filtering. That
filter is client-side and does not call the backend again.

## Data Mapping

The CLI response is normalized into `EncounterResult` and `EncounterBucket`.

Primary sources:

- `display.meanings`: reader-facing meanings, source refs, entries, and display
  glosses.
- `display.meanings[*].entries`: witness metadata such as source tool,
  dictionary, headword, source ref, and translation metadata.
- `display.meanings[*].evidence_gloss`: fuller same-entry source evidence when
  available.
- `display.components` / `components`: component lookup evidence for compounds,
  including member role, morphology, lookup terms, and dictionary meanings.
- `buckets[*].witnesses`: raw witnesses and source text when available.
- `ranking`: source tools, lemma ranks, learner order, and reasons.
- `translation_cache`: cache state shown in the UI sidebar.

The adapter derives:

- bucket display text
- source refs
- witnesses
- language layers
- translation notes
- evidence notes
- source-tool filtering
- DICO/Gaffiot translation pairing
- component dictionary entries for compound members

## Nearby Word Index

The encounter payload can include `word_index.anchors[]`. These anchors are
useful context, but they are not always the same thing as the returned headword.
For compound Sanskrit lookups, anchors can include component entries. For example,
`varnamala` can return component anchors for `varṇa` and `mālā` while the primary
bucket is `varṇamālā`.

The web UI therefore builds nearby-index candidates in this order:

1. the reader-entered query
2. encounter lexeme anchors, bucket lemmas, and witness headwords
3. embedded `word_index.anchors[]`

This keeps the source neighborhood centered on the actual encounter result when
the dictionary index can resolve the query directly, while still preserving
component anchors as fallbacks when the primary forms do not resolve.

The native section rail uses two index paths. The main section button opens a
dictionary encounter for the section's alphabet headword. Greek and Latin use
the upstream section `anchor.query`; Sanskrit prefers the section display
transliteration because encoded source keys such as `k`, `K`, or `A` are useful
for source ordering but can be poor encounter queries. The rail's single
`Browse section` action calls
`word-index browse <language> --source all --prefix <section-anchor>`, which
returns grouped source-native rows. The web adapter preserves the CLI's
`grouped-source-native` order and keeps each source/dictionary group in its own
returned order; it does not treat `word-index list --source all` as the native
browse contract.

Browse and nearby payloads may carry grouped homograph metadata. The adapter
preserves `homograph_count`, `homograph_policy`, `source_entry_count`, and
`source_entries` so the UI can render one headword row with an entry count
instead of repeating visually identical rows such as `ह / ha`.

For translated meanings, the CLI may provide a short `display_gloss` and a fuller
English `evidence_gloss`. When the fuller text clearly extends the short reader
line, the adapter promotes `evidence_gloss` into the Reader EN display and
translation target text. This comparison ignores punctuation differences because
DICO and Gaffiot may use different separators in preview text and full entry text.

## Compound Components

Some Sanskrit lookups return compound analysis as `display.components` or
top-level `components`. For example, `ashtanga` can return component entries for
`aṣṭan` and `aṅga`, with Heritage morphology plus linked DICO meanings.

The adapter keeps these as `EncounterResult.components` instead of merging them
into the main headword buckets. They are still dictionary evidence: source refs,
source tools, source languages, lookup terms, and full component glosses are
preserved. The UI shows them in a separate component-entry lane so the learner can
study the parts without losing the primary entry for the searched word.

Component payloads can arrive with preview-length `display_gloss` values while
the same component meaning carries the full upstream entry in `evidence_gloss`.
The adapter promotes the longer component `evidence_gloss` directly instead of
running secondary component lookups. This keeps compound study cards aligned with
the full entries returned by the CLI for source refs such as
`dico:1.html#afga#1:0`.

Component DICO/Gaffiot translations can arrive as separate `sources:
["translation"]` meanings with the same source ref as the French source meaning.
The adapter pairs those into a single component meaning with `translation`
metadata, so the UI can expose the same Reader EN / Source toggle used by normal
DICO and Gaffiot entries. French-only component meanings also participate in the
progressive translation check, so `translation=auto` can run when the main
headword buckets are already readable but component entries still need Reader EN.

## Long Diogenes Entries

Diogenes often returns contiguous dictionary entries split across source refs like:

```txt
diogenes:00
diogenes:00:00
diogenes:00:00:00
diogenes:00:01
```

The UI relies on those refs to group and order the entry. The number of `:`
segments after `diogenes:` becomes the visual indentation depth.

The CLI can return a clipped `display_gloss` even when the web request sets
`max_gloss_chars=54321`. When a Diogenes `display_gloss` ends in an ellipsis and
the same meaning includes a longer `evidence_gloss`, the adapter uses the fuller
evidence text as the bucket `display_gloss`. This prevents the web UI from showing
avoidable clipped reader text.

If no fuller same-entry source text is available, the UI leaves the clipped line
visible and labels it as source-provided clipping.

## Translation Layers

DICO, Gaffiot, and Bailly can produce source-language entries with optional
English reader translations.

The adapter pairs translated and source buckets when they share:

- translation-capable source tool: `dico`, `gaffiot`, or `bailly`
- source ref
- headword

The UI then exposes a Reader EN / Source toggle only when the group actually has
translation-layer data. French source text is not presented as English when the
translation cache is missing.

When translated and source buckets are merged, the merged bucket keeps reader
evidence on the reader side. French source evidence remains in
`translation.source_text`; it is not joined into the reader `evidence_note`.

For example, Gaffiot `nox` and DICO `purusa` return short English
`display_gloss` previews, full English translations in `evidence_gloss`, and full
French source buckets. Bailly behaves the same when the translation cache has a
Reader EN hit; when it does not, the UI keeps the French source visible rather
than presenting it as English. The adapter renders the full English text in
Reader EN and keeps the French text behind the Source toggle when both layers
are available.

## Failure Mode

If the CLI fails, the API returns a `502` JSON payload with:

- the original query parameters
- `backend: "cli"`
- empty `buckets`
- empty `source_tools`
- a user-facing `error`

The API does not silently replace live failures with sample data. That keeps
backend problems visible during development and testing.

## MOTD Integration

`/api/motd` adapts the CLI word recommendation feature for the sidebar's
Marginal word panel.

Normal load:

```sh
cd ..
just cli word-of-day all \
  --count 1 \
  --level beginner \
  --translation-mode cache \
  --candidate-source auto \
  --output json
```

Refresh:

```sh
cd ..
just cli word-of-day all \
  --count 1 \
  --level beginner \
  --translation-mode cache \
  --candidate-source llm \
  --fresh \
  --avoid <recent-keys> \
  --nonce <random-value> \
  --output json
```

The distinction is intentional. Normal load should be cache-friendly and stable.
Refresh should hit the LLM path so the learner can receive a genuinely fresh set
of words.

The server keeps a small in-memory recent-key list for avoid hints. Cache misses
and refresh requests forward recent keys to the CLI so the web layer does not
reinforce the same Sanskrit/Greek/Latin set indefinitely. Normal MOTD responses
are cached according to `suggested_ttl_seconds`; refresh responses also update
the normal cache slot so a successful manual refresh sticks for later normal
loads.

The browser also stores successful MOTD payloads in `localStorage` with the same
TTL cap used by the server. On a later page load, valid local MOTD data is read
before the first client render. Fresh data is shown immediately while the page
checks `/api/motd` in the background. Stale-but-valid data also stays visible
while the page shows the same refreshing treatment used for manual refreshes. If
no valid local MOTD exists, the page shows the loading skeleton while
`/api/motd` loads. Refresh requests, including automatic replacement of stale
local data, include the browser's currently visible MOTD keys as avoid hints so
repeat suppression still works after a server restart.

Known upstream caveat: the CLI can return a structurally valid recommendation
whose summary, display, and source evidence do not fully agree. The web app
renders the payload conservatively but does not try to correct those semantics.
Examples seen during testing include `luna` displaying as `luno` and source
evidence supporting a related verb while the card gloss says "moon."

The web app also does not synthesize native-script MOTD headwords. Greek
currently arrives from the CLI with Unicode display forms such as `φύσις`.
Sanskrit may arrive with a roman `display` such as `jala`, plus canonical fields
such as `canonical_name: "जल"` and `canonical.transliteration: "jala"`. The web
adapter treats those canonical fields as authoritative display data.

The preferred long-term shape is still an explicit script-aware display block:

```json
{
	"display_forms": {
		"native": "कर्म",
		"roman": "karma",
		"canonical": "कर्म",
		"script": "deva"
	}
}
```

The web adapter already preserves `display_forms`, `forms`, `canonical`, or
similarly named top-level/UI fields when present.

## Paradigm Integration

Encounter responses can include `paradigm_resolution`, which is normalized by
`src/lib/paradigm-resolution.ts` and rendered as grammar-reading candidates in
the main result column. These candidates are not synthetic guesses from the UI;
they are evidence forwarded by the CLI, including provenance, native analyses,
functional analyses, and an optional `paradigm_request`.

The web app loads full tables lazily. When a candidate has a `paradigm_request`,
the UI calls:

```txt
/api/paradigm?language=<lang>&lemma=<lemma>&kind=<declension|conjugation>&...
```

`src/routes/api/paradigm/+server.ts` validates the request, delegates to
`paradigmFromCli`, and normalizes returned tables with `src/lib/paradigm.ts`.
Loaded slots are displayed near the dictionary entry so morphology supports the
encounter instead of becoming a separate drill surface.

Latin paradigm resolution depends on Whitaker's Words being visible to the CLI
process. The adapter's subprocess `PATH` handling is therefore part of the
grammar contract, not just an operations convenience.

Sanskrit Heritage table requests are source-backed and can be sensitive to the
lemma spelling used by the resolver. The web endpoint preserves the resolver's
first request, but if a Sanskrit request returns no forms it can retry conservative
fallback spellings such as dropping a Heritage sense suffix and removing IAST
diacritics. This is a web-layer recovery path, not a substitute for upstream
resolver precision.

The UI treats zero-form paradigm payloads as unavailable tables even when the CLI
returns a structurally valid `langnet.paradigm.v1` payload. That protects the
learner from seeing `Table loaded` when the source only returned a warning such
as `heritage_declension_table_not_found`.
