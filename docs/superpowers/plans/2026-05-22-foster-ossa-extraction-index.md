# Foster Ossa Extraction Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, generated Foster Ossa extraction/index workflow that lets LangNet search and audit Foster concepts against page-backed PDF evidence.

**Architecture:** Add a small `langnet.foster_ossa` package for source-specific page extraction, structure detection, and summary planning. Add a DuckDB databuilder that imports generated JSONL into `data/build/foster_ossa.duckdb`, then expose extraction, search, concept lookup, encounter lookup, and summary dry-run commands through the existing Click CLI patterns.

**Tech Stack:** Python dataclasses, `orjson`, `duckdb`, `pyarrow`, Click, Poppler `pdftotext`, aisuite/OpenRouter for optional explicit summaries, `just cli`, `just cli-databuild`, pytest/nose2 via `just test`.

---

## File Map

- Create `src/langnet/foster_ossa/__init__.py`: package exports.
- Create `src/langnet/foster_ossa/models.py`: dataclasses and JSON helpers for pages, sections, encounters, concept mentions, and summary plans.
- Create `src/langnet/foster_ossa/extraction.py`: `pdftotext` runner and form-feed page parser.
- Create `src/langnet/foster_ossa/structure.py`: section classification, encounter detection, and concept mention extraction.
- Create `src/langnet/foster_ossa/summaries.py`: local summary chunk planning, prompt text, and explicit aisuite/OpenRouter call boundary.
- Create `src/langnet/databuild/foster_ossa.py`: DuckDB schema, builder, query helpers.
- Modify `src/langnet/databuild/base.py`: add `FosterOssaStats`.
- Modify `src/langnet/databuild/paths.py`: add `default_foster_ossa_path()`.
- Modify `src/langnet/cli_databuild.py`: add `databuild foster-ossa`.
- Modify `src/langnet/cli.py`: add `foster-ossa-extract`, `foster-ossa`, and `foster-ossa-summarize`.
- Modify `tests/test_cli_help.py`: include new commands.
- Create `tests/test_foster_ossa_extraction.py`: extraction, structure, and concept mention tests.
- Create `tests/test_foster_ossa_builder.py`: DuckDB builder and query tests.
- Create `tests/test_foster_ossa_cli.py`: CLI extraction/search/summary dry-run tests.
- Modify docs only after implementation if command names change from this plan.

## Task 1: Page Models And Text Extraction

**Files:**
- Create: `src/langnet/foster_ossa/__init__.py`
- Create: `src/langnet/foster_ossa/models.py`
- Create: `src/langnet/foster_ossa/extraction.py`
- Test: `tests/test_foster_ossa_extraction.py`

- [ ] **Step 1: Write failing page parser tests**

Create `tests/test_foster_ossa_extraction.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path

from langnet.foster_ossa.extraction import (
    extract_pdf_pages,
    iter_page_rows_from_pdftotext,
    write_page_rows_jsonl,
)


def test_iter_page_rows_from_pdftotext_splits_form_feed_pages() -> None:
    text = "\fTitle page\nOSSA LATINITATIS SOLA\n\fI Encounter 1 (1)\nFunctions produce true meaning.\n"

    pages = list(iter_page_rows_from_pdftotext(text, source_path=Path("ossa.pdf")))

    assert [page.page_number for page in pages] == [1, 2]
    assert pages[0].source_path == "ossa.pdf"
    assert pages[0].extraction_tool == "pdftotext"
    assert "OSSA LATINITATIS" in pages[0].text
    assert pages[0].text_hash
    assert pages[1].text.startswith("I Encounter 1")


def test_write_page_rows_jsonl_writes_one_json_object_per_page(tmp_path: Path) -> None:
    output = tmp_path / "foster-ossa-pages.jsonl"
    pages = list(
        iter_page_rows_from_pdftotext(
            "\fPreface\n\fI Encounter 1 (1)\nFirst text\n",
            source_path=Path("ossa.pdf"),
        )
    )

    write_page_rows_jsonl(pages, output)

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [row["page_number"] for row in rows] == [1, 2]
    assert rows[0]["source_path"] == "ossa.pdf"
    assert rows[1]["text"] == "I Encounter 1 (1)\nFirst text"


def test_extract_pdf_pages_uses_runner_output_without_real_pdf(tmp_path: Path) -> None:
    source = tmp_path / "ossa.pdf"
    source.write_bytes(b"%PDF synthetic")

    def runner(command: list[str]) -> str:
        assert command == ["pdftotext", "-layout", str(source), "-"]
        return "\fOne\n\fTwo\n"

    pages = list(extract_pdf_pages(source, runner=runner))

    assert [page.text for page in pages] == ["One", "Two"]
```

- [ ] **Step 2: Run extraction tests to verify failure**

Run:

```bash
just test tests/test_foster_ossa_extraction.py
```

Expected: FAIL because `langnet.foster_ossa` does not exist.

- [ ] **Step 3: Add package exports**

Create `src/langnet/foster_ossa/__init__.py`:

```python
"""Local generated indexes for Reginald Foster's Ossa Latinitatis Sola."""
```

- [ ] **Step 4: Add page dataclass and JSON helpers**

Create `src/langnet/foster_ossa/models.py`:

```python
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FosterOssaPage:
    page_number: int
    source_path: str
    extraction_tool: str
    text: str
    text_hash: str
    warning: str = ""

    @classmethod
    def from_text(
        cls,
        *,
        page_number: int,
        source_path: str,
        extraction_tool: str,
        text: str,
        warning: str = "",
    ) -> FosterOssaPage:
        normalized = text.strip()
        return cls(
            page_number=page_number,
            source_path=source_path,
            extraction_tool=extraction_tool,
            text=normalized,
            text_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            warning=warning,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 5: Add extraction functions**

Create `src/langnet/foster_ossa/extraction.py`:

```python
from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import orjson

from langnet.foster_ossa.models import FosterOssaPage

PdfTextRunner = Callable[[list[str]], str]


