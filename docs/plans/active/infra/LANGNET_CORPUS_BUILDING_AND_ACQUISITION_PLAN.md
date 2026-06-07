# LangNet Corpus Building and Acquisition Plan

> **For agentic workers:** This is the umbrella plan for building LangNet's reader corpus from disparate electronic sources. Work from source manifests and staging outputs first; do not import raw web/OCR output directly into the reader catalog.

**Goal:** Define what it means for LangNet to build a corpus, how we acquire and stage texts, how we preserve provenance and quality status, and how we prepare for larger-disk server migration.

## Open Knowledgebase Policy

LangNet treats its classical corpora and source trees as open scholarly knowledgebase data. The working assumption for CSEL, Patrologia, Church Fathers, and similar legacy corpora in this project is that the source material is free to use without restriction, and that derived databases produced by LangNet may publish the content they contain without restriction.

The acquisition process is therefore not a permission gate. It is a provenance, source-role, and quality-control process:

- Preserve where a reading witness, bibliographic fact, scan locator, or OCR output came from.
- Distinguish copied/source text from derived facts, normalized metadata, segmentation, collation, and parser output.
- Prefer public-domain and scholarly source traditions over restricted modern editions.
- Avoid treating a catalog, search page, scan locator, or database UI as clean reader text when it is only evidence for source discovery.
- Build a higher-quality derived knowledgebase by normalizing, collating, checking, and documenting imperfect upstream material.

Facts such as author names, work titles, volume ids, document ids, column ranges, source relationships, and coverage gaps are first-class derived knowledgebase data.

Subscription-only databases are not acquisition targets. They may be useful for
publicly visible bibliography, naming, or comparison context, but LangNet should
not depend on them for reader text. Prefer sources that support an open-access,
run-your-own-mirror posture: public source trees, stable site mirrors,
downloadable PDF/OCR witnesses, open bibliographic lists, or local reproducible
checkouts. The Library of Latin Texts is therefore tracked only as comparison
context, not as a text-import source.

## Definition: What It Means To Build A Corpus

For LangNet, building a corpus means moving a text through a controlled lifecycle:

- Identify a target author/work/source.
- Locate one or more electronic witnesses.
- Record source provenance and source-use role.
- Acquire raw source files or a reproducible retrieval manifest.
- Extract readable text into staging.
- Segment the text into reader-friendly units.
- Attach metadata: language, author, title, source, period, region, tradition, quality.
- Import into the reader catalog.
- Index for search, lookup, morphology, and Library discovery.
- Expose provenance and quality status in CLI/API/UI.
- Allow correction overlays and future replacement without losing original source witness history.

The reader catalog is not a claim of critical-edition authority. It is a library of electronic reading editions and source witnesses at known quality levels.

## Source Quality Model

Each imported source should carry source-level and work-level quality labels.

Recommended values:

- `machine_text_clean`: direct electronic text with minimal obvious noise.
- `machine_text_needs_segmentation`: clean text but needs structural splitting.
- `html_needs_boilerplate_strip`: HTML source where body extraction is required.
- `ocr_usable_with_artifacts`: OCR text is readable but has headers/footers/artifacts.
- `ocr_needs_correction`: OCR text exists but requires cleanup before learner display.
- `image_pdf_needs_ocr`: source images/PDF exist but no usable text layer yet.
- `mixed_provenance_needs_spot_check`: source origin/edition varies or is unclear.
- `metadata_only`: known work/source but no usable text yet.
- `wanted`: desired author/work with no current source.

UI wording:

- Use "electronic reading edition", "source witness", "OCR-derived text", and "needs correction".
- Avoid implying that any current reader text is a definitive critical edition.

## Data Layout

Current repo layout already has:

- `data/build/reader/`: generated reader catalog and book artifacts.
- `data/curated/`: hand-curated overlays, aliases, work maps, metadata, attributions.
- `data/generated/`: generated metadata/classification outputs.
- `data/reference/reader_source_index/`: checked-in flat provenance snapshots.
- `data/cache/`: local caches.

Add acquisition/staging layout:

