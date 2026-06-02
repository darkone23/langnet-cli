# Strong's Greek Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user has asked for no git ceremony in this workspace, so do not add commit steps unless explicitly requested later.

**Goal:** Add a first-class Greek biblical/religious dictionary provider that can resolve forms such as `Ἠσαίᾳ` to source-backed Strong's Greek lexical evidence instead of returning no source-backed meaning or unrelated LSJ fuzzy matches.

**Architecture:** Implement `strongs_greek` as a local DuckDB-backed Greek-English provider, parallel to `bailly` and `lewis_1890`. A databuild step imports Strong's Greek XML into `data/build/lex_strongs_greek.duckdb`; a staged execution handler emits normal `has_sense`/`gloss` triples; planner/tool catalog/web UI plumbing exposes it as an optional/default Greek dictionary source. Keep this separate from LSJ/Bailly: Strong's is a biblical lexicon and should be labeled as such.

**Tech Stack:** Python, Click, DuckDB, XML `ElementTree`, `query_spec` staged tool plans, `RawResponseEffect`, `ExtractionEffect`, `DerivationEffect`, `ClaimEffect`, Svelte/TypeScript web tool metadata, `nose2`, `bun`, `just`.

---

## Source Evidence

Use these sources as the first implementation targets:

- Strong's Greek XML source: `https://github.com/morphgnt/strongs-dictionary-xml`
- Raw XML: `https://raw.githubusercontent.com/morphgnt/strongs-dictionary-xml/master/strongsgreek.xml`
- License noted by upstream: Creative Commons CC0 waiver / public-domain style release.
- Example verified entry: Strong G2268 has Greek `Ἡσαΐας`, transliteration `Hēsaḯas`, and definition/KJV gloss for Esaias/Isaiah.
- Optional future morphology source: `https://github.com/morphgnt/sblgnt`

Do not vendor or download source data during this plan execution unless the implementer is explicitly asked to do so. Tests should use local inline XML fixtures.

## Scope

Implement now:

- Tool filter: `strongs_greek`
- User label: `Strong's Greek`
- Short UI label: `Strong's`
- Role: `biblical/religious Greek dictionary entries`
- Databuild command: `strongs-greek`
- Default DB path: `data/build/lex_strongs_greek.duckdb`
- Source language: English (`source_lang="en"`)
- Translation cache: not needed
- Greek language only (`grc`)
- Lookup by Strong number, Greek lemma, normalized Greek key, transliteration, and generated biblical proper-name form aliases.

Do not implement now:

- Hebrew Strong's.
- Full MorphGNT/SBLGNT token integration.
- Septuagint morphology tables.
- Reader-corpus cross-links from `Ἠσαίᾳ` to all Isaiah passages.

The provider should still be compatible with future MorphGNT/SBLGNT work by storing `strongs_number`, `lemma_unicode`, `lemma_translit`, and generated alias provenance.

## Task 1: Databuild and Lookup

**Files:**

- Create: `src/langnet/databuild/strongs_greek.py`
- Modify: `src/langnet/databuild/paths.py`
- Modify: `src/langnet/cli_databuild.py`
- Test: `tests/test_strongs_greek_databuild.py`
- Test: `tests/test_cli_help.py`

- [ ] **Step 1: Write failing databuild tests**

Create `tests/test_strongs_greek_databuild.py` with an inline XML fixture:

```python
from pathlib import Path

from langnet.databuild.strongs_greek import (
    StrongsGreekBuildConfig,
    StrongsGreekBuilder,
    lookup_strongs_greek_entries_by_headword,
    normalize_strongs_greek_key,
)


STRONGS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<strongsdictionary>
  <entry strongs="02268">
    <strongs>2268</strongs>
    <greek BETA="*(HSAI/+AS" unicode="Ἡσαΐας" translit="Hēsaḯas"/>
    <pronunciation strongs="hay-sah-ee'-as"/>
    <strongs_derivation>of Hebrew origin;</strongs_derivation>
    <strongs_def> Hesaias (i.e. Jeshajah), an Israelite</strongs_def>
    <kjv_def>:--Esaias.</kjv_def>
  </entry>
</strongsdictionary>
"""


def test_normalize_strongs_greek_key_collapses_accents_breathings_and_iota() -> None:
    assert normalize_strongs_greek_key("Ἡσαΐας") == "ησαιασ"
    assert normalize_strongs_greek_key("Ἠσαίᾳ") == "ησαια"


def test_strongs_greek_build_imports_xml_entries_and_aliases(tmp_path: Path) -> None:
    source = tmp_path / "strongsgreek.xml"
    source.write_text(STRONGS_XML, encoding="utf-8")
    output = tmp_path / "lex_strongs_greek.duckdb"

    result = StrongsGreekBuilder(
        StrongsGreekBuildConfig(source_path=source, output_path=output)
    ).build()

    assert result.output_path == output
    exact = lookup_strongs_greek_entries_by_headword(["Ἡσαΐας"], output)
    dative = lookup_strongs_greek_entries_by_headword(["Ἠσαίᾳ"], output)
    translit = lookup_strongs_greek_entries_by_headword(["hesaias"], output)
    number = lookup_strongs_greek_entries_by_headword(["G2268"], output)

    assert exact[0]["strongs_number"] == "G2268"
    assert dative[0]["strongs_number"] == "G2268"
    assert dative[0]["matched_alias_kind"] == "generated_form"
    assert translit[0]["strongs_number"] == "G2268"
    assert number[0]["lemma_unicode"] == "Ἡσαΐας"
```

Run:

```bash
just test test_strongs_greek_databuild -q
```

Expected: FAIL because `langnet.databuild.strongs_greek` does not exist.

- [ ] **Step 2: Add the default build path**

Modify `src/langnet/databuild/paths.py`:

```python
def default_strongs_greek_path() -> Path:
    """
    Default output path for the Strong's Greek biblical dictionary index.
    """
    return build_dir() / "lex_strongs_greek.duckdb"
```

- [ ] **Step 3: Implement `src/langnet/databuild/strongs_greek.py`**

Use this schema:

```sql
CREATE TABLE IF NOT EXISTS entries (
    entry_id VARCHAR PRIMARY KEY,
    strongs_number VARCHAR NOT NULL,
    strongs_int INTEGER NOT NULL,
    lemma_unicode VARCHAR NOT NULL,
    lemma_beta VARCHAR,
    lemma_translit VARCHAR,
    pronunciation VARCHAR,
    derivation TEXT,
    definition TEXT,
    kjv_definition TEXT,
    display_gloss TEXT NOT NULL,
    entry_hash VARCHAR NOT NULL,
    source_path VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS aliases (
    alias_key VARCHAR NOT NULL,
    alias_display VARCHAR NOT NULL,
    alias_kind VARCHAR NOT NULL,
    entry_id VARCHAR NOT NULL,
    strongs_number VARCHAR NOT NULL,
    rank INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS strongs_greek_alias_key_idx ON aliases(alias_key, rank, entry_id);
CREATE INDEX IF NOT EXISTS strongs_greek_number_idx ON entries(strongs_number);
```

Public API:

```python
from dataclasses import dataclass
from pathlib import Path


DEFAULT_STRONGS_GREEK_XML_URL = (
    "https://raw.githubusercontent.com/morphgnt/strongs-dictionary-xml/master/strongsgreek.xml"
)


@dataclass(slots=True)
class StrongsGreekBuildConfig:
    source_path: Path
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 500
    wipe_existing: bool = True
    force_rebuild: bool = False


def normalize_strongs_greek_key(value: str) -> str:
    ...


def lookup_strongs_greek_entries_by_headword(
    headwords: list[str], db_path: Path | None = None
) -> list[dict[str, object]]:
    ...
```

`normalize_strongs_greek_key()` requirements:

- Use Unicode normalization.
- Strip Greek combining accents and breathings.
- Preserve Greek base letters.
- Convert final sigma to sigma for lookup.
- Remove punctuation and spacing.
- For iota subscript, keep the base vowel enough to match generated aliases; do not require exact iota-subscript matching.
- For Latin transliteration input, lowercase, strip accents, and remove punctuation.

