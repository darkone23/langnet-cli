from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from langnet.cli import _encounter_morphology_fallback_terms, main
from langnet.execution.effects import ClaimEffect, ProvenanceLink
from langnet.reader_eval import evaluate_reader_token, summarize_reader_eval


def _claim_with_triples(
    *, tool: str, subject: str, triples: list[dict[str, object]]
) -> ClaimEffect:
    return ClaimEffect(
        claim_id=f"clm-{tool}",
        tool=f"claim.{tool}.fixture",
        call_id=f"call-{tool}",
        source_call_id=f"derive-{tool}",
        derivation_id=f"drv-{tool}",
        subject=subject,
        predicate="has_sense",
        value={"triples": triples},
        provenance_chain=[
            ProvenanceLink(
                stage="derive",
                tool=f"derive.{tool}.fixture",
                reference_id=f"drv-{tool}",
            )
        ],
        handler_version="test",
    )


def test_sanskrit_fallback_prefers_numbered_heritage_lemma_solution() -> None:
    claims = [
        {
            "tool": "claim.heritage.morph",
            "value": {
                "triples": [
                    {
                        "subject": "form:bhū_1",
                        "predicate": "has_morphology",
                        "object": {
                            "form": "bhū_1",
                            "lemma": "bhū_1",
                            "analysis": "imp. [1] ac. sg. 3",
                            "solution_number": 1,
                        },
                    },
                    {
                        "subject": "form:bhū_1",
                        "predicate": "has_morphology",
                        "object": {
                            "form": "bhū_1",
                            "lemma": "bhū_1",
                            "analysis": "imp. [1] ac. sg. 2",
                            "solution_number": 2,
                        },
                    },
                    {
                        "subject": "form:tu",
                        "predicate": "has_morphology",
                        "object": {
                            "form": "tu",
                            "lemma": "tu",
                            "analysis": "ind.",
                            "solution_number": 2,
                        },
                    },
                ]
            },
        }
    ]

    terms = _encounter_morphology_fallback_terms(
        claims,
        language="san",
        original="bhavatu",
    )

    assert terms == ["bhū"]


def test_reader_eval_scores_expected_lemma_gloss_and_morphology() -> None:
    result = evaluate_reader_token(
        {
            "passage_id": "aeneid_1_1_7",
            "language": "lat",
            "surface": "cano",
            "expected_lemmas": ["cano"],
            "expected_gloss_terms": ["sing"],
            "expect_morphology": True,
            "known_bad_gloss_terms": ["15th of month"],
        },
        {
            "lexeme_anchors": ["lex:cano"],
            "buckets": [
                {
                    "display_gloss": "sing; celebrate",
                    "witnesses": [
                        {
                            "lexeme_anchor": "lex:cano",
                            "gloss": "sing; celebrate",
                            "evidence": {"source_tool": "whitaker"},
                        }
                    ],
                }
            ],
        },
        morphology_rows=[
            {
                "source_tool": "whitaker",
                "form": "cano",
                "lemma": "cano",
                "analysis": "V 1 1 PRES ACTIVE IND",
            }
        ],
    )

    assert result["passed"] is True
    assert summarize_reader_eval([result]) == {
        "total": 1,
        "passed": 1,
        "failed": 0,
        "hit_rate": 1.0,
        "meaning_passed": 1,
        "meaning_failed": 0,
        "meaning_hit_rate": 1.0,
        "top_passed": 1,
        "top_failed": 0,
        "top_hit_rate": 1.0,
    }


def test_reader_eval_flags_known_bad_top_lemma() -> None:
    result = evaluate_reader_token(
        {
            "passage_id": "aeneid_1_1_7",
            "language": "lat",
            "surface": "virumque",
            "expected_lemmas": ["vir"],
            "expected_gloss_terms": ["man"],
            "known_bad_lemmas": ["virus"],
            "expect_morphology": False,
        },
        {
            "lexeme_anchors": ["lex:virus"],
            "buckets": [
                {
                    "display_gloss": "poison",
                    "witnesses": [{"lexeme_anchor": "lex:virus", "gloss": "poison"}],
                }
            ],
        },
    )

    assert result["passed"] is False
    assert result["checks"]["known_bad_lemma_not_top"] is False
    assert result["checks"]["lemma_hit"] is False


def test_reader_eval_allows_known_bad_lemma_below_first_bucket() -> None:
    result = evaluate_reader_token(
        {
            "passage_id": "aeneid_1_1_7",
            "language": "lat",
            "surface": "virumque",
            "expected_lemmas": ["vir"],
            "expected_gloss_terms": ["man"],
            "known_bad_lemmas": ["virus"],
            "expect_morphology": False,
        },
        {
            "lexeme_anchors": ["lex:vir", "lex:virus"],
            "buckets": [
                {
                    "display_gloss": "man; hero",
                    "witnesses": [{"lexeme_anchor": "lex:vir", "gloss": "man; hero"}],
                },
                {
                    "display_gloss": "poison",
                    "witnesses": [{"lexeme_anchor": "lex:virus", "gloss": "poison"}],
                },
            ],
        },
    )

    assert result["checks"]["known_bad_lemma_not_top"] is True
    assert result["checks"]["lemma_hit"] is True


