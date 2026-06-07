# Reader Collection Expansion Master Tracker

> **Purpose:** This is the master work tracker for expanding LangNet / Project Orion's reader collection while preserving provenance, source quality, and learner-facing usefulness.

## Goal

Build a higher-quality reader library across Latin, Greek, and Sanskrit by adding high-value works through manifest-backed, source-controlled acquisition. The project should prioritize works that users actually want to read, while also building the reference constellation that makes Project Orion feel like a real humanist library.

This is not a single-author plan and it is not a bulk-ingestion plan. PL122,
the PG pilot, and other source-specific passes already proved that ad-hoc
ingestion can work. Cusanus is the current exemplar for turning that experience
into a reusable text/work ingestion pattern, not the first ingest and not the
end goal.
Every expansion target must move through:

- source discovery
- source-role classification
- manifest creation
- raw/source artifact capture
- staged sample
- readability and boundary review
- import only after the sample is acceptable
- source-index export and quality-scorecard update

## Working Principles

- Prefer open-access or run-your-own-mirror sources.
- Do not use subscription databases as text acquisition sources.
- Treat source manifests as mandatory before reader import.
- Preserve raw witnesses unchanged.
- Keep learner-facing cleanup as derived text with an explicit policy.
- Keep reader segments at paragraph size or smaller unless a source-specific structure requires otherwise.
- Distinguish OCR correction from orthographic modernization.
- Keep translations out of source-work imports unless explicitly modeled as translations.
- For contested corpora, expose attribution status rather than flattening it.
- For scientific works, do not import until formulas, diagrams, tables, propositions, and scholia have a source/display policy.

## Master Scorecards And Artifacts

- `data/reference/ogl_import_audit/orion_humanist_mystical_acquisition_scorecard.tsv`
- `data/reference/ogl_import_audit/popular_latin_acquisition_scorecard.tsv`
- `data/reference/ogl_import_audit/pl_pg_acquisition_source_scorecard.tsv`
- `data/reference/ogl_import_audit/pl_pg_acquisition_next_steps.tsv`
- `data/reference/reader_quality_audit/current_known_issues.tsv`
- `data/curated/reader_library_watchlist/high_value_targets.yaml`
- `docs/plans/active/infra/READER_GOALS_COORDINATION_PLAN.md`
- `docs/plans/active/infra/LANGNET_CORPUS_BUILDING_AND_ACQUISITION_PLAN.md`
- `docs/plans/active/infra/READER_EXPANSION_QUALITY_CLOSEOUT_2026-06-07.md`

## Operational Skill

Use the local reader-work ingestion skill for future source acquisition,
manifesting, staging, and scorecard updates:

- `/home/nixos/.agents/skills/langnet-reader-work-ingestion/SKILL.md`

This skill is the process guardrail for reusable ingestion across many authors
and corpora. Cusanus is the current exemplar for clean electronic text plus
control-witness handling, not a one-off pipeline and not the first ingest.

## Active Lanes

## Reusable Text/Work Ingestion Roadmap

This roadmap should apply to Cusanus, Ficino, Bruno, Llull, Aquinas, Albertus,
popular Latin prose, and future scientific Latin targets.

### Stage 0: Target selection

Choose a work because it improves one of the active lanes:

- learner demand
- humanist/mystical/scholastic coverage
- scientific Latin coverage
- Greek reference/lookup coverage
- specialist corpus depth

Output:

- watchlist row
- scorecard row
- priority/cost estimate

### Stage 1: Source candidate discovery

Find open/mirrorable candidate witnesses.

Reusable source types:

- Wikisource electronic text
- Archive.org OCR/PDF/DjVu/hOCR derivatives
- public source trees such as OGL/First1KGreek
- stable public site mirrors
- bibliographic worklists and source-control pages
- local reproducible checkouts

Output:

- source evidence artifacts under `.firecrawl/reader-metadata/<batch>/`
- `data/sources_external/<author>/<work>/manifest.yaml`

### Stage 2: Source-role classification

Do not treat every URL as reader text.

Classify as:

- clean text witness
- OCR text witness
- page-image/PDF witness
- hOCR/layout witness
- bibliography/worklist
- scan locator
- identity-control source
- comparison/control witness
- translation/context only

Output:

- manifest candidate list
- scorecard status update

### Stage 3: Sample staging

Stage a bounded sample before any import.

Policy:

- segment at paragraph size or smaller
- preserve book/chapter/section/line/proposition labels as citation metadata
- preserve source uncertainty in metadata
- keep raw witness unchanged
- label quality honestly

Output:

- `data/build/reader_import_staging/<source>/<work>/*.segments.jsonl`
- staging summary JSON
- quality-audit row if defects remain

### Stage 4: Control witness check

Compare against another source when the primary source has uncertain edition,
OCR noise, attribution risk, or unknown provenance.

Output:

- manifest control-witness note
- source-index-ready provenance fields
- decision: import, defer, compare another witness, or reject

### Stage 5: Reader import wiring

Only after the sample is acceptable:

- wire source-specific staging into the reader import path
- preserve collection id, source id, source URL/path, witness role, quality status
- export source-index snapshots
- add aliases/classification metadata where needed

Output:

- reader catalog rows
- source-index TSV rows
- Library/watchlist status moved from planned/staged to imported/history

### Stage 6: Post-import quality loop

After import:

- inspect reader contents
- verify `/library` discovery aliases
- add known issues for segmentation/OCR/source uncertainty
- update scorecards

Output:

- accepted/imported status or rollback/defer decision

## Current Pilot Pattern

Cusanus currently exercises the `Wikisource electronic text + Archive control
witness` pattern. This is one reusable pattern among several already observed
in the project, alongside PL Wikisource staging, PG OCR pilot staging, Archive
OCR/PDF candidate review, and source-index/export refreshes.

The next roadmap objective is not "finish Cusanus at all costs"; it is:

- make this pattern repeatable
- use it for the next best low/medium-cost works
- avoid overfitting source acquisition code to one author
- reduce document and workflow drift by keeping one scoped ingestion playbook

### 1. Near-Term Reader Import Lane

These targets are closest to improving the live reader collection.

| Rank | Target | Status | Cost | Next action |
| --- | --- | --- | --- | --- |
| 1 | Nicolaus Cusanus, `De docta ignorantia` | `imported_source_index_exported` | low-medium | Imported as 104 paragraph-level segments in `cusanus_latin_wikisource`; next work is post-import reader/Library provenance QA, not more Cusanus acquisition. |
| 2 | Popular Latin prose pilot, likely Caesar or Sallust | `needs_source_review` | low-medium | Create first source manifest from open/mirrorable witness after checking existing catalog coverage. |
| 3 | Ficino, `De vita libri tres` | `source_candidate_verified` | medium-high | Compare 1489/1529/1549 text derivatives and select the cleanest opening sample. |
| 4 | Bruno, one Latin memory/magic work | `planned` | medium-high | Choose one source path and create a source manifest before staging. |

Acceptance:

- At least one target reaches staged sample with clean Latin text, stable boundaries, and source-control evidence.
- Import only after source-index fields can be populated accurately.
- `/library` and `reader works` expose aliases and acquisition provenance.

### 2. Humanist, Scholastic, Mystical Library Lane

