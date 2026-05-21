# Regression Cases

These words exercise the source shapes that have driven the current UI and
adapter behavior. They are not exhaustive tests. They are a small working set for
checking whether the reader still presents real CLI results sanely.

Run the API smoke set while `just dev` is running:

```sh
just smoke-api
```

Run direct CLI probes without the web server:

```sh
just smoke-cli
```

Run fast unit/regression tests without a server:

```sh
just test
```

Run the full local web verification set:

```sh
just verify
```

These cover display-model edge cases and source-neighborhood candidate ordering
that are easier to lock down in code than by manual visual inspection.

## `lat nox`, Gaffiot

```sh
just api-summary lat nox gaffiot cache
```

Purpose:

- exercises a long Gaffiot entry
- checks French source plus Reader EN layer pairing
- checks that `max_gloss_chars=54321` is not the web-layer limit

Expected shape:

- one Gaffiot bucket
- `target_len` and `source_len` should both be large
- Reader EN / Gaffiot FR layers should be available in the UI

Known caveat:

- direct `just cli-encounter lat nox gaffiot cache` may fail upstream with a CLI
  TypeError. `just smoke-cli` uses `lat nox all cache` so direct smoke remains
  stable while `smoke-api` still covers the exact Gaffiot web path.

## `san purusa`, DICO

```sh
just api-summary san purusa dico cache
```

Purpose:

- exercises a long DICO entry
- checks DICO French source plus Reader EN layer pairing
- checks that DICO numeric suffix cleanup does not damage readable text

Expected shape:

- one DICO bucket
- `target_len` and `source_len` should both be large
- Reader EN / DICO FR layers should be available in the UI

## `san पुराण`, DICO

```sh
just api-summary san पुराण dico cache
```

Purpose:

- exercises Devanagari query encoding through the web API
- checks multiple DICO buckets for one query
- checks that long translated DICO entries expand inside the active layer

Expected shape:

- two DICO buckets: usually `pura.na` and `puraa.na`
- both buckets should have Reader EN and DICO FR text
- the long `puraa.na` entry may still end with an upstream ellipsis

UI rule:

- if Reader EN is active, expansion must stay English
- if DICO FR is active, expansion must stay French
- if the returned text ends with an ellipsis and no fuller same-layer text exists,
  the UI may show `Returned text ends here.`

## `lat nexus`, Diogenes

```sh
just api-summary lat nexus diogenes off
```

Purpose:

- exercises Diogenes split entries
- checks grouping by dictionary source and lexeme
- checks source-ref ordering and indentation
- checks branch collapse behavior

Expected shape:

- multiple Diogenes buckets
- buckets should group into contiguous `nexus` and `necto` entries
- refs like `diogenes:00`, `diogenes:00:01`, and `diogenes:00:01:00` should
  determine reading order and indentation

## `lat ratio`, Whitaker Grammar

```sh
just api lat ratio all cache | jq '{source_tools, analysis_sources: [.analysis[].source], candidate: .paradigm_resolution.candidates[0]}'
curl 'http://127.0.0.1:43210/api/paradigm?language=lat&lemma=ratio&kind=declension&timeout_ms=120000' |
  jq '{lemma, block_count: (.paradigms|length), slot_count: ([.paradigms[]?.slots|length] | add // 0)}'
```

Purpose:

- exercises Latin grammar evidence from Whitaker's Words through the web server
- checks that server-launched CLI subprocesses can discover user-local binaries
- protects against losing paradigm resolution when the dev server's `PATH` omits
  `$HOME/.local/bin`

Expected shape:

- `source_tools` includes `whitakers`
- `analysis_sources` includes `whitaker` and `diogenes`
- the first paradigm candidate is a noun declension for `ratio`
- `unresolved_reason` is null

Protected by:

- `src/lib/server/langnet-cli-env.test.ts`
- `src/lib/paradigm-ui.test.ts`

## Paradigm UI Curation

```sh
curl 'http://127.0.0.1:43210/api/search?backend=cli&language=san&q=ashtanga&dictionary=all&translation=cache&max_buckets=8&max_gloss_chars=600' |
  jq '{count: (.paradigm_resolution.candidates|length), candidates: [.paradigm_resolution.candidates[] | {lemma, confidence, unresolved_reason, request: (.paradigm_request != null)}]}'
curl 'http://127.0.0.1:43210/api/paradigm?language=san&lemma=a%E1%B9%85ga_1&kind=declension&gender=Mas&timeout_ms=120000' |
  jq '{lemma, warnings, slot_count: ([.paradigms[]?.slots|length] | add // 0), form_count: ([.paradigms[]?.slots[]?.forms|length] | add // 0)}'
```

