# Project Orion UI Overhaul And Reader Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Begin the Project Orion UI overhaul by standardizing reusable manuscript-workspace primitives, then use reader traditional structure as the first concrete pilot for Work Desk, Canon Table, Marginalia, Apparatus Sheet, provenance, and research-backed metadata.

**Architecture:** Introduce shared UI vocabulary and components first: Object Card, Canon Table, Marginalium, Provenance Chip Row, Oracle Panel, Dossier, Wheel, and Apparatus Sheet. Keep `work_map_nodes` as the range backbone and add a companion division metadata overlay keyed by `work_id + node_id`. Add a new `reader structure` contract for Canon Table rendering while keeping `reader map` backward-compatible. The web reader consumes the new contract as a Work Desk Structure panel, then exposes the same structure through desktop marginalia and a mobile Apparatus Sheet. Firecrawl-backed research produces audit artifacts and curated/generated metadata records that feed the same provenance-bearing UI.

**Tech Stack:** Python dataclasses, YAML loaders, DuckDB catalog storage, Click CLI, pytest via `just test`, SvelteKit, TypeScript, Tailwind/DaisyUI, Bun tests via `cd webapp && just test`, Firecrawl CLI for bounded metadata research batches.

---

## Source Documents

- Design spec: `docs/superpowers/specs/2026-06-02-orion-reader-structure-design.md`
- Completed plan: `docs/plans/completed/infra/reader-traditional-structure-overhaul.md`
- Existing related plan: `docs/plans/completed/infra/reader-citation-reference-resolution.md`
- Reader web contract: `docs/READER_WEB_CONTRACT.md`
- UI guide: `webapp/docs/UI.md`
- Metadata enrichment loop: `docs/READER_METADATA_ENRICHMENT_LOOP.md`
- Reader metadata enrichment skill: `langnet-reader-metadata-enrichment`

## File Structure

- Modify `webapp/src/lib/ui-copy.ts`: add Orion vocabulary, apparatus labels, provenance labels, and async labels.
- Add or modify reusable reader UI primitives in `webapp/src/routes/reader/+page.svelte` and `webapp/src/app.css`: Object Card, Canon Table, Provenance Chip Row, Loading Strip, Apparatus Sheet.
- Create `src/langnet/reader/division_metadata.py`: load and validate curated division metadata YAML.
- Modify `src/langnet/reader/models.py`: add `ReaderDivisionMetadata`.
- Modify `src/langnet/reader/storage.py`: create/register/query `division_metadata`; add structure and current-division helpers.
- Modify `src/langnet/reader/service.py`: expose `structure_payload`; attach current division context to `contents`, `show`, and `resolve-address`.
- Modify `src/langnet/cli.py`: add `reader structure` and `reader sync-division-metadata`; pretty-print structure rows.
- Modify `src/langnet/reader/builder.py`: accept and register `division_metadata_dir`.
- Create `data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml`: seed one reviewed chapter bio fixture for product smoke coverage.
- Create `tests/test_reader_division_metadata.py`: loader tests.
- Modify `tests/test_reader_storage.py`: registration/query/current-context tests.
- Modify `tests/test_reader_cli.py`: CLI JSON contract tests.
- Modify `tests/test_reader_enumeration.py`: service integration tests.
- Modify `webapp/src/lib/ui-copy.ts`: add Orion vocabulary and async labels.
- Modify `webapp/src/lib/reader.ts`: add types and route state for structure apparatus.
- Modify `webapp/src/lib/server/reader-cli.ts`: add `readerStructure`.
- Modify `webapp/src/routes/api/reader/+server.ts`: add `mode=structure`.
- Modify `webapp/src/routes/reader/+page.svelte`: add structure loading, Work Desk Canon Table, current-division marginalia, and mobile Apparatus Sheet.
- Modify `webapp/src/app.css`: add component classes for Canon Table, object cards, provenance chips, and apparatus sheet.
- Add or modify web tests near `webapp/src/lib/reader.test.ts` and `webapp/src/lib/reader-page-loading.test.ts`.
- Add Firecrawl research artifacts under `.firecrawl/reader-metadata/orion-structure-pilot/` during the pilot research batch, but do not treat them as runtime data.
- Add curated YAML under the appropriate `data/curated/reader_*` directory for source-backed research outputs.

---

## Priority Order

This plan is not merely a ToC feature kickoff. Implement in this order:

1. UI system foundation: vocabulary, provenance chips, object-card patterns,
   async state rules, and mobile apparatus behavior.
2. Reader Work Desk and Leaf integration using the current contracts where
   possible.
3. Traditional structure backend contract and division metadata.
4. Firecrawl-backed research and generated/reviewed metadata enrichment.

Traditional structure is the pilot surface because it forces the UI to handle
World location, Oracle consultation, source evidence, generated prose, and
mobile apparatus access in one bounded feature.

### Task 1: Orion UI Vocabulary And Shared Primitives

**Files:**
- Modify: `webapp/src/lib/ui-copy.ts`
- Modify: `webapp/src/routes/reader/+page.svelte`
- Modify: `webapp/src/app.css`
- Test: `webapp/src/lib/reader-page-loading.test.ts`

- [ ] **Step 1: Write the failing UI primitive test**

In `webapp/src/lib/reader-page-loading.test.ts`, add assertions that the reader page and CSS expose the design-system primitives:

```ts
assert.ok(pageSource.includes('orionObjectCard'));
assert.ok(pageSource.includes('provenanceChips'));
assert.ok(pageSource.includes('orion-reader-loading-strip'));
assert.ok(pageSource.includes('readerLoadingElapsed'));
assert.ok(cssSource.includes('.orion-object-card'));
assert.ok(cssSource.includes('.orion-reader-provenance-chip'));
assert.ok(cssSource.includes('.orion-reader-apparatus-sheet'));
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd webapp && just test
```

Expected: FAIL because the shared primitive names and styles are not present.

- [ ] **Step 3: Add copy-layer vocabulary**

In `webapp/src/lib/ui-copy.ts`, add resource groups and expose them through `uiCopy`:

```ts
orionObjects: {
    word: 'Word',
    work: 'Work',
    author: 'Author',
    chapter: 'Chapter',
    passage: 'Passage',
    dossier: 'Dossier',
    leaf: 'Leaf',
    marginalium: 'Marginalia',
    canonTable: 'Canon Table',
    oracle: 'Oracle',
    wheel: 'Wheel'
},
provenance: {
    curated: 'Curated',
    source: 'Source',
    generated: 'LLM draft',
    reviewed: 'Reviewed',
    needsEvidence: 'Needs evidence',
    needsReview: 'Needs review'
},
async: {
    loading: 'Loading',
    refreshing: 'Refreshing',
    researching: 'Researching',
    seconds: '{{seconds}}s'
}
```

- [ ] **Step 4: Add reusable snippets**

In `webapp/src/routes/reader/+page.svelte`, add snippets near the existing reader snippets:

```svelte
{#snippet provenanceChips(chips: string[] | undefined)}
    {#if chips?.length}
        <div class="orion-reader-provenance-row">
            {#each chips as chip}
                <span class="orion-reader-provenance-chip">{chip}</span>
            {/each}
        </div>
    {/if}
{/snippet}

{#snippet orionObjectCard(kind: string, title: string, subtitle: string, chips: string[] = [])}
    <article class="orion-object-card">
        <span>{kind}</span>
        <strong>{title}</strong>
        {#if subtitle}
            <small>{subtitle}</small>
        {/if}
        {@render provenanceChips(chips)}
    </article>
{/snippet}
```

- [ ] **Step 5: Add CSS primitives**

In `webapp/src/app.css`, add:

```css
.orion-object-card {
    display: grid;
    gap: 0.3rem;
    border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
    border-left: 0.18rem solid color-mix(in oklab, var(--color-primary) 44%, var(--color-accent));
    border-radius: var(--radius-box);
    background: color-mix(in oklab, var(--color-base-100) 92%, var(--color-base-200));
    padding: 0.62rem;
}

.orion-object-card > span {
    color: color-mix(in oklab, var(--color-base-content) 48%, transparent);
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
}

.orion-object-card strong {
    color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
    font-family: var(--font-serif);
    font-size: 1rem;
    line-height: 1.2;
}

.orion-reader-provenance-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.28rem;
}

.orion-reader-provenance-chip {
    border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
    border-radius: 0.25rem;
    background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-accent) 8%);
    padding: 0.1rem 0.32rem;
    color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-primary));
    font-size: 0.66rem;
    font-weight: 800;
    line-height: 1.2;
}
```

- [ ] **Step 6: Run web tests**

Run:

