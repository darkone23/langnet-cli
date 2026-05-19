# Output Guide

LangNet currently exposes three useful output layers:

1. **Backend lookup output** from `lookup`.
2. **Evidence-backed claim/triple output** from `plan-exec` and `triples-dump`.
3. **First learner-facing reduced output** from `encounter`.

The learner-facing layer is still an MVP: it groups exact Witness Sense Units into buckets and preserves source evidence, but it is not yet the final semantic schema.

## High-Fidelity Display Rule

Display transforms may transliterate, normalize whitespace, expand abbreviations, label source notes, or add explanations. They must not silently discard source content. If a source segment is hard to interpret, keep it visible or move it into an explicit structured field that remains inspectable.

## `lookup`

`lookup` is useful for quick inspection. Its JSON is backend-keyed.

```bash
just cli lookup lat lupus --output json
```

Typical shape:

```json
{
  "whitakers": [...],
  "diogenes": {...},
  "cltk": {...}
}
```

`lookup --output pretty` is a terminal summary. It is intentionally compact and should not be treated as the final semantic schema.

## `plan-exec`

`plan-exec` runs the staged runtime:

```text
normalize → plan → fetch → extract → derive → claim
```

Use it when you need to know which tools were selected and what claim effects were produced.

```bash
just cli plan-exec lat lupus --output json
```

The JSON summary is intended for inspection and regression tests. It reports:

- cache status and response-ref count
- planned versus produced counts for fetch, extract, derive, and claim stages
- skipped optional calls with reasons and source-call IDs
- handler versions observed in produced effects
- compact claim rows

## `triples-dump`

`triples-dump` is the best current evidence-inspection command.

```bash
just triples-dump lat lupus whitakers
just triples-dump san agni cdsl
```

Use the third argument to narrow the tool family. Examples:

- `whitakers`
- `diogenes`
- `cdsl`
- `all`

Use `langs --output json` and `tools --output json` to list the supported
language and `tool_filter` values for subprocess callers. For example:

```bash
just cli langs --output json
just cli tools san --output json
```

The JSON response includes `schema_version`, language metadata,
`tool_filter`/`accepted_filter`, underlying staged `plan_tools`, source-tool
names, default-enabled status, and whether a source can participate in cached
translation projection. Sanskrit MW and AP90 are currently represented as CDSL
sub-dictionaries under the `cdsl` tool.

The self-description schemas live in:

- `docs/schemas/languages.v1.schema.json`
- `docs/schemas/tools.v1.schema.json`
- `docs/schemas/word_index.v1.schema.json`
- `docs/schemas/word_index_sections.v1.schema.json`

`word-of-day --output json` and `recommend-words --output json` return learner
recommendation cards using schema version `langnet.word_of_day.v1`. The schema
lives at `docs/schemas/word_of_day.v1.schema.json`.

```bash
just cli word-of-day san --output json
just cli recommend-words grc --count 3 --output json
```

Recommendation cards include `canonical_name` for the learner-facing headword
projection, plus a structured `canonical` object with `script`, `source`,
`transliteration`, `source_key`, and `lexeme`. Sanskrit cards prefer
Devanagari, Greek cards prefer UTF-8 Greek, and Latin cards keep the Latin
headword. Cards also include a short gloss, a learner note about why the word is
worth studying, and an optional encounter probe summary. The probe summary is
cache-only for translation evidence; these commands should not hide live
translation latency inside ordinary recommendation rendering.

For Greek beginner recommendations, `canonical.source_key` is upgraded to a
Diogenes inflection key when LangNet has a verified learner-key bridge. For
example, a `logos` card can expose `canonical.source_key: "lo/gos"`, which is
directly usable as `just cli paradigm grc lo/gos --kind declension --output
json`.

Candidate source modes:

- `--candidate-source curated` uses built-in learner inventories only. The
  Greek inventory is year-scale so MOTD refreshes are not dominated by a few
  famous words.
- `--candidate-source llm` requires OpenRouter credentials and fails if LLM
  candidate synthesis is unavailable.
- `--candidate-source auto` tries LLM synthesis when credentials and timeout
  permit it, then falls back to curated inventories with a warning.

Use `--fresh` with `--avoid` or `--exclude-recent` to keep recent cards out of
the first-choice set. The response includes `diagnostics.languages.<lang>` with
pool size, eligible/probed/accepted counts, deferred ambiguity/repeat counts,
and the first validation rejections. This makes it clear whether a card came
from LLM synthesis or curated fallback and how much candidate validation was
discarded before the final card list was produced.

## `paradigm` And `paradigm-resolve`

`paradigm` fetches source-backed inflection tables. It is a table tool, not a
full local morphology generator. The current implementation wraps:

- Sanskrit Heritage `sktdeclin` for noun/adjective declension tables.
- Sanskrit Heritage `sktconjug` for verb conjugation tables.
- Diogenes `do=inflect` for Latin and Greek inflection tables.

