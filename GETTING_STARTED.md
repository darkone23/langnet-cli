# Getting Started

This root document is a short pointer for the current project state. The
maintained setup and command guide lives in `docs/GETTING_STARTED.md`.

## Quick Start

```bash
devenv shell
langnet-cli --help
```

Or run commands through the project recipes:

```bash
just cli --help
just cli encounter lat arma gaffiot --translation-mode cache
just cli encounter san dharma dico --translation-mode cache
```

## Current Reliable Surface

The CLI is the reliable product surface. The current learner-facing command is:

```bash
langnet-cli encounter <language> <word> [tool-filter]
```

Use `docs/GETTING_STARTED.md` for environment details, external service
requirements, validation commands, and troubleshooting.

## Historical Note

Older V2 implementation notes have been moved out of this root quick-start. For
current architecture and roadmap decisions, start with:

- `docs/BASELINE_AND_ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`
- `docs/technical/design/TECHNICAL_VISION.md`