```text
data/
├── sources_external/                 # Raw or mirrored upstream source material; may move off-repo
│   ├── latin_library/
│   │   ├── manifest.yaml
│   │   └── raw/
│   ├── archive_org/
│   │   └── <identifier>/
│   │       ├── manifest.yaml
│   │       ├── metadata.json
│   │       └── raw/
│   ├── esotericarchives/
│   │   └── bruno/
│   │       ├── manifest.yaml
│   │       └── raw/
│   └── ocr/
│       └── <source_id>/
│           ├── manifest.yaml
│           ├── images/
│           ├── model_outputs/
│           └── reviewed/
├── build/
│   └── reader_import_staging/
│       ├── latin_library/
│       ├── archive_org/
│       ├── bruno/
│       └── llull/
└── curated/
    └── reader_library_axes/
        ├── authors/
        ├── works/
        └── watchlist/
```

Git policy:

- Commit source manifests, curated metadata, extractor code, small source indexes, and reference TSVs.
- Do not blindly commit large raw mirrors, PDFs, image sets, or OCR intermediate directories.
- When raw source material is too large for Git, record its location and checksum in `manifest.yaml`.
- Revisit this after server migration; large corpora may belong on mounted storage with reproducible manifests in Git.

## Source Manifest Schema

Use YAML for human-readable manifests.

Suggested fields:

```yaml
source_id: archive_org:jordanibruninola11brun
label: Jordani Bruni Nolani opera latine conscripta
source_type: archive_org
homepage_url: https://archive.org/details/jordanibruninola11brun
metadata_url: https://archive.org/metadata/jordanibruninola11brun
retrieved_at: 2026-06-07
retrieval_method: archive_metadata_derivative
raw_storage: data/sources_external/archive_org/jordanibruninola11brun/raw
selected_derivative: jordanibruninola11brun_djvu.txt
source_use_note: Open source witness; preserve Archive item metadata and derivative provenance.
quality_status: ocr_usable_with_artifacts
language: lat
authors:
  - Giordano Bruno
works:
  - title: De umbris idearum
    status: candidate
notes:
  - OCR and volume splitting require spot-check.
checksums: []
```

## Acquisition Lanes

### Lane 0: Popular classical Latin canon

The reader should not only expand by series such as PL, PG, and CSEL. Those are
valuable depth lanes, but many users first look for the common Latin works used
in classrooms, reading groups, and self-study.

Priority targets:

- Caesar, `De bello Gallico`
- Vergil, `Aeneid`
- Ovid, `Metamorphoses`
- Cicero, `In Catilinam`
- Catullus, `Carmina`
- Horace, `Odes`
- Sallust, `Bellum Catilinae` and `Bellum Iugurthinum`
- Tacitus, starting with `Agricola` and `Germania`

Policy:

- Prefer open/mirrorable witnesses, not subscription databases.
- Check existing reader catalog coverage before staging; if a work exists but is hard to find, fix aliases/search before importing duplicates.
- Stage one high-demand prose work first, preferably Caesar or Sallust, because book/chapter segmentation is simpler than poetry lineation.
- Preserve canonical citation shape: book/chapter, speech/section, poem number, or book/line as appropriate.
- Treat this lane as the learner-facing acquisition lane; PL/PG/CSEL remain high-value specialist/depth lanes.

Tracking artifact:

- `data/reference/ogl_import_audit/popular_latin_acquisition_scorecard.tsv`

### Lane 0b: Humanist, scholastic, and mystical source library

This is the Project Orion humanist-library lane: a curated library of Latin and
Greek source works around Platonism, scholastic natural philosophy, occult
philosophy, medicine, memory, etymology, and Christian/mystical transmission.

Priority targets:

- Agrippa, `De occulta philosophia libri tres`
- Ficino, `De vita libri tres` and Plotinus-related prefaces/commentary context
- Bruno, Latin memory/magic/philosophy works
- Albertus Magnus, natural philosophy works with attribution controls
- Paracelsus, Latin-only works and clearly marked pseudo-Paracelsian witnesses
- Llull, `Ars brevis` and Latin combinatorial/logical works
- Pico, `Oratio`, `Conclusiones`, and related Latin works
- Plethon, Greek works/reference witnesses and relationship metadata
- Suda, author/person bios as a structured reference substrate
- Orion of Thebes and Greek etymologica for lookup/reference enrichment

