> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# Bailly Greek Provider Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Bailly a first-class Greek dictionary backend/provider, with local DuckDB lookup, staged execution claims, encounter/tool-filter support, and the same French-to-English translation-cache pathway used by DICO and Gaffiot.

**Architecture:** Bailly should follow the local French-lexicon pattern already used by Gaffiot and DICO: `fetch.bailly` reads `lex_bailly.duckdb`, `extract.bailly.json` normalizes the local JSON payload, `derive.bailly.entries` preserves entries as derivation evidence, and `claim.bailly.entries` emits source-language French gloss triples. Greek Diogenes remains the morphology/citation provider; Bailly supplies dictionary evidence and translated learner glosses where the translation cache has entries.

**Tech Stack:** Python, Click, DuckDB, `query_spec` staged tool plans, `RawResponseEffect`, `ExtractionEffect`, `DerivationEffect`, `ClaimEffect`, translation cache projection, `nose2`, `just`.

---

## Scope and Boundaries

Bailly should support a close approximation of Greek Diogenes where that makes product sense:

- It is selectable through `tool_filter=bailly`.
- It is visible in `tools grc --output json`.
- It participates in Greek `all` plans as an optional local dictionary provider.
- It produces claims and triples through the same execution pipeline as other providers.
- It works in `plan`, `plan-exec`, `encounter`, and `triples-dump` through normal provider plumbing.
- It supports French source-entry translation via `TranslationCache`, matching DICO/Gaffiot behavior.

Bailly should not pretend to provide morphology. Keep Diogenes responsible for Greek parse/morphology and citation claims. Bailly evidence should be dictionary/source-gloss evidence.

## Existing Source of Truth

- Databuild: `src/langnet/databuild/bailly.py`
- XML extraction: `src/langnet/parsing/bailly_pdf_xml.py`
- Bailly default DB path: `src/langnet/databuild/paths.py::default_bailly_path`
- Local lexicon patterns:
  - `src/langnet/execution/handlers/gaffiot.py`
  - `src/langnet/execution/handlers/dico.py`
  - `src/langnet/planner/local_lexicons.py`
  - `src/langnet/execution/registry.py`
  - `src/langnet/translation/projection.py`

## Task 1: Add Bailly Execution Handler

**Files:**
- Create: `src/langnet/execution/handlers/bailly.py`
- Test: `tests/test_bailly_provider_handler.py`

- [ ] **Step 1: Write failing handler tests**

Add tests that create a temporary Bailly DuckDB with `apply_bailly_schema()` and `insert_pdf_structural_entry()`, then verify:

```python
def test_bailly_fetch_client_returns_local_entries() -> None:
    # Build temp Bailly DB with lemma "ἀγελαῖος", lemma_norm "agelaios".
    # Execute BaillyFetchClient with headword="agelaios".
    # Assert JSON body has one entry with blocks and page_start/page_end.
```

```python
def test_claim_bailly_entries_emits_french_gloss_triples() -> None:
    # Pass a RawResponseEffect through extract_bailly_json,
    # derive_bailly_entries, and claim_bailly_entries.
    # Assert value["triples"] contains:
    # - lex:agelaios has_sense sense:lex:agelaios#...
    # - gloss triple with source_lang="fr"
    # - evidence.source_tool == "bailly"
    # - evidence.source_ref starts with "bailly:"
```

Run:

```bash
just test test_bailly_provider_handler
```

Expected: FAIL because `langnet.execution.handlers.bailly` does not exist.

- [ ] **Step 2: Implement `src/langnet/execution/handlers/bailly.py`**

Follow `gaffiot.py` closely. Required functions/classes:

```python
def normalize_bailly_headword(raw: str) -> str:
    from langnet.normalizer.utils import normalize_greekish_token
    return normalize_greekish_token(raw) or raw.strip().lower()
```

```python
class BaillyFetchClient:
    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.bailly"
        self.db_path = db_path
```

The fetch client should pass ordered candidates to `lookup_bailly_entries()`:

- `headword`
- `lemma`
- `q`
- semicolon-split `lemma_candidates`

