# Foster Ossa Integration Status

This is the handoff document for the current Foster/Ossa integration. It tells
readers what works today, where the generated artifacts live, what is not yet
product-ready, and which Foster essentials are close enough to codify.

## Working Today

The local Foster/Ossa workflow can:

- extract page text from `~/reginald-foster/reginald-foster-latin.pdf` into
  `examples/debug/foster-ossa-pages.jsonl`;
- build a DuckDB artifact at `data/build/foster_ossa.duckdb`;
- derive a Lance full-text index at `data/build/foster_ossa_search.lance`;
- search pages and encounters by source-backed refs such as `page:49`,
  `toc:1.6`, and `encounter:1.1`;
- parse 105 numbered TOC encounter entries across Experiences 1, 3, and 4;
- generate validated TOC-entry summaries and experience rollups;
- render reviewable Markdown summaries under
  `docs/reference/foster-ossa/generated/`;
- audit generated Foster terms against the existing LangNet grammar concept
  registry.

Useful commands:

```bash
just cli foster-ossa search "Functions produce true meaning" \
  --index data/build/foster_ossa_search.lance \
  --limit 5 \
  --output json

just cli foster-ossa toc \
  --db data/build/foster_ossa.duckdb \
  --experience 1 \
  --output json

just cli foster-ossa search-index validate \
  --index data/build/foster_ossa_search.lance \
  --output json
```

## Current Artifacts

- `examples/debug/foster-ossa-pages.jsonl`: page-level extraction, 878 rows.
- `data/build/foster_ossa.duckdb`: structured pages, sections, TOC entries,
  detected encounters, and concept mentions.
- `data/build/foster_ossa_search.lance`: page and encounter search records.
- `examples/debug/foster-ossa-toc-all-summaries-v2.jsonl`: validated
  generated summaries for all 105 TOC entries.
- `examples/debug/foster-ossa-experience-summaries-v2.jsonl`: validated
  generated rollups for Experiences 1, 3, and 4.
- `docs/reference/foster-ossa/generated/`: human-readable generated summary
  documents.
- `data/build/foster_essentials.json`: machine-readable starter pack for
  codified Foster essentials.
- `docs/reference/foster-ossa/FOSTER_ESSENTIALS.md`: reviewable Markdown view
  of the same essentials pack.
- `docs/reference/foster-ossa/TAXONOMY_AUDIT.md`: generated term review queue.
- `docs/reference/foster-ossa/CORE_FUNCTION_BRIDGE.md`: first conservative
  Foster-to-LangNet concept mappings.
- `docs/reference/foster-ossa/DIDACTIC_SYNTHESIS.md`: didactic synthesis and
  platform implications.

## Experience 2

Experience 2 is present in the source extraction. It is not missing.

It is absent from the generated TOC-entry summary set because that scope follows
numbered systematic grammar encounters. The source describes the Second
Experience as the immediate spoken/application experience with reading sheets,
not as a second numbered grammar sequence. The current generated summary docs
therefore show Experiences 1, 3, and 4.

The next sensible Experience 2 task is a separate reading-sheet/spoken-Latin
summary scope, not a fake `experience-2.md` made from numbered grammar entries.

## Foster Essentials Ready To Codify

These items have enough support to begin product integration as structured
concept bridges, while still retaining source refs and conventional grammar
labels:

| Foster essential | Current concept bridge | Product use |
| --- | --- | --- |
| `of-possession` | `case.genitive` | Show a possession/relation gateway beside genitive evidence. |
| `to-for-from` | `case.dative` | Show a recipient/benefit/reference gateway beside dative evidence. |
| `object form` | `case.accusative` | Show the receiving/object function beside accusative evidence. |
| `function of address` | `case.vocative` | Show direct address separately from subject/object roles. |
| `location function` | `case.locative` | Show location/setting function where the platform has locative evidence. |
| `subject form` | `case.nominative` | Show naming/subject function where the platform has nominative evidence. |

These mappings are now available as a structured starter pack in
`data/build/foster_essentials.json` and a readable review document in
`docs/reference/foster-ossa/FOSTER_ESSENTIALS.md`. The review rationale is in
`CORE_FUNCTION_BRIDGE.md`.

## Not Yet Product-Ready

The integration does not yet provide:

- a product-facing Foster curriculum or lesson engine;
- final human-reviewed summaries for every claim;
- a final human-authored book-level summary called "Essentials of the Foster Method";
- a dedicated Experience 2 spoken-Latin/reading-sheet summarizer;
- semantic/vector embeddings beyond the current Lance full-text index;
- a stable Foster aggregate concept for `by-with-from-in`;
- reader-library examples attached to each promoted Foster concept;
- dictionary/morphology evidence packs for each Foster concept;
- UI surfaces that teach these concepts directly.

## Open Taxonomy Decisions

The biggest unresolved taxonomy item is `by-with-from-in`. It should not be
collapsed into only `case.ablative`, because the platform also has
`case.instrumental` and `case.locative`, and the Foster/Ossa label functions as
a broader learner-facing bundle.

The best next step is to introduce a Foster aggregate concept that links to:

- `case.ablative`;
- `case.instrumental`;
- `case.locative`;
- Latin preposition and no-preposition examples from the Foster source;
- morphology and dictionary evidence from LangNet readers.

Other high-value audit candidates include sequence of tenses, subjunctive,
indirect question, ablative absolute, relative pronoun, reflexive pronoun,
deponent verbs, indirect discourse, and participial time relationships.

## Reliability Gates

Before a generated item becomes product instruction:

- it must come from a `generated_valid` summary row;
- it must carry `toc:*` and/or `page:*` refs;
- it should be spot-checked against the local page extraction;
- it should map to a stable LangNet concept or be explicitly marked as a new
  Foster-specific candidate;
- it should have reader examples and morphology/dictionary evidence before it
  drives learner-facing behavior.

Current validation commands:

```bash
just cli foster-ossa search-index validate \
  --index data/build/foster_ossa_search.lance \
  --output json

just cli foster-ossa-taxonomy-audit \
  --toc-summaries examples/debug/foster-ossa-toc-all-summaries-v2.jsonl \
  --experience-summaries examples/debug/foster-ossa-experience-summaries-v2.jsonl \
  --output docs/reference/foster-ossa/TAXONOMY_AUDIT.md
```

## Recommended Next Slice

Use the first codified Foster essentials pack as a product substrate:

1. Attach reader examples from the indexed classics libraries.
2. Attach dictionary and morphology evidence from the existing LangNet
   analyzers.
3. Add a stable aggregate concept design for `by-with-from-in`.
4. Decide which essentials are ready to appear in the learner-facing UI.

That gives the application a practical "Foster essentials" substrate without
pretending the generated summaries are themselves the final curriculum.