Policy:

- Stay within supported source languages: Latin, Greek, and Sanskrit.
- Do not import translations as source works unless they are explicitly modeled as translations or metadata.
- Prefer open/mirrorable witnesses and local reproducible checkouts.
- Make attribution status visible for pseudo-Albertine, pseudo-Paracelsian, Hermetic, Dionysian, and other contested corpora.
- Treat Suda and etymologica as reference works as well as reader works; they should support author bios, term lookups, and UI cast coverage.
- Record relationship edges as curated metadata when source-backed: patron, teacher, translator, dedicatee, manuscript supplier, influence, opponent, school, or reception link.

Tracking artifact:

- `data/reference/ogl_import_audit/orion_humanist_mystical_acquisition_scorecard.tsv`

### Lane A: Direct electronic text

Examples:

- Project Gutenberg plain text.
- Site HTML with stable pages.
- EPUB with clean text.

Pipeline:

- Download/scrape source.
- Strip boilerplate if needed.
- Normalize Unicode and whitespace.
- Segment by headings or paragraphs.
- Stage as JSON/flat text.

### Lane B: Site mirror

Examples:

- Latin Library.
- Esoteric Archives Bruno section.

Pipeline:

- Polite mirror or targeted scrape.
- Record mirror command and source notice.
- Build source-specific extractor.
- Import selected target pages first.

### Lane C: Archive.org derivative

Examples:

- Bruno `jordanibruninola11brun`.
- Bruno `operalatineconsc02brun`.
- Francis Bacon, Thomas More, Spinoza, Duns Scotus candidates.

Pipeline:

- Fetch Archive metadata endpoint.
- Select best derivative in this order: `_djvu.txt`, EPUB, DjVu XML, Abbyy, Text PDF.
- Stage text and manifest.
- Spot-check OCR and split works only after derivative quality is known.

### Lane D: Wikisource electronic text

Examples:

- Latin Wikisource `Patrologia Latina/122`.
- Latin Wikisource individual work pages linked from a volume table of contents.

Pipeline:

- Use the volume/index page to identify works, authors, and PL/CSEL-style references.
- Prefer individual work pages when they contain full text.
- Preserve Wikisource page URL, linked source scan/file URL, author/title label, and volume reference.
- Record page quality/proofread status when available.
- Treat Wikisource as an electronic reading source witness, not as a critical edition.
- Cross-check high-value rows against Archive.org or another source when possible.

Strengths:

- Often already split at the work level.
- Good for table-of-contents and author/title legitimacy checks.
- Can bridge gaps where OGL lacks a volume, such as PL122 for Eriugena.

Risks:

- Page completeness and proofreading status vary.
- Wikimedia page/source metadata should be preserved before bulk import.
- Some pages may contain only an index, not full text.
- Markup/transclusion may require a Wikisource-specific extractor.

Recommended first target:

- `https://la.wikisource.org/wiki/Patrologia_Latina/122`
- Author/work target: Joannes Scotus Erigena.
- Initial works:
  - `De divisione naturae`
  - `De praedestinatione`
  - `Expositiones super Ierarchiam caelestem S. Dionysii`
  - `Versio operum S. Dionysii`

### Lane E: OCR/PDF/image extraction

Examples:

- Science History Institute Llull `Ars brevis`.
- Archive/HathiTrust scans without clean derivatives.

Pipeline:

- Download PDF/images.
- Run OCR model or text extraction.
- Store raw OCR outputs separately from reviewed text.
- Mark quality as `ocr_needs_correction` until reviewed.
- Promote to `ocr_usable_with_artifacts` only after spot-check.

OpenRouter/OCR note:

- It is acceptable to add an OpenRouter-backed OCR or cleanup pipeline later.
- The first version should be batch/offline, source-manifest driven, and reproducible.
- Model outputs must be attributed as derived cleanup, not original source text.
- Keep original source image/PDF reference and OCR output side-by-side.

### Lane F: Patrologia/CSEL series acquisition

Examples:

- Patrologia Latina missing volumes, especially `PL122` for Joannes Scotus Eriugena.
- Patrologia Graeca full-corpus acquisition, since no local PG checkout is currently present.
- CSEL missing volume ranges identified by the external scorecard.

Pipeline:

- Start from `data/reference/ogl_import_audit/pl_pg_acquisition_source_scorecard.tsv`.
- Confirm whether a missing work is absent from local source files or merely skipped by the importer.
- For PL, prefer Latin Wikisource for table-of-contents and work-level identity checks, then Archive.org PL 1-221 for missing-volume acquisition, then Corpus Corporum if usage allows.
- For PG, prototype against Open Patrologia Graeca / OGL-PatrologiaGraecaDev first, then compare Calfa OCR and Archive.org volume OCR as quality benchmarks or fallbacks.
- For CSEL, use the external scorecard to target missing base volume ids before doing work-level audits.
- Record every chosen source in a source manifest before importing text into the reader catalog.
- Preserve series metadata such as volume id, column/page references when available, source witness, OCR quality, and work boundary confidence.

Do not treat Patrologia or CSEL as a single clean corpus. They are series-level umbrellas with multiple possible witnesses, partial local checkouts, alternate source views, OCR quality differences, and uncertain work boundaries.

Current control artifacts:

- `data/reference/ogl_import_audit/pl_pg_acquisition_source_scorecard.tsv`: source ranking and roles.
- `data/reference/ogl_import_audit/pl_pg_acquisition_next_steps.tsv`: prioritized work queue.
- `data/sources_external/patrologia_latina/pl122/manifest.yaml`: PL122/Eriugena acquisition manifest.
- `data/sources_external/patrologia_graeca/pilot/manifest.yaml`: PG pilot acquisition manifest.

## Target Author/Work Register

### Near-term high-confidence targets

Patrologia Latina `PL122` / Joannes Scotus Eriugena:

- Source lane: Patrologia/CSEL series acquisition.
- Sources:
  - `https://la.wikisource.org/wiki/Patrologia_Latina/122`
- `https://archive.org/details/patrologia-latina_1-221`
- `https://archive.org/details/patrologiaecursu122mign`
- Initial works:
  - `De divisione naturae`
  - `De praedestinatione`
  - `Expositiones super Ierarchiam caelestem S. Dionysii`
  - `Versio operum S. Dionysii`
  - `Homilia in prologum Evangelii secundum Joannem`
  - `Commentarius in Evangelium secundum Joannem`
  - `De egressu et regressu animae ad Deum`
  - `Expositiones super Ierarchiam ecclesiasticam S. Dionysii`
  - `Expositiones in Mysticam theologiam S. Dionysii`
- Current status: selected nine works are now imported as a pilot slice from Wikisource despite `PL122` being absent from the local OGL checkout.
- Quality expectation: Wikisource may provide work-level structure; Archive.org provides OCR/scans for cross-check and fallback.
- Acceptance: Eriugena appears in `reader works`, `reader source-index`, `/library`, and regenerated source-index TSVs with explicit PL122 provenance.

Patrologia Graeca pilot:

- Source lane: Patrologia/CSEL series acquisition.
- Sources:
  - `https://sites.tufts.edu/perseusupdates/2015/08/07/open-patrologia-graeca-1-0/`
  - `https://github.com/calfa-co/Patrologia-Graeca`
  - `https://patristica.net/graeca/`
- Initial work selection policy:
  - Pick one high-value author/work from an OGL PG volume with available raw text or hOCR.
  - Pick one overlapping Calfa volume to compare OCR text quality.
  - Pick one DCO or patristica.net page as table-of-contents corroboration, not as bulk text.
- Current status: no local Patrologia Graeca checkout has been found.
- Quality expectation: OCR-derived Greek/Latin text with page/column metadata preserved when available.
- Acceptance: one PG pilot source manifest, one staged text sample, one source-index-visible imported work, and a written quality comparison.

Giordano Bruno:

- Source lane: site HTML and Archive.org derivative.
- Sources:
  - `https://www.esotericarchives.com/bruno/`
  - `https://archive.org/details/jordanibruninola11brun`
  - `https://archive.org/details/operalatineconsc02brun`
