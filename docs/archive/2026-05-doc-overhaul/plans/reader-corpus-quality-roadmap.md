> Archived during the 2026-05 documentation overhaul. Retained for historical context; current planning guidance lives in docs/ROADMAP.md, docs/EXECUTION_PLAN.md, and the current active plans under docs/plans/active/.

# Reader Corpus Quality Roadmap

## Goal

Build a source-agnostic reader corpus where texts are locally imported, cleaned,
enumerable, addressable, and enriched with research-backed metadata without
discarding ambiguity.

## Principles

- `reader works` should answer learner-facing questions such as "what books do
  we have?" without requiring import-source knowledge.
- Stable work IDs, CTS URNs where available, contents enumeration, and exact
  segment reads are the primary reader contract. Fuzzy or friendly citation
  shorthand is secondary.
- Source/import details stay available for audit and debugging.
- `works.author` is a canonical display field, not a place to encode every
  uncertainty.
- Ambiguous authorship must not be dropped. Store it as structured attribution
  claims that can be queried and reviewed separately.
- Accepted display overlays and accepted attribution claims are different facts:
  one changes visible canonical metadata, the other records evidence-backed
  scholarly/source tradition.

## Attribution Model

For a work described as "written by Aristotle or Avicenna":

- keep `works.author` as `Unattributed`, `Unknown`, `Anonymous`, or the best
  accepted display author;
- store two attribution claims:
  - `possible_author = Aristotle`
  - `possible_author = Avicenna`
- attach evidence and confidence to each claim;
- allow a later display-author overlay to select one canonical display author
  without deleting the competing attribution history.

## Duplicate Model

The import layer distinguishes accidental duplicates from scholarly duplicates.

- Accidental duplicates are repeated source copies or repeated parser outputs
  that produce the same canonical work, edition, and segment ids. These should
  be collapsed so address resolution remains deterministic.
- Scholarly duplicates are editions, translations, witnesses, or attribution
  traditions. These should remain discoverable through catalog rows, editions,
  artifacts, and attribution claims.
- Shared physical DuckDB files are allowed for efficiency, but only when the
  catalog still exposes one addressable work/artifact per logical work.

## Phases

1. **Import completeness**
   - Continue full curated builds for Perseus, digilibLT, PHI/TLG, and Sanskrit.
   - Keep disk usage managed by removing superseded debug builds only after a
     replacement validates.
   - Track source errors and zero-segment artifacts as build blockers.

2. **Text cleanliness**
   - Run strict validation over every curated catalog.
   - Separate true XML/legacy markup leakage from benign text such as monetary
     dollar signs.
   - Add focused validators for fused notes, blank text, unresolved aliases, and
     missing addressability.

3. **Canonical metadata overlays**
   - Use overlays only for display metadata changes: author, title, language,
     author id, and CTS URNs.
   - Require evidence and confidence.
   - Preserve uncertainty in notes when the display author is traditional or
     conventional rather than certain.

4. **Attribution claims**
   - Add a curated attribution-claims layer for possible, traditional,
     disputed, misattributed, translator, commentator, editor, and compiler
     relationships.
   - Register claims in the reader catalog without changing display metadata.
   - Add `reader attributions` so users and auditors can inspect all known
     claims for a work or person.

5. **Research enrichment loop**
   - Enumerate unknown/unattributed works.
   - Prioritize high-value works likely to appear in dictionary entries.
   - Use source metadata, local text, repository metadata, and web evidence.
   - Promote display overlays only when one display value is appropriate.
   - Record ambiguous evidence as attribution claims even when no display value
     is chosen.

6. **Learner-facing CLI validation**
   - Validate `docs/READER_CLI_BEGINNER_GUIDE.md` against actual catalogs.
   - Keep examples source-agnostic and command-copyable.
   - Prefer file-based JSON examples with `nu` for reliable repeatability.
   - Include discovery, enumeration, contents, direct segment reads, overlays,
     attributions, and validation.

## Current Status

- The attribution-claims slice is implemented in code, storage, builder
  registration, service, CLI, tests, and beginner/audit documentation.
