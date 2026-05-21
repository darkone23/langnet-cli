> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# Bailly Structural Extraction Iteration Plan

## Goal

Create a structural extraction loop for Bailly entries that uses Bailly.app as a gold shape/content reference and prepares PDF layout extraction without semantic interpretation.

## Scope

This iteration builds the local extraction loop:

- Parse scraped Bailly.app markdown into ordered structural blocks.
- Parse Poppler `pdftohtml -xml` page files into geometry-preserving text chunks.
- Use structural path keys such as `00`, `01`, `01:00`, `01:00:00`, and `02`.
- Keep entry lifetime explicit: a word opens at a layout-detected headword and closes when the next headword opens.
- Attach continuation-only pages to the currently open entry.
- Preserve text anchors and marker order.
- Avoid semantic labels such as learner gloss, citation meaning, or definition type.
- Build the DuckDB only from PDF-derived structural JSONL, not from Bailly.app scrapes.

Bailly.app scrapes remain verification fixtures for difficult entries.

## Structural Source Notes

- Dictionary body currently starts on physical PDF page 81 and ends on page 2574. Page 2575 is blank; page 2576 starts the Greek numeration appendix.
- Body pages with text but no new headword are continuation candidates. Examples include `γίγνομαι` on page 544 and `εἰ` on pages 747-748.
- Front-matter `SIGNES USUELS` says `E` indicates particularities attached to the dictionary article, `||` marks article divisions, and `*`, quantity marks, `=`, `+`, `×`, and prefix/suffix hyphen signs have conventional visual meanings. We should preserve these visible markers structurally or textually without translating them into semantic categories.

## Phases

1. @architect: Keep the schema minimal: `lemma`, `source`, `blocks`, and path-keyed structural blocks.
2. @coder: Add tests and implementation for Bailly.app markdown structural parsing.
3. @coder: Add tested Poppler XML page parsing, body-boundary classification, page audit, book-level entry open/close extraction, and JSONL export.
4. @auditor: Review fixture output for overinterpretation, noisy scrape bleed, and structural path drift.

## Verification

- `just test test_bailly_structural_parser test_bailly_pdf_xml test_bailly_xml_audit test_bailly_xml_extract_cli test_cli_help`
- `just cli -- bailly-xml-audit /home/nixos/digital-bailly-pdf/xml-pages --output examples/debug/bailly-xml-audit.tsv`
- `just cli -- bailly-xml-extract /home/nixos/digital-bailly-pdf/xml-pages --output examples/debug/bailly-structural-extract.jsonl`
- `just cli-databuild bailly --source examples/debug/bailly-structural-extract.jsonl --output examples/debug/bailly-structural.duckdb --wipe`
- Spot-check generated blocks against scraped `ἀγελαῖος` and difficult long entries such as `γίγνομαι` and `εἰ`.