Generated aliases for `Ἡσαΐας` should include:

- `Ἡσαΐας` exact lemma alias (`alias_kind="lemma"`, rank 0)
- transliteration aliases from XML (`Hēsaḯas`, `hesaias`, rank 2)
- Strong aliases (`2268`, `G2268`, `02268`, rank 0)
- proper-name forms for Greek `-ας` names (`Ἡσαΐου`, `Ἡσαΐᾳ`, `Ἡσαΐαν`) and normalized equivalents
- rough/smooth breathing-insensitive aliases so `Ἠσαίᾳ` can match `Ἡσαΐᾳ`

Build result should follow existing builder style enough for `_print_build_result()` to work.

- [ ] **Step 4: Add `databuild strongs-greek` CLI**

Modify `src/langnet/cli_databuild.py`:

```python
@databuild.command("strongs-greek")
@click.option("--source", "source_path", type=click.Path(exists=True), required=True)
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--limit", type=int, default=None)
@click.option("--batch-size", type=int, default=500, show_default=True)
@click.option("--wipe/--no-wipe", default=True, show_default=True)
@click.option("--force", is_flag=True)
def build_strongs_greek(...):
    """Build Strong's Greek biblical dictionary index from XML."""
```

Add `BuildStrongsGreekConfig` and `_build_strongs_greek_impl()` parallel to `BuildLewis1890Config`.

Add help coverage in `tests/test_cli_help.py`:

```python
def test_databuild_help_lists_strongs_greek() -> None:
    runner = CliRunner()
    result = runner.invoke(databuild, ["--help"])

    assert result.exit_code == 0
    assert "strongs-greek" in result.output
```

- [ ] **Step 5: Verify databuild**

Run:

```bash
just test test_strongs_greek_databuild test_cli_help -q
```

Expected: PASS.

## Task 2: Execution Handler

**Files:**

- Create: `src/langnet/execution/handlers/strongs_greek.py`
- Modify: `src/langnet/execution/registry.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_strongs_greek_provider_handler.py`

- [ ] **Step 1: Write failing handler tests**

Create `tests/test_strongs_greek_provider_handler.py`:

```python
from pathlib import Path

from query_spec import ToolCallSpec, ToolStage

from langnet.execution.handlers.strongs_greek import (
    StrongsGreekFetchClient,
    claim_strongs_greek_entries,
    derive_strongs_greek_entries,
    extract_strongs_greek_json,
    strongs_greek_entry_triples,
)
from tests.test_strongs_greek_databuild import STRONGS_XML
from langnet.databuild.strongs_greek import StrongsGreekBuildConfig, StrongsGreekBuilder


def _call(tool: str, call_id: str, source_call_id: str = "") -> ToolCallSpec:
    return ToolCallSpec(
        tool=tool,
        call_id=call_id,
        endpoint="test",
        params={"source_call_id": source_call_id} if source_call_id else {},
        stage=ToolStage.TOOL_STAGE_FETCH,
    )


def _db(tmp_path: Path) -> Path:
    source = tmp_path / "strongsgreek.xml"
    source.write_text(STRONGS_XML, encoding="utf-8")
    output = tmp_path / "lex_strongs_greek.duckdb"
    StrongsGreekBuilder(StrongsGreekBuildConfig(source_path=source, output_path=output)).build()
    return output


def test_strongs_greek_fetch_client_resolves_dative_isaiah(tmp_path: Path) -> None:
    client = StrongsGreekFetchClient(_db(tmp_path))
    raw = client.execute("strongs-fetch-1", "duckdb://strongs_greek", {"headword": "Ἠσαίᾳ"})

    assert raw.status_code == 200
    assert b"G2268" in raw.body
    assert b"generated_form" in raw.body


def test_strongs_greek_triples_emit_english_source_gloss() -> None:
    entry = {
        "entry_id": "strongs-greek:G2268",
        "strongs_number": "G2268",
        "lemma_unicode": "Ἡσαΐας",
        "lemma_translit": "Hēsaḯas",
        "definition": "Hesaias (i.e. Jeshajah), an Israelite",
        "kjv_definition": "Esaias.",
        "display_gloss": "Hesaias (i.e. Jeshajah), an Israelite; KJV: Esaias.",
        "entry_hash": "abc123",
    }

    triples = strongs_greek_entry_triples(entry)

    assert any(t["predicate"] == "has_sense" and t["subject"] == "lex:ησαιασ" for t in triples)
    gloss = next(t for t in triples if t["predicate"] == "gloss")
    assert gloss["metadata"]["source_lang"] == "en"
    assert gloss["metadata"]["source_entry"]["dict"] == "strongs_greek"
    assert gloss["metadata"]["source_entry"]["strongs_number"] == "G2268"
```

