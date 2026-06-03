from __future__ import annotations

import json
import unittest.mock
from pathlib import Path

from click.testing import CliRunner

from langnet.cli import main
from langnet.encounter_briefing import (
    BRIEFING_SHORT_MAX_CHARS,
    BRIEFING_SUMMARY_SCHEMA_VERSION,
    apply_briefing_model_response,
    briefing_cache_key,
    build_encounter_briefing_batch,
    build_encounter_briefing_flow,
    load_cached_briefing_flow,
    run_encounter_briefing_model_benchmark,
    store_cached_briefing_flow,
    validate_briefing_summary,
)


def test_build_encounter_briefing_flow_extracts_reader_word_study_digest() -> None:
    payload = {
        "schema_version": "langnet.encounter.v1",
        "query": "arma",
        "language": "lat",
        "lexeme_anchors": ["lex:arma", "lex:armum#noun"],
        "request": {"tool_filter": "all"},
        "display": {
            "header": {"forms": ["arma"], "source_keys": []},
            "analysis": [
                {
                    "form": "arma",
                    "lemma": "armum",
                    "analysis": "noun; nominative; plural; neuter",
                    "source": "whitakers",
                    "foster_display": "Naming Function; Group; Neuter",
                    "display_text": (
                        "arma -> armum: noun; nominative; plural; neuter "
                        "[Foster: Naming Function; Group; Neuter] (whitakers)"
                    ),
                }
            ],
            "meanings": [
                {
                    "bucket_id": "bucket:arms",
                    "display_gloss": "weapons; arms",
                    "sources": ["whitaker", "lewis_1890"],
                    "witness_count": 2,
                    "confidence_label": "multi-witness",
                    "source_refs": ["whitakers:4768", "lewis_1890:arma"],
                    "source_detail_summary": {
                        "source_refs": ["Verg. A. 1.1"],
                        "examples": ["arma virumque cano", "arma => arms"],
                    },
                },
                {
                    "bucket_id": "bucket:equipment",
                    "display_gloss": "equipment",
                    "sources": ["whitaker"],
                    "witness_count": 1,
                    "confidence_label": "single-witness",
                    "source_refs": ["whitakers:4768"],
                },
            ],
        },
        "reader_search": {
            "items": [
                {
                    "work_id": "urn:cts:latinLit:phi0690.phi003",
                    "title": "Aeneid",
                    "author": "Vergil",
                    "citation_path": "1.1",
                    "snippet": "Arma virumque cano...",
                }
            ]
        },
    }

    flow = build_encounter_briefing_flow(payload)

    digest = flow["digest"]
    assert digest["query"] == "arma"
    assert digest["language"] == "lat"
    assert digest["forms"] == ["arma"]
    assert digest["tool_filter"] == "all"
    assert digest["morphology"][0]["foster_display"] == "Naming Function; Group; Neuter"
    assert digest["meanings"][0]["gloss"] == "weapons; arms"
    assert digest["meanings"][0]["source_refs"] == [
        "whitakers:4768",
        "lewis_1890:arma",
        "Verg. A. 1.1",
    ]
    assert digest["phrase_pairs"] == [
        {
            "phrase": "arma virumque cano",
            "gloss": "",
            "source": "whitaker",
            "source_ref": "whitakers:4768",
        },
        {
            "phrase": "arma",
            "gloss": "arms",
            "source": "whitaker",
            "source_ref": "whitakers:4768",
        },
    ]
    assert digest["reader_usages"][0]["label"] == "Vergil, Aeneid 1.1"
    assert digest["source_refs"] == ["whitakers:4768", "lewis_1890:arma", "Verg. A. 1.1"]
    assert "Do not invent references" in flow["prompt"]["system"]
    assert "Do not infer definitions from lemma names" in flow["prompt"]["system"]
    assert "langnet.encounter_briefing.summary.v1" in flow["prompt"]["user"]
    assert flow["generation"]["model"] == "openai:qwen/qwen3.7-max"
    assert flow["draft_output"]["meanings"][0]["summary"] == "weapons; arms"
    assert flow["draft_output"]["meanings"][0]["source_glosses"] == ["weapons; arms"]
    assert flow["draft_output"]["phrase_pairs"][1]["phrase"] == "arma"
    assert flow["draft_output"]["phrase_pairs"][1]["gloss"] == "arms"


