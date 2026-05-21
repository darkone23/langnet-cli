> Archived during the 2026-05 documentation overhaul. Retained for historical context; current planning guidance lives in docs/ROADMAP.md, docs/EXECUTION_PLAN.md, and the current active plans under docs/plans/active/.

# CLTK Latin Lexicon Integration Backlog

## Context

`~/cltk-data/lat/lexicon` appears to contain Latin lexicon data that may be useful for LangNet dictionary and reader workflows, but it is not yet audited or integrated.

This is intentionally queued behind the current reader corpus/index/audit work. The immediate priority remains making corpus sources enumerable, discoverable, addressable, and retrievable by dictionary citation.

## Follow-Up

- Inventory files and formats under `~/cltk-data/lat/lexicon`.
- Compare coverage against current Latin dictionary sources.
- Decide whether this should feed dictionary lookup, citation/reference extraction, reader aliases, or a separate lexical metadata index.
- Add fixture-backed import tests before integrating.
