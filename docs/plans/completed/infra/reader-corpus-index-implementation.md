> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# Reader Corpus Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local reader corpus index over all supplied source trees, with a global catalog DB and per-book DuckDB files for exact enumeration, address lookup, and text retrieval.

**Architecture:** `@architect` owns the storage boundaries: a small `catalog.duckdb` enumerates collections/authors/works/artifacts and routes work/alias/address lookups to per-book DuckDB files under `data/build/reader/books/`. `@coder` implements focused adapters that emit normalized records for every supplied tree, including coarse fallback importers when perfect citation parsing is not available yet. `@auditor` verifies validation, duplicate alias handling, enumeration coverage, and read-only lookup behavior.

**Tech Stack:** Python dataclasses, Click, DuckDB, `xml.etree.ElementTree`, stdlib JSON/pathlib/hashlib, existing `just` test/lint commands. Alias files use a strict YAML subset parsed locally to avoid adding a new dependency.

## Current Verification Snapshot

- Perseus full generated catalog: `examples/debug/reader_perseus_full_current/catalog.duckdb`
- Latest verified stats: 1,223 works, 2,298 artifacts, 943,806 segments, 2,298 source files, 0 source errors.
- `reader validate --output json` returns no findings for the current Perseus catalog.
- Representative verified reads include Odyssey `urn:cts:greekLit:tlg0012.tlg002:3.74`, Livy `urn:cts:latinLit:phi0914.phi0011:1.pr.1`, Lucretius `urn:cts:latinLit:phi0550.phi001:1.1`, and Ammianus/Stoa contents enumeration.
- Remaining corpus-suite QA is focused on Sanskrit/DCS author authority, digilibLT metadata normalization, legacy PHI/TLG CTS bridging, and combined-suite inventory.

---

## File Structure

- Create `src/langnet/reader/__init__.py`: public reader package exports.
- Create `src/langnet/reader/models.py`: dataclasses for collections, authors, works, editions, book artifacts, segments, addresses, aliases, and build stats.
- Create `src/langnet/reader/paths.py`: reader catalog/book path helpers.
- Create `src/langnet/reader/alias_registry.py`: composed strict-YAML alias loader and validation helpers.
- Create `src/langnet/reader/storage.py`: catalog and per-book DuckDB schema/read/write helpers.
- Create `src/langnet/reader/adapters.py`: importer adapters for Perseus TEI, digilibLT TEI, PHI/TLG legacy dumps, Sanskrit JSON, Sanskrit plain/split/OCR text, translations, and DCS metadata files available in the supplied trees.
- Create `src/langnet/reader/builder.py`: orchestration for building catalog plus per-book DBs.
- Create `src/langnet/reader/service.py`: read-only query API for CLI commands.
- Modify `src/langnet/databuild/paths.py`: add reader build path helpers or delegate to `langnet.reader.paths`.
- Modify `src/langnet/cli_databuild.py`: add `databuild reader`.
- Modify `src/langnet/cli.py`: add `reader` command group.
- Create `data/curated/reader_aliases/greek/homer.yaml`: seed exact Homer aliases.
- Create `data/curated/reader_aliases/sanskrit/panini.yaml`: seed exact Sanskrit example alias.
- Create `tests/test_reader_alias_registry.py`.
- Create `tests/test_reader_storage.py`.
- Create `tests/test_reader_adapters.py`.
- Create `tests/test_reader_builder_cli.py`.
- Create `tests/test_reader_enumeration.py`.
- Create `tests/fixtures/reader/`: tiny TEI, Sanskrit JSON, legacy text, plain text, and alias fixtures.

## Task 1: Reader Models And Paths

**Files:**
- Create: `src/langnet/reader/__init__.py`
- Create: `src/langnet/reader/models.py`
- Create: `src/langnet/reader/paths.py`
- Modify: `src/langnet/databuild/paths.py`
- Test: `tests/test_reader_storage.py`

