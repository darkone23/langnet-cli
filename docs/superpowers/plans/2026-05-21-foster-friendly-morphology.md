# Foster-Friendly Morphology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the morphology evidence LangNet already receives from Heritage, Whitaker, Diogenes/Morpheus, and paradigm tables into a source-agnostic, Foster-friendly learner workflow.

**Architecture:** Keep source handlers source-specific, but add one reusable morphology candidate layer that converts existing triples and morphology objects into ranked candidates. Paradigm tables remain lazy and source-backed; lookup output advertises the best table request, Foster function, source evidence, and slot target so the web UI can show the relevant form in context without guessing.

**Tech Stack:** Python dataclasses/cattrs-style dict serialization, existing semantic triples, Typer/Click CLI JSON output, `langnet.paradigm_resolution.v1`, Heritage/Diogenes paradigm fetchers, SvelteKit/Bun web app, nose2 tests through `just test`, web verification through `webapp/justfile`.

---

## Current State

LangNet is closer to this goal than the open issues imply:

- Sanskrit Heritage analysis already emits structured morphology objects with features such as `case`, `number`, `gender`, `person`, `tense`, `voice`, `mood`, and `verb_class`.
- Whitaker already emits graph-style morphology facts such as `has_case`, `has_number`, `has_gender`, `has_tense`, `has_voice`, `has_mood`, and `has_person`.
- Diogenes already fetches Latin and Greek inflection tables through `do=inflect`, and the parser already normalizes table slots.
- Diogenes pages often include Perseus/Morpheus analysis lines such as `λόγος, λόγου: noun masc gen sg`; LangNet parses the tag bag but does not yet graduate those tags into canonical morphology predicates.
- The SvelteKit UI already has a Forms panel and lazy table loading, but candidate curation can hide the useful form behind noisy candidates.
- Foster functional labels exist, but they are not yet consistently attached to the morphology candidates learners see, and the docs do not teach the labels with cross-language examples.

This plan is therefore not a rewrite and not a new morphology engine. It is an evidence promotion and learner-facing integration pass.

## Execution Checkpoint - 2026-05-21

Completed in the current implementation stream:

- [x] Added learner-facing Foster display from source feature dictionaries.
- [x] Added `langnet.morphology.candidates` as the shared source-agnostic candidate layer.
- [x] Routed Heritage `has_morphology` objects through the candidate layer.
- [x] Routed Whitaker interpretation graphs through the candidate layer.
- [x] Promoted Diogenes/Morpheus tag bags into canonical form-level morphology predicates.
- [x] Routed direct `form:* inflection_of lex:*` graphs through the candidate layer.
- [x] Preserved lexeme-level morphology facts such as `has_declension` and `has_conjugation` on form candidates.
- [x] Kept spaCy optional, but fixed its morphology projection so it emits form-level features when used.
- [x] Extended `paradigm_resolution.v1` candidates with `observed_form`, `slot_features`, `foster_display`, `display_summary`, and `ranking_reasons`.
- [x] Updated the web Forms panel to normalize those fields, rank strongly determined candidates, show Foster display, and match table slots by explicit features.
- [x] Added `docs/technical/morphology-projection-audit.md` as the source coverage matrix.

Remaining before calling this fully validated:

- [ ] Finish the current full backend verification pass after the latest audit/doc changes.
- [ ] Add more real-page Diogenes/Morpheus fixtures for tag variants beyond the current noun/verb samples.
- [ ] Add more noisy Heritage fixtures, especially Sanskrit compounds and multiple-candidate ranking cases.
- [ ] Add dictionary-parsing fixtures that prove parsed entry grammar facts graduate to canonical predicates.
- [ ] Decide whether spaCy remains test-only/optional or gets a daemon/service plan before any runtime dependency grows around it.

## File Map

- Create `src/langnet/morphology/__init__.py`: package exports for the candidate layer.
- Create `src/langnet/morphology/candidates.py`: source-agnostic candidate dataclasses, triple projection helpers, Foster display attachment, and ranking.
- Create `tests/fixtures/foster_morphology_cases.json`: stable cross-language cases for Sanskrit, Latin, and Greek.
- Create `tests/test_morphology_candidates.py`: unit tests for candidate projection and ranking.
- Create `tests/test_foster_morphology_cases.py`: acceptance tests driven by the fixture file.
- Create `tests/test_diogenes_morpheus_morphology.py`: focused tests proving Morpheus tags become canonical morphology triples.
- Modify `src/langnet/execution/handlers/diogenes.py`: normalize Morpheus/Perseus tag bags into `has_case`, `has_number`, `has_gender`, `has_tense`, `has_voice`, `has_mood`, and `has_person` triples while preserving raw tags.
- Modify `src/langnet/cli.py`: replace private encounter morphology extraction helpers with calls into `langnet.morphology.candidates`.
- Modify `src/langnet/paradigm/grammar.py`: add optional learner-display fields to paradigm candidates.
- Modify `src/langnet/paradigm/resolver.py`: carry observed form, slot target, Foster display, and ranking reasons into the resolution payload.
- Modify `docs/schemas/paradigm_resolution.v1.schema.json`: allow the new optional candidate fields without removing current fields.
- Modify `tests/test_paradigm_resolution_contract.py`: pin the extended contract.
- Modify `tests/test_cli_encounter_output.py`: pin high-value encounter output for Heritage, Whitaker, and Diogenes.
- Modify `webapp/src/lib/paradigm-resolution.ts`: normalize optional candidate fields from CLI JSON.
- Modify `webapp/src/lib/paradigm-ui.ts`: rank visible candidates and match loaded slots using explicit candidate evidence.
- Modify `webapp/src/lib/paradigm-ui.test.ts`: cover candidate curation and slot matching.
- Modify `webapp/src/routes/+page.svelte`: render Foster-friendly candidate display and use the shared slot matcher.
- Create `docs/FOSTER_FUNCTIONAL_GRAMMAR_EXAMPLES.md`: cross-language learner examples.
- Modify `docs/PEDAGOGICAL_PHILOSOPHY.md`: link the examples and clarify that Foster labels supplement precise morphology.
- Modify `docs/OUTPUT_GUIDE.md`: document the new encounter/paradigm fields and examples.
- Modify `docs/technical/backend/paradigm-generation-limitations.md`: replace stale limitations with source-backed status and remaining gaps.
- Modify `webapp/docs/UI.md`: document the Forms panel behavior and slot highlighting.
- Modify `webapp/docs/REGRESSION_CASES.md`: add Foster-friendly morphology regression commands.

