# Bruno and Llull Electronic Text Acquisition Plan

> **For agentic workers:** Use `docs/research/electronic-text-acquisition-bruno-llull.md` as the research basis before implementing. Preserve source provenance and quality labels for every staged text.

**Goal:** Add a practical acquisition path for Giordano Bruno and Ramon Llull/Raimundus Lullus to the LangNet reader library.

## Findings Summary

Giordano Bruno:

- Strong near-term candidate.
- Esoteric Archives has multiple Latin HTML works.
- Archive.org has Latin Opera volumes with `_djvu.txt`, EPUB, Text PDF, Abbyy, and DjVu XML derivatives.

Ramon Llull:

- High-value target, but open electronic Latin text is harder to locate.
- Science History Institute has a public-domain digitized `Ars brevis` manuscript object with PDF/images.
- Corpus Christianorum documents the major `Raimundi Lulli Opera latina` scholarly series but is not an obvious open text source.
- Archive.org has selected works material, but not yet a clean Latin corpus lead.

## Phase 1: Bruno HTML Staging

Files likely touched:

- Add: `src/langnet/reader/source_acquisition.py`
- Add: `src/langnet/databuild/bruno.py`
- Add tests under `tests/`
- Add staging output under `data/build/reader_import_staging/bruno/`

Tasks:

- Scrape or mirror `https://www.esotericarchives.com/bruno/`.
- Extract linked Latin work pages.
- Strip navigation/footer boilerplate.
- Preserve source page URL, page title, extraction timestamp, and extractor version.
- Stage each work as normalized text or segmented JSON.

Initial target works:

- `De Umbris Idearum`
- `Ars Memoriae`
- `Cantus Circaeus`
- `De Magia`
- `De vinculis in genere`

Validation:

```bash
python -m py_compile src/langnet/reader/source_acquisition.py src/langnet/databuild/bruno.py
```

Manual QA:

- Inspect first 100 lines of staged `De Magia`.
- Confirm the content is Latin body text, not page boilerplate.
- Confirm source URL is preserved.

## Phase 2: Bruno Archive.org Derivative Staging

Archive identifiers:

- `jordanibruninola11brun`
- `operalatineconsc02brun`

Tasks:

- Download Archive metadata JSON.
- Select best derivative in this order: `_djvu.txt`, EPUB, DjVu XML, Abbyy, Text PDF.
- Stage derivative text with manifest.
- Do not attempt full work splitting until page/TOC quality is understood.

Validation:

```bash
just cli reader source-index --query bruno --limit 5 --output json
```

Manual QA:

- Confirm Archive-derived text has usable Latin OCR.
- Identify headers/footers/noise patterns.
- Decide whether `_djvu.txt` is enough or DjVu XML/Abbyy is needed.

## Phase 3: Reader Catalog Import For Bruno

Tasks:

- Add Bruno as Renaissance/Neo-Latin author metadata.
- Import staged Bruno works into the reader catalog as electronic reading editions.
- Add provenance labels: `esotericarchives_html` and/or `archive_org_derivative`.
- Add Library axes: Renaissance, Italy, philosophy, magic/memory, Neo-Latin.

Acceptance:

- `just cli reader works --query bruno --limit 5 --output json` returns Bruno works.
- `/library?q=bruno` shows Bruno works and provenance.
- Reader can open at least one staged Bruno work.

## Phase 4: Llull Research Continuation

Tasks:

- Search for open Latin electronic texts of `Ars brevis`, `Ars magna`, and other Latin Llull works.
- Investigate Llull DB / University of Barcelona pathways.
- Investigate Archive/HathiTrust public-domain derivatives for Editio Moguntina or other older editions.
- Use Science History Institute digitized `Ars brevis` only if OCR extraction becomes worthwhile.

Acceptance before implementation:

- At least one extractable Latin text source is identified.
- Rights/provenance posture is recorded.
- OCR or text quality is spot-checked.

## Do Not Do Yet

- Do not import all Archive OCR blindly.
- Do not treat Corpus Christianorum metadata as text availability.
- Do not mix translations into Latin reader imports without explicit language/source labels.
- Do not hide OCR uncertainty from the Library UI.