```bash
just cli paradigm san putra --kind declension --gender Mas --output json
just cli paradigm san gam --kind conjugation --class 1 --output json
just cli paradigm lat amo --kind conjugation --output json
just cli paradigm grc lo/gos --kind declension --output json
```

The JSON response uses schema version `langnet.paradigm.v1`. The schema lives at
`docs/schemas/paradigm.v1.schema.json`.

Important fields:

- `language`, `lemma`, `kind`, and `source` identify the requested table.
- `source_request` records the source-backed endpoint and request metadata.
- `paradigms[]` contains one or more table blocks.
- `paradigms[].dimensions` names the grammatical axes exposed by that block.
- `slots[]` contains feature-labeled cells such as case/number or
  tense/voice/person/number.
- `forms[]` preserves source forms and source keys.
- `warnings[]` reports partial or failed source-backed behavior.

Sanskrit table requests need the metadata Heritage requires:

- Declensions require `--gender Mas`, `--gender Fem`, or `--gender Neu`.
- Conjugations require `--class <present-class>`.

Latin and Greek table requests need a Diogenes-compatible lemma key. For Greek,
that can be a beta-code key such as `lo/gos`.

`paradigm-resolve` explains what LangNet believes before fetching a table. It is
primarily a resolver/debugging surface for ambiguity, missing metadata, and
future lookup integration.

Greek learner keys used by the curated MOTD pool are also resolver inputs when
LangNet has verified a Diogenes inflection key for them:

```bash
just cli paradigm-resolve grc logos --output json
just cli paradigm-resolve grc sophos --output json
```

Those responses include a `paradigm_request` such as `diogenes:inflect
lo/gos`. Unmapped romanized Greek keys degrade with
`unresolved_reason: "greek_learner_key_not_resolved_to_source_key"` so consumers
can distinguish a missing bridge from an indeclinable word.

```bash
just cli paradigm-resolve san putraa.naam \
  --record-json '{"normalized_form":"putrāṇām","lemma":"putra","part_of_speech":"noun","gender":"masculine","source":"heritage:sktreader","analyses":[{"case":"genitive","number":"plural"}]}' \
  --output json
```

The resolver JSON uses schema version `langnet.paradigm_resolution.v1`. The
schema lives at `docs/schemas/paradigm_resolution.v1.schema.json`.

Important resolver fields:

- `searched_form` and `normalized_form` keep the reader input separate from the
  normalized form.
- `native_analyses[]` preserves language-specific grammar evidence.
- `functional_analyses[]` maps native grammar into shared learner-facing
  relations such as `subject`, `direct_object`, `recipient_or_goal`, or
  `possession_or_association`.
- `paradigm_request` is present only when LangNet has enough metadata to fetch a
  table.
- `unresolved_reason` explains why a table should not be fetched yet.

Graceful degradation is part of the contract. If a source request fails, the
payload should prefer structured warnings over pretending the table is complete.
If Diogenes or Heritage returns source labels that cannot be fully normalized,
LangNet preserves `source_label` and source forms for inspection. Current limits
and warning values are documented in
`docs/technical/backend/paradigm-generation-limitations.md`.

`word-index --output json` commands return source-backed headword index rows
using schema version `langnet.word_index.v1`.

```bash
just cli word-index sources --output json
just cli word-index sections san --source all --output json
just cli word-index sections grc --source diogenes --output json
just cli word-index sections lat --source all --output json
just cli word-index browse san --source all --prefix d --limit 12 --output json
just cli word-index browse san --source all --prefix kha --homographs raw --limit 20 --output json
just cli word-index browse grc --source all --prefix n --limit 12 --output json
just cli word-index browse lat --source all --prefix r --limit 12 --output json
just cli word-index list all --source all --limit 25 --output json
just cli word-index neighborhood san dharma --source dico --radius 8 --output json
just cli word-index neighborhood lat lupus --source whitakers --radius 8 --output json
just cli word-index nearby san satya --source all --radius 5 --output json
just cli word-index nearby san satya --source all --radius 5 --merge none --output json
just cli word-index nearby san धर्म --source cdsl --radius 8 --output json
just cli word-index nearby lat lupus --source all --radius 5 --output json
just cli word-index nearby grc physis --source all --radius 8 --output json
just cli word-index nearby grc λόγος --source diogenes --radius 8 --output json
just cli word-index nearby grc logos --source diogenes --radius 8 --output json
just cli word-index wheel all --count 12 --seed daily --output json
just cli word-index wheel --language grc --source all --count 12 --seed daily --output json
```