## Non-Goals

- Do not build a full local Greek, Latin, or Sanskrit morphology engine.
- Do not pre-generate every paradigm form for every dictionary entry.
- Do not replace precise native grammar labels with Foster labels.
- Do not make Diogenes word search a hard dependency for this pass.
- Do not remove raw source evidence; promote it and keep provenance visible.

## Success Definition

- Sanskrit `putraa.naam` surfaces `putra` as a visible genitive plural candidate with a Heritage declension request and Foster `Possessing Function`.
- Latin `puellae` preserves ambiguity under one learner-readable candidate set: genitive singular, dative singular, nominative plural, with matching Foster functions.
- Greek `λόγου` or a betacode equivalent can use Diogenes/Morpheus evidence to resolve toward `λόγος`, genitive singular, and a Diogenes inflection request when the page supplies the Morpheus line.
- The Forms panel shows the relevant candidate instead of hiding it behind noisy alternatives.
- Loaded tables can highlight the slot matching the observed form/features.
- Documentation teaches the Foster labels with concrete Latin, Greek, and Sanskrit examples.

---

### Task 1: Acceptance Fixture

**Files:**
- Create: `tests/fixtures/foster_morphology_cases.json`
- Create: `tests/test_foster_morphology_cases.py`

- [ ] **Step 1: Add the cross-language fixture**

Create `tests/fixtures/foster_morphology_cases.json`:

```json
[
  {
    "id": "san-putra-gen-pl",
    "language": "san",
    "query": "putraa.naam",
    "dictionary": "heritage",
    "expected_lemma": "putra",
    "expected_source": "heritage:sktreader",
    "expected_features": {"case": "genitive", "number": "plural", "gender": "masculine"},
    "expected_functional_relations": ["possession_or_association"],
    "expected_foster_labels": ["Possessing Function"],
    "expected_paradigm_request": {"source": "heritage:sktdeclin", "kind": "declension"}
  },
  {
    "id": "san-dharma-case-ambiguity",
    "language": "san",
    "query": "dharma",
    "dictionary": "heritage",
    "expected_lemma": "dharma",
    "expected_source": "heritage:sktreader",
    "expected_functional_relations": ["subject", "direct_object", "address"],
    "expected_foster_labels": ["Naming Function", "Receiving Function", "Calling Function"],
    "expected_paradigm_request": {"source": "heritage:sktdeclin", "kind": "declension"}
  },
  {
    "id": "lat-puellae-ambiguity",
    "language": "lat",
    "query": "puellae",
    "dictionary": "whitakers",
    "expected_lemma": "puella",
    "expected_source": "whitakers",
    "expected_features_any": [
      {"case": "genitive", "number": "singular"},
      {"case": "dative", "number": "singular"},
      {"case": "nominative", "number": "plural"}
    ],
    "expected_functional_relations": ["possession_or_association", "recipient_or_goal", "subject"],
    "expected_foster_labels": ["Possessing Function", "To-For Function", "Naming Function"],
    "expected_paradigm_request": {"source": "diogenes:inflect", "kind": "declension"}
  },
  {
    "id": "lat-amamus-verb-facts",
    "language": "lat",
    "query": "amamus",
    "dictionary": "whitakers",
    "expected_lemma": "amo",
    "expected_source": "whitakers",
    "expected_features": {"person": "1", "number": "plural", "tense": "present", "voice": "active", "mood": "indicative"},
    "expected_foster_labels": ["Now-Time", "Doing Voice"],
    "expected_paradigm_request": {"source": "diogenes:inflect", "kind": "conjugation"}
  },
  {
    "id": "grc-logou-morpheus",
    "language": "grc",
    "query": "λόγου",
    "dictionary": "diogenes",
    "expected_lemma": "λόγος",
    "expected_source": "diogenes:morpheus",
    "expected_features": {"case": "genitive", "number": "singular", "gender": "masculine"},
    "expected_functional_relations": ["possession_or_association"],
    "expected_foster_labels": ["Possessing Function"],
    "expected_paradigm_request": {"source": "diogenes:inflect", "kind": "declension"}
  }
]
```

- [ ] **Step 2: Add fixture loader smoke tests**

Create `tests/test_foster_morphology_cases.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


FIXTURE = Path("tests/fixtures/foster_morphology_cases.json")


def test_foster_morphology_fixture_has_named_cases() -> None:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert [case["id"] for case in cases] == [
        "san-putra-gen-pl",
        "san-dharma-case-ambiguity",
        "lat-puellae-ambiguity",
        "lat-amamus-verb-facts",
        "grc-logou-morpheus",
    ]
    assert all(case["expected_lemma"] for case in cases)
    assert all(case["expected_paradigm_request"]["source"] for case in cases)
```

- [ ] **Step 3: Run fixture smoke test**

Run:

```bash
just test test_foster_morphology_cases
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/foster_morphology_cases.json tests/test_foster_morphology_cases.py
git commit -m "test: add foster morphology acceptance cases"
```

---

### Task 2: Source-Agnostic Candidate Model

**Files:**
- Create: `src/langnet/morphology/__init__.py`
- Create: `src/langnet/morphology/candidates.py`
- Create: `tests/test_morphology_candidates.py`

- [ ] **Step 1: Write candidate projection tests**

Create `tests/test_morphology_candidates.py`:

```python
from __future__ import annotations

from langnet.morphology.candidates import candidates_from_triples, rank_candidates


def test_heritage_morphology_object_projects_to_candidate() -> None:
    triples = [
        {
            "subject": "form:putra",
            "predicate": "has_morphology",
            "object": {
                "lemma": "putra",
                "form": "putrāṇām",
                "features": {"case": "genitive", "number": "plural", "gender": "masculine"},
                "analysis": "m. gen. pl.",
            },
            "metadata": {"source": "heritage:sktreader"},
        }
    ]

    candidates = candidates_from_triples("san", "putraa.naam", triples)

    assert candidates[0].lemma == "putra"
    assert candidates[0].observed_form == "putrāṇām"
    assert candidates[0].features["case"] == "genitive"
    assert candidates[0].functional_relations == ["possession_or_association"]
    assert "Possessing Function" in candidates[0].foster_labels


def test_whitaker_interpretation_graph_projects_to_candidate() -> None:
    triples = [
        {"subject": "form:puellae", "predicate": "has_interpretation", "object": "interp:puellae:1", "metadata": {"source": "whitakers"}},
        {"subject": "interp:puellae:1", "predicate": "realizes_lexeme", "object": "lex:puella", "metadata": {"source": "whitakers"}},
        {"subject": "interp:puellae:1", "predicate": "has_pos", "object": "noun", "metadata": {"source": "whitakers"}},
        {"subject": "interp:puellae:1", "predicate": "has_case", "object": "genitive", "metadata": {"source": "whitakers"}},
        {"subject": "interp:puellae:1", "predicate": "has_number", "object": "singular", "metadata": {"source": "whitakers"}},
        {"subject": "interp:puellae:1", "predicate": "has_gender", "object": "feminine", "metadata": {"source": "whitakers"}},
    ]

    candidates = candidates_from_triples("lat", "puellae", triples)

    assert candidates[0].lemma == "puella"
    assert candidates[0].features["case"] == "genitive"
    assert candidates[0].functional_relations == ["possession_or_association"]


def test_ranking_prefers_exact_observed_supported_candidate() -> None:
    triples = [
        {"subject": "form:noise", "predicate": "has_morphology", "object": {"lemma": "noise", "form": "putrāṇām", "features": {"case": "nominative"}}, "metadata": {"source": "heritage:sktreader"}},
        {"subject": "form:putra", "predicate": "has_morphology", "object": {"lemma": "putra", "form": "putrāṇām", "features": {"case": "genitive", "number": "plural", "gender": "masculine"}}, "metadata": {"source": "heritage:sktreader"}},
    ]

    ranked = rank_candidates(candidates_from_triples("san", "putraa.naam", triples))

    assert ranked[0].lemma == "putra"
    assert "case-number-gender" in ranked[0].ranking_reasons
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
just test test_morphology_candidates
```

Expected: FAIL with `ModuleNotFoundError: No module named 'langnet.morphology'`.

- [ ] **Step 3: Add the package exports**

Create `src/langnet/morphology/__init__.py`:

```python
from __future__ import annotations

from langnet.morphology.candidates import MorphologyCandidate, candidates_from_triples, rank_candidates

__all__ = ["MorphologyCandidate", "candidates_from_triples", "rank_candidates"]
```

- [ ] **Step 4: Add the minimal candidate implementation**

Create `src/langnet/morphology/candidates.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from langnet.pedagogy.foster import foster_display_for_features


CASE_TO_RELATION = {
    "nominative": "subject",
    "accusative": "direct_object",
    "dative": "recipient_or_goal",
    "ablative": "source_or_separation",
    "genitive": "possession_or_association",
    "locative": "location",
    "instrumental": "instrument_or_means",
    "vocative": "address",
}


@dataclass(frozen=True)
class MorphologyCandidate:
    language: str
    query: str
    observed_form: str
    normalized_form: str
    lemma: str
    source: str
    part_of_speech: str | None = None
    features: dict[str, Any] = field(default_factory=dict)
    analyses: list[dict[str, Any]] = field(default_factory=list)
    functional_relations: list[str] = field(default_factory=list)
    foster_labels: list[str] = field(default_factory=list)
    confidence: str = "low"
    provenance: list[str] = field(default_factory=list)
    ranking_reasons: list[str] = field(default_factory=list)


def candidates_from_triples(language: str, query: str, triples: list[Mapping[str, Any]]) -> list[MorphologyCandidate]:
    candidates: list[MorphologyCandidate] = []
    candidates.extend(_from_heritage_objects(language, query, triples))
    candidates.extend(_from_interpretation_graph(language, query, triples))
    return rank_candidates(candidates)


def rank_candidates(candidates: list[MorphologyCandidate]) -> list[MorphologyCandidate]:
    return sorted(candidates, key=_rank_key)
```

Then fill in these private helpers in the same file:

```python
def _from_heritage_objects(language: str, query: str, triples: list[Mapping[str, Any]]) -> list[MorphologyCandidate]:
    results: list[MorphologyCandidate] = []
    for triple in triples:
        if triple.get("predicate") != "has_morphology":
            continue
        obj = triple.get("object")
        if not isinstance(obj, Mapping):
            continue
        features = dict(obj.get("features") if isinstance(obj.get("features"), Mapping) else {})
        lemma = str(obj.get("lemma") or "").strip()
        observed = str(obj.get("form") or query).strip()
        if not lemma:
            continue
        results.append(_build_candidate(language, query, observed, lemma, _source(triple), features, obj.get("analysis")))
    return results


def _from_interpretation_graph(language: str, query: str, triples: list[Mapping[str, Any]]) -> list[MorphologyCandidate]:
    by_subject: dict[str, list[Mapping[str, Any]]] = {}
    form_to_interp: list[tuple[str, str]] = []
    for triple in triples:
        subject = str(triple.get("subject") or "")
        by_subject.setdefault(subject, []).append(triple)
        if triple.get("predicate") == "has_interpretation":
            form_to_interp.append((subject, str(triple.get("object") or "")))

    results: list[MorphologyCandidate] = []
    for form_anchor, interp_anchor in form_to_interp:
        interp_triples = by_subject.get(interp_anchor, [])
        lemma = _lexeme_from_interpretation(interp_triples)
        if not lemma:
            continue
        features = _features_from_predicates(interp_triples)
        observed = form_anchor.removeprefix("form:") or query
        source = _source(interp_triples[0]) if interp_triples else "unknown"
        results.append(_build_candidate(language, query, observed, lemma, source, features, None))
    return results
```

