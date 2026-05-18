# Lewis 1890 Latin Provider Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CLTK's Charlton T. Lewis 1890 *Elementary Latin Dictionary* a first-class Latin dictionary backend/provider with local DuckDB lookup, staged execution claims, encounter/tool-filter support, and English learner-facing glosses.

**Architecture:** `lewis_1890` should follow the local lexicon pattern used by Gaffiot and Bailly, but it is Latin-English, so it does not need translation-cache projection. `databuild lewis-1890` imports the CLTK source into `data/build/lex_lewis_1890.duckdb`; `fetch.lewis_1890` reads that database; `extract.lewis_1890.json`, `derive.lewis_1890.entries`, and `claim.lewis_1890.entries` project source entries into evidence-bearing triples.

**Tech Stack:** Python, Click, CLTK data files, DuckDB, PyArrow, `query_spec` staged tool plans, `RawResponseEffect`, `ExtractionEffect`, `DerivationEffect`, `ClaimEffect`, `nose2`, `just`.

---

## Scope and Boundaries

This provider should be distinct from the existing `cltk` provider:

- `cltk` remains supplemental IPA/CLTK enrichment and stays disabled by default unless `--include-cltk` is used.
- `lewis_1890` becomes a Latin dictionary provider/filter.
- `lewis_1890` participates in Latin `all` plans as an optional local dictionary provider.
- `lewis_1890` works through `plan`, `plan-exec`, `encounter`, and `triples-dump`.
- `lewis_1890` emits English source glosses directly with `source_lang="en"`.
- `lewis_1890` does not use French-to-English translation cache projection.

The provider name should be:

- Tool filter: `lewis_1890`
- User label: `Lewis 1890`
- Databuild command: `lewis-1890`
- Default DB path: `data/build/lex_lewis_1890.duckdb`
- Source default: `~/cltk_data/lat/lexicon/cltk_lat_lewis_elementary_lexicon/lewis.yaml`

## Existing Source of Truth

- CLTK source root: `/home/nixos/cltk_data/lat/lexicon/cltk_lat_lewis_elementary_lexicon`
- Source files:
  - `lewis.yaml`: key-to-plain-entry mapping
  - `lewis.xml`: TEI source, useful for later richer structure
  - `README.md`: bibliographic metadata, publication year 1890
- Existing local provider patterns:
  - `src/langnet/databuild/bailly.py`
  - `src/langnet/databuild/gaffiot.py`
  - `src/langnet/execution/handlers/bailly.py`
  - `src/langnet/execution/handlers/gaffiot.py`
  - `src/langnet/planner/local_lexicons.py`
  - `src/langnet/execution/registry.py`
  - `src/langnet/tool_catalog.py`

## Task 1: Databuild and Lookup

**Files:**
- Create: `src/langnet/databuild/lewis_1890.py`
- Modify: `src/langnet/databuild/paths.py`
- Modify: `src/langnet/cli_databuild.py`
- Test: `tests/test_lewis_1890_structured_db.py`
- Test: `tests/test_cli_help.py`

- [ ] **Step 1: Write failing database tests**

Add tests that build a temporary Lewis YAML fixture:

```python
def test_lewis_1890_build_imports_yaml_entries(tmp_path: Path) -> None:
    source = tmp_path / "lewis.yaml"
    source.write_text(
        'lupus: "lupus ī, m a wolf: lupa, V.; lupus in fabula."\n'
        'amo: "amō āvī ātus āre, to love, like."\n',
        encoding="utf-8",
    )
    output = tmp_path / "lex_lewis_1890.duckdb"

    result = Lewis1890Builder(
        Lewis1890BuildConfig(source_path=source, output_path=output)
    ).build()

    assert result.status == BuildStatus.SUCCESS
    assert lookup_lewis_1890_entries("lupus", output)[0]["headword_norm"] == "lupus"
```

Add a lookup candidate test:

```python
def test_lewis_1890_lookup_uses_ordered_candidates(tmp_path: Path) -> None:
    # Build entries for lupus and amo.
    # Call lookup_lewis_1890_entries_by_headword(["lupi", "lupus"], output).
    # Assert the lupus entry is returned.
```

Run:

```bash
just test test_lewis_1890_structured_db
```

Expected: FAIL because `langnet.databuild.lewis_1890` does not exist.

- [ ] **Step 2: Add the default path**

In `src/langnet/databuild/paths.py`, add:

```python
def default_lewis_1890_path() -> Path:
    return _build_root() / "lex_lewis_1890.duckdb"
```