`bailly_entry_triples(entry)` should emit the same basic shape as Gaffiot:

- `lex:{lemma_norm}` `has_sense` `sense:lex:{lemma_norm}#{digest}`
- `sense:*` `gloss` source text

Use Bailly block text as source text:

- Prefer joining non-empty non-head blocks in ordinal order.
- If an entry only has a head block, fall back to `raw_text`.
- Preserve `source_entry` metadata with `dict="bailly"`, `entry_id`, `lemma`, `lemma_norm`, `page_start`, `page_end`, `source_ref`, and `source_text`.

Use evidence:

```python
evidence = {
    "source_tool": "bailly",
    "source_ref": f"bailly:{entry_id}",
    "raw_blob_ref": "pdf_structural_jsonl",
    "page_start": entry.get("page_start"),
    "page_end": entry.get("page_end"),
}
```

Set gloss metadata:

```python
{
    "source_lang": "fr",
    "source_ref": source_ref,
    "display_gloss": display_gloss,
    "learner_gloss": learner_gloss,
    "learner_segments": learner_segments,
    "source_entry": source_entry,
    "source_segments": source_segments,
}
```

- [ ] **Step 3: Add extract/derive/claim functions**

Implement:

```python
def extract_bailly_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect
def derive_bailly_entries(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect
def claim_bailly_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect
```

Use stable prefixes:

- `bailly-ext`
- `bailly-der`
- `bailly-clm`

Use `kind="bailly.entries"`.

- [ ] **Step 4: Run handler tests**

Run:

```bash
just test test_bailly_provider_handler
```

Expected: PASS.

## Task 2: Add Bailly to Planner and Execution Registry

**Files:**
- Modify: `src/langnet/planner/local_lexicons.py`
- Modify: `src/langnet/planner/core.py`
- Modify: `src/langnet/execution/registry.py`
- Test: `tests/test_planner_core.py`

- [ ] **Step 1: Write failing planner test**

Add to `tests/test_planner_core.py`:

```python
def test_greek_plan_includes_bailly_dictionary_provider() -> None:
    plan = ToolPlanner(PlannerConfig(max_candidates=2)).build(_grc_normalized())
    tools = {call.tool for call in plan.tool_calls}

    assert "fetch.bailly" in tools
    assert "extract.bailly.json" in tools
    assert "derive.bailly.entries" in tools
    assert "claim.bailly.entries" in tools

    bailly_call = next(call for call in plan.tool_calls if call.tool == "fetch.bailly")
    assert bailly_call.params.get("headword") == "logos"
    assert bailly_call.params.get("lemma") == "λόγος"
    assert bailly_call.params.get("lemma_candidates") == "λόγος"
```

Run:

```bash
just test test_planner_core
```

Expected: FAIL because Bailly calls are not planned.

- [ ] **Step 2: Add `append_bailly_calls()`**

In `src/langnet/planner/local_lexicons.py`, add:

```python
def append_bailly_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
    lemma_candidates: list[str] | None = None,
) -> None:
    bailly_fetch_id = "bailly-1"
    params = {"headword": headword, "lemma": lemma}
    if lemma_candidates:
        params["lemma_candidates"] = ";".join(lemma_candidates)
    # Add fetch.bailly -> extract.bailly.json -> derive.bailly.entries
    # -> claim.bailly.entries using the Gaffiot priorities as the model.
```

Use endpoint names:

- `duckdb://bailly`
- `internal://bailly/json_extract`
- `internal://bailly/entry_derive`
- `internal://claim/bailly_entries`

- [ ] **Step 3: Call Bailly from Greek planner**

In `src/langnet/planner/core.py`, import `append_bailly_calls` and call it in `_build_greek_calls()` after Diogenes/CTS calls are added.

Use candidates:

```python
lemma_candidates=[
    cand.lemma
    for cand in normalized.candidates
    if cand.lemma
]
```

For `headword`, use `normalized.original`. For `lemma`, use `candidate.lemma` or `query_value`.

- [ ] **Step 4: Register handlers**