```bash
cd webapp && just test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add webapp/src/lib/ui-copy.ts webapp/src/routes/reader/+page.svelte webapp/src/app.css webapp/src/lib/reader-page-loading.test.ts
git commit -m "feat: add Orion UI primitives"
```

---

### Task 2: Reader Work Desk And Apparatus Foundation

**Files:**
- Modify: `webapp/src/routes/reader/+page.svelte`
- Modify: `webapp/src/app.css`
- Test: `webapp/src/lib/reader-page-loading.test.ts`

- [ ] **Step 1: Add failing Work Desk assertions**

In `webapp/src/lib/reader-page-loading.test.ts`, assert:

```ts
assert.ok(pageSource.includes('orion-reader-work-desk'));
assert.ok(pageSource.includes('orion-reader-leaf'));
assert.ok(pageSource.includes('orion-reader-apparatus-tabs'));
assert.ok(pageSource.includes("activeApparatusPanel = 'structure'"));
assert.ok(cssSource.includes('.orion-reader-work-desk'));
assert.ok(cssSource.includes('@media (max-width: 48rem)'));
```

- [ ] **Step 2: Run web test to verify failure**

Run:

```bash
cd webapp && just test
```

Expected: FAIL until Work Desk and apparatus scaffolding exists.

- [ ] **Step 3: Add Work Desk container**

In `webapp/src/routes/reader/+page.svelte`, add a Work Desk section above the current Leaf when `selectedWork` exists:

```svelte
{#if selectedWork}
    <section class="orion-reader-work-desk">
        {@render orionObjectCard(
            uiCopy.orionObjects.work,
            selectedWorkTitleLabel(),
            selectedWorkContributorLine() || selectedWorkDiscriminator() || '',
            selectedWork.classification_confidence ? [selectedWork.classification_confidence] : []
        )}
    </section>
{/if}
```

- [ ] **Step 4: Add mobile apparatus state**

Add state:

```ts
let activeApparatusPanel = $state<'structure' | 'word' | 'oracle' | 'evidence' | ''>('');
```

Add bottom apparatus tabs inside `<main>`:

```svelte
{#if selectedWork || selectedSegment || selectedWord}
    <nav class="orion-reader-apparatus-tabs" aria-label="Reader apparatus">
        <button type="button" onclick={() => (activeApparatusPanel = 'structure')}>Structure</button>
        <button type="button" onclick={() => (activeApparatusPanel = 'word')}>Word</button>
        <button type="button" onclick={() => (activeApparatusPanel = 'oracle')}>Oracle</button>
        <button type="button" onclick={() => (activeApparatusPanel = 'evidence')}>Evidence</button>
    </nav>
{/if}
```

- [ ] **Step 5: Add responsive shell CSS**

In `webapp/src/app.css`, add:

```css
.orion-reader-work-desk {
    display: grid;
    gap: 0.75rem;
    padding: 1rem;
    border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
}

.orion-reader-apparatus-tabs,
.orion-reader-apparatus-sheet {
    display: none;
}

@media (max-width: 48rem) {
    .orion-reader-shell {
        padding-bottom: 4.5rem;
    }

    .orion-reader-apparatus-tabs {
        position: fixed;
        z-index: 35;
        right: 0.75rem;
        bottom: 0.75rem;
        left: 0.75rem;
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.25rem;
        border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
        border-radius: var(--radius-box);
        background: color-mix(in oklab, var(--color-base-100) 94%, var(--color-base-200));
        padding: 0.3rem;
    }
}
```

- [ ] **Step 6: Run web tests**

Run:

```bash
cd webapp && just test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add webapp/src/routes/reader/+page.svelte webapp/src/app.css webapp/src/lib/reader-page-loading.test.ts
git commit -m "feat: scaffold reader work desk apparatus"
```

---

### Task 3: Division Metadata Loader

**Files:**
- Modify: `src/langnet/reader/models.py`
- Create: `src/langnet/reader/division_metadata.py`
- Test: `tests/test_reader_division_metadata.py`

- [ ] **Step 1: Write the failing loader tests**

Create `tests/test_reader_division_metadata.py`:

```python
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from langnet.reader.division_metadata import (
    accepted_division_metadata,
    load_division_metadata,
)


def test_load_division_metadata_reads_chapter_bio_with_provenance() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "sanskrit" / "bhagavadgita.yaml"
        source.parent.mkdir()
        source.write_text(
            """
division_metadata:
  - work_id: "urn:cts:sanskritLit:mbh.bhg"
    node_id: "bhg-09"
    summary: "A concise reviewed note on royal knowledge and secrecy."
    short_label: "Royal knowledge"
    traditional_reference: "BhG 9"
    status: "accepted"
    confidence: "high"
    generator_model: ""
    review_status: "reviewed"
    note: "Fixture reviewed chapter note."
    evidence:
      - source_type: "source-root"
        citation: "fixture"
        label: "fixture evidence"
""".lstrip(),
            encoding="utf-8",
        )

        rows = load_division_metadata(root)

    assert len(rows) == 1
    row = rows[0]
    assert row.work_id == "urn:cts:sanskritLit:mbh.bhg"
    assert row.node_id == "bhg-09"
    assert row.summary.startswith("A concise reviewed note")
    assert row.short_label == "Royal knowledge"
    assert row.traditional_reference == "BhG 9"
    assert row.status == "accepted"
    assert row.review_status == "reviewed"
    assert row.source_file == str(source)
    assert row.evidence[0].source_type == "source-root"


def test_accepted_division_metadata_filters_reviewable_drafts() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "draft.yaml"
        source.write_text(
            """
division_metadata:
  - work_id: "w"
    node_id: "n1"
    summary: "accepted"
    short_label: "accepted"
    traditional_reference: "W 1"
    status: "accepted"
    confidence: "high"
    generator_model: ""
    review_status: "reviewed"
    note: "fixture"
    evidence:
      - source_type: "fixture"
        citation: "fixture"
        label: "fixture"
  - work_id: "w"
    node_id: "n2"
    summary: "draft"
    short_label: "draft"
    traditional_reference: "W 2"
    status: "candidate"
    confidence: "medium"
    generator_model: "openrouter:test"
    review_status: "llm_draft"
    note: "fixture"
    evidence:
      - source_type: "llm"
        citation: "openrouter:test"
        label: "fixture"
""".lstrip(),
            encoding="utf-8",
        )

        rows = load_division_metadata(root)

    assert [row.node_id for row in accepted_division_metadata(rows)] == ["n1"]


def test_load_division_metadata_rejects_missing_evidence() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "bad.yaml"
        source.write_text(
            """
division_metadata:
  - work_id: "w"
    node_id: "n"
    summary: "missing evidence"
    short_label: "bad"
    traditional_reference: "W 1"
    status: "accepted"
    confidence: "high"
    generator_model: ""
    review_status: "reviewed"
    note: "fixture"
""".lstrip(),
            encoding="utf-8",
        )

        try:
            load_division_metadata(root)
        except ValueError as exc:
            message = str(exc)
        else:
            raise AssertionError("expected missing evidence to fail")

    assert "requires at least one evidence item" in message
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
just test tests.test_reader_division_metadata
```

Expected: FAIL with `ModuleNotFoundError: No module named 'langnet.reader.division_metadata'`.

- [ ] **Step 3: Add the dataclass**

In `src/langnet/reader/models.py`, after `ReaderWorkMapNode`, add:

```python
@dataclass(frozen=True)
class ReaderDivisionMetadata:
    work_id: str
    node_id: str
    summary: str
    short_label: str
    traditional_reference: str
    status: str
    confidence: str
    generator_model: str
    review_status: str
    note: str
    source_file: str = ""
    evidence: tuple[ReaderMetadataOverlayEvidence, ...] = ()
```

- [ ] **Step 4: Add the loader implementation**