def test_build_encounter_briefing_flow_filters_non_reference_source_notes() -> None:
    payload = {
        "schema_version": "langnet.encounter.v1",
        "query": "jñāna",
        "language": "san",
        "display": {
            "header": {"forms": ["jnaana"]},
            "meanings": [
                {
                    "bucket_id": "bucket:jnana",
                    "display_gloss": "knowledge",
                    "sources": ["cdsl", "dico"],
                    "witness_count": 2,
                    "confidence_label": "multi-witness",
                    "source_refs": ["dico:27.html#j~naana:0", "mw:80379.0"],
                    "source_detail_summary": {
                        "source_refs": ["ontologie.", "VS.", "Fig.", "L.", "ŚāṅkhŚr. xiii"],
                        "examples": ["jñāna => knowledge"],
                    },
                }
            ],
        },
    }

    flow = build_encounter_briefing_flow(payload)

    meaning = flow["digest"]["meanings"][0]
    assert meaning["source_refs"] == [
        "dico:27.html#j~naana:0",
        "mw:80379.0",
        "ŚāṅkhŚr. xiii",
    ]
    assert "ontologie." not in flow["digest"]["source_refs"]
    assert "VS." not in flow["digest"]["source_refs"]
    assert "Fig." not in flow["digest"]["source_refs"]
    assert "L." not in flow["digest"]["source_refs"]
    assert flow["draft_output"]["meanings"][0]["source_refs"] == [
        "dico:27.html#j~naana:0",
        "mw:80379.0",
        "ŚāṅkhŚr. xiii",
    ]


def test_encounter_briefing_spike_cli_reads_saved_payload() -> None:
    payload = json.dumps(
        {
            "schema_version": "langnet.encounter.v1",
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                        "confidence_label": "single-witness",
                        "source_detail_summary": {
                            "examples": ["arma => arms"],
                        },
                    }
                ],
            },
        }
    )

    result = CliRunner().invoke(
        main,
        [
            "encounter-briefing-spike",
            "--input-json",
            "-",
            "--model",
            "openai:qwen/qwen3.7-max",
        ],
        input=payload,
    )

    assert result.exit_code == 0, result.output
    flow = json.loads(result.output)
    assert flow["generation"]["model"] == "openai:qwen/qwen3.7-max"
    assert flow["digest"]["meanings"][0]["gloss"] == "weapons; arms"


def test_encounter_briefing_cli_reads_saved_payload() -> None:
    payload = json.dumps(
        {
            "schema_version": "langnet.encounter.v1",
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                        "confidence_label": "single-witness",
                    }
                ],
            },
        }
    )

    result = CliRunner().invoke(
        main,
        [
            "encounter-briefing",
            "--input-json",
            "-",
            "--model",
            "openai:qwen/qwen3.7-max",
        ],
        input=payload,
    )

    assert result.exit_code == 0, result.output
    flow = json.loads(result.output)
    assert flow["schema_version"] == "langnet.encounter_briefing.flow.v1"
    assert flow["digest"]["query"] == "arma"
    assert flow["draft_output"]["meanings"][0]["summary"] == "weapons; arms"


def test_encounter_briefing_cli_cache_only_returns_draft_on_miss(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "schema_version": "langnet.encounter.v1",
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )

    result = CliRunner().invoke(
        main,
        [
            "encounter-briefing",
            "--input-json",
            "-",
            "--cache-only",
            "--briefing-cache-dir",
            str(tmp_path),
        ],
        input=payload,
    )

    assert result.exit_code == 0, result.output
    flow = json.loads(result.output)
    assert flow["generation"]["status"] == "cache_miss"
    assert flow["final_output"]["short"] == flow["draft_output"]["short"]


def test_encounter_briefing_spike_cli_applies_saved_model_response() -> None:
    payload = json.dumps(
        {
            "schema_version": "langnet.encounter.v1",
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )
    model_response = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "arma: arms, weapons, or equipment.",
            "forms": ["arma"],
            "meanings": [
                {
                    "summary": "arms or weapons",
                    "source_glosses": ["weapons; arms"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "sources": ["whitaker"],
                    "translation_sources": [],
                    "confidence": "",
                    "source_refs": ["whitakers:4768"],
                }
            ],
            "grammar_functions": [],
            "word_decomposition": [],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["whitaker"],
            "caveats": [],
        }
    )

    result = CliRunner().invoke(
        main,
        [
            "encounter-briefing-spike",
            "--input-json",
            "-",
            "--model-response-json",
            model_response,
        ],
        input=payload,
    )

    assert result.exit_code == 0, result.output
    flow = json.loads(result.output)
    assert flow["generation"]["status"] == "accepted"
    assert flow["final_output"]["short"] == "arma: arms, weapons, or equipment."