- [ ] **Step 1: Write the failing path/model test**

Add this to `tests/test_reader_storage.py`:

```python
from __future__ import annotations

from pathlib import Path

from langnet.reader.models import ReaderAlias, ReaderAuthor, ReaderSegment
from langnet.reader.paths import reader_book_path, reader_catalog_path, reader_root


def test_reader_paths_are_under_build_reader(tmp_path: Path) -> None:
    root = reader_root(tmp_path)
    assert root == tmp_path / "build" / "reader"
    assert reader_catalog_path(tmp_path) == tmp_path / "build" / "reader" / "catalog.duckdb"
    assert reader_book_path(
        tmp_path,
        collection="perseus",
        namespace="greekLit",
        author_id="tlg0012",
        work_id="tlg002",
        edition_id="perseus-grc2",
    ) == (
        tmp_path
        / "build"
        / "reader"
        / "books"
        / "perseus"
        / "greekLit"
        / "tlg0012"
        / "tlg002"
        / "perseus-grc2.duckdb"
    )


def test_reader_model_minimum_fields() -> None:
    segment = ReaderSegment(
        segment_id="seg-1",
        work_id="urn:cts:greekLit:tlg0012.tlg002",
        edition_id="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
        segment_kind="line",
        citation_path="3.74",
        text="ψυχὰς παρθέμενοι",
        normalized_text="ψυχας παρθεμενοι",
        sort_key=74,
    )
    alias = ReaderAlias(
        alias="Od.",
        language="grc",
        kind="work_abbreviation",
        target="urn:cts:greekLit:tlg0012.tlg002",
        display="Homer, Odyssey",
        source_file="tests/fixtures/reader/aliases/greek/homer.yaml",
        sources=("lsj", "manual"),
    )
    author = ReaderAuthor(
        author_id="urn:cts:greekLit:tlg0012",
        collection_id="perseus",
        language="grc",
        name="Homer",
        source_id="tlg0012",
    )
    assert segment.citation_path == "3.74"
    assert alias.target.endswith("tlg002")
    assert author.name == "Homer"
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
just test tests/test_reader_storage.py
```

Expected: failure importing `langnet.reader`.

- [ ] **Step 3: Implement models and paths**

Create `src/langnet/reader/__init__.py`:

```python
from __future__ import annotations

__all__ = [
    "models",
]
```

Create `src/langnet/reader/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReaderCollection:
    collection_id: str
    label: str
    source_root: Path | None = None


@dataclass(frozen=True)
class ReaderAuthor:
    author_id: str
    collection_id: str
    language: str
    name: str
    source_id: str


@dataclass(frozen=True)
class ReaderWork:
    work_id: str
    collection_id: str
    language: str
    title: str
    author: str
    source_id: str
    author_id: str | None = None
    cts_work_urn: str | None = None


@dataclass(frozen=True)
class ReaderEdition:
    edition_id: str
    work_id: str
    label: str
    language: str
    source_path: Path
    cts_edition_urn: str | None = None


@dataclass(frozen=True)
class ReaderBookArtifact:
    artifact_id: str
    work_id: str
    edition_id: str
    artifact_path: Path
    source_path: Path
    adapter: str
    source_hash: str
    segment_count: int = 0
    token_count: int = 0


@dataclass(frozen=True)
class ReaderSegment:
    segment_id: str
    work_id: str
    edition_id: str
    segment_kind: str
    citation_path: str
    text: str
    normalized_text: str
    sort_key: int


@dataclass(frozen=True)
class ReaderSegmentAddress:
    segment_id: str
    address: str
    address_kind: str
    citation_path: str


@dataclass(frozen=True)
class ReaderAlias:
    alias: str
    language: str
    kind: str
    target: str
    display: str
    source_file: str
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReaderBuildStats:
    catalog_path: str
    artifact_count: int
    work_count: int
    segment_count: int
    alias_count: int
```