Create `src/langnet/reader/division_metadata.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from langnet.reader.models import ReaderDivisionMetadata, ReaderMetadataOverlayEvidence

_REQUIRED_KEYS = {
    "work_id",
    "node_id",
    "summary",
    "short_label",
    "traditional_reference",
    "status",
    "confidence",
    "generator_model",
    "review_status",
    "note",
    "evidence",
}
_SUPPORTED_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}
_SUPPORTED_CONFIDENCE = {"high", "medium", "low"}
_SUPPORTED_REVIEW_STATUSES = {"reviewed", "llm_draft", "needs_review", "source_backed"}
_REQUIRED_EVIDENCE_KEYS = {"source_type", "citation", "label"}


def load_division_metadata(root: Path) -> list[ReaderDivisionMetadata]:
    if not root.exists():
        return []
    rows: list[ReaderDivisionMetadata] = []
    for path in sorted(root.rglob("*.yaml")):
        rows.extend(_load_division_metadata_file(path))
    return rows


def accepted_division_metadata(
    rows: list[ReaderDivisionMetadata],
) -> list[ReaderDivisionMetadata]:
    return [row for row in rows if row.status == "accepted"]


def _load_division_metadata_file(path: Path) -> list[ReaderDivisionMetadata]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        msg = f"{path}: division metadata file must be a mapping"
        raise ValueError(msg)
    raw_rows = raw.get("division_metadata")
    if raw_rows is None:
        return []
    if not isinstance(raw_rows, list):
        msg = f"{path}: division_metadata must be a list"
        raise ValueError(msg)
    return [_row_from_record(path, cast(dict[str, Any], record)) for record in raw_rows]


def _row_from_record(path: Path, record: dict[str, Any]) -> ReaderDivisionMetadata:
    if not isinstance(record, dict):
        msg = f"{path}: division metadata item must be a mapping"
        raise ValueError(msg)
    missing = sorted(_REQUIRED_KEYS - record.keys())
    if missing:
        if "evidence" in missing:
            msg = f"{path}: division metadata requires at least one evidence item"
            raise ValueError(msg)
        msg = f"{path}: division metadata missing required keys: {', '.join(missing)}"
        raise ValueError(msg)
    status = _record_str(path, record, "status")
    confidence = _record_str(path, record, "confidence")
    review_status = _record_str(path, record, "review_status")
    if status not in _SUPPORTED_STATUSES:
        msg = f"{path}: unsupported division metadata status {status!r}"
        raise ValueError(msg)
    if confidence not in _SUPPORTED_CONFIDENCE:
        msg = f"{path}: unsupported division metadata confidence {confidence!r}"
        raise ValueError(msg)
    if review_status not in _SUPPORTED_REVIEW_STATUSES:
        msg = f"{path}: unsupported division metadata review_status {review_status!r}"
        raise ValueError(msg)
    return ReaderDivisionMetadata(
        work_id=_record_str(path, record, "work_id"),
        node_id=_record_str(path, record, "node_id"),
        summary=_record_str(path, record, "summary"),
        short_label=_record_str(path, record, "short_label"),
        traditional_reference=_record_str(path, record, "traditional_reference"),
        status=status,
        confidence=confidence,
        generator_model=_record_str(path, record, "generator_model"),
        review_status=review_status,
        note=_record_str(path, record, "note"),
        source_file=str(path),
        evidence=_evidence_from_record(path, record),
    )


def _evidence_from_record(
    path: Path,
    record: dict[str, Any],
) -> tuple[ReaderMetadataOverlayEvidence, ...]:
    raw_evidence = record["evidence"]
    if not isinstance(raw_evidence, list) or not raw_evidence:
        msg = f"{path}: division metadata requires at least one evidence item"
        raise ValueError(msg)
    evidence: list[ReaderMetadataOverlayEvidence] = []
    for raw_item in raw_evidence:
        if not isinstance(raw_item, dict):
            msg = f"{path}: division metadata evidence item must be a mapping"
            raise ValueError(msg)
        item = cast(dict[str, Any], raw_item)
        missing = sorted(_REQUIRED_EVIDENCE_KEYS - item.keys())
        if missing:
            msg = f"{path}: division metadata evidence missing required keys: {', '.join(missing)}"
            raise ValueError(msg)
        evidence.append(
            ReaderMetadataOverlayEvidence(
                source_type=_evidence_str(path, item, "source_type"),
                citation=_evidence_str(path, item, "citation"),
                label=_evidence_str(path, item, "label"),
                retrieved_at=_optional_record_str(item, "retrieved_at"),
            )
        )
    return tuple(evidence)


def _record_str(path: Path, record: dict[str, Any], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: division metadata key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _evidence_str(path: Path, record: dict[str, Any], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        msg = f"{path}: division metadata evidence key {key!r} must be a string"
        raise ValueError(msg)
    return value


def _optional_record_str(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    return value if isinstance(value, str) and value else None
```

- [ ] **Step 5: Run loader tests**

Run:

```bash
just test tests.test_reader_division_metadata
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/langnet/reader/models.py src/langnet/reader/division_metadata.py tests/test_reader_division_metadata.py
git commit -m "feat: load reader division metadata"
```

---

### Task 4: Division Metadata Storage

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Test: `tests/test_reader_storage.py`

- [ ] **Step 1: Write failing storage tests**

Add imports to `tests/test_reader_storage.py`:

```python
    ReaderDivisionMetadata,
```

and storage imports:

```python
    division_metadata_for_work,
    register_division_metadata,
```

Add tests near the work-map tests:

```python
def test_register_division_metadata_and_query_by_work() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.duckdb"
        create_catalog_db(catalog_path)
        register_division_metadata(
            catalog_path,
            [
                ReaderDivisionMetadata(
                    work_id="urn:cts:sanskritLit:mbh.bhg",
                    node_id="bhg-09",
                    summary="A reviewed chapter note.",
                    short_label="Royal knowledge",
                    traditional_reference="BhG 9",
                    status="accepted",
                    confidence="high",
                    generator_model="",
                    review_status="reviewed",
                    note="fixture",
                    source_file="fixture.yaml",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        rows = division_metadata_for_work(catalog_path, "urn:cts:sanskritLit:mbh.bhg")

    assert len(rows) == 1
    assert rows[0]["node_id"] == "bhg-09"
    assert rows[0]["summary"] == "A reviewed chapter note."
    assert rows[0]["traditional_reference"] == "BhG 9"
    assert rows[0]["evidence_count"] == 1


def test_division_metadata_for_work_handles_old_catalog_without_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.duckdb"
        create_catalog_db(catalog_path)
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute("DROP TABLE division_metadata")

        rows = division_metadata_for_work(catalog_path, "missing")

    assert rows == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
just test tests.test_reader_storage::test_register_division_metadata_and_query_by_work tests.test_reader_storage::test_division_metadata_for_work_handles_old_catalog_without_table
```

Expected: FAIL with missing import/function/table errors.

- [ ] **Step 3: Add catalog schema**

In `CATALOG_SCHEMA_SQL`, after `work_map_nodes`, add:

```sql
CREATE TABLE IF NOT EXISTS division_metadata (
    work_id VARCHAR NOT NULL,
    node_id VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    short_label TEXT NOT NULL,
    traditional_reference VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    generator_model VARCHAR NOT NULL,
    review_status VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);
```

Add index near `work_map_nodes_work_idx`:

```sql
CREATE INDEX IF NOT EXISTS division_metadata_work_idx ON division_metadata(work_id, node_id);
```

- [ ] **Step 4: Add register and query helpers**

In `src/langnet/reader/storage.py`, import `ReaderDivisionMetadata` from models and add:

```python
def register_division_metadata(
    catalog_path: Path,
    rows: Iterable[ReaderDivisionMetadata],
    *,
    replace: bool = True,
) -> None:
    create_catalog_db(catalog_path)
    row_values = [
        (
            row.work_id,
            row.node_id,
            row.summary,
            row.short_label,
            row.traditional_reference,
            row.status,
            row.confidence,
            row.generator_model,
            row.review_status,
            row.note,
            row.source_file,
            evidence.source_type,
            evidence.citation,
            evidence.label,
            evidence.retrieved_at,
        )
        for row in rows
        for evidence in row.evidence
    ]
    with _connect_write(catalog_path) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            if replace:
                conn.execute("DELETE FROM division_metadata")
            if row_values:
                frame = pl.DataFrame(
                    row_values,
                    schema={
                        "work_id": pl.Utf8,
                        "node_id": pl.Utf8,
                        "summary": pl.Utf8,
                        "short_label": pl.Utf8,
                        "traditional_reference": pl.Utf8,
                        "status": pl.Utf8,
                        "confidence": pl.Utf8,
                        "generator_model": pl.Utf8,
                        "review_status": pl.Utf8,
                        "note": pl.Utf8,
                        "source_file": pl.Utf8,
                        "evidence_source_type": pl.Utf8,
                        "evidence_citation": pl.Utf8,
                        "evidence_label": pl.Utf8,
                        "evidence_retrieved_at": pl.Utf8,
                    },
                    orient="row",
                )
                conn.register("division_metadata_rows", frame)
                conn.execute(
                    """
                    INSERT INTO division_metadata (
                        work_id, node_id, summary, short_label, traditional_reference,
                        status, confidence, generator_model, review_status, note,
                        source_file, evidence_source_type, evidence_citation,
                        evidence_label, evidence_retrieved_at
                    )
                    SELECT
                        work_id, node_id, summary, short_label, traditional_reference,
                        status, confidence, generator_model, review_status, note,
                        source_file, evidence_source_type, evidence_citation,
                        evidence_label, evidence_retrieved_at
                    FROM division_metadata_rows
                    """
                )
                conn.unregister("division_metadata_rows")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def division_metadata_for_work(catalog_path: Path, work_ref: str) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    work = get_work(catalog_path, work_ref)
    candidates = [work_ref]
    if work:
        for value in (work.get("work_id"), work.get("cts_work_urn"), work.get("parent_work_id")):
            if value:
                candidates.append(str(value))
    resolved = resolve_work_ref(catalog_path, work_ref)
    if resolved:
        candidates.append(resolved)
    candidates = list(dict.fromkeys(candidates))
    placeholders = ", ".join("?" for _ in candidates)
    with duckdb.connect(str(catalog_path), read_only=True) as conn:
        if not _table_exists(conn, "division_metadata"):
            return []
        return _dict_rows(
            conn,
            f"""
            SELECT
                work_id, node_id, summary, short_label, traditional_reference,
                status, confidence, generator_model, review_status, note, source_file,
                count(*) AS evidence_count
            FROM division_metadata
            WHERE work_id IN ({placeholders})
              AND status = 'accepted'
            GROUP BY
                work_id, node_id, summary, short_label, traditional_reference,
                status, confidence, generator_model, review_status, note, source_file
            ORDER BY work_id, node_id
            """,
            candidates,
        )
```

