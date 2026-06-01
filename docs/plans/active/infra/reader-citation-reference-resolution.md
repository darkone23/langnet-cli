# Reader Citation Reference Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or inline TDD execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve compact dictionary and research references such as `Lucr. 2, 391`, `BhG 9.2`, `Manu xi, 233`, and `Aṣṭādhyāyī 2.2.10` into concrete reader segments, including references that resolve to more than one segment.

**Architecture:** Keep human browse structure in `work_map_nodes` and add a separate catalog-level citation reference index for machine lookup. Source adapters emit native citation references when local metadata is available; the reader service first tries exact address lookup, then compact work-reference parsing, then citation-index lookup.

**Tech Stack:** Python dataclasses, DuckDB catalog/book databases, existing reader adapters/storage/service, pytest via `just test`.

---

## Design Notes

- `work_map_nodes` remains for tables of contents: books, chapters, sections, padas, and other reader-facing browse nodes.
- The citation reference index is for addressability: a single external reference can map to one or more `ReaderSegment` rows.
- Existing book `addresses` stay one-to-one because `addresses.address` is currently a primary key. Multi-segment references belong in the catalog index.
- DCS CoNLL-U files can supply native Sanskrit references from `## chapter`, `# sent_counter`, and `# sent_subcounter` without hand-curating every verse.
- Latin and Greek compact dictionary citations should resolve through curated aliases plus normalized citation paths, not through FTS.
- FTS remains useful for corroboration and discovery, but exact references should not depend on matching inflected text such as `vinum` versus `vina`.

## File Responsibilities

- `src/langnet/reader/citation_references.py`: normalize compact reference strings, parse DCS chapter/counter references, and build reference variants.
- `src/langnet/reader/models.py`: define `ReaderCitationReference`.
- `src/langnet/reader/adapters.py`: attach native DCS citation references to parsed books.
- `src/langnet/reader/builder.py`: register parsed citation references into the catalog after surviving works are known.
- `src/langnet/reader/storage.py`: create/register/query the citation reference table.
- `src/langnet/reader/service.py`: expose multi-segment resolution from `reader resolve-address`.
- `tests/test_reader_adapters.py`, `tests/test_reader_storage.py`, and `tests/test_reader_enumeration.py`: cover parser, storage, and service behavior.

## Tasks

- [ ] Add failing tests for DCS references, including `BhG 9.2` resolving to two segments.
- [ ] Add failing tests for compact Latin references using a `Lucr.` alias and `2, 391` punctuation normalization.
- [ ] Add citation-reference normalization and DCS native reference generation.
- [ ] Add catalog schema, registration, deletion, and lookup helpers.
- [ ] Wire parsed references through the builder.
- [ ] Update `ReaderService.resolve_address` to return `segments`, `resolution_status`, and backward-compatible `segment`.
- [ ] Verify targeted tests and at least one real catalog lookup when the built catalog is available.

