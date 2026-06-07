# Electronic Text Acquisition Research: Giordano Bruno and Ramon Llull

Research date: 2026-06-07

Method: targeted Firecrawl web searches and scrapes, saved under `.firecrawl/`.

## Acquisition Ranking

Preferred electronic formats:

- Direct HTML/plain text pages.
- Archive.org `_djvu.txt`, EPUB, DjVu XML, Abbyy, or text PDF derivatives.
- Digitized object pages with downloadable PDF/images.
- OCR/PDF extraction only when no better source exists.

## Giordano Bruno

Status: strong candidate for near-term import.

### Source: Esoteric Archives Bruno pages

URL: `https://www.esotericarchives.com/bruno/`

Firecrawl output:

- `.firecrawl/source-esotericarchives-bruno.md`

What it provides:

- A curated index of selected Bruno writings.
- Multiple Latin HTML works.
- Clear per-work links.

Latin works visible in the scraped index:

- `De Umbris Idearum`
- `Ars Memoriae`
- `Cantus Circaeus`
- `Ars Reminiscendi -- Triginta Sigilli`
- `Explicatio triginta sigillorum`
- `De Magia`
- `Theses De Magia`
- `Magia Mathematica`
- `De vinculis in genere`

Importability:

- High.
- HTML page extraction should be straightforward after boilerplate stripping.
- This should be treated as an electronic reading edition/source witness.

Recommended first import:

- Mirror or scrape only the Bruno section.
- Build one extractor for Esoteric Archives HTML pages.
- Preserve original page URL and extracted page title.
- Spot-check Latin body extraction on `De Umbris Idearum`, `De Magia`, and `De vinculis in genere`.

### Source: Archive.org Bruno Latin volumes

Archive item: `jordanibruninola11brun`

URL: `https://archive.org/details/jordanibruninola11brun`

Metadata URL: `https://archive.org/metadata/jordanibruninola11brun`

Firecrawl output:

- `.firecrawl/source-archive-meta-bruno-jordanibruninola11brun.json`

Title:

- `Jordani Bruni Nolani opera latine conscripta publicis sumptibus edita`

Useful derivatives found:

- `jordanibruninola11brun_djvu.txt`
- `jordanibruninola11brun.epub`
- `jordanibruninola11brun.pdf`
- `jordanibruninola11brun_abbyy.gz`
- `jordanibruninola11brun_djvu.xml`
- `jordanibruninola11brun_hocr_searchtext.txt.gz`

Archive item: `operalatineconsc02brun`

URL: `https://archive.org/details/operalatineconsc02brun`

Metadata URL: `https://archive.org/metadata/operalatineconsc02brun`

Firecrawl output:

- `.firecrawl/source-archive-meta-bruno-operalatineconsc02brun.json`

Title:

- `Opera Latine conscripta`

Useful derivatives found:

- `operalatineconsc02brun_djvu.txt`
- `operalatineconsc02brun.epub`
- `operalatineconsc02brun.pdf`
- `operalatineconsc02brun_abbyy.gz`
- `operalatineconsc02brun_djvu.xml`
- `operalatineconsc02brun_hocr_searchtext.txt.gz`

Importability:

- Medium-high.
- Archive derivatives give usable electronic text, but likely OCR cleanup and volume/table-of-contents splitting are needed.
- Best path is Archive metadata downloader plus derivative-text staging.

Recommended use:

- Use Archive volumes as coverage/backup and for works absent from Esoteric Archives.
- Use `_djvu.txt` for quick staging.
- Use DjVu XML/Abbyy if page boundaries and OCR correction are needed.

## Ramon Llull / Raimundus Lullus

Status: valuable target, but not as immediately importable from open electronic Latin text.

### Source: Science History Institute Digital Collections

URL: `https://digital.sciencehistory.org/works/txt90sk`

Firecrawl output:

- `.firecrawl/source-sciencehistory-llull-ars-brevis.md`

Title:

- `Ars brevis and Ars abbreviata praedicandi, versio latinus II`

What it provides:

- Digitized manuscript object.
- Public Domain rights mark.
- Downloadable PDF and image files.
- It appears to be image/PDF-oriented rather than clean electronic text.

Importability:

- Medium-low for immediate text import.
- Good provenance and public-domain posture.
- Would likely require OCR/PDF/image extraction.

Recommended use:

- Treat as a candidate for an OCR extraction pipeline, not as the first Llull import unless no better text exists.

### Source: Archive.org selected works

Archive item: `selectedworksofr00v1llul`

URL: `https://archive.org/details/selectedworksofr00v1llul`

Metadata URL: `https://archive.org/metadata/selectedworksofr00v1llul`

Firecrawl output:

- `.firecrawl/source-archive-meta-llull-selectedworksofr00v1llul.json`

What it provides:

- Derivative EPUB and text PDF are present in metadata, but several files are marked private.
- This appears to be translated/selected works rather than a clean Latin corpus source.

Importability:

- Low-medium.
- Useful for bibliography or translation-facing context, not the best Latin reader import source.

### Source: Corpus Christianorum / Raimundi Lulli Opera Latina

URL: `https://www.corpuschristianorum.org/cccm-lullus`

Firecrawl output:

- `.firecrawl/source-corpus-christianorum-lullus.md`

What it provides:

- Scholarly series context for `Raimundi Lulli Opera latina`.
- Notes that the edition is expected to run to approximately 55 volumes.
- Notes 44 volumes published as of January 2026.

Importability:

- Low for open import.
- This is important bibliographic/contextual infrastructure, but it is not an obvious open electronic text source.

Recommended use:

- Use as a bibliographic authority for work lists and desired coverage.
- Do not depend on it for raw text unless we have licensed access or another open electronic form.

### Source: University of Barcelona Ramon Llull Documentation Center

URL: `https://www.ub.edu/portal/web/philology-communication/centre-de-documentacio-ramon-llull`

Firecrawl output:

- `.firecrawl/source-ub-ramon-llull-documentation-center.md`

What it provides:

- Institutional documentation center lead.
- Useful for bibliography/source discovery.

Importability:

- Unknown/low from this page alone.
- Worth deeper site-specific research, likely through catalogs/databases rather than direct text.

## Recommendation

### Bruno

Proceed with an acquisition spike.

First implementation target:

- Esoteric Archives Bruno HTML extractor.
- Archive.org metadata downloader for Bruno Opera volumes.
- Staging output under `data/build/reader_import_staging/bruno/`.

Acceptance:

- At least three Bruno Latin works staged as clean reading text.
- Archive metadata manifest recorded for two Archive items.
- Source URL and retrieval method preserved.

### Llull

Create a watchlist/acquisition research task, but do not promise near-term import until a better open text source is found.

Next research targets:

- Llull DB / University of Barcelona databases.
- Narpan / `quiesramonllull` pages.
- Archive.org and HathiTrust item lists for Editio Moguntina volumes.
- Any public-domain Latin editions with `_djvu.txt` derivatives.

Acceptance for a future Llull import:

- At least one Latin work available in extractable text or OCR derivative.
- Provenance sufficient to identify work/title/source.
- OCR/text quality spot-check passes.