Create `src/langnet/reader/paths.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

from langnet.databuild.paths import build_dir

_SAFE_PART_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_part(value: str) -> str:
    cleaned = _SAFE_PART_RE.sub("_", value.strip())
    return cleaned.strip("._") or "unknown"


def reader_root(data_root: Path | None = None) -> Path:
    base = data_root / "build" if data_root is not None else build_dir()
    return base / "reader"


def reader_catalog_path(data_root: Path | None = None) -> Path:
    return reader_root(data_root) / "catalog.duckdb"


def reader_books_dir(data_root: Path | None = None) -> Path:
    return reader_root(data_root) / "books"


def reader_book_path(
    data_root: Path | None = None,
    *,
    collection: str,
    namespace: str,
    author_id: str,
    work_id: str,
    edition_id: str,
) -> Path:
    return (
        reader_books_dir(data_root)
        / _safe_part(collection)
        / _safe_part(namespace)
        / _safe_part(author_id)
        / _safe_part(work_id)
        / f"{_safe_part(edition_id)}.duckdb"
    )
```

Modify `src/langnet/databuild/paths.py` by adding:

```python
def default_reader_catalog_path() -> Path:
    """
    Default output path for the reader catalog index.
    """
    return build_dir() / "reader" / "catalog.duckdb"
```

- [ ] **Step 4: Run the model/path test**

Run:

```bash
just test tests/test_reader_storage.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/langnet/reader/__init__.py src/langnet/reader/models.py src/langnet/reader/paths.py src/langnet/databuild/paths.py tests/test_reader_storage.py
git commit -m "feat: add reader models and paths"
```

## Task 2: Catalog And Book Storage

**Files:**
- Create: `src/langnet/reader/storage.py`
- Modify: `tests/test_reader_storage.py`

- [ ] **Step 1: Write storage tests**

Append to `tests/test_reader_storage.py`:

```python
import duckdb

from langnet.reader.models import (
    ReaderBookArtifact,
    ReaderEdition,
    ReaderSegmentAddress,
    ReaderWork,
)
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    lookup_artifact_for_address,
    lookup_segment_by_address,
    register_book,
    register_segment_rows,
)


def test_catalog_routes_address_to_book_db(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.duckdb"
    book_path = tmp_path / "book.duckdb"
    create_catalog_db(catalog_path)
    create_book_db(book_path)

    work = ReaderWork(
        work_id="urn:cts:greekLit:tlg0012.tlg002",
        collection_id="perseus",
        language="grc",
        title="Odyssey",
        author="Homer",
        source_id="tlg0012.tlg002",
        cts_work_urn="urn:cts:greekLit:tlg0012.tlg002",
    )
    edition = ReaderEdition(
        edition_id="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
        work_id=work.work_id,
        label="Perseus Greek edition",
        language="grc",
        source_path=tmp_path / "odyssey.xml",
        cts_edition_urn="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
    )
    artifact = ReaderBookArtifact(
        artifact_id="odyssey-grc2",
        work_id=work.work_id,
        edition_id=edition.edition_id,
        artifact_path=book_path,
        source_path=edition.source_path,
        adapter="fixture",
        source_hash="abc",
        segment_count=1,
    )
    register_book(catalog_path, work, edition, artifact)
    register_segment_rows(
        book_path,
        segments=[
            ReaderSegment(
                segment_id="od-3-74",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                segment_kind="line",
                citation_path="3.74",
                text="ψυχὰς παρθέμενοι",
                normalized_text="ψυχας παρθεμενοι",
                sort_key=74,
            )
        ],
        addresses=[
            ReaderSegmentAddress(
                segment_id="od-3-74",
                address="urn:cts:greekLit:tlg0012.tlg002:3.74",
                address_kind="cts",
                citation_path="3.74",
            )
        ],
    )

    routed = lookup_artifact_for_address(catalog_path, "urn:cts:greekLit:tlg0012.tlg002:3.74")
    assert routed == book_path
    row = lookup_segment_by_address(book_path, "urn:cts:greekLit:tlg0012.tlg002:3.74")
    assert row is not None
    assert row["text"] == "ψυχὰς παρθέμενοι"


def test_book_db_has_required_tables(tmp_path: Path) -> None:
    book_path = tmp_path / "book.duckdb"
    create_book_db(book_path)
    with duckdb.connect(str(book_path), read_only=True) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
    assert {"book_metadata", "segments", "segment_addresses", "tokens", "local_aliases"} <= tables
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
just test tests/test_reader_storage.py
```