The remaining helper bodies should be exactly:

```python
def _build_candidate(language: str, query: str, observed: str, lemma: str, source: str, features: dict[str, Any], analysis: object) -> MorphologyCandidate:
    relations = []
    case = features.get("case")
    if isinstance(case, str) and case in CASE_TO_RELATION:
        relations.append(CASE_TO_RELATION[case])
    foster = foster_display_for_features(features)
    labels = [item["label"] for item in foster if isinstance(item, Mapping) and isinstance(item.get("label"), str)]
    reasons = _ranking_reasons(observed, lemma, features)
    return MorphologyCandidate(
        language=language,
        query=query,
        observed_form=observed,
        normalized_form=observed,
        lemma=lemma.removeprefix("lex:"),
        source=source,
        part_of_speech=str(features.get("pos")) if features.get("pos") else None,
        features=features,
        analyses=[{"text": analysis}] if isinstance(analysis, str) and analysis else [],
        functional_relations=relations,
        foster_labels=labels,
        confidence="high" if {"case", "number"}.issubset(features) else "medium",
        provenance=[source],
        ranking_reasons=reasons,
    )


def _features_from_predicates(triples: list[Mapping[str, Any]]) -> dict[str, Any]:
    pred_map = {
        "has_pos": "pos",
        "has_case": "case",
        "has_number": "number",
        "has_gender": "gender",
        "has_tense": "tense",
        "has_voice": "voice",
        "has_mood": "mood",
        "has_person": "person",
    }
    features: dict[str, Any] = {}
    for triple in triples:
        key = pred_map.get(str(triple.get("predicate") or ""))
        if key:
            features[key] = triple.get("object")
    return features


def _lexeme_from_interpretation(triples: list[Mapping[str, Any]]) -> str | None:
    for triple in triples:
        if triple.get("predicate") == "realizes_lexeme":
            return str(triple.get("object") or "").removeprefix("lex:")
    return None


def _source(triple: Mapping[str, Any]) -> str:
    metadata = triple.get("metadata")
    if isinstance(metadata, Mapping):
        return str(metadata.get("source") or metadata.get("tool") or "unknown")
    return "unknown"


def _ranking_reasons(observed: str, lemma: str, features: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if observed:
        reasons.append("observed-form")
    if lemma:
        reasons.append("lemma")
    if {"case", "number", "gender"}.issubset(features):
        reasons.append("case-number-gender")
    elif {"tense", "voice", "mood"}.issubset(features):
        reasons.append("tense-voice-mood")
    return reasons


def _rank_key(candidate: MorphologyCandidate) -> tuple[int, int, int, str]:
    full_nominal = int("case-number-gender" not in candidate.ranking_reasons)
    full_verbal = int("tense-voice-mood" not in candidate.ranking_reasons)
    confidence = {"high": 0, "medium": 1, "low": 2}.get(candidate.confidence, 3)
    return (confidence, min(full_nominal, full_verbal), -len(candidate.ranking_reasons), candidate.lemma)
```

Adjust only for actual `foster_display_for_features` return shape if the existing helper uses a different name or output structure.

- [ ] **Step 5: Run candidate tests**

Run:

```bash
just test test_morphology_candidates
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/langnet/morphology tests/test_morphology_candidates.py
git commit -m "feat: add source agnostic morphology candidates"
```

---

### Task 3: Diogenes Morpheus Predicate Promotion

**Files:**
- Modify: `src/langnet/execution/handlers/diogenes.py`
- Create: `tests/test_diogenes_morpheus_morphology.py`
- Modify: `tests/test_claim_contracts.py`

- [ ] **Step 1: Write Morpheus promotion tests**

Create `tests/test_diogenes_morpheus_morphology.py`:

```python
from __future__ import annotations

from langnet.execution.handlers import diogenes


def _predicates_for(html: str) -> list[tuple[str, str, object]]:
    parsed = diogenes._parse_diogenes_html(html)
    morph = parsed["chunks"][0]["morphology"]
    triples = diogenes._build_perseus_header_triples(
        morph,
        "lex:λόγος",
        {"source": "diogenes:morpheus"},
    )
    return [(str(t["subject"]), str(t["predicate"]), t["object"]) for t in triples]


def test_morpheus_noun_tags_become_canonical_feature_triples() -> None:
    triples = _predicates_for("<h1>Perseus analysis</h1><ul><li>λόγος, λόγου: noun masc gen sg</li></ul>")

    assert ("form:λόγος", "has_pos", "noun") in triples
    assert ("form:λόγος", "has_gender", "masculine") in triples
    assert ("form:λόγος", "has_case", "genitive") in triples
    assert ("form:λόγος", "has_number", "singular") in triples


def test_morpheus_verb_tags_become_canonical_feature_triples() -> None:
    triples = _predicates_for("<h1>Perseus analysis</h1><ul><li>λύω: verb 1st pres act ind sg</li></ul>")

    assert ("form:λύω", "has_pos", "verb") in triples
    assert ("form:λύω", "has_person", "1") in triples
    assert ("form:λύω", "has_tense", "present") in triples
    assert ("form:λύω", "has_voice", "active") in triples
    assert ("form:λύω", "has_mood", "indicative") in triples
    assert ("form:λύω", "has_number", "singular") in triples
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
just test test_diogenes_morpheus_morphology
```

Expected: FAIL because raw `has_feature {"tags": [...]}` exists but canonical predicates are missing.

- [ ] **Step 3: Add tag maps in Diogenes handler**

