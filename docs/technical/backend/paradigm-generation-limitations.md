# Paradigm Generation Limitations And Graceful Degradation

Status: Current implementation note

LangNet paradigm generation is source-backed. It wraps Sanskrit Heritage and Diogenes rather than claiming a complete in-house morphology engine.

## What Works Now

- Sanskrit noun declensions via Heritage `sktdeclin`.
- Sanskrit verb conjugation tables via Heritage `sktconjug`.
- Sanskrit resolver output that can turn Heritage morphology evidence such as
  `putrāṇām` or `devebhyaḥ` into a fetchable Heritage declension request when
  lemma and gender are known.
- Latin and Greek inflection tables via Diogenes `do=inflect`.
- Resolver payloads that separate native grammar from functional grammar.
- Verified Greek learner-key bridges for common MOTD words, such as `logos` to
  Diogenes `lo/gos` and `sophos` to `sofo/s`.
- CLI probes:
  - `paradigm-resolve`
  - `paradigm`
- Web adapter consumer:
  - `webapp/src/routes/api/paradigm/+server.ts`

## Current Limits

- The system does not yet perform full arbitrary reverse morphological analysis.
- The resolver needs evidence from lookup/analyzer records. If required metadata is missing, it should return an unresolved reason instead of guessing.
- Greek romanized learner keys are supported only when present in the verified
  learner-key bridge table. Unmapped romanized Greek reports
  `greek_learner_key_not_resolved_to_source_key`.
- Sanskrit declension requests require lemma plus Heritage gender: `Mas`, `Fem`, or `Neu`.
- Sanskrit conjugation requests require root plus present class.
- Sanskrit forms without analyzer/dictionary grammar evidence should remain
  unresolved. LangNet should not infer first-declension-style classes or
  Sanskrit stem classes by guessing from a bare string when source metadata is
  missing.
- Greek and Latin Diogenes tables can contain poetic, dialectal, enclitic, or orthographic variants. LangNet preserves these source forms rather than filtering them away.
- Diogenes labels can be syncretic, such as Greek `nom/voc pl`. LangNet keeps a primary normalized case and adds `case_alternates` with `is_ambiguous = true`.
- Heritage conjugation context is extracted from nearby tense/mood labels and voice header cells. If Heritage changes its HTML layout, forms may still parse while contextual labels degrade.
- Diogenes `do=inflect` may return an HTTP/0.9-style body. LangNet has a plain-HTTP fallback for this route, but HTTPS Diogenes endpoints are not supported by that fallback.

## Graceful Degradation Policy

When a source-backed request cannot produce a full paradigm, LangNet should prefer structured partial output over crashes:

- Return `warnings` in `langnet.paradigm.v1`.
- Return an empty `paradigms` list if the source request fails completely.
- Preserve raw source labels in `source_label` whenever feature normalization is incomplete.
- Preserve source forms and source keys even when grammatical interpretation is partial.
- Avoid inventing gender, declension, conjugation, tense, voice, or root data.

Examples of current warning values:

- `heritage_declension_table_not_found`
- `heritage_conjugation_tables_not_found`
- `heritage_declension_request_failed: <ExceptionType>`
- `heritage_conjugation_request_failed: <ExceptionType>`
- `diogenes_inflect_forms_not_found`
- `diogenes_inflect_request_failed: <ExceptionType>`

## Enhancement Path

1. Use resolver output as the only route into source-backed fetching.
2. Expand dictionary grammar extraction per source, especially source-native gender/class metadata.
3. Improve Heritage conjugation block labels for all tense/mood categories.
4. Group equivalent Diogenes forms into richer multi-analysis slots instead of preserving only `case_alternates`.
5. Add UI highlighting in the SvelteKit adapter from originating forms to matching paradigm slots.
6. Add local template generation only after source-backed behavior is stable and well documented.
