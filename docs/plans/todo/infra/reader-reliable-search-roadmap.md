# Reader Reliable Search Roadmap

Status as of 2026-05-24: Milestones 0 through 4 have an initial
implementation. The search layer now preserves token boundaries for multi-word
Greek transliteration candidates, filtered Lance FTS searches prefilter when
possible with a deeper fallback when scoped results are otherwise dropped, and
the first source-backed concept alias table routes learner terms such as
`proper place` to Greek search forms for Aristotle. The reader web API and UI
surface the query candidates so users can see how a search was interpreted. The
remaining high-value gaps are morphology-aware matching, broader source-backed
concept coverage, and better ranking of concept-expanded results.

## Purpose

This roadmap records what happened during the Aristotle `oikos topos` search,
what worked, what failed, and what should happen next if LangNet wants reader
search to be reliable for classical-language learners and researchers.

The immediate case was a user trying to find Aristotle on the "proper/natural
place" of bodies. The user typed a romanized conceptual query, `oikos topos`,
while the relevant Greek form is not `οἶκος τόπος` but the adjective phrase
`οἰκεῖος τόπος`, usually appearing in inflected forms such as:

- `ἐν τοῖς οἰκείοις τόποις`
- `ἐν τῷ οἰκείῳ τόπῳ`
- `εἰς τὸν οἰκεῖον τόπον`

The strongest Aristotle passages found locally were:

- Aristotle, *Physics* 4.4, around Bekker 211a:
  `just cli reader show urn:cts:greekLit:tlg0086.tlg031 --segment 4.4`
- Aristotle, *Physics* 4.5, around Bekker 212b-213a:
  `just cli reader show urn:cts:greekLit:tlg0086.tlg031 --segment 4.5`
- Aristotle, *De caelo* 1.8:
  `just cli reader show urn:cts:greekLit:tlg0086.tlg005 --segment 1.8`

## What Happened

The first searches used `reader search` against the Lance-backed reader search
index. Direct romanized phrase searches for `oikos topos` and `oikeios topos`
did not return the desired Aristotle passages. Searching the exact Greek phrase
`οἰκεῖος τόπος` found non-Aristotle hits in the broader corpus, but not the
Aristotle passages, because Aristotle's relevant text uses inflected phrases and
not necessarily the exact nominative phrase.

Narrowing `reader search` by Aristotle's author id or by the `De caelo` work id
also failed for common terms like `τόπος`, even though `reader show` could
retrieve the relevant Aristotle segments and the source XML clearly contained
the searched forms.

The reliable path was:

1. Use `reader authors` to identify Aristotle as `tlg0086`.
2. Use `reader works` to identify `De caelo` and `Physica`.
3. Use local source search with `rg` against the imported First1KGreek XML.
4. Use `reader show` to retrieve the cited reader segments once the work and
   citation path were known.

That means the corpus data and segment retrieval path were sound, but the
search path was not reliable enough for this user task.

## What Worked

Reader catalog discovery worked. `reader authors --language grc` found Aristotle,
and `reader works --author-id tlg0086` exposed the expected works, including:

- `urn:cts:greekLit:tlg0086.tlg005` for *De caelo*
- `urn:cts:greekLit:tlg0086.tlg031` for *Physica*

Reader segment retrieval worked. Once a work and citation path were known,
`reader show` returned the desired text. It also attached the CTSv2 canonical
address inside the segment payload.

The source import worked. The relevant Greek text exists in the local source XML
and in reader segment artifacts.

The search index has useful infrastructure already. It includes display text,
normalized search text, folded text, token text, language, work metadata, author
metadata, classification fields, and Lance FTS indexes.

## What Did Not Work

Romanized Greek query handling was too brittle. Before the 2026-05-24 pass, the
Greek transliteration inspection for `oikeios topos` produced a collapsed
candidate:

```text
οικειοστοποσ
```

It should preserve token boundaries:

```text
οικειοσ τοποσ
```