Expected: failure importing `langnet.reader.storage`.

- [ ] **Step 3: Implement storage helpers**

Create `src/langnet/reader/storage.py` with catalog/book schema functions and lookup helpers. Use `duckdb.connect(str(path))`, create parent directories before writes, and return dictionaries from lookups.

Required public functions: `create_catalog_db`, `create_book_db`, `register_book`, `register_segment_rows`, `lookup_artifact_for_address`, and `lookup_segment_by_address`.

Use this exact catalog-routing query in `lookup_artifact_for_address`:

```sql
SELECT ba.artifact_path
FROM book_artifacts ba
JOIN editions e ON e.edition_id = ba.edition_id
JOIN works w ON w.work_id = ba.work_id
WHERE ? = w.cts_work_urn OR ? LIKE w.cts_work_urn || ':%'
ORDER BY LENGTH(w.cts_work_urn) DESC
LIMIT 1
```

Use this exact book lookup query in `lookup_segment_by_address`:

```sql
SELECT s.segment_id, s.segment_kind, s.citation_path, s.text, s.normalized_text
FROM segment_addresses a
JOIN segments s ON s.segment_id = a.segment_id
WHERE a.address = ?
LIMIT 1
```

- [ ] **Step 4: Run storage tests**

Run:

```bash
just test tests/test_reader_storage.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/langnet/reader/storage.py tests/test_reader_storage.py
git commit -m "feat: add reader catalog and book storage"
```

## Task 3: Composed Alias Registry

**Files:**
- Create: `src/langnet/reader/alias_registry.py`
- Create: `data/curated/reader_aliases/greek/homer.yaml`
- Create: `data/curated/reader_aliases/sanskrit/panini.yaml`
- Create: `tests/test_reader_alias_registry.py`

- [ ] **Step 1: Write alias tests**

Create `tests/test_reader_alias_registry.py`:

```python
from __future__ import annotations

from pathlib import Path

from langnet.reader.alias_registry import AliasConflict, load_aliases, validate_aliases


def test_loads_composed_alias_files(tmp_path: Path) -> None:
    root = tmp_path / "aliases"
    (root / "greek").mkdir(parents=True)
    (root / "greek" / "homer.yaml").write_text(
        '''
aliases:
  - alias: "Od."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:greekLit:tlg0012.tlg002"
    display: "Homer, Odyssey"
    sources: ["lsj", "manual"]
''',
        encoding="utf-8",
    )
    aliases = load_aliases(root)
    assert len(aliases) == 1
    assert aliases[0].alias == "Od."
    assert aliases[0].sources == ("lsj", "manual")


def test_validate_aliases_reports_conflicting_targets(tmp_path: Path) -> None:
    root = tmp_path / "aliases"
    root.mkdir()
    (root / "a.yaml").write_text(
        '''
aliases:
  - alias: "Cat."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:greekLit:tlg0086.tlg006"
    display: "Aristotle, Categories"
    sources: ["manual"]
  - alias: "Cat."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:latinLit:phi0474.phi001"
    display: "Catullus"
    sources: ["manual"]
''',
        encoding="utf-8",
    )
    conflicts = validate_aliases(load_aliases(root))
    assert conflicts == [
        AliasConflict(
            alias="Cat.",
            language="grc",
            targets=("urn:cts:greekLit:tlg0086.tlg006", "urn:cts:latinLit:phi0474.phi001"),
        )
    ]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
just test tests/test_reader_alias_registry.py
```

