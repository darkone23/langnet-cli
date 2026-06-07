# OpenGreekAndLatin Importer Audit And Fix Plan

> **For agentic workers:** Start with audit outputs. Do not change source-view precedence until `data`, `corrected`, `split`, and `volumes` have been compared on real source quality.

**Goal:** Make the OpenGreekAndLatin reader imports trustworthy: no silent file loss, no unjustified source-view preference, no avoidable misattribution, and clear reports for skipped or alternate source files.

## Current Findings

Current importer behavior:

- `data/` is preferred over alternate views.
- `corrected/`, `split/`, and `volumes/` are marked as skipped alternate views when `data/` exists.
- Duplicate work ids are skipped.
- Zero-segment files are skipped.
- Source metadata records skipped/error status, but the human audit surface was not obvious enough.

Current local audit snapshot:

- `opengreekandlatin_patrologia`: 4,241 candidates, 1,275 selected/imported, 2,962 skipped alternate views, 3 zero-segment skips, 1 duplicate skip.
- `opengreekandlatin_csel`: 352 candidates, 264 selected/imported, 81 skipped volume views, 7 duplicate skips.
- `opengreekandlatin_church_fathers`: 3 candidates, 3 selected/imported, all synthetic ids.
- `opengreekandlatin_latin`: 7 candidates, 7 selected/imported.

Important concern:

- We have not proven that `data/` is higher quality than `corrected/` for Patrologia.
- We have not proven that `data/` has better work granularity than `split/`.
- We have not proven that `volumes/` should always lose to split/work-level data.

## New Audit Command

Use:

```bash
just cli reader ogl-audit --output json
```

Useful focused form:

```bash
just cli reader ogl-audit \
  --collection opengreekandlatin_patrologia \
  --sample-limit 20 \
  --output json
```

The command reports:

- Candidate counts by collection.
- Selected source count.
- Current catalog source-index row count.
- Selected local source files missing from catalog.
- Import status counts.
- Source view counts.
- Skip reason counts.
- Sample skipped/missing files.

## Completeness Scorecards

Maintain generated scorecards under:

```text
data/reference/ogl_import_audit/
```

Current files:

- `current_ogl_audit.json`: full `reader ogl-audit` output.
- `csel_patrologia_completeness_scorecard.tsv`: CSEL/Patrologia local source and catalog scorecard.
- `csel_patrologia_completeness_scorecard.json`: JSON scorecard.
- `csel_external_scorecard.tsv`: CSEL external baseline coverage using the Wikipedia volume list.
- `csel_external_scorecard.json`: JSON CSEL external baseline scorecard.
- `pl_pg_acquisition_source_scorecard.tsv`: candidate-source scorecard for Patrologia Latina and Patrologia Graeca acquisition.
- `pl_pg_acquisition_source_scorecard.json`: JSON candidate-source scorecard.
- `open_web_legitimacy_queue.tsv`: rows needing author/title/source confirmation on the open web.

The scorecard must distinguish:

- External corpus completeness: what the full corpus should contain.
- Local checkout completeness: what exists under `/home/nixos/opengreekandlatin/...`.
- Import/catalog completeness: what LangNet selected, parsed, and exposed.

Current scorecard findings:

- Patrologia local checkout has 81 distinct visible PL volume ids under `volumes/`, range `PL3` through `PL85`; `PL122` is absent.
- Patrologia catalog currently exposes 1,275 rows, 210,395 segments, and 25,203,407 words.
- CSEL local checkout has 65 distinct visible CSEL volume ids under `Volumes/`, range `CSEL1` through `CSEL67`.
- CSEL catalog currently exposes 264 rows, 85,726 segments, and 9,770,722 words.
- Wikipedia's CSEL volume list currently yields 107 base volume ids, `CSEL1` through `CSEL107`; local visible CSEL volume-id coverage is about 60.7%.
- Locally missing CSEL base volume ids from that coarse baseline are `61`, `66`, and `68-107`.
- Wikipedia describes Patrologia Latina as 217 volumes, plus index volumes 218-221; our local visible PL volume ids cover roughly 37.3% of that 217-volume baseline.
- Wikipedia describes Patrologia Graeca as 161 volumes, often bound as 166 physical volumes; no local Patrologia Graeca checkout was found under `/home/nixos/opengreekandlatin`.

