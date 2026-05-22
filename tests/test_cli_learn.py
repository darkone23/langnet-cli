from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from click.testing import CliRunner

from langnet.cli import main

FIXTURE_DIR = Path("tests/fixtures/learning")
MIN_GENITIVE_WORK_EVIDENCE = 3
SEGMENT_BACKED_CONCEPT_COUNT = 23
GENITIVE_SEGMENT_EVIDENCE_COUNT = 3


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _concept_golden_projection(concept: dict[str, object]) -> dict[str, object]:
    evidence = concept["evidence"]
    skills = concept["skills"]
    assert isinstance(evidence, list)
    assert isinstance(skills, dict)
    evidence_items = cast(list[dict[str, object]], evidence)
    skill_map = cast(dict[str, object], skills)
    return {
        "id": concept["id"],
        "kind": concept["kind"],
        "foster_gateway": concept["foster_gateway"],
        "traditional": concept["traditional"],
        "source_anchor_ids": [item["source_anchor_id"] for item in evidence_items],
        "skill_keys": sorted(skill_map),
    }


def test_learn_concepts_lists_registry_for_cli_exploration() -> None:
    result = CliRunner().invoke(main, ["learn", "concepts", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "langnet.grammar_concepts.v1"
    ids = [concept["id"] for concept in payload["concepts"]]
    assert "case.genitive" in ids
    assert "process.declension" in ids


def test_learn_concept_shows_foster_and_native_traditional_terms() -> None:
    result = CliRunner().invoke(main, ["learn", "concept", "case.genitive", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["concept"]["foster_gateway"] == "Possessing Function"
    assert payload["concept"]["traditional"]["grc"] == "γενική"
    assert payload["concept"]["traditional"]["lat"] == "genetivus"
    assert payload["concept"]["traditional"]["san"] == "ṣaṣṭhī vibhakti"
    assert payload["concept"]["traditional"]["san_role"] == "sambandha"
    assert "Sanskrit kāraka/vibhakti grammatical tradition" in payload["concept"]["source_basis"]
    evidence = payload["concept"]["evidence"]
    assert evidence[0]["evidence_level"] == "reader_work"
    assert {item["source_anchor_id"] for item in evidence} >= {
        "grammar.source.dionysius_thrax.ars_grammatica",
        "grammar.source.varro.de_lingua_latina",
        "grammar.source.panini.astadhyayi",
    }
    assert {item["work_id"] for item in evidence} >= {
        "langnet:reader:tlg:tlg0063.001",
        "langnet:reader:phi:lat0684.001",
        "langnet:reader:sanskrit_dcs:dcs_413",
    }


def test_learn_concept_case_genitive_matches_golden_fixture() -> None:
    result = CliRunner().invoke(main, ["learn", "concept", "case.genitive", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert {
        "schema_version": payload["schema_version"],
        "concept": _concept_golden_projection(payload["concept"]),
    } == _fixture("learn_concept_case_genitive.json")


def test_learn_evidence_report_summarizes_ready_and_remaining_evidence() -> None:
    result = CliRunner().invoke(main, ["learn", "evidence-report", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    summary = payload["summary"]
    assert payload["schema_version"] == "langnet.grammar_evidence_report.v1"
    assert summary["total_concepts"] >= 1
    assert summary["with_source_basis"] == summary["total_concepts"]
    assert summary["with_work_evidence"] == summary["total_concepts"]
    assert summary["missing_work_evidence"] == 0
    assert summary["with_segment_evidence"] == SEGMENT_BACKED_CONCEPT_COUNT
    assert (
        summary["missing_segment_evidence"]
        == summary["total_concepts"] - SEGMENT_BACKED_CONCEPT_COUNT
    )
    genitive = next(item for item in payload["concepts"] if item["id"] == "case.genitive")
    assert genitive["evidence_counts"]["reader_work"] >= MIN_GENITIVE_WORK_EVIDENCE
    assert genitive["evidence_counts"]["reader_segment"] == GENITIVE_SEGMENT_EVIDENCE_COUNT
    assert genitive["missing"] == []
    guna = next(item for item in payload["concepts"] if item["id"] == "sound_change.guna")
    assert guna["evidence_counts"]["reader_segment"] == 1
    assert guna["missing"] == []


def test_learn_map_projects_features_to_concepts() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--part-of-speech",
            "noun",
            "--paradigm-kind",
            "declension",
            "--feature",
            "case=genitive",
            "--feature",
            "number=plural",
            "--feature",
            "gender=masculine",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["concept_ids"] == [
        "case.genitive",
        "number.plural",
        "gender.masculine",
        "process.declension",
    ]
    assert payload["concepts"][0]["traditional"]["san_role"] == "sambandha"


def test_learn_map_genitive_plural_masculine_matches_golden_fixture() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--part-of-speech",
            "noun",
            "--paradigm-kind",
            "declension",
            "--feature",
            "case=genitive",
            "--feature",
            "number=plural",
            "--feature",
            "gender=masculine",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert {
        "schema_version": payload["schema_version"],
        "input": payload["input"],
        "concept_ids": payload["concept_ids"],
        "concepts": [_concept_golden_projection(concept) for concept in payload["concepts"]],
    } == _fixture("learn_map_genitive_plural_masculine.json")