def test_encounter_briefing_spike_cli_stores_saved_model_response_when_cache_enabled(
    tmp_path: Path,
) -> None:
    payload = json.dumps(
        {
            "schema_version": "langnet.encounter.v1",
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )
    model_response = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "arma: arms, weapons, or equipment.",
            "forms": ["arma"],
            "meanings": [
                {
                    "summary": "arms or weapons",
                    "source_glosses": ["weapons; arms"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "sources": ["whitaker"],
                    "translation_sources": [],
                    "confidence": "",
                    "source_refs": ["whitakers:4768"],
                }
            ],
            "grammar_functions": [],
            "word_decomposition": [],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["whitaker"],
            "caveats": [],
        }
    )

    result = CliRunner().invoke(
        main,
        [
            "encounter-briefing-spike",
            "--input-json",
            "-",
            "--model-response-json",
            model_response,
            "--briefing-cache-dir",
            str(tmp_path),
            "--cache-policy",
            "read-write",
        ],
        input=payload,
    )

    assert result.exit_code == 0, result.output
    assert list(tmp_path.glob("*.json"))


def test_encounter_briefing_cache_round_trips_completed_flow(tmp_path: Path) -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )
    completed = apply_briefing_model_response(
        flow,
        json.dumps(
            {
                "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
                "short": "arma: arms, weapons, or equipment.",
                "forms": ["arma"],
                "meanings": [
                    {
                        "summary": "arms or weapons",
                        "source_glosses": ["weapons; arms"],
                        "source_gloss_language": "en",
                        "translation_status": "english-or-unknown",
                        "sources": ["whitaker"],
                        "translation_sources": [],
                        "confidence": "",
                        "source_refs": ["whitakers:4768"],
                    }
                ],
                "grammar_functions": [],
                "word_decomposition": [],
                "reader_usages": [],
                "phrase_pairs": [],
                "dictionary_sources": ["whitaker"],
                "caveats": [],
            }
        ),
    )

    cache_key = briefing_cache_key(flow)
    assert cache_key.startswith("eb:")
    store_cached_briefing_flow(tmp_path, completed)

    cached = load_cached_briefing_flow(tmp_path, flow)

    assert cached is not None
    assert cached["generation"]["status"] == "cache_hit"
    assert cached["generation"]["cached_status"] == "accepted"
    assert cached["generation"]["cache_key"] == cache_key
    assert cached["final_output"]["short"] == "arma: arms, weapons, or equipment."


def test_encounter_briefing_batch_spike_cli_reads_jsonl_payloads() -> None:
    payloads = [
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [{"display_gloss": "weapons; arms", "sources": ["whitaker"]}],
            },
        },
        {
            "query": "λόγος",
            "language": "grc",
            "display": {
                "header": {"forms": ["logos"]},
                "meanings": [
                    {
                        "display_gloss": "word; account",
                        "sources": ["bailly", "translation"],
                        "translation_sources": ["bailly"],
                    }
                ],
            },
        },
    ]

    result = CliRunner().invoke(
        main,
        ["encounter-briefing-batch-spike", "--input-jsonl", "-"],
        input="\n".join(json.dumps(payload) for payload in payloads),
    )

    assert result.exit_code == 0, result.output
    batch = json.loads(result.output)
    assert batch["summary"]["total"] == len(payloads)
    assert batch["summary"]["flag_counts"]["translation_derived"] == 1


