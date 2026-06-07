# Reader Collection Expansion Master Tracker

> **Purpose:** This is the master work tracker for expanding LangNet / Project Orion's reader collection while preserving provenance, source quality, and learner-facing usefulness.

## Goal

Build a higher-quality reader library across Latin, Greek, and Sanskrit by adding high-value works through manifest-backed, source-controlled acquisition. The project should prioritize works that users actually want to read, while also building the reference constellation that makes Project Orion feel like a real humanist library.

This is not a bulk-ingestion plan. Every expansion target must move through:

- source discovery
- source-role classification
- manifest creation
- raw/source artifact capture
- staged sample
- readability and boundary review
- import only after the sample is acceptable
- source-index export and quality-scorecard update

## Working Principles

- Prefer open-access or run-your-own-mirror sources.
- Do not use subscription databases as text acquisition sources.
- Treat source manifests as mandatory before reader import.
- Preserve raw witnesses unchanged.
- Keep learner-facing cleanup as derived text with an explicit policy.
- Distinguish OCR correction from orthographic modernization.
- Keep translations out of source-work imports unless explicitly modeled as translations.
- For contested corpora, expose attribution status rather than flattening it.
- For scientific works, do not import until formulas, diagrams, tables, propositions, and scholia have a source/display policy.

## Master Scorecards And Artifacts

- `data/reference/ogl_import_audit/orion_humanist_mystical_acquisition_scorecard.tsv`
- `data/reference/ogl_import_audit/popular_latin_acquisition_scorecard.tsv`
- `data/reference/ogl_import_audit/pl_pg_acquisition_source_scorecard.tsv`
- `data/reference/ogl_import_audit/pl_pg_acquisition_next_steps.tsv`
- `data/reference/reader_quality_audit/current_known_issues.tsv`
- `data/curated/reader_library_watchlist/high_value_targets.yaml`
- `docs/plans/active/infra/READER_GOALS_COORDINATION_PLAN.md`
- `docs/plans/active/infra/LANGNET_CORPUS_BUILDING_AND_ACQUISITION_PLAN.md`

## Active Lanes

### 1. Near-Term Reader Import Lane

These targets are closest to improving the live reader collection.

| Rank | Target | Status | Cost | Next action |
| --- | --- | --- | --- | --- |
| 1 | Nicolaus Cusanus, `De docta ignorantia` | `sample_staged_source_control_partial` | low-medium | Replace Archive wrapper with clean hOCR/searchtext parsing if needed, then promote Cusanus sample to import staging if boundaries remain stable. |
| 2 | Popular Latin prose pilot, likely Caesar or Sallust | `needs_source_review` | low-medium | Create first source manifest from open/mirrorable witness after checking existing catalog coverage. |
| 3 | Ficino, `De vita libri tres` | `source_candidate_verified` | medium-high | Compare 1489/1529/1549 text derivatives and select the cleanest opening sample. |
| 4 | Bruno, one Latin memory/magic work | `planned` | medium-high | Choose one source path and create a source manifest before staging. |

Acceptance:

- At least one target reaches staged sample with clean Latin text, stable boundaries, and source-control evidence.
- Import only after source-index fields can be populated accurately.
- `/library` and `reader works` expose aliases and acquisition provenance.

### 2. Humanist, Scholastic, Mystical Library Lane

These define the Project Orion humanist library identity.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| Agrippa, `De occulta philosophia` | `deferred_lexeme_cleanup_needed` | high | Source and sample exist, but 1533 OCR needs long-s/f and lexeme-level cleanup policy. |
| Ficino, `De vita libri tres` | `source_candidate_verified` | medium-high | Multiple Archive witnesses; likely next after Cusanus. |
| Cusanus, `De docta ignorantia` | `sample_staged_source_control_partial` | low-medium | Best current import candidate. |
| Bruno, Latin memory/magic/philosophy works | `planned` | medium-high | Strong Project Orion identity fit. |
| Albertus Magnus | `needs_source_review` | high | Must distinguish authentic Albertus from pseudo-Albertine works. |
| Paracelsus | `needs_source_review` | high | Latin-only filtering and pseudo-attribution handling required. |
| Ramon Llull | `needs_ocr` | medium-high | Existing research points to OCR/PDF unless clean Latin source is found. |
| Aquinas | watchlist target | medium/high unknown | Needs source decision and scorecard row. |
| Duns Scotus | watchlist target | high | Corpus scale and source complexity likely high. |
| Pico | `needs_source_review` | medium | Useful bridge for Ficino/Plotinus/cabala/humanist synthesis. |
| Plethon | `needs_source_review` | uncertain | Likely relationship/reference metadata first. |

Acceptance:

- Each target has explicit language support: Latin, Greek, or Sanskrit only.
- Contested authorship and pseudo-corpora are modeled in metadata.
- Relationship edges are source-backed: teacher, patron, translator, manuscript supplier, influence, opponent, school, or reception link.

### 3. Popular Classical Latin Lane

This lane addresses common reader demand and classroom/self-study usefulness.

Initial queue:

- Caesar, `De bello Gallico`
- Vergil, `Aeneid`
- Ovid, `Metamorphoses`
- Cicero, `In Catilinam`
- Catullus, `Carmina`
- Horace, `Odes`
- Sallust, `Bellum Catilinae` and `Bellum Iugurthinum`
- Tacitus, starting with `Agricola` and `Germania`

Acceptance:

- Verify existing catalog coverage before importing duplicates.
- Prefer prose-first imports when possible because book/chapter boundaries are simpler.
- Preserve canonical citation shape: book/chapter, speech/section, poem number, or book/line.

### 4. Scientific Latin Lane

High-value, but more expensive because ordinary prose segmentation is not enough.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| Newton, `Principia` | `source_candidate_identified` | high | Propositions, scholia, formulas, diagrams. |
| Kepler, `Astronomia nova`, `Harmonices mundi` | `source_candidate_identified` | high | Diagrams, tables, astronomical notation. |
| Euler, `Mechanica` and broader works | `source_candidate_verified` | high | Archive OCR exists; Euler Archive has 850+ work identity-control pages. |

Acceptance:

- Define formula/diagram/table policy before staging.
- Preserve proposition/scholium/corollary citation structure.
- Do not damage mathematical notation during text extraction.

### 5. Reference Constellation Lane

This makes Orion more than a text dump.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| Suda author/person bios | `imported_needs_reference_index` | medium | Already imported as First1KGreek reader work; needs structured lookup layer. |
| Orion of Thebes / Greek etymologica | `needs_inventory` | medium | Project identity target; inventory current lexicographic works first. |
| Pseudo-Zonaras, Stephanus Byzantius, other lexica | present/unknown | medium | Need inventory and source-role classification. |

Acceptance:

- Author/person cards can resolve to Suda/reference entries.
- Greek lookup can surface etymological/reference witnesses.
- UI cast-of-characters figures resolve to reader works, reference entries, or acquisition targets.

### 6. Specialist Corpus Depth Lane

PL/PG/CSEL remain important, but should not crowd out more directly useful reader targets.

| Target | Status | Cost | Notes |
| --- | --- | --- | --- |
| PL122 / Eriugena | imported | completed pilot | Fourteen works imported and source-indexed. |
| PG pilot | imported sample | high | OCR noise/segmentation calibration needed before broad PG. |
| CSEL61 / Prudentius | `source_candidate_verified` | medium-high | Candidate found; PDF/OCR parsing and sample staging pending. |
| Full PL/PG expansion | planned/deferred | very high | Massive corpus; proceed volume-by-volume or target-by-target. |

Acceptance:

- Each volume/series expansion has a manifest before import.
- OCR and segmentation risks are tracked before broad import.
- Source-index snapshots remain accurate.

## Cost Model

| Cost | Typical source type | Examples |
| --- | --- | --- |
| Low | Clean electronic text with clear structure | Wikisource Cusanus if source-control passes |
| Low-medium | Clean text plus one control witness | Cusanus with Archive cross-check |
| Medium | Archive OCR from later/cleaner print | Some Ficino or CSEL candidates |
| Medium-high | HTML/source-specific cleanup or mixed editions | Bruno, Llull if source text is found |
| High | Early print OCR, long-s/ligatures, pseudo-corpora | Agrippa, Albertus, Paracelsus |
| High | Scientific notation, diagrams, tables | Newton, Kepler, Euler |
| Very high | Bulk corpus acquisition | Full PL/PG/CSEL expansion |

## Current Best Work Order

1. Finish Cusanus source-control and promote to import staging if acceptable.
2. Create first popular Latin source manifest, preferably Caesar or Sallust.
3. Compare Ficino witnesses and stage one opening sample.
4. Pick one Bruno Latin work and create a source manifest.
5. Inventory Suda/Orion/etymologica reference coverage.
6. Add Aquinas and Duns Scotus to the humanist/mystical scorecard with explicit source-path decisions.
7. Define scientific Latin display policy before Newton/Kepler/Euler staging.
8. Return to Agrippa once lexeme-level OCR cleanup policy exists.
9. Continue CSEL61 and PG only through sample-first gates.

## Done This Session

- PL122/Eriugena cleaned, staged, imported, and source-indexed.
- PL/PG/CSEL scorecards and source-role language updated.
- UChicago PLD bibliography added as PL identity/worklist evidence.
- CSEL61 source candidate identified and manifest updated.
- Popular Latin acquisition scorecard created.
- Humanist/mystical acquisition scorecard created.
- Agrippa manifest and sample created, then deferred for lexeme-level cleanup.
- Ficino manifest created with three candidate witnesses.
- Cusanus manifest created and clean Wikisource sample staged.
- Newton, Kepler, and Euler added as scientific Latin targets.
- Euler `Mechanica` manifest created.
- Suda/Orion reference constellation lane defined.

## Immediate Next Checkpoint

Cusanus should be the next concrete import candidate if source-control review passes.

Required before import:

- Confirm clean text boundaries for Dedicatio and Liber primus.
- Decide whether Archive hOCR/searchtext parsing is needed for control.
- Generate import-ready staging records with source-index fields.
- Add or update quality audit row if source uncertainty remains.
