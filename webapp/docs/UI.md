# UI Notes

The interface is a reader surface for word encounters, not an analytics
dashboard. It should keep the dictionary entry central while still exposing where
the evidence came from.

## Current Principles

- Search is one word at a time.
- Language mode is explicit: Sanskrit, Greek, or Latin.
- Native-script Sanskrit and Greek search input may show a quiet romanization
  line for pronunciation and orientation. This is a reading aid only; it does not
  change the lookup query or claim morphological analysis.
- `dictionary=all` is a first-class request value.
- Source-tool choices before search affect the backend request.
- Returned-tool choices after search are live client-side filters.
- Page state belongs in the URL so word encounters are reloadable and shareable.
- Results are grouped by dictionary source and lexeme.
- Compound component evidence is shown as secondary dictionary entries, not as
  loose metadata.
- Related source rows should remain contiguous.
- Result cards begin with dictionary text, not controls.
- Metadata belongs in compact card chrome.
- Expansion controls should appear only inline with dictionary text that is long,
  clipped, or has fuller same-entry detail available.
- DICO, Gaffiot, and Bailly expose Reader EN / Source layers only when
  relevant.
- Slow translation modes should not hide cached dictionary results while waiting
  for cache population or generation.

## Page Layout

The page uses a two-column layout on large screens:

- Main column: search form, loading state, grouped results.
- Topbar: compact translation mode control plus reader/night theme controls.
- Fixed sidebar rail: Marginal word, source worlds, returned worlds, endpoint
  preview, and cache state. On desktop it scrolls independently from the main
  reading column.

On smaller screens, the sidebar stacks below the main column.

The sidebar shows both the shareable page-state URL and the raw search endpoint.
The page-state URL restores language, word, dictionaries, returned-tool filters,
theme, backend, translation mode, and reader section state. A URL with `q=`
prefills the page; it only runs the lookup on page load when `load=yes` is also
present.

The live browser URL is intentionally prefill-oriented. Manual searches remove
`load=yes` from the address bar after the request is consumed, which prevents tab
restore or browser tab discard from unexpectedly launching a fresh lookup. The
sidebar Page link can still include `load=yes` for sharing an immediately loading
encounter.

The header includes the project title and motto:

```txt
Project Orion
Every day is a good day for learning.
```

The theme switch supports:

- `manuscript`: light reader theme
- `vespers`: dark reader theme

## Reader Desk

The `/reader` route is a read-only passage reader for cataloged source texts. It
is not a replacement for the one-word dictionary desk.

Principles:

- Start from the unified library, language, work, or address.
- Keep the book page as the largest and quietest visual surface.
- Show work title, author, library context, and current citation as compact orientation
  chrome.
- Treat next/previous as reading motion through the current work, similar to a
  Kindle or Scaife-style text page, not as generic search-result paging.
- Put work and author discovery in the main results surface. Sidebar panels are
  for contextual reading aids, not search result lists.
- Provide an author TOC organized by the active source language's alphabet:
  Greek letters for Greek, varnamala-style sections for Sanskrit, and Latin
  letters for Latin.
- Show one visible index per language. Catalog selection is an internal adapter
  concern and should not appear as a learner-facing dropdown. Source-specific
  audit catalogs are operator/debug artifacts, not product navigation.
- Keep library discovery separate from the book's table-of-contents/contents
  window. Discovery gets the reader to a work; the TOC or contents window keeps
  them oriented inside the work.
- Use learner-facing labels for library coverage. Internal catalog IDs,
  collection IDs, and import-history labels should not be prominent controls.
- Let a selected passage word continue into the existing dictionary encounter
  page instead of duplicating the full dictionary UI beside every passage.
- Keep corpus metadata and attribution detail secondary until upstream contracts
  and learner needs justify an "About this text" panel.
- Preserve source-native citation. Greek and Latin CTS-style paths and Sanskrit
  DCS sentence IDs should not be forced into one shared book/line metaphor.

Current behavior:

- The discovery surface defaults to a language-scoped browse when the query is
  empty.
- Discovery can pivot through shelves, facets, groups, tags, author facets,
  work-title search, author browse, and indexed text search without leaving the
  Reader Desk.
- Author discovery relies on CLI-native `author-sections`,
  `authors --section`, author query, and `works --author-id` contracts. The
  first author page preloads after the section index loads, and non-Latin section
  controls include roman hints such as `Π P` and `व va`.
- Returning to the Reader Desk in the same tab may restore the visible author
  index from `sessionStorage` instead of repeating the initial catalog and author
  requests. This is a resume optimization only; changing language, discovery
  filter, or text-search state still asks the API for fresh data.
- The Reader Desk treats the browser URL as canonical navigation state. Language,
  catalog, author section, author/work query, author and cursor positions,
  selected work, segment, selected word, text query, text-search mode, discovery
  group/tag, sort, page cursor, and theme are mirrored into query parameters so
  refresh, copy/paste, and browser back/forward can resume the same place as far
  as upstream cursors remain valid.
- The Book TOC panel shows the current page-local contents window, not a global
  library search.
- The central leaf renders one page at a time, where a page is a bounded chunk of
  source segments from `contents`. Exact citation opens use `show` to resolve the
  target and then render the surrounding chunk as the page.
- Sanskrit passage text prefers upstream display Devanagari where available and
  keeps transliteration in the source/detail area.

## Marginal Word

The Marginal word panel is backed by `/api/motd`.

Normal page load is cache-friendly. If a valid MOTD payload exists in browser
`localStorage`, the panel renders it immediately and does not automatically call
`/api/motd`. Stale payloads remain on screen until the learner asks for refresh,
so returning to a tab does not blank or churn the page. If no valid local payload
exists, the panel shows solid control placeholders and three result-shaped
skeleton cards while `/api/motd` loads. Built-in starter words should not
masquerade as daily recommendations.

Refresh is deliberately different. Clicking Refresh keeps the current cards on
screen, disables the small controls, and applies a subtle moving gloss animation
while the backend asks the CLI for LLM-generated fresh candidates. This avoids a
blanking flash while preserving the user's request for real randomness. Refresh
sends the current visible MOTD keys as avoid hints so a browser with a stored
folio can still discourage repeats after a server restart.

The `load=yes` / `prefill` toggle controls whether MOTD links immediately run the
word lookup or only fill the search form. Active MOTD links are marked when the
current page state matches the recommendation.

## Dictionary Index

The Dictionary index is a word-wheel neighborhood, not another result list. Its
job is to orient the reader near the resolved headword and provide nearby terms
for further lookup.

Lookup sequencing:

- Run `encounter` first for reader-entered words.
- Ask `/api/word-index` for the reader-entered query first.
- Use encounter lexeme anchors, bucket lemmas, and witness headwords as the next
  fallback tier.
- Use resolved `word_index.anchors[]` from the encounter payload only after the
  primary encounter values. Those anchors may include component lookups for
  compounds, so they should not replace the searched headword as the center of
  the source neighborhood.
- If the encounter lookup fails after accepting a valid one-word query, still
  ask `/api/word-index` for the reader-entered query so the learner can browse
  nearby source terms instead of losing the neighborhood panel.
- While encounter is pending, show the index as pending too; do not show a stale
  or raw-input neighborhood as if it were resolved.

Native section rail:

- Ask `/api/word-index?mode=sections` for the selected language.
- Render the returned section order directly: Greek alphabet, Sanskrit
  varṇamālā, or Latin alphabet.
- Clicking the main section letter opens a learner lookup for that alphabet
  headword. Greek and Latin use the section anchor query returned by upstream;
  Sanskrit uses the section's display transliteration first because dictionary
  keys such as `k` or `A` are not always the best encounter query.
- The single `Browse section` control in the rail header asks
  `/api/word-index?mode=browse` for the active section's anchor prefix. Browse
  rows are grouped by source/dictionary and preserve each group's source-native
  order.
