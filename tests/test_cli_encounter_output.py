from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import duckdb
from click.testing import CliRunner

from langnet.cli import main
from langnet.execution.effects import ClaimEffect, ProvenanceLink
from langnet.translation import (
    BASE_SYSTEM,
    TranslationCache,
    TranslationRecord,
    build_translation_key,
    default_hints_for_language,
)

TRANSLATION_FIXTURE_PATH = Path("tests/fixtures/translation_cache_golden_rows.json")


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


def _translation_language(source_lexicon: str) -> str:
    return "lat" if source_lexicon == "gaffiot" else "san"


def _claim_from_translation_row(row: dict[str, object]) -> ClaimEffect:
    source_lexicon = str(row["source_lexicon"])
    headword = str(row["headword_norm"])
    source_ref = str(row["source_ref"])
    source_text = str(row["source_text"])
    sense_anchor = f"sense:lex:{headword}#{source_lexicon}-{row['entry_id']}"
    evidence: dict[str, object] = {
        "source_tool": source_lexicon,
        "source_ref": source_ref,
    }
    if source_lexicon == "gaffiot":
        evidence["variant_num"] = int(str(row["occurrence"]))
    return _claim_with_triples(
        tool=source_lexicon,
        subject=f"lex:{headword}",
        triples=[
            {
                "subject": f"lex:{headword}",
                "predicate": "has_sense",
                "object": sense_anchor,
                "metadata": {"evidence": dict(evidence)},
            },
            {
                "subject": sense_anchor,
                "predicate": "gloss",
                "object": source_text,
                "metadata": {
                    "source_lang": "fr",
                    "source_ref": source_ref,
                    "evidence": dict(evidence),
                },
            },
        ],
    )


def _write_translation_cache_from_rows(
    *,
    cache_path: Path,
    rows: list[dict[str, object]],
    model: str,
) -> None:
    conn = duckdb.connect(str(cache_path))
    try:
        cache = TranslationCache(conn)
        for row in rows:
            source_lexicon = str(row["source_lexicon"])
            key = build_translation_key(
                source_lexicon=source_lexicon,
                entry_id=str(row["entry_id"]),
                occurrence=int(str(row["occurrence"])),
                headword_norm=str(row["headword_norm"]),
                source_text=str(row["source_text"]),
                model=model,
                prompt=BASE_SYSTEM,
                hint="\n".join(default_hints_for_language(_translation_language(source_lexicon))),
            )
            cache.upsert(
                TranslationRecord(
                    key=key,
                    translated_text=str(row["translated_text"]),
                    status="ok",
                    duration_ms=5,
                )
            )
    finally:
        conn.close()


def test_encounter_sanskrit_cdsl_snapshot() -> None:
    triples = [
        {
            "subject": "lex:Darma",
            "predicate": "has_sense",
            "object": "sense:lex:Darma#1",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:1"},
                "display_iast": "dharma",
                "display_slp1": "Darma",
                "source_encoding": "slp1",
            },
        },
        {
            "subject": "sense:lex:Darma#1",
            "predicate": "gloss",
            "object": "dharma; duty",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:1"},
                "display_iast": "dharma",
                "display_slp1": "Darma",
                "source_encoding": "slp1",
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="cdsl", subject="lex:Darma", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "dharma",
                "cdsl",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "dharma [san]\n"
        "============\n"
        "Forms: dharma\n"
        "Source keys: Darma\n"
        "\n"
        "Meanings\n"
        "1. dharma; duty\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
        "   refs: mw:1\n"
    )


