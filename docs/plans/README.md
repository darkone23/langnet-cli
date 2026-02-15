# Project Plans Overview

Plans are organized by lifecycle and feature area. Use the structure below when adding or moving plans:

```
docs/plans/
├── active/
│   └── <feature-area>/   # skt, whitakers, dico, pedagogy, infra, semantic-reduction, etc.
└── todo/
    └── <feature-area>/
```

## Lifecycle Categories
- **active/** — In progress or being implemented.
- **todo/** — Ideas and scoped work that has not started.

## Maintenance Guidelines
1. Place new plans under the correct feature area directory (e.g., `active/skt/` for Heritage/CLTK/Sanskrit work).
2. Avoid duplicates; each plan should appear in only one lifecycle directory.
3. Add status markers inside the file (`🔄 IN PROGRESS`, `⏳ PENDING`) and keep them accurate.
4. If a plan is paused, move it back to `todo/` and note the blockers.

## Clean-Up Notes
- Semantic reduction plans are grouped under `active/semantic-reduction/` and `todo/semantic-reduction/`.
- `active/skt/` is currently empty; use it for Heritage/CDSL improvements instead of creating new top-level files.

## Related Documentation
- **[docs/DEVELOPER.md](../DEVELOPER.md)** — Development workflow and AI integration