This is now fixed in `transliterate_variants()`. The inspection payload includes
`οικειοσ τοποσ` and no longer emits `οικειοστοποσ`.

The search layer is surface-text oriented, not lemma or concept oriented. A
reader can reasonably type `oikos topos`, but the system does not yet know that
`οἰκεῖος` is an adjective derived from `οἶκος`, meaning "belonging to one's
household/own," hence "proper" or "natural" in the Aristotelian phrase.

Inflection is not handled. A search for `οἰκεῖος τόπος` should be able to match
`οἰκείῳ τόπῳ`, `οἰκεῖον τόπον`, and `οἰκείοις τόποις`. Today, exact and phrase
search are mostly normalized string search, not morphological phrase search.

Filtered search recall was weak. In `src/langnet/reader/search_index.py`,
`_lance_fts_search()` calls `lance_fts(..., prefilter = false)` and uses an
overfetch of `max(limit + offset, limit * 5, 50)`. Work, author, collection,
group, and tag filters are applied after FTS candidates are produced. For common
Greek terms like `τόπος`, the first global FTS candidates may be lexica,
commentaries, or other works; after filtering to Aristotle or a specific work,
the result set can be empty even when matching segments exist deeper in the
index.

This is now partially fixed. Scoped searches use Lance prefiltering when filters
are present, and fall back to a full-dataset overfetch if the prefiltered call
is unavailable or returns no rows. This makes work-scoped searches reliable for
the known `τόπος` and `οἰκείῳ τόπῳ` cases, while still leaving ranking and
concept expansion for later milestones.

The UI did not make query interpretation visible enough. The first pass now
shows compact query-candidate chips in the reader search result area, including
source-backed concept aliases such as `proper place: οικειοσ τοποσ`. The next
layer should make the explanation more directly teachable and should show
filters and fallback routes when text search does not find anything.

## CTSv1 and CTSv2 Behavior

The reader catalog still uses CTSv1-style URNs as stable internal `work_id`
values for many imported Greek and Latin works, for example:

```text
urn:cts:greekLit:tlg0086.tlg031
```

The newer CTSv2 identity is stored separately as `canonical_text_id`, for
example:

```text
urn:ctsv2:grc:physica-epeithe-to-eidenai
```

`reader show` currently preserves the caller's input in top-level `address`.
Therefore, this command:

```bash
just cli reader show urn:cts:greekLit:tlg0086.tlg031 --segment 4.5 --output json
```

returns a top-level address based on the CTSv1 work ref:

```text
urn:cts:greekLit:tlg0086.tlg031 4.5
```

But the canonical CTSv2 address is present at:

```text
.segment.canonical_address
```

For the same segment, that is:

```text
urn:ctsv2:grc:physica-epeithe-to-eidenai?ref=4.5
```

The direct CTSv2 form already resolves:

```bash
just cli reader show 'urn:ctsv2:grc:physica-epeithe-to-eidenai?ref=4.5' --output json
```

The cleanup task is not to remove CTSv1 internal ids immediately. It is to make
CTSv2 the preferred display and linking identity everywhere user-facing, while
keeping CTSv1 as an internal compatibility key.

## Design Goal

Reliable reader search should let a user find relevant passages when they know
any one of the following:

- a surface form in Greek, Latin, or Sanskrit
- a romanized form
- a lemma or dictionary headword
- an inflected form
- a conceptual English phrase
- an author, work, or approximate citation area

For the Aristotle case, all of these should be viable:

- `οἰκείῳ τόπῳ`
- `οἰκεῖος τόπος`
- `oikeios topos`
- `oikos topos`
- `proper place`
- `natural place`
- `Aristotle proper place`
- `Physics natural place`

The system should explain enough of the query interpretation that a learner can
understand why `oikos` led to `oikeios`, and why `οἰκεῖος τόπος` matched an
inflected passage.

## Recommended Roadmap

### Milestone 0: Regression Harness

Initial status: covered in `tests/test_reader_search_index.py` for multi-token
Greek transliteration and filtered common-term recall. Full Aristotle
concept-query fixtures remain a later layer because `oikos topos` and
`proper place` require curated concept aliases or morphology.

