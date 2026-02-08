# Maintainability Refactor – Pickup Notes

Quick guidance for anyone executing the tasks in `MAINTAINABILITY_DECOUPLING_PLAN.md`.

- **Read first**: 
  - Plan: `docs/plans/todo/infra/MAINTAINABILITY_DECOUPLING_PLAN.md` (phases + regression checks)
  - Context: `docs/technical/MAINTAINABILITY_REVIEW.md`
- **Work in phases**: Don’t mix phases. Start with Phase 1 (wiring/config) before normalization/adapters.
- **Regression gates**: Use the checks listed per phase. Keep API shapes stable unless explicitly approved.
- **Shell**: Run everything via devenv: `devenv shell langnet-cli -- <cmd>`.
- **Testing**:
  - Fast/unit: maintain/run the “fast” target (unit/schema tests that don’t need services).
  - Integration: mark tests needing external services; keep them opt-in.
  - Fuzz: for adapter/normalizer changes, run `just fuzz-tools` (per backend) or `just fuzz-query` and diff outputs; only update fixtures with clear rationale.
- **Smoke API**: After wiring/health changes, hit `/api/health` and `/api/q` (lat/grc/san) or run `langnet-cli verify` inside devenv.
- **Docs**: Update `docs/technical/*` and the plan as phases land; note any fixture updates.
- **Health probes**: `/api/health` now calls `src/langnet/health.py`. Extend there (cache stats, degraded messaging) rather than inlining logic in ASGI/CLI.
- **Hygiene**: No `__pycache__` or ad-hoc artifacts checked in; put scratch/debug outputs under `examples/debug`.
- **Safety**: Don’t revert existing workspace changes unless explicitly instructed; avoid destructive git commands.
