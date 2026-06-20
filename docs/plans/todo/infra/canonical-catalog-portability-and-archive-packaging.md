# Canonical Catalog Portability And Archive Packaging

Status: todo
Owner: @architect, @auditor
Created: 2026-06-20
Supersedes follow-up phases from: `docs/plans/completed/infra/LANGNET_CANONICAL_CATALOG_EXPORT_PLAN.md`

## Goal

Make canonical reader catalog exports portable across servers and long-term
storage targets.

## Scope

- Decide whether production should transfer canonical export artifacts, rebuild
  them from source/catalog data, or do both.
- Add archive packaging options after the directory format is stable:
  `.zip` first, and `.tar.zst` only if the deployment environment already has a
  reliable local dependency path.
- Document restore and smoke-validation commands for a new server.
- Add size estimates for representative catalog, collection, and single-work
  bundles.
- Define retention policy for generated exports under production storage.

## Acceptance

- A restored bundle can be validated with `reader export validate`.
- Archive packaging preserves the same relative file paths and checksum rows as
  the directory export.
- Migration docs distinguish canonical LangNet bundle data from upstream source
  evidence and generated presentation exports.
