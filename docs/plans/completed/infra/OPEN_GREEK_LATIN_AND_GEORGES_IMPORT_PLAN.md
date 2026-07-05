# OpenGreek+Latin Reader Import and Georges 1913 Dictionary Plan

Status: active
Owner: @architect, @coder, @auditor
Created: 2026-06-05
Last updated: 2026-06-05

## Goal

Make OpenGreek+Latin imports and Georges 1913 dictionary support reliable enough
to be treated as first-class LangNet data sources.

The current state is a useful bootstrap, not the final architecture:

- Georges 1913 builds successfully into `data/build/lex_georges_1913.duckdb`.
- OpenGreek+Latin source roots can be parsed with the generic Perseus TEI parser
  for many files.
- Generic OpenGreek+Latin parsing exposed corpus-specific reliability issues:
  duplicate source trees, multiple editions per work, root-level non-CTS files,
  zero-segment files, and weak synthetic identity handling.

## Non-goals

- Do not import every XML file blindly.
- Do not treat generated/synthetic CTS-like IDs as real source CTS authority.
- Do not collapse multiple editions silently without a recorded policy.
- Do not wire Georges into production lookup behavior until the translation
  pipeline can distinguish dictionaries, language direction, and ranking.

## Current verified facts

### Georges 1913

Build command:

```bash
just cli-databuild build-georges-1913 \
  --source-dir /home/nixos/opengreekandlatin/Latin/Georges_1913-avr17.col
```

Verified build artifact:

```text
data/build/lex_georges_1913.duckdb
entry_count: 167397
lex_id: GEORGES_1913_DEM_LAT
size: about 135 MB
```

Implementation issue already fixed:

- `.col` source has a trailing textual footer after valid compressed chunks.
- The parser now stops cleanly at that footer instead of treating it as a zlib
  block.

### OpenGreek+Latin source roots

Requested roots:

```text
/home/nixos/opengreekandlatin/Latin
/home/nixos/opengreekandlatin/csel-dev
/home/nixos/opengreekandlatin/patrologia_latina-dev
/home/nixos/opengreekandlatin/church_fathers-dev
```

Observed source tree shape:

```text
Latin: 7 selected data XMLs
CSEL: data/ plus Volumes/
Patrologia: data/, corrected/, split/, volumes/
Church Fathers: root-level XML files
```

Key issue:

- `patrologia_latina-dev` contains overlapping views of the same corpus.
- Importing `data/`, `corrected/`, `split/`, and `volumes/` together creates
  duplicate/transient artifacts and can exhaust disk.

Temporary mitigation already added:

- Prefer `data/` subtree when present.
- Preserve root-level XML files for corpora like `church_fathers-dev`.
- Use synthetic `urn:cts:langnet:...` fallback namespace for non-CTS files.
- Fix root-level synthetic fallback IDs so files do not collapse to one work.

This mitigation is not the final importer.

## Desired architecture

Create an OpenGreek+Latin-specific reader import layer instead of continuing to
special-case generic Perseus parsing.

Proposed modules:

```text
src/langnet/reader/opengreekandlatin.py
tests/test_reader_opengreekandlatin_import.py
```

The new module should expose:

```python
@dataclass(frozen=True)
class OglSourceCandidate:
    collection_id: str
    source_path: Path
    source_root: Path
    source_view: str
    source_priority: int
    source_id: str
    cts_work_urn: str | None
    cts_edition_urn: str | None
    synthetic_work_id: str | None
    edition_key: str
    import_policy: str


def discover_ogl_sources(root: Path, collection_id: str) -> list[OglSourceCandidate]:
    ...


def parse_ogl_tei(candidate: OglSourceCandidate) -> ParsedBook:
    ...
```

## Source selection policy

### `opengreekandlatin_latin`

Default policy:

- Prefer `data/`.
- Import CTS-style TEI text files.
- Exclude build/repository metadata XML.

Expected behavior:

- One source file normally maps to one reader work/artifact.

### `opengreekandlatin_csel`

Default policy:

- Prefer `data/`.
- Treat `Volumes/` as an alternate edition/source view, not default import.
- Preserve edition identity when multiple files represent the same work.

Open decision:

- If two files share the same CTS work URN but have distinct edition URNs, keep
  them as separate editions/artifacts under one work.
- If two files share both work and edition URNs, select one deterministically and
  record the skipped duplicate.

### `opengreekandlatin_patrologia`

Default policy:

