from __future__ import annotations

from query_spec import CanonicalCandidate, LanguageHint, NormalizedQuery

from langnet.cli import _filter_plan_tools
from langnet.execution import predicates
from langnet.execution.handlers.lewis_1890 import lewis_1890_entry_triples
from langnet.planner.core import PlannerConfig, ToolPlanner


def test_lewis_1890_entry_triples_include_english_source_metadata() -> None:
    triples = lewis_1890_entry_triples(
        {
            "entry_id": "lewis-1890:lupus",
            "headword_raw": "lupus",
            "headword_norm": "lupus",
            "source_key": "lupus",
            "plain_text": "lupus ī, m a wolf: lupa, V.",
            "entry_hash": "hash-lupus",
        }
    )

    gloss = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss["metadata"]

    assert metadata["source_lang"] == "en"
    assert metadata["evidence"]["source_tool"] == "lewis_1890"
    assert metadata["source_entry"]["dict"] == "lewis_1890"
    assert "wolf" in metadata["display_gloss"]


def test_tool_filter_lewis_1890_keeps_only_lewis_plan_calls_and_dependencies() -> None:
    normalized = NormalizedQuery(
        original="lupus",
        language=LanguageHint.LANGUAGE_HINT_LAT,
        candidates=[
            CanonicalCandidate(lemma="lupus", encodings={}, sources=["diogenes_parse"]),
        ],
        normalizations=[],
    )
    plan = ToolPlanner(PlannerConfig(max_candidates=2)).build(normalized)

    _filter_plan_tools(plan, "lewis_1890")

    tools = [call.tool for call in plan.tool_calls]
    kept_call_ids = {call.call_id for call in plan.tool_calls}
    assert tools == [
        "fetch.lewis_1890",
        "extract.lewis_1890.json",
        "derive.lewis_1890.entries",
        "claim.lewis_1890.entries",
    ]
    assert kept_call_ids == {
        "lewis-1890-1",
        "lewis-1890-extract-1",
        "lewis-1890-derive-1",
        "claim-lewis-1890-1",
    }
    assert plan.dependencies
    assert all(
        dependency.from_call_id in kept_call_ids and dependency.to_call_id in kept_call_ids
        for dependency in plan.dependencies
    )