- The first real claims file records Sanskrit DCS traditional, probable, and
  name-ambiguous authorship cases without relying on fabricated examples.
- A tiny real DCS proof build confirms attribution claims are queryable while
  display authors remain unchanged when overlays are disabled.
- A second targeted DCS proof build confirms seven additional Sanskrit
  research-backed overlays and attribution claims, including Carakasaṃhitā's
  Caraka/Agniveśa/Dṛḍhabala transmission layers.
- A third targeted DCS proof build confirms four additional Sanskrit literary
  and philosophy overlays and attribution claims for Somadeva, Nāgārjuna,
  Daṇḍin, and Kālidāsa.
- Additional targeted proof builds confirm Sanskrit philology/commentary and
  philosophy overlays, including commentator claims for Vātsyāyana and
  Candrakīrti and durable-only curated citations.
- A further targeted DCS proof build confirms didactic, smṛti, and philosophy
  overlays for Bhartṛhari, Yājñavalkya, and Mādhavācārya, with Yājñavalkya
  preserved as a traditional-author claim.
- A literary/medical DCS proof build adds four more research-backed display
  authors and attribution claims: Govardhana, Bhāvamiśra, Bilhaṇa, and
  Budhasvāmin.
- Reader CLI routing now keeps alias resolution catalog-first. The `Od. 3.74`
  path no longer scans book artifacts for the literal alias string before
  resolving the alias, friendly `show` addresses follow the same rule, and
  non-CTS direct addresses route to the addressed work's artifacts from catalog
  metadata.
- Work references now resolve by alias, `work_id`, or `cts_work_urn`, so exact
  CTS work URNs can drive `contents` and `show ... --segment` even when the
  stored corpus work id is internal.
- Catalog builds now register only aliases whose targets are present in the
  built catalog, and validation reports unresolved alias targets.
- PHI/TLG legacy IDT imports now populate `cts_work_urn` for clean numeric work
  ids, giving future curated builds a catalog-level CTS bridge without writing
  duplicate segment addresses.
- Validation now flags clean PHI/TLG legacy work ids that should have a
  generated CTS work URN but do not.
- PHI/TLG legacy build performance has been improved by batching catalog
  registration, using Polars-backed bulk catalog inserts, caching repeated
  source hashes, batching writes per physical book DB, and sharing one physical
  book DB per legacy source text file while keeping one catalog artifact per
  work.
- Catalog-level authorship questions now have a direct CLI path:
  `reader works --author <name>` searches display authors, while
  `reader works --attributed-to <name>` searches display authors plus accepted
  authorship attribution claims without reading book text.
- `docs/READER_CORPUS_STATUS.md` records the current handoff state for
  verified catalogs, metadata policy, citation policy, catalog-level tooling,
  chronology deferral, and next checkpoints.
- The current Perseus curated catalog has 0 unknown authors after accepted
  Appendix Vergiliana overlays and 0 strict validation issues.
- The current PHI/TLG legacy catalog has 7,836 works, 10,591,345 segments,
  2,196 physical book DBs, 0 source errors, and 0 strict validation issues
  after catalog-local alias filtering.
- The refreshed Sanskrit curated catalog has 977 works, 3,319,944 segments,
  0 source errors, 0 strict validation issues, and 38 accepted claim-level
  attribution records. 564 Sanskrit works remain `Unknown`.
- Accepted contained works now participate in author index and author-selector
  browsing. The Sanskrit catalog verifies contained `Bhagavadgītā` under
  `Vyāsa` via `langnet:reader:author:san:vyasa`.
- Session wrap-up and resumption notes are recorded in
  `docs/handoff/reader-corpus-wrapup-2026-05-14.md` and mirrored to
  `/tmp/langnet-reader-corpus-wrapup-2026-05-14.md`.

## Next Step

- Continue Sanskrit metadata enrichment for remaining `Unknown` works,
  prioritizing high-value named-title cases.
- Validate the beginner CLI guide against the final current catalogs.