Create a small reader-search regression fixture before changing behavior.

Initial cases:

- `oikeios topos`, language `grc`, author Aristotle, should find *Physics* 4.4
  or 4.5.
- `oikos topos`, language `grc`, author Aristotle, should suggest or find
  `οἰκεῖος τόπος` passages.
- `οἰκείῳ τόπῳ`, language `grc`, should find *Physics* 4.5.
- `τόπος`, language `grc`, work *De caelo*, should find at least one segment in
  that work.
- `proper place`, language `grc`, author Aristotle, should route to the concept
  or bilingual alias layer rather than silently returning no useful Greek hits.

These should exercise the CLI and, separately, the web API route.

### Milestone 1: Fix Greek Transliteration Query Candidates

Initial status: implemented in `src/langnet/normalizer/greek_transliterator.py`.

Preserve token boundaries in `transliterate_variants()` or in the reader search
candidate construction layer.

Expected inspection:

```bash
just cli reader search-index inspect-query 'oikeios topos' \
  --language grc \
  --mode fuzzy \
  --field auto \
  --output json
```

Should include:

```text
οικειοσ τοποσ
```

not only:

```text
οικειοστοποσ
```

This is the fastest high-value fix because it improves many romanized Greek
multi-word searches without requiring a new morphology index.

### Milestone 2: Fix Filtered Search Recall

Initial status: implemented for the Lance FTS path in
`src/langnet/reader/search_index.py` using prefiltering plus a deeper fallback.

Make author/work/collection filters effective before ranking drops useful hits.

Options:

1. Preferred: use Lance/SQL prefiltering if supported for this dataset and query
   shape.
2. Acceptable short-term: increase overfetch aggressively when restrictive
   filters are present.
3. Fallback: for work-scoped searches, search the per-work segment artifact or a
   work-filtered derived view instead of global FTS.

The product requirement is simple: if a matching segment exists in a filtered
work or author corpus, a common word search should not return zero only because
the global top-k was consumed by other works.

### Milestone 3: Add Query Explanation Payloads

Initial status: implemented for reader search query candidates. The CLI returns
`request.query_candidates`, and the SvelteKit `/api/reader?mode=search` mapper
now preserves concept metadata fields (`concept_id`, `concept_label`,
`explanation`, and `source_file`). The reader UI displays the visible expanded
query candidates near the result count.

Extend search responses with an explicit interpretation block:

```json
{
  "input": "oikos topos",
  "language": "grc",
  "candidates": [
    {"query": "oikos topos", "kind": "raw"},
    {"query": "οικοσ τοποσ", "kind": "transliteration"},
    {"query": "οἰκεῖος τόπος", "kind": "concept_alias"},
    {"query": "οἰκείῳ τόπῳ", "kind": "inflection_variant"}
  ],
  "filters": {
    "author_id": "urn:cts:greekLit:tlg0086"
  }
}
```

The UI should display a compact version of this when results are weak or when a
query was expanded.

### Milestone 4: Add Curated Concept Alias Search

Initial status: implemented for the first high-value Greek case in
`data/curated/reader_search/greek/aristotle-natural-place.yaml`. The loader in
`src/langnet/reader/search_concepts.py` reads YAML concept records, and
`src/langnet/reader/search_index.py` expands fuzzy searches whose labels match
the concept into normalized source-language search candidates. Live CLI and web
API probes confirm that `proper place` with Greek + Aristotle *Physics* scope
returns concept-alias hits with CTSv2 canonical addresses.

Create a small curated table for high-value classical concepts. This is not a
replacement for morphology; it is a pragmatic bridge for searches where the
learner knows a concept but not the exact source-language phrase.

Example row:

```yaml
id: aristotle-natural-place
language: grc
labels:
  - proper place
  - natural place
  - oikos topos
  - oikeios topos
source_queries:
  - οἰκεῖος τόπος
  - οἰκεῖον τόπον
  - οἰκείῳ τόπῳ
  - οἰκείοις τόποις
preferred_filters:
  authors:
    - urn:cts:greekLit:tlg0086
  works:
    - urn:cts:greekLit:tlg0086.tlg031
    - urn:cts:greekLit:tlg0086.tlg005
notes: >
  οἰκεῖος derives from οἶκος and means one's own, appropriate, proper;
  in Aristotle's physical works it supports the natural/proper place concept.
```

This table should be inspectable and source-backed. It should not silently hide
the original query.

### Milestone 5: Build Lemma and Morphology-Aware Search

Add a token-level reader index:

```text
segment_id
work_id
citation_path
token_index
surface
normalized_surface
lemma
morphology
source
confidence
```

For Greek, start with available local analyzers/dictionaries and tolerate
multiple analyses per token. The search API should support:

- lemma search
- lemma-near-lemma search
- lemma plus surface phrase search
- exact surface phrase as a separate mode

For the Aristotle case, the desired logical query is:

```text
lemma:οἰκεῖος NEAR lemma:τόπος
```

This should match `οἰκείῳ τόπῳ`, `οἰκεῖον τόπον`, and plural forms.

### Milestone 6: Prefer CTSv2 in User-Facing Reader Output

Keep CTSv1 `work_id` internally for compatibility, but make CTSv2 prominent in
user-facing output.

Changes:

- Add top-level `canonical_address` to `reader show` payloads.
- Add top-level `canonical_text_id` where applicable.
- Make pretty output display CTSv2 first and CTSv1 as an internal/source id.
- Ensure web reader links use `segment.canonical_address` or the new top-level
  `canonical_address`.
- Add tests that direct CTSv2 and CTSv1 inputs both resolve to the same segment.

### Milestone 7: UI Search Workflow

The Reader UI should support a research workflow:

- Search within an author.
- Search within selected works.
- Show active filters clearly.
- Show query expansions when applied.
- Offer "search source files / exact corpus fallback" only as a diagnostic mode,
  not as the normal user path.
- Provide direct links to `reader show` addresses using CTSv2.

For this case, the UI should let the user choose Aristotle, select *Physics* and
*De caelo*, type `oikos topos`, and see both the linguistic explanation and the
matching passages.

## Validation Strategy

Use three levels of validation:

1. Unit tests for normalization and transliteration.
2. Search-index regression fixtures for known passages.
3. Web API/UI tests that assert filtered search returns the expected result
   shape and exposes query interpretation.

Minimum acceptance checks:

```bash
just cli reader search-index inspect-query 'oikeios topos' \
  --language grc \
  --mode fuzzy \
  --output json

just cli reader search 'οἰκείῳ τόπῳ' \
  --language grc \
  --author-id urn:cts:greekLit:tlg0086 \
  --mode fuzzy \
  --output json

just cli reader show 'urn:ctsv2:grc:physica-epeithe-to-eidenai?ref=4.5' \
  --output json
```

The first command should expose token-preserving Greek candidates. The second
should return Aristotle, *Physics* 4.5 or a nearby relevant segment. The third
should resolve through CTSv2 and expose the same segment as the CTSv1 work-id
form.

## Open Questions

- Which Greek morphology source should be the first production-grade provider
  for token lemma indexing?
- Should concept aliases live under `data/curated/reader_search/`, under the
  learning taxonomy, or as part of a broader source-backed concepts table?
- Should `reader search --mode fuzzy` become the UI default for Greek, or should
  the UI run multiple explicit modes and merge results?
- How should we rank exact source-language matches against concept-alias matches?
- Should work-scoped search use the global Lance index with prefiltering, or a
  per-work/per-author side index?

## Recommended Next Step

Implement Milestones 0 through 2 together:

1. Add the Aristotle regression cases.
2. Fix Greek multi-token transliteration candidates.
3. Fix filtered search recall enough that author/work-scoped search can find
   common terms inside the selected corpus.

That package is small enough to verify thoroughly and large enough to make the
Reader UI materially more trustworthy.