def test_encounter_sanskrit_heritage_analysis_snapshot() -> None:
    triples = [
        {
            "subject": "form:dharma",
            "predicate": "has_morphology",
            "object": {
                "lemma": "dharma",
                "form": "dharma",
                "analysis": "m. sg. voc.",
                "dictionary_url": "https://sanskrit.inria.fr/DICO/34.html#dharma",
            },
            "metadata": {
                "evidence": {"source_tool": "heritage", "raw_blob_ref": "raw_html"},
            },
        }
    ]
    result = SimpleNamespace(
        claims=[
            ClaimEffect(
                claim_id="clm-heritage",
                tool="claim.heritage.morph",
                call_id="call-heritage",
                source_call_id="derive-heritage",
                derivation_id="drv-heritage",
                subject="lex:dharma",
                predicate="has_morphology",
                value={"triples": triples},
                provenance_chain=[],
                handler_version="test",
            )
        ]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "dharma",
                "heritage",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "dharma [san]\n============\n\nAnalysis\n- dharma -> dharma: m. sg. voc. (heritage)\n"
    )


def test_encounter_retries_uncached_when_cached_normalization_has_no_senses() -> None:
    stale_result = SimpleNamespace(
        claims=[
            ClaimEffect(
                claim_id="clm-heritage",
                tool="claim.heritage.morph",
                call_id="call-heritage",
                source_call_id="derive-heritage",
                derivation_id="drv-heritage",
                subject="lex:nirudha",
                predicate="has_morphology",
                value={
                    "triples": [
                        {
                            "subject": "form:nirudha",
                            "predicate": "has_morphology",
                            "object": {
                                "lemma": "nirudha",
                                "form": "nirudha",
                                "analysis": "?",
                            },
                            "metadata": {
                                "evidence": {"source_tool": "heritage"},
                            },
                        }
                    ]
                },
                provenance_chain=[],
                handler_version="test",
            )
        ]
    )
    recovered_triples = [
        {
            "subject": "lex:niruqa",
            "predicate": "has_sense",
            "object": "sense:lex:niruqa#purged",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:109472.0"},
                "display_iast": "nirūḍha",
                "display_slp1": "nirUQa",
            },
        },
        {
            "subject": "sense:lex:niruqa#purged",
            "predicate": "gloss",
            "object": "purged",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:109472.0"},
                "display_iast": "nirūḍha",
                "display_slp1": "nirUQa",
            },
        },
    ]
    recovered_result = SimpleNamespace(
        claims=[_claim_with_triples(tool="cdsl", subject="lex:niruqa", triples=recovered_triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", side_effect=[stale_result, recovered_result]):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "nirudha",
                "--max-buckets",
                "1",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "nirudha [san]\n"
        "=============\n"
        "Forms: nirūḍha\n"
        "Source keys: nirUQa\n"
        "Warning: Cached normalization produced no sense buckets; retried with fresh "
        "normalization.\n"
        "\n"
        "Meanings\n"
        "1. purged\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
        "   refs: mw:109472.0\n"
    )


def test_encounter_latin_source_language_snapshot() -> None:
    triples = [
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#1",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:lupus",
                    "source_lang": "fr",
                }
            },
        },
        {
            "subject": "sense:lex:lupus#1",
            "predicate": "gloss",
            "object": "loup",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:lupus",
                    "source_lang": "fr",
                }
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "lupus",
                "gaffiot",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "lupus [lat]\n"
        "===========\n"
        "Forms: lupus\n"
        "\n"
        "Meanings\n"
        "1. loup\n"
        "   sources: gaffiot; witnesses: 1; confidence: single-witness\n"
        "   refs: gaffiot:lupus\n"
        "   source language: fr\n"
    )