Run:

```bash
just test test_strongs_greek_provider_handler -q
```

Expected: FAIL because handler module does not exist.

- [ ] **Step 2: Implement handler**

Create `src/langnet/execution/handlers/strongs_greek.py` parallel to `lewis_1890.py`.

Required public API:

```python
class StrongsGreekFetchClient:
    tool = "fetch.strongs_greek"


def strongs_greek_entry_triples(entry: Mapping[str, object]) -> list[dict[str, object]]:
    ...


def extract_strongs_greek_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    ...


def derive_strongs_greek_entries(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    ...


def claim_strongs_greek_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    ...
```

Triple metadata requirements:

- `source_tool="strongs_greek"`
- `source_lang="en"`
- `source_ref="strongs_greek:G2268"`
- `raw_blob_ref="strongs_greek_xml"`
- `source_entry.dict="strongs_greek"`
- `source_entry.strongs_number="G2268"`
- `source_entry.lemma_unicode="Ἡσαΐας"`
- `source_entry.lemma_translit="Hēsaḯas"`
- `source_entry.source_text` is the compact combined derivation/definition/KJV gloss.

Lex anchor:

```python
lex_anchor = f"lex:{normalize_strongs_greek_key(lemma_unicode)}"
```

Sense anchor:

```python
sense_anchor = f"sense:{lex_anchor}#{sha256(source_ref + ':' + display_gloss)[:8]}"
```

- [ ] **Step 3: Wire registry and CLI fetch client**

Modify `src/langnet/execution/registry.py`:

```python
from langnet.execution.handlers import strongs_greek as strongs_greek_handlers

extract["extract.strongs_greek.json"] = strongs_greek_handlers.extract_strongs_greek_json
derive["derive.strongs_greek.entries"] = strongs_greek_handlers.derive_strongs_greek_entries
claim["claim.strongs_greek.entries"] = strongs_greek_handlers.claim_strongs_greek_entries
```

Modify `src/langnet/cli.py` near the other `_create_*_client()` helpers:

```python
def _create_strongs_greek_client(tool: str, use_stubs: bool) -> ToolClient:
    if use_stubs:
        return DummyToolClient(tool)
    from langnet.execution.handlers.strongs_greek import StrongsGreekFetchClient
    return StrongsGreekFetchClient()
```

Add to the client factory map:

```python
"fetch.strongs_greek": lambda: _create_strongs_greek_client(tool, use_stubs),
```

- [ ] **Step 4: Verify handler**

Run:

```bash
just test test_strongs_greek_provider_handler -q
```

Expected: PASS.

## Task 3: Planner and Tool Catalog

**Files:**

- Modify: `src/langnet/planner/local_lexicons.py`
- Modify: `src/langnet/planner/core.py`
- Modify: `src/langnet/tool_catalog.py`
- Test: `tests/test_planner_core.py`
- Test: `tests/test_tool_catalog.py`

- [ ] **Step 1: Write failing planner/catalog tests**

In `tests/test_planner_core.py`:

