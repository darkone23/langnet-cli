# Pedagogically Native Word Index Ordering

Status: Active
Source request: `/tmp/langnet-upstream-native-word-index-order-request.md`
Feature area: pedagogy

## Goal

Add explicit source-native, language-native, and learner-facing ordering metadata to `word-index` payloads so dictionary neighborhoods can explain their order honestly.

This should keep durable plumbing keys such as `wheel_order_key`, `source_order_key`, and `source_order_id`, but stop requiring the UI to infer whether those keys represent source order, native language collation, seeded discovery order, or fallback canonical-key order.

## Session Closure Note - 2026-05-11

The source-backed V1 ordering slice is stable enough to hand off for review or
continued UI work. The implemented surface now covers source-local `order`
metadata, collapsed lexeme-card ordering, merged source-window ordering,
seeded-discovery wheel ordering, and native section rails for Sanskrit, Greek,
and Latin.

For Sanskrit specifically, the section rail now follows the 52-item varnamala
and uses source-native CDSL SLP1 anchors for dictionary navigation. This means
the learner-facing label can stay pedagogically native while the clickable
anchor preserves distinctions that rough ASCII would collapse, such as `R` for
ण, `S` for श, `z` for ष, `kz` for क्ष, and `jY` for ज्ञ.

Verified closure checks from this session:

```bash
just test test_word_index_sections test_word_index_ordering test_paradigm_resolver test_paradigm_service test_cli_paradigm test_cli_paradigm_resolve
just cli word-index sections san --source all --output json
just cli word-index nearby san R --source cdsl --radius 1 --output json
just cli word-index nearby san S --source cdsl --radius 1 --output json
just cli word-index nearby san z --source cdsl --radius 1 --output json
just cli word-index nearby san kz --source cdsl --radius 1 --output json
just lint-all
just test-fast
```

Remaining follow-up work should be treated as new scope:

- build a standalone Sanskrit varga collation key for full source-independent
  ordering, if needed;
- add UI affordances that render section rails and source-window warnings
  clearly;
- broaden live fixture coverage for less common Sanskrit initials and dictionary
  sources beyond CDSL-backed anchors.

## Design Position

This is a metadata and pedagogy layer over existing word-index behavior. The first implementation should not reorder everything blindly. It should:

- preserve current stable ordering fields;
- add explicit `order` objects;
- label existing source-local, merged, discovery, and fallback policies;
- add native/language collation keys where they are defensible;
- disclose fallback ordering when native/source ordering is unavailable.

Follow-up request: `/tmp/langnet-upstream-native-alphabet-index-request.md`

The native alphabet request adds a complementary browsing surface: section
anchors for Greek alphabet, Latin alphabet, and Sanskrit varnamala rails. This
does not replace `word-index nearby`; it gives clients native display anchors
that can open source-backed neighborhoods.

## Proposed Payload Shape

Use an `order` object with:

```json
{
  "policy": "source-native",
  "label": "Sanskrit source order",
  "collation": "source",
  "key": "...",
  "display_key": "...",
  "explanation": "Ordered by MW source headword key."
}
```

Allowed policies:

- `source-native`
- `language-native`
- `canonical-key`
- `source-window-merge`
- `seeded-discovery`
- `fallback`

Allowed collations:

- `sa-varga`
- `sa-devanagari`
- `grc-lexical`
- `lat-lexical`
- `source`
- `canonical-key`
- `seeded-discovery`
- `merged-source-window`

## Implementation Tasks

### Task 1: Schema And Contract

Files:

- Modify `docs/schemas/word_index.v1.schema.json`
- Modify `tests/test_word_index.py`

Success marks:

- `items[]`, `source_entries[]`, top-level `neighborhood`, merged `neighborhood.groups[]`, and wheel payloads can carry an `order` object.
- Existing payloads remain backward compatible because `additionalProperties` already permits extension fields.
- Schema tests validate representative source, merged, fallback, and wheel ordering payloads.

Current slice:

- Added `docs/schemas/word_index.v1.schema.json` support for optional `order`
  objects on payloads, rows, source entries, neighborhoods, and grouped
  neighborhoods.
- Added `tests/test_word_index_ordering.py` coverage for source rows, collapsed
  cards, merged neighborhoods, grouped source windows, and wheel payload order.

### Task 2: Order Metadata Model

Files:

- Modify `src/langnet/word_index/service.py`
- Add focused tests in `tests/test_word_index_ordering.py`

Success marks:

- Source-local rows get `order.policy = "source-native"` or `canonical-key` depending on available source order evidence.
- Merged `source=all` neighborhoods get `order.policy = "source-window-merge"`.
- Wheel payloads get `order.policy = "seeded-discovery"`.
- Miss/nearest/fallback neighborhoods include an explanation tied to `anchor_status`.

Current slice:

- Source-local rows carry `source-native` order metadata when a
  `source_order_key` is available.
- Collapsed lexeme cards carry `canonical-key` order metadata, while preserving
  per-source `source_entries[].order`.
- Merged `source=all` neighborhoods carry `source-window-merge` metadata.
- Wheel payloads carry `seeded-discovery` metadata.

### Task 3: Sanskrit Ordering Keys

Files:

- Modify `src/langnet/word_index/service.py`
- Add tests in `tests/test_word_index_ordering.py`

Success marks:

- Sanskrit rows expose a Sanskrit-aware ordering key when a native/source key is available.
- Fallback roman/canonical ordering is explicitly labeled as fallback or canonical-key order.
- `word-index nearby san varnamala --source all --output json` can explain merged source neighborhoods without implying Latin alphabetic order.

Current limitation:

- Sanskrit source rows are labeled with `collation = "source"` for now. This is
  intentionally honest: it preserves the indexed source sequence and avoids
  claiming a standalone `sa-varga` collation before that key is implemented.

Current Sanskrit section slice:

- The Sanskrit section rail now exposes the 52-item varnamala used by the
  learner-facing documentation: 14 vowels, anusvara and visarga, 33 consonants,
  and the common conjuncts क्ष, त्र, and ज्ञ.
- Section labels and transliterations are learner-facing, but section anchors
  use source-native CDSL SLP1 prefixes. This keeps distinct Sanskrit phonemes
  from being collapsed by rough ASCII spellings: ऋ anchors with `f`, ङ with
  `N`, ट with `w`, ण with `R`, श with `S`, ष with `z`, क्ष with `kz`, and ज्ञ
  with `jY`.
- `word-index nearby san <anchor.query> --source cdsl` accepts those anchors and
  opens the corresponding source-local neighborhood.

### Task 3b: Native Section Anchors

Files:

- Add `docs/schemas/word_index_sections.v1.schema.json`
- Modify `src/langnet/word_index/service.py`
- Modify `src/langnet/cli.py`
- Add `tests/test_word_index_sections.py`

Success marks:

- `word-index sections san --source all --output json` returns varnamala section
  anchors grouped as vowels, vargas, semivowels, sibilants, aspirate, and
  common conjuncts.
- `word-index sections grc --source diogenes --output json` returns Greek
  alphabet section anchors.
- `word-index sections lat --source all --output json` returns Latin alphabet
  section anchors.
- Payloads use `langnet.word_index_sections.v1`, include a top-level `order`,
  and warn when section buckets should not be confused with full source cursor
  semantics.

### Task 4: Greek Ordering Keys

Files:

- Modify `src/langnet/word_index/service.py`
- Add tests in `tests/test_word_index_ordering.py`

Success marks:

- Greek rows preserve Greek display, beta/lookup key, source key, and Greek/source ordering metadata.
- Diogenes/LSJ source-local rows are labeled as source order when using source offsets.
- Fallback canonical order is explicitly labeled.

### Task 5: Documentation

Files:

- Modify `docs/OUTPUT_GUIDE.md`
- Modify `docs/ROADMAP.md`
- Modify `docs/PROJECT_STATUS.md`

Success marks:

- Docs state that `wheel_order_key` is durable plumbing, not necessarily alphabetic or native order.
- Docs explain `order.policy`, `order.collation`, and where `order` appears.
- Wheel/discovery and dictionary-neighborhood semantics are described separately.

## Acceptance Checks

```bash
just test test_word_index test_word_index_ordering
just lint-all
just test-fast
```

Live smoke checks, when local indices are available:

```bash
just cli word-index nearby san varnamala --source all --output json
just cli word-index nearby grc λόγος --source diogenes --output json
just cli word-index wheel san --count 5 --output json
```

The live JSON should include `order` metadata that lets the UI label panels as dictionary neighborhood, Sanskrit source order, Greek source order, merged source neighborhoods, fallback order, or discovery wheel without guessing from internal key names.
