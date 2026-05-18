from __future__ import annotations

from query_spec import CanonicalCandidate, LanguageHint, NormalizedQuery

from langnet.cli import _filter_plan_tools
from langnet.execution import predicates
from langnet.execution.handlers.bailly import bailly_entry_triples
from langnet.planner.core import PlannerConfig, ToolPlanner

AGELAIOS_PAGE = 90
NESTED_BAILLY_BLOCK_LEVEL = 2


def test_bailly_entry_triples_include_source_entry_and_french_segments() -> None:
    triples = bailly_entry_triples(
        {
            "entry_id": "bailly-p090-c1-0004",
            "lemma": "ἀγελαῖος",
            "lemma_norm": "agelaios",
            "page_start": AGELAIOS_PAGE,
            "page_end": AGELAIOS_PAGE,
            "blocks": [
                {"path": "00", "marker": "head", "text": "ἀγελαῖος, α, ον [ ᾰγ ]"},
                {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
            ],
        }
    )

    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss_triple["metadata"]
    evidence = metadata["evidence"]
    source_entry = metadata["source_entry"]
    source_segments = metadata["source_segments"]

    assert metadata["source_lang"] == "fr"
    assert evidence["source_tool"] == "bailly"
    assert source_entry["page_start"] == AGELAIOS_PAGE
    assert source_entry["dict"] == "bailly"
    assert source_segments
    assert any(segment["display_text"] == "qui forme un troupeau" for segment in source_segments)
    assert "troupeau" in metadata["learner_gloss"]
    assert "troupeau" in metadata["display_gloss"]


def test_bailly_entry_triples_preserve_block_hierarchy_and_encoded_refs() -> None:
    triples = bailly_entry_triples(
        {
            "entry_id": "bailly-p1848-c1-0026",
            "lemma": "πέτρος",
            "lemma_norm": "petros",
            "page_start": 1848,
            "page_end": 1848,
            "blocks": [
                {
                    "path": "00",
                    "marker": "head",
                    "text": "πέτρος, ου ( ὁ )",
                    "ordinal": 0,
                    "layout": {"column": 1, "top": 1005, "left": 104},
                },
                {
                    "path": "01",
                    "marker": "1",
                    "text": "pierre, Il. 7, 270 ||",
                    "ordinal": 1,
                    "layout": {"column": 1, "top": 1004, "left": 91},
                },
                {
                    "path": "01:00",
                    "marker": "2",
                    "text": "rar. c. πέτρα, rocher",
                    "ordinal": 2,
                    "layout": {"column": 1, "top": 1102, "left": 131},
                },
            ],
        }
    )

    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss_triple["metadata"]
    source_blocks = metadata["source_blocks"]
    source_segments = metadata["source_segments"]

    assert [block["path"] for block in source_blocks] == ["00", "01", "01:00"]
    assert source_blocks[0]["kind"] == "head"
    assert source_blocks[1]["level"] == 1
    assert source_blocks[1]["source_ref"] == "bailly:bailly-p1848-c1-0026:01"
    assert source_blocks[2]["parent_path"] == "01"
    assert source_blocks[2]["level"] == NESTED_BAILLY_BLOCK_LEVEL
    assert source_blocks[2]["source_ref"] == "bailly:bailly-p1848-c1-0026:01:00"
    assert source_blocks[2]["layout"] == {"column": 1, "top": 1102, "left": 131}
    assert metadata["source_entry"]["blocks"] == source_blocks
    assert source_segments[0]["source_ref"] == "bailly:bailly-p1848-c1-0026:01"
    assert source_segments[0]["source_path"] == "01"
    assert source_segments[1]["source_ref"] == "bailly:bailly-p1848-c1-0026:01:00"


def test_tool_filter_bailly_keeps_only_bailly_plan_calls_and_dependencies() -> None:
    normalized = NormalizedQuery(
        original="logos",
        language=LanguageHint.LANGUAGE_HINT_GRC,
        candidates=[
            CanonicalCandidate(
                lemma="λόγος",
                encodings={"accentless": "λόγος"},
                sources=["diogenes_parse"],
            )
        ],
        normalizations=[],
    )
    plan = ToolPlanner(PlannerConfig(max_candidates=2)).build(normalized)

    _filter_plan_tools(plan, "bailly")

    tools = [call.tool for call in plan.tool_calls]
    kept_call_ids = {call.call_id for call in plan.tool_calls}
    assert tools == [
        "fetch.bailly",
        "extract.bailly.json",
        "derive.bailly.entries",
        "claim.bailly.entries",
    ]
    assert "fetch.diogenes" not in tools
    assert kept_call_ids == {
        "bailly-1",
        "bailly-extract-1",
        "bailly-derive-1",
        "claim-bailly-1",
    }
    assert plan.dependencies
    assert all(
        dependency.from_call_id in kept_call_ids and dependency.to_call_id in kept_call_ids
        for dependency in plan.dependencies
    )