Expected: failure importing `langnet.reader.alias_registry`.

- [ ] **Step 3: Implement strict YAML alias loader**

Create `src/langnet/reader/alias_registry.py`. Implement a strict parser that supports only:

- top-level `aliases:`
- list items beginning `  - alias: "Od."`
- indented scalar keys `language`, `kind`, `target`, `display`
- inline list key `sources: ["a", "b"]`

Reject unsupported lines with `ValueError` naming the file and line number. Return `ReaderAlias` rows with `source_file` set to the YAML path.

Also create seed alias files:

`data/curated/reader_aliases/greek/homer.yaml`

```yaml
aliases:
  - alias: "Il."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:greekLit:tlg0012.tlg001"
    display: "Homer, Iliad"
    sources: ["lsj", "diogenes", "manual"]

  - alias: "Od."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:greekLit:tlg0012.tlg002"
    display: "Homer, Odyssey"
    sources: ["lsj", "diogenes", "manual"]
```

`data/curated/reader_aliases/sanskrit/panini.yaml`

```yaml
aliases:
  - alias: "Śivasūtra"
    language: "san"
    kind: "work_title"
    target: "langnet:reader:sanskrit:panini:sivasutra"
    display: "Pāṇini, Śivasūtra"
    sources: ["manual"]
```

- [ ] **Step 4: Run alias tests**

Run:

```bash
just test tests/test_reader_alias_registry.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/langnet/reader/alias_registry.py data/curated/reader_aliases tests/test_reader_alias_registry.py
git commit -m "feat: add reader alias registry"
```

## Task 4: Perseus TEI Adapter

**Files:**
- Create: `src/langnet/reader/adapters.py`
- Create: `tests/test_reader_adapters.py`
- Create: `tests/fixtures/reader/perseus_odyssey.xml`

- [ ] **Step 1: Add Perseus fixture and test**

Create `tests/fixtures/reader/perseus_odyssey.xml` with minimal TEI containing an edition div `urn:cts:greekLit:tlg0012.tlg002.perseus-grc2`, a book `n="3"`, and two line nodes `n="74"` and `n="75"`.

Create `tests/test_reader_adapters.py` with:

```python
from __future__ import annotations

from pathlib import Path

from langnet.reader.adapters import parse_perseus_tei


FIXTURES = Path("tests/fixtures/reader")


def test_parse_perseus_tei_builds_line_segments_and_cts_addresses() -> None:
    result = parse_perseus_tei(FIXTURES / "perseus_odyssey.xml")
    assert result.work.work_id == "urn:cts:greekLit:tlg0012.tlg002"
    assert result.edition.edition_id == "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2"
    assert result.segments[0].citation_path == "3.74"
    assert result.segments[0].text == "ψυχὰς παρθέμενοι"
    assert result.addresses[0].address == "urn:cts:greekLit:tlg0012.tlg002:3.74"
```

- [ ] **Step 2: Run adapter test to verify failure**

Run:

```bash
just test tests/test_reader_adapters.py
```

Expected: failure importing `parse_perseus_tei`.

- [ ] **Step 3: Implement `parse_perseus_tei`**

In `src/langnet/reader/adapters.py`, define `ParsedBook` and implement `parse_perseus_tei(path: Path) -> ParsedBook`.

The implementation must:

- parse TEI namespace with `xml.etree.ElementTree`
- find `div[@type='edition']`
- read its `n` as CTS edition URN
- derive work URN by removing the final edition component
- derive author/work IDs from the URN tail
- collect `div[@type='textpart']` ancestors and `l[@n]` line nodes
- create citation paths like `3.74`
- build CTS segment addresses like `<work_urn>:3.74`
- normalize text with Unicode NFKC and collapsed whitespace

- [ ] **Step 4: Run adapter tests**

Run:

```bash
just test tests/test_reader_adapters.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/langnet/reader/adapters.py tests/test_reader_adapters.py tests/fixtures/reader/perseus_odyssey.xml
git commit -m "feat: parse Perseus reader TEI"
```

## Task 5: Remaining Source Tree Adapters

**Files:**
- Modify: `src/langnet/reader/adapters.py`
- Modify: `tests/test_reader_adapters.py`
- Create: `tests/fixtures/reader/digiliblt_sample.xml`
- Create: `tests/fixtures/reader/sanskrit_raghuvamsa.json`
- Create: `tests/fixtures/reader/sanskrit_plain.txt`
- Create: `tests/fixtures/reader/phi_legacy.txt`

- [ ] **Step 1: Add digilibLT, Sanskrit, and legacy text tests**

Append tests that require:

```python
from langnet.reader.adapters import (
    parse_digiliblt_tei,
    parse_legacy_text_dump,
    parse_sanskrit_json,
    parse_sanskrit_plain_text,
)


def test_parse_digiliblt_tei_builds_paragraph_segments() -> None:
    result = parse_digiliblt_tei(FIXTURES / "digiliblt_sample.xml")
    assert result.work.collection_id == "digiliblt"
    assert result.work.title == "De controuersiis agrorum"
    assert result.segments[0].segment_kind == "paragraph"
    assert "aduersantur" in result.segments[0].text


def test_parse_sanskrit_json_builds_line_segments_from_tokens() -> None:
    result = parse_sanskrit_json(FIXTURES / "sanskrit_raghuvamsa.json")
    assert result.work.language == "san"
    assert result.work.title == "Raghuvaṃśa"
    assert result.segments[0].text == "vāc artha iva"
    assert result.segments[0].citation_path == "1"


def test_parse_sanskrit_plain_text_builds_retrievable_lines() -> None:
    result = parse_sanskrit_plain_text(
        FIXTURES / "sanskrit_plain.txt",
        collection_id="sanskrit_texts",
        language="san",
    )
    assert result.work.language == "san"
    assert result.segments[0].segment_kind == "line"
    assert result.segments[0].citation_path == "1"


def test_parse_legacy_text_dump_preserves_source_markers() -> None:
    result = parse_legacy_text_dump(
        FIXTURES / "phi_legacy.txt",
        collection_id="phi",
        language="lat",
    )
    assert result.work.collection_id == "phi"
    assert result.segments[0].segment_kind in {"section", "line"}
    assert result.segments[0].text
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
just test tests/test_reader_adapters.py
```

Expected: failure importing the new parser functions.

- [ ] **Step 3: Implement the adapters**

Add `parse_digiliblt_tei`, `parse_sanskrit_json`, `parse_sanskrit_plain_text`, and `parse_legacy_text_dump` functions.

`parse_digiliblt_tei` must read TEI `title`, `author`, publication `idno`, and `p` paragraphs. Use collection `digiliblt`, language `lat`, and LangNet reader addresses.

`parse_sanskrit_json` must read JSON keys `text`, `author`, `edition`, and `lines`. Convert each line list of token objects into a space-joined text segment using each token's `w` value. Use language `san`, collection `sanskrit_json`, and LangNet reader addresses.

`parse_sanskrit_plain_text` must import plain text, OCR, split text, and translation files as line or paragraph segments. It should derive a stable work ID from the path stem and preserve the source path in edition metadata.

`parse_legacy_text_dump` must import PHI/TLG text dumps even before perfect citation recovery exists. It should decode bytes with `utf-8` fallback to `latin-1`, strip NUL padding, preserve visible source markers in text, and split into non-empty line/section segments.

- [ ] **Step 4: Run adapter tests**

Run:

```bash
just test tests/test_reader_adapters.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/langnet/reader/adapters.py tests/test_reader_adapters.py tests/fixtures/reader/digiliblt_sample.xml tests/fixtures/reader/sanskrit_raghuvamsa.json tests/fixtures/reader/sanskrit_plain.txt tests/fixtures/reader/phi_legacy.txt
git commit -m "feat: parse reader supplement corpora"
```