- When upstream groups homographs, render one headword row and show the entry
  count, e.g. `20 entries`, rather than repeating the same native headword.
- Keep searched words on the nearby path. Browse is for entering a native index
  section; nearby is for orienting around a specific encounter.

Index row labels:

- `resolved term`: a row that matches the current encounter's resolved lexeme
  keys. There may be more than one for ambiguous or multi-lexeme lookups.
- `index anchor`: the anchor returned by the word-index neighborhood request.
  This is the center of that neighborhood, but it is not necessarily the only
  resolved term from encounter.
- `before` / `after`: neighboring entries in the dictionary/index order returned
  by the backend.
- `nearby`: a related item from the merged lexeme layer when the backend marks it
  as neither strictly before nor after.

The highlighted row does not need to appear first. It should appear in the
ordered neighborhood where the backend places it, ideally between before and
after rows. The UI should preserve backend order for source-local groups and use
the merged lexeme layer when it gives a clearer before/anchor/after balance.

Earmarks are reader conveniences. They should never change the active dictionary
filters or the resolved neighborhood for the current word.

## Result Grouping

The result list groups buckets by:

1. primary source tool
2. dictionary
3. lexeme/headword

Witness metadata is preferred for grouping. Bucket lemmas are fallback data.

Within each group, buckets are sorted by source ref. This is especially important
for Diogenes because split source refs form a single contiguous dictionary entry.
The UI should keep all Diogenes rows for the same word together so the reader can
move through the entry naturally.

## Component Entries

When the CLI returns component evidence for a compound, the UI places those
members above the gathered entries in a compact component-entry lane. These are
not decorative parse notes. They can be real DICO dictionary entries, sometimes
long, so they use the same result-card chrome, bookplate, reader font, source
labels, Reader EN / Source toggle, and inline expansion pattern as other
dictionary text.

Component entries remain separate from the searched headword. For `ashtanga`, the
main CDSL entry stays under `aṣṭāṅga`, while `aṣṭan` and `aṅga` can be read as
component evidence with their own source refs and glosses.

When a component payload contains a short `display_gloss` plus a fuller
`evidence_gloss`, the web adapter should render the fuller evidence text. For
`ashtanga`, the `aṅga` component should use the full `dico:1.html#afga#1:0`
evidence returned in the component payload, not the short preview line.

## Grammar Forms

When encounter data includes paradigm resolution, the UI shows a compact Forms
panel before dictionary groups. The panel should help the reader understand the
current word's grammatical shape without displacing the dictionary evidence.

Rules:

- Show candidate readings only when the backend returns them.
- Prefer resolved, fetchable readings in the first view.
- Hold back low-confidence unresolved alternates when a resolved reading exists;
  they are source ambiguity, not the main lesson.
- Keep readings compact: lemma, part of speech, paradigm kind, provenance, and
  the most useful feature labels.
- Load full paradigm tables only after the learner asks for them.
- Do not call a table loaded unless the source returns at least one form.
- Group large tables by useful grammatical dimensions such as number for
  declensions or mood / tense / voice for conjugations.
- Highlight forms that match the current encounter when table data is loaded.
- Treat unresolved candidates as quiet evidence, not as errors.
- Keep grammar close to the encounter. Do not turn the page into a conjugation
  dashboard.

## Result Group Anatomy

Each result group has:

- title: lexeme/headword
- small source emblem and source badge
- optional lead line from the first/root section
- compact chrome with reader/source layer, section count, witness count, and
  source icons
- optional Reader EN / Source toggle for DICO and Gaffiot translation layers
- reader sections in source order

The card chrome should remain quiet. It is there for orientation, not to compete
with the dictionary entry.

## Headword Display

Result and component titles use an explicit display model rather than browser
`::first-letter` splitting when the script is known.

Rules:

- Sanskrit titles render from a Devanagari `initial` plus `rest`. Single-grapheme
  forms such as `द` and `दा` still use the taller illuminated block.
