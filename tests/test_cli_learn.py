from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from click.testing import CliRunner

from langnet.cli import main
from langnet.foster_ossa.essentials import default_foster_essentials
from langnet.learning.foster_bridge import load_foster_bridges

FIXTURE_DIR = Path("tests/fixtures/learning")
MIN_GENITIVE_WORK_EVIDENCE = 3
SEGMENT_BACKED_CONCEPT_COUNT = 24
GENITIVE_SEGMENT_EVIDENCE_COUNT = 3
PARTICIPLE_SEGMENT_EVIDENCE_COUNT = 4


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
    assert "process.participle" in ids


def test_learn_concepts_compact_view_is_ui_friendly() -> None:
    result = CliRunner().invoke(
        main,
        ["learn", "concepts", "--kind", "case", "--view", "compact", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["view"] == "compact"
    genitive = next(concept for concept in payload["concepts"] if concept["id"] == "case.genitive")
    assert genitive["source_evidence_counts"]["reader_segment"] >= GENITIVE_SEGMENT_EVIDENCE_COUNT
    assert genitive["foster_bridge_ids"] == ["of-possession"]
    assert genitive["foster_bridges"][0] == {
        "id": "of-possession",
        "status": "promoted_match",
        "concept_ids": ["case.genitive"],
        "related_concept_ids": [],
        "plain_english": "Foster/Ossa possession or relation maps to the genitive concept.",
        "learner_action": (
            "Ask what relation, possession, belonging, source, or description the form marks."
        ),
        "morphology_predicates": ["case=genitive"],
        "source_refs": ["page:69", "page:125", "page:140", "page:522", "page:618"],
        "summary_refs": ["toc:1.6", "toc:1.22", "toc:1.25", "toc:4.30"],
    }
    assert genitive["native_gateways"] == [
        {
            "language": "grc",
            "label": "Greek",
            "term": "γενική",
            "role": "",
            "foster_gateway": "Possessing Function",
            "explanation": (
                "Greek gateway: γενική; LangNet uses Possessing Function as the learner gateway."
            ),
        },
        {
            "language": "lat",
            "label": "Latin",
            "term": "genetivus",
            "role": "",
            "foster_gateway": "Possessing Function",
            "explanation": (
                "Latin gateway: genetivus; LangNet uses Possessing Function as the learner gateway."
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
    ]
    assert "evidence" not in genitive


def test_learn_concept_shows_foster_and_native_traditional_terms() -> None:
    result = CliRunner().invoke(main, ["learn", "concept", "case.genitive", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["concept"]["foster_gateway"] == "Possessing Function"
    assert payload["concept"]["traditional"]["grc"] == "γενική"
    assert payload["concept"]["traditional"]["lat"] == "genetivus"
    assert payload["concept"]["traditional"]["san"] == "ṣaṣṭhī vibhakti"
    assert payload["concept"]["traditional"]["san_role"] == "sambandha"
    assert payload["concept"]["native_gateways"][2] == {
        "language": "san",
        "label": "Sanskrit",
        "term": "ṣaṣṭhī vibhakti",
        "role": "sambandha",
        "foster_gateway": "Possessing Function",
        "explanation": (
            "Sanskrit gateway: ṣaṣṭhī vibhakti (sambandha); "
            "LangNet uses Possessing Function as the learner gateway."
        ),
    }
    assert "Sanskrit kāraka/vibhakti grammatical tradition" in payload["concept"]["source_basis"]
    foster_bridges = payload["concept"]["foster_bridges"]
    assert foster_bridges[0]["id"] == "of-possession"
    assert foster_bridges[0]["foster_terms"][:2] == [
        "of-possession",
        "function of-possession",
    ]
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
    participle = next(item for item in payload["concepts"] if item["id"] == "process.participle")
    assert participle["evidence_counts"]["reader_segment"] == PARTICIPLE_SEGMENT_EVIDENCE_COUNT
    assert participle["missing"] == []


def test_learn_foster_bridge_lists_reviewed_foster_ossa_mappings() -> None:
    result = CliRunner().invoke(main, ["learn", "foster-bridge", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "langnet.foster_bridge.v1"
    bridges = {bridge["id"]: bridge for bridge in payload["bridges"]}
    assert bridges["of-possession"]["status"] == "promoted_match"
    assert bridges["of-possession"]["concept_ids"] == ["case.genitive"]
    assert bridges["by-with-from-in"]["status"] == "aggregate_candidate"
    assert bridges["by-with-from-in"]["concept_ids"] == []
    assert bridges["by-with-from-in"]["related_concept_ids"] == [
        "case.ablative",
        "case.instrumental",
        "case.locative",
    ]


def test_learn_foster_bridges_are_sourced_from_foster_essentials() -> None:
    essentials = {essential.id: essential for essential in default_foster_essentials()}
    bridges = load_foster_bridges()

    assert set(bridges) == set(essentials)
    for bridge_id, essential in essentials.items():
        bridge = bridges[bridge_id]
        assert bridge.source_refs == list(essential.source_refs)
        assert bridge.summary_refs == list(essential.summary_refs)
        assert bridge.learner_action == essential.learner_action
        assert bridge.product_use == essential.product_use
        assert bridge.morphology_predicates == list(essential.morphology_predicates)

    assert bridges["by-with-from-in"].concept_ids == []
    assert bridges["by-with-from-in"].related_concept_ids == [
        "case.ablative",
        "case.instrumental",
        "case.locative",
    ]


def test_learn_foster_bridge_detail_resolves_alias_and_embeds_concepts() -> None:
    result = CliRunner().invoke(
        main,
        ["learn", "foster-bridge", "function to-for-from", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    bridge = payload["bridge"]
    assert bridge["id"] == "to-for-from"
    assert bridge["concept_ids"] == ["case.dative"]
    assert bridge["concepts"][0]["id"] == "case.dative"
    assert bridge["concepts"][0]["foster_gateway"] == "To-For Function"
    assert "docs/reference/foster-ossa/CORE_FUNCTION_BRIDGE.md" in bridge["review_docs"]


def test_learn_foster_bridge_pretty_output_shows_aggregate_status() -> None:
    result = CliRunner().invoke(main, ["learn", "foster-bridge", "by-with-from-in"])

    assert result.exit_code == 0, result.output
    assert "by-with-from-in [aggregate_candidate]" in result.output
    assert "related: case.ablative, case.instrumental, case.locative" in result.output
    assert "not a single universal case concept" in result.output


def test_learn_foster_bridge_compact_view_includes_ui_actions() -> None:
    result = CliRunner().invoke(
        main,
        ["learn", "foster-bridge", "of-possession", "--view", "compact", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    bridge = payload["bridge"]
    assert payload["view"] == "compact"
    assert bridge["id"] == "of-possession"
    assert bridge["learner_action"].startswith("Ask what relation")
    assert bridge["product_use"] == "Show a possession/relation gateway beside genitive evidence."
    assert bridge["morphology_predicates"] == ["case=genitive"]
    assert bridge["source_actions"][0] == {
        "ref": "page:69",
        "kind": "foster_ossa_page",
        "status": "actionable_unresolved",
        "command": [
            "foster-ossa",
            "search",
            "of-possession",
            "--limit",
            "5",
            "--output",
            "json",
        ],
    }


def test_learn_concept_links_related_foster_aggregate_candidates() -> None:
    result = CliRunner().invoke(main, ["learn", "concept", "case.ablative", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    concept = payload["concept"]
    assert concept["related_foster_bridge_ids"] == ["by-with-from-in"]
    assert concept["foster_bridges"][0]["id"] == "by-with-from-in"
    assert concept["foster_bridges"][0]["status"] == "aggregate_candidate"


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
    assert payload["concepts"][0]["foster_bridge_ids"] == ["of-possession"]
    assert payload["diagnostics"] == {"unmapped_features": [], "ignored_features": []}


def test_learn_map_compact_view_keeps_diagnostics_and_small_concepts() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--pos",
            "noun",
            "--paradigm-kind",
            "declension",
            "--feature",
            "case=genitive",
            "--view",
            "compact",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["view"] == "compact"
    assert payload["concept_ids"] == ["case.genitive", "process.declension"]
    assert payload["diagnostics"] == {"unmapped_features": [], "ignored_features": []}
    assert payload["concepts"][0]["foster_bridge_ids"] == ["of-possession"]
    assert "evidence" not in payload["concepts"][0]


def test_learn_map_normalizes_feature_input_for_cli_exploration() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--pos",
            "NOUN",
            "--paradigm-kind",
            "DECLENSION",
            "--feature",
            "Case= Ablative ",
            "--feature",
            "Number= Dual ",
            "--feature",
            "Gender= Neuter ",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["input"] == {
        "features": {"case": "ablative", "number": "dual", "gender": "neuter"},
        "part_of_speech": "noun",
        "paradigm_kind": "declension",
    }
    assert payload["concept_ids"] == [
        "case.ablative",
        "number.dual",
        "gender.neuter",
        "process.declension",
    ]
    assert payload["diagnostics"] == {"unmapped_features": [], "ignored_features": []}


def test_learn_map_rejects_duplicate_feature_keys() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--feature",
            "case=genitive",
            "--feature",
            "Case=dative",
            "--output",
            "json",
        ],
    )

    assert result.exit_code != 0
    assert "duplicate --feature key: case" in result.output


def test_learn_doctor_reports_didactic_readiness_and_known_gaps() -> None:
    result = CliRunner().invoke(main, ["learn", "doctor", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "langnet.learn_doctor.v1"
    assert payload["ok"] is True
    checks = {check["id"]: check for check in payload["checks"]}
    assert checks["learn:evidence"]["status"] == "warn"
    assert "process.declension" in checks["learn:evidence"]["metadata"]["concepts_with_gaps"]
    assert checks["learn:foster_essentials"]["status"] == "pass"
    assert checks["learn:foster_refs"]["status"] == "warn"
    assert checks["learn:foster_refs"]["metadata"]["sample_actions"][0]["status"] == (
        "actionable_unresolved"
    )
    assert checks["learn:mapper"]["status"] == "pass"


def test_learn_map_reports_unmapped_and_ignored_features() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--pos",
            "verb",
            "--feature",
            "voice=middle",
            "--feature",
            "dialect=ionic",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["concept_ids"] == ["process.conjugation"]
    assert payload["diagnostics"] == {
        "unmapped_features": [{"key": "voice", "value": "middle"}],
        "ignored_features": [{"key": "dialect", "value": "ionic"}],
    }


def test_learn_map_projects_participial_forms_to_action_as_noun_form() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--pos",
            "participle",
            "--paradigm-kind",
            "declension",
            "--feature",
            "case=accusative",
            "--feature",
            "number=singular",
            "--feature",
            "gender=neuter",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["concept_ids"] == [
        "case.accusative",
        "number.singular",
        "gender.neuter",
        "process.participle",
        "process.declension",
    ]
    participle = next(
        concept for concept in payload["concepts"] if concept["id"] == "process.participle"
    )
    assert participle["foster_gateway"] == "Action As Noun Form"
    assert participle["traditional"]["lat"] == "participium"
    assert participle["traditional"]["san"] == "kṛdanta / kṛt"


def test_learn_map_pretty_output_shows_mapping_diagnostics() -> None:
    result = CliRunner().invoke(
        main,
        [
            "learn",
            "map",
            "--pos",
            "verb",
            "--feature",
            "voice=middle",
            "--feature",
            "dialect=ionic",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Concept mapping:" in result.output
    assert "- process.conjugation" in result.output
    assert "Unmapped features:" in result.output
    assert "- voice=middle" in result.output
    assert "Ignored features:" in result.output
    assert "- dialect=ionic" in result.output


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
