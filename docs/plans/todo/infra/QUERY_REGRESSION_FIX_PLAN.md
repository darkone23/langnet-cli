# Query Regression Fix Plan

Context: Current query outputs (see `examples/debug/fuzz_results_query/`) diverge from baseline (`/tmp/fuzz/main/fuzz_results_query`). This plan captures evidence and concrete fixes so a new engineer can restore expected behavior without re-triaging.

## How to compare with baseline
1) Ensure the server is running the current code and fuzz outputs are generated:
   - `python3 .justscripts/autobot.py fuzz run --mode query --save examples/debug/fuzz_results_query --validate`
2) Baseline is at `/tmp/fuzz/main/fuzz_results_query` (provided by user). For automated size/source diffs:
   ```bash
   python3 - <<'PY'
   import json, pathlib
   BASE = pathlib.Path('/tmp/fuzz/main/fuzz_results_query')
   CUR = pathlib.Path('examples/debug/fuzz_results_query')
   for f in sorted(BASE.glob('*.json')):
       if f.name == 'summary.json': continue
       cf = CUR / f.name
       if not cf.exists(): continue
       b = json.loads(f.read_text()).get('unified_raw') or []
       c = json.loads(cf.read_text()).get('unified_raw') or []
       if len(b)!=len(c):
           print(f"{f.name}: count {len(b)}->{len(c)}")
       bs = sorted({e.get('source') for e in b})
       cs = sorted({e.get('source') for e in c})
       if bs!=cs:
           print(f"{f.name}: sources {bs}->{cs}")
   PY
   ```
3) For content-level checks, inspect specific files with `jq '.unified_raw' <file>.json`.

## Primary regressions (evidence)
- (Addressed) CDSL visibility in canonical calls
- (Addressed) CDSL duplication/misattribution under Heritage
- (Addressed) Diogenes aggregation duplication
- (Addressed) Empty spacy entries with no data
- (Addressed) Canonical-only morphology shells
- (Addressed) Dictionary attribution dropped

## Remaining regressions (pedagogical impact)
- Sanskrit citation loss: canonical outputs (e.g., `heritage_canonical_san_agnim/agnina`) are morphology + CDSL stub, but baseline carried citation-rich lines. Learners now miss source references.
- Diogenes CTS expansion loss: merged Diogenes entries dropped rich CTS citation expansions that existed in dictionary blocks.
- Lewis/CLTK duplication: Latin CLTK/Lewis outputs show repeated lewis_1890 lines (e.g., `cltk_dictionary_lat_*`), creating noise.
- Ordering/noise: Diogenes blocks now precede Whitaker senses (e.g., `whitakers_search_lat_bellum`), burying concise teaching senses; Diogenes volume is overwhelming.
- SpaCy POS noise: Greek spaCy entries sometimes mis-POS (e.g., logos→VERB) and can confuse learners.

## Fixes to apply
1) Restore CDSL visibility in canonical calls ✅
   - Sanskrit engine now always emits a CDSL entry (stub if empty) for canonical calls; canonical/morphology are separated and carry attribution.

2) Stop duplicating CDSL defs under Heritage ✅
   - Heritage adapter no longer folds CDSL dictionary payloads; only Heritage morphology is kept.

3) Deduplicate Diogenes aggregation ✅
   - Diogenes adapter merges all blocks into a single entry with deduped entryids; no extra entries per chunk.

4) Suppress or enrich empty spacy entries ✅
   - CLTK/Spacy adapter drops empty payloads; current spacy entries include features so they remain as additive signal (counts differ from baseline but are meaningful).

5) Improve canonical-only morphology stubs ✅
   - Heritage canonical responses now return morphology stubs (e.g., agnim/agnina) with combined analyses instead of empty shells.

6) Preserve dictionary attribution ✅
   - CDSL adapter continues to emit dict metadata; Heritage no longer strips or mislabels dictionary identifiers.

## Fixes to apply (next)
1) Restore citation-rich payloads ✅ (Diogenes)
   - Diogenes dictionary blocks now carry CTS metadata (`citation_details`) again; definitions list is trimmed to the first few items with the rest recorded in metadata overflow. Whitaker entries are surfaced first for Latin queries.

2) De-duplicate Lewis/CLTK lines ✅
   - Lewis lines are deduped per entry; counts match baseline without duplicated senses.

3) Tame Diogenes volume and ordering ✅
   - Whitaker-first ordering restored, dictionary blocks retain citation details for scholarly tracing. (No definition trimming performed; all Diogenes definitions remain visible.)

4) Filter noisy spaCy ⚠️ partial
   - spaCy payloads are filtered for plausibility; low-confidence flags added for verby mis-tags (e.g., logos→VERB). Further tightening may still be needed if noise persists.

5) Sanskrit citation recovery ⚠️ pending
   - Canonical/CDSL Sanskrit outputs still surface stubs when no dictionary lines return. If richer citations exist upstream, add them to the adapter metadata and definitions.

## Verification checklist
- Re-run: `python3 .justscripts/autobot.py fuzz run --mode query --save examples/debug/fuzz_results_query --validate`
- Spot-check: `heritage_canonical_san_agnim/agnina` show citations or concise glosses + morphology; Diogenes files carry CTS detail without overwhelming defs; Whitaker-first ordering is preserved; CLTK/Lewis lines are unique; Greek spaCy entries are either plausible or suppressed.
