# Foster Ossa Extraction And Index Design

## Purpose

LangNet needs a source-backed Foster reference layer before it expands Foster
terminology in lookup, learning, or sentence-reading tools. Current labels are
useful, but some are project vocabulary rather than terms grounded directly in
Reginald Foster's published method. This project will create local generated
artifacts from `~/reginald-foster/reginald-foster-latin.pdf` so developers can
search, cite, summarize, and audit Foster concepts against the PDF.

The first deliverable is not a learner UI. It is a reproducible local extraction
and indexing loop, modeled on the Bailly PDF import pattern: committed code,
tests, schemas, and docs; generated text, JSONL, DuckDB, and LLM summaries stay
local and ignored.

## Source And Artifact Policy

The source PDF is copyrighted local material. LangNet should not commit the PDF
or full extracted text. The repository may commit extraction code, tests using
small synthetic fixtures, schemas, and short metadata descriptions. Generated
artifacts should live under ignored paths such as:

- `examples/debug/foster-ossa-pages.jsonl`
- `examples/debug/foster-ossa-structure.jsonl`
- `examples/debug/foster-ossa-summaries.jsonl`
- `data/build/foster_ossa.duckdb`

Public docs and CLI output should use short paraphrases and page references.
They should not reproduce long passages from the PDF.

## Architecture

The pipeline has four layers.

1. **Page extraction:** read the PDF with Poppler tools already available in the
   environment. The first implementation should use `pdftotext` because it is
   fast and enough for page-aware search. Poppler XML can be added later for
   layout-heavy sections.
2. **Structure detection:** split extracted pages into durable units:
   front matter, abbreviations, Five Experiences, encounters, reading sheets,
   indexes, bibliography, and sentence-structure notes.
3. **Local index:** build a DuckDB index with pages, sections, encounters,
   concept mentions, method principles, and optional generated summaries.
4. **Inspection commands:** expose search and lookup commands so developers can
   ask whether a LangNet Foster term is source-backed, unsupported, or merely a
   project overlay.

This should follow the Bailly import boundary: parsing and extraction are
source-specific, while the downstream index presents a small stable inspection
contract.

## Data Model

The first DuckDB schema should stay conservative.

- `pages`: physical PDF page number, extracted text, text hash, extraction tool,
  warning fields, and rough section classification.
- `sections`: durable structural spans such as `front_matter`,
  `first_experience`, `reading_sheets_first_experience`, `indexes`, and
  `bibliography`.
- `encounters`: experience number, encounter number, title, normalized title,
  page start, page end, and raw heading text.
- `concept_mentions`: detected term, normalized term, category, page number,
  encounter id when known, and a short local context window.
- `method_principles`: curated or rule-detected method claims, each tied to one
  or more page references and marked by provenance type.
- `summaries`: optional LLM-generated page, encounter, section, or concept
  summaries with model, prompt version, source span, source hash, generated text,
  and validation status.

The index should make provenance obvious. Any summary or method principle must
point back to page and structure rows.

## LLM Summary Enrichment

LLM summaries are useful, but they are derived metadata. They must never replace
the extracted source text or page references.

The summary workflow should reuse the existing aisuite/OpenRouter precedent:

- read `OPENAI_API_KEY` and `OPENAI_API_BASE` or `OPENAI_BASE_URL`;
- default to OpenRouter-compatible aisuite calls;
- require an explicit `--summarize` or separate summary command before network
  calls happen;
- write generated summaries into local JSONL or DuckDB rows;
- include model id, prompt version, input span id, input text hash, timestamp,
  and any warnings;
- keep summaries short, source-faithful, and page-backed;
- allow dry-run mode that reports planned chunks without calling a model.

Recommended summary scopes:

- page summary: one or two sentences for search and triage;
- encounter summary: what the encounter teaches, using Foster's structure;
- concept summary: where a grammar/function/process term appears and how the
  method uses it;
- method summary: durable principles such as dictionary-first work, function
  over jargon, real-text reading, repetition, sentence structure, and active
  student work.

Prompt rules should require the model to separate direct source wording from
paraphrase, avoid inventing unsupported concepts, and list source page spans.

## CLI Shape

Use these command names for the first implementation unless a test exposes a
conflict with existing Click routing:

```bash
just cli foster-ossa-extract \
  --source ~/reginald-foster/reginald-foster-latin.pdf \
  --output examples/debug/foster-ossa-pages.jsonl

just cli-databuild foster-ossa \
  --source examples/debug/foster-ossa-pages.jsonl \
  --output data/build/foster_ossa.duckdb \
  --wipe

just cli foster-ossa search "function"
just cli foster-ossa encounter 1
just cli foster-ossa concept "genitive"
```

For LLM summaries:

```bash
just cli foster-ossa-summarize \
  --db data/build/foster_ossa.duckdb \
  --scope encounter \
  --model openai:deepseek/deepseek-v4-flash \
  --output examples/debug/foster-ossa-summaries.jsonl \
  --dry-run
```

The default behavior should be local-only. Any network call requires explicit
summary/populate flags.

## Integration With Existing Foster Work

This index should support, but not immediately rewrite, existing Foster-facing
code:

- `src/langnet/pedagogy/foster.py`
- `docs/GRAMMAR_LEARNING_OVERLAY.md`
- `docs/FOSTER_FUNCTIONAL_GRAMMAR_EXAMPLES.md`
- `docs/superpowers/plans/2026-05-21-foster-friendly-morphology.md`

After the index exists, LangNet can audit labels such as `NAMING`,
`RECEIVING`, `TIME_NOW`, and `FOR_SELF` against the local Foster source. The
result should classify each term as:

- directly supported by Foster wording;
- supported by Foster method but project-normalized;
- useful project overlay without direct Foster wording;
- unsupported and should be renamed or removed.

## Testing

Tests should avoid the real PDF and use small synthetic fixtures:

- page extraction parser tests for JSONL row shape;
- structure detector tests for Experience and encounter headings;
- concept mention tests for abbreviations and function terms;
- DuckDB builder tests with two or three fixture pages;
- CLI help tests for extraction, build, search, and summary commands;
- dry-run summary tests proving no network call is made.

Manual verification against the real local PDF should use ignored artifacts in
`examples/debug` and `data/build`.

## Non-Goals

- Do not commit the PDF or full extracted text.
- Do not make LLM summaries authoritative.
- Do not rewrite learner-facing Foster labels before the source audit exists.
- Do not implement broad passage interpretation in this slice.
- Do not require OpenRouter credentials for extraction, search, or databuild.

## Success Criteria

- A developer can extract the local PDF into page-aware JSONL.
- A developer can build a local DuckDB index from that JSONL.
- A developer can search terms and retrieve page-backed Foster references.
- Encounter structure is represented well enough to ask what a given encounter
  teaches.
- Optional LLM summaries can be generated locally and audited against page
  spans.
- Existing Foster terminology can be classified as directly source-backed,
  method-backed, project overlay, or unsupported.