```python
def test_greek_plan_includes_strongs_greek_provider() -> None:
    plan = ToolPlanner(PlannerConfig(max_candidates=2)).build(_grc_normalized())
    tools = {call.tool for call in plan.tool_calls}

    assert "fetch.strongs_greek" in tools
    assert "extract.strongs_greek.json" in tools
    assert "derive.strongs_greek.entries" in tools
    assert "claim.strongs_greek.entries" in tools

    strongs_call = next(call for call in plan.tool_calls if call.tool == "fetch.strongs_greek")
    assert strongs_call.params.get("headword") == "logos"
    assert strongs_call.params.get("lemma") == "λόγος"
    assert strongs_call.params.get("lemma_candidates") == "λόγος"
```

In `tests/test_tool_catalog.py`:

```python
def test_catalog_lists_greek_strongs_greek_filter() -> None:
    filters = {entry.tool_filter for entry in catalog_entries("grc")}

    assert "strongs_greek" in filters
```

```python
def test_tools_json_output_lists_greek_strongs_greek() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["tools", "grc", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    strongs = next(tool for tool in payload["tools"] if tool["tool_filter"] == "strongs_greek")
    assert strongs["accepted_filter"] == "strongs_greek"
    assert strongs["translation_capable"] is False
    assert "claim.strongs_greek.entries" in strongs["plan_tools"]
```

Run:

```bash
just test test_planner_core test_tool_catalog -q
```

Expected: FAIL because planner/catalog do not expose `strongs_greek`.

- [ ] **Step 2: Add planner helper**

Modify `src/langnet/planner/local_lexicons.py`:

```python
def append_strongs_greek_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
    lemma_candidates: list[str] | None = None,
) -> None:
    fetch_id = "strongs-greek-1"
    params = {"headword": headword, "lemma": lemma}
    if lemma_candidates:
        params["lemma_candidates"] = ";".join(lemma_candidates)
    # fetch.strongs_greek -> extract.strongs_greek.json
    # -> derive.strongs_greek.entries -> claim.strongs_greek.entries
```

Use priorities near Bailly, but after LSJ/Bailly in UI display if ranking ties. Suggested fetch priority: `7`, extract `8`, derive `9`, claim `10`.

- [ ] **Step 3: Add planner config and Greek calls**

Modify `src/langnet/planner/core.py`:

```python
from langnet.planner.local_lexicons import append_strongs_greek_calls
```

Add `include_strongs_greek: bool = True` to `PlannerConfig`.

In `_build_greek_calls()`, after Bailly calls:

```python
if self.config.include_strongs_greek:
    lemma_candidates = [candidate.lemma for candidate in normalized.candidates if candidate.lemma]
    append_strongs_greek_calls(
        calls,
        deps,
        headword=(normalized.original or candidate.lemma).lower(),
        lemma=candidate.lemma,
        lemma_candidates=lemma_candidates,
    )
```

- [ ] **Step 4: Add catalog entry**

Modify `src/langnet/tool_catalog.py`:

```python
ToolCatalogEntry(
    language="grc",
    tool_filter="strongs_greek",
    label="Strong's Greek",
    role="biblical/religious Greek dictionary entries",
    source_tools=("strongs_greek",),
    plan_tools=(
        "fetch.strongs_greek",
        "extract.strongs_greek.json",
        "derive.strongs_greek.entries",
        "claim.strongs_greek.entries",
    ),
    translation_capable=False,
    notes="English biblical Greek dictionary; useful for proper names and New Testament/Septuagint vocabulary.",
)
```

- [ ] **Step 5: Verify planner/catalog**

Run:

```bash
just test test_planner_core test_tool_catalog -q
```

Expected: PASS.

## Task 4: Encounter Integration and `Ἠσαίᾳ` Regression

**Files:**

- Modify: `src/langnet/cli.py`
- Test: `tests/test_encounter_strongs_greek.py`
- Test: `tests/test_greek_anchor_normalization.py`

- [ ] **Step 1: Write failing encounter regression**

Create `tests/test_encounter_strongs_greek.py` with focused unit coverage around claims/reduction rather than a full live CLI integration:

```python
from langnet.reduction import reduce_claims
from langnet.execution.handlers.strongs_greek import strongs_greek_entry_triples


def test_encounter_reduction_can_use_strongs_greek_for_isaiah() -> None:
    entry = {
        "entry_id": "strongs-greek:G2268",
        "strongs_number": "G2268",
        "lemma_unicode": "Ἡσαΐας",
        "lemma_translit": "Hēsaḯas",
        "definition": "Hesaias (i.e. Jeshajah), an Israelite",
        "kjv_definition": "Esaias.",
        "display_gloss": "Hesaias (i.e. Jeshajah), an Israelite; KJV: Esaias.",
        "entry_hash": "abc123",
    }
    claims = [
        {
            "claim_id": "strongs-test",
            "tool": "claim.strongs_greek.entries",
            "subject": "lex:ησαιασ",
            "predicate": "has_lemmas",
            "value": {"triples": strongs_greek_entry_triples(entry)},
            "provenance_chain": [],
        }
    ]

    result = reduce_claims(query="Ἠσαίᾳ", language="grc", claims=claims)

    assert result.buckets
    assert result.buckets[0].display_gloss.startswith("Hesaias")
    assert result.buckets[0].witnesses[0].source_tool == "strongs_greek"
```

Run:

```bash
just test test_encounter_strongs_greek -q
```

Expected: FAIL until handler triples are shaped correctly and recognized by reduction.

- [ ] **Step 2: Keep LSJ no-match safety intact**

The previous `Ἠσαίᾳ` fix must remain true:

```bash
just test test_greek_anchor_normalization -q
```

Expected: PASS. Strong's must add evidence through `strongs_greek`, not by accepting Diogenes fuzzy fallback entries.

- [ ] **Step 3: Verify filter behavior**

After planner/filter plumbing, these commands should work once a test DB or real DB exists:

```bash
just cli tools grc --output json
just cli plan grc 'Ἠσαίᾳ' strongs_greek --output json
just cli encounter grc 'Ἠσαίᾳ' strongs_greek --output json
just cli encounter grc 'Ἠσαίᾳ' all --output json
```

Expected:

- `tools grc` lists `strongs_greek`.
- `encounter ... strongs_greek` has one source-backed bucket for G2268.
- `encounter ... all` includes Strong's evidence and does not include unrelated `ἥσθημα` evidence.

Do not add alternate provider aliases in the first slice. Prefer the single canonical filter `strongs_greek`.

## Task 5: Web UI Tool Exposure

**Files:**

- Modify: `webapp/src/lib/search-data.ts`
- Modify: `webapp/src/lib/source-outline.ts` only if source-specific outline behavior is needed
- Test: `webapp/src/lib/search-data.test.ts`

- [ ] **Step 1: Write failing web tool test**

Modify `webapp/src/lib/search-data.test.ts`:

```ts
const greekTools = toolsForLanguage('grc').map(({ id }) => id);
assert.ok(greekTools.includes('strongs_greek'));
assert.deepEqual(resolveToolRequests('grc', ['strongs_greek']), ['strongs_greek']);
assert.ok(encounterWord('', 'grc', ['all']).source_tools.includes('strongs_greek'));
```

Run:

```bash
cd webapp
bun src/lib/search-data.test.ts
```

Expected: FAIL because `ToolId` does not include `strongs_greek`.

- [ ] **Step 2: Add web tool metadata**

Modify `webapp/src/lib/search-data.ts`:

```ts
export type ToolId =
    | 'cdsl'
    | ...
    | 'strongs_greek';
```

Add a `tools` entry:

```ts
{
    id: 'strongs_greek',
    language: 'grc',
    label: "Strong's Greek",
    shortLabel: "Strong's",
    kind: 'dictionary',
    description: 'Biblical and religious Greek dictionary entries, useful for proper names.'
}
```

- [ ] **Step 3: Verify web metadata**

Run:

```bash
cd webapp
bun src/lib/search-data.test.ts
bun run check
```

Expected: PASS with zero Svelte diagnostics.

## Task 6: Documentation and Source Policy

**Files:**

- Modify: `docs/GETTING_STARTED.md` or `docs/OUTPUT_GUIDE.md`
- Modify: `docs/READER_METADATA_ENRICHMENT_LOOP.md` if provider affects enrichment examples
- Modify: `data/README.md` if generated DB/source expectations belong there

