from __future__ import annotations

import json
from pathlib import Path

import cattrs
import jsonschema

from langnet.paradigm.grammar import (
    FunctionalAnalysis,
    NativeAnalysis,
    ParadigmRequest,
    ParadigmResolutionCandidate,
    ParadigmResolutionPayload,
)

SCHEMA_PATH = Path("docs/schemas/paradigm_resolution.v1.schema.json")
PUELLAE_ANALYSIS_COUNT = 3


def _assert_matches_schema(payload: object) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_sanskrit_syncretic_resolution_preserves_native_and_functional_analysis() -> None:
    candidate = ParadigmResolutionCandidate(
        lemma="deva",
        entry_type="variant",
        part_of_speech="noun",
        paradigm_kind="declension",
        native_analyses=[
            NativeAnalysis(
                language="san",
                features={
                    "case": "dative",
                    "number": "plural",
                    "gender": "masculine",
                    "native_label": "caturthi bahuvacana",
                },
                source="heritage:sktreader",
            ),
            NativeAnalysis(
                language="san",
                features={
                    "case": "ablative",
                    "number": "plural",
                    "gender": "masculine",
                    "native_label": "pancami bahuvacana",
                },
                source="heritage:sktreader",
            ),
        ],
        functional_analyses=[
            FunctionalAnalysis(
                relation="recipient_or_goal",
                native_feature={"case": "dative", "number": "plural"},
                confidence="high",
            ),
            FunctionalAnalysis(
                relation="source_or_separation",
                native_feature={"case": "ablative", "number": "plural"},
                confidence="high",
            ),
        ],
        paradigm_request=ParadigmRequest(
            source="heritage:sktdeclin",
            language="san",
            lemma="deva",
            kind="declension",
            options={"gender": "Mas"},
        ),
        confidence="high",
        provenance=["heritage:sktreader", "cdsl:mw"],
    )
    payload = ParadigmResolutionPayload(
        searched_form="devebhyaḥ",
        normalized_form="devebhyaḥ",
        language="san",
        candidates=[candidate],
    )

    data = cattrs.unstructure(payload)

    _assert_matches_schema(data)
    analyses = data["candidates"][0]["native_analyses"]
    assert [analysis["features"]["case"] for analysis in analyses] == ["dative", "ablative"]
    assert {analysis["relation"] for analysis in data["candidates"][0]["functional_analyses"]} == {
        "recipient_or_goal",
        "source_or_separation",
    }


def test_latin_puellae_can_carry_multiple_native_analyses_for_one_lemma() -> None:
    candidate = ParadigmResolutionCandidate(
        lemma="puella",
        entry_type="variant",
        part_of_speech="noun",
        paradigm_kind="declension",
        observed_form="puellae",
        slot_features={"case": "genitive", "number": "singular"},
        foster_display="Possessing Function; Single; Female",
        display_summary="puella: genitive singular (Possessing Function; Single; Female)",
        ranking_reasons=["observed-form", "case-number-gender"],
        native_analyses=[
            NativeAnalysis(
                language="lat",
                features={"case": "genitive", "number": "singular", "declension": "1"},
                source="whitakers",
            ),
            NativeAnalysis(
                language="lat",
                features={"case": "dative", "number": "singular", "declension": "1"},
                source="whitakers",
            ),
            NativeAnalysis(
                language="lat",
                features={"case": "nominative", "number": "plural", "declension": "1"},
                source="whitakers",
            ),
        ],
        functional_analyses=[
            FunctionalAnalysis(
                relation="possession_or_association",
                native_feature={"case": "genitive", "number": "singular"},
                confidence="medium",
            ),
            FunctionalAnalysis(
                relation="recipient_or_goal",
                native_feature={"case": "dative", "number": "singular"},
                confidence="medium",
            ),
            FunctionalAnalysis(
                relation="subject",
                native_feature={"case": "nominative", "number": "plural"},
                confidence="medium",
            ),
        ],
        paradigm_request=ParadigmRequest(
            source="diogenes:inflect",
            language="lat",
            lemma="puella",
            kind="declension",
            options={},
        ),
        confidence="medium",
        provenance=["whitakers"],
    )
    payload = ParadigmResolutionPayload(
        searched_form="puellae",
        normalized_form="puellae",
        language="lat",
        candidates=[candidate],
    )

    data = cattrs.unstructure(payload)

    _assert_matches_schema(data)
    assert len(data["candidates"][0]["native_analyses"]) == PUELLAE_ANALYSIS_COUNT
    assert data["candidates"][0]["observed_form"] == "puellae"
    assert data["candidates"][0]["foster_display"] == "Possessing Function; Single; Female"
    assert data["candidates"][0]["paradigm_request"]["source"] == "diogenes:inflect"


