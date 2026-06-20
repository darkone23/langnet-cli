# Plans

Plans are for resumable work, not permanent project status. If a file records
what happened in one session, move it to `docs/archive/`. If it records
completed implementation, move it to `docs/plans/completed/`. If it still
describes work someone can pick up, keep it here and make the next action
obvious.

## Structure

```text
docs/plans/
├── active/      # work currently being driven
├── todo/        # scoped future work
└── completed/   # completed plans and handoff records
```

Feature areas should be subdirectories such as `infra`, `skt`, `pedagogy`,
`dico`, or `semantic-reduction`.

## Active Drivers

Start with these when choosing what to do next:

- `docs/EXECUTION_PLAN.md` - compact operating queue.
- `docs/ROADMAP.md` - durable milestone sequence.
- `docs/plans/active/infra/READER_GOALS_COORDINATION_PLAN.md` - reader, library,
  source-acquisition, and provenance work order.

## Supporting Active Plans

These are scoped implementation or design plans. They should be worked only
when they support the active drivers above.

Reader, corpus, and library:

- `infra/READER_COLLECTION_EXPANSION_MASTER_TRACKER_2026-06-07.md`
- `infra/reader-traditional-structure-overhaul.md`
- `infra/READER_EXPERIENCE_MODALITY_AND_TYPOGRAPHY_PLAN.md`

Pedagogy:

- `pedagogy/foster-learning-experience/TOC_SUMMARY_PIPELINE.md`

Do not add dated status files, running-service notes, or session handoffs under
`active/`. Put them under `docs/archive/<date-or-topic>/`.

## Active Plan Zero Closeout Queue

Goal: drive `docs/plans/active/` toward zero files by finishing implementation
plans, folding durable status into `docs/EXECUTION_PLAN.md` or `docs/ROADMAP.md`,
and moving completed records to `docs/plans/completed/` or `docs/archive/`.

Do not create another active plan to manage this. Use this queue as the current
closeout matrix.

| Order | Active file | Closeout class | Next action |
| --- | --- | --- | --- |
| 1 | `infra/reader-traditional-structure-overhaul.md` | UI overhaul implementation plan | Continue route/controller decomposition and visual QA; complete or split after route-size and global-CSS gates are below thresholds. |
| 2 | `infra/READER_EXPERIENCE_MODALITY_AND_TYPOGRAPHY_PLAN.md` | Design policy plus UI follow-up | Move durable design policy into web/docs once remaining concrete UI tasks are represented elsewhere, then archive the plan. |
| 3 | `pedagogy/foster-learning-experience/TOC_SUMMARY_PIPELINE.md` | Generated-artifact pipeline plan | Finish retry/rollup/taxonomy mapping or demote to todo if Foster work is paused. |
| 4 | `infra/READER_COLLECTION_EXPANSION_MASTER_TRACKER_2026-06-07.md` | Tracker/coordination record | Collapse current work order into `READER_GOALS_COORDINATION_PLAN.md` and the completed corpus framework, then archive this dated tracker. |
| 5 | `infra/READER_GOALS_COORDINATION_PLAN.md` | Temporary coordination driver | Keep until reader work has one surviving implementation plan per lane; then fold durable priorities into `docs/EXECUTION_PLAN.md` and archive. |

Closeout rule for each file:

- if code/tests/docs accepted the planned behavior, move it to
  `docs/plans/completed/`;
- if it is a dated tracker, session handoff, or superseded coordination note,
  move it to `docs/archive/`;
- if only future work remains, reduce it to one concrete todo plan under
  `docs/plans/todo/`;
- if it still drives current implementation, keep it active but make its next
  action and validation command explicit.

## Todo Plans

Todo plans are scoped future work, not broad status pages:

- `dico/`: DICO refinement.
- `infra/`: CTS citation hydration, reliable reader search, Strong's Greek,
  source-enrichment provider rerun, source-acquisition helper, popular Latin,
  public traffic enforcement, and Project Orion humanist/mystical follow-ups.
- `pedagogy/`: compound lookup, contextual meaning, paradigm follow-up, and
  word-index exploration.
- `semantic-reduction/`: reducer similarity refinement.
- `skt/`: Sanskrit tokenization and compound evidence.

Archive placeholders, superseded web enablement notes, and completed
implementation plans instead of leaving them in `todo/`.

## Recently Archived Status Records

- `docs/archive/2026-06-reader-expansion/READER_CURRENT_STATUS_HANDOFF_2026-06-07.md`
- `docs/archive/2026-06-reader-expansion/READER_EXPANSION_QUALITY_CLOSEOUT_2026-06-07.md`
- `docs/archive/2026-06-reader-expansion/local-lexicon-witness-handoff.md`

These are useful evidence and handoff records. They are not current work-order
documents.

## Completed Records

`docs/plans/completed/` keeps implementation records and handoff history. These
files may contain old commands, checklist snapshots, and historical context, but
they are not active guidance.

Recently completed/retired from active:

- `docs/plans/completed/infra/public-static-presence-and-crawler-safe-app.md`
- `docs/plans/completed/infra/OPEN_GREEK_LATIN_AND_GEORGES_IMPORT_PLAN.md`
- `docs/plans/completed/infra/READER_WORD_CONTEXT_RETRIEVAL_QUALITY_PLAN.md`
- `docs/plans/completed/infra/LANGNET_LIBRARY_EXPLORER_PLAN.md`
- `docs/plans/completed/infra/reader-source-backed-enrichment.md`
- `docs/plans/completed/infra/reader-citation-reference-resolution.md`
- `docs/plans/completed/infra/OPEN_GREEK_LATIN_IMPORTER_AUDIT_AND_FIX_PLAN.md`
- `docs/plans/completed/infra/LANGNET_CORPUS_BUILDING_AND_ACQUISITION_PLAN.md`
- `docs/plans/completed/infra/BRUNO_LLULL_ELECTRONIC_TEXT_ACQUISITION.md`
- `docs/plans/completed/infra/LANGNET_CANONICAL_CATALOG_EXPORT_PLAN.md`
- `docs/plans/completed/infra/anonymous-client-attestation-and-rate-limiting.md`
- `docs/plans/completed/pedagogy/learner-encounter-roadmap.md`
- `docs/plans/completed/pedagogy/real-input-fuzzing-roadmap.md`
- `docs/plans/completed/skt/cdsl-entry-grammar-plan.md`

## Archival Rule

Move stale plans to `docs/archive/` rather than leaving them under `active/` or
`todo/`.

A stale plan is one that:

- describes foundation work already implemented;
- has old test counts or old command names;
- duplicates the canonical roadmap;
- depends on an architecture that no longer exists.

Status docs and handoff snapshots should live in `docs/ROADMAP.md`,
`docs/EXECUTION_PLAN.md`, or `docs/archive/`, not under `active/`.
