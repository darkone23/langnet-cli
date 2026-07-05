# Reader Corpus Session Wrap-Up

Date: 2026-05-14

This is the resumption note for the reader/corpus work before pivoting to a new
side project. The project is still in active development, but the current
foundation is usable for corpus-operator exploration and web-reader integration
work.

## Current Goal

Build a source-agnostic, local, cleaned DuckDB reader corpus that can answer:

- what works are available;
- what authors are available;
- what works are by, attributed to, or traditionally linked to a person;
- what is inside a work;
- how to read an exact segment by stable `work_id`, CTS work URN, or native
  catalog address.

The normal learner-facing interface should not require import-source knowledge.
Source/import fields stay available for audit and debugging.

## Current Catalogs

Generated development catalogs live under `examples/debug/`. They are not
durable packaged data.

- `examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb`
  - PHI/TLG legacy curated catalog.
  - Last recorded status: 7,836 works, 10,591,345 segments, 87,197,666 tokens,
    2,196 physical book DB files, 0 source errors, strict validation 0 issues.
- `examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb`
  - Sanskrit curated catalog.
  - Last recorded status: 977 works, 3,319,944 segments, 26,382,642 tokens, 0
    source errors, strict validation 0 issues, 564 remaining `Unknown` display
    authors, 38 accepted claim-level attribution records.
- `examples/debug/reader_perseus_full_curated_current/catalog.duckdb`
  - Perseus curated catalog.
  - Last recorded status: 1,223 works, 2,298 artifacts, 950,141 segments,
    strict validation 0 issues.
- `examples/debug/reader_digiliblt_anonymous_overlay_verify/catalog.duckdb`
  - digilibLT overlay proof/audit catalog.
  - Last recorded status: 390 works/artifacts, 112,104 segments, strict
    validation 0 issues.

## Work Completed This Session

- Implemented and tested reader catalog/storage surfaces for works, contents,
  exact segment reads, author sections, native author indexes, aliases,
  metadata overlays, and attribution claims.
- Added curated metadata policy:
  - display metadata overlays live under `data/curated/reader_metadata/`;
  - ambiguous or historical authorship evidence lives under
    `data/curated/reader_attributions/`;
  - contained/sub-work declarations live under
    `data/curated/reader_contained_works/`.
- Improved PHI/TLG legacy import:
  - one logical catalog work per IDT work;
  - one shared physical book DB per source text file where appropriate;
  - generated CTS-equivalent work URNs for clean PHI/TLG ids;
  - canon metadata files are treated as source metadata, not reader works.
- Improved Sanskrit import/title cleanup:
  - better GRETIL title derivation;
  - header metadata support for grouped/single-file Sanskrit text dumps;
  - reduced raw filename-looking titles and title-prefix authors.
- Improved author index quality:
  - TLG homonym disambiguation now prefers canon name descriptors and then
    category labels;
  - accepted `author_id` overlays can canonicalize duplicate display authors;
  - duplicate-looking titles such as `Fragmenta` are preserved as distinct
    works when the authority/work identity differs.
- Added contained-work handling for the Bhagavadgita:
  - `reader works --query bhagavad` returns contained `Bhagavadgita`;
  - `reader authors --language san --query vyasa` returns `Vyasa`;
  - `reader works --language san --author-id langnet:reader:author:san:vyasa`
    returns both `Mahabharata` and contained `Bhagavadgita`.

## Last Fix

Problem: The Bhagavadgita showed up in broad work search as a contained work,
but it did not participate correctly in the author-index/author-selector path.

Root cause: `list_works()` returned contained works for broad searches, but
`_list_contained_work_rows()` returned no rows whenever `author_id` was passed.
Also, `_raw_author_rows()` built the author index only from top-level `works`,
so accepted contained-work authors could be invisible unless the parent work
also had that display author.

Fix:

- `src/langnet/reader/storage.py`
  - `_raw_author_rows()` now unions accepted `contained_works` into author
    index source rows.
  - `_list_contained_work_rows()` now supports synthetic author selectors such
    as `langnet:reader:author:san:vyasa`.
- `tests/test_reader_storage.py`
  - regression test ensures a Bhagavadgita-style contained work appears under
    the contained author's author selector.

Verification:

```bash
just test tests.test_reader_storage
just ruff-format --check
just ruff-check
```

Observed result:

- `tests.test_reader_storage`: 17 tests OK.
- `ruff format --check`: 247 files already formatted.
- `ruff check`: all checks passed.

Real-catalog spot checks:

```bash
just cli reader --catalog examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb \
  authors --language san --query vyāsa --output json

just cli reader --catalog examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb \
  works --language san --author-id langnet:reader:author:san:vyasa --output json
```

Observed result:

- author index includes `Vyāsa` with selector
  `langnet:reader:author:san:vyasa`;
- works by that selector include:
  - `Mahābhārata`;
  - contained `Bhagavadgītā` with CTS work URN `urn:cts:sanskritLit:mbh.bhg`.

## How To Resume

Start by reading these files:

- `docs/READER_CORPUS_STATUS.md`
- `docs/READER_CLI_HANDOFF.md`
- `docs/READER_CLI_BEGINNER_GUIDE.md`
- `docs/READER_WEB_CONTRACT.md`
- `docs/archive/2026-05-doc-overhaul/plans/reader-corpus-quality-roadmap.md`
- `docs/plans/completed/infra/reader-metadata-overlay-plan.md`
- `docs/plans/completed/infra/reader-attribution-claims-implementation.md`

Then run a quick smoke check:

```bash
export CATALOG=examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb

just cli reader --catalog $CATALOG summary
just cli reader --catalog $CATALOG works --query bhagavad --output json
just cli reader --catalog $CATALOG authors --language san --query vyāsa --output json
just cli reader --catalog $CATALOG works --language san \
  --author-id langnet:reader:author:san:vyasa --output json
just cli reader --catalog $CATALOG validate --output json
```

Use `nu`, not `jq`, for JSON inspection.

## Open Work

- Continue Sanskrit metadata enrichment for remaining `Unknown` works,
  prioritizing named works likely to appear in dictionary entries.
- Add more research-backed overlays for duplicate or unclear authors, especially
  Greek and Sanskrit buckets where display names collide.
- Preserve ambiguity instead of dropping it:
  - use display overlays only when a canonical display value is justified;
  - use attribution claims for possible, traditional, disputed, commentator,
    compiler, redactor, translator, and editor relationships.
- Validate `docs/READER_CLI_BEGINNER_GUIDE.md` against the current catalogs
  after the next rebuild.
- Prepare the bulk classification pass after catalog cleanliness is stable:
  author/work date range, period/category, unknown/disputed/anonymous flags, and
  influence/popularity score.
- Investigate local `~/cltk-data/lat/lexicon` as a future dictionary/lexicon
  corpus integration source after the current reader foundation is stable.
- Keep cleaning superseded debug builds under `examples/debug/` only after a
  newer replacement catalog validates.

## Resumption Rules

- No git ceremony unless explicitly requested.
- Use `just` commands for project tasks.
- Use `nu` instead of `jq`.
- Keep local scratch/debug output under `examples/debug/`.
- Do not store host-local paths or `examples/debug` paths as curated evidence
  citations.
- Curated evidence citations should use durable web URLs or portable source-root
  references such as `sanskrit-dcs:data/...`, `perseus:...`, or `digiliblt:...`.