In `src/langnet/execution/registry.py`:

```python
from langnet.execution.handlers import bailly as bailly_handlers

extract["extract.bailly.json"] = bailly_handlers.extract_bailly_json
derive["derive.bailly.entries"] = bailly_handlers.derive_bailly_entries
claim["claim.bailly.entries"] = bailly_handlers.claim_bailly_entries
```

- [ ] **Step 5: Run planner tests**

Run:

```bash
just test test_planner_core
```

Expected: PASS.

## Task 3: Add Bailly Fetch Client to CLI Execution

**Files:**
- Modify: `src/langnet/cli.py`
- Test: `tests/test_bailly_plan_exec.py`

- [ ] **Step 1: Write failing plan-exec test**

Create a test that builds a temporary Bailly DB, monkeypatches `default_bailly_path()` or constructs `BaillyFetchClient(db_path=...)`, and verifies `_build_exec_clients()` can create a client for `fetch.bailly`.

If direct private-function testing is too brittle, use `CliRunner` with a small plan containing `fetch.bailly` and verify plan execution reaches the handler with the temp DB.

Run:

```bash
just test test_bailly_plan_exec
```

Expected: FAIL because no `fetch.bailly` factory exists.

- [ ] **Step 2: Add `_create_bailly_client()`**

In `src/langnet/cli.py`, near `_create_gaffiot_client()`:

```python
def _create_bailly_client(tool: str, use_stubs: bool) -> ToolClient | None:
    try:
        from langnet.execution.handlers.bailly import BaillyFetchClient  # noqa: PLC0415

        return BaillyFetchClient()
    except Exception:
        if use_stubs:
            return StubToolClient(tool)
    return None
```

Add to `special_factories`:

```python
"fetch.bailly": lambda: _create_bailly_client(tool, use_stubs),
```

- [ ] **Step 3: Run execution client tests**

Run:

```bash
just test test_bailly_plan_exec
```

Expected: PASS.

## Task 4: Add Bailly to Tool Catalog and CLI Help Contracts

**Files:**
- Modify: `src/langnet/tool_catalog.py`
- Modify: `tests/test_tool_catalog.py`
- Modify: `tests/test_cli_help.py`

- [ ] **Step 1: Write failing catalog tests**

Add expectations:

```python
def test_catalog_lists_greek_bailly_filter() -> None:
    filters = {entry.tool_filter for entry in catalog_entries("grc")}
    assert "bailly" in filters
```

In `test_tools_json_output_lists_translation_capable_sources`, add a Greek query or a new test:

```python
result = runner.invoke(main, ["tools", "grc", "--output", "json"])
payload = json.loads(result.output)
bailly = next(tool for tool in payload["tools"] if tool["tool_filter"] == "bailly")
assert bailly["translation_capable"] is True
assert "claim.bailly.entries" in bailly["plan_tools"]
```

Run:

```bash
just test test_tool_catalog test_cli_help
```

Expected: FAIL because Bailly is missing from the catalog.

- [ ] **Step 2: Add catalog entry**

In `_CATALOG`, add after Greek Diogenes:

```python
ToolCatalogEntry(
    language="grc",
    tool_filter="bailly",
    label="Bailly",
    role="Greek-French dictionary entries",
    source_tools=("bailly",),
    plan_tools=(
        "fetch.bailly",
        "extract.bailly.json",
        "derive.bailly.entries",
        "claim.bailly.entries",
    ),
    translation_capable=True,
    notes="French source entries can be projected through the translation cache.",
),
```

- [ ] **Step 3: Update CLI help expectations if needed**

If help tests assert expected source filters or command names, add `bailly` to the Greek provider expectations.

- [ ] **Step 4: Run catalog/help tests**

Run:

```bash
just test test_tool_catalog test_cli_help
```

Expected: PASS.

## Task 5: Add Bailly Translation Projection

**Files:**
- Modify: `src/langnet/translation/projection.py`
- Modify: `tests/test_translation_projection.py`
- Optionally modify: `tests/fixtures/translation_cache_golden_rows.json`

- [ ] **Step 1: Write failing translation projection test**

