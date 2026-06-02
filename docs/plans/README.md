# Plans

Plans are for work management, not permanent reference. Keep this directory
small, current, and tied to work that can be resumed.

## Structure

```text
docs/plans/
├── active/      # work currently being driven
├── todo/        # scoped future work
└── completed/   # completed plans and handoff records
```

Feature areas should be subdirectories such as `infra`, `skt`, `pedagogy`,
`dico`, or `semantic-reduction`.

## Active Plans

Only these plans are active after the 2026-05 documentation overhaul:

- `docs/plans/active/infra/reader-source-backed-enrichment.md`
- `docs/plans/active/infra/reader-traditional-structure-overhaul.md`
- `docs/plans/active/pedagogy/learner-encounter-roadmap.md`
- `docs/plans/active/pedagogy/real-input-fuzzing-roadmap.md`
- `docs/plans/active/skt/cdsl-entry-grammar-plan.md`

Current milestone status and broad planning belong in `docs/ROADMAP.md` and
`docs/EXECUTION_PLAN.md`, not in `docs/plans/active/`.

## Todo Plans

Todo plans are scoped future work, not broad status pages:

- `dico/`: DICO refinement.
- `infra/`: citation resolution follow-up.
- `pedagogy/`: compound lookup, contextual meaning, paradigm follow-up, and
  word-index exploration.
- `semantic-reduction/`: reducer similarity refinement.
- `skt/`: Sanskrit tokenization and compound evidence.

Archive placeholders, superseded web enablement notes, and completed
implementation plans instead of leaving them in `todo/`.

## Completed Records

`docs/plans/completed/` keeps implementation records and handoff history. These
files may contain old commands, checklist snapshots, and historical context, but
they are not active guidance.

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