Purpose:

- checks that noisy resolver output does not become a noisy first-view grammar
  panel
- checks that empty source-backed tables are treated as unavailable, not loaded
- checks the Sanskrit fallback path for Heritage lemma spelling when it can
  recover a real table
- checks that large tables can be grouped into didactic sections

Expected shape:

- `ashtanga` may return several upstream candidates, but the UI first view should
  prefer the resolved fetchable candidate and report hidden alternates quietly
- Sanskrit `aṅga_1` table loading should not show `Table loaded` for a zero-form
  payload
- when the web endpoint can recover with a conservative fallback such as `anga`,
  the returned paradigm should include forms
- large Latin conjugations such as `amo` should not render as one undifferentiated
  flat list

Protected by:

- `src/lib/paradigm-ui.test.ts`

## `san varnamala`, Word Index

```sh
cd ../langnet-cli
just cli encounter san varnamala all --translation-mode cache --cache-policy read-only --output json --max-buckets 12 --max-gloss-chars 1400
just cli word-index nearby san varnamala --source all --radius 1 --output json
just cli word-index browse san --source all --prefix d --limit 12 --output json
just cli word-index browse san --source all --prefix ha --limit 20 --output json
just cli encounter grc n diogenes --translation-mode cache --cache-policy read-only --output json --max-buckets 3
just cli encounter grc logos bailly --translation-mode cache --cache-policy read-only --output json --max-buckets 3
just cli encounter lat nox lewis_1890 --translation-mode off --cache-policy read-only --output json --max-buckets 3
just cli encounter san ka cdsl --translation-mode cache --cache-policy read-only --output json --max-buckets 3
```

Purpose:

- exercises Sanskrit compound/component word-index context
- checks that the source neighborhood stays centered on `varṇamālā`
- checks that component anchors such as `varṇa` / `vara` do not override the
  searched headword
- checks that a missed encounter can still fall back to the reader-entered query
  for nearby-index lookup
- checks that native section browsing uses grouped source-native order rather
  than collapsed canonical-key list order
- checks that learner browse uses top-level grouped homograph rows rather than
  source-detail rows
- checks that Bailly and Lewis 1890 remain accepted as standalone upstream
  source filters

Expected shape:

- encounter bucket lemmas include `varramala` and `varṇamālā`
- direct nearby lookup for `varnamala` resolves to `वर्णमाला`
- embedded component anchors may include `vara` / `वर`, but those are fallback
  candidates, not the primary highlighted source row
- failed encounter payloads do not prevent `wordIndexCandidateQueries` from
  returning the original one-word query
- native section clicks resolve to alphabet headword encounters: Greek/Latin use
  the section anchor query, while Sanskrit uses the section display
  transliteration so `क` opens `ka` rather than the empty `k` lookup
- browse payloads report `request.homographs: "grouped"` and
  `order.policy: grouped-source-native`
- browse payloads expose learner rows in top-level `items[]`; `groups[].items[]`
  remain source/dictionary detail windows
- `ha` groups visually identical headwords such as `ह / ha` into one learner row
  with `homograph_count`, `source_entry_count`, and `source_counts`
- Bailly may return French source evidence without a cached Reader EN layer; that
  is a cache/upstream state to surface, not a reason to relabel French as English
- Lewis 1890 returns English Latin entries directly under `source_tool:
lewis_1890`

Protected by:

- `src/lib/search-data.test.ts`
- `src/lib/word-index-fallbacks.test.ts`
- `src/lib/word-index.test.ts`

## Display Model Unit Cases

```sh
just test
```

Purpose:

- checks Sanskrit native title display and roman fallback transliteration
- checks single-grapheme Sanskrit forms such as `da` and `daa`
- checks Sanskrit component terms such as `dhātrī`, `putra`, and `k.rrta`
- checks Greek display forms, including Greek Extended one-grapheme `ὁ`
- checks Latin explicit initial/rest splitting
- checks search-term romanization for native Sanskrit and Greek input

Expected shape:

- Sanskrit and Greek result headers prefer native-script primary titles when a
  matching anchor is available
- supporting forms render as compact metadata, not as competing titles
- Devanagari titles split the first grapheme from the remainder while keeping
  the word visually connected
- Sanskrit Devanagari search terms such as `येनाक्षरसमाम्नायमधिगम्य` expose an
  IAST reading aid without changing the lookup query