Word-index rows distinguish source-local naming from LangNet's normalized
contract. `source_name` is the exact source/index headword key, `canonical_name`
is the learner-facing normalized lemma, `canonical_key` is the stable ASCII-ish
index key, and `lookup` is the value passed to `encounter` for source inspection.
Rows also carry durable domain identifiers: `lexeme_id` identifies the
source-independent word, `lexeme_key` is the lossless identity key used before
building that ID, `wheel_id` is the stable wheel-facing handle for that lexeme,
`wheel_order_key` is the canonical total ordering key, `native_order_key` is the
language-native collation key used by integrated neighborhoods, `index_entry_id`
identifies the exact source-backed row, and `source_order_id` is a squuid-like
stable sortable ID derived from the source ordering key plus a short uniqueness
hash. The structured `ids` object repeats
those IDs with the source reference for web/front-end callers. Rows also include
structured `display` metadata and an `encounter` request object that can be used
to inspect the source entry in detail. `word-index list --source all` is
lexeme-centered: rows with the same `lexeme_id` are collapsed into one card,
ordered by `wheel_order_key`, and the exact source rows are listed under
`source_entries`. With `--source all`, nearby/neighborhood output now defaults
to `merge=lexeme`: the top-level neighborhood has
`policy = "integrated_language_native"`, an `anchor`, and learner-facing
`items[]` with one row per `lexeme_id`, ordered by the language-native
`native_order_key`. Source-local provenance remains available under
`neighborhood.groups[]`. Pass `--merge none` to return only the older
source-local grouped shape. Specific source/dictionary neighborhoods remain
source-order neighborhoods and declare that with
`window.policy = "source_entry_contiguous"`, `window.contiguous = true`, and
`window.collapsed = false`. Integrated neighborhoods collect bounded candidate
windows from indexed native sections, collapse them into cross-source lexeme
cards, then apply the radius after language-native sorting. Thus
`anchor.source_entries` is stable across radius changes; `--radius` controls
neighboring lexemes, not the current word's provenance. Cross-language
similarity is intentionally a later explicit mode. Use `word-index browse` when
the UI needs a didactic source-native browse panel instead of collapsed lexeme
cards. Browse payloads use `mode = "browse"`;
with `--source all`, the top-level order is `policy = "grouped-source-native"`
and learner-facing rows live under top-level `items[]`. The backing source
windows remain under `groups[]`, one source/dictionary group at a time. Each
group keeps its own `source-native` row order, `source_ref`, `source_order_key`,
display metadata, transliteration, and encounter request. V1 intentionally does
not claim a single globally interleaved native order across dictionaries; it is
a grouped source-native browse surface. Browse defaults to
`--homographs grouped`, which compacts adjacent identical headwords within each
source/dictionary group and then groups matching learner rows across
dictionaries into top-level cards with `homograph_count`, `source_count`,
`source_counts[]`, `source_entry_count`, and `source_entries[]`. This keeps
runs such as repeated Sanskrit `ख kha` or MW/AP90 `ह ha` entries
learner-friendly while preserving every source ref and source-order key. Pass
`--homographs raw` to audit the exact ungrouped source rows; in raw mode,
top-level `items[]` is empty and callers should inspect `groups[]`.
`word-index list --source all` remains
the collapsed canonical lexeme-card view. For mixed wheels within a language, keep
`--source all` and select the language with the positional argument or
`--language grc`; `--source` remains reserved for backend/source families such
as `cdsl`, `dico`, `gaffiot`, `whitakers`, and `diogenes`. Wheel output is also
lexeme-centered: rows with the same `lexeme_id` are collapsed into one wheel
card, and the exact source rows are listed under `source_entries`. Wheels with
`--source all` balance available source/dictionary buckets while selecting
lexeme cards, rather than returning duplicate cards for the same word from
different sources. The top-level wheel payload has `order.policy =
"seeded-discovery"` and `order.collation = "seeded-discovery"`; use that to
label the wheel as a deterministic discovery sequence, not as dictionary order.
Each returned wheel card has `order.policy = "canonical-key"` because duplicate
source rows are collapsed to one lexeme card. Each `source_entries[]` row still
has its own `source-native` order metadata for dictionary-neighborhood
navigation.
`word-index sections` returns native alphabet or varnamala section anchors using
schema version `langnet.word_index_sections.v1`. Use it for a compact
dictionary navigation rail. Section labels are display labels, transliteration
is supporting text, and each section includes an `anchor` that can be passed to
`word-index nearby` or future source-order cursor surfaces. For Greek, the rail
keeps learner labels separate from Diogenes source keys: for example Θ displays
`transliteration = "th"` but anchors with `query = "q"`, Ξ uses `query = "c"`,
Ψ uses `query = "y"`, and Ω uses `query = "ō"`.

Sanskrit sections follow a 52-item varnamala rail: 14 vowels, anusvara and
visarga, the 33 consonants grouped by articulation, plus the common conjuncts
क्ष, त्र, and ज्ञ. The displayed transliteration is learner-facing, while
`anchor.query` is the source-native CDSL SLP1 prefix needed to open the correct
dictionary neighborhood. Examples: ऋ uses `query = "f"`, ङ uses
`query = "N"`, ट uses `query = "w"`, ण uses `query = "R"`, श uses
`query = "S"`, ष uses `query = "z"`, क्ष uses `query = "kz"`, and ज्ञ uses
`query = "jY"`. This distinction avoids collapsing Sanskrit phonemes that
share rough ASCII spellings such as `t`, `n`, or `sh`.