def test_encounter_latin_translation_cache_snapshot() -> None:
    model = "test:model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        key = build_translation_key(
            source_lexicon="gaffiot",
            entry_id="gaffiot_38776",
            occurrence=1,
            headword_norm="lupus",
            source_text="loup",
            model=model,
            prompt=BASE_SYSTEM,
            hint="\n".join(default_hints_for_language("lat")),
        )
        conn = duckdb.connect(str(cache_path))
        try:
            TranslationCache(conn).upsert(
                TranslationRecord(
                    key=key,
                    translated_text="wolf",
                    status="ok",
                    duration_ms=5,
                )
            )
        finally:
            conn.close()

        triples = [
            {
                "subject": "lex:lupus",
                "predicate": "has_sense",
                "object": "sense:lex:lupus#gaffiot-loup",
                "metadata": {
                    "evidence": {
                        "source_tool": "gaffiot",
                        "source_ref": "gaffiot:gaffiot_38776",
                        "variant_num": 1,
                    }
                },
            },
            {
                "subject": "sense:lex:lupus#gaffiot-loup",
                "predicate": "gloss",
                "object": "loup",
                "metadata": {
                    "source_lang": "fr",
                    "source_ref": "gaffiot:gaffiot_38776",
                    "evidence": {
                        "source_tool": "gaffiot",
                        "source_ref": "gaffiot:gaffiot_38776",
                        "variant_num": 1,
                    },
                },
            },
        ]
        result = SimpleNamespace(
            claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
        )

        with patch("langnet.cli._execute_lookup_plan", return_value=result):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    "lat",
                    "lupus",
                    "gaffiot",
                    "--use-translation-cache",
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--max-buckets",
                    "2",
                    "--max-gloss-chars",
                    "80",
                ],
            )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "lupus [lat]\n"
        "===========\n"
        "Forms: lupus\n"
        "\n"
        "Meanings\n"
        "1. wolf\n"
        "   sources: translation; witnesses: 1; confidence: single-witness\n"
        "   refs: gaffiot:gaffiot_38776\n"
        "   translated from: gaffiot\n"
        "   source language: en\n"
        "2. loup\n"
        "   sources: gaffiot; witnesses: 1; confidence: single-witness\n"
        "   refs: gaffiot:gaffiot_38776\n"
        "   source language: fr\n"
    )


def test_encounter_sanskrit_dico_translation_cache_snapshot() -> None:
    model = "test:model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        key = build_translation_key(
            source_lexicon="dico",
            entry_id="dharma",
            occurrence=0,
            headword_norm="dharma",
            source_text="loi, devoir, vertu",
            model=model,
            prompt=BASE_SYSTEM,
            hint="\n".join(default_hints_for_language("san")),
        )
        conn = duckdb.connect(str(cache_path))
        try:
            TranslationCache(conn).upsert(
                TranslationRecord(
                    key=key,
                    translated_text="law, duty, virtue",
                    status="ok",
                    duration_ms=5,
                )
            )
        finally:
            conn.close()

        triples = [
            {
                "subject": "lex:dharma",
                "predicate": "has_sense",
                "object": "sense:lex:dharma#dico",
                "metadata": {
                    "evidence": {
                        "source_tool": "dico",
                        "source_ref": "dico:34.html#dharma:0",
                    }
                },
            },
            {
                "subject": "sense:lex:dharma#dico",
                "predicate": "gloss",
                "object": "loi, devoir, vertu",
                "metadata": {
                    "source_lang": "fr",
                    "source_ref": "dico:34.html#dharma:0",
                    "evidence": {
                        "source_tool": "dico",
                        "source_ref": "dico:34.html#dharma:0",
                    },
                },
            },
        ]
        result = SimpleNamespace(
            claims=[_claim_with_triples(tool="dico", subject="lex:dharma", triples=triples)]
        )

        with patch("langnet.cli._execute_lookup_plan", return_value=result):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    "san",
                    "dharma",
                    "dico",
                    "--use-translation-cache",
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--max-buckets",
                    "2",
                    "--max-gloss-chars",
                    "80",
                ],
            )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "dharma [san]\n"
        "============\n"
        "Forms: dharma\n"
        "\n"
        "Meanings\n"
        "1. law, duty, virtue\n"
        "   sources: translation; witnesses: 1; confidence: single-witness\n"
        "   refs: dico:34.html#dharma:0\n"
        "   translated from: dico\n"
        "   source language: en\n"
        "2. loi, devoir, vertu\n"
        "   sources: dico; witnesses: 1; confidence: single-witness\n"
        "   refs: dico:34.html#dharma:0\n"
        "   source language: fr\n"
    )