Add a Bailly claim fixture:

```python
def _bailly_claim() -> Mapping[str, Any]:
    return {
        "claim_id": "claim-bailly-agelaios",
        "tool": "claim.bailly.entries",
        "value": {
            "triples": [
                {
                    "subject": "lex:agelaios",
                    "predicate": "has_sense",
                    "object": "sense:lex:agelaios#bailly-troupeau",
                    "metadata": {
                        "evidence": {
                            "source_tool": "bailly",
                            "source_ref": "bailly:bailly-p090-c1-0004",
                        }
                    },
                },
                {
                    "subject": "sense:lex:agelaios#bailly-troupeau",
                    "predicate": "gloss",
                    "object": "qui forme un troupeau",
                    "metadata": {
                        "source_lang": "fr",
                        "source_ref": "bailly:bailly-p090-c1-0004",
                        "evidence": {
                            "source_tool": "bailly",
                            "source_ref": "bailly:bailly-p090-c1-0004",
                        },
                    },
                },
            ]
        },
    }
```

Add:

```python
def test_cached_bailly_translation_projects_as_english_gloss() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    key = build_translation_key(
        source_lexicon="bailly",
        entry_id="bailly-p090-c1-0004",
        occurrence=0,
        headword_norm="agelaios",
        source_text="qui forme un troupeau",
        model="test:model",
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("grc")),
    )
    cache.upsert(TranslationRecord(key=key, translated_text="forming a herd", status="ok", duration_ms=7))

    projected = project_cached_translations(
        claims=[_bailly_claim()],
        language="grc",
        model="test:model",
        cache=cache,
    )

    triples = projected[0]["value"]["triples"]
    assert any(triple.get("object") == "forming a herd" for triple in triples)
```

Run:

```bash
just test test_translation_projection
```

Expected: FAIL because `translation_source_from_evidence()` ignores `source_tool == "bailly"`.

- [ ] **Step 2: Add Bailly source identity**

In `translation_source_from_evidence()`:

```python
if source_tool == "bailly":
    _, _, entry_id = source_ref.partition(":")
    if not entry_id:
        return None
    return TranslationSource(
        source_lexicon="bailly",
        entry_id=entry_id,
        occurrence=_int_value(evidence.get("occurrence")),
        source_ref=source_ref,
        source_tool=source_tool,
    )
```

Default occurrence should be `0` unless a later Bailly handler chooses to emit per-block occurrences.

- [ ] **Step 3: Run translation tests**

Run:

```bash
just test test_translation_projection
```

Expected: PASS.

## Task 6: Encounter and Triples Output Contracts

**Files:**
- Modify: `tests/test_cli_encounter_output.py`
- Modify: `tests/test_cli_triples_json.py` or add `tests/test_bailly_triples.py`
- Modify: `src/langnet/encounter_ranking.py` only if Bailly ordering needs source-specific behavior.

- [ ] **Step 1: Write focused triples test**

Add a unit test that uses `bailly_entry_triples()` directly:

```python
def test_bailly_entry_triples_include_source_entry_and_french_segments() -> None:
    triples = bailly_entry_triples({
        "entry_id": "bailly-p090-c1-0004",
        "lemma": "ἀγελαῖος",
        "lemma_norm": "agelaios",
        "page_start": 90,
        "page_end": 90,
        "blocks": [
            {"path": "00", "marker": "head", "text": "ἀγελαῖος, α, ον [ ᾰγ ]"},
            {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
        ],
    })
    gloss = next(triple for triple in triples if triple["predicate"] == "gloss")
    assert gloss["metadata"]["source_lang"] == "fr"
    assert gloss["metadata"]["evidence"]["source_tool"] == "bailly"
    assert gloss["metadata"]["source_entry"]["page_start"] == 90
```

- [ ] **Step 2: Verify `tool_filter=bailly` keeps Bailly plan calls**

Use the existing `_filter_plan_tools()` behavior: because it matches `fetch.bailly`, `extract.bailly.json`, `derive.bailly.entries`, and `claim.bailly.entries`, no special filter code should be needed. Add a test if there is already a nearby filter contract.