- Import `data/` only.
- Treat `corrected/`, `split/`, and `volumes/` as alternate views.
- Add a future CLI flag for explicit alternate-view import:

```text
--opengreekandlatin-patrologia-view data|corrected|split|volumes|all
```

Acceptance rule:

- Default Patrologia import must not write duplicate transient book artifacts for
  all views.
- It must be possible to explain why every skipped XML was skipped.

### `opengreekandlatin_church_fathers`

Default policy:

- Import root-level XML files.
- Synthesize stable LangNet work IDs using collection, root/source slug, and file
  stem.
- Extract title and author from TEI header where possible.
- Never collapse root-level files into one synthetic work.

## Identity policy

Use real CTS URNs only when source files provide real CTS URNs.

For non-CTS files:

```text
work_id: urn:cts:langnet:<collection>.<source-slug>_<file-stem>
edition_id: urn:cts:langnet:<collection>.<source-slug>_<file-stem>.auto
cts_work_urn: null or synthetic only if current schema requires a value
canonical_text_id: generated ctsv2 id from title/incipit plus disambiguator
```

Preferred schema improvement:

- Add an explicit `synthetic_identity` or source metadata marker so downstream
  code can distinguish source CTS identity from LangNet synthetic identity.

## Segment extraction policy

The OGL parser should support:

- `l`, `p`, `ab`, `seg`, `head`, and milestone-style structures.
- TEI `div` hierarchy as citation context.
- Fallback paragraph segmentation only after preserving source citation labels.
- Zero-segment files should be recorded as skipped with reason
  `no_text_segments`, not silently dropped.

For each parsed file, record:

```text
source_view
segment_strategy
segment_count
line_count
paragraph_count
has_real_cts_urn
synthetic_identity_used
```

## Catalog behavior

The importer should write source-file metadata before parsing, but it must also
record import outcomes:

```text
text_imported
skipped_duplicate
skipped_alternate_view
skipped_no_segments
parse_error
```

If the existing `source_files.file_status` is not enough, add source metadata
rows:

```text
subject_kind: source_file
key: import_status
key: import_skip_reason
key: source_view
key: selected_by_policy
```

## Georges 1913 first-class dictionary plan

### Current issue

Georges is currently built through the DICO builder path. It produces a useful
DuckDB artifact, but the schema/table names still reflect the older
French-to-Sanskrit DICO model (`entries_fr`).

### Desired dictionary identity

```text
lex_id: GEORGES_1913_DEM_LAT
language: lat
metalanguage: de
direction: lat -> de
source_family: opengreekandlatin
default_artifact: data/build/lex_georges_1913.duckdb
```

### Required implementation

1. Add explicit dictionary registry metadata for Georges.
2. Expose Georges in CLI dictionary inventory.
3. Add lookup service support:
   - Latin query normalization.
   - German definition/display metadata.
   - ranking separate from Gaffiot/Whitaker.
4. Translation pipeline integration:
   - Latin token -> candidate lemmas -> Georges lookup.
   - German definition snippets available as supporting evidence.
   - Do not mix German definitions into English explanation unless explicitly
     translated or labeled.
5. Optional translation sub-pipeline:
   - `de -> en` gloss summarization for UI convenience.
   - Preserve original German text as primary evidence.

### Preferred schema direction

Either:

- keep the current table for compatibility and add lexicon metadata table, or
- create a new normalized table shape for all HTML/COL dictionaries.

Minimum required metadata table:

```sql
CREATE TABLE IF NOT EXISTS lexicon_metadata (
  lex_id VARCHAR PRIMARY KEY,
  source_label VARCHAR NOT NULL,
  source_language VARCHAR NOT NULL,
  metalanguage VARCHAR NOT NULL,
  direction VARCHAR NOT NULL,
  source_path VARCHAR,
  entry_count INTEGER,
  build_version VARCHAR
);
```

## Implementation phases

### Phase 1: OGL discovery and policy tests

Owner: @coder

Tasks:

- Add `src/langnet/reader/opengreekandlatin.py`.
- Move OGL filtering/source selection out of `ReaderBuilder`.
- Unit-test source discovery against synthetic fixtures:
  - `data/` preferred over `split/`.
  - root-level Church Fathers files preserved.
  - metadata XML excluded.
  - duplicate edition candidates classified.

Acceptance:

```bash
just test test_reader_opengreekandlatin_import
```

### Phase 2: OGL parser and import outcome metadata

Owner: @coder

Tasks:

- Add OGL-specific parse wrapper around TEI parsing.
- Add import outcome metadata for skipped files and zero-segment files.
- Ensure synthetic IDs are stable and unique.
- Ensure multiple editions per work are represented or skipped by policy with
  recorded reason.

Acceptance:

- A focused import of all four roots succeeds without disk exhaustion.
- All source files have either an artifact or an explicit skip/error reason.
- Church Fathers produces three distinct works, not one.

### Phase 3: Production OGL rebuild

Owner: @sleuth, @coder

Tasks:

- Clean any failed OGL artifacts.
- Run production `--no-wipe` import or full reader rebuild depending on storage
  safety.
- Query and save counts:
  - source files by collection/status
  - works by collection
  - artifacts by collection
  - skipped files by reason

Acceptance:

```text
opengreekandlatin_latin: imported works > 0
opengreekandlatin_csel: imported works > 0
opengreekandlatin_patrologia: imported works > 0
opengreekandlatin_church_fathers: imported works = 3 unless source files change
source_error_count: 0 or fully explained
```

### Phase 4: Georges dictionary registry

Owner: @coder

Tasks:

- Add first-class Georges dictionary metadata.
- Rename or abstract DICO-specific table assumptions where necessary.
- Add CLI inventory/listing.
- Add lookup command path if missing.

Acceptance:

```bash
just cli-databuild build-georges-1913 \
  --source-dir /home/nixos/opengreekandlatin/Latin/Georges_1913-avr17.col

just cli dictionary list --output json
just cli lookup lat amo --dictionary georges-1913 --output json
```

If `dictionary list` or dictionary-scoped `lookup` commands do not exist, add
the smallest compatible CLI surface.

### Phase 5: Translation pipeline integration

Owner: @architect, @coder, @auditor

Tasks:

- Make Georges available as a Latin lexical evidence source.
- Label German metalanguage clearly.
- Add optional `de -> en` glossing only as derived convenience.
- Add UI/API flags so users can see source dictionary and language.

Acceptance:

- Latin lookup can show Georges entries.
- Translation pipeline can cite Georges as supporting evidence.
- UI does not misrepresent German definitions as English.
- Tests cover dictionary-source attribution.

## Validation commands

OGL:

```bash
just cli-databuild reader \
  --opengreekandlatin-latin-dir /home/nixos/opengreekandlatin/Latin \
  --opengreekandlatin-csel-dir /home/nixos/opengreekandlatin/csel-dev \
  --opengreekandlatin-patrologia-dir /home/nixos/opengreekandlatin/patrologia_latina-dev \
  --opengreekandlatin-church-fathers-dir /home/nixos/opengreekandlatin/church_fathers-dev \
  --no-wipe \
  --progress-every 500
```

Georges:

```bash
just cli-databuild build-georges-1913 \
  --source-dir /home/nixos/opengreekandlatin/Latin/Georges_1913-avr17.col
```

Catalog inspection:

```bash
bash ./.justscripts/run-dev-tool python - <<'PY'
import duckdb
with duckdb.connect("data/build/reader/catalog.duckdb", read_only=True) as conn:
    print(conn.execute("""
        SELECT collection_id, COUNT(*)
        FROM works
        WHERE collection_id LIKE 'opengreekandlatin_%'
        GROUP BY collection_id
        ORDER BY collection_id
    """).fetchall())
PY
```

## Risks

- Disk exhaustion if duplicate Patrologia views are imported.
- Silent edition collapse if multiple files share a CTS work ID.
- Synthetic IDs being mistaken for source CTS authority.
- Source metadata rows registered without corresponding works if imports fail
  mid-run.
- German definitions being displayed as if they were English translation data.

## Current implementation status

Phase 1 and the core of Phase 2 are implemented:

- Added `src/langnet/reader/opengreekandlatin.py`.
- Added OGL path-policy discovery and source-view classification.
- Added import outcome metadata for imported, alternate-view skipped,
  duplicate skipped, zero-segment skipped, and parse-error files.
- Wired `ReaderBuilder` to use the OGL discovery/parser policy module.
- Added `unittest` fixtures in `tests/test_reader_opengreekandlatin_import.py`
  that run under the project `just test` wrapper.
- Added `lexicon_metadata` to the DICO/Georges builder path.
- Georges limited smoke build confirms:
  `GEORGES_1913_DEM_LAT`, `source_language=lat`, `metalanguage=de`,
  `direction=lat->de`.
- Updated the existing full `data/build/lex_georges_1913.duckdb` artifact with
  `lexicon_metadata` without forcing a full rebuild.