In `src/langnet/execution/handlers/diogenes.py`, near `_normalize_pos`, add:

```python
_MORPHEUS_TAG_FEATURES: dict[str, tuple[str, str]] = {
    "nom": (predicates.HAS_CASE, "nominative"),
    "gen": (predicates.HAS_CASE, "genitive"),
    "dat": (predicates.HAS_CASE, "dative"),
    "acc": (predicates.HAS_CASE, "accusative"),
    "voc": (predicates.HAS_CASE, "vocative"),
    "abl": (predicates.HAS_CASE, "ablative"),
    "loc": (predicates.HAS_CASE, "locative"),
    "sg": (predicates.HAS_NUMBER, "singular"),
    "dual": (predicates.HAS_NUMBER, "dual"),
    "pl": (predicates.HAS_NUMBER, "plural"),
    "masc": (predicates.HAS_GENDER, "masculine"),
    "fem": (predicates.HAS_GENDER, "feminine"),
    "neut": (predicates.HAS_GENDER, "neuter"),
    "1st": (predicates.HAS_PERSON, "1"),
    "2nd": (predicates.HAS_PERSON, "2"),
    "3rd": (predicates.HAS_PERSON, "3"),
    "pres": (predicates.HAS_TENSE, "present"),
    "imperf": (predicates.HAS_TENSE, "imperfect"),
    "fut": (predicates.HAS_TENSE, "future"),
    "aor": (predicates.HAS_TENSE, "aorist"),
    "perf": (predicates.HAS_TENSE, "perfect"),
    "plup": (predicates.HAS_TENSE, "pluperfect"),
    "act": (predicates.HAS_VOICE, "active"),
    "mid": (predicates.HAS_VOICE, "middle"),
    "pass": (predicates.HAS_VOICE, "passive"),
    "mp": (predicates.HAS_VOICE, "middle/passive"),
    "ind": (predicates.HAS_MOOD, "indicative"),
    "subj": (predicates.HAS_MOOD, "subjunctive"),
    "opt": (predicates.HAS_MOOD, "optative"),
    "imperat": (predicates.HAS_MOOD, "imperative"),
    "inf": (predicates.HAS_MOOD, "infinitive"),
    "part": (predicates.HAS_MOOD, "participle"),
}


def _morpheus_feature_triples(form_anchor: str, tags: list[str], base_evidence: Mapping[str, object]) -> list[dict[str, object]]:
    triples: list[dict[str, object]] = []
    emitted: set[tuple[str, str]] = set()
    for tag in tags:
        feature = _MORPHEUS_TAG_FEATURES.get(tag.lower())
        if not feature or feature in emitted:
            continue
        predicate, value = feature
        triples.append(_make_triple(form_anchor, predicate, value, base_evidence))
        emitted.add(feature)
    return triples
```

- [ ] **Step 4: Emit canonical feature triples**

In `_build_perseus_header_triples`, immediately after the existing `has_pos` triple append, add:

```python
            triples.extend(_morpheus_feature_triples(form_anchor, tags, base_evidence))
```

Do not remove the existing raw `has_feature` tag or defs triples.

- [ ] **Step 5: Add claim contract assertion**

In `tests/test_claim_contracts.py`, extend the Diogenes morphology fixture test or add a new one that asserts at least one `has_case` or `has_tense` triple is present from a Perseus analysis header. Use the same style as the existing claim-contract tests and do not require live Diogenes.

- [ ] **Step 6: Run focused tests**

Run:

```bash
just test test_diogenes_morpheus_morphology test_diogenes_parser test_claim_contracts
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/langnet/execution/handlers/diogenes.py tests/test_diogenes_morpheus_morphology.py tests/test_claim_contracts.py
git commit -m "feat: promote diogenes morpheus morphology tags"
```

---

### Task 4: Encounter Integration Through Candidate Layer

**Files:**
- Modify: `src/langnet/cli.py`
- Modify: `tests/test_cli_encounter_output.py`
- Modify: `tests/test_foster_morphology_cases.py`

- [ ] **Step 1: Add encounter assertions for source-backed candidates**

In `tests/test_cli_encounter_output.py`, add tests for:

```python
def test_encounter_paradigm_resolution_prefers_sanskrit_supported_candidate() -> None:
    # Use existing fixture/helper style from this file.
    # Assert candidate lemma == "putra".
    # Assert candidate native_analyses include case=genitive number=plural.
    # Assert candidate paradigm_request.source == "heritage:sktdeclin".
```

Also add a Diogenes fixture test proving Morpheus triples can produce a Greek candidate:

```python
def test_encounter_paradigm_resolution_uses_diogenes_morpheus_features() -> None:
    # Build an encounter payload from fixture triples.
    # Assert lemma == "λόγος".
    # Assert native_analyses include genitive singular masculine.
    # Assert functional_analyses include possession_or_association.
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
just test test_cli_encounter_output
```

Expected: FAIL because `src/langnet/cli.py` still has private extraction paths and does not consume promoted Diogenes morphology uniformly.

- [ ] **Step 3: Replace private extraction path with morphology candidates**

In `src/langnet/cli.py`, keep the public output contract, but change `_encounter_paradigm_records` so it:

```python
from langnet.morphology.candidates import candidates_from_triples
```

and converts each `MorphologyCandidate` into the existing record shape expected by `resolve_paradigm_request`. The adapter should set:

```python
{
    "normalized_form": candidate.normalized_form,
    "observed_form": candidate.observed_form,
    "lemma": candidate.lemma,
    "part_of_speech": candidate.part_of_speech,
    "source": candidate.source,
    "features": candidate.features,
    "analyses": candidate.analyses or [candidate.features],
    "foster_labels": candidate.foster_labels,
    "functional_relations": candidate.functional_relations,
    "ranking_reasons": candidate.ranking_reasons,
}
```

Keep existing direct-record fallback only for records not represented by triples, and add a comment explaining which legacy path remains and why.

- [ ] **Step 4: Promote fixture file into acceptance checks**