Sanskrit sections report `order.collation = "sa-varga"`. Source-local row order
still comes from `word-index nearby`, so the payload includes a warning rather
than implying a full standalone Sanskrit cursor. For CDSL source-native browse,
SLP1 case is meaningful and preserved: `--prefix N` opens ङ/ṅa rows, while
`--prefix na` opens dental न/na rows. CDSL neighborhoods choose exact anchors
with that same source-sensitive distinction, then return before/after rows by
the dictionary's source position rather than by lowercased ASCII spelling.
Ordering semantics are explicit in the `order` object. Durable fields like
`wheel_order_key` and `source_order_key` are plumbing keys; callers should read
`order.policy`, `order.collation`, `order.label`, and `order.explanation` before
presenting order to learners. Current policies include `source-native` for
source-local dictionary rows, `canonical-key` for collapsed lexeme cards,
`grouped-source-native` for browse payloads that preserve source order in
separate groups, `language-native` for integrated `--source all`
neighborhoods, `source-window-merge` for legacy/source-window merge metadata,
and `seeded-discovery` for wheel payloads. For Sanskrit source rows this
currently preserves the indexed source sequence honestly as
`collation = "source"`, while integrated Sanskrit neighborhoods declare
`order.collation = "sa-varga"` and sort by `native_order_key`. The exact
source-local ordering remains available on each collapsed card's
`source_entries[].order`.
Native-script queries are accepted where the source index can be projected to a
stable canonical key: Sanskrit Devanagari is expanded through the existing
Velthuis/CDSL path, and Greek Unicode is expanded to the same ASCII key used by
Diogenes lookup rows. Common Greek Latinized forms are also normalized for the
word index, so `physis` can resolve to the indexed Diogenes key `fusis`.

Latin `--source all` includes Gaffiot, Whitaker's Words, and Diogenes when their
local DuckDB indexes are built. Whitaker's generated `DICTLINE.GEN` stores
stems plus grammatical codes rather than a frontend-ready browse table, so
LangNet materializes a local `data/build/lex_whitakers.duckdb` and derives
best-effort learner citation forms for word-index use. For example, Whitaker's
stem `lup` with noun code `2 1 M` is indexed as `lupus`, and verb stem `am`
with conjugation code `1` is indexed as `amo`. The original stem remains in
`display.source_key` and `metadata.source_stem` for inspection. This is a
dictionary-headword index, not a generated-form index or a complete local
morphological analyzer.

Build or refresh the Whitaker word index from a local checkout with:

```bash
just cli-databuild whitakers-index --source ../whitakers-words/DICTLINE.GEN
just cli word-index sources lat --output json
just cli word-index nearby lat lupus --source all --radius 5 --output json
```

Diogenes Greek/Latin neighborhoods require a local built index. Full indexes
should use direct Diogenes XML import when the local Diogenes data files are
available:

```bash
just cli-databuild diogenes-index lat --mode direct --max-entries 0
just cli-databuild diogenes-index grc --mode direct --max-entries 0
just cli word-index neighborhood lat amo --source diogenes --radius 8 --output json
just cli word-index neighborhood grc apo --source diogenes --radius 8 --output json
```

For fixed windows around a seed, use CGI crawl mode:

```bash
just cli-databuild diogenes-index lat --mode crawl --seed-word amo --max-entries 1000
just cli-databuild diogenes-index grc --mode crawl --seed-word apo --max-entries 1000
```

The direct builder imports Diogenes' local XML dictionary files. The crawl
builder talks to `Perseus.cgi` and follows `prev_entry`/`next_entry` navigation
offsets. Both write `data/build/lex_diogenes_lat.duckdb` or
`data/build/lex_diogenes_grc.duckdb`. Runtime `word-index` commands only read
those DuckDB files; they do not crawl live.

Use `doctor` when a subprocess caller needs a local, non-network readiness
check for the CLI surface, schema files, translation cache path, translation
dependencies, and optional tools:

```bash
just cli doctor --output json
just cli doctor --require-openai-key --output json
```

The readiness JSON uses schema version `langnet.doctor.v1`; its schema lives at
`docs/schemas/doctor.v1.schema.json`.

Current output is text by default. Use `--output json` for structured inspection.

Current `triples-dump --output json` shape:

```json
{
  "query": {
    "language": "san",
    "text": "agni",
    "normalized_candidates": ["agni"]
  },
  "tool_filter": "cdsl",
  "filters": {
    "predicate": "gloss",
    "subject_prefix": null,
    "max_triples": 10
  },
  "claims": [
    {
      "claim_id": "clm-example",
      "tool": "claim.cdsl.sense",
      "subject": "drv-example",
      "predicate": "has_sense",
      "derivation_id": "drv-example"
    }
  ],
  "triples": [
    {
      "claim_id": "clm-example",
      "subject": "lex:agni",
      "predicate": "has_sense",
      "object": "sense:lex:agni#example",
      "metadata": {
        "evidence": {
          "source_tool": "cdsl",
          "claim_id": "clm-example",
          "response_id": "resp-example",
          "source_ref": "mw:123",
          "raw_blob_ref": "raw_json"
        }
      },
      "display_iast": "agni",
      "display_slp1": "agni",
      "source_encoding": "slp1"
    },
    {
      "claim_id": "clm-example",
      "subject": "sense:lex:agni#example",
      "predicate": "gloss",
      "object": "fire; sacrificial fire",
      "metadata": {
        "source_ref": "mw:123",
        "evidence": {
          "source_tool": "cdsl",
          "claim_id": "clm-example",
          "response_id": "resp-example",
          "source_ref": "mw:123",
          "raw_blob_ref": "raw_json"
        }
      }
    }
  ],
  "warnings": []
}
```

The JSON shape keeps claim metadata separate from triple metadata so tools can inspect claims without scraping the text renderer. Text output remains supported.

## `encounter`

`encounter` is the current learner-facing path. It runs staged evidence, projects exact cache-backed translations when the configured cache exists, reduces source glosses into exact buckets, and prints a compact word encounter.

```bash
just cli encounter san dharma cdsl --max-buckets 5
just cli encounter san agni heritage --no-cache
just cli encounter lat lupus gaffiot
```

Pretty output should be treated as a prototype learner interface. It is the
right surface for examples and snapshots, but not the machine contract. Use
`encounter --output json` for downstream renderers.

The accepted-output gallery currently covers representative Sanskrit, Latin, and Greek snapshots in `tests/test_cli_encounter_output.py`. Add new examples there when display ranking or source transforms change.

Long source entries are expected. The compact display line is a learner summary,
not a replacement for source evidence. JSON consumers should inspect
`display.meanings[*].entries[*]`, `source_entry`, `source_text_chars`, and
`evidence_length_note` when they need to explain whether a visible ellipsis came
from LangNet compaction or from an upstream source entry. For example, DICO can
return source text that itself ends with `...`; LangNet should still rank exact
headword matches first and preserve the useful learner sense in
`display_gloss`.

### JSON Contract

`encounter --output json` keeps the raw reduction fields for compatibility:

- `query`, `language`, `lexeme_anchors`, `buckets`, `unbucketed_witnesses`, and
  `warnings`;
- `buckets[*].witnesses[*].evidence`, which remains the provenance-rich source
  evidence;
- `ranking`, aligned by index with the sorted `buckets` list;
- `translation_cache`, with cache availability, hit/miss counts, and population
  batches.

New renderer-facing fields are additive:

- `schema_version`: currently `langnet.encounter.v1`;
- `request`: normalized request metadata such as language, text, tool filter,
  cache mode, and translation mode;
- `display.header`: forms and source keys ready for a first-screen header;
- `display.analysis`: morphology rows with `display_text` and Foster labels;
- `display.meanings`: display-ready meaning rows aligned by `bucket_id` to
  `buckets`, including source refs, source-detail summaries, translation
  provenance, source languages, witness counts, and confidence labels;
- `display.meanings[*].entries`: one stable summary per witness with common
  entry metadata such as source tool, source ref, headword, entry id,
  dictionary, source-entry summary, typed source notes, raw blob reference, and
  translation provenance;
- `word_index`: compact index context for follow-up navigation. It deliberately
  does not inline nearby rows. Instead it reports that primary encounter buckets
  are ranked sense evidence rather than a contiguous dictionary slice, then
  exposes anchor handles such as `lexeme_id`, `index_entry_id`,
  `source_order_id`, `source_order_key`, and min/max source-window bounds. Use
  those handles with `word-index nearby` now, and with the planned unified
  wheel-neighborhood surface later;
- `paradigm_resolution`: present only when `--include-paradigm-resolution` is
  passed. This embeds a `langnet.paradigm_resolution.v1` payload for the searched
  form, built from encounter morphology triples and resolver logic. It can
  include native analyses, functional analyses, a lazy `paradigm_request`, and
  `unresolved_reason` values. It does not fetch full paradigm tables; clients
  should call `paradigm` only after the learner opens a forms/paradigm panel.
- `actions` and `display.actions`: UI-ready lazy follow-up targets derived from
  the encounter context. Current action kinds are `view_paradigm`,
  `open_word_index_neighborhood`, and `inspect_source_entry`. These actions
  include structured request objects and CLI-style `argv` hints where a command
  exists, but they do not fetch additional tables or inline dictionary windows
  during the encounter call.