## Task 6: Reader Builder

**Files:**
- Create: `src/langnet/reader/builder.py`
- Modify: `src/langnet/cli_databuild.py`
- Create: `tests/test_reader_builder_cli.py`

- [ ] **Step 1: Write builder test**

Create `tests/test_reader_builder_cli.py` with a direct builder test that uses fixture source directories and alias root, then asserts:

- `catalog.duckdb` exists
- one per-book DB exists for each fixture source family
- catalog has `book_artifacts` rows for Perseus, digilibLT, PHI/TLG legacy, Sanskrit JSON, and Sanskrit plain text fixtures
- catalog can enumerate Greek authors and works
- alias `Od.` is loaded
- address `urn:cts:greekLit:tlg0012.tlg002:3.74` routes to the book DB

- [ ] **Step 2: Run builder test to verify failure**

Run:

```bash
just test tests/test_reader_builder_cli.py
```

Expected: failure importing `ReaderBuilder`.

- [ ] **Step 3: Implement builder**

Create `ReaderBuildConfig` and `ReaderBuilder` in `src/langnet/reader/builder.py`.

Required config fields:

```python
perseus_dir: Path | None = None
digiliblt_dir: Path | None = None
phi_latin_dir: Path | None = None
tlg_e_dir: Path | None = None
sanskrit_dir: Path | None = None
alias_dir: Path | None = None
output_root: Path | None = None
limit: int | None = None
wipe_existing: bool = True
```

The builder should:

- create `catalog.duckdb`
- load aliases into catalog
- parse fixture/full source files through adapters for Perseus, digilibLT, PHI Latin, TLG Greek, Sanskrit JSON, Sanskrit text/OCR/split folders, translations, and DCS/CONLLU files covered by this plan
- write one per-book DB per parsed book
- register work, edition, and book artifact in the catalog
- return `BuildResult[ReaderBuildStats | BuildErrorStats]`

- [ ] **Step 4: Wire `databuild reader`**

Modify `src/langnet/cli_databuild.py`:

- add `BuildReaderConfig`
- add `_build_reader_impl`
- add `@databuild.command("reader")`
- options: `--perseus-dir`, `--digiliblt-dir`, `--phi-latin-dir`, `--tlg-e-dir`, `--sanskrit-dir`, `--alias-dir`, `--output-root`, `--limit`, `--wipe/--no-wipe`

- [ ] **Step 5: Run builder tests**

Run:

```bash
just test tests/test_reader_builder_cli.py
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/langnet/reader/builder.py src/langnet/cli_databuild.py tests/test_reader_builder_cli.py
git commit -m "feat: build reader corpus index"
```

## Task 7: Reader Service And CLI

**Files:**
- Create: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`
- Modify: `tests/test_reader_builder_cli.py`
- Create: `tests/test_reader_enumeration.py`
- Modify: `tests/test_cli_help.py`

- [ ] **Step 1: Write service/CLI tests**

Add tests for:

- `ReaderService.collections()`
- `ReaderService.authors(language="grc")`
- `ReaderService.works(language="grc")`
- `ReaderService.contents("Od.")`
- `ReaderService.show("urn:cts:greekLit:tlg0012.tlg002:3.74")`
- `ReaderService.show_work_segment("Od.", "3.74")`
- `ReaderService.resolve_address("Od. 3.74")`
- `langnet-cli reader --help` includes `collections`, `authors`, `works`, `contents`, `show`, `summary`, `aliases`, `alias-check`

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
just test tests/test_reader_builder_cli.py tests/test_reader_enumeration.py tests/test_cli_help.py
```

Expected: failure importing `ReaderService` or missing CLI group.

- [ ] **Step 3: Implement service**