def test_run_encounter_briefing_model_benchmark_records_status_and_latency() -> None:
    expected_item_count = 2
    expected_fast_elapsed_ms = 250
    payloads = [
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    ]
    responses = {
        "openai:test-fast": json.dumps(
            {
                "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
                "short": "arma: arms or weapons.",
                "forms": ["arma"],
                "meanings": [
                    {
                        "summary": "arms or weapons",
                        "source_glosses": ["weapons; arms"],
                        "source_gloss_language": "en",
                        "translation_status": "english-or-unknown",
                        "sources": ["whitaker"],
                        "translation_sources": [],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
                "grammar_functions": [],
                "word_decomposition": [],
                "reader_usages": [],
                "phrase_pairs": [],
                "dictionary_sources": ["whitaker"],
                "caveats": [],
            }
        ),
        "openai:test-bad": "not json",
    }
    times = iter([10.0, 10.25, 20.0, 21.0])

    benchmark = run_encounter_briefing_model_benchmark(
        payloads,
        models=["openai:test-fast", "openai:test-bad"],
        generate_response=lambda flow, model: responses[model],
        clock=lambda: next(times),
    )

    assert benchmark["schema_version"] == "langnet.encounter_briefing.model_benchmark.v1"
    assert benchmark["summary"]["total_items"] == expected_item_count
    assert benchmark["summary"]["by_model"]["openai:test-fast"]["accepted"] == 1
    assert (
        benchmark["summary"]["by_model"]["openai:test-fast"]["avg_elapsed_ms"]
        == expected_fast_elapsed_ms
    )
    assert benchmark["summary"]["by_model"]["openai:test-bad"]["invalid_json"] == 1
    assert benchmark["items"][0]["status"] == "accepted"
    assert benchmark["items"][0]["final_short"] == "arma: arms or weapons."
    assert benchmark["items"][1]["status"] == "invalid_json"
    assert "raw_response" not in benchmark["items"][0]


def test_encounter_briefing_model_benchmark_cli_reads_jsonl_payloads() -> None:
    payload = {
        "query": "arma",
        "language": "lat",
        "display": {
            "header": {"forms": ["arma"]},
            "meanings": [
                {
                    "display_gloss": "weapons; arms",
                    "sources": ["whitaker"],
                    "source_refs": ["whitakers:4768"],
                }
            ],
        },
    }
    response = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "arma: arms or weapons.",
            "forms": ["arma"],
            "meanings": [
                {
                    "summary": "arms or weapons",
                    "source_glosses": ["weapons; arms"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "sources": ["whitaker"],
                    "translation_sources": [],
                    "source_refs": ["whitakers:4768"],
                }
            ],
            "grammar_functions": [],
            "word_decomposition": [],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["whitaker"],
            "caveats": [],
        }
    )

    with unittest.mock.patch("langnet.cli._encounter_briefing_generate_response") as generate:

        def generate_response(flow, *, model):
            assert model == "openai:test-fast"
            return response

        generate.side_effect = generate_response
        result = CliRunner().invoke(
            main,
            [
                "encounter-briefing-model-benchmark",
                "--input-jsonl",
                "-",
                "--model",
                "openai:test-fast",
            ],
            input=json.dumps(payload),
        )

    assert result.exit_code == 0, result.output
    benchmark = json.loads(result.output)
    assert benchmark["summary"]["by_model"]["openai:test-fast"]["accepted"] == 1
    assert benchmark["items"][0]["final_short"] == "arma: arms or weapons."


def test_encounter_briefing_digest_cleans_anchor_suffix_forms() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "arma",
            "language": "lat",
            "display": {"header": {"forms": ["armum#noun", "armo#verb"]}},
            "lexeme_anchors": ["lex:armum#noun", "lex:armo#verb"],
        }
    )

    assert flow["digest"]["forms"] == ["armum", "armo"]


def test_encounter_briefing_deterministic_short_is_sidebar_sized() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "λόγος",
            "language": "grc",
            "display": {
                "header": {"forms": ["logos"]},
                "meanings": [
                    {
                        "display_gloss": (
                            "account of money handled, σανίδες εἰς ἃς τὸν λ. "
                            "ἀναγράφομεν IG 1(2).374.191; ἐδίδοσαν τὸν λ. ib. "
                            "232.2; λ. δώσεις τῶν μισθῶν"
                        ),
                        "sources": ["diogenes"],
                        "source_refs": ["diogenes:00:00:00"],
                    },
                    {
                        "display_gloss": (
                            "generally, account, reckoning, explanation, narrative, "
                            "proportion, reason, argument, public account, private account, "
                            "verbal expression, rational principle, discussion, speech"
                        ),
                        "sources": ["diogenes"],
                    },
                ],
            },
        }
    )

    assert len(flow["draft_output"]["short"]) <= BRIEFING_SHORT_MAX_CHARS
    assert flow["draft_output"]["short"].endswith("...")


def test_encounter_briefing_draft_compacts_citation_heavy_dictionary_prose() -> None:
    source_gloss = (
        "Ἰησοῦς, οῦ, dat. οῖ, Joshua, LXX Jo. 1.1, al., Act.Ap. 7.45; "
        "in NT, with dat. -οῦ, Jesus, Ev.Matt. 9.27, al."
    )

    flow = build_encounter_briefing_flow(
        {
            "schema_version": "langnet.encounter.v1",
            "query": "Ἰησοῦ",
            "language": "grc",
            "display": {
                "header": {"forms": ["Ἰησοῦ"]},
                "meanings": [
                    {
                        "display_gloss": source_gloss,
                        "sources": ["diogenes"],
                        "source_refs": ["diogenes:00:00"],
                        "confidence_label": "single-witness",
                    }
                ],
            },
        }
    )

    meaning = flow["draft_output"]["meanings"][0]
    assert meaning["source_glosses"] == [source_gloss]
    assert meaning["summary"] == "Joshua; in NT, Jesus"
    assert flow["draft_output"]["short"] == "Ἰησοῦ: Joshua; in NT, Jesus"