- [ ] **Step 3: Decide whether Bailly needs ranking weights**

Initial recommendation: do not add source-specific ranking until provider output exists in encounter fixtures. Generic source ordering is enough for first integration.

If Bailly entries are buried behind Diogenes in Greek `all`, add a small ordering helper later, similar to `gaffiot_source_order`.

- [ ] **Step 4: Run encounter/triples tests**

Run:

```bash
just test test_bailly_triples test_cli_triples_json test_cli_encounter_output
```

Expected: PASS.

## Task 7: End-to-End Local Verification

**Files:**
- No production files unless verification exposes a bug.
- Use existing debug artifacts or build a fresh small temp DB in tests.

- [ ] **Step 1: Verify the Bailly database exists or rebuild it**

If using the full local corpus:

```bash
just cli -- bailly-xml-extract /home/nixos/digital-bailly-pdf/xml-pages --output examples/debug/bailly-structural-extract.jsonl
just cli-databuild bailly --source examples/debug/bailly-structural-extract.jsonl --output data/build/lex_bailly.duckdb --wipe
```

- [ ] **Step 2: Verify direct lookup still works**

```bash
just cli -- bailly-db-lookup agelaios --db data/build/lex_bailly.duckdb --limit 2
just cli -- bailly-db-lookup 'γίγνομαι' --db data/build/lex_bailly.duckdb --limit 1
just cli -- bailly-db-lookup 'εἰ' --db data/build/lex_bailly.duckdb --limit 1
```

Expected: entries with page spans and structural blocks.

- [ ] **Step 3: Verify provider planning**

```bash
just cli-plan grc agelaios --output json
```

Expected: JSON includes `fetch.bailly`, `extract.bailly.json`, `derive.bailly.entries`, and `claim.bailly.entries`.

- [ ] **Step 4: Verify Bailly-only encounter**

```bash
just cli encounter grc agelaios bailly --output json
```

Expected: claim output includes Bailly source refs and French gloss/source segments.

- [ ] **Step 5: Verify Greek all-provider encounter**

```bash
just cli encounter grc agelaios all --output json
```

Expected: Diogenes evidence remains present; Bailly evidence is also present when `lex_bailly.duckdb` exists. Missing Bailly DB should be non-fatal because the fetch call is optional.

- [ ] **Step 6: Verify translation projection**

Use existing translation-cache workflow with a cached Bailly key, or add a test fixture. Expected: Bailly French glosses project into English gloss triples with:

```python
metadata["source_lang"] == "en"
metadata["evidence"]["source_tool"] == "translation"
metadata["evidence"]["derived_from_tool"] == "bailly"
metadata["evidence"]["source_text_lang"] == "fr"
```

## Final Verification

Run:

```bash
just test test_bailly_provider_handler test_bailly_structured_db test_bailly_pdf_xml test_planner_core test_tool_catalog test_translation_projection test_cli_help
just ruff-check
```

If touching encounter display/ranking:

```bash
just test test_cli_encounter_output test_cli_triples_json
```

If the full suite is practical in the session:

```bash
just test-fast
```

## Open Design Questions

1. Should Bailly be included in Greek `all` immediately, or only exposed behind `tool_filter=bailly` until we inspect encounter ranking?

   Recommendation: include it in Greek `all` as optional. It is local and non-fatal when the DB is absent.

2. Should Bailly emit one gloss triple per structural block or one combined source-entry gloss?

   Recommendation: start with one combined gloss triple per entry. The current translation cache model keys by source text; per-block triples would create many more translation units and may over-fragment learner display. Later, we can emit block-level claims if educational display benefits from the structure.

3. Should Bailly use Greek Unicode or normalized Latin transliteration for `lex:` anchors?

   Recommendation: use `lemma_norm` for `lex:` anchors, matching lookup and cache stability, while preserving Greek lemma in `source_entry`.

4. Should Bailly have a word-index source?

   Recommendation: not in the first provider integration. Add word-index support later if the product needs Bailly browsing/neighborhoods.