- Cleaned up `ReaderBuilder` OGL metadata registration so each OGL root is
  discovered once per metadata pass.

Real-root OGL discovery policy currently reports:

```text
latin:      text_imported=7
csel:       text_imported=264, skipped_alternate_view=81, skipped_duplicate=7
patrologia: text_imported=1275, skipped_alternate_view=2962,
            skipped_no_segments=3, skipped_duplicate=1
church:     text_imported=3
```

Do not run production OGL import until @auditor reviews the new policy module.

Focused validation already run:

```text
just test test_reader_opengreekandlatin_import
.....
Ran 5 tests
OK

temporary ReaderBuilder OGL catalog smoke:
works=1
source_files=[('skipped', 2), ('text', 1)]
import_status=[('skipped_alternate_view', 1), ('skipped_duplicate', 1), ('text_imported', 1)]

existing Georges artifact metadata:
('GEORGES_1913_DEM_LAT', 'Georges 1913 German-Latin', 'lat', 'de', 'lat->de', 167397)
```

## Immediate next step

Have @auditor review Phase 1/2, then run production OGL import if approved.

Recommended agent handoff:

```text
@auditor Review Phase 1/2 implementation from
docs/plans/completed/infra/OPEN_GREEK_LATIN_AND_GEORGES_IMPORT_PLAN.md:
src/langnet/reader/opengreekandlatin.py, ReaderBuilder wiring, OGL import
outcome metadata, synthetic ID policy, and Georges lexicon_metadata changes.
Focus on correctness, silent data-loss risks, and whether production OGL import
is safe to run.
```

## Production import update - 2026-06-05

Auditor review found one blocking production issue during post-import inspection:
CSEL and Patrologia can share the same source CTS work URN. Because
`works.work_id` is globally primary-keyed, raw CTS work IDs caused later OGL
collections to overwrite earlier catalog rows. The concrete observed symptom was
`opengreekandlatin_csel` reporting `264` imported source files but only `235`
works/artifacts.

Fix applied:

- OGL parsed books now use LangNet-scoped catalog keys:
  `urn:langnet:ogl:<collection_id>:<source_id>`.
- Source CTS authority remains preserved in `cts_work_urn` and
  `cts_edition_urn`.
- Source metadata now includes `catalog_work_id` and `catalog_edition_id` for
  auditability.
- Segment IDs, segment foreign keys, addresses, and citation references are
  rewritten consistently to the catalog-scoped IDs.
- Added a temp catalog smoke proving CSEL and Patrologia can import the same CTS
  work URN without overwriting each other.

Production cleanup and reimport:

- Removed the pre-fix OGL catalog rows and OGL book directories only.
- Re-ran OGL import with `--no-wipe`.
- Import completed with `source_error_count=0`.

Final production OGL counts:

```text
works_by_collection:
opengreekandlatin_church_fathers: 3
opengreekandlatin_csel: 264
opengreekandlatin_latin: 7
opengreekandlatin_patrologia: 1275

artifacts_by_collection:
opengreekandlatin_church_fathers: 3
opengreekandlatin_csel: 264
opengreekandlatin_latin: 7
opengreekandlatin_patrologia: 1275

source_files_by_status:
opengreekandlatin_church_fathers text: 3
opengreekandlatin_csel skipped: 88
opengreekandlatin_csel text: 264
opengreekandlatin_latin text: 7
opengreekandlatin_patrologia skipped: 2966
opengreekandlatin_patrologia text: 1275

missing_artifacts_for_imported_sources: []
non_namespaced_ogl_work_ids: []
parse_errors: []
```

Disk impact after import:

```text
opengreekandlatin_church_fathers: 8.9M
opengreekandlatin_patrologia: 3.0G
opengreekandlatin_csel: 638M
opengreekandlatin_latin: 15M
filesystem free: 15G
```

## OGL author/title audit update - 2026-06-05

Additional reader audit found that raw import coverage was correct, but author
and title quality was not sufficient for Patrologia and fallback Church Fathers
sources.

Fixes applied:

- OGL importer now reads nearby CTS inventory files (`__cts__.xml`) for
  `groupname`, `title`, `edition label`, and `edition description`.
- Weak TEI titles such as `tmp1340.tmp1340` or generic
  `Patrologiae Cursus Completus. Series Latina (PL)` are replaced with CTS
  inventory titles when available.
- Unknown/blank/anonymous parsed authors are replaced with CTS inventory
  groupnames when available.