Create `src/langnet/reader/service.py` with a `ReaderService` class exposing `collections`, `authors`, `works`, `contents`, `show`, `show_work_segment`, `resolve_address`, `summary`, `aliases`, and `alias_conflicts`.

`resolve_address("Od. 3.74")` should split the first whitespace token as alias, look up an exact alias target, append `:3.74` when the target is a CTS work URN, and call `show`.

`contents("Od.")` should resolve the work or alias through the catalog, open the relevant per-book DB, and return ordered segment metadata without dumping all text by default.

- [ ] **Step 4: Add CLI group**

Modify `src/langnet/cli.py`:

- add `@click.group("reader")`
- add subcommands `collections`, `authors`, `works`, `contents`, `show`, `resolve-address`, `summary`, `aliases`, `alias-check`
- support `--catalog-path`
- output pretty text by default and JSON with `--output json`
- register the group with `main.add_command(reader)`
- `reader show` should accept either one address argument or `reader show <work> --segment <path>`

- [ ] **Step 5: Run CLI tests**

Run:

```bash
just test tests/test_reader_builder_cli.py tests/test_reader_enumeration.py tests/test_cli_help.py
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/langnet/reader/service.py src/langnet/cli.py tests/test_reader_builder_cli.py tests/test_reader_enumeration.py tests/test_cli_help.py
git commit -m "feat: add reader CLI lookup"
```

## Task 8: Validation And Final Gates

**Files:**
- Modify: `src/langnet/reader/builder.py`
- Modify: `src/langnet/reader/service.py`
- Modify: `tests/test_reader_builder_cli.py`
- Modify: `README.md` or `data/README.md`

- [ ] **Step 1: Add validation tests**

Add tests that require:

- duplicate alias conflict is reported
- catalog artifact path missing is reported
- book DB missing required table is reported
- expected source families can be enumerated after a fixture build

- [ ] **Step 2: Implement validation**

Add `validate_reader_catalog(catalog_path: Path) -> list[dict[str, str]]` in `builder.py` or a focused `validation.py` if the module grows too large. Wire it to `databuild reader --validate-only` or `reader alias-check` if simpler.

- [ ] **Step 3: Document commands**

Update `data/README.md` with:

```markdown
- `build/reader/catalog.duckdb`: global reader corpus index.
- `build/reader/books/`: per-book DuckDB files used for direct segment lookup.
- `just cli-databuild reader --perseus-dir ~/perseus --digiliblt-dir ~/Classics-Data/digiliblt --phi-latin-dir ~/Classics-Data/phi-latin --tlg-e-dir ~/Classics-Data/tlg_e --sanskrit-dir ~/Classics-Data/sanskrit`: build local reader artifacts.
- `just cli reader collections`, `authors`, `works`, and `contents`: enumerate imported sources.
- `just cli reader show <address>`: retrieve one segment.
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
just test tests/test_reader_alias_registry.py tests/test_reader_storage.py tests/test_reader_adapters.py tests/test_reader_builder_cli.py tests/test_reader_enumeration.py tests/test_cli_help.py
```

Expected: pass.

- [ ] **Step 5: Run quality gates**

Run:

```bash
just ruff-check src/langnet/reader src/langnet/cli.py src/langnet/cli_databuild.py tests/test_reader_alias_registry.py tests/test_reader_storage.py tests/test_reader_adapters.py tests/test_reader_builder_cli.py tests/test_reader_enumeration.py
just typecheck src/langnet/reader
```

Expected: both commands exit 0. If `typecheck` does not accept a path in this repo, run `just typecheck` and record any unrelated pre-existing failures separately.

- [ ] **Step 6: Commit**

```bash
git add src/langnet/reader src/langnet/cli.py src/langnet/cli_databuild.py tests/test_reader_alias_registry.py tests/test_reader_storage.py tests/test_reader_adapters.py tests/test_reader_builder_cli.py tests/test_reader_enumeration.py tests/test_cli_help.py data/README.md
git commit -m "test: validate reader corpus index"
```
