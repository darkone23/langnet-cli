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

## Current Canonical Plan

- `docs/plans/active/infra/design-to-runtime-roadmap.md`
- `docs/plans/active/infra/junior-engineer-start-packet.md`

The roadmap remains the active implementation source of truth. The junior start packet is a short assignment handoff and should not become a parallel roadmap.

## Junior Work

- `docs/plans/todo/infra/junior-task-backlog.md`

Tasks there should be small, explicit, service-free where possible, and independently testable.

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