In `tests/test_foster_morphology_cases.py`, add focused tests that load fixture cases and exercise helper-level conversion. Do not call live Heritage, Whitaker, or Diogenes in these tests; use fixture triples or existing parser fixtures.

- [ ] **Step 5: Run focused tests**

Run:

```bash
just test test_morphology_candidates test_cli_encounter_output test_foster_morphology_cases
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/langnet/cli.py tests/test_cli_encounter_output.py tests/test_foster_morphology_cases.py
git commit -m "feat: route encounter morphology through candidates"
```

---

### Task 5: Extend Paradigm Resolution Candidate Fields

**Files:**
- Modify: `src/langnet/paradigm/grammar.py`
- Modify: `src/langnet/paradigm/resolver.py`
- Modify: `docs/schemas/paradigm_resolution.v1.schema.json`
- Modify: `tests/test_paradigm_resolution_contract.py`

- [ ] **Step 1: Write schema contract test**

In `tests/test_paradigm_resolution_contract.py`, add a candidate containing:

```python
observed_form="puellae",
slot_features={"case": "genitive", "number": "singular"},
foster_labels=["Possessing Function"],
display_summary="puellae can be genitive singular: Possessing Function",
ranking_reasons=["observed-form", "case-number-gender"],
```

Assert that `cattrs.unstructure` output validates against `docs/schemas/paradigm_resolution.v1.schema.json`.

- [ ] **Step 2: Run schema test to verify failure**

Run:

```bash
just test test_paradigm_resolution_contract
```

Expected: FAIL because dataclass fields and schema properties are absent.

- [ ] **Step 3: Add optional dataclass fields**

In `src/langnet/paradigm/grammar.py`, extend `ParadigmResolutionCandidate`:

```python
    observed_form: str | None = None
    slot_features: dict[str, FeatureValue] = field(default_factory=dict)
    foster_labels: list[str] = field(default_factory=list)
    display_summary: str | None = None
    ranking_reasons: list[str] = field(default_factory=list)
```

Place these after `paradigm_kind` and before analysis lists so display fields are visible near the core candidate identity.

- [ ] **Step 4: Update resolver output**

In `src/langnet/paradigm/resolver.py`, when building a candidate from a lookup record, pass:

```python
observed_form=record.get("observed_form") or record.get("normalized_form") or searched_form,
slot_features=_primary_slot_features(native_analyses),
foster_labels=list(record.get("foster_labels") or []),
display_summary=_candidate_display_summary(lemma, native_analyses, record),
ranking_reasons=list(record.get("ranking_reasons") or []),
```

Add helpers:

```python
def _primary_slot_features(native_analyses: list[NativeAnalysis]) -> dict[str, FeatureValue]:
    if not native_analyses:
        return {}
    return dict(native_analyses[0].features)


def _candidate_display_summary(lemma: str, native_analyses: list[NativeAnalysis], record: Mapping[str, object]) -> str | None:
    labels = record.get("foster_labels")
    if not isinstance(labels, list) or not labels:
        return None
    feature_bits = []
    if native_analyses:
        features = native_analyses[0].features
        for key in ("case", "number", "gender", "person", "tense", "voice", "mood"):
            value = features.get(key)
            if value:
                feature_bits.append(str(value))
    grammar = " ".join(feature_bits)
    return f"{lemma}: {grammar} ({', '.join(str(label) for label in labels)})"
```

- [ ] **Step 5: Update JSON schema**

In `docs/schemas/paradigm_resolution.v1.schema.json`, add optional candidate properties:

```json
"observed_form": {"type": ["string", "null"]},
"slot_features": {"type": "object", "additionalProperties": {"type": ["string", "number", "integer", "boolean", "null"]}},
"foster_labels": {"type": "array", "items": {"type": "string"}},
"display_summary": {"type": ["string", "null"]},
"ranking_reasons": {"type": "array", "items": {"type": "string"}}
```

Keep `additionalProperties: false`.

- [ ] **Step 6: Run contract tests**

Run:

```bash
just test test_paradigm_resolution_contract test_paradigm_resolver
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/langnet/paradigm/grammar.py src/langnet/paradigm/resolver.py docs/schemas/paradigm_resolution.v1.schema.json tests/test_paradigm_resolution_contract.py
git commit -m "feat: expose learner fields on paradigm candidates"
```

---

### Task 6: Candidate Ranking And Table Slot Matching In Web UI

**Files:**
- Modify: `webapp/src/lib/paradigm-resolution.ts`
- Modify: `webapp/src/lib/paradigm-ui.ts`
- Modify: `webapp/src/lib/paradigm-ui.test.ts`
- Modify: `webapp/src/routes/+page.svelte`

- [ ] **Step 1: Add TypeScript tests**

In `webapp/src/lib/paradigm-ui.test.ts`, add:

```ts
import { curateParadigmCandidates, paradigmSlotMatchesCandidate } from './paradigm-ui';

test('curateParadigmCandidates keeps the supported putra genitive plural visible', () => {
  const candidates = [
    { lemma: 'noise', confidence: 'high', ranking_reasons: ['observed-form'], native_analyses: [], functional_analyses: [] },
    {
      lemma: 'putra',
      confidence: 'high',
      observed_form: 'putrāṇām',
      slot_features: { case: 'genitive', number: 'plural', gender: 'masculine' },
      ranking_reasons: ['observed-form', 'case-number-gender'],
      native_analyses: [],
      functional_analyses: [],
      paradigm_request: { source: 'heritage:sktdeclin', language: 'san', lemma: 'putra', kind: 'declension', options: { gender: 'Mas' } }
    }
  ];

  expect(curateParadigmCandidates(candidates, 1)[0].lemma).toBe('putra');
});

test('paradigmSlotMatchesCandidate matches by explicit slot features', () => {
  const candidate = { observed_form: 'λόγου', slot_features: { case: 'genitive', number: 'singular' } };
  const slot = { label: 'Genitive Singular', features: { case: 'genitive', number: 'singular' }, forms: [{ text: 'λόγου', normalized: 'λόγου' }] };

  expect(paradigmSlotMatchesCandidate(slot, candidate, 'λόγου')).toBe(true);
});
```