def test_encounter_briefing_draft_drops_greek_example_fragments() -> None:
    source_gloss = (
        "reward of good tidings, given to the messenger, "
        "εὐαγγέλιον δέ μοι ἔστω Od. 14.152; "
        "οὐ . . εὐ. τόδε τείσω ib. 166"
    )

    flow = build_encounter_briefing_flow(
        {
            "schema_version": "langnet.encounter.v1",
            "query": "εὐαγγελίου",
            "language": "grc",
            "display": {
                "header": {"forms": ["euaggel_ion"]},
                "meanings": [
                    {
                        "display_gloss": source_gloss,
                        "sources": ["diogenes"],
                        "source_refs": ["diogenes:00:00"],
                        "confidence_label": "single-witness",
                    }
                ],
            },
        }
    )

    meaning = flow["draft_output"]["meanings"][0]
    assert meaning["source_glosses"] == [source_gloss]
    assert meaning["summary"] == "reward of good tidings, given to the messenger"
    assert "ib. 166" not in flow["draft_output"]["short"]


def test_encounter_briefing_phrase_pairs_skip_citation_only_examples() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "mater",
            "language": "lat",
            "display": {
                "meanings": [
                    {
                        "display_gloss": "mother",
                        "sources": ["lewis_1890"],
                        "source_refs": ["lewis_1890:mater"],
                        "source_detail_summary": {
                            "examples": [
                                "Cic. Fam. 9, 7, 1",
                                "alma mater",
                                "alma mater => nourishing mother",
                            ],
                        },
                    }
                ]
            },
        }
    )

    assert flow["digest"]["phrase_pairs"] == [
        {
            "phrase": "alma mater",
            "gloss": "",
            "source": "lewis_1890",
            "source_ref": "lewis_1890:mater",
        },
        {
            "phrase": "alma mater",
            "gloss": "nourishing mother",
            "source": "lewis_1890",
            "source_ref": "lewis_1890:mater",
        },
    ]


def test_encounter_briefing_digest_marks_translation_derived_meanings() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "λόγος",
            "language": "grc",
            "display": {
                "header": {"forms": ["logos"]},
                "meanings": [
                    {
                        "display_gloss": "word; account",
                        "sources": ["bailly", "translation"],
                        "source_refs": ["bailly:bailly-p1450-c1-0024"],
                        "translation_sources": ["bailly"],
                        "source_langs": ["fr"],
                    }
                ],
            },
        }
    )

    meaning = flow["digest"]["meanings"][0]
    assert flow["digest"]["translation_pipeline"] == {
        "output_language": "en",
        "source_gloss_policy": "copy-exact",
        "summary_policy": "english-paraphrase-from-evidence",
    }
    assert meaning["source_gloss_language"] == "fr"
    assert meaning["translation_status"] == "translation-derived"
    assert meaning["translation_sources"] == ["bailly"]
    assert "Translate source-language glosses into English" in flow["prompt"]["user"]
    assert flow["draft_output"]["meanings"][0]["source_gloss_language"] == "fr"
    assert flow["draft_output"]["meanings"][0]["translation_status"] == "translation-derived"


def test_encounter_briefing_separates_decomposition_from_clicked_word_morphology() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "jnana",
            "language": "san",
            "display": {
                "header": {"forms": ["j~naana", "jñāna"]},
                "analysis": [
                    {
                        "form": "jñāna",
                        "lemma": "jñāna",
                        "analysis": "n. sg. voc.",
                        "source": "heritage",
                    },
                    {
                        "form": "jña",
                        "lemma": "jña",
                        "analysis": "f. sg. nom.",
                        "source": "heritage",
                    },
                    {
                        "form": "an_2",
                        "lemma": "an_2",
                        "analysis": "pft. ac. sg. 3",
                        "source": "heritage",
                    },
                ],
            },
        }
    )

    assert [row["form"] for row in flow["digest"]["morphology"]] == ["jñāna"]
    assert [row["form"] for row in flow["digest"]["word_decomposition"]] == ["jña", "an_2"]
    assert flow["draft_output"]["grammar_functions"][0]["form"] == "jñāna"
    assert [row["form"] for row in flow["draft_output"]["word_decomposition"]] == [
        "jña",
        "an_2",
    ]