def run_pdftotext(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def iter_page_rows_from_pdftotext(
    text: str,
    *,
    source_path: Path,
) -> Iterator[FosterOssaPage]:
    raw_pages = text.split("\f")
    page_number = 0
    for raw_page in raw_pages:
        stripped = raw_page.strip()
        if not stripped:
            continue
        page_number += 1
        yield FosterOssaPage.from_text(
            page_number=page_number,
            source_path=str(source_path),
            extraction_tool="pdftotext",
            text=stripped,
        )


def extract_pdf_pages(
    source_path: Path,
    *,
    runner: PdfTextRunner = run_pdftotext,
) -> Iterator[FosterOssaPage]:
    expanded = source_path.expanduser()
    command = ["pdftotext", "-layout", str(expanded), "-"]
    text = runner(command)
    yield from iter_page_rows_from_pdftotext(text, source_path=expanded)


def write_page_rows_jsonl(pages: Iterable[FosterOssaPage], output_path: Path) -> int:
    expanded = output_path.expanduser()
    expanded.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with expanded.open("wb") as handle:
        for page in pages:
            handle.write(orjson.dumps(page.as_dict()))
            handle.write(b"\n")
            count += 1
    return count
```

- [ ] **Step 6: Run extraction tests**

Run:

```bash
just test tests/test_foster_ossa_extraction.py
```

Expected: PASS for the three extraction tests.

- [ ] **Step 7: Commit extraction foundation**

```bash
git add src/langnet/foster_ossa/__init__.py src/langnet/foster_ossa/models.py src/langnet/foster_ossa/extraction.py tests/test_foster_ossa_extraction.py
git commit -m "feat: add foster ossa page extraction"
```

## Task 2: Structure Detection And Concept Mentions

**Files:**
- Modify: `src/langnet/foster_ossa/models.py`
- Create: `src/langnet/foster_ossa/structure.py`
- Modify: `tests/test_foster_ossa_extraction.py`

- [ ] **Step 1: Add failing structure tests**

Append to `tests/test_foster_ossa_extraction.py`:

```python
from langnet.foster_ossa.structure import (
    classify_page_section,
    detect_concept_mentions,
    detect_encounters,
    structured_page_rows,
)


def test_classify_page_section_identifies_major_book_regions() -> None:
    assert classify_page_section(3, "THE MERE BONES OF LATIN") == "front_matter"
    assert classify_page_section(49, "PRIMA\nEXPERIENTIA\nfirst experience") == (
        "first_experience"
    )
    assert classify_page_section(165, "Reading Sheets—First Experience") == (
        "reading_sheets_first_experience"
    )
    assert classify_page_section(776, "BIBLIOGRAPHIA\nbibliography") == "bibliography"
    assert classify_page_section(823, "roles or cases and functions") == "indexes"


def test_detect_encounters_reads_experience_and_encounter_numbers() -> None:
    pages = list(
        iter_page_rows_from_pdftotext(
            "\fPRIMA EXPERIENTIA\n\fI Encounter 1 (1)\nFirst principles\n"
            "\fI Encounter 2 (2)\nNouns and functions\n",
            source_path=Path("ossa.pdf"),
        )
    )

    encounters = detect_encounters(pages)

    assert [(item.experience, item.encounter, item.page_start) for item in encounters] == [
        (1, 1, 2),
        (1, 2, 3),
    ]
    assert encounters[0].title == "First principles"


def test_detect_concept_mentions_finds_source_terms_with_context() -> None:
    page = FosterOssaPage.from_text(
        page_number=23,
        source_path="ossa.pdf",
        extraction_tool="pdftotext",
        text="The list of the seven functions includes nom. subject, acc. object, and gen. possession.",
    )

    mentions = detect_concept_mentions([page])

    normalized = {(mention.term, mention.category) for mention in mentions}
    assert ("nom.", "abbreviation") in normalized
    assert ("acc.", "abbreviation") in normalized
    assert ("gen.", "abbreviation") in normalized
    assert ("function", "method") in normalized
    assert all(mention.context for mention in mentions)


def test_structured_page_rows_add_section_without_mutating_text() -> None:
    pages = list(
        iter_page_rows_from_pdftotext(
            "\fTHE MERE BONES OF LATIN\n\fI Encounter 1 (1)\nFunctions produce true meaning.\n",
            source_path=Path("ossa.pdf"),
        )
    )

    rows = structured_page_rows(pages)

    assert rows[0].section == "front_matter"
    assert rows[1].section == "first_experience"
    assert rows[1].text == "I Encounter 1 (1)\nFunctions produce true meaning."
```

- [ ] **Step 2: Run structure tests to verify failure**

Run:

```bash
just test tests/test_foster_ossa_extraction.py
```

Expected: FAIL because structure dataclasses/functions do not exist.

- [ ] **Step 3: Add structure dataclasses**

Extend `src/langnet/foster_ossa/models.py`:

```python
@dataclass(frozen=True, slots=True)
class FosterOssaStructuredPage:
    page_number: int
    source_path: str
    extraction_tool: str
    section: str
    text: str
    text_hash: str
    warning: str = ""

    @classmethod
    def from_page(cls, page: FosterOssaPage, *, section: str) -> FosterOssaStructuredPage:
        return cls(
            page_number=page.page_number,
            source_path=page.source_path,
            extraction_tool=page.extraction_tool,
            section=section,
            text=page.text,
            text_hash=page.text_hash,
            warning=page.warning,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FosterOssaEncounter:
    encounter_id: str
    experience: int
    encounter: int
    page_start: int
    page_end: int
    heading: str
    title: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FosterOssaConceptMention:
    term: str
    normalized_term: str
    category: str
    page_number: int
    encounter_id: str | None
    context: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 4: Add structure detection**

Create `src/langnet/foster_ossa/structure.py`:

```python
from __future__ import annotations

import re
from collections.abc import Sequence

from langnet.foster_ossa.models import (
    FosterOssaConceptMention,
    FosterOssaEncounter,
    FosterOssaPage,
    FosterOssaStructuredPage,
)

EXPERIENCE_BY_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
ENCOUNTER_RE = re.compile(r"\b(?P<roman>I{1,3}|IV|V)\s+Encounter\s+(?P<n>\d+)\s+\(\d+\)")
CONCEPT_TERMS = {
    "nom.": "abbreviation",
    "acc.": "abbreviation",
    "gen.": "abbreviation",
    "dat.": "abbreviation",
    "abl.": "abbreviation",
    "voc.": "abbreviation",
    "loc.": "abbreviation",
    "function": "method",
    "functions": "method",
    "subject": "syntax",
    "object": "syntax",
    "Time 1": "verb_time",
    "Time 2": "verb_time",
    "T.1": "verb_time",
    "T.2": "verb_time",
}


def classify_page_section(page_number: int, text: str) -> str:
    lowered = text.casefold()
    if "bibliographia" in lowered or "bibliography" in lowered:
        return "bibliography"
    if "roles or cases and functions" in lowered or page_number >= 787:
        return "indexes"
    if "reading sheets—first experience" in lowered or "primae experientiae lectionum" in lowered:
        return "reading_sheets_first_experience"
    if "quinta experientia" in lowered or page_number >= 651:
        return "fifth_experience"
    if "quarta experientia" in lowered or page_number >= 455:
        return "fourth_experience"
    if "tertia experientia" in lowered or page_number >= 251:
        return "third_experience"
    if "secvnda experientia" in lowered or "secunda experientia" in lowered or page_number >= 201:
        return "second_experience"
    if "prima experientia" in lowered or "encounter" in lowered or page_number >= 49:
        return "first_experience"
    return "front_matter"


def structured_page_rows(pages: Sequence[FosterOssaPage]) -> list[FosterOssaStructuredPage]:
    return [
        FosterOssaStructuredPage.from_page(
            page,
            section=classify_page_section(page.page_number, page.text),
        )
        for page in pages
    ]


def detect_encounters(pages: Sequence[FosterOssaPage]) -> list[FosterOssaEncounter]:
    starts: list[tuple[int, re.Match[str], FosterOssaPage]] = []
    for page in pages:
        match = ENCOUNTER_RE.search(page.text)
        if match:
            starts.append((page.page_number, match, page))

    encounters: list[FosterOssaEncounter] = []
    for index, (page_number, match, page) in enumerate(starts):
        experience = EXPERIENCE_BY_ROMAN[match.group("roman")]
        encounter = int(match.group("n"))
        next_page = starts[index + 1][0] if index + 1 < len(starts) else page_number
        title = _first_content_line_after_heading(page.text, match.group(0))
        encounters.append(
            FosterOssaEncounter(
                encounter_id=f"{experience}.{encounter}",
                experience=experience,
                encounter=encounter,
                page_start=page_number,
                page_end=max(page_number, next_page - 1),
                heading=match.group(0),
                title=title,
            )
        )
    return encounters


def detect_concept_mentions(
    pages: Sequence[FosterOssaPage],
    encounters: Sequence[FosterOssaEncounter] | None = None,
) -> list[FosterOssaConceptMention]:
    mentions: list[FosterOssaConceptMention] = []
    for page in pages:
        encounter_id = _encounter_id_for_page(page.page_number, encounters or [])
        for term, category in CONCEPT_TERMS.items():
            pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
            for match in pattern.finditer(page.text):
                mentions.append(
                    FosterOssaConceptMention(
                        term=term,
                        normalized_term=_normalize_term(term),
                        category=category,
                        page_number=page.page_number,
                        encounter_id=encounter_id,
                        context=_context_window(page.text, match.start(), match.end()),
                    )
                )
    return mentions


def _first_content_line_after_heading(text: str, heading: str) -> str:
    tail = text.split(heading, 1)[1] if heading in text else text
    for line in tail.splitlines():
        stripped = line.strip(" \t—:-")
        if stripped:
            return stripped
    return ""


def _context_window(text: str, start: int, end: int, radius: int = 80) -> str:
    prefix = text[max(0, start - radius) : start]
    term = text[start:end]
    suffix = text[end : end + radius]
    return " ".join(f"{prefix}{term}{suffix}".split())


def _normalize_term(term: str) -> str:
    return term.strip(".").casefold().replace(" ", "_")


def _encounter_id_for_page(
    page_number: int,
    encounters: Sequence[FosterOssaEncounter],
) -> str | None:
    for encounter in encounters:
        if encounter.page_start <= page_number <= encounter.page_end:
            return encounter.encounter_id
    return None
```

- [ ] **Step 5: Run structure tests**

Run:

```bash
just test tests/test_foster_ossa_extraction.py
```

Expected: PASS.

- [ ] **Step 6: Commit structure detection**

```bash
git add src/langnet/foster_ossa/models.py src/langnet/foster_ossa/structure.py tests/test_foster_ossa_extraction.py
git commit -m "feat: detect foster ossa structure"
```

## Task 3: DuckDB Databuild

**Files:**
- Modify: `src/langnet/databuild/base.py`
- Modify: `src/langnet/databuild/paths.py`
- Create: `src/langnet/databuild/foster_ossa.py`
- Test: `tests/test_foster_ossa_builder.py`

- [ ] **Step 1: Write failing builder tests**

Create `tests/test_foster_ossa_builder.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from returns.result import Success

from langnet.databuild.foster_ossa import (
    FosterOssaBuildConfig,
    FosterOssaBuilder,
    lookup_concept_mentions,
    search_foster_ossa,
)
from langnet.databuild.paths import default_foster_ossa_path


def _write_pages(path: Path) -> None:
    rows = [
        {
            "page_number": 1,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "THE MERE BONES OF LATIN",
            "text_hash": "h1",
            "warning": "",
        },
        {
            "page_number": 2,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "I Encounter 1 (1)\nFunctions produce true meaning. nom. subject acc. object.",
            "text_hash": "h2",
            "warning": "",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_default_foster_ossa_path_is_build_duckdb() -> None:
    assert default_foster_ossa_path().name == "foster_ossa.duckdb"
    assert default_foster_ossa_path().parent.name == "build"


def test_foster_ossa_builder_imports_pages_structure_and_mentions(tmp_path: Path) -> None:
    source = tmp_path / "pages.jsonl"
    output = tmp_path / "foster_ossa.duckdb"
    _write_pages(source)

    result = FosterOssaBuilder(
        FosterOssaBuildConfig(source_path=source, output_path=output, wipe_existing=True)
    ).build()

    assert result.status.value == "success"
    assert isinstance(result.stats, Success)
    stats = result.stats.unwrap()
    assert stats.page_count == 2
    assert stats.encounter_count == 1
    assert stats.concept_mention_count >= 3

    search_rows = search_foster_ossa("true meaning", db_path=output)
    assert search_rows[0]["page_number"] == 2
    assert "Functions produce true meaning" in search_rows[0]["text"]

    concept_rows = lookup_concept_mentions("nom.", db_path=output)
    assert concept_rows[0]["term"] == "nom."
    assert concept_rows[0]["encounter_id"] == "1.1"
```

- [ ] **Step 2: Run builder tests to verify failure**

Run:

```bash
just test tests/test_foster_ossa_builder.py
```

Expected: FAIL because `langnet.databuild.foster_ossa` and path helper do not exist.

- [ ] **Step 3: Add stats and default path**

In `src/langnet/databuild/base.py`, add the dataclass before `BuildStats`:

```python
@dataclass(frozen=True)
class FosterOssaStats:
    path: str
    page_count: int | None = None
    section_count: int | None = None
    encounter_count: int | None = None
    concept_mention_count: int | None = None
    summary_count: int | None = None
    size_mb: float | None = None
```

Then update `BuildStats`:

```python
BuildStats = (
    CTSStats
    | CdslStats
    | LexiconStats
    | ReaderCorpusStats
    | FosterOssaStats
    | BuildErrorStats
)
```

In `src/langnet/databuild/paths.py`, add:

```python
def default_foster_ossa_path() -> Path:
    """
    Default output path for the local Foster Ossa extraction index.
    """
    return build_dir() / "foster_ossa.duckdb"
```

- [ ] **Step 4: Add Foster Ossa builder**

Create `src/langnet/databuild/foster_ossa.py`:

```python
from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
from returns.result import Failure, Success

from langnet.foster_ossa.models import FosterOssaPage
from langnet.foster_ossa.structure import (
    detect_concept_mentions,
    detect_encounters,
    structured_page_rows,
)

from .base import BuildErrorStats, BuildResult, BuildStatus, FosterOssaStats
from .paths import default_foster_ossa_path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pages (
    page_number INTEGER PRIMARY KEY,
    source_path VARCHAR NOT NULL,
    extraction_tool VARCHAR NOT NULL,
    section VARCHAR NOT NULL,
    text TEXT NOT NULL,
    text_hash VARCHAR NOT NULL,
    warning VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS sections (
    section VARCHAR PRIMARY KEY,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    page_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id VARCHAR PRIMARY KEY,
    experience INTEGER NOT NULL,
    encounter INTEGER NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    heading VARCHAR NOT NULL,
    title VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS concept_mentions (
    term VARCHAR NOT NULL,
    normalized_term VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    page_number INTEGER NOT NULL,
    encounter_id VARCHAR,
    context TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    summary_id VARCHAR PRIMARY KEY,
    scope VARCHAR NOT NULL,
    source_ref VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    prompt_version VARCHAR NOT NULL,
    input_hash VARCHAR NOT NULL,
    generated_text TEXT NOT NULL,
    validation_status VARCHAR NOT NULL
);

CREATE INDEX IF NOT EXISTS pages_text_idx ON pages(text);
CREATE INDEX IF NOT EXISTS concept_mentions_norm_idx ON concept_mentions(normalized_term);
CREATE INDEX IF NOT EXISTS concept_mentions_page_idx ON concept_mentions(page_number);
"""


@dataclass(frozen=True)
class FosterOssaBuildConfig:
    source_path: Path
    output_path: Path | None = None
    limit: int | None = None
    wipe_existing: bool = True
    force_rebuild: bool = False


class FosterOssaBuilder:
    def __init__(self, config: FosterOssaBuildConfig) -> None:
        self.source_path = config.source_path.expanduser()
        self.output_path = config.output_path or default_foster_ossa_path()
        self.limit = config.limit
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[FosterOssaStats | BuildErrorStats]:
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(f"Foster Ossa JSONL not found at {self.source_path}")
            if self.output_path.exists():
                if self.wipe_existing:
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.output_path))
            apply_foster_ossa_schema(self._conn)
            pages = list(self._iter_pages())
            self._insert_pages(pages)
            stats = self.get_stats()
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(stats),
            )
        except Exception as exc:  # noqa: BLE001
            return BuildResult(
                status=BuildStatus.FAILED,
                output_path=self.output_path,
                stats=Failure(BuildErrorStats(error=str(exc))),
                message=str(exc),
            )
        finally:
            self.cleanup()

    def _iter_pages(self) -> Iterator[FosterOssaPage]:
        count = 0
        with self.source_path.open(encoding="utf-8") as handle:
            for line_num, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                loaded = json.loads(stripped)
                if not isinstance(loaded, Mapping):
                    raise ValueError(f"Expected object on JSONL line {line_num}")
                yield FosterOssaPage(
                    page_number=int(loaded["page_number"]),
                    source_path=str(loaded["source_path"]),
                    extraction_tool=str(loaded["extraction_tool"]),
                    text=str(loaded["text"]),
                    text_hash=str(loaded["text_hash"]),
                    warning=str(loaded.get("warning") or ""),
                )
                count += 1
                if self.limit is not None and count >= self.limit:
                    break

    def _insert_pages(self, pages: Sequence[FosterOssaPage]) -> None:
        assert self._conn is not None
        structured = structured_page_rows(pages)
        encounters = detect_encounters(pages)
        mentions = detect_concept_mentions(pages, encounters)
        sections = _section_rows(structured)

        self._conn.register("page_batch", _arrow_table([page.as_dict() for page in structured]))
        self._conn.register("section_batch", _arrow_table(sections))
        self._conn.register("encounter_batch", _arrow_table([row.as_dict() for row in encounters]))
        self._conn.register("mention_batch", _arrow_table([row.as_dict() for row in mentions]))
        try:
            self._conn.execute(
                """
                INSERT INTO pages
                SELECT page_number, source_path, extraction_tool, section, text, text_hash, warning
                FROM page_batch
                """
            )
            if sections:
                self._conn.execute("INSERT INTO sections SELECT * FROM section_batch")
            if encounters:
                self._conn.execute("INSERT INTO encounters SELECT * FROM encounter_batch")
            if mentions:
                self._conn.execute("INSERT INTO concept_mentions SELECT * FROM mention_batch")
        finally:
            for name in ("page_batch", "section_batch", "encounter_batch", "mention_batch"):
                try:
                    self._conn.unregister(name)
                except duckdb.CatalogException:
                    pass

    def get_stats(self) -> FosterOssaStats:
        size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 3) if self.output_path.exists() else None
        if not self.output_path.exists():
            return FosterOssaStats(path=str(self.output_path), size_mb=size_mb)
        conn = self._conn or duckdb.connect(str(self.output_path), read_only=True)
        try:
            return FosterOssaStats(
                path=str(self.output_path),
                page_count=_count(conn, "pages"),
                section_count=_count(conn, "sections"),
                encounter_count=_count(conn, "encounters"),
                concept_mention_count=_count(conn, "concept_mentions"),
                summary_count=_count(conn, "summaries"),
                size_mb=size_mb,
            )
        finally:
            if conn is not self._conn:
                conn.close()

    def cleanup(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def apply_foster_ossa_schema(conn: duckdb.DuckDBPyConnection) -> None:
    for stmt in SCHEMA_SQL.strip().split(";"):
        sql_stmt = stmt.strip()
        if sql_stmt:
            conn.execute(sql_stmt)


def search_foster_ossa(
    query: str,
    *,
    db_path: Path | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    path = db_path or default_foster_ossa_path()
    conn = duckdb.connect(str(path.expanduser()), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT page_number, section, text
            FROM pages
            WHERE lower(text) LIKE ?
            ORDER BY page_number
            LIMIT ?
            """,
            [f"%{query.casefold()}%", limit],
        ).fetchall()
    finally:
        conn.close()
    return [{"page_number": row[0], "section": row[1], "text": row[2]} for row in rows]


def lookup_concept_mentions(
    term: str,
    *,
    db_path: Path | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    path = db_path or default_foster_ossa_path()
    normalized = term.strip(".").casefold().replace(" ", "_")
    conn = duckdb.connect(str(path.expanduser()), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT term, normalized_term, category, page_number, encounter_id, context
            FROM concept_mentions
            WHERE normalized_term = ?
            ORDER BY page_number
            LIMIT ?
            """,
            [normalized, limit],
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "term": row[0],
            "normalized_term": row[1],
            "category": row[2],
            "page_number": row[3],
            "encounter_id": row[4],
            "context": row[5],
        }
        for row in rows
    ]


def _section_rows(pages: Sequence[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[int]] = {}
    for page in pages:
        grouped.setdefault(page.section, []).append(page.page_number)
    return [
        {
            "section": section,
            "page_start": min(numbers),
            "page_end": max(numbers),
            "page_count": len(numbers),
        }
        for section, numbers in sorted(grouped.items(), key=lambda item: min(item[1]))
    ]


def _arrow_table(rows: Sequence[Mapping[str, Any]]) -> pa.Table:
    return pa.Table.from_pylist([dict(row) for row in rows])


def _count(conn: duckdb.DuckDBPyConnection, table: str) -> int:
    result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(result[0]) if result else 0
```

- [ ] **Step 5: Run builder tests**

Run:

```bash
just test tests/test_foster_ossa_builder.py
```

Expected: PASS.

- [ ] **Step 6: Commit builder**

```bash
git add src/langnet/databuild/base.py src/langnet/databuild/paths.py src/langnet/databuild/foster_ossa.py tests/test_foster_ossa_builder.py
git commit -m "feat: build foster ossa index"
```

## Task 4: Databuild And Inspection CLI

**Files:**
- Modify: `src/langnet/cli_databuild.py`
- Modify: `src/langnet/cli.py`
- Modify: `tests/test_cli_help.py`
- Create: `tests/test_foster_ossa_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_foster_ossa_cli.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from langnet.cli import main


def test_foster_ossa_extract_writes_jsonl_with_mocked_runner(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "ossa.pdf"
    output = tmp_path / "pages.jsonl"
    source.write_bytes(b"%PDF synthetic")

    def fake_extract_pdf_pages(path):
        from langnet.foster_ossa.extraction import iter_page_rows_from_pdftotext

        assert path == source
        return iter_page_rows_from_pdftotext("\fOne\n\fTwo\n", source_path=source)

    monkeypatch.setattr("langnet.foster_ossa.extraction.extract_pdf_pages", fake_extract_pdf_pages)

    result = CliRunner().invoke(
        main,
        ["foster-ossa-extract", "--source", str(source), "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert "wrote:" in result.output
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [row["page_number"] for row in rows] == [1, 2]


def test_foster_ossa_search_reads_built_db(tmp_path: Path) -> None:
    source = tmp_path / "pages.jsonl"
    db = tmp_path / "foster_ossa.duckdb"
    source.write_text(
        json.dumps(
            {
                "page_number": 1,
                "source_path": "ossa.pdf",
                "extraction_tool": "pdftotext",
                "text": "I Encounter 1 (1)\nFunctions produce true meaning. nom. subject.",
                "text_hash": "h1",
                "warning": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    build_result = CliRunner().invoke(
        main,
        ["databuild", "foster-ossa", "--source", str(source), "--output", str(db), "--wipe"],
    )
    assert build_result.exit_code == 0, build_result.output

    result = CliRunner().invoke(
        main,
        ["foster-ossa", "search", "true meaning", "--db", str(db), "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["results"][0]["page_number"] == 1


def test_foster_ossa_concept_lookup_outputs_mentions(tmp_path: Path) -> None:
    source = tmp_path / "pages.jsonl"
    db = tmp_path / "foster_ossa.duckdb"
    source.write_text(
        json.dumps(
            {
                "page_number": 1,
                "source_path": "ossa.pdf",
                "extraction_tool": "pdftotext",
                "text": "I Encounter 1 (1)\nnom. subject acc. object",
                "text_hash": "h1",
                "warning": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    CliRunner().invoke(
        main,
        ["databuild", "foster-ossa", "--source", str(source), "--output", str(db), "--wipe"],
    )

    result = CliRunner().invoke(
        main,
        ["foster-ossa", "concept", "nom.", "--db", str(db), "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mentions"][0]["term"] == "nom."
```

Extend `tests/test_cli_help.py`:

```python
def test_foster_ossa_command_help() -> None:
    _assert_help(["foster-ossa-extract"])
    _assert_help(["foster-ossa"])
    _assert_help(["foster-ossa", "search"])
    _assert_help(["foster-ossa", "concept"])
    _assert_help(["foster-ossa", "encounter"])
    _assert_help(["foster-ossa-summarize"])
    _assert_help(["databuild", "foster-ossa"])
```

- [ ] **Step 2: Run CLI tests to verify failure**

Run:

```bash
just test tests/test_foster_ossa_cli.py tests/test_cli_help.py
```

Expected: FAIL because commands do not exist.

- [ ] **Step 3: Wire databuild command**

In `src/langnet/cli_databuild.py`, add:

```python
@dataclass
class BuildFosterOssaConfig:
    source_path: str
    output: str | None
    limit: int | None
    wipe: bool
    force: bool
```

Add implementation helper:

```python
def _build_foster_ossa_impl(config: BuildFosterOssaConfig) -> None:
    _ensure_logging()
    from langnet.databuild.foster_ossa import FosterOssaBuildConfig, FosterOssaBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_foster_ossa_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_foster_ossa_path()
    builder_config = FosterOssaBuildConfig(
        source_path=Path(config.source_path).expanduser(),
        output_path=output_path,
        limit=config.limit,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    result = FosterOssaBuilder(builder_config).build()
    _print_build_result(result)
```

Add command under `databuild`:

```python
@databuild.command("foster-ossa")
@click.option(
    "--source",
    "source_path",
    type=click.Path(exists=True),
    required=True,
    help="Path to PDF-derived Foster Ossa page JSONL.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/foster_ossa.duckdb)",
)
@click.option("--limit", type=int, help="Limit pages for testing.")
@click.option(
    "--wipe/--no-wipe",
    default=True,
    show_default=True,
    help="Delete existing DB before building.",
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_foster_ossa(
    source_path: str,
    output: str | None,
    limit: int | None,
    wipe: bool,
    force: bool,
) -> None:
    """Build local Foster Ossa extraction index from page JSONL."""
    config = BuildFosterOssaConfig(
        source_path=source_path,
        output=output,
        limit=limit,
        wipe=wipe,
        force=force,
    )
    _build_foster_ossa_impl(config)
```

- [ ] **Step 4: Wire top-level extraction and inspection commands**

In `src/langnet/cli.py`, add these command functions before `main.add_command(index)`:

```python
@main.command("foster-ossa-extract")
@click.option(
    "--source",
    "source_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to local Ossa Latinitatis Sola PDF.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output page JSONL path.",
)
def foster_ossa_extract(source_path: Path, output: Path) -> None:
    """Extract Foster Ossa PDF pages to local generated JSONL."""
    from langnet.foster_ossa.extraction import (  # noqa: PLC0415
        extract_pdf_pages,
        write_page_rows_jsonl,
    )

    count = write_page_rows_jsonl(extract_pdf_pages(source_path), output)
    click.echo(f"wrote: {output.expanduser()} pages={count}")


@click.group("foster-ossa")
def foster_ossa() -> None:
    """Inspect the local Foster Ossa extraction index."""


@foster_ossa.command("search")
@click.argument("query")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option("--limit", type=int, default=10, show_default=True)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
)
def foster_ossa_search(query: str, db_path: Path | None, limit: int, output: str) -> None:
    """Search page text in the local Foster Ossa index."""
    from langnet.databuild.foster_ossa import search_foster_ossa  # noqa: PLC0415

    results = search_foster_ossa(query, db_path=db_path, limit=limit)
    if output == "json":
        click.echo(orjson.dumps({"results": results}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    for row in results:
        click.echo(f"p. {row['page_number']} [{row['section']}]")
        click.echo(str(row["text"]).replace("\n", " ")[:240])


@foster_ossa.command("concept")
@click.argument("term")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option("--limit", type=int, default=20, show_default=True)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
)
def foster_ossa_concept(term: str, db_path: Path | None, limit: int, output: str) -> None:
    """Show page-backed concept mentions from the Foster Ossa index."""
    from langnet.databuild.foster_ossa import lookup_concept_mentions  # noqa: PLC0415

    mentions = lookup_concept_mentions(term, db_path=db_path, limit=limit)
    if output == "json":
        click.echo(orjson.dumps({"mentions": mentions}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    for mention in mentions:
        encounter = mention.get("encounter_id") or "-"
        click.echo(f"p. {mention['page_number']} encounter={encounter} {mention['term']}")
        click.echo(f"  {mention['context']}")


@foster_ossa.command("encounter")
@click.argument("encounter_id")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
)
def foster_ossa_encounter(encounter_id: str, db_path: Path | None, output: str) -> None:
    """Show a Foster Ossa encounter summary row and page span."""
    from langnet.databuild.foster_ossa import lookup_encounter  # noqa: PLC0415

    row = lookup_encounter(encounter_id, db_path=db_path)
    if output == "json":
        click.echo(orjson.dumps({"encounter": row}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    if row is None:
        click.echo(f"No Foster Ossa encounter found for {encounter_id!r}.")
        return
    click.echo(f"{row['encounter_id']}: {row['heading']} pages {row['page_start']}-{row['page_end']}")
    if row["title"]:
        click.echo(f"  {row['title']}")


main.add_command(foster_ossa)
```

Also add `lookup_encounter()` to `src/langnet/databuild/foster_ossa.py`:

```python
def lookup_encounter(
    encounter_id: str,
    *,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    path = db_path or default_foster_ossa_path()
    conn = duckdb.connect(str(path.expanduser()), read_only=True)
    try:
        row = conn.execute(
            """
            SELECT encounter_id, experience, encounter, page_start, page_end, heading, title
            FROM encounters
            WHERE encounter_id = ?
            """,
            [encounter_id],
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "encounter_id": row[0],
        "experience": row[1],
        "encounter": row[2],
        "page_start": row[3],
        "page_end": row[4],
        "heading": row[5],
        "title": row[6],
    }
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
just test tests/test_foster_ossa_cli.py tests/test_cli_help.py
```

Expected: PASS.

- [ ] **Step 6: Commit CLI wiring**

```bash
git add src/langnet/cli.py src/langnet/cli_databuild.py src/langnet/databuild/foster_ossa.py tests/test_cli_help.py tests/test_foster_ossa_cli.py
git commit -m "feat: add foster ossa cli"
```

## Task 5: Summary Planning And Explicit LLM Boundary

**Files:**
- Create: `src/langnet/foster_ossa/summaries.py`
- Modify: `src/langnet/cli.py`
- Modify: `tests/test_foster_ossa_cli.py`
- Test: `tests/test_foster_ossa_extraction.py`

- [ ] **Step 1: Add failing summary plan tests**

Append to `tests/test_foster_ossa_extraction.py`:

```python
from langnet.foster_ossa.summaries import plan_summary_chunks


def test_plan_summary_chunks_is_local_and_hashes_inputs() -> None:
    rows = [
        {"page_number": 1, "text": "First page text", "text_hash": "h1"},
        {"page_number": 2, "text": "Second page text", "text_hash": "h2"},
    ]

    plans = plan_summary_chunks(rows, scope="page", model="openai:test-model")

    assert [plan.source_ref for plan in plans] == ["page:1", "page:2"]
    assert plans[0].model == "openai:test-model"
    assert plans[0].prompt_version == "foster-ossa-summary-v1"
    assert plans[0].input_hash
    assert "First page text" in plans[0].input_text
```

Append to `tests/test_foster_ossa_cli.py`:

```python
def test_foster_ossa_summarize_dry_run_does_not_require_api_key(tmp_path: Path) -> None:
    source = tmp_path / "pages.jsonl"
    db = tmp_path / "foster_ossa.duckdb"
    output = tmp_path / "summaries.jsonl"
    source.write_text(
        json.dumps(
            {
                "page_number": 1,
                "source_path": "ossa.pdf",
                "extraction_tool": "pdftotext",
                "text": "I Encounter 1 (1)\nFunctions produce true meaning.",
                "text_hash": "h1",
                "warning": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    CliRunner().invoke(
        main,
        ["databuild", "foster-ossa", "--source", str(source), "--output", str(db), "--wipe"],
    )

    result = CliRunner().invoke(
        main,
        [
            "foster-ossa-summarize",
            "--db",
            str(db),
            "--scope",
            "page",
            "--model",
            "openai:test-model",
            "--output",
            str(output),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "planned:" in result.output
    row = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
    assert row["source_ref"] == "page:1"
    assert row["generated_text"] == ""
    assert row["validation_status"] == "planned"
```

- [ ] **Step 2: Run summary tests to verify failure**

Run:

```bash
just test tests/test_foster_ossa_extraction.py tests/test_foster_ossa_cli.py
```

Expected: FAIL because summary functions and CLI command do not exist.

- [ ] **Step 3: Add summary models**

Extend `src/langnet/foster_ossa/models.py`:

```python
@dataclass(frozen=True, slots=True)
class FosterOssaSummaryPlan:
    source_ref: str
    scope: str
    model: str
    prompt_version: str
    input_hash: str
    input_text: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 4: Add summary planning module**

Create `src/langnet/foster_ossa/summaries.py`:

```python
from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from typing import Any

import aisuite as ai

from langnet.foster_ossa.models import FosterOssaSummaryPlan

PROMPT_VERSION = "foster-ossa-summary-v1"
SUMMARY_SYSTEM_PROMPT = (
    "You summarize local extracted text from Reginald Foster's Ossa Latinitatis Sola "
    "for internal source-audit tooling. Be conservative. Use only the supplied text. "
    "Separate Foster wording from paraphrase. Keep the summary short and cite the "
    "source_ref supplied by the tool."
)


def plan_summary_chunks(
    rows: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    model: str,
) -> list[FosterOssaSummaryPlan]:
    plans: list[FosterOssaSummaryPlan] = []
    for row in rows:
        source_ref = _source_ref(row, scope)
        input_text = str(row.get("text") or "")
        plans.append(
            FosterOssaSummaryPlan(
                source_ref=source_ref,
                scope=scope,
                model=model,
                prompt_version=PROMPT_VERSION,
                input_hash=hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
                input_text=input_text,
            )
        )
    return plans


def summarize_plan(plan: FosterOssaSummaryPlan) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY before generating Foster Ossa summaries.")
    api_base = os.getenv("OPENAI_API_BASE", os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"))
    os.environ["OPENAI_BASE_URL"] = api_base
    client = ai.Client({"api_key": api_key})
    response = client.chat.completions.create(
        model=plan.model,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"source_ref: {plan.source_ref}\n\n{plan.input_text}",
            },
        ],
    )
    return response.choices[0].message.content or ""


def _source_ref(row: Mapping[str, Any], scope: str) -> str:
    if scope == "page":
        return f"page:{row['page_number']}"
    if scope == "encounter":
        return f"encounter:{row.get('encounter_id', '')}"
    return f"{scope}:{row.get('page_number', row.get('source_ref', 'unknown'))}"
```

- [ ] **Step 5: Add summary query helper**

Add to `src/langnet/databuild/foster_ossa.py`:

```python
def page_rows_for_summary(
    *,
    db_path: Path | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    path = db_path or default_foster_ossa_path()
    conn = duckdb.connect(str(path.expanduser()), read_only=True)
    params: list[Any] = []
    limit_sql = ""
    if limit is not None:
        limit_sql = " LIMIT ?"
        params.append(limit)
    try:
        rows = conn.execute(
            f"""
            SELECT page_number, section, text, text_hash
            FROM pages
            ORDER BY page_number
            {limit_sql}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [
        {"page_number": row[0], "section": row[1], "text": row[2], "text_hash": row[3]}
        for row in rows
    ]
```

- [ ] **Step 6: Add summary CLI command**

In `src/langnet/cli.py`, add:

```python
@main.command("foster-ossa-summarize")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option(
    "--scope",
    type=click.Choice(["page"], case_sensitive=False),
    default="page",
    show_default=True,
)
@click.option(
    "--model",
    default="openai:deepseek/deepseek-v4-flash",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output local summary JSONL path.",
)
@click.option("--limit", type=int, help="Limit source rows for testing.")
@click.option("--dry-run", is_flag=True, help="Plan chunks without calling OpenRouter.")
def foster_ossa_summarize(
    db_path: Path | None,
    scope: str,
    model: str,
    output: Path,
    limit: int | None,
    dry_run: bool,
) -> None:
    """Generate or plan local Foster Ossa LLM summaries."""
    from langnet.databuild.foster_ossa import page_rows_for_summary  # noqa: PLC0415
    from langnet.foster_ossa.summaries import plan_summary_chunks, summarize_plan  # noqa: PLC0415

    rows = page_rows_for_summary(db_path=db_path, limit=limit)
    plans = plan_summary_chunks(rows, scope=scope, model=model)
    output_path = output.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        for plan in plans:
            generated_text = "" if dry_run else summarize_plan(plan)
            row = {
                "source_ref": plan.source_ref,
                "scope": plan.scope,
                "model": plan.model,
                "prompt_version": plan.prompt_version,
                "input_hash": plan.input_hash,
                "generated_text": generated_text,
                "validation_status": "planned" if dry_run else "generated",
            }
            handle.write(orjson.dumps(row))
            handle.write(b"\n")
    click.echo(f"planned: {len(plans)} summaries -> {output_path}")
```

- [ ] **Step 7: Run summary tests**

Run:

```bash
just test tests/test_foster_ossa_extraction.py tests/test_foster_ossa_cli.py tests/test_cli_help.py
```

Expected: PASS.

- [ ] **Step 8: Commit summary boundary**

```bash
git add src/langnet/foster_ossa/models.py src/langnet/foster_ossa/summaries.py src/langnet/databuild/foster_ossa.py src/langnet/cli.py tests/test_foster_ossa_extraction.py tests/test_foster_ossa_cli.py tests/test_cli_help.py
git commit -m "feat: plan foster ossa summaries"
```

## Task 6: Real PDF Smoke Verification And Documentation

**Files:**
- Modify: `docs/OUTPUT_GUIDE.md`
- Modify: `docs/PEDAGOGICAL_PHILOSOPHY.md`
- Optional local generated files under ignored `examples/debug/` and `data/build/`

- [ ] **Step 1: Add output guide note**

Add this section to `docs/OUTPUT_GUIDE.md` near other local databuild/index commands:

````markdown
## Foster Ossa Local Index

The Foster Ossa workflow builds local generated artifacts from a local copy of
`Ossa Latinitatis Sola`. The PDF and extracted full text are not committed.

```bash
just cli foster-ossa-extract \
  --source ~/reginald-foster/reginald-foster-latin.pdf \
  --output examples/debug/foster-ossa-pages.jsonl

just cli-databuild foster-ossa \
  --source examples/debug/foster-ossa-pages.jsonl \
  --output data/build/foster_ossa.duckdb \
  --wipe

just cli foster-ossa search "function"
just cli foster-ossa concept "nom."
just cli foster-ossa-summarize \
  --db data/build/foster_ossa.duckdb \
  --scope page \
  --output examples/debug/foster-ossa-summaries.jsonl \
  --dry-run
```

LLM summaries are generated metadata. Use page references and extracted source
rows as evidence; do not treat summaries as authoritative Foster wording.
````

- [ ] **Step 2: Add philosophy note**

In `docs/PEDAGOGICAL_PHILOSOPHY.md`, add one paragraph under "Foster Display Vocabulary":

```markdown
The local Foster Ossa index is the source-audit layer for this vocabulary. Use
it to distinguish wording directly supported by Foster's published method from
LangNet's own normalized overlay labels. Generated summaries can help triage
the material, but page-backed extracted text remains the evidence layer.
```

- [ ] **Step 3: Run docs and Foster tests**

Run:

```bash
just test tests/test_foster_ossa_extraction.py tests/test_foster_ossa_builder.py tests/test_foster_ossa_cli.py tests/test_cli_help.py
```

Expected: PASS.

- [ ] **Step 4: Run real local extraction smoke**

Run:

```bash
just cli foster-ossa-extract \
  --source ~/reginald-foster/reginald-foster-latin.pdf \
  --output examples/debug/foster-ossa-pages.jsonl
```

Expected: command reports roughly `pages=879`. Generated file is ignored by git.

- [ ] **Step 5: Run real local databuild smoke**

Run:

```bash
just cli-databuild foster-ossa \
  --source examples/debug/foster-ossa-pages.jsonl \
  --output data/build/foster_ossa.duckdb \
  --wipe
```

Expected: `status: success`, nonzero `page_count`, nonzero `encounter_count`, nonzero `concept_mention_count`.

- [ ] **Step 6: Run inspection smoke**

Run:

```bash
just cli foster-ossa search "Functions produce true meaning" --db data/build/foster_ossa.duckdb
just cli foster-ossa concept "nom." --db data/build/foster_ossa.duckdb --limit 5
just cli foster-ossa-summarize \
  --db data/build/foster_ossa.duckdb \
  --scope page \
  --limit 2 \
  --output examples/debug/foster-ossa-summaries.jsonl \
  --dry-run
```

Expected: search and concept commands print page-backed rows; summary command writes planned rows without requiring `OPENAI_API_KEY`.

- [ ] **Step 7: Run focused quality gates**

Run:

```bash
just ruff-check src/langnet/foster_ossa src/langnet/databuild/foster_ossa.py tests/test_foster_ossa_extraction.py tests/test_foster_ossa_builder.py tests/test_foster_ossa_cli.py
just typecheck
```

Expected: PASS, or existing unrelated typecheck failures are documented with exact failing files.

- [ ] **Step 8: Commit docs and verification-ready implementation**

```bash
git add docs/OUTPUT_GUIDE.md docs/PEDAGOGICAL_PHILOSOPHY.md
git commit -m "docs: document foster ossa index workflow"
```

## Self-Review

- Spec coverage: extraction, generated artifacts, DuckDB indexing, inspection commands, local-only defaults, and optional aisuite/OpenRouter summaries are each covered by a task.
- Source/artifact policy: the plan commits code/tests/docs only; real PDF extraction outputs stay in ignored `examples/debug/` and `data/build/`.
- LLM boundary: Task 5 requires dry-run and explicit summary command before any OpenRouter call.
- Type consistency: models use `FosterOssaPage`, `FosterOssaStructuredPage`, `FosterOssaEncounter`, `FosterOssaConceptMention`, and `FosterOssaSummaryPlan` consistently across extraction, builder, and CLI tasks.
- No placeholders: all implementation steps include concrete paths, snippets, commands, and expected outcomes.