- Initial works:
  - `De Umbris Idearum`
  - `Ars Memoriae`
  - `Cantus Circaeus`
  - `De Magia`
  - `De vinculis in genere`
- Quality expectation: HTML likely high; Archive OCR likely usable with artifacts.

Rene Descartes:

- Source lane: Latin Library and Project Gutenberg.
- Sources:
  - `https://www.thelatinlibrary.com/des.html`
  - `https://www.gutenberg.org/ebooks/23306`
- Initial work:
  - `Meditationes de prima philosophia`
- Quality expectation: strong electronic text candidate.

Anselm of Canterbury:

- Source lane: Latin Library.
- Source:
  - `https://www.thelatinlibrary.com/anselm.html`
- Initial works:
  - `Proslogion`
  - `Epistula ad Urbanum Papam`
- Quality expectation: strong HTML candidate, mixed provenance.

Thomas More:

- Source lane: direct PDF/e-text and Archive.org.
- Sources:
  - `https://essentialmore.org/e-texts/`
  - Archive.org complete works candidates.
- Initial works:
  - `Utopia`
  - `Epigrammata`
  - `Historia Richardi Tertii`
  - `Responsio ad Lutherum`
- Quality expectation: PDF parsing or OCR likely needed for some works.

### Medium-term targets needing source confirmation

Francis Bacon:

- Source lane: Archive.org and possible specialist resources.
- Sources discovered:
  - Archive.org `The Works of Francis Bacon`.
  - Princeton Bacon Latin Works page as bibliographic lead.
- Need: identify Latin original text availability and derivative quality.

Spinoza:

- Source lane: Archive.org and open editions.
- Sources discovered:
  - Archive.org `The Chief Works of Benedict de Spinoza`.
  - Liberty Fund pages may be translation-oriented.
- Need: identify Latin text source for `Ethica` and other Latin works.

Duns Scotus:

- Source lane: Archive.org, Franciscan Archive, specialist pages.
- Sources discovered:
  - Sydney Penner Duns Scotus page.
  - Franciscan Archive.
  - Archive.org secondary/selected material.
- Need: locate actual Latin electronic text, not only bibliography/translation.

Pseudo-Dionysius:

- Source lane: Greek HTML/direct text and possibly Latin translation sources.
- Sources discovered:
  - Ldysinger page for Greek/English `Mystical Theology`.
- Need: distinguish Greek Pseudo-Dionysius from Latin translations.

Joannes Scotus Eriugena:

- Promoted to near-term as Patrologia Latina `PL122` / Joannes Scotus Eriugena.
- Keep the Documenta Catholica Omnia author page as corroborating evidence, not as the default text source.
- Later follow-up: add `Versio Ambiguorum S. Maximi` and `Versus` after the initial PL122 extraction path is proven.

Axiochus:

- Source lane: Greek web text/Archive.
- Sources discovered:
  - ToposText work page.
  - Archive.org printed/OCR material.
- Need: locate Greek text in importable form and map as pseudo-Platonic.

### Harder/high-value targets

Ramon Llull / Raimundus Lullus:

- Source lane: OCR/PDF/image extraction and deeper source research.
- Sources:
  - Science History Institute digitized `Ars brevis`.
  - Corpus Christianorum `Raimundi Lulli Opera latina` as bibliographic authority.
  - University of Barcelona Ramon Llull Documentation Center.
  - Archive.org selected works candidate.
- Need: open Latin electronic source or OCR strategy.
- Quality expectation: likely OCR/review path.

Marsilio Ficino:

- Source lane: deeper research required.
- Sources discovered so far are mostly secondary or scholarly context.
- Need: locate public-domain Latin electronic text or OCRable editions.

Thomas Aquinas:

- Source lane: GitHub/Corpus Thomisticum/Index Thomisticus.
- Sources:
  - `https://github.com/Geremia/AquinasOperaOmnia`
  - Corpus Thomisticum.
  - Index Thomisticus Treebank for some structured material.
- Need: decide acceptable source and parser for large-scale Aquinas import.

## Server and Disk Migration Considerations

Problem:

- Raw mirrors, Archive derivatives, PDFs, image sets, OCR outputs, reader artifacts, and search indexes will exceed comfortable repo/server disk limits.

Principles:

- Keep Git as the control plane: manifests, code, metadata, small reference outputs.
- Keep bulky source data on mounted storage or external object storage.
- Make every bulky source reproducible from a manifest.
- Keep build outputs disposable where possible.

Recommended future layout on larger server:

```text
/srv/langnet/
├── repo/langnet-cli/
├── sources/
│   ├── latin_library/
│   ├── archive_org/
│   ├── esotericarchives/
│   └── ocr/
├── build/
│   ├── reader/
│   └── reader_import_staging/
├── cache/
└── logs/
```

Migration tasks:

- Add environment variables for source/build/cache roots.
- Default to repo-local `data/` paths for development.
- Support `/srv/langnet/...` paths for production/databuild.
- Ensure process-compose and just recipes can point to external data roots.
- Document rsync or rehydrate-from-manifest steps.

Candidate env vars:

- `LANGNET_DATA_ROOT`
- `LANGNET_SOURCE_ROOT`
- `LANGNET_BUILD_ROOT`
- `LANGNET_CACHE_ROOT`
- `LANGNET_READER_CATALOG_PATH`

## Implementation Phases

### Phase 1: Source acquisition framework

Tasks:

- Add manifest schema docs and examples.
- Add helper code for source manifests.
- Add Archive.org metadata downloader.
- Add staging directory conventions.
- Add tests for manifest parsing and derivative selection.

Acceptance:

- One Archive identifier can be resolved to a selected derivative plan.
- One source manifest can be read and displayed by CLI.

### Phase 2: Bruno proof of concept

Tasks:

- Stage Bruno HTML from Esoteric Archives.
- Stage Bruno Archive metadata and `_djvu.txt`.
- Spot-check three works.
- Import at least one Bruno work into reader catalog.

Acceptance:

- `just cli reader works --query bruno --limit 5 --output json` returns Bruno.
- `/library?q=bruno` shows Bruno with provenance.

### Phase 3: Latin Library proof of concept

Tasks:

- Mirror or targeted-download Anselm and Descartes pages.
- Extract body text.
- Import Descartes `Meditationes` and Anselm `Proslogion`.

Acceptance:

- `just cli reader works --query descartes --limit 5 --output json` returns `Meditationes`.
- `just cli reader works --query anselm --limit 5 --output json` returns `Proslogion`.

### Phase 4: OCR lane design

Tasks:

- Select one OCR candidate, likely Llull `Ars brevis`.
- Define input/output directory conventions.
- Decide whether to use local OCR, OpenRouter vision/OCR, or hybrid.
- Store model output separately from reviewed text.

Acceptance:

- A source with images/PDF can produce staged OCR text with quality labels.
- The original source and OCR model output are both preserved.

### Phase 5: Library UI integration

Tasks:

- Add `/library`.
- Add source-index explorer.
- Add acquisition/watchlist empty states.
- Add quality/provenance chips.

Acceptance:

- User can ask "do we have Bruno?" and see imported/staged status.
- User can ask "do we have Llull?" and see wanted/research/OCR-candidate status if not yet imported.

## Immediate Taskfile For Agent

@architect and @coder should start with Phase 1, not with a bulk import.

Task:

- Implement source manifest helpers and Archive.org derivative selection.
- Create example manifests for Bruno Archive items.
- Create source acquisition docs under `docs/technical/reader-source-acquisition.md`.
- Do not download large derivatives unless explicitly instructed.

Validation:

```bash
python -m py_compile src/langnet/reader/source_acquisition.py
just test test_reader_cli
```

Manual QA:

- Read the generated Bruno manifest.
- Confirm it identifies `_djvu.txt`, EPUB, DjVu XML, Abbyy, and Text PDF candidates.
- Confirm no large raw source files were committed accidentally.

## Relationship To Library Explorer

The Library Explorer is the UI and API surface for asking what we have.

This plan is the upstream supply chain for making the answer better.

The two should meet at:

- Source manifests.
- Source index rows.
- Work/library axis metadata.
- Watchlist/acquisition status.
- Quality/provenance chips.