Adjust object fields to match existing TypeScript interfaces after opening `webapp/src/lib/paradigm-ui.test.ts`.

- [ ] **Step 2: Run web tests to verify failure**

Run:

```bash
cd webapp && just test
```

Expected: FAIL because `paradigmSlotMatchesCandidate` is absent or candidate ranking ignores `ranking_reasons`.

- [ ] **Step 3: Normalize optional fields**

In `webapp/src/lib/paradigm-resolution.ts`, add optional properties to the candidate type and normalizer:

```ts
observed_form?: string | null;
slot_features?: Record<string, string | number | boolean | null>;
foster_labels?: string[];
display_summary?: string | null;
ranking_reasons?: string[];
```

Default arrays to `[]` and objects to `{}`.

- [ ] **Step 4: Improve curation**

In `webapp/src/lib/paradigm-ui.ts`, update `curateParadigmCandidates` so the sort key prefers:

1. candidates with `paradigm_request`,
2. candidates with `case-number-gender` or `tense-voice-mood` in `ranking_reasons`,
3. candidates with `observed_form`,
4. higher confidence,
5. existing stable lemma ordering.

Add and export:

```ts
export function paradigmSlotMatchesCandidate(slot: ParadigmSlot, candidate: ParadigmResolutionCandidate, query: string): boolean {
  const slotFeatures = slot.features ?? {};
  const targetFeatures = candidate.slot_features ?? {};
  const featureKeys = Object.keys(targetFeatures);
  if (featureKeys.length > 0 && featureKeys.every((key) => String(slotFeatures[key] ?? '') === String(targetFeatures[key] ?? ''))) {
    return true;
  }

  const targets = new Set([candidate.observed_form, query].filter((value): value is string => Boolean(value)));
  return slot.forms.some((form) => targets.has(form.text) || targets.has(form.normalized ?? ''));
}
```

- [ ] **Step 5: Use shared matcher in Svelte**

In `webapp/src/routes/+page.svelte`, replace local slot-match logic with `paradigmSlotMatchesCandidate(slot, candidate, currentQuery)`. Keep the old query-only fallback inside the helper, not in the component.

- [ ] **Step 6: Run web verification**

Run:

```bash
cd webapp && just test
cd webapp && just verify
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add webapp/src/lib/paradigm-resolution.ts webapp/src/lib/paradigm-ui.ts webapp/src/lib/paradigm-ui.test.ts webapp/src/routes/+page.svelte
git commit -m "feat: improve foster forms panel curation"
```

---

### Task 7: Foster Learning Documentation

**Files:**
- Create: `docs/FOSTER_FUNCTIONAL_GRAMMAR_EXAMPLES.md`
- Modify: `docs/PEDAGOGICAL_PHILOSOPHY.md`
- Modify: `docs/OUTPUT_GUIDE.md`
- Modify: `docs/technical/backend/paradigm-generation-limitations.md`
- Modify: `webapp/docs/UI.md`
- Modify: `webapp/docs/REGRESSION_CASES.md`

- [ ] **Step 1: Create learner examples**

Create `docs/FOSTER_FUNCTIONAL_GRAMMAR_EXAMPLES.md`:

```markdown
# Foster Functional Grammar Examples

Foster labels explain the job a form is doing. They do not replace the native grammar label or source evidence.

| Foster label | Native grammar examples | Learner reading |
| --- | --- | --- |
| Naming Function | Greek `λόγος` nominative singular; Sanskrit `putraḥ` nominative singular; Latin `puella` nominative singular | The form can name the subject or topic. |
| Receiving Function | Greek `λόγον` accusative singular; Sanskrit `putram` accusative singular; Latin `puellam` accusative singular | The form can receive the action. |
| Possessing Function | Greek `λόγου` genitive singular; Sanskrit `putrāṇām` genitive plural; Latin `puellae` genitive singular | The form can mark possession, association, or belonging. |
| To-For Function | Greek `λόγῳ` dative singular; Latin `puellae` dative singular | The form can mark a recipient, goal, or beneficiary. |
| By-With Function | Sanskrit instrumental forms; Latin ablative forms when used instrumentally | The form can mark means or accompaniment. |
| From Function | Sanskrit ablative forms; Latin ablative forms when used separatively | The form can mark source or separation. |
| In-At Function | Sanskrit locative forms; Greek and Latin dative/ablative location uses by context | The form can mark location. |
| Calling Function | Greek `λόγε` vocative singular; Sanskrit vocative forms; Latin `puella` vocative singular | The form can address someone or something directly. |

## What A Good Lookup Should Show

For `putraa.naam`, a learner should see:

- observed form: `putrāṇām`
- lemma: `putra`
- native grammar: masculine genitive plural
- Foster label: Possessing Function
- evidence source: Heritage morphology
- action: load the `putra` declension table and highlight genitive plural

For `puellae`, a learner should see the ambiguity instead of one forced answer:

- `puellae`: feminine genitive singular, Possessing Function
- `puellae`: feminine dative singular, To-For Function
- `puellae`: feminine nominative plural, Naming Function

For `λόγου`, a learner should see:

- observed form: `λόγου`
- lemma: `λόγος`
- native grammar: masculine genitive singular
- Foster label: Possessing Function
- evidence source: Diogenes/Morpheus analysis
- action: load the Diogenes inflection table and highlight genitive singular
```

- [ ] **Step 2: Link examples from philosophy doc**

In `docs/PEDAGOGICAL_PHILOSOPHY.md`, add a short paragraph under the Foster section:

```markdown
Concrete examples live in [Foster Functional Grammar Examples](FOSTER_FUNCTIONAL_GRAMMAR_EXAMPLES.md). That page is the learner-facing reference for mapping terms such as Naming Function and Possessing Function back to conventional case labels in Latin, Greek, and Sanskrit.
```