Keep naming parallel to `default_bailly_path()` and `default_gaffiot_path()`.

- [ ] **Step 3: Implement `src/langnet/databuild/lewis_1890.py`**

Use this schema:

```sql
CREATE TABLE IF NOT EXISTS entries (
    entry_id VARCHAR PRIMARY KEY,
    headword_raw VARCHAR NOT NULL,
    headword_norm VARCHAR NOT NULL,
    source_key VARCHAR NOT NULL,
    plain_text TEXT NOT NULL,
    entry_hash VARCHAR NOT NULL,
    source_path VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS lewis_1890_headword_norm_idx ON entries(headword_norm);
CREATE INDEX IF NOT EXISTS lewis_1890_headword_entry_idx ON entries(headword_norm, entry_id);
```

Required public API:

```python
LEX_ID = "LEWIS_1890_EN_LAT"
DEFAULT_SOURCE = (
    Path.home()
    / "cltk_data"
    / "lat"
    / "lexicon"
    / "cltk_lat_lewis_elementary_lexicon"
    / "lewis.yaml"
)

@dataclass
class Lewis1890BuildConfig:
    source_path: Path | None = None
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 500
    wipe_existing: bool = True
    force_rebuild: bool = False
```

Normalize headwords with the Latin normalization style used by Gaffiot:

```python
def normalize_lewis_1890_headword(raw: str) -> str:
    stripped = (raw or "").strip()
    if "," in stripped:
        stripped = stripped.split(",", 1)[0]
    stripped = stripped.lstrip("0123456789. ").strip()
    expanded = (
        stripped.replace("æ", "ae")
        .replace("Æ", "ae")
        .replace("œ", "oe")
        .replace("Œ", "oe")
    )
    return strip_accents(expanded.lower())
```

Use `yaml.safe_load()` if available from the CLTK dependency set. If `yaml` cannot be imported, raise a `RuntimeError` that tells the caller `PyYAML is required to read CLTK Lewis 1890 YAML source`.

For each YAML item:

- `source_key`: YAML key, e.g. `lupus`
- `headword_raw`: first token from the entry text if present, else the key
- `headword_norm`: normalized source key first, falling back to normalized raw headword
- `entry_id`: `lewis-1890:{source_key}`
- `plain_text`: YAML value as a stripped string
- `entry_hash`: SHA-256 of `source_key + "\0" + plain_text`

Add lookup functions:

```python
def lookup_lewis_1890_entries(headword: str, db_path: Path | None = None) -> list[dict]:
    return lookup_lewis_1890_entries_by_headword([headword], db_path)

def lookup_lewis_1890_entries_by_headword(
    headwords: list[str], db_path: Path | None = None
) -> list[dict]:
    ...
```

Return dictionaries with `entry_id`, `headword_raw`, `headword_norm`, `source_key`, `plain_text`, and `entry_hash`.

- [ ] **Step 4: Add `databuild lewis-1890` CLI**

In `src/langnet/cli_databuild.py`, add `BuildLewis1890Config`, `_build_lewis_1890_impl()`, and a Click command:

```python
@databuild.command("lewis-1890")
@click.option("--source", "source_path", type=click.Path(), default=None)
@click.option("--output", "-o", type=click.Path())
@click.option("--limit", type=int)
@click.option("--batch-size", type=int, default=500, show_default=True)
@click.option("--wipe/--no-wipe", default=True, show_default=True)
@click.option("--force", is_flag=True)
def build_lewis_1890(...):
    """Build Lewis 1890 Latin-English index from CLTK source."""
```

Add help coverage in `tests/test_cli_help.py` asserting `lewis-1890` appears under `databuild --help`.

- [ ] **Step 5: Verify databuild**

Run:

```bash
just test test_lewis_1890_structured_db test_cli_help
just cli-databuild lewis-1890 --source /home/nixos/cltk_data/lat/lexicon/cltk_lat_lewis_elementary_lexicon/lewis.yaml --output examples/debug/lex_lewis_1890.duckdb --wipe
```

Expected: tests PASS; databuild reports `LEWIS_1890_EN_LAT` and roughly 17,582 entries.

## Task 2: Execution Handler

**Files:**
- Create: `src/langnet/execution/handlers/lewis_1890.py`
- Modify: `src/langnet/execution/registry.py`
- Test: `tests/test_lewis_1890_provider_handler.py`

- [ ] **Step 1: Write failing provider tests**

Add tests parallel to Bailly/Gaffiot:

```python
def test_lewis_1890_fetch_client_returns_local_entries(tmp_path: Path) -> None:
    # Build a temp Lewis DB containing lupus.
    # Execute Lewis1890FetchClient with headword="lupus".
    # Assert JSON body contains one entry with source_key="lupus".
```

```python
def test_claim_lewis_1890_entries_emits_english_gloss_triples(tmp_path: Path) -> None:
    # Pass fetch output through extract_lewis_1890_json,
    # derive_lewis_1890_entries, and claim_lewis_1890_entries.
    # Assert value["triples"] contains source_tool="lewis_1890",
    # source_lang="en", and a gloss object containing "wolf".
```

Run:

```bash
just test test_lewis_1890_provider_handler
```

Expected: FAIL because the handler does not exist.

- [ ] **Step 2: Implement fetch/extract/derive/claim**

Required handler API:

```python
class Lewis1890FetchClient:
    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.lewis_1890"
        self.db_path = db_path
```

Candidate order:

- `headword`
- `lemma`
- `q`
- semicolon-split `lemma_candidates`

Required staged functions:

```python
def lewis_1890_entry_triples(entry: Mapping[str, object]) -> list[dict[str, object]]
def extract_lewis_1890_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect
def derive_lewis_1890_entries(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect
def claim_lewis_1890_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect
```

Use stable prefixes:

- `lewis-1890-ext`
- `lewis-1890-der`
- `lewis-1890-clm`

Use `kind="lewis_1890.entries"`.

Evidence shape:

```python
evidence = {
    "source_tool": "lewis_1890",
    "source_ref": f"lewis_1890:{source_key}",
    "raw_blob_ref": "cltk_lewis_yaml",
    "entry_hash": entry.get("entry_hash"),
}
```

Gloss metadata:

```python
{
    "source_lang": "en",
    "source_ref": source_ref,
    "display_gloss": display_text(gloss),
    "learner_gloss": compact_source_gloss(gloss),
    "learner_segments": learner_segments_from_text(gloss),
    "source_entry": {
        "dict": "lewis_1890",
        "source_ref": source_ref,
        "entry_id": entry_id,
        "headword_raw": entry.get("headword_raw"),
        "headword_norm": headword,
        "source_key": entry.get("source_key"),
        "source_text": gloss,
    },
    "source_segments": source_segments_from_text(
        gloss,
        segment_type="definition_segment",
        labels=["definition"],
    ),
}
```

- [ ] **Step 3: Register staged handlers**

In `src/langnet/execution/registry.py`, register:

```python
extract["extract.lewis_1890.json"] = lewis_1890_handlers.extract_lewis_1890_json
derive["derive.lewis_1890.entries"] = lewis_1890_handlers.derive_lewis_1890_entries
claim["claim.lewis_1890.entries"] = lewis_1890_handlers.claim_lewis_1890_entries
```

- [ ] **Step 4: Verify handler**

Run:

```bash
just test test_lewis_1890_provider_handler
just ruff-check
```

Expected: PASS.

## Task 3: Planner, CLI Execution Client, and Tool Catalog

**Files:**
- Modify: `src/langnet/planner/local_lexicons.py`
- Modify: `src/langnet/planner/core.py`
- Modify: `src/langnet/cli.py`
- Modify: `src/langnet/tool_catalog.py`
- Test: `tests/test_planner_core.py`
- Test: `tests/test_lewis_1890_plan_exec.py`
- Test: `tests/test_tool_catalog.py`

- [ ] **Step 1: Add planner tests**

In `tests/test_planner_core.py`, add:

```python
def test_latin_plan_includes_lewis_1890_dictionary_provider() -> None:
    plan = ToolPlanner(PlannerConfig(max_candidates=2)).build(_lat_normalized())
    tools = {call.tool for call in plan.tool_calls}

    assert "fetch.lewis_1890" in tools
    assert "extract.lewis_1890.json" in tools
    assert "derive.lewis_1890.entries" in tools
    assert "claim.lewis_1890.entries" in tools
```

Expected initial failure: Lewis 1890 calls are absent.

- [ ] **Step 2: Add local lexicon planner helper**

In `src/langnet/planner/local_lexicons.py`, add:

```python
def append_lewis_1890_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
    lemma_candidates: list[str],
) -> None:
    ...
```

Use call IDs:

- `lewis-1890-1`
- `lewis-1890-extract-1`
- `lewis-1890-derive-1`
- `claim-lewis-1890-1`

Use tools:

- `fetch.lewis_1890`
- `extract.lewis_1890.json`
- `derive.lewis_1890.entries`
- `claim.lewis_1890.entries`

Use endpoint `duckdb://lewis_1890` for fetch and internal endpoints for later stages.

- [ ] **Step 3: Wire Latin planner config**

In `src/langnet/planner/core.py`:

- Import `append_lewis_1890_calls`.
- Add `include_lewis_1890: bool = True` to `PlannerConfig`.
- In `_build_latin_calls()`, append Lewis 1890 after Whitaker/CLTK and before or near Gaffiot:

```python
if self.config.include_lewis_1890:
    append_lewis_1890_calls(
        calls,
        deps,
        headword=query_value,
        lemma=candidate.lemma.lower(),
        lemma_candidates=[
            cand.lemma.lower()
            for cand in normalized.candidates
            if cand.lemma and cand.lemma.lower()
        ],
    )
```

- [ ] **Step 4: Add CLI execution client**

In `src/langnet/cli.py`, add a factory parallel to `_create_bailly_client()`:

```python
def _create_lewis_1890_client(tool: str, use_stubs: bool):
    if use_stubs:
        return _make_stub_client(tool)
    from langnet.execution.handlers.lewis_1890 import Lewis1890FetchClient

    return Lewis1890FetchClient()
```

Register it in `_get_client_factory()` for `"fetch.lewis_1890"`.

Add `tests/test_lewis_1890_plan_exec.py` that builds a temp DB, patches `default_lewis_1890_path()`, calls `_build_exec_clients()`, and verifies the returned fetch client can resolve `lupus`.

- [ ] **Step 5: Add tool catalog entry**

In `src/langnet/tool_catalog.py`, add a Latin entry:

```python
ToolCatalogEntry(
    language="lat",
    tool_filter="lewis_1890",
    label="Lewis 1890",
    role="Latin-English dictionary entries",
    source_tools=("lewis_1890",),
    plan_tools=(
        "fetch.lewis_1890",
        "extract.lewis_1890.json",
        "derive.lewis_1890.entries",
        "claim.lewis_1890.entries",
    ),
    translation_capable=False,
    notes="CLTK source for Charlton T. Lewis, An Elementary Latin Dictionary (1890).",
)
```

Update catalog tests to assert:

- `tools lat --output json` lists `accepted_filter="lewis_1890"`.
- `translation_capable` is false.
- `lewis_1890` is accepted by tool filtering.

- [ ] **Step 6: Verify planner/catalog/CLI client**

Run:

```bash
just test test_planner_core test_lewis_1890_plan_exec test_tool_catalog
just ruff-check
```

Expected: PASS.

## Task 4: Encounter and Triples Contracts

**Files:**
- Test: `tests/test_lewis_1890_triples.py`
- Test: existing encounter/triples tests as needed

- [ ] **Step 1: Add direct triples contract tests**

Add:

```python
def test_lewis_1890_entry_triples_include_english_source_metadata() -> None:
    triples = lewis_1890_entry_triples(
        {
            "entry_id": "lewis-1890:lupus",
            "headword_raw": "lupus",
            "headword_norm": "lupus",
            "source_key": "lupus",
            "plain_text": "lupus ī, m a wolf: lupa, V.",
            "entry_hash": "abc123",
        }
    )

    gloss = next(t for t in triples if t["predicate"] == "gloss")
    metadata = gloss["metadata"]

    assert metadata["source_lang"] == "en"
    assert metadata["evidence"]["source_tool"] == "lewis_1890"
    assert metadata["source_entry"]["dict"] == "lewis_1890"
    assert "wolf" in metadata["display_gloss"]
```

- [ ] **Step 2: Add filter contract test**

Build a Latin plan and apply CLI plan filtering:

```python
def test_tool_filter_lewis_1890_keeps_only_lewis_plan_calls_and_dependencies() -> None:
    plan = ToolPlanner(PlannerConfig(max_candidates=2)).build(_lat_normalized())
    filtered = _filter_plan_tools(plan, "lewis_1890")
    assert {call.tool for call in filtered.tool_calls} == {
        "fetch.lewis_1890",
        "extract.lewis_1890.json",
        "derive.lewis_1890.entries",
        "claim.lewis_1890.entries",
    }
```

- [ ] **Step 3: Verify triples/filter tests**

Run:

```bash
just test test_lewis_1890_triples test_cli_triples_json test_lewis_1890_provider_handler
just ruff-check
```

Expected: PASS.

## Task 5: Word-Index and Wheel Integration