These define the Project Orion humanist library identity.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| Agrippa, `De occulta philosophia` | `deferred_lexeme_cleanup_needed` | high | Source and sample exist, but 1533 OCR needs long-s/f and lexeme-level cleanup policy. |
| Ficino, `De vita libri tres` | `source_candidate_verified` | medium-high | Multiple Archive witnesses; likely next after Cusanus. |
| Cusanus, `De docta ignorantia` | `imported_source_index_exported` | low-medium | Integrated from staged Wikisource text with Archive 1913 control-witness provenance. |
| Bruno, Latin memory/magic/philosophy works | `planned` | medium-high | Strong Project Orion identity fit. |
| Albertus Magnus | `needs_source_review` | high | Must distinguish authentic Albertus from pseudo-Albertine works. |
| Paracelsus | `needs_source_review` | high | Latin-only filtering and pseudo-attribution handling required. |
| Ramon Llull | `needs_ocr` | medium-high | Existing research points to OCR/PDF unless clean Latin source is found. |
| Aquinas | `deferred_non_importable_quality_gate` | medium-high | q.50 OCR evidence is preserved but closed as non-importable for this stack; future work requires OCR/article-structure cleanup or q.1 witness decision. |
| Duns Scotus | `deferred_source_decision_required` | high | Inspected Archive.org volumes are non-Ordinatio candidates; no active staging remains until a source/work decision is made. |
| Pico | `needs_source_review` | medium | Useful bridge for Ficino/Plotinus/cabala/humanist synthesis. |
| Plethon | `needs_source_review` | uncertain | Likely relationship/reference metadata first. |

Acceptance:

- Each target has explicit language support: Latin, Greek, or Sanskrit only.
- Contested authorship and pseudo-corpora are modeled in metadata.
- Relationship edges are source-backed: teacher, patron, translator, manuscript supplier, influence, opponent, school, or reception link.

### 3. Popular Classical Latin Lane

This lane addresses common reader demand and classroom/self-study usefulness.

Initial queue:

- Caesar, `De bello Gallico`
- Vergil, `Aeneid`
- Ovid, `Metamorphoses`
- Cicero, `In Catilinam`
- Catullus, `Carmina`
- Horace, `Odes`
- Sallust, `Bellum Catilinae` and `Bellum Iugurthinum`
- Tacitus, starting with `Agricola` and `Germania`

Acceptance:

- Verify existing catalog coverage before importing duplicates.
- Prefer prose-first imports when possible because book/chapter boundaries are simpler.
- Preserve canonical citation shape: book/chapter, speech/section, poem number, or book/line.

### 4. Scientific Latin Lane

High-value, but more expensive because ordinary prose segmentation is not enough.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| Newton, `Principia` | `source_candidate_identified` | high | Propositions, scholia, formulas, diagrams. |
| Kepler, `Astronomia nova`, `Harmonices mundi` | `source_candidate_identified` | high | Diagrams, tables, astronomical notation. |
| Euler, `Mechanica` and broader works | `source_candidate_verified` | high | Archive OCR exists; Euler Archive has 850+ work identity-control pages. |

Acceptance:

- Define formula/diagram/table policy before staging.
- Preserve proposition/scholium/corollary citation structure.
- Do not damage mathematical notation during text extraction.

### 5. Reference Constellation Lane

This makes Orion more than a text dump.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| Suda author/person bios | `imported_needs_reference_index` | medium | Already imported as First1KGreek reader work; needs structured lookup layer. |
| Orion of Thebes / Greek etymologica | `needs_inventory` | medium | Project identity target; inventory current lexicographic works first. |
| Pseudo-Zonaras, Stephanus Byzantius, other lexica | present/unknown | medium | Need inventory and source-role classification. |

Acceptance:

- Author/person cards can resolve to Suda/reference entries.
- Greek lookup can surface etymological/reference witnesses.
- UI cast-of-characters figures resolve to reader works, reference entries, or acquisition targets.

### 6. Specialist Corpus Depth Lane

PL/PG/CSEL remain important, but should not crowd out more directly useful reader targets.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| PL122 / Eriugena | imported | completed pilot | Fourteen works imported and source-indexed. |
| PG pilot | imported sample | high | OCR noise/segmentation calibration needed before broad PG. |
| CSEL61 / Prudentius | `source_candidate_verified` | medium-high | Candidate found; PDF/OCR parsing and sample staging pending. |
| Full PL/PG expansion | planned/deferred | very high | Massive corpus; proceed volume-by-volume or target-by-target. |