- [ ] **Step 3: Update output guide and limitations**

In `docs/OUTPUT_GUIDE.md`, document the candidate fields from Task 5 and include one compact JSON fragment:

```json
{
  "lemma": "putra",
  "observed_form": "putrāṇām",
  "slot_features": {"case": "genitive", "number": "plural", "gender": "masculine"},
  "foster_labels": ["Possessing Function"],
  "paradigm_request": {"source": "heritage:sktdeclin", "language": "san", "lemma": "putra", "kind": "declension"}
}
```

In `docs/technical/backend/paradigm-generation-limitations.md`, state that source-backed tables exist, but arbitrary local reverse morphology remains out of scope.

- [ ] **Step 4: Update web docs**

In `webapp/docs/UI.md`, describe the Forms panel:

```markdown
The Forms panel ranks candidates by source-backed morphology, shows native grammar beside Foster labels, and loads full tables only when requested. When a candidate includes `slot_features`, loaded tables highlight the matching slot.
```

In `webapp/docs/REGRESSION_CASES.md`, add commands:

```bash
just cli encounter san putraa.naam heritage --include-paradigm-resolution --output json --translation-mode off
just cli encounter lat puellae whitakers --include-paradigm-resolution --output json --translation-mode off
just cli encounter grc λόγου diogenes --include-paradigm-resolution --output json --translation-mode off
```

- [ ] **Step 5: Run docs checks**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 6: Commit**

```bash
git add docs/FOSTER_FUNCTIONAL_GRAMMAR_EXAMPLES.md docs/PEDAGOGICAL_PHILOSOPHY.md docs/OUTPUT_GUIDE.md docs/technical/backend/paradigm-generation-limitations.md webapp/docs/UI.md webapp/docs/REGRESSION_CASES.md
git commit -m "docs: add foster morphology examples"
```

---

### Task 8: End-To-End Verification And Issue Triage

**Files:**
- Modify: `docs/EXECUTION_PLAN.md`
- Modify: `docs/STATUS.md`

- [ ] **Step 1: Run focused backend verification**

Run:

```bash
just test test_morphology_candidates test_diogenes_morpheus_morphology test_foster_morphology_cases test_cli_encounter_output test_paradigm_resolution_contract test_paradigm_resolver
```

Expected: PASS.

- [ ] **Step 2: Run full backend verification**

Run:

```bash
just lint-all
just test-fast
```

Expected: PASS.

- [ ] **Step 3: Run web verification**

Run:

```bash
cd webapp && just verify
```

Expected: PASS.

- [ ] **Step 4: Run live source-backed smoke checks**

Run these only when Heritage, Diogenes, and Whitaker are locally available:

```bash
just cli encounter san putraa.naam heritage --include-paradigm-resolution --output json --translation-mode off --no-cache
just cli encounter lat puellae whitakers --include-paradigm-resolution --output json --translation-mode off --no-cache
just cli encounter grc λόγου diogenes --include-paradigm-resolution --output json --translation-mode off --no-cache
just cli paradigm san putra --kind declension --gender Mas --output json
just cli paradigm grc lo/gos --kind declension --output json
```

Expected:

- `putraa.naam` shows `putra` genitive plural and `heritage:sktdeclin`.
- `puellae` shows Latin ambiguity and `diogenes:inflect`.
- `λόγου` shows a Diogenes/Morpheus genitive singular candidate when Morpheus evidence is present.
- `putra` table contains a genitive plural slot with `putrāṇām`.
- `lo/gos` table contains a genitive singular slot with `λόγου`.

- [ ] **Step 5: Update status docs**

In `docs/EXECUTION_PLAN.md`, add this current milestone:

```markdown
- Foster-friendly morphology: source-backed Heritage, Whitaker, and Diogenes/Morpheus evidence now flows into ranked paradigm candidates, with Foster labels and table slot targets.
```

In `docs/STATUS.md`, add:

```markdown
Foster-friendly morphology is implemented for the source-backed path. Remaining future work is broader local reverse morphology and any source-specific edge cases not represented by Heritage, Whitaker, or Diogenes/Morpheus evidence.
```

- [ ] **Step 6: Prepare GitHub issue actions**

Use these issue comments:

For issue `#3 improved diogenes integration`:

```markdown
Updated scope: keep this open, but narrow it to Diogenes/Morpheus morphology promotion and source-backed inflection UX. LangNet now consumes Morpheus analysis lines when Diogenes pages expose them, promotes tag bags into canonical morphology predicates, and uses those facts to resolve Foster-friendly paradigm candidates. Remaining work: validate more Greek/Latin tag variants and decide whether Diogenes word-search should become a separate optional feature.
```

For issue `#2 UI companion project`:

```markdown
Recommend closing as superseded. The SvelteKit webapp now owns the browser/mobile companion surface, including lookup, Forms/paradigm actions, and lazy paradigm table loading. Any remaining UI work should be filed as targeted webapp issues.
```

For issue `#1 reader functionality`:

```markdown
Recommend keeping open but renaming to "Reader workflow: passage -> lookup -> usage examples". The dictionary and Forms workflow is now clearer, but reader integration is still a product workflow question: first-party reader hosting, external reader links, and source-backed usage examples by language.
```

- [ ] **Step 7: Commit status updates**

```bash
git add docs/EXECUTION_PLAN.md docs/STATUS.md
git commit -m "docs: record foster morphology milestone"
```

---

## Self-Review Notes

- The plan covers the user correction that Heritage, Whitaker, Diogenes tables, and web Forms UI already exist.
- The Diogenes task specifically targets Morpheus/Perseus tags already present on pages, rather than assuming a new endpoint.
- The plan remains source-language agnostic by normalizing to candidate features and Foster display while preserving source-specific provenance.
- The plan does not lose native grammar; it adds Foster labels beside `case`, `number`, `gender`, `person`, `tense`, `voice`, and `mood`.
- The plan is intentionally actionable: every task has files, failing tests, implementation direction, verification commands, and commit points.