- Remaining Patrologia cases use conservative title-derived labels such as
  `Incertus`, `Concilium`, `Patrologia Latina editor`, or explicit named
  authors when the title itself identifies the author.
- Fallback/synthetic OGL author IDs now use `urn:langnet:ogl-author:...` so
  distinct synthetic works do not collapse under a shared fallback CTS group.
- CTSv2 remains the preferred reader-facing canonical identity; source CTS URNs
  remain provenance/source metadata.

Final validation after reimport:

```text
works_by_collection:
opengreekandlatin_church_fathers: 3
opengreekandlatin_csel: 264
opengreekandlatin_latin: 7
opengreekandlatin_patrologia: 1275

artifacts_by_collection matches works_by_collection.
missing_artifacts_for_imported_sources: []
unknown_authors: []
weak_titles: []
missing_ctsv2_ids: []
non_namespaced_work_ids: []
parse_errors: []
```

Church Fathers sample now distinguishes:

```text
Gregory of Nazianzus -> Christus Patiens
Gregory of Nazianzus -> Five Theological Orations
Jesus ben Sira -> Ecclesiasticus: The Greek Text of Codex 248
```

Related future plan:

- `docs/plans/completed/infra/LANGNET_CANONICAL_CATALOG_EXPORT_PLAN.md`

## Final integration update - 2026-06-05

The OGL import stack is now integrated across the reader catalog, search index,
CLI metadata, and public UI provenance documentation.

Implemented since the author/title audit:

- OGL language inference now uses TEI `langUsage` when the parsed primary
  language is `und`; Church Fathers fallback editions now surface as `grc`.
- OGL fallback author IDs are collection-scoped to avoid unrelated synthetic CTS
  works collapsing under one fallback author identity.
- `reader collections` now returns human-readable labels and descriptions for
  imported collections including First1KGreek, digilibLT, OGL Latin, OGL CSEL,
  OGL Patrologia, OGL Church Fathers, PHI, TLG, Perseus, and Sanskrit sources.
- `/about` now includes a source-provenance section that lists reader corpora,
  lexical/morphological sources, external engines, curated LangNet layers, and
  generated/indexed artifacts.
- The public-site copy contract was extended so the provenance section is covered
  by Svelte/TypeScript checking.
- The reader search index was rebuilt after the final OGL reimport.

Final reader/search validation:

```text
OGL imported works:
opengreekandlatin_church_fathers: 3
opengreekandlatin_csel: 264
opengreekandlatin_latin: 7
opengreekandlatin_patrologia: 1275

OGL languages:
opengreekandlatin_church_fathers: grc 3
opengreekandlatin_csel: lat 264
opengreekandlatin_latin: lat 7
opengreekandlatin_patrologia: lat 1275

quality gates:
source_error_count: 0
missing_artifacts_for_imported_sources: []
unknown_authors: []
weak_titles: []
missing_ctsv2_ids: []
non_namespaced_ogl_work_ids: []
search_index_issue_count: 0
```

Search index rebuild summary:

```text
segment_count: 9893627
work_count: 10872
language_counts:
  cop: 15670
  eng: 195678
  grc: 5939057
  heb: 66473
  lat: 1118583
  san: 2558166
fts_indexed: true
```

CLI/UI validation run:

```text
just test test_reader_opengreekandlatin_import
cd webapp && bun src/lib/reader/index.test.ts && bun run check
cd webapp && bun run build
```

All commands completed successfully.

Remaining follow-up candidates:

- Move this plan to `docs/plans/completed/infra/` once Georges is also signed
  off as first-class in the same release branch.
- Canonical catalog directory export is now implemented as described in
  `docs/plans/completed/infra/LANGNET_CANONICAL_CATALOG_EXPORT_PLAN.md`;
  presentation exports and archive packaging remain separate todo plans.
- Add deeper per-source licensing/attribution notes if the public provenance page
  needs to become a formal credits page rather than an input-inventory page.

## Georges runtime integration update - 2026-06-06

Georges 1913 is now wired as a first-class Latin lookup provider, not only as a
built provenance artifact.

Implemented:

- Added `src/langnet/execution/handlers/georges_1913.py`:
  - DuckDB-backed fetch client for `data/build/lex_georges_1913.duckdb`.
  - Headword normalization for Latin lookup.
  - `extract.georges_1913.json`, `derive.georges_1913.entries`, and
    `claim.georges_1913.entries` handlers.
  - Evidence triples use `source_tool=georges_1913`, `source_lang=de`, and
    source refs such as `georges_1913:Georges_1913-avr17.col:95920#lupus:0`.