- `components` and `display.components`: optional structured component links
  when a morphology tool exposes a likely decomposition, such as Sanskrit
  compound members from Heritage `iic.` rows or Latin Whitaker tackons. These
  links include the component surface, lemma, learner display form, role,
  analysis, lookup terms, and linked evidence status/meanings. They are
  supporting evidence for rendering partial links; they do not replace or
  reorder the primary `display.meanings` buckets;
- `display.options`: rendering controls used to build display strings.

Example:

```bash
just cli encounter san putraa.naam heritage \
  --include-paradigm-resolution \
  --output json
```

Web/API consumers should render `display.*`, inspect `ranking` for ordering
reasons, and keep `buckets[*].witnesses[*].evidence` available for provenance
expansion. They should not scrape pretty output.

The current schemas live in:

- `docs/schemas/encounter.v1.schema.json`
- `docs/schemas/encounter-error.v1.schema.json`

The schema is intentionally additive-friendly: consumers can rely on required
fields for the current iteration, while future compatible fields can be added
without changing `schema_version`.

When `encounter --output json` fails after command dispatch, stdout is still
JSON and the process exits nonzero. The error shape is:

```json
{
  "schema_version": "langnet.encounter.error.v1",
  "ok": false,
  "request": {
    "language": "lat",
    "text": "lupus",
    "tool_filter": "gaffiot",
    "normalize": true,
    "no_cache": false,
    "include_cltk": false,
    "translation_mode": "off"
  },
  "error": {
    "code": "encounter_failed",
    "type": "RuntimeError",
    "message": "backend unavailable"
  }
}
```

Callers should parse stdout first when they requested JSON, even when the exit
status is nonzero.

## `reader-eval`

`reader-eval` runs reader-oriented fixture checks against the same reduced
encounter path. It is intended for iteration: report current hit quality, fix
one class of misses, then rerun the same fixture.

```bash
just cli reader-eval --fixture tests/fixtures/reader_eval_classics.json --translation-mode cache
just cli reader-eval --language lat --limit 4 --output json
```

By default the command exits successfully and reports misses. Add
`--fail-on-miss` only when the selected fixture set is ready to become a gate.
The current seed fixture lives at `tests/fixtures/reader_eval_classics.json` and
covers initial Aeneid, Iliad, and Bhagavad Gita opening-token probes.
The summary separates broad evidence hits from first-screen learner quality:
overall strict pass rate, broad meaning pass rate, and top-answer pass rate.
`top_lemma_hit` remains visible as a diagnostic because some backends expose an
inflected surface as the top lemma even when the first gloss is useful.

For Sanskrit, Heritage is the preferred analysis/morphology source. A Heritage-only encounter may show an `Analysis` section without meaning buckets:

```text
agni [san]
==========

Analysis
- agn -> agn: loc. sg. m. (heritage)
- agn -> agn: loc. sg. n. (heritage)
```

For a combined Sanskrit lookup, `encounter` should show Heritage analysis alongside CDSL/DICO meaning evidence. CDSL source keys remain inspectable separately from learner-facing IAST display forms.

### Evidence Walkthrough: Sanskrit `dharma`

Use `encounter` first to see the learner-facing result:

```bash
just cli encounter san dharma all --no-cache --max-buckets 3
```

For CDSL-backed meanings, the displayed bucket text may use a display gloss. This must not omit source content by default. Today `metadata.display_gloss` only applies display-safe Sanskrit transliteration transforms; the raw CDSL gloss remains in the evidence triple object.

To inspect where a displayed CDSL meaning came from, dump the source triples:

```bash
just cli triples-dump san dharma cdsl --no-cache --output json --predicate gloss --max-triples 3
```

In the JSON, inspect the matching `gloss` triple:

- `object` is the raw CDSL source-near gloss.
- `metadata.display_gloss` is the conservative learner-display string used by `encounter` when present. It should preserve source content unless a future parser separates notes into explicit fields.
- `metadata.source_entry` identifies the CDSL row and source keys, including dictionary id, line number, `source_ref`, SLP1 key, and IAST key.
- `metadata.source_segments` is an ordered, source-complete split of the raw gloss text. Each segment has `raw_text`, `display_text`, and, where recognized, `segment_type` plus `labels` such as `definition`, `cross_reference`, `source_reference`, `citation`, or `example`.
- `metadata.source_notes`, when present, summarizes confidently typed cross-reference/source-reference segments. It does not replace or remove the original segments.
- `metadata.source_ref` identifies the dictionary row, such as `mw:<line>`.
- `metadata.evidence.response_id`, `extraction_id`, `derivation_id`, and `claim_id` show the runtime path that produced the triple.
- `metadata.display_iast` and `metadata.display_slp1` show the learner form and source key separately.

That separation is the current evidence contract: learner output can be cleaner than source text, but source text remains inspectable.