def test_encounter_briefing_batch_reports_quality_flags() -> None:
    batch = build_encounter_briefing_batch(
        [
            {
                "query": "arma",
                "language": "lat",
                "display": {
                    "header": {"forms": ["arma"]},
                    "meanings": [
                        {
                            "display_gloss": "weapons; arms",
                            "sources": ["whitaker"],
                        }
                    ],
                },
            },
            {
                "query": "jnana",
                "language": "san",
                "display": {
                    "header": {"forms": ["jñāna"]},
                    "analysis": [
                        {
                            "form": "jñāna",
                            "lemma": "jñāna",
                            "analysis": "n. sg. voc.",
                            "source": "heritage",
                        },
                        {
                            "form": "jña",
                            "lemma": "jña",
                            "analysis": "f. sg. nom.",
                            "source": "heritage",
                        },
                    ],
                    "meanings": [
                        {
                            "display_gloss": "jñāna n. knowledge, knowing, science, wisdom",
                            "sources": ["dico", "translation"],
                            "translation_sources": ["dico"],
                            "source_langs": ["fr"],
                        }
                    ],
                },
            },
        ]
    )

    assert batch["schema_version"] == "langnet.encounter_briefing.batch.v1"
    assert batch["summary"]["total"] == len(batch["items"])
    assert batch["summary"]["by_language"] == {"lat": 1, "san": 1}
    assert batch["summary"]["flag_counts"]["translation_derived"] == 1
    assert batch["summary"]["flag_counts"]["has_word_decomposition"] == 1
    assert batch["items"][0]["quality_flags"] == ["no_reader_usages"]
    assert set(batch["items"][1]["quality_flags"]) >= {
        "translation_derived",
        "has_word_decomposition",
        "needs_llm_summary",
        "no_reader_usages",
    }


def test_validate_briefing_summary_accepts_paraphrase_with_copied_evidence() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "analysis": [
                    {
                        "form": "arma",
                        "lemma": "armum",
                        "analysis": "noun; nominative; plural; neuter",
                        "source": "whitakers",
                        "foster_display": "Naming Function; Group; Neuter",
                    }
                ],
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                        "confidence_label": "single-witness",
                        "source_detail_summary": {
                            "examples": ["arma => arms"],
                        },
                    }
                ],
            },
            "reader_search": {
                "items": [
                    {
                        "title": "Aeneid",
                        "author": "Vergil",
                        "citation_path": "1.1",
                        "snippet": "Arma virumque cano...",
                    }
                ]
            },
        }
    )
    summary = {
        "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
        "short": "Here the word can be explained as arms or military equipment.",
        "forms": ["arma"],
        "meanings": [
            {
                "summary": "arms or military gear",
                "source_glosses": ["weapons; arms"],
                "source_gloss_language": "en",
                "translation_status": "english-or-unknown",
                "sources": ["whitaker"],
                "translation_sources": [],
                "source_refs": ["whitakers:4768"],
                "confidence": "single-witness",
            }
        ],
        "grammar_functions": [
            {
                "summary": "neuter plural noun",
                "form": "arma",
                "lemma": "armum",
                "analysis": "noun; nominative; plural; neuter",
                "foster_display": "Naming Function; Group; Neuter",
                "source": "whitakers",
            }
        ],
        "word_decomposition": [],
        "reader_usages": [
            {
                "label": "Vergil, Aeneid 1.1",
                "snippet": "Arma virumque cano...",
                "note": "opening usage",
            }
        ],
        "phrase_pairs": [
            {
                "phrase": "arma",
                "gloss": "arms",
                "source": "whitaker",
                "source_ref": "whitakers:4768",
                "note": "entry phrase with English gloss",
            }
        ],
        "dictionary_sources": ["whitaker", "whitakers"],
        "caveats": [],
    }

    assert validate_briefing_summary(summary, flow["digest"]) == []


def test_apply_briefing_model_response_accepts_valid_grounded_summary() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )
    response_text = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "arma: arms, weapons, or equipment.",
            "forms": ["arma"],
            "meanings": [
                {
                    "summary": "arms or weapons",
                    "source_glosses": ["weapons; arms"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "sources": ["whitaker"],
                    "translation_sources": [],
                    "confidence": "",
                    "source_refs": ["whitakers:4768"],
                }
            ],
            "grammar_functions": [],
            "word_decomposition": [],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["whitaker"],
            "caveats": [],
        }
    )

    completed = apply_briefing_model_response(flow, response_text)

    assert completed["generation"]["status"] == "accepted"
    assert completed["final_output"]["short"] == "arma: arms, weapons, or equipment."
    assert completed["model_output"]["meanings"][0]["summary"] == "arms or weapons"