- [ ] **Step 1: Document provider boundary**

Add a short section:

```markdown
### Strong's Greek

`strongs_greek` is a Greek-English biblical dictionary provider built from
Strong's Greek XML. It is useful for biblical names and New Testament /
Septuagint vocabulary that classical Greek dictionaries may miss. It is not a
replacement for LSJ or Bailly; it should be treated as religious/biblical
lexical evidence.
```

- [ ] **Step 2: Document source acquisition**

Record that source XML is external and should be downloaded deliberately:

```bash
curl -L \
  https://raw.githubusercontent.com/morphgnt/strongs-dictionary-xml/master/strongsgreek.xml \
  -o examples/debug/strongsgreek.xml

just cli-databuild strongs-greek \
  --source examples/debug/strongsgreek.xml \
  --output data/build/lex_strongs_greek.duckdb \
  --wipe
```

- [ ] **Step 3: Verify docs are consistent**

Run:

```bash
rg -n "strongs_greek|Strong's Greek|strongs-greek" docs data src webapp tests
```

Expected: entries appear in plan, docs, source code, tests, and web metadata.

## Task 7: End-to-End Verification

**Files:** no new files unless test fixtures require adjustment.

- [ ] **Step 1: Build fixture or real DB**

For local verification with real source:

```bash
curl -L \
  https://raw.githubusercontent.com/morphgnt/strongs-dictionary-xml/master/strongsgreek.xml \
  -o examples/debug/strongsgreek.xml

just cli-databuild strongs-greek \
  --source examples/debug/strongsgreek.xml \
  --output data/build/lex_strongs_greek.duckdb \
  --wipe
```

Expected: build result prints success and a positive entry count.

- [ ] **Step 2: Verify exact target**

Run:

```bash
just cli encounter grc 'Ἠσαίᾳ' strongs_greek --output json
```

Expected:

- `lexeme_anchors` contains a Strong's-derived Isaiah lexeme anchor.
- At least one bucket has `source_tools=["strongs_greek"]` or includes `strongs_greek`.
- Display gloss contains `Hesaias`, `Jeshajah`, `Israelite`, or `Esaias`.
- No bucket references `ἥσθημα`.

- [ ] **Step 3: Verify `all` target**

Run:

```bash
just cli encounter grc 'Ἠσαίᾳ' all --output json
```

Expected:

- Strong's bucket appears.
- Diogenes no-match/fuzzy result does not produce a false `ἥσθημα` bucket.
- Encounter briefing has a source-backed compact meaning and can offer model generation.

- [ ] **Step 4: Verify broad checks**

Run:

```bash
just ruff-format src/langnet/databuild/strongs_greek.py src/langnet/execution/handlers/strongs_greek.py tests/
just test test_strongs_greek_databuild test_strongs_greek_provider_handler test_encounter_strongs_greek test_planner_core test_tool_catalog test_greek_anchor_normalization -q
cd webapp && bun run format:check && bun run test && bun run check
```

Expected: all pass.

## Follow-Up Options

1. Add MorphGNT/SBLGNT token morphology as a separate provider or alias source. This can improve NT inflected forms, but it does not solve Septuagint-only forms by itself.
2. Add a Septuagint proper-name alias table from reader corpus occurrences after the reader search index can export token-to-work contexts.
3. Add `strongs_hebrew` later for Hebrew Bible names and cross-language source metadata, but keep it separate from Greek provider work.
4. Add source-backed reader search concepts for biblical proper names so clicking Isaiah can also suggest reader passages in `tlg0527` and related patristic commentary.

## Self-Review

- Spec coverage: plan covers source acquisition, databuild, provider handler, planner/catalog, encounter regression, web UI exposure, docs, and verification.
- Placeholder scan: no `TBD` or vague implementation-only steps remain.
- Type consistency: provider/filter/tool names use canonical `strongs_greek`; databuild command uses `strongs-greek`; default DB path is `lex_strongs_greek.duckdb`.
- Scope check: MorphGNT/SBLGNT and Hebrew Strong's are listed as follow-ups, not bundled into the first provider slice.