When typed source notes or typed source segments are present, `encounter` may
show them below the source refs as compact provenance hints, for example
`source notes: cross refs: ...; source refs: ...; examples: ...`. Pass
`--no-source-details` for a quieter first screen. The raw gloss still remains
available as the evidence line and in `triples-dump`.

### Evidence Walkthrough: DICO/Gaffiot Translation Cache

DICO and Gaffiot now follow the same evidence shape for French dictionary-entry
glosses. Their source text remains French and is marked with `source_lang: fr`;
cached English translations are separate derived witnesses.

For translated DICO/Gaffiot glosses:

- `metadata.parsed_glosses` contains individual English gloss candidates parsed from the translated text.
- `metadata.translated_segments` keeps the translated output in ordered display segments.
- `metadata.evidence.derived_from_tool` and `metadata.evidence.derived_from_sense` point back to the French source witness.

In `encounter`, cache-backed translation buckets are displayed before untranslated
French source buckets, and the output includes `translated from: dico` or
`translated from: gaffiot` when that provenance is available. Multi-witness
non-translated buckets are ranked ahead of single-witness buckets.

DICO and Gaffiot source entries are French source evidence. Cached English text is derived evidence, not a replacement for the French source.

First inspect the source French gloss:

```bash
just cli triples-dump lat lupus gaffiot --no-cache --output json --predicate gloss --max-triples 3
just cli triples-dump san dharma dico --no-cache --output json --predicate gloss --max-triples 3
```

In those source triples:

- `object` is the original French source gloss.
- `metadata.source_lang` should be `fr` when the source handler marks it.
- `metadata.evidence.source_tool` is `gaffiot` or `dico`.
- `metadata.evidence.source_ref` identifies the source entry, such as `gaffiot:<entry>` or `dico:<page>.html#<anchor>:<occurrence>`.

After a matching cache row exists, inspect the derived English evidence through `encounter`:

```bash
just cli encounter lat lupus gaffiot --translation-cache-db data/cache/langnet.duckdb --output json
just cli encounter san dharma dico --translation-cache-db data/cache/langnet.duckdb --output json
```

To populate missing DICO/Gaffiot translations during an explicit lookup, use
`--translation-mode auto`:

```bash
just cli encounter lat lupus gaffiot --translation-mode auto --translation-cache-db data/cache/langnet.duckdb
just cli encounter san dharma dico --translation-mode auto --translation-cache-db data/cache/langnet.duckdb
```

To warm translations ahead of reading, place one term per line in a text file
and run `translation-warm`. This is explicit cache population, so it may call
the configured model for cache misses. The default translation model is
`openai:google/gemini-2.5-flash`, with
`openai:deepseek/deepseek-v4-flash` as the default fallback on provider failures,
empty responses, or slow completed responses. Pass `--translation-model` to test
or pin a different OpenRouter model for population. Cache writes remain
model-stamped, but cache-only reads can reuse any compatible successful row for
the same source, prompt, and hint:

```bash
just cli translation-warm lat examples/debug/latin_words.txt --tool-filter gaffiot --translation-cache-db data/cache/langnet.duckdb
just cli translation-warm san examples/debug/sanskrit_words.txt --tool-filter dico --translation-cache-db data/cache/langnet.duckdb
```

Use `--dry-run --output json` to inspect how many translation projections are
already cached or missing without making network calls.

`encounter --output json` includes a top-level `translation_cache` object with
the resolved mode, cache DB path, availability, hit/miss counts before and after
projection, and any rows written by explicit population.

Use `translation-cache` for cache maintenance without touching lookup or
normalization rows:

```bash
just cli translation-cache status --output json
just cli translation-cache clear --yes --output json
```

The maintenance JSON uses schema version `langnet.translation_cache.v1`; its
schema lives at `docs/schemas/translation-cache.v1.schema.json`.

It also includes a top-level `ranking` array aligned to the sorted bucket list.
Each item reports the bucket sort key, preferred-lemma rank, learner-quality
score, source-order signals, translation/bilingual source flags, source tools,
bucket lemmas, and short human-readable reasons. This is the preferred surface
for future web renderers that need to explain why one meaning appears before
another.

This mode reads existing cache rows first, calls OpenRouter only for missing
translation keys, writes successful translations back to the cache, and then
displays the projected English evidence. It requires `OPENAI_API_KEY` only when
a cache miss must be populated.

In the JSON, look for a witness whose `source_tool` is `translation`. Its evidence should include:

- `source_lexicon`: `gaffiot` or `dico`
- `source_ref`: the original French entry reference
- `source_text_hash`: the hash of the exact French source text that was translated
- `source_text_lang`: the language of the source text used for the cache key, currently `fr`
- `gloss_lang`: the language of the derived gloss object, currently `en`
- `translation_id`: the cache identity
- `model`, `prompt_hash`, and `hint_hash`
- `derived_from_tool`: the source tool, such as `gaffiot` or `dico`
- `derived_from_sense`: the source French sense anchor