- Registered Georges in the execution registry, planner local lexicon calls,
  planner Latin defaults, CLI fetch client factory, and tool catalog.
- Extended translation projection to accept German (`de`) source glosses and
  build translation-cache keys for `georges_1913`.
- Updated ranking/source-priority logic so Georges is treated as bilingual source
  evidence.
- Updated the web lookup tool model so Latin dictionary filters include
  `georges_1913` and web payload mapping preserves Georges source labels,
  source refs, and translation metadata.
- Avoided unsupported word-index neighborhood warnings by falling Georges lookup
  back to generic Latin word-index context until a dedicated Georges word-index
  source is implemented.

Validation:

```text
python -m py_compile src/langnet/execution/handlers/georges_1913.py ...
just cli tools lat --output json
just cli encounter lat lupus georges_1913 --translation-mode cache --output json
just cli encounter lat lupus all --translation-mode cache --output json
cd webapp && bun src/lib/search-data.test.ts && bun src/lib/server/langnet-cli-payload.test.ts && bun src/lib/reader/reader-api.test.ts && bun run check
cd webapp && bun run build
```

Live server verification after prod build/restart:

```text
/api/health -> ok
/api/search?language=lat&q=lupus&dictionary=georges_1913&translation=cache
  dictionaries: [georges_1913]
  source_tools includes georges_1913
  translation.source_lexicon: georges_1913
  translation_cache.before.total: 1

/api/search?language=lat&q=lupus&translation=cache
  source_tools includes georges_1913
  translation_cache.before.total: 3

/api/reader?mode=authors&language=grc&q=Jesus%20ben%20Sira&limit=10
  display_name: Jesus ben Sira
  work_count: 1
```

Remaining follow-up:

- Add dedicated Georges word-index list/neighborhood/wheel SQL if we want it to
  behave like Gaffiot/Lewis in word-index browsing.
- Improve reader UI discoverability so users understand that imported authors
  such as Jesus ben Sira are found in the Reader Authors view, while text search
  searches passage contents.

## Georges word-index and Reader discoverability integration - 2026-06-06

Completed follow-up integration work:

- Added `georges_1913` as a first-class Latin word-index source in `src/langnet/word_index/service.py`.
- Wired Georges into word-index source status, list, browse groups, nearby neighborhoods, and word wheel sampling.
- Removed the temporary CLI fallback that mapped `georges_1913` word-index anchors to `all`; direct Georges encounter actions now anchor against Georges.
- Fixed translation cache source-language projection so Georges entries carry `source_text_lang=de` instead of inheriting the French default.
- Clarified Reader discovery UI copy so author/catalog search is visibly distinct from passage text search, including the Jesus ben Sira case.
- Expanded focused tests for Georges source status, list payloads, browse grouping, wheel inclusion, tool catalog metadata, web search metadata, and translation projection behavior.

Validation performed:

- `python -m py_compile src/langnet/translation/projection.py src/langnet/word_index/service.py src/langnet/cli.py`
- `just test test_word_index test_word_index_ordering test_tool_catalog`
- `just test test_translation_projection test_encounter_translation`
- `cd webapp && bun src/lib/search-data.test.ts`
- `cd webapp && bun run check`
- `cd webapp && bun run build`
- `just cli word-index list lat --source georges_1913 --prefix lu --limit 5 --output json`
- `just cli word-index nearby lat lupus --source georges_1913 --radius 1 --output json`
- `just cli encounter lat lupus georges_1913 --translation-mode cache --output json`
- Restarted the process-compose-managed web service by killing the listener on `43210`; `/api/health` recovered successfully.
- Live API check: `/api/search?language=lat&q=lupus&dictionary=georges_1913&translation=cache` returns Georges-only evidence with `source_langs=["de"]`.
- Live API check: `/api/word-index?language=lat&source=georges_1913&mode=nearby&query=lupus&radius=1` returns a Georges `lupus` exact anchor.
- Live API check: `/api/reader?mode=authors&language=grc&q=Jesus%20ben%20Sira&limit=10` returns the OGL Jesus ben Sira author record.

Remaining follow-up candidates:

- Add a dedicated UI affordance from Reader text search no-results states to author/catalog search when the query resembles a name.
- Populate/refresh English translation-cache rows for high-value Georges entries now that `source_text_lang=de` is correct.
