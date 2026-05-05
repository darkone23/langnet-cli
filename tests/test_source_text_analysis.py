from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from click.testing import CliRunner

from langnet.cli import main
from langnet.execution.source_text import analyze_source_entry

FUZZ_FIXTURE_PATH = Path("tests/fixtures/source_entry_analysis_fuzz.json")


def test_analyze_source_entry_extracts_dico_gloss_and_references() -> None:
    analysis = analyze_source_entry(
        "dharma [ dharman ] m. n. loi, condition, nature propre | "
        "devoir religieux [ Mah. ] ; cf. svadharma",
        source_tool="dico",
    )

    assert analysis["learner_gloss"] == ("loi, condition, nature propre; devoir religieux [ Mah. ]")
    gloss_candidates = cast(list[dict[str, object]], analysis["gloss_candidates"])
    grammar_parse = cast(dict[str, object], analysis["grammar_parse"])
    source_references = cast(list[dict[str, object]], analysis["source_references"])
    source_segments = cast(list[dict[str, object]], analysis["source_segments"])
    assert gloss_candidates[0] == {
        "text": "loi, condition, nature propre",
        "kind": "grammar_definition",
        "labels": ["definition", "grammar_parse"],
    }
    assert grammar_parse["parser"] == "lark:dico_entry"
    assert grammar_parse["headword"] == "dharma"
    assert {"text": "Mah.", "kind": "bracket_reference", "labels": ["source_reference"]} in (
        source_references
    )
    assert {
        "text": "svadharma",
        "kind": "cross_reference",
        "labels": ["cross_reference", "source_reference"],
    } in source_references
    assert source_segments[-1] == {
        "index": 1,
        "raw_text": "cf. svadharma",
        "display_text": "cf. svadharma",
        "segment_type": "cross_reference_segment",
        "labels": ["cross_reference", "source_reference"],
    }


def test_analyze_source_entry_preserves_dico_later_sense_sections() -> None:
    analysis = analyze_source_entry(
        "purāṇa [ purā -na ] a. m. n. f. purāṇī vieux, ancien, antique ; fané — "
        "n. antiquité ; vieille légende, histoire ancienne | lit. «récit d'antan», "
        "recueil mythologique et religieux ; un purāṇa traite traditionnellement "
        "de cinq sujets",
        source_tool="dico",
    )

    learner_gloss = str(analysis["learner_gloss"])
    learner_segments = cast(list[dict[str, object]], analysis["learner_segments"])
    assert "vieille légende" in learner_gloss
    assert "récit d'antan" in learner_gloss
    assert learner_segments[0]["display_text"] == learner_gloss


def test_analyze_source_entry_extracts_gaffiot_citations_and_examples() -> None:
    analysis = analyze_source_entry(
        "ĭī, n. (princeps), 1 commencement : "
        "nec principium nec finem habere Cic. CM 78, n'avoir ni commencement ni fin "
        "|| principio Cic. Off. 1, 11",
        source_tool="gaffiot",
    )

    assert analysis["learner_gloss"] == "commencement"
    citations = cast(list[dict[str, object]], analysis["citations"])
    examples = cast(list[dict[str, object]], analysis["examples"])
    grammar_parse = cast(dict[str, object], analysis["grammar_parse"])
    source_segments = cast(list[dict[str, object]], analysis["source_segments"])
    citation_texts = [item["text"] for item in citations]
    assert "Cic. CM 78" in citation_texts
    assert "Cic. Off. 1, 11" in citation_texts
    assert examples[0]["citation"] == "Cic. CM 78"
    assert examples[0]["labels"] == ["example", "citation", "grammar_parse"]
    assert grammar_parse["parser"] == "lark:gaffiot_entry"
    assert source_segments[-1] == {
        "index": 1,
        "raw_text": "principio Cic. Off. 1, 11",
        "display_text": "principio Cic. Off. 1, 11",
        "segment_type": "example_segment",
        "labels": ["example", "citation", "source_reference"],
    }


def test_entry_analyze_cli_outputs_json() -> None:
    result = CliRunner().invoke(
        main,
        [
            "entry-analyze",
            "ĭī, n. (princeps), 1 commencement : principio Cic. Off. 1, 11",
            "--source-tool",
            "gaffiot",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["source_tool"] == "gaffiot"
    assert payload["learner_gloss"] == "commencement"
    assert payload["citations"][0]["text"] == "Cic. Off. 1, 11"


def test_entry_analyze_cli_reads_file(tmp_path) -> None:
    entry_path = tmp_path / "entry.txt"
    entry_path.write_text("dharma [ dharman ] m. n. loi, condition [ Mah. ]", encoding="utf-8")

    result = CliRunner().invoke(
        main,
        [
            "entry-analyze",
            "--file",
            str(entry_path),
            "--source-tool",
            "dico",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["learner_gloss"] == "loi, condition [ Mah. ]"
    assert payload["source_references"][0]["text"] == "Mah."


def test_source_entry_analysis_fuzz_fixture_minimum_invariants() -> None:
    cases = json.loads(FUZZ_FIXTURE_PATH.read_text(encoding="utf-8"))

    for case in cases:
        analysis = analyze_source_entry(case["entry"], source_tool=case["source_tool"])
        expect = case["expect"]
        grammar_parse = cast(dict[str, object] | None, analysis.get("grammar_parse"))
        expected_parsed = expect.get("parsed")
        if expected_parsed is True:
            assert grammar_parse is not None, case["id"]
            assert grammar_parse["parsed"] is True, case["id"]
            assert grammar_parse["parser"] == expect["parser"], case["id"]
        elif expected_parsed is False and grammar_parse is not None:
            assert grammar_parse.get("parsed") is not True, case["id"]

        expected_gloss = expect.get("learner_gloss_contains")
        if expected_gloss:
            assert expected_gloss in str(analysis.get("learner_gloss", "")), case["id"]

        expected_citation = expect.get("citation_contains")
        if expected_citation:
            citations = cast(list[dict[str, object]], analysis.get("citations", []))
            assert expected_citation in [item["text"] for item in citations], case["id"]

        expected_reference = expect.get("source_reference_contains")
        if expected_reference:
            refs = cast(list[dict[str, object]], analysis.get("source_references", []))
            assert expected_reference in [item["text"] for item in refs], case["id"]
