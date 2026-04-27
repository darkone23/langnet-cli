# Plans

Plans are for work management, not permanent reference. Keep this directory small and current.

## Structure

```text
docs/plans/
├── active/      # work currently being driven
├── todo/        # scoped future work
└── completed/   # completed plans and handoff records
```

Feature areas should be subdirectories such as `infra`, `skt`, `pedagogy`, `dico`, or `semantic-reduction`.

## Current Planning References

- `docs/EXECUTION_PLAN.md`
- `docs/plans/active/infra/design-to-runtime-roadmap.md`
- `docs/plans/active/infra/stabilization-planning-session.md`
- `docs/plans/active/pedagogy/learner-encounter-roadmap.md`

The execution plan is the compact operating view. The roadmap remains the milestone sequence. The active implementation roadmap contains detailed sequencing.
The stabilization planning session is the current working agenda for reconciling
status, target state, gaps, and ranked next tasks.
The learner encounter roadmap is the active plan for turning `encounter` from a
source-first evidence display into validated learner-facing output across
Sanskrit, Latin, and Greek.

## Junior Work

Keep small pickup tasks in `docs/EXECUTION_PLAN.md` unless they need a dedicated plan. Tasks should be explicit, service-free where possible, and independently testable.

## Archival Rule

Move stale plans to `docs/archive/` rather than leaving them under `active/` or `todo/`.

A stale plan is one that:

- describes foundation work already implemented
- has old test counts or old command names
- duplicates the canonical roadmap
- depends on an architecture that no longer exists

## Status Markers

Use simple markers:

- `🔄 ACTIVE`
- `⏳ TODO`
- `✅ DONE`
- `🧊 ARCHIVED`