**Files:**
- Modify: `src/langnet/word_index/service.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_word_index.py`
- Test: `tests/test_word_index_sections.py`

- [ ] **Step 1: Add failing word-index source tests**

Extend `WordIndexPaths` fixtures with:

- `bailly: Path`
- `lewis_1890: Path`

Add fixture writers:

```python
def _write_bailly_fixture(path: Path) -> None:
    # entries(entry_id, lemma, lemma_norm, source_kind, source_path,
    # page_start, page_end, raw_text, block_count, updated_at)
    # include agelaios, logos, nomos
```

```python
def _write_lewis_1890_fixture(path: Path) -> None:
    # entries(entry_id, headword_raw, headword_norm, source_key,
    # plain_text, entry_hash, source_path, updated_at)
    # include amo, lupus, nox
```

Update `test_word_index_sources_report_local_statuses()` to expect:

```python
("grc", "bailly", "bailly")
("lat", "lewis_1890", "lewis_1890")
```

Add source-specific tests:

```python
def test_word_index_list_reads_lewis_1890_source() -> None:
    payload = word_index_list_payload("lat", source="lewis_1890", prefix="lu", ...)
    assert payload["items"][0]["source"] == "lewis_1890"
    assert payload["items"][0]["canonical_key"] == "lupus"
```

```python
def test_word_index_neighborhood_reads_bailly_source() -> None:
    payload = word_index_neighborhood_payload("grc", "logos", source="bailly", ...)
    assert payload["neighborhood"]["anchor"]["source"] == "bailly"
```

```python
def test_word_index_wheel_includes_lewis_1890_and_bailly_sources() -> None:
    lat_payload = word_index_wheel_payload("lat", source="all", ...)
    grc_payload = word_index_wheel_payload("grc", source="all", ...)
    assert "lewis_1890" in {item["source"] for item in lat_payload["items"]}
    assert "bailly" in {item["source"] for item in grc_payload["items"]}
```

Run:

```bash
just test test_word_index test_word_index_sections
```

Expected: FAIL because `WordIndexPaths`, `_sources_for_request()`, and source adapters do not know about Bailly/Lewis 1890.

- [ ] **Step 2: Extend word-index path/source registry**

In `src/langnet/word_index/service.py`:

- Import `default_bailly_path`, `default_lewis_1890_path`, `lookup_lewis_1890` normalizer, and `normalize_bailly_headword`.
- Extend `WordIndexSource` to include `"bailly"` and `"lewis_1890"`.
- Add `_SOURCE_ORDER` positions so order remains stable:

```python
_SOURCE_ORDER = {
    "cdsl": 0,
    "dico": 1,
    "gaffiot": 2,
    "lewis_1890": 3,
    "whitakers": 4,
    "diogenes": 5,
    "bailly": 6,
}
```

- Extend `WordIndexPaths` with `bailly` and `lewis_1890` default paths.
- Update `_sources_for_request("all", ...)` so Latin includes `gaffiot`, `lewis_1890`, `whitakers`, `diogenes`, and Greek includes `diogenes`, `bailly`.
- Add source statuses for Bailly and Lewis 1890.

- [ ] **Step 3: Add Lewis 1890 list/neighborhood/wheel adapters**

Implement:

```python
def _list_lewis_1890(path: Path, *, prefix: str, limit: int, warnings: list[dict[str, str]]) -> list[dict[str, object]]
def _neighborhood_lewis_1890(path: Path, *, query: str, radius: int, warnings: list[dict[str, str]]) -> list[dict[str, object]]
def _wheel_lewis_1890(path: Path, *, seed: str, limit: int, warnings: list[dict[str, str]]) -> list[dict[str, object]]
def _lewis_1890_item(row: Sequence[object]) -> dict[str, object]
```

Use table `entries` with columns `entry_id`, `headword_raw`, `headword_norm`, `source_key`, `entry_hash`.

Set item fields:

- `language="lat"`
- `source="lewis_1890"`
- `dictionary="lewis_1890"`
- `source_ref=f"lewis_1890:{source_key}"`
- `lookup=headword_norm`
- `canonical_key=_plain_index_key(headword_norm)`

- [ ] **Step 4: Add Bailly list/neighborhood/wheel adapters**

Implement:

```python
def _list_bailly(path: Path, *, prefix: str, limit: int, warnings: list[dict[str, str]]) -> list[dict[str, object]]
def _neighborhood_bailly(path: Path, *, query: str, radius: int, warnings: list[dict[str, str]]) -> list[dict[str, object]]
def _wheel_bailly(path: Path, *, seed: str, limit: int, warnings: list[dict[str, str]]) -> list[dict[str, object]]
def _bailly_item(row: Sequence[object]) -> dict[str, object]
```