def test_apply_briefing_model_response_accepts_decomposition_dictionary_source() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "राजा",
            "language": "san",
            "display": {
                "header": {"forms": ["rāja", "rajaḥ", "raaja"]},
                "analysis": [
                    {
                        "form": "rājan",
                        "lemma": "rājan",
                        "analysis": "m. sg. nom.",
                        "source": "heritage",
                    }
                ],
                "meanings": [
                    {
                        "display_gloss": "= 1. rājan, a king, sovereign",
                        "sources": ["cdsl"],
                        "source_refs": ["mw:176248.0"],
                    },
                    {
                        "display_gloss": (
                            "rāja iic. rājan . rājaka [ -ka ] m. roitelet. "
                            "rājakartṛ [ kartṛ ] m. soc. organisateur du sacre d'un roi."
                        ),
                        "sources": ["dico"],
                        "source_refs": ["dico:54.html#raaja:0"],
                        "source_langs": ["fr"],
                    },
                ],
            },
        }
    )
    response_text = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "A king or sovereign, with related compound forms.",
            "forms": ["rāja", "rajaḥ", "raaja"],
            "meanings": [
                {
                    "summary": "A king or sovereign.",
                    "source_glosses": ["= 1. rājan, a king, sovereign"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "sources": ["cdsl"],
                    "translation_sources": [],
                    "source_refs": ["mw:176248.0"],
                },
                {
                    "summary": "A French entry with derived royal compounds.",
                    "source_glosses": [
                        "rāja iic. rājan . rājaka [ -ka ] m. roitelet. "
                        "rājakartṛ [ kartṛ ] m. soc. organisateur du sacre d'un roi."
                    ],
                    "source_gloss_language": "fr",
                    "translation_status": "source-language",
                    "sources": ["dico"],
                    "translation_sources": [],
                    "source_refs": ["dico:54.html#raaja:0"],
                },
            ],
            "grammar_functions": [],
            "word_decomposition": [
                {
                    "form": "rājan",
                    "lemma": "rājan",
                    "analysis": "m. sg. nom.",
                    "source": "heritage",
                    "note": "Possible nominative singular analysis.",
                }
            ],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["cdsl", "dico", "heritage"],
            "caveats": [],
        }
    )

    assert flow["draft_output"]["dictionary_sources"] == ["cdsl", "dico", "heritage"]
    assert flow["draft_output"]["meanings"][0]["summary"] == "rājan, a king, sovereign"

    completed = apply_briefing_model_response(flow, response_text)

    assert completed["generation"]["status"] == "accepted"
    assert completed["final_output"]["short"] == "A king or sovereign, with related compound forms."


def test_apply_briefing_model_response_normalizes_scalar_caveat() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )
    response_text = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "arma: arms or weapons.",
            "forms": ["arma"],
            "meanings": [
                {
                    "summary": "arms or weapons",
                    "source_glosses": ["weapons; arms"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "sources": ["whitaker"],
                    "translation_sources": [],
                    "source_refs": ["whitakers:4768"],
                }
            ],
            "grammar_functions": [],
            "word_decomposition": [],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["whitaker"],
            "caveats": "Single-witness dictionary evidence.",
        }
    )

    completed = apply_briefing_model_response(flow, response_text)

    assert completed["generation"]["status"] == "accepted"
    assert completed["final_output"]["caveats"] == ["Single-witness dictionary evidence."]


def test_apply_briefing_model_response_rejects_unsupported_summary() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )
    response_text = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "arma: to arm or equip.",
            "forms": ["arma"],
            "meanings": [
                {
                    "summary": "to arm or equip",
                    "source_glosses": ["to arm"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "sources": ["whitaker"],
                    "translation_sources": [],
                    "source_refs": ["whitakers:4768"],
                }
            ],
            "grammar_functions": [],
            "word_decomposition": [],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["whitaker"],
            "caveats": [],
        }
    )

    completed = apply_briefing_model_response(flow, response_text)

    assert completed["generation"]["status"] == "rejected"
    assert completed["final_output"] == flow["draft_output"]
    assert completed["generation"]["validation_issues"][0]["code"] == "unsupported_meaning_gloss"