def test_unresolved_resolution_explains_missing_metadata_without_guessing() -> None:
    candidate = ParadigmResolutionCandidate(
        lemma="unknown",
        entry_type="unknown",
        part_of_speech="noun",
        paradigm_kind="declension",
        native_analyses=[],
        functional_analyses=[],
        paradigm_request=None,
        confidence="low",
        provenance=["fixture"],
        unresolved_reason="missing_gender_or_declension",
    )
    payload = ParadigmResolutionPayload(
        searched_form="mystery",
        normalized_form="mystery",
        language="san",
        candidates=[candidate],
    )

    data = cattrs.unstructure(payload)

    _assert_matches_schema(data)
    assert data["candidates"][0]["paradigm_request"] is None
    assert data["candidates"][0]["unresolved_reason"] == "missing_gender_or_declension"


def test_candidate_can_carry_optional_learning_overlay_without_breaking_contract() -> None:
    payload = {
        "schema_version": "langnet.paradigm_resolution.v1",
        "searched_form": "putraa.naam",
        "normalized_form": "putrāṇām",
        "language": "san",
        "warnings": [],
        "candidates": [
            {
                "lemma": "putra",
                "entry_type": "root",
                "part_of_speech": "noun",
                "paradigm_kind": "declension",
                "observed_form": "putrāṇām",
                "slot_features": {
                    "case": "genitive",
                    "number": "plural",
                    "gender": "masculine",
                },
                "foster_display": "Possessing Function; Group; Male",
                "display_summary": "putrāṇām: Possessing Function; Group; Male",
                "ranking_reasons": ["observed-form", "lemma", "case-number-gender"],
                "concept_ids": [
                    "case.genitive",
                    "number.plural",
                    "gender.masculine",
                    "process.declension",
                ],
                "learning_overlay": {
                    "schema_version": "langnet.learning_overlay.v1",
                    "status": "mapped",
                    "concept_ids": ["case.genitive"],
                    "concepts": [
                        {
                            "id": "case.genitive",
                            "kind": "case",
                            "foster_gateway": "Possessing Function",
                            "plain_english": (
                                "Marks belonging, association, source, description, or relation."
                            ),
                            "traditional": {
                                "en": "genitive",
                                "grc": "γενική",
                                "lat": "genetivus",
                                "san": "ṣaṣṭhī vibhakti",
                                "san_role": "sambandha",
                            },
                            "native_gateways": [
                                {
                                    "language": "grc",
                                    "label": "Greek",
                                    "term": "γενική",
                                    "role": "",
                                    "foster_gateway": "Possessing Function",
                                    "explanation": (
                                        "Greek gateway: γενική; LangNet uses "
                                        "Possessing Function as the learner gateway."
                                    ),
                                },
                                {
                                    "language": "lat",
                                    "label": "Latin",
                                    "term": "genetivus",
                                    "role": "",
                                    "foster_gateway": "Possessing Function",
                                    "explanation": (
                                        "Latin gateway: genetivus; LangNet uses "
                                        "Possessing Function as the learner gateway."
                                    ),
                                },
                                {
                                    "language": "san",
                                    "label": "Sanskrit",
                                    "term": "ṣaṣṭhī vibhakti",
                                    "role": "sambandha",
                                    "foster_gateway": "Possessing Function",
                                    "explanation": (
                                        "Sanskrit gateway: ṣaṣṭhī vibhakti (sambandha); "
                                        "LangNet uses Possessing Function as the learner gateway."
                                    ),
                                },
                            ],
                            "source_evidence": [
                                {
                                    "evidence_level": "reader_work",
                                    "source_anchor_id": "grammar.source.panini.astadhyayi",
                                    "work_id": "langnet:reader:sanskrit_dcs:dcs_413",
                                    "canonical_text_id": ("urn:ctsv2:san:astadhyayi-vrddhir-adaic"),
                                    "cts_work_urn": None,
                                    "citation_path": None,
                                    "canonical_address": ("urn:ctsv2:san:astadhyayi-vrddhir-adaic"),
                                    "label": "Pāṇini, Aṣṭādhyāyī",
                                }
                            ],
                        }
                    ],
                    "missing_evidence": ["reader_segment_links"],
                },
                "native_analyses": [],
                "functional_analyses": [],
                "paradigm_request": None,
                "confidence": "high",
                "provenance": ["heritage"],
                "unresolved_reason": None,
            }
        ],
    }

    _assert_matches_schema(payload)