Use table `entries` with columns `entry_id`, `lemma`, `lemma_norm`, `page_start`, `page_end`.

Set item fields:

- `language="grc"`
- `source="bailly"`
- `dictionary="bailly"`
- `source_ref=f"bailly:{entry_id}"`
- `lookup=lemma_norm`
- `canonical_name=lemma`
- `canonical_key=_plain_index_key(lemma_norm)`

- [ ] **Step 5: Wire encounter word-index source mapping**

In `src/langnet/cli.py`, update `WORD_INDEX_SOURCES`:

```python
WORD_INDEX_SOURCES = {
    "all",
    "cdsl",
    "dico",
    "gaffiot",
    "lewis_1890",
    "whitakers",
    "diogenes",
    "bailly",
}
```

This lets `encounter lat lupus lewis_1890` and `encounter grc agelaios bailly` request matching word-index context rather than falling back to `all`.

- [ ] **Step 6: Verify word-index/wheel integration**

Run:

```bash
just test test_word_index test_word_index_sections test_cli_encounter_output
just cli word-index sources all --output json
just cli word-index list lat --source lewis_1890 --prefix lu --limit 5 --output json
just cli word-index nearby grc agelaios --source bailly --radius 1 --output json
just cli word-index wheel all --source all --count 8 --seed lewis-bailly-smoke --output json
```

Expected: source statuses include Bailly and Lewis 1890 when DBs exist; list/neighborhood/wheel payloads include source-backed entries.

## Task 6: End-to-End Verification

**Files:**
- No new production files unless verification finds a bug.
- Update this plan's checkboxes as tasks complete.

- [ ] **Step 1: Build the default Lewis 1890 DB**

Run:

```bash
just cli-databuild lewis-1890 --source /home/nixos/cltk_data/lat/lexicon/cltk_lat_lewis_elementary_lexicon/lewis.yaml --output data/build/lex_lewis_1890.duckdb --wipe
```

Expected:

- status success
- lex_id `LEWIS_1890_EN_LAT`
- entry count around 17,582

- [ ] **Step 2: Add or use a lookup smoke command**

If a dedicated lookup command is useful, add `lewis-1890-db-lookup` to `src/langnet/cli.py` parallel to `bailly-db-lookup`. Otherwise verify through provider execution only.

Smoke words:

```bash
just cli encounter lat lupus lewis_1890 --no-normalize --output json
just triples-dump lat lupus lewis_1890
just cli-plan lat lupus --no-cache --output json
```

Expected:

- plan includes the four Lewis 1890 staged calls
- encounter includes a `lewis_1890` source bucket
- triples include English gloss/source metadata

- [ ] **Step 3: Run focused and full gates**

Run:

```bash
just test test_lewis_1890_structured_db test_lewis_1890_provider_handler test_lewis_1890_plan_exec test_tool_catalog test_planner_core test_lewis_1890_triples test_cli_help
just ruff-check
just test-fast
```

Expected:

- focused tests PASS
- ruff PASS
- fast suite PASS

`just typecheck` is a known project-wide non-clean gate due existing reader/storage diagnostics. If run, report whether Lewis 1890 adds diagnostics separately from existing failures.

## Review Checkpoints

Ask `@architect` after Task 1:

```markdown
@architect "Review the Lewis 1890 databuild schema and provider boundary. Does this correctly separate CLTK IPA enrichment from first-class dictionary evidence?"
```

Ask `@auditor` after Task 4:

```markdown
@auditor "Review the Lewis 1890 provider integration for regressions in Latin plans, tool filtering, evidence metadata, and encounter/triples contracts."
```

## Completion Criteria

The work is complete when:

- `databuild lewis-1890` imports the CLTK source reliably into DuckDB.
- `Lewis1890FetchClient` can fetch local entries without CLTK runtime initialization.
- Latin plans include `fetch/extract/derive/claim.lewis_1890` calls.
- `tools lat --output json` lists `Lewis 1890`.
- `encounter lat lupus lewis_1890 --no-normalize --output json` returns English dictionary evidence.
- `triples-dump lat lupus lewis_1890` returns source-backed gloss triples.
- `word-index sources/list/nearby/wheel` expose Lewis 1890 and Bailly from their DuckDB indexes.
- Focused tests, `just ruff-check`, and `just test-fast` pass.