def test_apply_briefing_model_response_rejects_malformed_summary_shape() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "jnana",
            "language": "san",
            "display": {
                "header": {"forms": ["jñāna"]},
                "analysis": [
                    {
                        "form": "jña",
                        "lemma": "jña",
                        "analysis": "f. sg. nom.",
                        "source": "heritage",
                    }
                ],
                "meanings": [
                    {
                        "display_gloss": "knowledge",
                        "sources": ["cdsl"],
                        "source_refs": ["mw:80379.0"],
                    }
                ],
            },
        }
    )
    response_text = json.dumps(
        {
            "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
            "short": "jnana: knowledge.",
            "forms": ["jñāna"],
            "meanings": [
                {
                    "summary": "knowledge",
                    "source_glosses": ["knowledge"],
                    "source_gloss_language": "en",
                    "translation_status": "english-or-unknown",
                    "source_refs": ["mw:80379.0"],
                }
            ],
            "grammar_functions": [],
            "word_decomposition": ["jña (f. sg. nom.)"],
            "reader_usages": [],
            "phrase_pairs": [],
            "dictionary_sources": ["cdsl"],
            "caveats": [],
        }
    )

    completed = apply_briefing_model_response(flow, response_text)

    assert completed["generation"]["status"] == "rejected"
    assert {issue["code"] for issue in completed["generation"]["validation_issues"]} >= {
        "invalid_item_type",
        "missing_meaning_field",
    }


def test_validate_briefing_summary_accepts_unicode_normalized_source_gloss() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "λόγος",
            "language": "grc",
            "display": {
                "header": {"forms": ["logos"]},
                "meanings": [
                    {
                        "display_gloss": "word in gén.: ἔργα λόγου μέζω",
                        "sources": ["bailly", "translation"],
                        "translation_sources": ["bailly"],
                        "source_refs": ["bailly:bailly-p1450-c1-0024"],
                    }
                ],
            },
        }
    )
    summary = flow["draft_output"]
    summary["meanings"][0]["source_glosses"] = ["word in gén.: ἔργα λόγου μέζω"]

    assert validate_briefing_summary(summary, flow["digest"]) == []


def test_validate_briefing_summary_rejects_unsupported_evidence() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "arma",
            "language": "lat",
            "display": {
                "header": {"forms": ["arma"]},
                "analysis": [
                    {
                        "form": "arma",
                        "lemma": "armum",
                        "analysis": "noun; nominative; plural; neuter",
                        "source": "whitakers",
                    }
                ],
                "meanings": [
                    {
                        "display_gloss": "weapons; arms",
                        "sources": ["whitaker"],
                        "source_refs": ["whitakers:4768"],
                    }
                ],
            },
        }
    )
    summary = {
        "schema_version": BRIEFING_SUMMARY_SCHEMA_VERSION,
        "short": "Unsupported summary claims are caught through copied evidence fields.",
        "forms": ["arma"],
        "meanings": [
            {
                "summary": "to arm or equip",
                "source_glosses": ["to arm"],
                "sources": ["bailly"],
                "source_refs": ["Cic. Foo 1"],
            }
        ],
        "grammar_functions": [
            {
                "summary": "verb",
                "form": "armo",
                "analysis": "verb; present active imperative",
                "source": "diogenes",
            }
        ],
        "word_decomposition": [
            {
                "form": "ar",
                "lemma": "ar",
                "analysis": "invented segment",
                "source": "bailly",
            }
        ],
        "reader_usages": [{"label": "Vergil, Aeneid 1.1", "snippet": "arma"}],
        "phrase_pairs": [
            {
                "phrase": "arma",
                "gloss": "arm",
                "source": "bailly",
                "source_ref": "bailly:arma",
            }
        ],
        "dictionary_sources": ["bailly"],
        "caveats": [],
    }

    issues = validate_briefing_summary(summary, flow["digest"])

    assert {issue["code"] for issue in issues} >= {
        "unsupported_dictionary_source",
        "unsupported_form",
        "unsupported_grammar_analysis",
        "unsupported_meaning_gloss",
        "unsupported_phrase_pair",
        "unsupported_source_ref",
        "unsupported_reader_usage",
        "unsupported_word_decomposition",
    }


def test_validate_briefing_summary_rejects_unsupported_translation_metadata() -> None:
    flow = build_encounter_briefing_flow(
        {
            "query": "λόγος",
            "language": "grc",
            "display": {
                "header": {"forms": ["logos"]},
                "meanings": [
                    {
                        "display_gloss": "word; account",
                        "sources": ["bailly", "translation"],
                        "source_refs": ["bailly:bailly-p1450-c1-0024"],
                        "translation_sources": ["bailly"],
                        "source_langs": ["fr"],
                    }
                ],
            },
        }
    )
    summary = flow["draft_output"]
    summary["meanings"][0]["source_gloss_language"] = "en"
    summary["meanings"][0]["translation_status"] = "human-reviewed"

    issues = validate_briefing_summary(summary, flow["digest"])

    assert {issue["code"] for issue in issues} >= {
        "unsupported_source_gloss_language",
        "unsupported_translation_status",
    }