- [ ] **Step 5: Run storage tests**

Run:

```bash
just test tests.test_reader_storage::test_register_division_metadata_and_query_by_work tests.test_reader_storage::test_division_metadata_for_work_handles_old_catalog_without_table
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/langnet/reader/storage.py tests/test_reader_storage.py
git commit -m "feat: store reader division metadata"
```

---

### Task 5: UI-Ready Structure Payload

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_reader_storage.py`
- Test: `tests/test_reader_enumeration.py`
- Test: `tests/test_reader_cli.py`

- [ ] **Step 1: Add failing structure service test**

In `tests/test_reader_enumeration.py`, add a fixture test that registers a work map node plus division metadata and checks `ReaderService.structure_payload`:

```python
def test_reader_service_structure_payload_merges_map_and_division_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:sanskritLit:mbh.bhg",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="mbh.bhg",
            canonical_text_id="urn:ctsv2:san:bhagavadgita-dhrtarastra-uvaca",
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id="urn:cts:sanskritLit:mbh.bhg",
                    node_id="bhg-09",
                    parent_node_id=None,
                    level=1,
                    kind="chapter",
                    label="Rāja Vidyā Rāja Guhya Yoga",
                    native_label="राजविद्याराजगुह्ययोग",
                    ordinal=9,
                    start_citation="231273",
                    end_citation="231341",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )
        register_division_metadata(
            catalog_path,
            [
                ReaderDivisionMetadata(
                    work_id="urn:cts:sanskritLit:mbh.bhg",
                    node_id="bhg-09",
                    summary="A reviewed chapter note.",
                    short_label="Royal knowledge",
                    traditional_reference="BhG 9",
                    status="accepted",
                    confidence="high",
                    generator_model="",
                    review_status="reviewed",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        payload = ReaderService(catalog_path).structure_payload("urn:cts:sanskritLit:mbh.bhg")

    assert payload["mode"] == "structure"
    assert payload["summary"]["node_count"] == 1
    item = payload["items"][0]
    assert item["node_id"] == "bhg-09"
    assert item["object_type"] == "chapter"
    assert item["summary"] == "A reviewed chapter note."
    assert item["short_label"] == "Royal knowledge"
    assert item["traditional_reference"] == "BhG 9"
    assert item["provenance_chips"] == ["Curated", "Reviewed"]
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```bash
just test tests.test_reader_enumeration::test_reader_service_structure_payload_merges_map_and_division_metadata
```

Expected: FAIL with missing imports/functions.

- [ ] **Step 3: Add structure helper in storage**

Add this helper in `src/langnet/reader/storage.py` near `work_map_for_work`:

```python
def structure_for_work(catalog_path: Path, work_ref: str) -> list[dict[str, Any]]:
    nodes = work_map_for_work(catalog_path, work_ref)
    metadata = {
        (str(row["work_id"]), str(row["node_id"])): row
        for row in division_metadata_for_work(catalog_path, work_ref)
    }
    items: list[dict[str, Any]] = []
    for node in nodes:
        meta = metadata.get((str(node["work_id"]), str(node["node_id"])), {})
        provenance_chips = _structure_provenance_chips(node, meta)
        items.append(
            {
                **node,
                "object_type": str(node.get("kind") or "division"),
                "summary": meta.get("summary"),
                "short_label": meta.get("short_label"),
                "traditional_reference": meta.get("traditional_reference"),
                "division_metadata_status": meta.get("status"),
                "division_review_status": meta.get("review_status"),
                "division_confidence": meta.get("confidence"),
                "division_evidence_count": meta.get("evidence_count"),
                "provenance_chips": provenance_chips,
            }
        )
    return items


def _structure_provenance_chips(
    node: Mapping[str, Any],
    meta: Mapping[str, Any],
) -> list[str]:
    chips: list[str] = []
    provenance = str(node.get("provenance") or "")
    if provenance == "curated":
        chips.append("Curated")
    elif provenance == "native":
        chips.append("Source")
    elif provenance == "inferred":
        chips.append("Inferred")
    review_status = str(meta.get("review_status") or "")
    if review_status == "reviewed":
        chips.append("Reviewed")
    elif review_status == "llm_draft":
        chips.append("LLM draft")
    elif review_status == "needs_review":
        chips.append("Needs review")
    return chips
```

- [ ] **Step 4: Add service payload**

Import `structure_for_work` in `src/langnet/reader/service.py` and add:

```python
    def structure_payload(self, work_ref: str) -> dict[str, Any]:
        items = structure_for_work(self.catalog_path, work_ref)
        top_level = [item for item in items if int(item.get("level") or 0) == 1]
        kinds = sorted({str(item.get("kind") or "") for item in items if item.get("kind")})
        return self._payload(
            "structure",
            items,
            work_ref=work_ref,
            summary={
                "node_count": len(items),
                "top_level_count": len(top_level),
                "kinds": kinds,
                "has_division_metadata": any(item.get("summary") for item in items),
            },
        )
```

- [ ] **Step 5: Add CLI command and pretty output**

In `_emit_reader_item`, add:

```python
    elif mode == "structure":
        label = item.get("short_label") or item.get("label")
        reference = item.get("traditional_reference") or item.get("start_citation")
        click.echo(
            f"{item.get('ordinal')}  {item.get('kind')}  {label}  "
            f"{reference}  {item.get('start_citation')}..{item.get('end_citation')}"
        )
```

In `src/langnet/cli.py`, after `reader_map`, add:

```python
@reader_cli.command("structure")
@click.argument("work_ref")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_structure(ctx: click.Context, work_ref: str, output: str) -> None:
    """Show UI-ready traditional structure for one reader work."""
    _emit_reader_payload(_reader_service_from_context(ctx).structure_payload(work_ref), output)
```

- [ ] **Step 6: Add CLI JSON test**

In `tests/test_reader_cli.py`, add a test using the existing runner/catalog fixture style. The assertion must check:

```python
assert payload["mode"] == "structure"
assert payload["summary"]["node_count"] == 1
assert payload["items"][0]["traditional_reference"] == "BhG 9"
```

Use the same registration pattern from the service test.

- [ ] **Step 7: Run targeted tests**

Run:

```bash
just test tests.test_reader_enumeration::test_reader_service_structure_payload_merges_map_and_division_metadata
just test tests.test_reader_cli::test_reader_cli_structure_returns_ui_ready_nodes
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/langnet/reader/storage.py src/langnet/reader/service.py src/langnet/cli.py tests/test_reader_storage.py tests/test_reader_enumeration.py tests/test_reader_cli.py
git commit -m "feat: expose reader structure payload"
```

---

### Task 6: Current Division Context

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/reader/service.py`
- Test: `tests/test_reader_storage.py`
- Test: `tests/test_reader_enumeration.py`

- [ ] **Step 1: Write failing current-context test**

In `tests/test_reader_storage.py`, import `current_divisions_for_segment` and add:

```python
def test_current_divisions_for_segment_finds_covering_work_map_node() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:sanskritLit:mbh.bhg",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="mbh.bhg",
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id="urn:cts:sanskritLit:mbh.bhg",
                    node_id="bhg-09",
                    parent_node_id=None,
                    level=1,
                    kind="chapter",
                    label="Rāja Vidyā Rāja Guhya Yoga",
                    native_label=None,
                    ordinal=9,
                    start_citation="231273",
                    end_citation="231341",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        rows = current_divisions_for_segment(
            catalog_path,
            "urn:cts:sanskritLit:mbh.bhg",
            "231276",
        )

    assert [row["node_id"] for row in rows] == ["bhg-09"]
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```bash
just test tests.test_reader_storage::test_current_divisions_for_segment_finds_covering_work_map_node
```

Expected: FAIL with missing function.

- [ ] **Step 3: Add storage helper**

Add in `src/langnet/reader/storage.py`:

```python
def current_divisions_for_segment(
    catalog_path: Path,
    work_ref: str,
    citation_path: str,
) -> list[dict[str, Any]]:
    items = structure_for_work(catalog_path, work_ref)
    current_sort = _citation_sort_value(citation_path)
    matches = [
        item
        for item in items
        if _citation_sort_value(str(item.get("start_citation") or "")) <= current_sort
        <= _citation_sort_value(str(item.get("end_citation") or ""))
    ]
    return sorted(matches, key=lambda item: (int(item.get("level") or 0), int(item.get("ordinal") or 0)))


def _citation_sort_value(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value)
    return tuple(int(part) for part in parts) if parts else (0,)
```

If `storage.py` does not already import `re`, add `import re` at the top.

- [ ] **Step 4: Attach current context to service payloads**

In `ReaderService.contents_payload`, after decorating/budgeting items:

```python
        for item in items:
            divisions = current_divisions_for_segment(
                self.catalog_path,
                str(item.get("work_id") or work_id),
                str(item.get("citation_path") or ""),
            )
            item["current_divisions"] = divisions
```

In `segment_payload` and `show_work_segment`, add a `current_divisions` top-level field:

```python
            "current_divisions": (
                current_divisions_for_segment(
                    self.catalog_path,
                    str(segment.get("work_id") or ""),
                    str(segment.get("citation_path") or ""),
                )
                if segment
                else []
            ),
```

Import `current_divisions_for_segment`.

- [ ] **Step 5: Add service test**

In `tests/test_reader_enumeration.py`, add an assertion to a `show_work_segment` fixture:

```python
assert payload["current_divisions"][0]["node_id"] == "bhg-09"
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
just test tests.test_reader_storage::test_current_divisions_for_segment_finds_covering_work_map_node
just test tests.test_reader_enumeration::test_reader_service_show_includes_current_division_context
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/langnet/reader/storage.py src/langnet/reader/service.py tests/test_reader_storage.py tests/test_reader_enumeration.py
git commit -m "feat: attach reader division context"
```

---

### Task 7: Sync Division Metadata Through Builder And CLI

**Files:**
- Modify: `src/langnet/reader/builder.py`
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`
- Add: `data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml`
- Test: `tests/test_reader_cli.py`
- Test: `tests/test_reader_builder_cli.py`

- [ ] **Step 1: Add curated seed metadata**

Create `data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml`:

```yaml
division_metadata:
  - work_id: "urn:cts:sanskritLit:mbh.bhg"
    node_id: "bhg-09"
    summary: "Chapter 9 presents the teaching as royal knowledge and royal secret, joining devotion, insight, and the claim that the divine is present without being exhausted by the world."
    short_label: "Royal knowledge and secret"
    traditional_reference: "BhG 9"
    status: "accepted"
    confidence: "medium"
    generator_model: ""
    review_status: "reviewed"
    note: "Initial reviewed product fixture for the Canon Table metadata layer. Keep the summary concise and provenance-marked until broader chapter-bio review exists."
    evidence:
      - source_type: "source-root"
        citation: "data/curated/reader_work_maps/sanskrit/bhagavadgita.yaml:bhg-09"
        label: "Curated Bhagavadgita chapter 9 work-map node."
```

- [ ] **Step 2: Add service sync payload**

In `src/langnet/reader/service.py`, import loader functions and add:

```python
    def sync_division_metadata_payload(self, division_metadata_dir: Path) -> dict[str, Any]:
        rows = accepted_division_metadata(load_division_metadata(division_metadata_dir))
        register_division_metadata(self.catalog_path, rows)
        return {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "sync-division-metadata",
            "catalog_path": str(self.catalog_path),
            "summary": {
                "division_metadata_dir": str(division_metadata_dir),
                "synced_count": len(rows),
            },
        }
```

- [ ] **Step 3: Add CLI sync command**

In `src/langnet/cli.py`, after `reader_sync_work_maps`, add:

```python
@reader_cli.command("sync-division-metadata")
@click.option(
    "--division-metadata-dir",
    type=click.Path(),
    default="data/curated/reader_division_metadata",
    show_default=True,
    help="Curated reader division metadata directory.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sync_division_metadata(
    ctx: click.Context,
    division_metadata_dir: str,
    output: str,
) -> None:
    """Sync curated chapter/book/division metadata into the reader catalog."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).sync_division_metadata_payload(
            Path(division_metadata_dir).expanduser()
        ),
        output,
    )
```

- [ ] **Step 4: Wire builder config**

In `ReaderBuilderConfig`, add:

```python
    division_metadata_dir: Path | None = Path("data/curated/reader_division_metadata")
```

In the builder initialization flow where work maps are loaded and registered, load accepted division metadata and call `register_division_metadata`. Use `[]` when the config path is `None`.

- [ ] **Step 5: Add CLI sync test**

In `tests/test_reader_cli.py`, add a runner test that invokes:

```python
result = runner.invoke(
    main,
    [
        "reader",
        "--catalog",
        str(catalog_path),
        "sync-division-metadata",
        "--division-metadata-dir",
        str(metadata_root),
        "--output",
        "json",
    ],
)
payload = json.loads(result.output)
assert payload["mode"] == "sync-division-metadata"
assert payload["summary"]["synced_count"] == 1
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
just test tests.test_reader_cli::test_reader_cli_sync_division_metadata
just test tests.test_reader_builder_cli
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/langnet/reader/builder.py src/langnet/reader/service.py src/langnet/cli.py data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml tests/test_reader_cli.py tests/test_reader_builder_cli.py
git commit -m "feat: sync reader division metadata"
```

---

### Task 8: Web Reader Structure API Contract

**Files:**
- Modify: `webapp/src/lib/reader.ts`
- Modify: `webapp/src/lib/server/reader-cli.ts`
- Modify: `webapp/src/routes/api/reader/+server.ts`
- Test: `webapp/src/lib/reader.test.ts`

- [ ] **Step 1: Add failing TypeScript contract test**

In `webapp/src/lib/reader.test.ts`, add:

```ts
import { strict as assert } from 'node:assert';
import type { ReaderStructureResponse } from './reader';

const structurePayload: ReaderStructureResponse = {
    schema_version: 'langnet.reader.v1',
    mode: 'structure',
    catalog_path: 'catalog.duckdb',
    request: { work_ref: 'urn:cts:sanskritLit:mbh.bhg' },
    summary: {
        node_count: 1,
        top_level_count: 1,
        kinds: ['chapter'],
        has_division_metadata: true
    },
    items: [
        {
            work_id: 'urn:cts:sanskritLit:mbh.bhg',
            node_id: 'bhg-09',
            parent_node_id: null,
            level: 1,
            kind: 'chapter',
            object_type: 'chapter',
            label: 'Rāja Vidyā Rāja Guhya Yoga',
            native_label: 'राजविद्याराजगुह्ययोग',
            ordinal: 9,
            start_citation: '231273',
            end_citation: '231341',
            provenance: 'curated',
            confidence: 'high',
            status: 'accepted',
            note: 'fixture',
            source_file: 'fixture',
            summary: 'A reviewed chapter note.',
            short_label: 'Royal knowledge',
            traditional_reference: 'BhG 9',
            provenance_chips: ['Curated', 'Reviewed'],
            word_count: 10,
            word_count_method: 'whitespace_tokens'
        }
    ]
};

assert.equal(structurePayload.items[0].traditional_reference, 'BhG 9');
```

- [ ] **Step 2: Run web test to verify failure**

Run:

```bash
cd webapp && just test
```

Expected: FAIL with missing `ReaderStructureResponse` type.

- [ ] **Step 3: Add web types**

In `webapp/src/lib/reader.ts`, add:

```ts
export type ReaderStructureNode = {
    work_id: string;
    node_id: string;
    parent_node_id?: string | null;
    level: number;
    kind: string;
    object_type: string;
    label: string;
    native_label?: string | null;
    ordinal: number;
    start_citation: string;
    end_citation: string;
    provenance: string;
    confidence: string;
    status: string;
    note?: string;
    source_file?: string;
    canonical_text_id?: string | null;
    canonical_address?: string | null;
    summary?: string | null;
    short_label?: string | null;
    traditional_reference?: string | null;
    division_metadata_status?: string | null;
    division_review_status?: string | null;
    division_confidence?: string | null;
    division_evidence_count?: number | null;
    provenance_chips?: string[];
    word_count?: number;
    word_count_method?: string;
};

export type ReaderStructureResponse = {
    schema_version: string;
    mode: 'structure';
    catalog_path: string;
    request: {
        work_ref: string;
    };
    summary: {
        node_count: number;
        top_level_count: number;
        kinds: string[];
        has_division_metadata: boolean;
    };
    items: ReaderStructureNode[];
};
```

Add to `ReaderSegment`:

```ts
    current_divisions?: ReaderStructureNode[];
```

Add to `ReaderShowResponse`:

```ts
    current_divisions?: ReaderStructureNode[];
```

- [ ] **Step 4: Add server adapter**

In `webapp/src/lib/server/reader-cli.ts`, import `ReaderStructureResponse` and add:

```ts
export async function readerStructure({
    catalogId,
    language,
    work,
    options = {}
}: {
    catalogId: string | null;
    language?: LanguageMode;
    work: string;
    options?: ReaderCliOptions;
}): Promise<ReaderStructureResponse & { catalog: ReaderCatalog }> {
    const catalog = await resolveReaderCatalog(catalogId, language, options);
    const rawPayload = await runReaderJsonCommand(
        catalog,
        ['structure', work, '--output', 'json'],
        options
    );
    return {
        ...(withCatalog(rawPayload, catalog) as ReaderStructureResponse & { catalog: ReaderCatalog }),
        items: arrayOfObjects(rawPayload.items) as ReaderStructureResponse['items']
    };
}
```

- [ ] **Step 5: Add API mode**

In `webapp/src/routes/api/reader/+server.ts`:

Add import:

```ts
    readerStructure,
```

Add to `validModes`:

```ts
    'structure',
```

Add handler before `contents`:

```ts
        if (mode === 'structure') {
            const work = (url.searchParams.get('work') ?? '').trim();
            if (!work)
                return respond({ error: 'Reader structure requires a work parameter.' }, { status: 400 });
            return cachedRespond(await readerStructure({ catalogId, language, work, options }));
        }
```

- [ ] **Step 6: Run web tests**

Run:

```bash
cd webapp && just test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add webapp/src/lib/reader.ts webapp/src/lib/server/reader-cli.ts webapp/src/routes/api/reader/+server.ts webapp/src/lib/reader.test.ts
git commit -m "feat: add reader structure web contract"
```

---

### Task 9: Reader UI Structure Panel And Async State

**Files:**
- Modify: `webapp/src/lib/ui-copy.ts`
- Modify: `webapp/src/routes/reader/+page.svelte`
- Modify: `webapp/src/app.css`
- Test: `webapp/src/lib/reader-page-loading.test.ts`

- [ ] **Step 1: Add failing source-level UI test**

In `webapp/src/lib/reader-page-loading.test.ts`, add assertions that read `webapp/src/routes/reader/+page.svelte` and `webapp/src/app.css`:

```ts
assert.ok(pageSource.includes("let structure = $state<ReaderStructureNode[]>([])"));
assert.ok(pageSource.includes("mode: 'structure'"));
assert.ok(pageSource.includes("orion-reader-canon-table"));
assert.ok(pageSource.includes("orion-reader-provenance-chip"));
assert.ok(pageSource.includes("readerLoadingElapsed('structure')"));
assert.ok(cssSource.includes('.orion-reader-canon-table'));
assert.ok(cssSource.includes('.orion-reader-apparatus-sheet'));
```

- [ ] **Step 2: Run web test to verify failure**

Run:

```bash
cd webapp && just test
```

Expected: FAIL because structure UI state/classes are missing.

- [ ] **Step 3: Add localization keys**

In `webapp/src/lib/ui-copy.ts`, add resources:

```ts
readerStructure: {
    title: 'Structure',
    empty: 'No accepted structure map yet.',
    loading: 'Loading structure',
    open: 'Open',
    study: 'Study division',
    evidence: 'Evidence',
    current: 'Current division'
},
apparatus: {
    structure: 'Structure',
    word: 'Word',
    oracle: 'Oracle',
    evidence: 'Evidence',
    close: 'Close apparatus'
}
```

Expose them in `uiCopy`.

- [ ] **Step 4: Add state and loading timer key**

In `webapp/src/routes/reader/+page.svelte`:

Import types:

```ts
    type ReaderStructureNode,
    type ReaderStructureResponse,
```

Extend loading key:

```ts
type ReaderLoadingKey =
    | 'shelves'
    | 'library'
    | 'authors'
    | 'textSearch'
    | 'contents'
    | 'segment'
    | 'structure';
```

Add state:

```ts
let structure = $state<ReaderStructureNode[]>([]);
let structureLoading = $state(false);
let structureError = $state('');
let structureLoadingElapsedSeconds = $state(0);
let activeApparatusPanel = $state<'structure' | 'word' | 'oracle' | 'evidence' | ''>('');
```

Update timer setters:

```ts
else if (kind === 'structure') structureLoadingElapsedSeconds = seconds;
```

and getter:

```ts
if (kind === 'structure') return structureLoadingElapsedSeconds;
```

- [ ] **Step 5: Add structure fetch**

Add:

```ts
async function loadStructure(work: string) {
    if (!work || !catalogId) return;
    structureLoading = true;
    structureError = '';
    startReaderLoadingTimer('structure');
    try {
        const params = new URLSearchParams({
            mode: 'structure',
            catalog: catalogId,
            language,
            work,
            timeout_ms: '120000'
        });
        const response = await fetchPayload<ReaderStructureResponse>(`/api/reader?${params}`);
        const data = response.payload;
        if (!response.ok) throw new Error(data.error || 'Reader structure failed.');
        structure = data.items ?? [];
    } catch (error) {
        structureError = error instanceof Error ? error.message : 'Reader structure failed.';
    } finally {
        structureLoading = false;
        stopReaderLoadingTimer('structure');
    }
}
```

Call `await loadStructure(readerWorkRef(work))` inside `openWork` after `selectedWork = work`, and call it in route rehydration when a work is selected.

- [ ] **Step 6: Add Canon Table snippets**

Add snippets before markup:

```svelte
{#snippet provenanceChips(chips: string[] | undefined)}
    {#if chips?.length}
        <div class="orion-reader-provenance-row">
            {#each chips as chip}
                <span class="orion-reader-provenance-chip">{chip}</span>
            {/each}
        </div>
    {/if}
{/snippet}

{#snippet canonTable(items: ReaderStructureNode[])}
    <div class="orion-reader-canon-table">
        {#each items as item}
            <article class="orion-reader-division-card" style={`--division-depth: ${Math.max(0, item.level - 1)}`}>
                <div>
                    <span>{item.kind}</span>
                    <strong>{item.short_label || item.label}</strong>
                    {#if item.native_label}
                        <small>{item.native_label}</small>
                    {/if}
                </div>
                <div>
                    <span>{item.traditional_reference || item.start_citation}</span>
                    <small>{item.start_citation}..{item.end_citation}</small>
                </div>
                {#if item.summary}
                    <p>{item.summary}</p>
                {/if}
                {@render provenanceChips(item.provenance_chips)}
                <button type="button" class="btn btn-xs" onclick={() => showSegment(item.work_id, item.start_citation, 'push')}>
                    {uiCopy.readerStructure.open}
                </button>
            </article>
        {/each}
    </div>
{/snippet}
```

- [ ] **Step 7: Replace Book contents sidebar heading**

Change the sidebar panel title from hardcoded `Book contents` to `uiCopy.readerStructure.title`. Render:

```svelte
{#if structureLoading && !structure.length}
    {@render readerSkeletonRows(uiCopy.readerStructure.loading, 'structure', 'contents', 4)}
{:else if structureError}
    {@render readerErrorPanel('Structure failed to load', structureError, 'Load structure again', () => selectedWork && void loadStructure(readerWorkRef(selectedWork)))}
{:else if structure.length}
    {@render canonTable(structure)}
{:else if selectedWork}
    <p class="text-base-content/55 text-sm">{uiCopy.readerStructure.empty}</p>
{:else}
    <p class="text-base-content/55 text-sm">No book selected.</p>
{/if}
```

Keep the old segment `contents` list in a secondary details block named `Page segments` so exact segment navigation is not lost.

- [ ] **Step 8: Add CSS**

In `webapp/src/app.css`, add:

```css
.orion-reader-canon-table {
    display: grid;
    gap: 0.45rem;
    max-height: 28rem;
    overflow: auto;
}

.orion-reader-division-card {
    display: grid;
    gap: 0.35rem;
    border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
    border-left: 0.18rem solid color-mix(in oklab, var(--color-primary) 42%, var(--color-accent));
    border-radius: var(--radius-box);
    background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
    padding: 0.55rem;
    padding-left: calc(0.55rem + var(--division-depth, 0) * 0.7rem);
}

.orion-reader-division-card strong {
    display: block;
    color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
    font-family: var(--font-serif);
    font-size: 0.95rem;
    line-height: 1.2;
}

.orion-reader-division-card span,
.orion-reader-division-card small {
    color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
    font-size: 0.72rem;
    font-weight: 700;
}

.orion-reader-division-card p {
    color: color-mix(in oklab, var(--color-base-content) 68%, transparent);
    font-family: var(--font-serif);
    font-size: 0.82rem;
    line-height: 1.35;
}

.orion-reader-provenance-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.28rem;
}

.orion-reader-provenance-chip {
    border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
    border-radius: 0.25rem;
    background: color-mix(in oklab, var(--color-base-100) 78%, var(--color-accent) 8%);
    padding: 0.1rem 0.32rem;
    color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-primary));
    font-size: 0.66rem;
    font-weight: 800;
    line-height: 1.2;
}

.orion-reader-apparatus-sheet {
    display: none;
}
```

- [ ] **Step 9: Run web tests**

Run:

```bash
cd webapp && just test
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add webapp/src/lib/ui-copy.ts webapp/src/routes/reader/+page.svelte webapp/src/app.css webapp/src/lib/reader-page-loading.test.ts
git commit -m "feat: show reader structure canon table"
```

---

### Task 10: Mobile Apparatus Sheet

**Files:**
- Modify: `webapp/src/routes/reader/+page.svelte`
- Modify: `webapp/src/app.css`
- Test: `webapp/src/lib/reader-page-loading.test.ts`

- [ ] **Step 1: Add failing mobile apparatus assertions**

In `webapp/src/lib/reader-page-loading.test.ts`, add:

```ts
assert.ok(pageSource.includes('orion-reader-apparatus-tabs'));
assert.ok(pageSource.includes("activeApparatusPanel = 'structure'"));
assert.ok(pageSource.includes('orion-reader-apparatus-sheet open'));
assert.ok(cssSource.includes('@media (max-width: 48rem)'));
assert.ok(cssSource.includes('.orion-reader-apparatus-tabs'));
```

- [ ] **Step 2: Run web test to verify failure**

Run:

```bash
cd webapp && just test
```

Expected: FAIL until apparatus markup/CSS exists.

- [ ] **Step 3: Add mobile apparatus markup**

Near the end of `webapp/src/routes/reader/+page.svelte`, inside `<main>`, add:

```svelte
{#if selectedWork || selectedSegment || selectedWord}
    <nav class="orion-reader-apparatus-tabs" aria-label="Reader apparatus">
        <button type="button" onclick={() => (activeApparatusPanel = 'structure')}>
            <ScrollText size={15} />
            {uiCopy.apparatus.structure}
        </button>
        <button type="button" onclick={() => (activeApparatusPanel = 'word')}>
            <BookOpen size={15} />
            {uiCopy.apparatus.word}
        </button>
        <button type="button" onclick={() => (activeApparatusPanel = 'oracle')}>
            <Sparkles size={15} />
            {uiCopy.apparatus.oracle}
        </button>
        <button type="button" onclick={() => (activeApparatusPanel = 'evidence')}>
            <Database size={15} />
            {uiCopy.apparatus.evidence}
        </button>
    </nav>
{/if}

{#if activeApparatusPanel}
    <section class="orion-reader-apparatus-sheet open" aria-label="Reader apparatus sheet">
        <div class="orion-reader-apparatus-sheet-head">
            <strong>{activeApparatusPanel}</strong>
            <button type="button" class="btn btn-xs" onclick={() => (activeApparatusPanel = '')}>
                {uiCopy.apparatus.close}
            </button>
        </div>
        {#if activeApparatusPanel === 'structure'}
            {#if structure.length}
                {@render canonTable(structure)}
            {:else}
                <p>{uiCopy.readerStructure.empty}</p>
            {/if}
        {:else if activeApparatusPanel === 'word'}
            <p>{selectedWord || uiCopy.encounterBriefing.empty}</p>
        {:else if activeApparatusPanel === 'oracle'}
            <p>{selectedWordBriefingOutput?.short || uiCopy.encounterBriefing.empty}</p>
        {:else}
            <p>{selectedSegment?.canonical_address || selectedSegment?.address || selectedWork?.canonical_address || ''}</p>
        {/if}
    </section>
{/if}
```

- [ ] **Step 4: Add responsive CSS**

In `webapp/src/app.css`, add:

```css
@media (max-width: 48rem) {
    .orion-reader-shell {
        padding-bottom: 4.5rem;
    }

    .orion-reader-apparatus-tabs {
        position: fixed;
        z-index: 35;
        right: 0.75rem;
        bottom: 0.75rem;
        left: 0.75rem;
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.25rem;
        border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
        border-radius: var(--radius-box);
        background: color-mix(in oklab, var(--color-base-100) 94%, var(--color-base-200));
        padding: 0.3rem;
        box-shadow: 0 1rem 2rem color-mix(in oklab, var(--color-neutral) 18%, transparent);
    }

    .orion-reader-apparatus-tabs button {
        display: grid;
        justify-items: center;
        gap: 0.12rem;
        border: 0;
        border-radius: 0.35rem;
        background: transparent;
        padding: 0.32rem 0.2rem;
        color: color-mix(in oklab, var(--color-base-content) 68%, var(--color-primary));
        font-size: 0.68rem;
        font-weight: 750;
    }

    .orion-reader-apparatus-sheet {
        position: fixed;
        z-index: 40;
        right: 0;
        bottom: 0;
        left: 0;
        display: grid;
        max-height: min(78vh, 42rem);
        gap: 0.75rem;
        border-top: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
        border-radius: 0.65rem 0.65rem 0 0;
        background: var(--color-base-100);
        padding: 0.85rem;
        box-shadow: 0 -1rem 2.2rem color-mix(in oklab, var(--color-neutral) 20%, transparent);
        overflow: auto;
    }

    .orion-reader-apparatus-sheet-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        font-family: var(--font-serif);
        text-transform: capitalize;
    }
}
```

- [ ] **Step 5: Run web tests**

Run:

```bash
cd webapp && just test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add webapp/src/routes/reader/+page.svelte webapp/src/app.css webapp/src/lib/reader-page-loading.test.ts
git commit -m "feat: add mobile reader apparatus sheet"
```

---

### Task 11: Firecrawl-Backed Metadata Enrichment Pilot

**Files:**
- Create: `.firecrawl/reader-metadata/orion-structure-pilot/README.md`
- Create: `.firecrawl/reader-metadata/orion-structure-pilot/targets.json`
- Create: `.firecrawl/reader-metadata/orion-structure-pilot/bhagavadgita-chapter-9-search.json`
- Create: `.firecrawl/reader-metadata/orion-structure-pilot/bhagavadgita-chapter-9-source-1.md`
- Create: `.firecrawl/reader-metadata/orion-structure-pilot/plato-republic-book-10-search.json`
- Create: `.firecrawl/reader-metadata/orion-structure-pilot/plato-republic-book-10-source-1.md`
- Modify: `data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml`
- Optional modify: `data/curated/reader_work_maps/**`
- Optional modify: `data/curated/reader_aliases/**`

- [ ] **Step 1: Confirm Firecrawl availability**

Run:

```bash
firecrawl --status
```

Expected: command reports available credits or authenticated status. If it fails because credentials are unavailable, skip this task and leave a note in `.firecrawl/reader-metadata/orion-structure-pilot/README.md` after creating the directory.

- [ ] **Step 2: Create research batch directory and target list**

Run:

```bash
mkdir -p .firecrawl/reader-metadata/orion-structure-pilot
```

Create `.firecrawl/reader-metadata/orion-structure-pilot/targets.json` with:

```json
{
  "batch": "orion-structure-pilot",
  "purpose": "Source-backed work and chapter context for the Project Orion UI overhaul pilot.",
  "targets": [
    {
      "id": "bhagavadgita-chapter-9",
      "work_id": "urn:cts:sanskritLit:mbh.bhg",
      "node_id": "bhg-09",
      "query": "Bhagavad Gita chapter 9 Raja Vidya Raja Guhya Yoga summary source"
    },
    {
      "id": "plato-republic-book-10",
      "work_query": "Republic Plato Greek",
      "traditional_reference": "Republic Book 10",
      "query": "Plato Republic Book 10 Greek text Stephanus source"
    }
  ]
}
```

- [ ] **Step 3: Search for durable sources**

Run:

```bash
firecrawl search "Bhagavad Gita chapter 9 Raja Vidya Raja Guhya Yoga summary source" --limit 5 --json \
  -o ".firecrawl/reader-metadata/orion-structure-pilot/bhagavadgita-chapter-9-search.json"

firecrawl search "Plato Republic Book 10 Greek text Stephanus source" --limit 5 --json \
  -o ".firecrawl/reader-metadata/orion-structure-pilot/plato-republic-book-10-search.json"
```

Expected: JSON search result files exist. Prefer durable scholarly, institutional, library, or source-text pages over generic summaries.

- [ ] **Step 4: Scrape selected durable pages**

Start with these concrete durable targets, replacing either URL only if the search results from Step 3 show a stronger source or if Firecrawl reports that the page cannot be scraped:

```bash
firecrawl scrape "https://www.gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=9&field_nsutra_value=1" --only-main-content \
  -o ".firecrawl/reader-metadata/orion-structure-pilot/bhagavadgita-chapter-9-source-1.md"

firecrawl scrape "https://www.perseus.tufts.edu/hopper/text?doc=Plat.%20Rep.%2010" --only-main-content \
  -o ".firecrawl/reader-metadata/orion-structure-pilot/plato-republic-book-10-source-1.md"
```

Expected: markdown files contain source context relevant to the target. Do not paste long scraped prose into curated YAML. If a replacement URL is selected from search results, record that exact URL in the batch README before committing.

- [ ] **Step 5: Verify local catalog identity**

Run:

```bash
export CATALOG=data/build/reader/catalog.duckdb
test -f "$CATALOG" && just cli reader --catalog "$CATALOG" works --language san --query Bhagavadgita --limit 10 --output json || true
test -f "$CATALOG" && just cli reader --catalog "$CATALOG" works --language grc --query Republic --limit 10 --output json || true
test -f "$CATALOG" && just cli reader --catalog "$CATALOG" structure urn:cts:sanskritLit:mbh.bhg --output json || true
```

Expected when the catalog exists: the Bhagavadgita target resolves and Plato Republic candidates can be inspected. If the catalog is unavailable, continue only with `candidate` records and note the missing local identity check.

- [ ] **Step 6: Update curated metadata from research**

For Bhagavadgita chapter 9, update `data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml` only with concise, reviewed wording supported by the scraped source and local work map.

Use evidence items like:

```yaml
      - source_type: "web_source"
        citation: "https://www.gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=9&field_nsutra_value=1"
        label: "Source page used to corroborate the chapter title or context."
        retrieved_at: "2026-06-02"
```

For Plato Republic Book 10, write a `candidate` work map or alias record only if the local catalog identity and citation range are verified. If not verified, record the finding in the batch README and leave the YAML unchanged.

- [ ] **Step 7: Write batch notes**

Create `.firecrawl/reader-metadata/orion-structure-pilot/README.md`:

```markdown
# Orion Structure Pilot Research

## Targets

- Bhagavadgita chapter 9, `urn:cts:sanskritLit:mbh.bhg`, node `bhg-09`
- Plato Republic Book 10, local identity pending unless verified

## Sources Used

- `https://www.gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=9&field_nsutra_value=1`: source page used to corroborate the Bhagavadgita chapter 9 title and chapter context.
- `https://www.perseus.tufts.edu/hopper/text?doc=Plat.%20Rep.%2010`: source-text page used to inspect Republic Book 10 identity and citation range.

## Records Added Or Changed

- `data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml`: added or reviewed the BhG 9 division note with source-backed evidence.

## Follow Ups

- Verify Republic local work identity and range before accepting a work map.
```

- [ ] **Step 8: Run focused validation**

Run:

```bash
just test tests.test_reader_division_metadata
test -f data/build/reader/catalog.duckdb && just cli reader --catalog data/build/reader/catalog.duckdb sync-division-metadata --output json || true
```

Expected: tests pass. Sync command runs when the catalog exists.

- [ ] **Step 9: Commit**

```bash
git add .firecrawl/reader-metadata/orion-structure-pilot data/curated/reader_division_metadata/sanskrit/bhagavadgita.yaml
git commit -m "data: add reader structure research pilot"
```

---

### Task 12: Documentation And Contract Updates

**Files:**
- Modify: `docs/READER_WEB_CONTRACT.md`
- Modify: `webapp/docs/UI.md`
- Modify: `docs/READER_DATA_BUILD.md`
- Modify: `docs/READER_METADATA_ENRICHMENT_LOOP.md`

- [ ] **Step 1: Update reader web contract**

In `docs/READER_WEB_CONTRACT.md`, add `structure` to current `/api/reader` modes and add a "Structure" section with this content:

Heading:

```markdown
## Structure
```

Command example:

```bash
just cli reader --catalog $CATALOG structure urn:cts:sanskritLit:mbh.bhg --output json
```

Stable field list:

- `items[].work_id`
- `items[].node_id`
- `items[].parent_node_id`
- `items[].level`
- `items[].kind`
- `items[].object_type`
- `items[].label`
- `items[].native_label`
- `items[].ordinal`
- `items[].start_citation`
- `items[].end_citation`
- `items[].traditional_reference`
- `items[].summary`
- `items[].short_label`
- `items[].provenance_chips`
- `summary.node_count`
- `summary.top_level_count`
- `summary.kinds`
- `summary.has_division_metadata`

Closing note:

```markdown
`structure` is the UI-ready Canon Table contract. `map` remains the backward-compatible table-of-contents contract.
```

- [ ] **Step 2: Update UI docs**

In `webapp/docs/UI.md`, add an "Orion Structure Apparatus" section summarizing:

```markdown
- Library, Work Desk, Leaf, Word Desk, and Learn Desk are World places.
- Oracle actions answer from the current place.
- Structure uses Canon Table rows, not raw segment lists.
- Desktop keeps structure in the sticky apparatus.
- Mobile opens Structure, Word, Oracle, and Evidence through the Apparatus Sheet.
- Async states use skeletons for new content and one loading strip or badge with elapsed seconds for replacement.
```

- [ ] **Step 3: Update data build docs**

In `docs/READER_DATA_BUILD.md`, add `data/curated/reader_division_metadata` to the curated inputs list and builder command notes.

- [ ] **Step 4: Update metadata enrichment docs**

In `docs/READER_METADATA_ENRICHMENT_LOOP.md`, add division metadata to the curated data layers:

```markdown
- `data/curated/reader_division_metadata`: chapter, book, section, or other division bios, short labels, traditional references, generated/reviewed status, and evidence for UI object cards.
```

Clarify that Firecrawl artifacts under `.firecrawl/reader-metadata/orion-structure-pilot/` are audit scratch and should feed reviewed YAML or generated classification queues rather than runtime UI content.

- [ ] **Step 5: Run docs grep sanity**

Run:

```bash
rg -n "reader structure|division_metadata|Apparatus Sheet|Canon Table|Firecrawl" docs/READER_WEB_CONTRACT.md webapp/docs/UI.md docs/READER_DATA_BUILD.md docs/READER_METADATA_ENRICHMENT_LOOP.md
```

Expected: each document has at least one matching line.

- [ ] **Step 6: Commit**

```bash
git add docs/READER_WEB_CONTRACT.md webapp/docs/UI.md docs/READER_DATA_BUILD.md docs/READER_METADATA_ENRICHMENT_LOOP.md
git commit -m "docs: document reader structure contract"
```

---

### Task 13: Final Verification

**Files:**
- No source changes unless verification finds defects.

- [ ] **Step 1: Run backend targeted tests**

Run:

```bash
just test tests.test_reader_division_metadata
just test tests.test_reader_storage
just test tests.test_reader_enumeration
just test tests.test_reader_cli
```

Expected: PASS.

- [ ] **Step 2: Run web verification**

Run:

```bash
cd webapp && just verify
```

Expected: PASS.

- [ ] **Step 3: Run real CLI smoke when catalog exists**

Run:

```bash
test -f data/build/reader/catalog.duckdb && just cli reader structure urn:cts:sanskritLit:mbh.bhg --output json || true
```

Expected when catalog exists: JSON payload with `mode: "structure"`. Expected when catalog does not exist: command exits through `true` without blocking completion.

- [ ] **Step 4: Inspect git diff**

Run:

```bash
git status --short
git log --oneline -5
```

Expected: only intentional implementation files are dirty, or all task commits are present and the worktree contains only unrelated pre-existing edits.

- [ ] **Step 5: Request review**

Ask for a review focused on:

- generated text provenance labeling;
- old-catalog compatibility;
- mobile apparatus usability;
- citation range matching for non-numeric references;
- whether `structure` and `map` contracts remain clearly distinct.