def test_encounter_json_projects_all_translation_golden_rows() -> None:
    fixture = json.loads(TRANSLATION_FIXTURE_PATH.read_text())
    rows = list(fixture["rows"])
    model = str(fixture["model"])
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        _write_translation_cache_from_rows(cache_path=cache_path, rows=rows, model=model)

        for row in rows:
            source_lexicon = str(row["source_lexicon"])
            language = _translation_language(source_lexicon)
            result = SimpleNamespace(claims=[_claim_from_translation_row(row)])

            with patch("langnet.cli._execute_lookup_plan", return_value=result):
                cli_result = CliRunner().invoke(
                    main,
                    [
                        "encounter",
                        language,
                        str(row["headword_norm"]),
                        source_lexicon,
                        "--use-translation-cache",
                        "--translation-cache-db",
                        str(cache_path),
                        "--translation-model",
                        model,
                        "--output",
                        "json",
                    ],
                )

            assert cli_result.exit_code == 0, cli_result.output
            payload = json.loads(cli_result.output)
            translated_buckets = [
                bucket
                for bucket in payload["buckets"]
                if bucket["display_gloss"] == row["translated_text"]
            ]
            assert len(translated_buckets) == 1
            translated_witness = translated_buckets[0]["witnesses"][0]
            assert translated_witness["source_tool"] == "translation"
            assert translated_witness["evidence"]["source_lexicon"] == source_lexicon
            assert translated_witness["evidence"]["source_ref"] == row["source_ref"]
            assert translated_witness["evidence"]["parsed_glosses"]


def test_encounter_prefers_multi_witness_bucket_snapshot() -> None:
    triples = [
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#apple",
            "metadata": {"evidence": {"source_tool": "fixture", "source_ref": "fixture:apple"}},
        },
        {
            "subject": "sense:lex:lupus#apple",
            "predicate": "gloss",
            "object": "apple",
            "metadata": {"evidence": {"source_tool": "fixture", "source_ref": "fixture:apple"}},
        },
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#wolf-a",
            "metadata": {"evidence": {"source_tool": "whitaker", "source_ref": "whitaker:lupus"}},
        },
        {
            "subject": "sense:lex:lupus#wolf-a",
            "predicate": "gloss",
            "object": "wolf",
            "metadata": {"evidence": {"source_tool": "whitaker", "source_ref": "whitaker:lupus"}},
        },
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#wolf-b",
            "metadata": {"evidence": {"source_tool": "diogenes", "source_ref": "ls:6387"}},
        },
        {
            "subject": "sense:lex:lupus#wolf-b",
            "predicate": "gloss",
            "object": "wolf",
            "metadata": {"evidence": {"source_tool": "diogenes", "source_ref": "ls:6387"}},
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="latin", subject="lex:lupus", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "lupus",
                "all",
                "--max-buckets",
                "2",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "lupus [lat]\n"
        "===========\n"
        "Forms: lupus\n"
        "\n"
        "Meanings\n"
        "1. wolf\n"
        "   sources: diogenes, whitaker; witnesses: 2; confidence: multi-witness\n"
        "   refs: whitaker:lupus, ls:6387\n"
        "2. apple\n"
        "   sources: fixture; witnesses: 1; confidence: single-witness\n"
        "   refs: fixture:apple\n"
    )


def test_encounter_greek_learner_output_snapshot() -> None:
    triples = [
        {
            "subject": "lex:λόγος",
            "predicate": "has_sense",
            "object": "sense:lex:λόγος#1",
            "metadata": {
                "evidence": {
                    "source_tool": "diogenes",
                    "source_ref": "lsj:logos",
                }
            },
        },
        {
            "subject": "sense:lex:λόγος#1",
            "predicate": "gloss",
            "object": "word; speech; account; reason",
            "metadata": {
                "evidence": {
                    "source_tool": "diogenes",
                    "source_ref": "lsj:logos",
                }
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="diogenes", subject="lex:λόγος", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "grc",
                "λόγος",
                "diogenes",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "λόγος [grc]\n"
        "===========\n"
        "Forms: λόγος\n"
        "\n"
        "Meanings\n"
        "1. word; speech; account; reason\n"
        "   sources: diogenes; witnesses: 1; confidence: single-witness\n"
        "   refs: lsj:logos\n"
    )