- Sanskrit compounds may render component labels from roman/IAST input into
  Devanagari. The component evidence remains visually distinct from the main
  searched headword.
- Sanskrit multi-grapheme titles can include the Devanagari connector treatment
  so the word's top line feels continuous.
- Greek and Latin titles use the same explicit `initial` plus `rest` split, but
  without the Sanskrit connector.
- Greek Extended characters such as `ὁ` count as native Greek and should keep
  breathings/accents attached to the illuminated initial.
- Encoded keys, source keys, and roman forms belong in compact headword forms
  below the title. They should not compete with the native-script title.

## Search Romanization

For learner orientation, the search form can show a deterministic romanization
for native-script Sanskrit and Greek input before any backend result arrives.

Rules:

- Sanskrit Devanagari input shows IAST.
- Greek Unicode input shows a simple roman form, preserving long vowels and rough
  breathing where the local transliterator can identify them.
- Romanization is not a parser. It does not split compounds, choose a lemma, or
  alter the submitted query.
- Latin and already-roman Sanskrit/Greek input do not need a duplicate reading
  line.

## Reader Sections

Reader sections are the body of a dictionary entry.

For Diogenes:

- `diogenes:00` has no indentation.
- `diogenes:00:00` has one indentation level.
- `diogenes:00:00:00` has two indentation levels.
- Heading-like sections use smaller, stronger reader styling.
- Branch controls collapse every descendant until the next sibling or shallower
  source ref.
- Long body sections can show a preview first, then expand inline without moving
  controls into separate rows.

The visual model is close to:

```txt
root section
  child section
    subchild section
  sibling section
```

Internal IDs should not be shown in the normal reader view unless they are small
enough to avoid stealing horizontal space.

## Expansion Policy

The UI should not have many expand/collapse mechanisms.

Allowed:

- an inline chevron at the end of a long dictionary section
- an inline chevron at the end of a clipped dictionary section when fuller source
  detail exists

Avoid:

- group-level "show more" expanders
- per-card metadata drawers
- separate rows just to expand source detail
- always-expanded citation panels
- controls that shift attention away from the dictionary text

If the backend only provides a clipped line and no fuller source detail, show a
quiet note rather than pretending the UI can recover missing text. For translated
DICO and Gaffiot entries, expansion stays inside the active Reader EN or source
layer instead of replacing the layer with mixed evidence detail.

## Translation Layers

DICO, Gaffiot, and Bailly may provide source FR plus Reader EN. Those layers are
shown as a card-level toggle when relevant.

Rules:

- Do not show Reader EN / Source toggles for sources without language-layer data.
- Do not show an English yes/no column.
- Do not label French source text as Reader EN when translation is missing.
- Prefer "Reader EN" and "Source" language wording over generic bilingual labels.

For `auto`, `populate`, and `do-it-all`, the page uses a progressive flow: show
cached results first, inspect whether DICO/Gaffiot/Bailly still returned FR
source text without Reader EN, and only then display a small enrichment status
while the slow translation pass runs in the background. The main reading column
should remain usable during that pass.

## Visual Direction

The current direction is "classic manuscript meets Tufte CSS meets DaisyUI":

- bookish serif type for dictionary entries
- bundled Noto Serif fonts for Latin Extended, Greek, Greek Extended, and
  Devanagari text
- quiet manuscript colors inspired by illuminated pages
- small source emblems as mnemonic markers
- DaisyUI for standard controls and states
- custom CSS for reading rhythm, indentation, source-specific section styling, and
  theme tokens
- minimal ornament around dictionary text

The medieval flavor should support memory and orientation. It should not become
ceremony around the text.

## What To Avoid

- Mysterious confidence percentages
- Red-heavy tool controls
- Dashboard density in the main reading column
- Repeating "why am I showing this" for every section
- Exposing long internal IDs in normal reading flow
- Making controls larger than the dictionary text
- Adding expanders for anything except recoverable clipped dictionary entries