- Greek search terms such as `λόγου` expose a roman reading aid without changing
  the lookup query
- Latin titles keep the plain lexeme path

Protected by:

- `src/lib/headword-display.test.ts`
- `src/lib/search-romanization.test.ts`

## Tab Restore And Font Stability

Manual checks:

```sh
just verify
```

Then, with the human-owned dev server running:

- Open a dictionary encounter, leave the tab, and return. The rendered encounter
  should remain settled; the page should not automatically rerun `/api/search`,
  `/api/motd`, or `/api/word-index` unless the URL explicitly has `load=yes` or
  the learner clicks a refresh/search control.
- Open a prefill-only URL with `load=no` or `prefill=yes`. It should fill the
  search form without restoring an old encounter over the form.
- Open `/reader`, let the author index render, navigate away, and return in the
  same tab. The visible author index should restore without repeating the initial
  catalog and author-section request chain.
- On `/reader`, move through an author section, author list cursor, work, page
  cursor, text-search query, discovery group/tag, passage segment, and selected
  word. The URL should carry the state; a refresh or copied URL should
  reconstruct the same reader position as far as the upstream cursor remains
  valid.
- Watch first paint for Latin, Greek, Greek Extended, and Devanagari text. The
  splash should hide fallback-font rendering, and the visible app should not
  perform a late Noto font swap.

Implementation notes:

- Main desk restore state lives in `sessionStorage` under
  `orion-desk-state:v2`.
- Reader index restore state lives in `sessionStorage` under
  `orion-reader-index-state:v1`.
- MOTD cards live in `localStorage` under `orion-motd-cache:v3`.
- App font faces are declared directly in `src/app.css` with script-specific
  `unicode-range` values and `font-display: block`.
- `src/lib/component-gloss.test.ts`
- `src/lib/motd-cache.test.ts`

## `san ashtanga`, Component Entries

```sh
cd ../langnet-cli
just cli encounter san ashtanga all --translation-mode cache --cache-policy read-only --output json --max-buckets 12 --max-gloss-chars 54321
just cli encounter san aṅga dico --translation-mode cache --cache-policy read-only --output json --max-buckets 12 --max-gloss-chars 54321
```

Purpose:

- checks compound component display for `aṣṭan` and `aṅga`
- checks that `aṅga` component cards use full upstream component evidence when
  it is present
- protects against showing only the short component preview when full backend
  evidence is available

Expected shape:

- raw `ashtanga` component payload may contain a short `display_gloss`
- the same component meaning should include the full entry in `evidence_gloss`
- web adapter output should promote the longer component evidence text

Protected by:

- `src/lib/component-gloss.test.ts`

## Reader Desk Discovery And Text Search

```sh
curl 'http://127.0.0.1:43210/api/reader?mode=shelves&catalog=development&language=san&sample_limit=2' |
  jq '{mode, count: (.items|length), first: .items[0]}'
curl 'http://127.0.0.1:43210/api/reader?mode=search&catalog=development&language=grc&q=logos&search_mode=fuzzy&limit=5' |
  jq '{mode, count: (.items|length), first: .items[0]}'
curl 'http://127.0.0.1:43210/api/reader?mode=facets&catalog=development&language=lat' |
  jq '{mode, count: (.items|length)}'
```

Purpose:

- checks that Reader Desk discovery routes reach shelves, facets, groups, tags,
  and author facets through `/api/reader`
- checks that text search uses the reader search index path instead of work
  title search
- checks URL state for `view`, `text_q`, `search_mode`, `group`, `tag`, `sort`,
  and `page_cursor`

## MOTD Daily Rotation

```sh
just motd
just motd-refresh
```

Purpose:

- checks that the sidebar does not sit forever on built-in starter words
- checks that local MOTD storage honors the returned TTL instead of expiring after
  a short prefill window
- checks that refresh requests send current visible MOTD keys as avoid hints
- checks that repeated server-side generations have recent-key memory available
  so the web layer does not reinforce one recurring Greek candidate

Protected by:

- `src/lib/motd-cache.test.ts`

## When A Case Fails

Use this order:

1. Run `just api-summary ...` to see what the web API returns.
2. Run `just cli-encounter ...` to see whether the direct CLI returns the same
   shape or fails upstream.
3. If the API has correct data but the UI is wrong, inspect `src/routes/+page.svelte`.
4. If the direct CLI fails but the API succeeds, note it as upstream/direct-CLI
   instability before changing the web adapter.
5. If both direct CLI and API return clipped or semantically odd text, treat it as
   source/CLI behavior unless the web adapter is dropping fields.
