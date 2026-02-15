# Component Documentation

This directory contains technical references for the core system and its backends.

## What Lives Here
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — End-to-end system view and API notes.
- **[backend/](backend/README.md)** — Engine, Diogenes, Cologne/CDSL, and Whitaker’s Words specifics.
- **[design/](design/)** — Semantic reduction design notes and drafts.
- **[opencode/](opencode/)** — Multi-model AI workflow guidance.

## When to Read What
- Start with **ARCHITECTURE.md** to understand the request flow and schema boundaries.
- Use the **backend** README files when changing adapter behavior or adding features.
- Check **opencode** when routing tasks to personas (@architect, @coder, etc.).

## Maintenance Notes
- Update the relevant backend README when interface or normalization rules change.
- Keep examples in sync with `src/langnet/schema.py` to avoid drift in output expectations.
- If you add a new component, create a short README here and link it from `backend/README.md`.