Current PL/PG acquisition-source reading:

- Existing OGL Patrologia Latina is a partial, already-integrated source and should remain under audit rather than be discarded.
- Latin Wikisource is a strong Patrologia Latina table-of-contents and legitimacy source, and may be a practical text source for selected missing works after rights/format review.
- Internet Archive's PL 1-221 item is the strongest bulk fallback for missing PL volumes, especially when a specific externally attested volume such as PL122 is absent locally.
- Corpus Corporum may be the highest-quality machine-text source for Latin/medieval material if access and reuse constraints permit import.
- Documenta Catholica Omnia is useful for corroboration and selective investigation, but rights and formatting notices require caution before bulk ingestion.
- Open Patrologia Graeca / OGL-PatrologiaGraecaDev is the strongest full-coverage Patrologia Graeca acquisition lead because no local PG checkout is currently present.
- The Calfa Patrologia-Graeca GitHub repository is a recent, useful OCR benchmark/pilot source for selected PG volumes, not yet a proven complete PG replacement.
- Local TLG CD D/E author listings under `~/Classics-Data/tlg_e/` are identity-control evidence for Greek author mapping and disputed attribution conventions, not raw text sources.

Uncovered-work interpretation:

- If a work is externally attested but absent from local source files, create an acquisition target.
- If a work is present locally but skipped as alternate/duplicate/no-segment, create an importer audit target.
- If a work is imported but misidentified, create a curated overlay or importer parsing fix.

## Audit Dimensions

### Coverage

Questions:

- Which local XML files are source-like TEI?
- Which files are selected for import?
- Which files are skipped as alternate views?
- Which selected files are missing from the current catalog?
- Which catalog rows do not map back to selected local files?

Acceptance:

- Every skipped file has an explicit reason.
- Every selected source path appears in source-index rows after rebuild.

### Source View Quality

Compare `data`, `corrected`, `split`, and `volumes`.

Metrics:

- Parse success.
- Segment count.
- Token count.
- title/author/CTS metadata strength.
- OCR/noise artifacts.
- header/footer contamination.
- work boundary quality.

Acceptance:

- We can justify per-collection precedence.
- If `corrected/` is better for Patrologia, importer policy changes.
- If `split/` is better for work granularity, importer policy changes.

### Attribution Quality

Questions:

- Are source titles strong or weak?
- Are authors derived from TEI headers, CTS inventory, title inference, or fallback?
- Which rows are still `Unknown`, `Incertus`, `AA VV`, or synthetic?
- Which `tmp*` ids need overlays?
- Does the open web corroborate that this author/work pairing is legitimate?

Acceptance:

- Generate a queue of weak attribution rows.
- Use curated overlays for high-value corrections.
- Avoid broad heuristic author inference unless source evidence is strong.

### Open-Web Legitimacy Check

Importer audit must include external source research for questionable or high-value rows. The question is not only "did the XML parse?" but "is this actually the work we think it is?"

Use Firecrawl or equivalent web research to answer:

- Is this title attested under this author?
- Is this title in the claimed Patrologia/CSEL/OGL volume?
- Is this CTS/source id plausibly tied to the work?
- Is the title a collection, volume heading, table of contents, commentary, apparatus, fragment, translation, or actual work?
- Is the apparent author a person, collection label, tradition, editor, translator, uncertain attribution, or title-derived guess?
- Is there an open bibliographic page or corpus page that confirms the mapping?

Evidence sources to prefer:

- Latin Wikisource volume/work pages.
- Archive.org metadata and volume tables of contents.
- Documenta Catholica Omnia author/work pages.
- Corpus Christianorum/Brepols pages for bibliographic context, not raw text import.
- Library/catalog records when they identify the exact volume/work.
- Existing OGL CTS inventories and TEI headers.
- Scholarly reference pages when corpus pages are missing.