The high-fidelity rule applies here too: the English gloss expands the source evidence for learners, but the source French triple remains the evidence-bearing input and must stay inspectable.

### Evidence Walkthrough: Latin `lupus`

Use `encounter` for the learner-facing view:

```bash
just cli encounter lat lupus all --no-cache --max-buckets 3
```

Then inspect the exact triples that the reducer can consume:

```bash
just cli triples-dump lat lupus all --no-cache --output json --predicate gloss --max-triples 5
```

For each displayed meaning, match the bucket text to a `gloss` triple. The
important fields are:

- `subject`: the sense anchor that received the gloss.
- `object`: the source gloss text used by WSU extraction.
- `metadata.evidence.source_tool`: the backend witness, such as `whitaker`, `diogenes`, `gaffiot`, or `translation`.
- `metadata.evidence.source_ref`: the source-local dictionary/reference identifier when available.
- `claim_id` and `claim_tool`: the claim row that emitted the triple.

If a translated Gaffiot bucket is displayed first, the corresponding English
witness should also expose `translated_from`, `translation_id`, and
`metadata.evidence.derived_from_sense`; use those fields to find the original
French source witness in the same claim.

Triples use this shape:

```json
{
  "subject": "lex:lupus#noun",
  "predicate": "has_sense",
  "object": "sense:lex:lupus#noun#...",
  "metadata": {
    "evidence": {
      "source_tool": "whitaker",
      "call_id": "...",
      "response_id": "...",
      "extraction_id": "...",
      "derivation_id": "...",
      "claim_id": "...",
      "raw_blob_ref": "raw_text"
    }
  }
}
```

## Reading Triples

| Anchor | Meaning |
| --- | --- |
| `form:<surface>` | observed input or inflected surface form |
| `interp:...` | one scoped interpretation of a form |
| `lex:<lemma>` | normalized lexical item |
| `sense:<lex>#...` | source-backed sense node |

Common predicates:

- `has_interpretation`
- `realizes_lexeme`
- `has_sense`
- `gloss`
- `has_citation`
- `has_morphology`
- `has_pos`, `has_case`, `has_number`, `has_gender`, `has_tense`, `has_voice`, `has_mood`
- `has_feature` for tool-specific details

The canonical predicate/evidence reference is `docs/technical/predicates_evidence.md`.

## Sanskrit CDSL Display

CDSL source rows are stored and queried in Sanskrit Lexicon/Cologne-style SLP1 keys. For example, `dharma` is backed by the source key `Darma`, `dharmaḥ` by `DarmaH`, and `kṛṣṇa` by `kfzRa`.

Runtime triples preserve those source-near forms as evidence:

- `display_iast` is the learner-facing form.
- `display_slp1` is the CDSL/source key.
- `display_gloss` is a conservative learner-facing gloss string for CDSL entries. It currently preserves source content and applies display-safe transliteration transforms only.
- `source_entry` identifies the dictionary row and CDSL source keys.
- `source_segments` stores ordered raw/display segment pairs with conservative `segment_type` and `labels` where recognized; unrecognized source text remains present rather than removed.
- `source_encoding` is usually `slp1`.

The `encounter` command uses these fields for display. It shows IAST forms first and source keys separately, prefers `display_gloss` when present, and summarizes typed cross-reference/source-reference/example segments as compact source notes unless `--no-source-details` is passed. The raw CDSL entry text remains available as the `gloss` triple object with source references.

## Evidence Fields

| Field | Meaning |
| --- | --- |
| `source_tool` | backend or source family that produced the assertion |
| `call_id` | planned tool call that led to the claim |
| `response_id` | raw response used by extraction, when available |
| `extraction_id` | structured extraction effect |
| `derivation_id` | normalized derivation effect |
| `claim_id` | claim projection that emitted the triple |
| `source_ref` | stable dictionary/source entry reference, when available |
| `raw_blob_ref` | raw payload field such as `raw_text`, `raw_html`, or `raw_json` |
| `display_iast` | learner-facing Sanskrit display form, especially for CDSL SLP1 entries |
| `display_slp1` | raw or source-near Sanskrit SLP1 form for debugging and round-trip checks |
| `display_gloss` | learner-facing display string for a source gloss; raw source text remains the triple object |
| `source_entry` | structured source-row identity, such as CDSL dictionary id, line number, source ref, and source keys |
| `source_segments` | ordered source-complete segments with raw and display text |
| `source_encoding` | encoding of source-near display fields, for example `slp1` |

## Display Policy

Future learner-facing output should order information this way:

1. Headword/form.
2. Morphology or source-backed analysis when it clarifies the form, especially Sanskrit Heritage.
3. Grouped meanings.
4. Citations and source evidence.
5. Source disagreements or caveats.

Backend-keyed output remains useful for debugging, but learner-facing examples should now prefer `encounter` because it follows the claim-to-WSU reduction path.