def test_reader_eval_flags_expected_answer_below_first_bucket() -> None:
    result = evaluate_reader_token(
        {
            "passage_id": "aeneid_1_1_7",
            "language": "lat",
            "surface": "cano",
            "expected_lemmas": ["cano"],
            "expected_gloss_terms": ["sing"],
            "expect_morphology": False,
        },
        {
            "lexeme_anchors": ["lex:cano", "lex:canus"],
            "buckets": [
                {
                    "display_gloss": "white, gray",
                    "witnesses": [{"lexeme_anchor": "lex:canus", "gloss": "white, gray"}],
                },
                {
                    "display_gloss": "sing; celebrate",
                    "witnesses": [{"lexeme_anchor": "lex:cano", "gloss": "sing; celebrate"}],
                },
            ],
        },
    )

    assert result["checks"]["lemma_hit"] is True
    assert result["checks"]["top_lemma_hit"] is False
    assert result["checks"]["top_gloss_hit"] is False
    assert result["top_passed"] is False
    assert result["meaning_passed"] is False


def test_reader_eval_matches_sanskrit_iast_expected_to_slp1_anchor() -> None:
    result = evaluate_reader_token(
        {
            "passage_id": "bhagavad_gita_1_1_2",
            "language": "san",
            "surface": "dharmakṣetre",
            "expected_lemmas": ["dharmakṣetra"],
            "expected_gloss_terms": ["law-field"],
            "expected_components": ["dharma", "kṣetra"],
            "expect_morphology": False,
        },
        {
            "lexeme_anchors": ["lex:darmakzetra"],
            "buckets": [
                {
                    "display_gloss": "Darma—kzetra n. ‘law-field’ = kuru-kzetra",
                    "witnesses": [
                        {
                            "lexeme_anchor": "lex:darmakzetra",
                            "gloss": "Darma—kzetra n. ‘law-field’ = kuru-kzetra",
                            "evidence": {
                                "display_iast": "dharmakṣetra",
                                "display_slp1": "Darmakzetra",
                            },
                        }
                    ],
                }
            ],
        },
    )

    assert result["checks"]["lemma_hit"] is True
    assert result["checks"]["component_hit"] is True


def test_reader_eval_matches_greek_unicode_expected_to_diogenes_ascii_anchor() -> None:
    result = evaluate_reader_token(
        {
            "passage_id": "iliad_1_1_7",
            "language": "grc",
            "surface": "μῆνιν",
            "expected_lemmas": ["μῆνις"],
            "expected_gloss_terms": ["wrath"],
            "known_bad_lemmas": ["μήνιον"],
            "expect_morphology": False,
        },
        {
            "lexeme_anchors": ["lex:mhnis"],
            "buckets": [
                {
                    "display_gloss": "wrath; anger",
                    "witnesses": [{"lexeme_anchor": "lex:mhnis", "gloss": "wrath; anger"}],
                }
            ],
        },
    )

    assert result["checks"]["lemma_hit"] is True
    assert result["meaning_passed"] is True


def test_reader_eval_keeps_greek_known_bad_accent_check_strict() -> None:
    result = evaluate_reader_token(
        {
            "passage_id": "iliad_1_1_7",
            "language": "grc",
            "surface": "θεὰ",
            "expected_lemmas": ["θεά"],
            "expected_gloss_terms": ["goddess"],
            "known_bad_lemmas": ["θέα"],
            "expect_morphology": False,
        },
        {
            "lexeme_anchors": ["lex:qea"],
            "buckets": [
                {
                    "display_gloss": "goddess",
                    "witnesses": [{"lexeme_anchor": "lex:qea", "gloss": "goddess"}],
                }
            ],
        },
    )

    assert result["checks"]["lemma_hit"] is True
    assert result["checks"]["known_bad_lemma_not_top"] is True


def test_reader_eval_command_reports_json_with_patched_lookup(tmp_path: Path) -> None:
    fixture_path = tmp_path / "reader_eval.json"
    fixture_path.write_text(
        json.dumps(
            {
                "passages": [
                    {
                        "id": "fixture",
                        "language": "lat",
                        "work": "Fixture",
                        "citation": "1",
                        "tokens": [
                            {
                                "surface": "lupus",
                                "expected_lemmas": ["lupus"],
                                "expected_gloss_terms": ["wolf"],
                                "expect_morphology": False,
                            }
                        ],
                    }
                ]
            }
        )
    )
    triples = [
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#wolf",
            "metadata": {"evidence": {"source_tool": "fixture"}},
        },
        {
            "subject": "sense:lex:lupus#wolf",
            "predicate": "gloss",
            "object": "wolf",
            "metadata": {"evidence": {"source_tool": "fixture"}},
        },
    ]
    lookup_result = SimpleNamespace(
        claims=[_claim_with_triples(tool="fixture", subject="lex:lupus", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=lookup_result):
        cli_result = CliRunner().invoke(
            main,
            [
                "reader-eval",
                "--fixture",
                str(fixture_path),
                "--output",
                "json",
                "--translation-mode",
                "off",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    payload = json.loads(cli_result.output)
    assert payload["summary"] == {
        "total": 1,
        "passed": 1,
        "failed": 0,
        "hit_rate": 1.0,
        "meaning_passed": 1,
        "meaning_failed": 0,
        "meaning_hit_rate": 1.0,
        "top_passed": 1,
        "top_failed": 0,
        "top_hit_rate": 1.0,
    }
    assert payload["results"][0]["surface"] == "lupus"