Acceptance:

- Each volume/series expansion has a manifest before import.
- OCR and segmentation risks are tracked before broad import.
- Source-index snapshots remain accurate.

## Cost Model

| Cost | Typical source type | Examples |
| --- | --- | --- |
| Low | Clean electronic text with clear structure | Wikisource Cusanus if source-control passes |
| Low-medium | Clean text plus one control witness | Cusanus with Archive cross-check |
| Medium | Archive OCR from later/cleaner print | Some Ficino or CSEL candidates |
| Medium-high | HTML/source-specific cleanup or mixed editions | Bruno, Llull if source text is found |
| High | Early print OCR, long-s/ligatures, pseudo-corpora | Agrippa, Albertus, Paracelsus |
| High | Scientific notation, diagrams, tables | Newton, Kepler, Euler |
| Very high | Bulk corpus acquisition | Full PL/PG/CSEL expansion |

## Current Best Work Order

1. QA `/library` source-index browsing after the truncation fix, especially PHI and one very large collection.
2. QA Cusanus reader and Library provenance display after import.
3. Treat Aquinas q.50 as preserved non-importable evidence, not active integration work, until a dedicated OCR/article-structure cleanup task is opened.
4. Treat Duns Scotus as source-decision deferred, not active staging work, until an Ordinatio witness or non-Ordinatio pivot is explicitly selected.
5. Keep Agrippa deferred until lexeme-level OCR cleanup policy exists.
6. Resume expansion targets such as popular Latin, Ficino, Bruno, CSEL61, or PG only after the current quality gates are stable.

## Done This Session

- PL122/Eriugena cleaned, staged, imported, and source-indexed.
- PL/PG/CSEL scorecards and source-role language updated.
- UChicago PLD bibliography added as PL identity/worklist evidence.
- CSEL61 source candidate identified and manifest updated.
- Popular Latin acquisition scorecard created.
- Humanist/mystical acquisition scorecard created.
- Agrippa manifest and sample created, then deferred for lexeme-level cleanup.
- Ficino manifest created with three candidate witnesses.
- Cusanus manifest created and clean Wikisource sample staged.
- Newton, Kepler, and Euler added as scientific Latin targets.
- Euler `Mechanica` manifest created.
- Suda/Orion reference constellation lane defined.
- Reader-work ingestion skill created and linked as the reusable process guardrail.
- Aquinas and Duns Scotus added to the humanist/mystical scorecard with source-decision next actions.
- Aquinas and Duns Scotus source-decision manifests created with conservative source roles and sample-first acceptance targets.
- Aquinas and Duns Scotus Archive.org derivative metadata/DjVu text inspected; Aquinas volume is usable for Prima Pars q.50-q.119, while inspected Scotus volumes are non-Ordinatio candidates.
- Aquinas Summa theologiae I q.50 OCR candidate sample staged with explicit `candidate_not_import_ready` status.
- Cusanus De docta ignorantia integrated into the reader catalog through generic staged JSONL import and source-index export.
- `/library` source-index truncation fixed by using 20000-row source-index loads for initial and filtered views, increasing the API cap, and adding capped-result UI messaging.

## Immediate Next Checkpoint

Create the reusable ingestion path for clean electronic text plus control
witnesses. Cusanus should exercise that path first because it is already staged,
but the design must be reusable for future Wikisource/electronic-text works.

Required before import:

- Preserve clean text boundaries for Dedicatio, Liber primus, Liber secundus, and Liber tertius.
- Use local Archive hOCR search text as source-control evidence, not as reader text.
- Wire paragraph-level staging records into reader import with source-index fields in an author-agnostic way.
- Add or update quality audit row if source uncertainty remains.