Evidence outputs:

- Store raw Firecrawl/search artifacts under `.firecrawl/`.
- Promote only reviewed claims into curated YAML overlays or audit reports.
- Record evidence citation, evidence label, retrieved date, and confidence.
- Keep "not found on open web" as a meaningful audit result for low-confidence rows.

Audit queue fields:

- `collection_id`
- `source_id`
- `source_path`
- `current_author`
- `current_title`
- `current_cts_work_urn`
- `current_canonical_text_id`
- `issue_type`
- `web_query`
- `evidence_url`
- `evidence_label`
- `evidence_result`: `confirmed`, `contradicted`, `ambiguous`, `not_found`
- `recommended_action`: `keep`, `overlay_author`, `overlay_title`, `split_work`, `suppress`, `needs_human_review`, `acquire_missing_source`
- `confidence`

Example:

- If `Joannes Scotus Erigena` is expected from PL122, audit should verify PL122 externally, then determine whether PL122 exists locally. In the current checkout, PL122 appears absent locally, so the action is acquisition, not importer correction.
- Latin Wikisource can be both an evidence source and an acquisition candidate when it provides individual work pages with usable text.

### Missing Expected Works

Examples:

- Joannes Scotus Eriugena should be PL122, but local OGL `volumes/` does not contain `PL122`.
- Current catalog has no Eriugena/Periphyseon/De divisione naturae.

Acceptance:

- Distinguish "missing from local source checkout" from "source present but importer skipped it."
- Add acquisition targets for source gaps rather than blaming the importer when the source is absent.

### PL/PG Acquisition Scorecard

Maintain `data/reference/ogl_import_audit/pl_pg_acquisition_source_scorecard.tsv` as the current source selection record.

Score every source on:

- Machine text availability.
- Coverage.
- Provenance strength.
- Rights/reuse risk.
- Import effort.
- Recommended role in the pipeline.

Use roles deliberately:

- `primary_text_source`: preferred import source when rights and quality are acceptable.
- `primary_pg_ocr_corpus_candidate`: likely first PG source to prototype.
- `bulk_ocr_fallback_and_missing_volume_acquisition`: useful for missing volumes when no clean text source exists.
- `toc_and_legitimacy`: evidence source for author/work/volume confirmation.
- `bibliographic_reference_and_download_catalog`: source discovery, not direct text import.
- `identity_control_authority_not_text_source`: identifier/author mapping support only.

## Implementation Phases

### Phase 1: Audit surfaces

- Add and use `reader ogl-audit`.
- Save audit outputs under `data/reference/reader_source_index/` or a new `data/reference/ogl_import_audit/`.
- Document current counts.
- Maintain CSEL/Patrologia completeness scorecards.
- Maintain an open-web legitimacy queue for suspicious rows.

### Phase 2: View comparison samples

- Select 10 Patrologia works where `data` and `corrected` both exist.
- Select 10 Patrologia works where `data` and `split` overlap.
- Compare extracted text and metadata.
- For each sampled work, run an open-web legitimacy check for author/title/volume identity.
- Decide whether current precedence should change.

### Phase 3: Policy fix

- Replace global `data` preference with explicit per-collection source-view policy.
- Consider per-work best-candidate selection.
- Preserve alternate views as source witnesses, not invisible noise.

### Phase 4: Attribution cleanup queue

- Export weak OGL rows.
- Add curated overlays for high-value bad title/author cases.
- Add generated/source-backed classification only after identity is stable.

### Phase 5: Rebuild loop

- Rebuild reader catalog.
- Regenerate source-index TSVs.
- Run OGL audit.
- Sync generated classification for changed rows.
- Inspect `/library`.

## Do Not Do Yet

- Do not assume `corrected/` is always better before comparing.
- Do not import all alternate views as separate works.
- Do not hide duplicate/alternate witnesses.
- Do not use broad title heuristics to "fix" authors without evidence.
